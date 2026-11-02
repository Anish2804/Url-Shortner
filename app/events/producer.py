"""Asynchronous Kafka event producer with non-blocking bounded buffering."""

import asyncio
from typing import Any, Dict, Optional
from aiokafka import AIOKafkaProducer

from app.core.config import settings
from app.core.logging import get_logger
from app.events.schema import ClickEventMessage

logger = get_logger("kafka_producer")


class KafkaProducerManager:
    """Production Kafka producer with bounded queue buffering for zero redirect latency."""

    def __init__(self):
        self._producer: Optional[AIOKafkaProducer] = None
        self._queue: asyncio.Queue[ClickEventMessage] = asyncio.Queue(
            maxsize=settings.KAFKA_PRODUCER_FALLBACK_QUEUE_MAX
        )
        self._worker_task: Optional[asyncio.Task] = None
        self._is_running: bool = False
        self._is_connected: bool = False

        # Telemetry
        self.published_events: int = 0
        self.dropped_events: int = 0
        self.failed_events: int = 0
        self._last_connect_attempt: float = 0.0

    async def start(self) -> None:
        """Start producer connection and background dispatcher."""
        self._is_running = True
        try:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                request_timeout_ms=settings.KAFKA_PRODUCER_TIMEOUT_MS,
                compression_type="gzip",
                enable_idempotence=True,
            )
            await asyncio.wait_for(self._producer.start(), timeout=1.5)
            self._is_connected = True
            logger.info("Kafka producer connected to %s", settings.KAFKA_BOOTSTRAP_SERVERS)
        except Exception as e:
            if self._producer:
                try:
                    await self._producer.stop()
                except Exception:
                    pass
            self._producer = None
            self._is_connected = False
            logger.info("Kafka broker offline (%s). Standalone local mode active (direct database persistence).", str(e))

        self._worker_task = asyncio.create_task(self._dispatch_loop())

    async def stop(self) -> None:
        """Gracefully drain queue and shut down producer."""
        qsize = self._queue.qsize()
        if qsize > 0:
            logger.info("Kafka producer stopping: draining %d buffered events...", qsize)
            try:
                await asyncio.wait_for(self._queue.join(), timeout=3.0)
            except asyncio.TimeoutError:
                logger.warning("Queue drain timed out, proceeding with shutdown.")

        self._is_running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        if self._producer and self._is_connected:
            await self._producer.stop()
            self._producer = None
            self._is_connected = False
            logger.info("Kafka producer stopped")

    def enqueue_click_event(self, event: ClickEventMessage) -> bool:
        """Non-blocking enqueue for redirect path.
        
        Returns True if queued, spills to Redis or records drop if bounded memory exceeded.
        """
        try:
            self._queue.put_nowait(event)
            return True
        except asyncio.QueueFull:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._spillover_to_redis(event))
                return True
            except RuntimeError:
                self.dropped_events += 1
                logger.warning("Kafka producer buffer full (%d items). Dropping click event to protect redirect latency.", self._queue.maxsize)
                return False

    async def _spillover_to_redis(self, event: ClickEventMessage) -> None:
        """Durable spillover to Redis list buffer when in-memory queue is saturated."""
        try:
            from app.cache.redis_client import redis_manager
            r_client = await redis_manager.get_client()
            if r_client:
                await r_client.rpush("buffer:clicks:spillover", event.model_dump_json())
                return
        except Exception as e:
            logger.debug("Redis spillover fallback failed: %s", str(e))
        self.dropped_events += 1

    async def _dispatch_loop(self) -> None:
        """Background worker consuming from bounded queue and delivering to Kafka."""
        while self._is_running:
            try:
                # 1. First drain from Redis spillover if Redis is connected
                from app.cache.redis_client import redis_manager
                if redis_manager.is_available:
                    try:
                        r_client = await redis_manager.get_client()
                        if r_client:
                            raw_item = await r_client.lpop("buffer:clicks:spillover")
                            if raw_item:
                                spillover_msg = ClickEventMessage.model_validate_json(raw_item)
                                await self._publish_event(spillover_msg)
                    except Exception:
                        pass

                # 2. Consume from internal bounded memory queue
                try:
                    event = await asyncio.wait_for(self._queue.get(), timeout=0.2)
                    await self._publish_event(event)
                    self._queue.task_done()
                except asyncio.TimeoutError:
                    continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in Kafka dispatch loop: %s", str(e))
                await asyncio.sleep(0.5)

    async def _publish_event(self, event: ClickEventMessage) -> None:
        """Send message to Kafka with partition key = short_code."""
        if not self._is_connected or not self._producer:
            import time
            now = time.time()
            if now - self._last_connect_attempt > 30.0:
                self._last_connect_attempt = now
                p: Optional[AIOKafkaProducer] = None
                try:
                    p = AIOKafkaProducer(
                        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                        request_timeout_ms=settings.KAFKA_PRODUCER_TIMEOUT_MS,
                    )
                    await asyncio.wait_for(p.start(), timeout=1.5)
                    self._producer = p
                    self._is_connected = True
                except Exception:
                    if p:
                        try:
                            await p.stop()
                        except Exception:
                            pass
                    self._producer = None
                    self._is_connected = False

            if not self._is_connected:
                # Standalone Fallback: Persist directly to DB when Kafka broker is offline
                await self._persist_event_direct(event)
                self.published_events += 1
                return

        try:
            payload = event.model_dump_json().encode("utf-8")
            # Partition key guarantees all clicks for the same short code land on the same partition
            key = event.short_code.encode("utf-8")
            await asyncio.wait_for(
                self._producer.send_and_wait(settings.KAFKA_TOPIC_CLICKS, value=payload, key=key),
                timeout=settings.KAFKA_PRODUCER_TIMEOUT_MS / 1000.0,
            )
            self.published_events += 1
        except Exception as e:
            self.failed_events += 1
            logger.warning("Failed to publish event %s to Kafka, persisting locally: %s", event.event_id, str(e))
            await self._persist_event_direct(event)

    async def _persist_event_direct(self, event: ClickEventMessage) -> None:
        """Standalone fallback: Persist click event directly to database when Kafka broker is offline."""
        try:
            import uuid
            from datetime import datetime
            from sqlalchemy import update
            from app.database.session import async_session_factory
            from app.models.analytics import ClickEvent
            from app.models.url import Url

            async with async_session_factory() as session:
                url_id_val = uuid.UUID(event.url_id) if isinstance(event.url_id, str) else event.url_id
                event_id_val = uuid.UUID(event.event_id) if isinstance(event.event_id, str) else event.event_id
                clicked_at_val = (
                    datetime.fromisoformat(event.timestamp)
                    if isinstance(event.timestamp, str)
                    else event.timestamp
                )

                click_orm = ClickEvent(
                    id=event_id_val,
                    url_id=url_id_val,
                    short_code=event.short_code,
                    ip_hash=event.ip_hash,
                    anonymized_ip=event.anonymized_ip,
                    user_agent=event.user_agent,
                    device_type=event.device_type,
                    browser=event.browser,
                    os=event.os,
                    country_code=event.country_code,
                    city=event.city,
                    referrer=event.referrer,
                    referrer_domain=event.referrer_domain,
                    is_bot=event.is_bot,
                    clicked_at=clicked_at_val,
                )
                session.add(click_orm)
                stmt = (
                    update(Url)
                    .where(Url.id == url_id_val)
                    .values(click_count=Url.click_count + 1)
                )
                await session.execute(stmt)
                await session.commit()
                logger.info("Persisted click event %s for %s directly to database", event_id_val, event.short_code)
        except Exception as e:
            logger.error("Direct click event persistence failed: %s", str(e), exc_info=True)

    def get_metrics(self) -> Dict[str, Any]:
        """Producer observability telemetry."""
        return {
            "is_connected": self._is_connected,
            "queue_size": self._queue.qsize(),
            "max_queue_size": self._queue.maxsize,
            "published_events": self.published_events,
            "dropped_events": self.dropped_events,
            "failed_events": self.failed_events,
        }


kafka_producer = KafkaProducerManager()
