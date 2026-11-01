"""Authentication and token management endpoints."""

from typing import Annotated
from fastapi import APIRouter, Depends, Header, Request, status

from app.api.dependencies import get_auth_service, get_current_user
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
)
from app.schemas.common import ApiResponse
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=ApiResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: UserRegister,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiResponse[UserResponse]:
    """Register a new user account with Argon2id password hashing."""
    user = await auth_service.register(payload)
    return ApiResponse(success=True, data=user)


@router.post("/login", response_model=ApiResponse[TokenResponse])
async def login_user(
    request: Request,
    payload: UserLogin,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    user_agent: Annotated[str | None, Header()] = None,
) -> ApiResponse[TokenResponse]:
    """Authenticate with credentials and obtain JWT access and refresh token pair."""
    client_ip = request.client.host if request.client else None
    tokens = await auth_service.login(payload, user_agent=user_agent, ip_address=client_ip)
    return ApiResponse(success=True, data=tokens)


@router.post("/refresh", response_model=ApiResponse[TokenResponse])
async def refresh_token(
    request: Request,
    payload: RefreshTokenRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    user_agent: Annotated[str | None, Header()] = None,
) -> ApiResponse[TokenResponse]:
    """Rotate cryptographic refresh token with automatic token-reuse detection."""
    client_ip = request.client.host if request.client else None
    tokens = await auth_service.refresh_tokens(payload.refresh_token, user_agent=user_agent, ip_address=client_ip)
    return ApiResponse(success=True, data=tokens)


@router.post("/logout", response_model=ApiResponse[dict])
async def logout_user(
    payload: RefreshTokenRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiResponse[dict]:
    """Revoke refresh token and invalidate session."""
    await auth_service.logout(payload.refresh_token)
    return ApiResponse(success=True, data={"message": "Logged out successfully"})


@router.post("/change-password", response_model=ApiResponse[dict])
async def change_password(
    payload: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiResponse[dict]:
    """Change user password and revoke all other existing refresh tokens."""
    await auth_service.change_password(current_user, payload)
    return ApiResponse(success=True, data={"message": "Password changed successfully"})
