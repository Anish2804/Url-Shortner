"""Asynchronous Redis client with connection pooling, metrics, and graceful degradation."""

import asyncio
import time
from typing import Any, Dict, Optional
import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("redis_client")


class RedisManager:
    """Manages Redis connection lifecycle, metrics, and fallback state."""

    def __init__(self):
        self._client: Optional[aioredis.Redis] = None
        self._is_available: bool = False
        self._last_check: float = 0.0
        self._check_interval: float = 60.0  # seconds between reconnect probes
        self._reconnecting: bool = False

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
                socket_timeout=0.5,
                socket_connect_timeout=0.5,
                decode_responses=True,
            )
            await asyncio.wait_for(self._client.ping(), timeout=0.5)
            self._is_available = True
            logger.info("Connected to Redis at %s", settings.REDIS_URL)
        except Exception as e:
            self._is_available = False
            logger.info("Redis offline (%s). Running in zero-delay direct PostgreSQL fallback mode.", str(e))

    async def close(self) -> None:
        """Close connection pool gracefully."""
        if self._client:
            try:
                await self._client.aclose()
            except Exception:
                pass
            self._client = None
            self._is_available = False
            logger.info("Redis connection closed")

    @property
    def is_available(self) -> bool:
        return self._is_available

    async def get_client(self) -> Optional[aioredis.Redis]:
        """Return active Redis client immediately without blocking caller if offline."""
        if self._is_available:
            return self._client

        now = time.monotonic()
        if not self._reconnecting and (now - self._last_check > self._check_interval):
            self._last_check = now
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._probe_connection())
            except RuntimeError:
                pass

        return None

    async def _probe_connection(self) -> None:
        """Non-blocking background probe for Redis availability."""
        if self._reconnecting:
            return
        self._reconnecting = True
        try:
            if self._client is None:
                self._client = aioredis.from_url(
                    settings.REDIS_URL,
                    max_connections=settings.REDIS_MAX_CONNECTIONS,
                    socket_timeout=0.5,
                    socket_connect_timeout=0.5,
                    decode_responses=True,
                )
            await asyncio.wait_for(self._client.ping(), timeout=0.5)
            self._is_available = True
            logger.info("Reconnected to Redis successfully")
        except Exception:
            self._is_available = False
        finally:
            self._reconnecting = False

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
