"""Cache-aside service with stampede locking and null-sentinel penetration defense."""

import json
import secrets
import time
from typing import Any, Dict, Optional, Tuple
from app.cache.redis_client import redis_manager
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("cache_service")

# Lua script for atomic unlock only if lock value matches token
LUA_RELEASE_LOCK = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


class CacheService:
    """Service encapsulating Redis cache-aside operations for shortened links."""

    @staticmethod
    def _url_key(identifier: str) -> str:
        return f"url:map:{identifier.strip()}"

    @staticmethod
    def _null_key(identifier: str) -> str:
        return f"url:null:{identifier.strip()}"

    @staticmethod
    def _lock_key(identifier: str) -> str:
        return f"url:lock:{identifier.strip()}"

    async def get_url(self, identifier: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Fetch URL mapping from cache.
        
        Returns:
            (is_hit, payload_or_none)
            - If null sentinel is hit, returns (True, None) indicating known non-existent link.
            - If cache miss or Redis down, returns (False, None).
            - If valid cached payload found, returns (True, payload).
        """
        client = await redis_manager.get_client()
        if not client:
            redis_manager.record_fallback()
            return False, None

        start = time.perf_counter()
        try:
            # Check penetration sentinel first
            null_key = self._null_key(identifier)
            is_null = await client.get(null_key)
            if is_null:
                redis_manager.record_hit()
                redis_manager.record_op((time.perf_counter() - start) * 1000)
                return True, None

            # Check cached URL payload
            raw = await client.get(self._url_key(identifier))
            redis_manager.record_op((time.perf_counter() - start) * 1000)
            if raw:
                redis_manager.record_hit()
                data = json.loads(raw)
                return True, data

            redis_manager.record_miss()
            return False, None
        except Exception as e:
            logger.warning("Redis read error for %s: %s", identifier, str(e))
            redis_manager.record_fallback()
            return False, None

    async def set_url(
        self,
        identifier: str,
        data: Dict[str, Any],
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Cache shortened URL destination and metadata."""
        client = await redis_manager.get_client()
        if not client:
            return

        ttl = ttl_seconds or settings.REDIS_URL_CACHE_TTL_SECONDS
        start = time.perf_counter()
        try:
            payload = json.dumps(data)
            await client.set(self._url_key(identifier), payload, ex=ttl)
            # Remove any null sentinel if URL was just created or restored
            await client.delete(self._null_key(identifier))
            redis_manager.record_op((time.perf_counter() - start) * 1000)
        except Exception as e:
            logger.warning("Redis write error for %s: %s", identifier, str(e))

    async def set_null(self, identifier: str) -> None:
        """Cache null sentinel to protect database against cache penetration attacks."""
        client = await redis_manager.get_client()
        if not client:
            return

        start = time.perf_counter()
        try:
            await client.set(
                self._null_key(identifier),
                "1",
                ex=settings.REDIS_CACHE_NULL_TTL_SECONDS,
            )
            redis_manager.record_op((time.perf_counter() - start) * 1000)
        except Exception as e:
            logger.warning("Redis null-sentinel write error for %s: %s", identifier, str(e))

    async def invalidate(self, short_code: str, custom_alias: Optional[str] = None) -> None:
        """Invalidate cache entries when destination or status changes."""
        client = await redis_manager.get_client()
        if not client:
            return

        keys = [self._url_key(short_code), self._null_key(short_code)]
        if custom_alias:
            keys.extend([self._url_key(custom_alias), self._null_key(custom_alias)])

        try:
            await client.delete(*keys)
        except Exception as e:
            logger.warning("Redis invalidate error for %s: %s", short_code, str(e))

    async def acquire_lock(self, identifier: str, timeout_seconds: int = 5) -> Optional[str]:
        """Acquire distributed lock to prevent cache stampedes on hot cache misses."""
        client = await redis_manager.get_client()
        if not client:
            return None

        token = secrets.token_hex(16)
        try:
            acquired = await client.set(self._lock_key(identifier), token, nx=True, ex=timeout_seconds)
            return token if acquired else None
        except Exception:
            return None

    async def release_lock(self, identifier: str, token: str) -> None:
        """Release distributed lock safely via atomic Lua script."""
        client = await redis_manager.get_client()
        if not client:
            return

        try:
            await client.eval(LUA_RELEASE_LOCK, 1, self._lock_key(identifier), token)
        except Exception:
            pass


cache_service = CacheService()
