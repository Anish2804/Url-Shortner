"""Custom branded domain endpoints."""

import uuid
from typing import Annotated, List
from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_current_user, get_domain_service
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.domain import DomainCreate, DomainResponse, DomainVerifyResponse
from app.services.domain_service import DomainService

router = APIRouter(prefix="/domains", tags=["Custom Domains"])


@router.post("/", response_model=ApiResponse[DomainResponse], status_code=status.HTTP_201_CREATED)
async def add_custom_domain(
    payload: DomainCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    domain_service: Annotated[DomainService, Depends(get_domain_service)],
) -> ApiResponse[DomainResponse]:
    """Register a custom branded domain for short links."""
    res = await domain_service.add_domain(current_user, payload)
    return ApiResponse(success=True, data=res)


@router.get("/", response_model=ApiResponse[List[DomainResponse]])
async def list_custom_domains(
    current_user: Annotated[User, Depends(get_current_user)],
    domain_service: Annotated[DomainService, Depends(get_domain_service)],
) -> ApiResponse[List[DomainResponse]]:
    """List custom domains registered by the authenticated user."""
    res = await domain_service.list_user_domains(current_user)
    return ApiResponse(success=True, data=res)


@router.post("/{domain_id}/verify", response_model=ApiResponse[DomainVerifyResponse])
async def verify_custom_domain(
    domain_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    domain_service: Annotated[DomainService, Depends(get_domain_service)],
) -> ApiResponse[DomainVerifyResponse]:
    """Verify domain ownership via DNS TXT record challenge."""
    res = await domain_service.verify_domain(domain_id, current_user)
    return ApiResponse(success=True, data=res)
