"""High-speed URL redirect endpoint with cache-aside and asynchronous Kafka streaming."""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import RedirectResponse

from app.api.dependencies import get_redirect_service
from app.monitoring.prometheus import redirects_total
from app.services.redirect_service import RedirectService

router = APIRouter(tags=["Redirection"])


@router.get(
    "/{short_code}",
    response_class=RedirectResponse,
    summary="Redirect short URL to original destination",
    description="High-performance redirect backed by Redis cache and asynchronous Kafka click event dispatch.",
)
async def redirect_to_destination(
    short_code: str,
    request: Request,
    redirect_service: Annotated[RedirectService, Depends(get_redirect_service)],
    user_agent: Annotated[Optional[str], Header()] = None,
    referer: Annotated[Optional[str], Header()] = None,
    pwd: Annotated[Optional[str], Query(description="Password if link is protected")] = None,
    x_link_password: Annotated[Optional[str], Header()] = None,
) -> RedirectResponse:
    """Resolve short code to original destination and emit click analytics asynchronously."""
    # Extract client IP
    forwarded = request.headers.get("X-Forwarded-For")
    client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else None)

    password = pwd or x_link_password

    destination_url, status_code = await redirect_service.resolve_redirect(
        code_or_alias=short_code,
        client_ip=client_ip,
        user_agent_str=user_agent,
        referrer_str=referer,
        provided_password=password,
    )

    redirects_total.labels(status_code=str(status_code)).inc()

    # Issue standard 301 or 302 HTTP redirect
    return RedirectResponse(url=destination_url, status_code=status_code)
