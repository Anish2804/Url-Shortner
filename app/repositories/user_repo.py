"""User and authentication repository."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import RefreshToken, Role, User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """User database access layer with role management and lockout tracking."""

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        stmt = select(User).where(User.id == user_id).options(selectinload(User.roles))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email.strip().lower()).options(selectinload(User.roles))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        stmt = select(User).where(User.username == username.strip().lower()).options(selectinload(User.roles))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_identifier(self, identifier: str) -> Optional[User]:
        clean = identifier.strip().lower()
        stmt = (
            select(User)
            .where((User.email == clean) | (User.username == clean))
            .options(selectinload(User.roles))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create_role(self, role_name: str, description: Optional[str] = None) -> Role:
        stmt = select(Role).where(Role.name == role_name)
        result = await self.session.execute(stmt)
        role = result.scalar_one_or_none()
        if not role:
            role = Role(name=role_name, description=description)
            self.session.add(role)
            await self.session.flush()
            await self.session.refresh(role)
        return role

    async def increment_failed_logins(self, user: User, max_attempts: int, lockout_minutes: int) -> None:
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= max_attempts:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=lockout_minutes)
        await self.session.flush()

    async def reset_failed_logins(self, user: User) -> None:
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.now(timezone.utc)
        await self.session.flush()

    # Refresh token methods
    async def save_refresh_token(self, token: RefreshToken) -> RefreshToken:
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_refresh_token(self, hashed_token: str) -> Optional[RefreshToken]:
        stmt = (
            select(RefreshToken)
            .where(RefreshToken.hashed_token == hashed_token)
            .options(selectinload(RefreshToken.user).selectinload(User.roles))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, token: RefreshToken, replaced_by: Optional[str] = None) -> None:
        token.revoked = True
        if replaced_by:
            token.replaced_by_hash = replaced_by
        await self.session.flush()

    async def revoke_all_user_refresh_tokens(self, user_id: uuid.UUID) -> None:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
            .values(revoked=True)
        )
        await self.session.execute(stmt)
        await self.session.flush()
