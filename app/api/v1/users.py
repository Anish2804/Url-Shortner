"""User identity and profile endpoints."""

from typing import Annotated
from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=ApiResponse[UserResponse])
async def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApiResponse[UserResponse]:
    """Get current authenticated user identity and role authorizations."""
    return ApiResponse(success=True, data=UserResponse.model_validate(current_user))
