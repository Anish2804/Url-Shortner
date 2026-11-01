"""Administrative service for abuse reports, domain blocking, and platform governance."""

import uuid
from typing import List
from app.core.exceptions import NotFoundException
from app.models.abuse import AbuseReport
from app.models.user import User
from app.repositories.abuse_repo import AbuseRepository
from app.schemas.abuse import (
    AbuseReportCreate,
    AbuseReportResponse,
    BlockedDomainCreate,
    BlockedDomainResponse,
)


class AdminService:
    """Service handling platform moderation, abuse reports, and domain blocks."""

    def __init__(self, abuse_repo: AbuseRepository):
        self.abuse_repo = abuse_repo

    async def submit_abuse_report(self, payload: AbuseReportCreate) -> AbuseReportResponse:
        """Public endpoint allowing users to flag phishing or malicious short links."""
        report = AbuseReport(
            short_code=payload.short_code,
            reporter_email=payload.reporter_email,
            reason=payload.reason,
            details=payload.details,
            status="PENDING",
        )
        saved = await self.abuse_repo.create(report)
        return AbuseReportResponse.model_validate(saved)

    async def list_abuse_reports(self, skip: int = 0, limit: int = 50) -> List[AbuseReportResponse]:
        """Admin list of pending abuse reports."""
        reports = await self.abuse_repo.list_pending_reports(skip=skip, limit=limit)
        return [AbuseReportResponse.model_validate(r) for r in reports]

    async def resolve_abuse_report(
        self,
        report_id: uuid.UUID,
        status: str,
        admin_user: User,
    ) -> None:
        """Review and resolve abuse report."""
        success = await self.abuse_repo.update_report_status(
            report_id=report_id,
            status=status,
            reviewed_by=admin_user.id,
        )
        if not success:
            raise NotFoundException("Abuse report not found")

    async def block_domain(self, payload: BlockedDomainCreate) -> BlockedDomainResponse:
        """Add domain to security blocklist."""
        blocked = await self.abuse_repo.add_blocked_domain(payload.domain, payload.reason)
        return BlockedDomainResponse.model_validate(blocked)
