"""Distributed sliding-window rate limiter with in-memory fallback."""

import time
from collections import defaultdict
from typing import Dict, List, Tuple
from app.cache.redis_client import redis_manager
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("rate_limiter")


class SlidingWindowRateLimiter:
    """Sliding-window rate limiter backed by Redis with in-memory fallback."""

    def __init__(self):
        # In-memory fallback storage: dict of key -> list of float timestamps
        self._memory_buckets: Dict[str, List[float]] = defaultdict(list)

    async def is_allowed(
        self,
        identifier: str,
        limit: int,
        window_seconds: int = 60,
    ) -> Tuple[bool, int, int]:
        """Check if request is within sliding window limit.
        
        Returns:
            (allowed: bool, remaining: int, retry_after: int)
        """
        if not settings.REDIS_RATE_LIMIT_ENABLED:
            return True, limit, 0

        client = await redis_manager.get_client()
        now = time.time()
        window_start = now - window_seconds
        key = f"ratelimit:{identifier}"

        if client:
            try:
                pipe = client.pipeline()
                # 1. Remove timestamps outside the sliding window
                pipe.zremrangebyscore(key, 0, window_start)
                # 2. Add current timestamp with unique member
                member = f"{now}:{time.perf_counter()}"
                pipe.zadd(key, {member: now})
                # 3. Count requests in window
                pipe.zcard(key)
                # 4. Set TTL on key
                pipe.expire(key, window_seconds + 5)
                
                results = await pipe.execute()
                current_count = results[2]

                remaining = max(0, limit - current_count)
                if current_count > limit:
                    # Over limit
                    return False, 0, int(window_seconds)

                return True, remaining, 0
            except Exception as e:
                logger.warning("Redis rate limit error, using in-memory fallback: %s", str(e))
                # Fall through to in-memory fallback

        # In-memory sliding window fallback
        timestamps = self._memory_buckets[identifier]
        # Prune old timestamps
        self._memory_buckets[identifier] = [ts for ts in timestamps if ts > window_start]
        self._memory_buckets[identifier].append(now)

        current_count = len(self._memory_buckets[identifier])
        remaining = max(0, limit - current_count)
        if current_count > limit:
            return False, 0, int(window_seconds)

        return True, remaining, 0


rate_limiter = SlidingWindowRateLimiter()
