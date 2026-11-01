"""API key lifecycle service with scopes and revocation."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from app.core.exceptions import BadRequestException, NotFoundException, UnauthorizedException
from app.core.security import ensure_utc, generate_api_key, hash_token
from app.models.api_key import ApiKey
from app.models.user import User
from app.repositories.api_key_repo import ApiKeyRepository
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreatedResponse, ApiKeyResponse


class ApiKeyService:
    """Service handling machine credentials, verification, and scopes."""

    def __init__(self, api_key_repo: ApiKeyRepository):
        self.api_key_repo = api_key_repo

    async def create_key(self, user: User, payload: ApiKeyCreate) -> ApiKeyCreatedResponse:
        """Generate high-entropy scoped API key, store hash, and return secret once."""
        full_key, prefix, hashed_key = generate_api_key(prefix="lks")

        expires_at = None
        if payload.expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)

        scopes_str = ",".join(s.strip() for s in payload.scopes if s.strip())

        api_key = ApiKey(
            user_id=user.id,
            name=payload.name,
            prefix=prefix,
            hashed_key=hashed_key,
            scopes=scopes_str,
            is_active=True,
            expires_at=expires_at,
        )

        saved = await self.api_key_repo.create(api_key)

        return ApiKeyCreatedResponse(
            id=saved.id,
            name=saved.name,
            prefix=saved.prefix,
            scopes=[s.strip() for s in saved.scopes.split(",") if s.strip()],
            is_active=saved.is_active,
            expires_at=saved.expires_at,
            last_used_at=saved.last_used_at,
            created_at=saved.created_at,
            key=full_key,
        )

    async def list_keys(self, user: User) -> List[ApiKeyResponse]:
        """List active and revoked API keys for the authenticated user."""
        keys = await self.api_key_repo.list_by_user(user.id)
        return [
            ApiKeyResponse(
                id=k.id,
                name=k.name,
                prefix=k.prefix,
                scopes=[s.strip() for s in k.scopes.split(",") if s.strip()],
                is_active=k.is_active,
                expires_at=k.expires_at,
                last_used_at=k.last_used_at,
                created_at=k.created_at,
            )
            for k in keys
        ]

    async def revoke_key(self, key_id: uuid.UUID, user: User) -> None:
        """Revoke API key."""
        success = await self.api_key_repo.revoke(key_id, user.id)
        if not success:
            raise NotFoundException("API key not found or already inactive")

    async def verify_key(self, raw_key: str, required_scope: Optional[str] = None) -> Tuple[User, ApiKey]:
        """Verify API key, check expiry, validate scope, and update last_used timestamp."""
        hashed = hash_token(raw_key.strip())
        key_record = await self.api_key_repo.get_by_hashed_key(hashed)

        if not key_record or not key_record.is_active:
            raise UnauthorizedException("Invalid or inactive API key")

        now = datetime.now(timezone.utc)
        if key_record.expires_at and ensure_utc(key_record.expires_at) <= now:
            raise UnauthorizedException("API key has expired")

        if required_scope and not key_record.has_scope(required_scope):
            raise UnauthorizedException(f"API key missing required permission scope '{required_scope}'")

        # Update last used timestamp
        await self.api_key_repo.update_last_used(key_record.id)

        user = key_record.user
        if not user or not user.is_active:
            raise UnauthorizedException("Associated user account is deactivated")

        return user, key_record
