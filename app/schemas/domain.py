"""Custom branded domain schemas."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class DomainCreate(BaseModel):
    """Add a custom branded domain."""
    domain: str = Field(..., min_length=3, max_length=255, description="Domain name, e.g., link.mybrand.com")


class DomainResponse(BaseModel):
    """Custom domain details and verification instructions."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    domain: str
    verification_token: str
    is_verified: bool
    is_active: bool
    verified_at: Optional[datetime] = None
    created_at: datetime


class DomainVerifyResponse(BaseModel):
    """Result of domain DNS verification check."""
    domain: str
    is_verified: bool
    message: str
