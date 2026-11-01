"""Unit tests for CacheService covering cache-aside, stampede locking, and null sentinels."""

import json
import pytest
from unittest.mock import AsyncMock, patch
from app.cache.cache_service import CacheService, LUA_RELEASE_LOCK


@pytest.mark.asyncio
async def test_cache_service_get_url_miss_and_hit():
    service = CacheService()
    mock_redis = AsyncMock()

    # 1. Cache Miss (both null and url key return None)
    mock_redis.get.return_value = None
    with patch("app.cache.cache_service.redis_manager.get_client", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_redis
        is_hit, payload = await service.get_url("abc1234")
        assert is_hit is False
        assert payload is None

    # 2. Null Sentinel Hit (null key returns "1")
    mock_redis.get.side_effect = lambda k: "1" if "url:null:" in k else None
    with patch("app.cache.cache_service.redis_manager.get_client", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_redis
        is_hit, payload = await service.get_url("abc1234")
        assert is_hit is True
        assert payload is None

    # 3. Cache Hit (url key returns JSON string)
    expected_data = {"id": "1", "original_url": "https://example.com/target", "is_active": True}
    mock_redis.get.side_effect = lambda k: json.dumps(expected_data) if "url:map:" in k else None
    with patch("app.cache.cache_service.redis_manager.get_client", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_redis
        is_hit, payload = await service.get_url("abc1234")
        assert is_hit is True
        assert payload == expected_data


@pytest.mark.asyncio
async def test_cache_service_set_url_and_null():
    service = CacheService()
    mock_redis = AsyncMock()

    with patch("app.cache.cache_service.redis_manager.get_client", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_redis
        # set_url should set key and delete null key
        await service.set_url("abc1234", {"test": 123}, ttl_seconds=300)
        mock_redis.set.assert_called_once()
        mock_redis.delete.assert_called_once_with(service._null_key("abc1234"))

        # set_null should set null key
        mock_redis.reset_mock()
        await service.set_null("abc1234")
        mock_redis.set.assert_called_once()


@pytest.mark.asyncio
async def test_cache_service_invalidate():
    service = CacheService()
    mock_redis = AsyncMock()

    with patch("app.cache.cache_service.redis_manager.get_client", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_redis
        # Invalidate with custom alias deletes 4 keys
        await service.invalidate("short123", custom_alias="alias123")
        mock_redis.delete.assert_called_once()
        args, _ = mock_redis.delete.call_args
        assert len(args) == 4


@pytest.mark.asyncio
async def test_cache_service_distributed_lock_lifecycle():
    service = CacheService()
    mock_redis = AsyncMock()

    with patch("app.cache.cache_service.redis_manager.get_client", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_redis
        # Successfully acquire lock
        mock_redis.set.return_value = True
        token = await service.acquire_lock("hot_link", timeout_seconds=5)
        assert token is not None

        # Release lock with Lua script
        await service.release_lock("hot_link", token)
        mock_redis.eval.assert_called_once_with(
            LUA_RELEASE_LOCK,
            1,
            service._lock_key("hot_link"),
            token,
        )
