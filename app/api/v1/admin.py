"""Administrative governance, abuse reporting, and domain blocklist endpoints."""

import uuid
from typing import Annotated, List
from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_admin_service, get_current_active_admin
from app.models.user import User
from app.schemas.abuse import (
    AbuseReportCreate,
    AbuseReportResponse,
    BlockedDomainCreate,
    BlockedDomainResponse,
)
from app.schemas.common import ApiResponse
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["Admin & Moderation"])


@router.post("/abuse-reports", response_model=ApiResponse[AbuseReportResponse], status_code=status.HTTP_201_CREATED)
async def submit_abuse_report(
    payload: AbuseReportCreate,
    admin_service: Annotated[AdminService, Depends(get_admin_service)],
) -> ApiResponse[AbuseReportResponse]:
    """Submit an abuse report for a malicious or phishing short link."""
    res = await admin_service.submit_abuse_report(payload)
    return ApiResponse(success=True, data=res)


@router.get("/abuse-reports", response_model=ApiResponse[List[AbuseReportResponse]])
async def list_pending_abuse_reports(
    admin_user: Annotated[User, Depends(get_current_active_admin)],
    admin_service: Annotated[AdminService, Depends(get_admin_service)],
) -> ApiResponse[List[AbuseReportResponse]]:
    """List pending abuse reports (Administrator only)."""
    reports = await admin_service.list_abuse_reports()
    return ApiResponse(success=True, data=reports)


@router.put("/abuse-reports/{report_id}/resolve", response_model=ApiResponse[dict])
async def resolve_abuse_report(
    report_id: uuid.UUID,
    admin_user: Annotated[User, Depends(get_current_active_admin)],
    admin_service: Annotated[AdminService, Depends(get_admin_service)],
) -> ApiResponse[dict]:
    """Mark an abuse report as RESOLVED (Administrator only)."""
    await admin_service.resolve_abuse_report(report_id, "RESOLVED", admin_user)
    return ApiResponse(success=True, data={"message": "Abuse report marked as RESOLVED"})


@router.post("/blocked-domains", response_model=ApiResponse[BlockedDomainResponse], status_code=status.HTTP_201_CREATED)
async def block_malicious_domain(
    payload: BlockedDomainCreate,
    admin_user: Annotated[User, Depends(get_current_active_admin)],
    admin_service: Annotated[AdminService, Depends(get_admin_service)],
) -> ApiResponse[BlockedDomainResponse]:
    """Add a domain to the security blocklist (Administrator only)."""
    res = await admin_service.block_domain(payload)
    return ApiResponse(success=True, data=res)
