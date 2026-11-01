"""Distributed analytics reporting and CSV export endpoints."""

from datetime import date
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, Response

from app.api.dependencies import get_analytics_service, require_analytics_read
from app.models.user import User
from app.schemas.analytics import (
    UrlAnalyticsSummary,
    UserAnalyticsOverview,
)
from app.schemas.common import ApiResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview", response_model=ApiResponse[UserAnalyticsOverview])
async def get_account_analytics_overview(
    current_user: Annotated[User, Depends(require_analytics_read)],
    analytics_service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    start_date: Annotated[Optional[date], Query(description="Start date (YYYY-MM-DD)")] = None,
    end_date: Annotated[Optional[date], Query(description="End date (YYYY-MM-DD)")] = None,
) -> ApiResponse[UserAnalyticsOverview]:
    """Get aggregated dashboard overview across all links owned by the authenticated user."""
    overview = await analytics_service.get_user_overview(
        user=current_user,
        start_date=start_date,
        end_date=end_date,
    )
    return ApiResponse(success=True, data=overview)


@router.get("/urls/{short_code}", response_model=ApiResponse[UrlAnalyticsSummary])
@router.get("/{short_code}", response_model=ApiResponse[UrlAnalyticsSummary])
async def get_url_analytics_summary(
    short_code: str,
    current_user: Annotated[User, Depends(require_analytics_read)],
    analytics_service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    start_date: Annotated[Optional[date], Query(description="Start date (YYYY-MM-DD)")] = None,
    end_date: Annotated[Optional[date], Query(description="End date (YYYY-MM-DD)")] = None,
) -> ApiResponse[UrlAnalyticsSummary]:
    """Retrieve comprehensive aggregated click analytics, time series, and categorical breakdowns."""
    summary = await analytics_service.get_url_analytics(
        short_code=short_code,
        user=current_user,
        start_date=start_date,
        end_date=end_date,
    )
    return ApiResponse(success=True, data=summary)


@router.get("/urls/{short_code}/export")
@router.get("/{short_code}/export")
async def export_url_analytics_csv(
    short_code: str,
    current_user: Annotated[User, Depends(require_analytics_read)],
    analytics_service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    start_date: Annotated[Optional[date], Query(description="Start date (YYYY-MM-DD)")] = None,
    end_date: Annotated[Optional[date], Query(description="End date (YYYY-MM-DD)")] = None,
) -> Response:
    """Export raw click event logs as a downloadable CSV spreadsheet."""
    csv_content = await analytics_service.export_clicks_csv(
        short_code=short_code,
        user=current_user,
        start_date=start_date,
        end_date=end_date,
    )
    filename = f"analytics_{short_code}_{date.today().isoformat()}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
