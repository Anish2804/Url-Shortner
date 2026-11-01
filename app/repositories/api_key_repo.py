"""API key repository for cryptographic credential lookups."""

import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.api_key import ApiKey
from app.repositories.base import BaseRepository


class ApiKeyRepository(BaseRepository[ApiKey]):
    """Database operations for API keys."""

    def __init__(self, session: AsyncSession):
        super().__init__(ApiKey, session)

    async def get_by_hashed_key(self, hashed_key: str) -> Optional[ApiKey]:
        stmt = (
            select(ApiKey)
            .where(ApiKey.hashed_key == hashed_key, ApiKey.is_active.is_(True))
            .options(selectinload(ApiKey.user))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: uuid.UUID) -> Sequence[ApiKey]:
        stmt = select(ApiKey).where(ApiKey.user_id == user_id).order_by(ApiKey.created_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def revoke(self, key_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        stmt = (
            update(ApiKey)
            .where(ApiKey.id == key_id, ApiKey.user_id == user_id)
            .values(is_active=False)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def update_last_used(self, key_id: uuid.UUID) -> None:
        stmt = (
            update(ApiKey)
            .where(ApiKey.id == key_id)
            .values(last_used_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)
        await self.session.flush()
