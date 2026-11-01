"""Abuse report and blocked domain repository."""

import uuid
from typing import Optional, Sequence
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.abuse import AbuseReport, BlockedDomain
from app.repositories.base import BaseRepository


class AbuseRepository(BaseRepository[AbuseReport]):
    """Database operations for abuse reports and domain blocks."""

    def __init__(self, session: AsyncSession):
        super().__init__(AbuseReport, session)

    async def list_pending_reports(self, skip: int = 0, limit: int = 50) -> Sequence[AbuseReport]:
        stmt = (
            select(AbuseReport)
            .where(AbuseReport.status == "PENDING")
            .order_by(AbuseReport.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def update_report_status(
        self,
        report_id: uuid.UUID,
        status: str,
        reviewed_by: uuid.UUID,
    ) -> bool:
        stmt = (
            update(AbuseReport)
            .where(AbuseReport.id == report_id)
            .values(status=status, reviewed_by=reviewed_by)
        )
        res = await self.session.execute(stmt)
        await self.session.flush()
        return res.rowcount > 0

    async def is_domain_blocked(self, domain: str) -> bool:
        clean = domain.strip().lower()
        stmt = select(BlockedDomain).where(BlockedDomain.domain == clean, BlockedDomain.is_active.is_(True))
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none() is not None

    async def add_blocked_domain(self, domain: str, reason: str) -> BlockedDomain:
        clean = domain.strip().lower()
        blocked = BlockedDomain(domain=clean, reason=reason, is_active=True)
        self.session.add(blocked)
        await self.session.flush()
        return blocked
