"""Integration tests for Redis cache-aside resilience and database fallback."""

import pytest
from app.cache.cache_service import CacheService
from app.cache.redis_client import RedisManager


@pytest.mark.asyncio
async def test_cache_service_fallback_when_redis_offline():
    """Verify that when Redis is disconnected, cache operations fall back gracefully without raising exceptions."""
    offline_manager = RedisManager()
    # Explicitly do NOT initialize or connect
    assert offline_manager.is_available is False

    cache = CacheService()

    # get_url should return (False, None) and record fallback
    is_hit, payload = await cache.get_url("non_existent_code")
    assert is_hit is False
    assert payload is None

    # set_url should safely do nothing without raising exceptions
    await cache.set_url("some_code", {"original_url": "https://example.com"})

    # set_null should safely do nothing
    await cache.set_null("some_code")

    # invalidate should safely do nothing
    await cache.invalidate("some_code")

    # acquire_lock should return None safely
    lock = await cache.acquire_lock("some_code")
    assert lock is None
