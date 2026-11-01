"""API v1 master router aggregating all sub-routers."""

from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.api_keys import router as api_keys_router
from app.api.v1.auth import router as auth_router
from app.api.v1.domains import router as domains_router
from app.api.v1.urls import router as urls_router
from app.api.v1.users import router as users_router

v1_router = APIRouter()

v1_router.include_router(auth_router)
v1_router.include_router(users_router)
v1_router.include_router(urls_router)
v1_router.include_router(analytics_router)
v1_router.include_router(api_keys_router)
v1_router.include_router(admin_router)
v1_router.include_router(domains_router)
