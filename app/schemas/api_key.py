"""API Key creation and management schemas."""

import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ApiKeyCreate(BaseModel):
    """API key creation request."""
    name: str = Field(..., min_length=1, max_length=100, description="Friendly label for the API key")
    scopes: List[str] = Field(
        default=["urls:read", "urls:write", "analytics:read"],
        description="List of permission scopes granted to this key",
    )
    expires_in_days: Optional[int] = Field(
        default=None,
        ge=1,
        le=365,
        description="Optional expiration in days (up to 365)",
    )


class ApiKeyResponse(BaseModel):
    """API key response without raw secret."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    prefix: str = Field(..., description="Key prefix for identification, e.g., lks_8a1f")
    scopes: List[str] = Field(default_factory=list)
    is_active: bool
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    created_at: datetime


class ApiKeyCreatedResponse(ApiKeyResponse):
    """Returned once upon key generation containing the unhashed secret key."""
    key: str = Field(..., description="Full secret API key. Store safely; it will NOT be shown again.")
