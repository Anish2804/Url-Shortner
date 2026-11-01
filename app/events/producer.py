"""Asynchronous Kafka event producer with non-blocking bounded buffering."""

import asyncio
import json
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
            await self._producer.start()
            self._is_connected = True
            logger.info("Kafka producer connected to %s", settings.KAFKA_BOOTSTRAP_SERVERS)
        except Exception as e:
            self._is_connected = False
            logger.warning("Kafka is currently unavailable: %s. Using bounded buffering fallback.", str(e))

        self._worker_task = asyncio.create_task(self._dispatch_loop())

    async def stop(self) -> None:
        """Gracefully drain queue and shut down producer."""
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
        
        Returns True if queued, False if queue was full (protects against unbounded memory).
        """
        try:
            self._queue.put_nowait(event)
            return True
        except asyncio.QueueFull:
            self.dropped_events += 1
            logger.warning("Kafka producer buffer full (%d items). Dropping click event to protect redirect latency.", self._queue.maxsize)
            return False

    async def _dispatch_loop(self) -> None:
        """Background worker consuming from bounded queue and delivering to Kafka."""
        while self._is_running:
            try:
                event = await self._queue.get()
                await self._publish_event(event)
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in Kafka dispatch loop: %s", str(e))
                await asyncio.sleep(0.5)

    async def _publish_event(self, event: ClickEventMessage) -> None:
        """Send message to Kafka with partition key = short_code."""
        if not self._is_connected or not self._producer:
            # Try reconnecting if disconnected
            try:
                if self._producer is None:
                    self._producer = AIOKafkaProducer(
                        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                        request_timeout_ms=settings.KAFKA_PRODUCER_TIMEOUT_MS,
                    )
                    await self._producer.start()
                self._is_connected = True
            except Exception:
                self.failed_events += 1
                self._is_connected = False
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
            logger.warning("Failed to publish event %s to Kafka: %s", event.event_id, str(e))

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
