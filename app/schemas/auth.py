"""Authentication and registration request/response schemas."""

import re
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserRegister(BaseModel):
    """User registration payload."""
    email: str = Field(..., max_length=255, description="Valid user email address")
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    password: str = Field(..., min_length=8, max_length=128, description="Strong user password")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip().lower()
        pattern = r"^[\w\.\+\-]+@[\w\-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, clean):
            raise ValueError("Invalid email address format")
        return clean

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        clean = v.strip().lower()
        if not re.match(r"^[a-zA-Z0-9_\-\.]+$", clean):
            raise ValueError("Username may only contain letters, numbers, underscores, dashes, and dots")
        return clean

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseModel):
    """User login credential payload."""
    username_or_email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class TokenResponse(BaseModel):
    """Access and refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(default=1800, description="Access token expiration in seconds")


class RefreshTokenRequest(BaseModel):
    """Token rotation request."""
    refresh_token: str = Field(..., min_length=10)


class PasswordResetRequest(BaseModel):
    """Request password reset link/token."""
    email: str = Field(..., max_length=255)


class PasswordResetConfirm(BaseModel):
    """Confirm password reset with received token."""
    token: str = Field(..., min_length=10)
    new_password: str = Field(..., min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    """Change password for authenticated user."""
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)
