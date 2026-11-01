"""URL creation, update, bulk ingestion, and search schemas."""

import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class UrlCreate(BaseModel):
    """Single URL creation request."""
    original_url: str = Field(..., max_length=2048, description="Target destination URL")
    custom_alias: Optional[str] = Field(default=None, min_length=3, max_length=50, description="Optional custom alias")
    title: Optional[str] = Field(default=None, max_length=255, description="Descriptive label for link")
    redirect_http_code: int = Field(default=302, description="Redirect status code (301 or 302)")
    expires_at: Optional[datetime] = Field(default=None, description="Optional expiration date/time")
    password: Optional[str] = Field(default=None, min_length=4, max_length=128, description="Optional link protection password")
    is_one_time: bool = Field(default=False, description="Whether link auto-expires after single use")

    @field_validator("redirect_http_code")
    @classmethod
    def validate_redirect_code(cls, v: int) -> int:
        if v not in (301, 302, 307, 308):
            raise ValueError("Redirect code must be 301, 302, 307, or 308")
        return v

    @field_validator("custom_alias")
    @classmethod
    def validate_custom_alias(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip()
            if not re.match(r"^[a-zA-Z0-9_\-]+$", clean):
                raise ValueError("Custom alias may only contain alphanumeric characters, underscores, and dashes")
            return clean
        return v

    @field_validator("expires_at")
    @classmethod
    def validate_expiration(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None:
            # Ensure timezone awareness
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            if v <= datetime.now(timezone.utc):
                raise ValueError("Expiration date must be in the future")
        return v


class UrlBulkCreate(BaseModel):
    """Bulk URL creation request payload."""
    items: List[UrlCreate] = Field(..., min_length=1, max_length=100, description="Batch of URLs (up to 100)")


class UrlUpdate(BaseModel):
    """Update existing shortened URL destination or metadata."""
    original_url: Optional[str] = Field(default=None, max_length=2048)
    title: Optional[str] = Field(default=None, max_length=255)
    redirect_http_code: Optional[int] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)
    expires_at: Optional[datetime] = Field(default=None)
    password: Optional[str] = Field(default=None)
    remove_password: bool = Field(default=False, description="Clear existing password protection")

    @field_validator("redirect_http_code")
    @classmethod
    def validate_redirect_code(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v not in (301, 302, 307, 308):
            raise ValueError("Redirect code must be 301, 302, 307, or 308")
        return v


class UrlResponse(BaseModel):
    """Short URL response payload."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    short_code: str
    original_url: str
    short_url: str = Field(default="", description="Full ready-to-use short URL")
    custom_alias: Optional[str] = None
    title: Optional[str] = None
    redirect_http_code: int
    is_active: bool
    is_expired: bool = False
    is_password_protected: bool = False
    is_one_time: bool
    is_consumed: bool
    click_count: int
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class UrlBulkResponse(BaseModel):
    """Response containing successfully created and failed batch items."""
    created: List[UrlResponse] = Field(default_factory=list)
    failed: List[dict] = Field(default_factory=list)
    total_requested: int
    total_successful: int


class UrlFilterParams(BaseModel):
    """Query filters for URL listings."""
    search: Optional[str] = Field(default=None, description="Search in short_code, alias, title, or original_url")
    is_active: Optional[bool] = Field(default=None, description="Filter by active status")
    is_expired: Optional[bool] = Field(default=None, description="Filter by expired status")
    sort_by: str = Field(default="created_at", description="Field to sort by: created_at, click_count, title")
    sort_order: str = Field(default="desc", description="Sort order: asc or desc")


class UrlAccessVerification(BaseModel):
    """Payload when accessing password-protected short link."""
    password: str = Field(..., min_length=1, max_length=128)
