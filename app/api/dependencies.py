"""FastAPI dependency injection providers for database, security, and services."""

import uuid
from typing import Annotated, Optional
from fastapi import Depends, Header, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_access_token
from app.database.session import get_db
from app.models.api_key import ApiKey
from app.models.user import User
from app.repositories.abuse_repo import AbuseRepository
from app.repositories.analytics_repo import AnalyticsRepository
from app.repositories.api_key_repo import ApiKeyRepository
from app.repositories.domain_repo import DomainRepository
from app.repositories.url_repo import UrlRepository
from app.repositories.user_repo import UserRepository
from app.services.admin_service import AdminService
from app.services.analytics_service import AnalyticsService
from app.services.api_key_service import ApiKeyService
from app.services.auth_service import AuthService
from app.services.domain_service import DomainService
from app.services.redirect_service import RedirectService
from app.services.url_service import UrlService

# Bearer security scheme
security_bearer = HTTPBearer(auto_error=False)


# ------------------------------------------------------------------------------
# Repository Dependencies
# ------------------------------------------------------------------------------
def get_user_repo(session: Annotated[AsyncSession, Depends(get_db)]) -> UserRepository:
    return UserRepository(session)


def get_url_repo(session: Annotated[AsyncSession, Depends(get_db)]) -> UrlRepository:
    return UrlRepository(session)


def get_api_key_repo(session: Annotated[AsyncSession, Depends(get_db)]) -> ApiKeyRepository:
    return ApiKeyRepository(session)


def get_analytics_repo(session: Annotated[AsyncSession, Depends(get_db)]) -> AnalyticsRepository:
    return AnalyticsRepository(session)


def get_abuse_repo(session: Annotated[AsyncSession, Depends(get_db)]) -> AbuseRepository:
    return AbuseRepository(session)


def get_domain_repo(session: Annotated[AsyncSession, Depends(get_db)]) -> DomainRepository:
    return DomainRepository(session)


# ------------------------------------------------------------------------------
# Service Dependencies
# ------------------------------------------------------------------------------
def get_auth_service(user_repo: Annotated[UserRepository, Depends(get_user_repo)]) -> AuthService:
    return AuthService(user_repo)


def get_url_service(
    url_repo: Annotated[UrlRepository, Depends(get_url_repo)],
    abuse_repo: Annotated[AbuseRepository, Depends(get_abuse_repo)],
) -> UrlService:
    return UrlService(url_repo, abuse_repo)


def get_redirect_service(url_repo: Annotated[UrlRepository, Depends(get_url_repo)]) -> RedirectService:
    return RedirectService(url_repo)


def get_analytics_service(
    analytics_repo: Annotated[AnalyticsRepository, Depends(get_analytics_repo)],
    url_repo: Annotated[UrlRepository, Depends(get_url_repo)],
) -> AnalyticsService:
    return AnalyticsService(analytics_repo, url_repo)


def get_api_key_service(api_key_repo: Annotated[ApiKeyRepository, Depends(get_api_key_repo)]) -> ApiKeyService:
    return ApiKeyService(api_key_repo)


def get_admin_service(abuse_repo: Annotated[AbuseRepository, Depends(get_abuse_repo)]) -> AdminService:
    return AdminService(abuse_repo)


def get_domain_service(domain_repo: Annotated[DomainRepository, Depends(get_domain_repo)]) -> DomainService:
    return DomainService(domain_repo)


# ------------------------------------------------------------------------------
# Authentication & Authorization Dependencies
# ------------------------------------------------------------------------------
async def get_current_user(
    auth: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security_bearer)],
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> User:
    """Validate Bearer JWT access token and return authenticated User entity."""
    if not auth or not auth.credentials:
        raise UnauthorizedException("Authentication credentials were not provided")

    payload = decode_access_token(auth.credentials)
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedException("Invalid token subject")

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise UnauthorizedException("Invalid user ID in token")

    user = await user_repo.get_by_id(user_uuid)
    if not user:
        raise UnauthorizedException("User account not found")

    if not user.is_active:
        raise ForbiddenException("Account is inactive")

    return user


async def get_current_active_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Verify that current user possesses administrator privileges."""
    is_admin = current_user.is_superuser or any(r.name == "admin" for r in current_user.roles)
    if not is_admin:
        raise ForbiddenException("Administrator privileges required for this action")
    return current_user


async def get_user_from_jwt_or_api_key(
    request: Request,
    auth: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security_bearer)],
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    api_key_service: Annotated[ApiKeyService, Depends(get_api_key_service)],
    x_api_key: Annotated[Optional[str], Header()] = None,
) -> User:
    """Dual-mode authentication supporting either User Bearer JWT or machine API Key."""
    # Check X-API-Key header first
    if x_api_key:
        user, _ = await api_key_service.verify_key(x_api_key)
        return user

    # Otherwise authenticate via JWT Bearer token
    if auth and auth.credentials:
        return await get_current_user(auth, user_repo)

    raise UnauthorizedException("Authentication required via Bearer JWT or X-API-Key header")
