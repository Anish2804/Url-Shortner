"""Unified export of all Pydantic request and response schemas."""

from app.schemas.abuse import (
    AbuseReportCreate,
    AbuseReportResponse,
    BlockedDomainCreate,
    BlockedDomainResponse,
)
from app.schemas.analytics import (
    AnalyticsDateFilter,
    CategoryBreakdownItem,
    ClickEventResponse,
    TimeSeriesPoint,
    UrlAnalyticsSummary,
    UserAnalyticsOverview,
)
from app.schemas.api_key import (
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeyResponse,
)
from app.schemas.auth import (
    ChangePasswordRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
)
from app.schemas.common import (
    ApiResponse,
    ErrorDetail,
    PaginatedResponse,
    PaginationParams,
)
from app.schemas.domain import (
    DomainCreate,
    DomainResponse,
    DomainVerifyResponse,
)
from app.schemas.url import (
    UrlAccessVerification,
    UrlBulkCreate,
    UrlBulkResponse,
    UrlCreate,
    UrlFilterParams,
    UrlResponse,
    UrlUpdate,
)
from app.schemas.user import (
    RoleResponse,
    UserProfileUpdate,
    UserResponse,
)

__all__ = [
    "ApiResponse",
    "ErrorDetail",
    "PaginationParams",
    "PaginatedResponse",
    "UserRegister",
    "UserLogin",
    "TokenResponse",
    "RefreshTokenRequest",
    "PasswordResetRequest",
    "PasswordResetConfirm",
    "ChangePasswordRequest",
    "RoleResponse",
    "UserResponse",
    "UserProfileUpdate",
    "UrlCreate",
    "UrlBulkCreate",
    "UrlUpdate",
    "UrlResponse",
    "UrlBulkResponse",
    "UrlFilterParams",
    "UrlAccessVerification",
    "ApiKeyCreate",
    "ApiKeyResponse",
    "ApiKeyCreatedResponse",
    "AnalyticsDateFilter",
    "ClickEventResponse",
    "TimeSeriesPoint",
    "CategoryBreakdownItem",
    "UrlAnalyticsSummary",
    "UserAnalyticsOverview",
    "AbuseReportCreate",
    "AbuseReportResponse",
    "BlockedDomainCreate",
    "BlockedDomainResponse",
    "DomainCreate",
    "DomainResponse",
    "DomainVerifyResponse",
]
