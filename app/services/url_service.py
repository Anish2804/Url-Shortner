"""Core URL Shortening Engine: Base62 generation, SSRF mitigation, normalization, and QR codes."""

import io
import ipaddress
import secrets
import socket
import urllib.parse
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple
import qrcode
from qrcode.image.pil import PilImage

from app.cache.cache_service import cache_service
from app.core.config import settings
from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    MaliciousDomainException,
    NotFoundException,
    SSRFBlockedException,
)
from app.core.logging import get_logger
from app.core.security import ensure_utc, hash_password
from app.models.url import Url
from app.models.user import User
from app.repositories.abuse_repo import AbuseRepository
from app.repositories.url_repo import UrlRepository
from app.schemas.url import (
    UrlBulkCreate,
    UrlBulkResponse,
    UrlCreate,
    UrlFilterParams,
    UrlResponse,
    UrlUpdate,
)

logger = get_logger("url_service")

# Base62 character set
BASE62_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE62_BASE = len(BASE62_ALPHABET)


def encode_base62(num: int) -> str:
    """Encode an integer into Base62 string."""
    if num == 0:
        return BASE62_ALPHABET[0]
    chars = []
    while num > 0:
        num, rem = divmod(num, BASE62_BASE)
        chars.append(BASE62_ALPHABET[rem])
    chars.reverse()
    return "".join(chars)


def generate_collision_resistant_short_code(length: int = 7) -> str:
    """Generate high-entropy, unpredictable Base62 short code.
    
    Generates cryptographically strong random bits to avoid exposing
    sequential predictable database primary keys to end users.
    7 chars of Base62 provides 62^7 = ~3.52 trillion combinations.
    """
    max_val = BASE62_BASE ** length
    random_int = secrets.randbelow(max_val)
    code = encode_base62(random_int)
    # Pad to fixed length if necessary
    return code.zfill(length)


class UrlService:
    """Service for URL validation, shortening, life-cycle control, and QR generation."""

    def __init__(self, url_repo: UrlRepository, abuse_repo: AbuseRepository):
        self.url_repo = url_repo
        self.abuse_repo = abuse_repo

    def validate_and_normalize_url(self, raw_url: str) -> str:
        """Validate destination URL against protocol, SSRF, and malformed inputs."""
        clean = raw_url.strip()
        if len(clean) > settings.MAX_URL_LENGTH:
            raise BadRequestException(f"URL length exceeds maximum allowed limit of {settings.MAX_URL_LENGTH} characters")

        try:
            parsed = urllib.parse.urlsplit(clean)
        except Exception:
            raise BadRequestException("Malformed destination URL")

        scheme = (parsed.scheme or "").lower()
        if scheme not in settings.ALLOWED_URL_SCHEMES:
            raise BadRequestException(
                f"URL scheme '{scheme}' is forbidden. Only {settings.ALLOWED_URL_SCHEMES} are permitted."
            )

        hostname = parsed.hostname
        if not hostname:
            raise BadRequestException("Destination URL must contain a valid hostname")

        # SSRF Mitigation: Block private, link-local, loopback, and cloud metadata IPs
        if not settings.ALLOW_PRIVATE_IPS:
            self._validate_destination_ip(hostname)

        # Normalize URL: lowercase scheme and host, remove default ports
        netloc = hostname
        if parsed.port and not (
            (scheme == "http" and parsed.port == 80) or (scheme == "https" and parsed.port == 443)
        ):
            netloc = f"{netloc}:{parsed.port}"

        path = parsed.path
        normalized = urllib.parse.urlunsplit((scheme, netloc, path, parsed.query, parsed.fragment))
        return normalized

    def _validate_destination_ip(self, hostname: str) -> None:
        """Resolve destination host and block private, loopback, or internal networks."""
        def is_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
            return (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_multicast
            )

        # Check direct IP literals first
        try:
            ip_obj = ipaddress.ip_address(hostname)
            if is_blocked(ip_obj):
                raise SSRFBlockedException("Direct access to private or local IP addresses is prohibited")
        except ValueError:
            # It's a hostname, resolve via DNS
            try:
                addr_info = socket.getaddrinfo(hostname, None)
                for item in addr_info:
                    sockaddr = item[4]
                    ip_str = sockaddr[0]
                    ip_obj = ipaddress.ip_address(ip_str)
                    if is_blocked(ip_obj):
                        raise SSRFBlockedException(
                            f"Hostname '{hostname}' resolves to a restricted private or internal IP ({ip_str})"
                        )
            except socket.gaierror:
                # DNS failure: Allow domain to be shortened (it may resolve in client browser)
                pass

    async def create_url(self, payload: UrlCreate, user: Optional[User] = None) -> UrlResponse:
        """Create a shortened URL with collision avoidance."""
        normalized_url = self.validate_and_normalize_url(payload.original_url)

        # Extract domain for blocklist check
        domain = urllib.parse.urlsplit(normalized_url).hostname or ""
        if await self.abuse_repo.is_domain_blocked(domain):
            raise MaliciousDomainException(f"Destination domain '{domain}' is blocked by security policy")

        # Handle custom alias or generate collision-resistant code
        if payload.custom_alias:
            alias = payload.custom_alias.strip()
            if await self.url_repo.exists_code_or_alias(alias):
                raise ConflictException(f"The custom alias '{alias}' is already in use")
            short_code = alias
            custom_alias = alias
        else:
            custom_alias = None
            # Collision retry loop (typically succeeds on first try with 3.5T space)
            short_code = ""
            for _ in range(5):
                candidate = generate_collision_resistant_short_code()
                if not await self.url_repo.exists_code_or_alias(candidate):
                    short_code = candidate
                    break
            if not short_code:
                # Fallback to UUID-derived code
                short_code = encode_base62(uuid.uuid4().int)[:8]

        # Password hashing if link is password-protected
        password_hash = hash_password(payload.password) if payload.password else None

        url_entity = Url(
            user_id=user.id if user else None,
            original_url=normalized_url,
            short_code=short_code,
            custom_alias=custom_alias,
            title=payload.title,
            redirect_http_code=payload.redirect_http_code,
            expires_at=payload.expires_at,
            password_hash=password_hash,
            is_one_time=payload.is_one_time,
        )

        saved = await self.url_repo.create(url_entity)
        return self._to_response(saved)

    async def create_bulk_urls(self, bulk_payload: UrlBulkCreate, user: User) -> UrlBulkResponse:
        """Batch create up to 100 shortened URLs."""
        created_responses: List[UrlResponse] = []
        failed_items: List[dict] = []

        for idx, item in enumerate(bulk_payload.items):
            try:
                res = await self.create_url(item, user)
                created_responses.append(res)
            except Exception as e:
                failed_items.append({"index": idx, "original_url": item.original_url, "error": str(e)})

        return UrlBulkResponse(
            created=created_responses,
            failed=failed_items,
            total_requested=len(bulk_payload.items),
            total_successful=len(created_responses),
        )

    async def get_url_by_code(self, short_code: str) -> UrlResponse:
        """Retrieve URL metadata by short code or alias."""
        url = await self.url_repo.get_by_short_code(short_code)
        if not url:
            url = await self.url_repo.get_by_alias(short_code)
        if not url:
            raise NotFoundException("Shortened URL not found")
        return self._to_response(url)

    async def update_url(self, short_code: str, payload: UrlUpdate, user: User) -> UrlResponse:
        """Update existing URL destination, status, or credentials with cache invalidation."""
        url = await self.url_repo.get_by_short_code(short_code)
        if not url:
            url = await self.url_repo.get_by_alias(short_code)
        if not url:
            raise NotFoundException("Shortened URL not found")

        # Authorization check: only owner or superuser can edit
        if url.user_id != user.id and not user.is_superuser:
            raise BadRequestException("You do not have permission to modify this URL")

        if payload.original_url:
            norm = self.validate_and_normalize_url(payload.original_url)
            domain = urllib.parse.urlsplit(norm).hostname or ""
            if await self.abuse_repo.is_domain_blocked(domain):
                raise MaliciousDomainException("Destination domain is blocked")
            url.original_url = norm

        if payload.title is not None:
            url.title = payload.title
        if payload.redirect_http_code is not None:
            url.redirect_http_code = payload.redirect_http_code
        if payload.is_active is not None:
            url.is_active = payload.is_active
        if payload.expires_at is not None:
            url.expires_at = payload.expires_at

        if payload.remove_password:
            url.password_hash = None
        elif payload.password:
            url.password_hash = hash_password(payload.password)

        updated = await self.url_repo.update(url)

        # Invalidate cache
        await cache_service.invalidate(url.short_code, url.custom_alias)
        return self._to_response(updated)

    async def delete_url(self, short_code: str, user: User) -> None:
        """Soft delete URL and invalidate cache."""
        url = await self.url_repo.get_by_short_code(short_code)
        if not url:
            url = await self.url_repo.get_by_alias(short_code)
        if not url:
            raise NotFoundException("Shortened URL not found")

        if url.user_id != user.id and not user.is_superuser:
            raise BadRequestException("You do not have permission to delete this URL")

        await self.url_repo.soft_delete(url)
        await cache_service.invalidate(url.short_code, url.custom_alias)

    async def list_user_urls(
        self,
        user: User,
        filters: UrlFilterParams,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[UrlResponse], int]:
        """List and filter URLs belonging to the user."""
        items, total = await self.url_repo.list_user_urls(
            user_id=user.id,
            search=filters.search,
            is_active=filters.is_active,
            is_expired=filters.is_expired,
            sort_by=filters.sort_by,
            sort_order=filters.sort_order,
            skip=skip,
            limit=limit,
        )
        responses = [self._to_response(u) for u in items]
        return responses, total

    def generate_qr_code(self, short_code: str, box_size: int = 10, border: int = 4) -> bytes:
        """Generate high-resolution PNG QR code pointing to the shortened link."""
        full_url = f"{settings.BASE_URL.rstrip('/')}/{short_code}"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=max(1, min(box_size, 20)),
            border=max(1, min(border, 10)),
        )
        qr.add_data(full_url)
        qr.make(fit=True)
        img: PilImage = qr.make_image(fill_color="black", back_color="white")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def _to_response(self, url: Url) -> UrlResponse:
        """Map ORM entity to API response model with computed fields."""
        now = datetime.now(timezone.utc)
        is_expired = False
        if url.expires_at:
            is_expired = ensure_utc(url.expires_at) <= now

        code = url.custom_alias or url.short_code
        full_short_url = f"{settings.BASE_URL.rstrip('/')}/{code}"

        return UrlResponse(
            id=url.id,
            short_code=url.short_code,
            original_url=url.original_url,
            short_url=full_short_url,
            custom_alias=url.custom_alias,
            title=url.title,
            redirect_http_code=url.redirect_http_code,
            is_active=url.is_active,
            is_expired=is_expired,
            is_password_protected=bool(url.password_hash),
            is_one_time=url.is_one_time,
            is_consumed=url.is_consumed,
            click_count=url.click_count,
            expires_at=url.expires_at,
            created_at=url.created_at,
            updated_at=url.updated_at,
        )
