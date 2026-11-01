"""Abuse reporting and domain blocklist schemas."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class AbuseReportCreate(BaseModel):
    """Submit an abuse report for a malicious or phishing short link."""
    short_code: str = Field(..., min_length=1, max_length=64)
    reporter_email: Optional[str] = Field(default=None, max_length=255)
    reason: str = Field(..., min_length=3, max_length=100, description="e.g., Phishing, Malware, Spam, Copyright")
    details: Optional[str] = Field(default=None, max_length=2000)


class AbuseReportResponse(BaseModel):
    """Abuse report status view."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    short_code: str
    reporter_email: Optional[str] = None
    reason: str
    details: Optional[str] = None
    status: str
    created_at: datetime


class BlockedDomainCreate(BaseModel):
    """Administrative creation of blocked domain entry."""
    domain: str = Field(..., min_length=3, max_length=255, description="Domain name to block, e.g., badsite.com")
    reason: str = Field(..., min_length=3, max_length=255)


class BlockedDomainResponse(BaseModel):
    """Blocked domain response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    domain: str
    reason: str
    is_active: bool
    created_at: datetime
