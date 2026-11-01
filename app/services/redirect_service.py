"""High-performance URL redirect service with cache-aside and asynchronous Kafka streaming."""

import hashlib
import hmac
import ipaddress
import urllib.parse
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from user_agents import parse as parse_user_agent

from app.cache.cache_service import cache_service
from app.core.config import settings
from app.core.exceptions import (
    InvalidLinkPasswordException,
    LinkAlreadyConsumedException,
    LinkExpiredException,
    LinkInactiveException,
    LinkPasswordRequiredException,
    NotFoundException,
)
from app.core.logging import get_logger
from app.core.security import ensure_utc, verify_password
from app.events.producer import kafka_producer
from app.events.schema import ClickEventMessage
from app.repositories.url_repo import UrlRepository

logger = get_logger("redirect_service")


def anonymize_ip(ip_str: Optional[str]) -> Optional[str]:
    """Mask client IP address to ensure GDPR/privacy compliance.
    
    Zeroes out last octet for IPv4 (e.g., 198.51.100.0) or last 80 bits for IPv6.
    """
    if not ip_str:
        return None
    try:
        ip = ipaddress.ip_address(ip_str.strip())
        if ip.version == 4:
            network = ipaddress.IPv4Network(f"{ip_str}/24", strict=False)
            return str(network.network_address)
        else:
            network = ipaddress.IPv6Network(f"{ip_str}/48", strict=False)
            return str(network.network_address)
    except ValueError:
        return None


def hash_ip(ip_str: Optional[str]) -> str:
    """Generate salted HMAC-SHA256 hash of client IP for unique visitor calculation."""
    raw = (ip_str or "unknown").strip()
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()


class RedirectService:
    """Service executing high-speed redirects with cache-aside and non-blocking analytics."""

    def __init__(self, url_repo: UrlRepository):
        self.url_repo = url_repo

    async def resolve_redirect(
        self,
        code_or_alias: str,
        client_ip: Optional[str] = None,
        user_agent_str: Optional[str] = None,
        referrer_str: Optional[str] = None,
        provided_password: Optional[str] = None,
    ) -> Tuple[str, int]:
        """Resolve short link to destination URL with cache-aside and async click publishing.
        
        Returns:
            (destination_url, http_redirect_code)
        """
        # Step 1: Check Redis Cache
        is_hit, cached_data = await cache_service.get_url(code_or_alias)

        url_record: Dict[str, Any]
        if is_hit:
            if cached_data is None:
                # Null sentinel hit (defends against cache penetration for unknown URLs)
                raise NotFoundException("Shortened URL not found")
            url_record = cached_data
        else:
            # Step 2: Database Fallback on Cache Miss
            url = await self.url_repo.get_active_by_code_or_alias(code_or_alias)
            if not url:
                # Populate null sentinel with short TTL
                await cache_service.set_null(code_or_alias)
                raise NotFoundException("Shortened URL not found")

            # Check expiration
            now = datetime.now(timezone.utc)
            if url.expires_at and ensure_utc(url.expires_at) <= now:
                raise LinkExpiredException()

            if url.is_one_time and url.is_consumed:
                raise LinkAlreadyConsumedException()

            if not url.is_active or url.is_deleted:
                raise LinkInactiveException()

            # Prepare cache payload
            url_record = {
                "id": str(url.id),
                "original_url": url.original_url,
                "short_code": url.short_code,
                "custom_alias": url.custom_alias,
                "redirect_http_code": url.redirect_http_code,
                "expires_at": url.expires_at.isoformat() if url.expires_at else None,
                "password_hash": url.password_hash,
                "is_one_time": url.is_one_time,
                "is_active": url.is_active,
            }

            # Only cache in Redis if NOT a one-time link (one-time links must hit DB for atomic consumption)
            if not url.is_one_time:
                await cache_service.set_url(code_or_alias, url_record)

        # Step 3: Validate Link Constraints (Expiration, Passwords, One-Time)
        now_dt = datetime.now(timezone.utc)
        if url_record.get("expires_at"):
            exp = datetime.fromisoformat(url_record["expires_at"])
            if exp <= now_dt:
                raise LinkExpiredException()

        # Password Protection Verification
        password_hash = url_record.get("password_hash")
        if password_hash:
            if not provided_password:
                raise LinkPasswordRequiredException()
            if not verify_password(provided_password, password_hash):
                raise InvalidLinkPasswordException()

        # One-Time Link Atomic Consumption
        if url_record.get("is_one_time"):
            url_uuid = uuid.UUID(url_record["id"])
            consumed = await self.url_repo.atomic_consume_one_time_link(url_uuid)
            if not consumed:
                # Invalidate cache just in case
                await cache_service.invalidate(url_record["short_code"], url_record.get("custom_alias"))
                raise LinkAlreadyConsumedException()
            # Invalidate any cache mapping
            await cache_service.invalidate(url_record["short_code"], url_record.get("custom_alias"))

        # Step 4: Non-Blocking Kafka Click Event Dispatch
        self._dispatch_click_event(url_record, client_ip, user_agent_str, referrer_str)

        destination_url = url_record["original_url"]
        http_code = url_record.get("redirect_http_code", 302)
        return destination_url, http_code

    def _dispatch_click_event(
        self,
        url_record: Dict[str, Any],
        client_ip: Optional[str],
        user_agent_str: Optional[str],
        referrer_str: Optional[str],
    ) -> None:
        """Parse client context and enqueue event to Kafka in background."""
        ip_h = hash_ip(client_ip)
        anon_ip = anonymize_ip(client_ip)

        # Parse user agent
        ua = parse_user_agent(user_agent_str or "")
        device_type = "mobile" if ua.is_mobile else "tablet" if ua.is_tablet else "bot" if ua.is_bot else "desktop"
        browser_name = ua.browser.family or "Other"
        os_name = ua.os.family or "Other"
        is_bot = ua.is_bot

        # Parse referrer domain
        referrer_domain = None
        if referrer_str:
            try:
                referrer_domain = urllib.parse.urlsplit(referrer_str).hostname
            except Exception:
                referrer_domain = None

        # GeoIP resolution
        from app.services.geoip_service import geoip_service
        country_code, city = geoip_service.resolve(client_ip)

        click_message = ClickEventMessage(
            url_id=url_record["id"],
            short_code=url_record["short_code"],
            ip_hash=ip_h,
            anonymized_ip=anon_ip,
            user_agent=user_agent_str[:512] if user_agent_str else None,
            device_type=device_type,
            browser=browser_name,
            os=os_name,
            country_code=country_code,
            city=city,
            referrer=referrer_str[:512] if referrer_str else None,
            referrer_domain=referrer_domain,
            is_bot=is_bot,
        )

        # Enqueue into Kafka producer buffer (non-blocking, < 0.2ms)
        kafka_producer.enqueue_click_event(click_message)
