"""Asynchronous Redis client with connection pooling, metrics, and graceful degradation."""

import asyncio
import time
from typing import Any, Dict, Optional
import redis.asyncio as aioredis
from redis.exceptions import ConnectionError, RedisError, TimeoutError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("redis_client")


class RedisManager:
    """Manages Redis connection lifecycle, metrics, and fallback state."""

    def __init__(self):
        self._client: Optional[aioredis.Redis] = None
        self._is_available: bool = False
        self._last_check: float = 0.0
        self._check_interval: float = 5.0  # seconds between reconnect attempts

        # In-memory telemetry
        self.hits: int = 0
        self.misses: int = 0
        self.fallbacks: int = 0
        self.total_operations: int = 0
        self.total_latency_ms: float = 0.0

    async def initialize(self) -> None:
        """Create Redis connection pool and test connection."""
        try:
            self._client = aioredis.from_url(
                settings.REDIS_URL,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                socket_timeout=settings.REDIS_TIMEOUT_SECONDS,
                socket_connect_timeout=settings.REDIS_TIMEOUT_SECONDS,
                decode_responses=True,
            )
            await self._client.ping()
            self._is_available = True
            logger.info("Connected to Redis at %s", settings.REDIS_URL)
        except Exception as e:
            self._is_available = False
            logger.warning("Redis is currently unavailable: %s. Operating in PostgreSQL fallback mode.", str(e))

    async def close(self) -> None:
        """Close connection pool gracefully."""
        if self._client:
            await self._client.aclose()
            self._client = None
            self._is_available = False
            logger.info("Redis connection closed")

    @property
    def is_available(self) -> bool:
        return self._is_available

    async def get_client(self) -> Optional[aioredis.Redis]:
        """Return active Redis client or attempt reconnect if check interval elapsed."""
        now = time.monotonic()
        if not self._is_available and (now - self._last_check > self._check_interval):
            self._last_check = now
            try:
                if self._client is None:
                    self._client = aioredis.from_url(
                        settings.REDIS_URL,
                        max_connections=settings.REDIS_MAX_CONNECTIONS,
                        socket_timeout=settings.REDIS_TIMEOUT_SECONDS,
                        decode_responses=True,
                    )
                await asyncio.wait_for(self._client.ping(), timeout=settings.REDIS_TIMEOUT_SECONDS)
                self._is_available = True
                logger.info("Reconnected to Redis successfully")
            except Exception:
                self._is_available = False
                return None

        return self._client if self._is_available else None

    def record_hit(self) -> None:
        self.hits += 1

    def record_miss(self) -> None:
        self.misses += 1

    def record_fallback(self) -> None:
        self.fallbacks += 1

    def record_op(self, duration_ms: float) -> None:
        self.total_operations += 1
        self.total_latency_ms += duration_ms

    def get_metrics(self) -> Dict[str, Any]:
        """Return real-time cache performance metrics."""
        total_requests = self.hits + self.misses
        hit_ratio = round((self.hits / total_requests) * 100, 2) if total_requests > 0 else 0.0
        avg_latency = round(self.total_latency_ms / self.total_operations, 3) if self.total_operations > 0 else 0.0
        return {
            "is_connected": self._is_available,
            "hits": self.hits,
            "misses": self.misses,
            "hit_ratio_percent": hit_ratio,
            "database_fallbacks": self.fallbacks,
            "total_operations": self.total_operations,
            "average_latency_ms": avg_latency,
        }


redis_manager = RedisManager()
