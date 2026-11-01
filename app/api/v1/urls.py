"""URL management API endpoints for creation, updates, pagination, and QR generation."""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import get_url_service, get_user_from_jwt_or_api_key
from app.models.user import User
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationParams
from app.schemas.url import (
    UrlBulkCreate,
    UrlBulkResponse,
    UrlCreate,
    UrlFilterParams,
    UrlResponse,
    UrlUpdate,
)
from app.services.url_service import UrlService

router = APIRouter(prefix="/urls", tags=["URLs"])


@router.post("/", response_model=ApiResponse[UrlResponse], status_code=status.HTTP_201_CREATED)
async def create_short_url(
    payload: UrlCreate,
    current_user: Annotated[User, Depends(get_user_from_jwt_or_api_key)],
    url_service: Annotated[UrlService, Depends(get_url_service)],
) -> ApiResponse[UrlResponse]:
    """Create a new shortened URL with collision-resistant Base62 ID or custom alias."""
    res = await url_service.create_url(payload, current_user)
    return ApiResponse(success=True, data=res)


@router.post("/bulk", response_model=ApiResponse[UrlBulkResponse], status_code=status.HTTP_201_CREATED)
async def create_bulk_short_urls(
    payload: UrlBulkCreate,
    current_user: Annotated[User, Depends(get_user_from_jwt_or_api_key)],
    url_service: Annotated[UrlService, Depends(get_url_service)],
) -> ApiResponse[UrlBulkResponse]:
    """Batch-create multiple shortened URLs in a single request (up to 100 items)."""
    res = await url_service.create_bulk_urls(payload, current_user)
    return ApiResponse(success=True, data=res)


@router.get("/", response_model=ApiResponse[PaginatedResponse[UrlResponse]])
async def list_user_urls(
    current_user: Annotated[User, Depends(get_user_from_jwt_or_api_key)],
    url_service: Annotated[UrlService, Depends(get_url_service)],
    pagination: Annotated[PaginationParams, Depends()],
    search: Annotated[Optional[str], Query(description="Search short code, alias, title or destination")] = None,
    is_active: Annotated[Optional[bool], Query(description="Filter by active status")] = None,
    is_expired: Annotated[Optional[bool], Query(description="Filter by expiration")] = None,
    sort_by: Annotated[str, Query(description="Sort field: created_at, click_count, title")] = "created_at",
    sort_order: Annotated[str, Query(description="Sort order: asc or desc")] = "desc",
) -> ApiResponse[PaginatedResponse[UrlResponse]]:
    """List, search, filter, and paginate through URLs owned by the authenticated user."""
    filters = UrlFilterParams(
        search=search,
        is_active=is_active,
        is_expired=is_expired,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    items, total = await url_service.list_user_urls(
        user=current_user,
        filters=filters,
        skip=pagination.offset,
        limit=pagination.limit,
    )
    total_pages = max(1, (total + pagination.page_size - 1) // pagination.page_size)

    paginated = PaginatedResponse[UrlResponse](
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
        has_next=pagination.page < total_pages,
        has_prev=pagination.page > 1,
    )
    return ApiResponse(success=True, data=paginated)


@router.get("/{short_code}", response_model=ApiResponse[UrlResponse])
async def get_url_details(
    short_code: str,
    url_service: Annotated[UrlService, Depends(get_url_service)],
) -> ApiResponse[UrlResponse]:
    """Get metadata for a specific shortened URL by short code or alias."""
    res = await url_service.get_url_by_code(short_code)
    return ApiResponse(success=True, data=res)


@router.put("/{short_code}", response_model=ApiResponse[UrlResponse])
async def update_url(
    short_code: str,
    payload: UrlUpdate,
    current_user: Annotated[User, Depends(get_user_from_jwt_or_api_key)],
    url_service: Annotated[UrlService, Depends(get_url_service)],
) -> ApiResponse[UrlResponse]:
    """Update destination URL, title, expiration, or password protection with cache invalidation."""
    res = await url_service.update_url(short_code, payload, current_user)
    return ApiResponse(success=True, data=res)


@router.delete("/{short_code}", response_model=ApiResponse[dict])
async def delete_url(
    short_code: str,
    current_user: Annotated[User, Depends(get_user_from_jwt_or_api_key)],
    url_service: Annotated[UrlService, Depends(get_url_service)],
) -> ApiResponse[dict]:
    """Soft-delete shortened URL and evict from cache."""
    await url_service.delete_url(short_code, current_user)
    return ApiResponse(success=True, data={"message": "URL successfully deleted"})


@router.get("/{short_code}/qr")
async def get_url_qr_code(
    short_code: str,
    url_service: Annotated[UrlService, Depends(get_url_service)],
    box_size: Annotated[int, Query(ge=1, le=20)] = 10,
    border: Annotated[int, Query(ge=1, le=10)] = 4,
) -> Response:
    """Generate high-resolution PNG QR code pointing to the shortened link."""
    # Verify URL exists first
    await url_service.get_url_by_code(short_code)
    qr_bytes = url_service.generate_qr_code(short_code, box_size=box_size, border=border)
    return Response(content=qr_bytes, media_type="image/png")
