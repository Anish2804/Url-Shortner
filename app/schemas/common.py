"""Standardized API response wrappers, envelopes, and pagination schemas."""

from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Detailed error object following API standard."""
    code: str = Field(..., description="Machine-readable error identifier")
    message: str = Field(..., description="Human-readable explanation of the error")
    details: Optional[dict[str, Any]] = Field(default=None, description="Additional context or validation details")


class ApiResponse(BaseModel, Generic[T]):
    """Unified API response envelope."""
    model_config = ConfigDict(from_attributes=True)

    success: bool = Field(default=True, description="Indicates if the request succeeded")
    data: Optional[T] = Field(default=None, description="Payload data returned on success")
    error: Optional[ErrorDetail] = Field(default=None, description="Error data returned on failure")


class PaginationParams(BaseModel):
    """Query parameters for offset-based pagination."""
    page: int = Field(default=1, ge=1, description="Page number starting at 1")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page (max 100)")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard pagination payload."""
    items: List[T] = Field(default_factory=list, description="List of items on current page")
    total: int = Field(..., description="Total items across all pages")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="True if next page exists")
    has_prev: bool = Field(..., description="True if previous page exists")
