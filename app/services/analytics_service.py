"""Analytics service for aggregated summaries, time-series metrics, and CSV reporting."""

from datetime import date
from typing import Optional
from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.user import User
from app.repositories.analytics_repo import AnalyticsRepository
from app.repositories.url_repo import UrlRepository
from app.schemas.analytics import (
    CategoryBreakdownItem,
    TimeSeriesPoint,
    UrlAnalyticsSummary,
    UserAnalyticsOverview,
)


class AnalyticsService:
    """Service providing aggregated dashboard metrics and exports."""

    def __init__(self, analytics_repo: AnalyticsRepository, url_repo: UrlRepository):
        self.analytics_repo = analytics_repo
        self.url_repo = url_repo

    async def get_url_analytics(
        self,
        short_code: str,
        user: User,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> UrlAnalyticsSummary:
        """Fetch complete analytical breakdown for a URL owned by the user."""
        url = await self.url_repo.get_by_short_code(short_code)
        if not url:
            url = await self.url_repo.get_by_alias(short_code)
        if not url:
            raise NotFoundException("Shortened URL not found")

        # Authorization: owner or admin
        if url.user_id != user.id and not user.is_superuser:
            raise ForbiddenException("You do not have permission to view analytics for this URL")

        raw_summary = await self.analytics_repo.get_url_summary(url.id, start_date, end_date)

        time_series = [TimeSeriesPoint(**p) for p in raw_summary["time_series"]]
        devices = [CategoryBreakdownItem(**d) for d in raw_summary["devices"]]
        browsers = [CategoryBreakdownItem(**b) for b in raw_summary["browsers"]]
        operating_systems = [CategoryBreakdownItem(**o) for o in raw_summary["operating_systems"]]
        countries = [CategoryBreakdownItem(**c) for c in raw_summary["countries"]]
        referrers = [CategoryBreakdownItem(**r) for r in raw_summary["referrers"]]

        return UrlAnalyticsSummary(
            short_code=url.short_code,
            original_url=url.original_url,
            total_clicks=raw_summary["total_clicks"],
            unique_visitors=raw_summary["unique_visitors"],
            bot_clicks=raw_summary["bot_clicks"],
            time_series=time_series,
            devices=devices,
            browsers=browsers,
            operating_systems=operating_systems,
            countries=countries,
            referrers=referrers,
        )

    async def get_user_overview(
        self,
        user: User,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> UserAnalyticsOverview:
        """Fetch platform summary across all links for authenticated user."""
        overview_data = await self.analytics_repo.get_user_overview(user.id, start_date, end_date)
        return UserAnalyticsOverview.model_validate(overview_data)

    async def export_clicks_csv(
        self,
        short_code: str,
        user: User,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> str:
        """Generate raw click event CSV string for download."""
        url = await self.url_repo.get_by_short_code(short_code)
        if not url:
            url = await self.url_repo.get_by_alias(short_code)
        if not url:
            raise NotFoundException("Shortened URL not found")

        if url.user_id != user.id and not user.is_superuser:
            raise ForbiddenException("You do not have permission to export analytics for this URL")

        return await self.analytics_repo.export_clicks_csv(url.id, start_date, end_date)
