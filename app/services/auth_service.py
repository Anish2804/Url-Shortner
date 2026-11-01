"""Authentication service managing user identity, Argon2id security, lockout, and JWT tokens."""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import uuid

from app.core.config import settings
from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
)
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    decode_access_token,
    ensure_utc,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.user import RefreshToken, User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import (
    ChangePasswordRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
)
from app.schemas.user import UserResponse

logger = get_logger("auth_service")


class AuthService:
    """Service handling registration, authentication, token rotation, and lockout protection."""

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def register(self, payload: UserRegister) -> UserResponse:
        """Register new user account with hashed password and default user role."""
        # Check uniqueness
        if await self.user_repo.get_by_email(payload.email):
            raise ConflictException("An account with this email address already exists")
        if await self.user_repo.get_by_username(payload.username):
            raise ConflictException("This username is already taken")

        hashed_pw = hash_password(payload.password)
        default_role = await self.user_repo.get_or_create_role("user", "Standard platform user")

        user = User(
            email=payload.email,
            username=payload.username,
            hashed_password=hashed_pw,
            is_active=True,
            is_verified=False,
            roles=[default_role],
        )

        saved_user = await self.user_repo.create(user)
        logger.info("New user registered: %s (id=%s)", saved_user.username, saved_user.id)
        return UserResponse.model_validate(saved_user)

    async def login(
        self,
        payload: UserLogin,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> TokenResponse:
        """Authenticate user with brute-force lockout defense and return token pair."""
        user = await self.user_repo.get_by_identifier(payload.username_or_email)
        if not user:
            raise UnauthorizedException("Invalid username or password")

        # Check account lockout
        now = datetime.now(timezone.utc)
        locked_until = ensure_utc(user.locked_until)
        if locked_until and locked_until > now:
            minutes_left = max(1, int((locked_until - now).total_seconds() / 60))
            raise ForbiddenException(
                f"Account is temporarily locked due to multiple failed login attempts. Try again in {minutes_left} minutes."
            )

        if not user.is_active:
            raise ForbiddenException("This account has been deactivated")

        # Verify password
        if not verify_password(payload.password, user.hashed_password):
            await self.user_repo.increment_failed_logins(
                user,
                max_attempts=settings.MAX_FAILED_LOGIN_ATTEMPTS,
                lockout_minutes=settings.ACCOUNT_LOCKOUT_MINUTES,
            )
            raise UnauthorizedException("Invalid username or password")

        # Reset failed attempts on successful login
        await self.user_repo.reset_failed_logins(user)

        # Generate tokens
        return await self._issue_token_pair(user, user_agent, ip_address)

    async def refresh_tokens(
        self,
        raw_refresh_token: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> TokenResponse:
        """Perform refresh token rotation with reuse detection."""
        hashed = hash_token(raw_refresh_token)
        token_record = await self.user_repo.get_refresh_token(hashed)

        if not token_record:
            raise UnauthorizedException("Invalid or revoked refresh token")

        # Check if already revoked (reuse detection: revoke all user sessions!)
        if token_record.revoked:
            logger.warning(
                "Revoked refresh token reuse detected for user %s! Revoking all sessions as security precaution.",
                token_record.user_id,
            )
            await self.user_repo.revoke_all_user_refresh_tokens(token_record.user_id)
            raise UnauthorizedException("Compromised token detected. All active sessions have been revoked for your safety.")

        now = datetime.now(timezone.utc)
        if ensure_utc(token_record.expires_at) <= now:
            raise UnauthorizedException("Refresh token has expired. Please log in again.")

        user = token_record.user
        if not user or not user.is_active:
            raise UnauthorizedException("Account is not active")

        # Generate new refresh token
        new_raw, new_hash = generate_refresh_token()
        # Revoke current token and link to replacement
        await self.user_repo.revoke_refresh_token(token_record, replaced_by=new_hash)

        # Save new refresh token record
        new_token_record = RefreshToken(
            user_id=user.id,
            hashed_token=new_hash,
            expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            user_agent=user_agent[:512] if user_agent else None,
            ip_address=ip_address[:45] if ip_address else None,
        )
        await self.user_repo.save_refresh_token(new_token_record)

        # Generate new access token
        access_token = create_access_token(
            subject=str(user.id),
            claims={"username": user.username, "roles": [r.name for r in user.roles]},
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_raw,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def logout(self, raw_refresh_token: str) -> None:
        """Revoke refresh token on logout."""
        hashed = hash_token(raw_refresh_token)
        token_record = await self.user_repo.get_refresh_token(hashed)
        if token_record:
            await self.user_repo.revoke_refresh_token(token_record)

    async def change_password(self, user: User, payload: ChangePasswordRequest) -> None:
        """Update authenticated user's password and revoke active refresh tokens."""
        if not verify_password(payload.old_password, user.hashed_password):
            raise BadRequestException("Current password is incorrect")

        user.hashed_password = hash_password(payload.new_password)
        await self.user_repo.update(user)
        # Revoke other sessions
        await self.user_repo.revoke_all_user_refresh_tokens(user.id)
        logger.info("Password changed for user %s", user.username)

    async def _issue_token_pair(
        self,
        user: User,
        user_agent: Optional[str],
        ip_address: Optional[str],
    ) -> TokenResponse:
        """Helper to generate JWT access token and persist new refresh token."""
        access_token = create_access_token(
            subject=str(user.id),
            claims={"username": user.username, "roles": [r.name for r in user.roles]},
        )
        raw_refresh, hashed_refresh = generate_refresh_token()
        now = datetime.now(timezone.utc)

        token_record = RefreshToken(
            user_id=user.id,
            hashed_token=hashed_refresh,
            expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            user_agent=user_agent[:512] if user_agent else None,
            ip_address=ip_address[:45] if ip_address else None,
        )
        await self.user_repo.save_refresh_token(token_record)

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
