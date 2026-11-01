"""Custom domain repository for branded shortening."""

import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import CustomDomain
from app.repositories.base import BaseRepository


class DomainRepository(BaseRepository[CustomDomain]):
    """Database operations for custom domains."""

    def __init__(self, session: AsyncSession):
        super().__init__(CustomDomain, session)

    async def get_by_domain(self, domain: str) -> Optional[CustomDomain]:
        clean = domain.strip().lower()
        stmt = select(CustomDomain).where(CustomDomain.domain == clean)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_by_user(self, user_id: uuid.UUID) -> Sequence[CustomDomain]:
        stmt = select(CustomDomain).where(CustomDomain.user_id == user_id).order_by(CustomDomain.created_at.desc())
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def mark_verified(self, domain_id: uuid.UUID) -> bool:
        stmt = (
            update(CustomDomain)
            .where(CustomDomain.id == domain_id)
            .values(is_verified=True, verified_at=datetime.now(timezone.utc))
        )
        res = await self.session.execute(stmt)
        await self.session.flush()
        return res.rowcount > 0
