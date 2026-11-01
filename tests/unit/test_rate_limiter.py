"""Unit tests for sliding-window rate limiter (in-memory and Redis fallback)."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.cache.rate_limiter import SlidingWindowRateLimiter
from app.core.config import settings


@pytest.mark.asyncio
async def test_rate_limiter_disabled_bypass():
    limiter = SlidingWindowRateLimiter()
    with patch.object(settings, "REDIS_RATE_LIMIT_ENABLED", False):
        allowed, remaining, retry_after = await limiter.is_allowed("test_user", limit=5)
        assert allowed is True
        assert remaining == 5
        assert retry_after == 0


@pytest.mark.asyncio
async def test_rate_limiter_in_memory_sliding_window():
    limiter = SlidingWindowRateLimiter()
    with patch.object(settings, "REDIS_RATE_LIMIT_ENABLED", True):
        # Force client to None so in-memory fallback triggers
        with patch("app.cache.rate_limiter.redis_manager.get_client", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            
            # Make 3 allowed requests with limit=3
            for i in range(3):
                allowed, remaining, _ = await limiter.is_allowed("user_mem", limit=3, window_seconds=60)
                assert allowed is True
            
            # 4th request must be rejected
            allowed, remaining, retry_after = await limiter.is_allowed("user_mem", limit=3, window_seconds=60)
            assert allowed is False
            assert remaining == 0
            assert retry_after == 60


@pytest.mark.asyncio
async def test_rate_limiter_redis_mock_pipeline():
    limiter = SlidingWindowRateLimiter()
    mock_redis = MagicMock()
    mock_pipe = MagicMock()
    mock_pipe.zremrangebyscore = MagicMock()
    mock_pipe.zadd = MagicMock()
    mock_pipe.zcard = MagicMock()
    mock_pipe.expire = MagicMock()
    
    # execute returns results: [removed, added, count=2, expire]
    mock_pipe.execute = AsyncMock(return_value=[0, 1, 2, True])
    mock_redis.pipeline = MagicMock(return_value=mock_pipe)

    with patch.object(settings, "REDIS_RATE_LIMIT_ENABLED", True):
        with patch("app.cache.rate_limiter.redis_manager.get_client", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_redis
            
            allowed, remaining, retry = await limiter.is_allowed("user_redis", limit=5, window_seconds=60)
            assert allowed is True
            assert remaining == 3
            assert retry == 0

            # Test over limit: count=6
            mock_pipe.execute = AsyncMock(return_value=[0, 1, 6, True])
            allowed, remaining, retry = await limiter.is_allowed("user_redis", limit=5, window_seconds=60)
            assert allowed is False
            assert remaining == 0
            assert retry == 60
