"""API key management endpoints for machine credentials."""

import uuid
from typing import Annotated, List
from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_api_key_service, get_current_user
from app.models.user import User
from app.schemas.api_key import (
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeyResponse,
)
from app.schemas.common import ApiResponse
from app.services.api_key_service import ApiKeyService

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


@router.post("/", response_model=ApiResponse[ApiKeyCreatedResponse], status_code=status.HTTP_201_CREATED)
async def create_api_key(
    payload: ApiKeyCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    api_key_service: Annotated[ApiKeyService, Depends(get_api_key_service)],
) -> ApiResponse[ApiKeyCreatedResponse]:
    """Generate a new scoped API key. Note: The raw key secret is returned only once."""
    res = await api_key_service.create_key(current_user, payload)
    return ApiResponse(success=True, data=res)


@router.get("/", response_model=ApiResponse[List[ApiKeyResponse]])
async def list_api_keys(
    current_user: Annotated[User, Depends(get_current_user)],
    api_key_service: Annotated[ApiKeyService, Depends(get_api_key_service)],
) -> ApiResponse[List[ApiKeyResponse]]:
    """List all API keys belonging to the authenticated user."""
    keys = await api_key_service.list_keys(current_user)
    return ApiResponse(success=True, data=keys)


@router.delete("/{key_id}", response_model=ApiResponse[dict])
async def revoke_api_key(
    key_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    api_key_service: Annotated[ApiKeyService, Depends(get_api_key_service)],
) -> ApiResponse[dict]:
    """Revoke an API key immediately."""
    await api_key_service.revoke_key(key_id, current_user)
    return ApiResponse(success=True, data={"message": "API key revoked successfully"})
