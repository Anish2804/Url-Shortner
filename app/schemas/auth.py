from typing import Any
import re
from pydantic import BaseModel, Field, field_validator, model_validator


class UserRegister(BaseModel):
    """User registration payload."""
    email: str = Field(..., max_length=255, description="Valid user email address")
    username: str = Field(..., min_length=2, max_length=50, description="Unique username")
    password: str = Field(..., min_length=6, max_length=128, description="User password")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if "@" not in clean or "." not in clean:
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
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class UserLogin(BaseModel):
    """User login credential payload."""
    username_or_email: str | None = Field(default=None, max_length=255)
    username: str | None = None
    password: str = Field(..., min_length=1, max_length=128)

    @model_validator(mode="before")
    @classmethod
    def resolve_username_or_email(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("username_or_email") and data.get("username"):
                data["username_or_email"] = data["username"]
        return data


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


class EmailVerificationRequest(BaseModel):
    """Request email verification token."""
    email: str = Field(..., max_length=255)


class EmailVerificationConfirm(BaseModel):
    """Confirm email verification with received token."""
    token: str = Field(..., min_length=10)
