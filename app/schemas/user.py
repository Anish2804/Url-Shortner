"""User profile and identity schemas."""

import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    description: Optional[str] = None


class UserResponse(BaseModel):
    """User profile response without sensitive credentials."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    username: str
    is_active: bool
    is_verified: bool
    is_superuser: bool
    roles: List[RoleResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class UserProfileUpdate(BaseModel):
    """User profile update payload."""
    email: Optional[str] = Field(default=None, max_length=255)
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)
