"""Analytics filtering, time-series rollups, and breakdown schemas."""

import uuid
from datetime import date, datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AnalyticsDateFilter(BaseModel):
    """Time window filter for analytics queries."""
    start_date: Optional[date] = Field(default=None, description="Start date (inclusive, YYYY-MM-DD)")
    end_date: Optional[date] = Field(default=None, description="End date (inclusive, YYYY-MM-DD)")


class ClickEventResponse(BaseModel):
    """Individual sanitized click event response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    short_code: str
    clicked_at: datetime
    country_code: Optional[str] = None
    city: Optional[str] = None
    device_type: str
    browser: str
    os: str
    referrer_domain: Optional[str] = None
    is_bot: bool


class TimeSeriesPoint(BaseModel):
    """Datapoint for time-series charts (daily or hourly)."""
    date_or_hour: str = Field(..., description="ISO date or datetime string")
    clicks: int = Field(default=0)
    unique_visitors: int = Field(default=0)


class CategoryBreakdownItem(BaseModel):
    """Categorical count and percentage for distribution charts."""
    category: str
    count: int
    percentage: float = Field(default=0.0, description="Percentage of total (0-100)")


class UrlAnalyticsSummary(BaseModel):
    """Complete aggregated analytics report for a specific shortened URL."""
    short_code: str
    original_url: str
    total_clicks: int
    unique_visitors: int
    bot_clicks: int
    time_series: List[TimeSeriesPoint] = Field(default_factory=list)
    devices: List[CategoryBreakdownItem] = Field(default_factory=list)
    browsers: List[CategoryBreakdownItem] = Field(default_factory=list)
    operating_systems: List[CategoryBreakdownItem] = Field(default_factory=list)
    countries: List[CategoryBreakdownItem] = Field(default_factory=list)
    referrers: List[CategoryBreakdownItem] = Field(default_factory=list)


class TopUrlItem(BaseModel):
    """Top performing URL overview."""
    short_code: str
    title: Optional[str] = None
    original_url: str
    total_clicks: int


class UserAnalyticsOverview(BaseModel):
    """Platform-wide or user-wide analytics dashboard summary."""
    total_urls: int
    total_clicks: int
    total_unique_visitors: int
    total_bot_clicks: int
    top_urls: List[TopUrlItem] = Field(default_factory=list)
    daily_traffic: List[TimeSeriesPoint] = Field(default_factory=list)
