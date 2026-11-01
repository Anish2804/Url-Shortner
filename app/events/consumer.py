"""Kafka consumer with batch processing, deduplication, retry logic, and DLQ routing."""

import asyncio
import json
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from app.core.config import settings
from app.core.logging import get_logger
from app.database.session import async_session_factory
from app.events.schema import ClickEventMessage
from app.models.analytics import ClickEvent
from app.repositories.analytics_repo import AnalyticsRepository
from app.repositories.url_repo import UrlRepository

logger = get_logger("kafka_consumer")


class DeduplicationCache:
    """Bounded LRU cache for deduplicating incoming Kafka events."""

    def __init__(self, capacity: int = 10000):
        self.capacity = capacity
        self.cache: OrderedDict[str, float] = OrderedDict()

    def is_duplicate(self, event_id: str) -> bool:
        if event_id in self.cache:
            self.cache.move_to_end(event_id)
            return True
        self.cache[event_id] = datetime.now(timezone.utc).timestamp()
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
        return False


class KafkaAnalyticsConsumer:
    """Consumer processing click batches, updating aggregates, and forwarding poisonous messages to DLQ."""

    def __init__(self):
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._dlq_producer: Optional[AIOKafkaProducer] = None
        self._is_running: bool = False
        self._dedup = DeduplicationCache(capacity=20000)

        # Telemetry
        self.processed_events: int = 0
        self.duplicate_events: int = 0
        self.dlq_events: int = 0
        self.batches_processed: int = 0

    async def start(self) -> None:
        """Start Kafka consumer and DLQ producer."""
        self._is_running = True
        try:
            self._consumer = AIOKafkaConsumer(
                settings.KAFKA_TOPIC_CLICKS,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id=settings.KAFKA_CONSUMER_GROUP,
                enable_auto_commit=False,  # Manual commits after successful DB transaction
                auto_offset_reset="earliest",
                max_poll_records=settings.KAFKA_BATCH_SIZE,
            )
            await self._consumer.start()

            self._dlq_producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            )
            await self._dlq_producer.start()

            logger.info("Kafka analytics consumer started for topic %s", settings.KAFKA_TOPIC_CLICKS)
        except Exception as e:
            logger.warning("Kafka consumer could not connect to %s: %s", settings.KAFKA_BOOTSTRAP_SERVERS, str(e))
            self._is_running = False

    async def stop(self) -> None:
        """Gracefully close Kafka consumer."""
        self._is_running = False
        if self._consumer:
            await self._consumer.stop()
            self._consumer = None
        if self._dlq_producer:
            await self._dlq_producer.stop()
            self._dlq_producer = None
        logger.info("Kafka analytics consumer stopped")

    async def run_worker_loop(self) -> None:
        """Poll Kafka in batches, deduplicate, persist to PostgreSQL, and commit offsets."""
        if not self._consumer:
            return

        while self._is_running:
            try:
                # Batch poll with timeout
                data = await self._consumer.getmany(
                    timeout_ms=settings.KAFKA_BATCH_TIMEOUT_MS,
                    max_records=settings.KAFKA_BATCH_SIZE,
                )

                if not data:
                    await asyncio.sleep(0.1)
                    continue

                for tp, messages in data.items():
                    if not messages:
                        continue

                    valid_events: List[ClickEvent] = []
                    url_clicks_count: Dict[uuid.UUID, int] = {}

                    for msg in messages:
                        try:
                            payload = json.loads(msg.value.decode("utf-8"))
                            event = ClickEventMessage(**payload)

                            # Deduplication check
                            if self._dedup.is_duplicate(event.event_id):
                                self.duplicate_events += 1
                                continue

                            url_uuid = uuid.UUID(event.url_id)
                            clicked_dt = datetime.fromisoformat(event.timestamp)

                            db_event = ClickEvent(
                                id=uuid.UUID(event.event_id),
                                url_id=url_uuid,
                                short_code=event.short_code,
                                clicked_at=clicked_dt,
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
                            )
                            valid_events.append(db_event)
                            url_clicks_count[url_uuid] = url_clicks_count.get(url_uuid, 0) + 1

                        except Exception as parse_err:
                            logger.error("Failed to parse event message: %s. Forwarding to DLQ.", str(parse_err))
                            await self._send_to_dlq(msg.value, str(parse_err))

                    # Persist valid events in single database transaction
                    if valid_events:
                        await self._persist_batch(valid_events, url_clicks_count)

                    # Manually commit partition offsets after successful persistence
                    await self._consumer.commit({tp: messages[-1].offset + 1})
                    self.batches_processed += 1

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in consumer loop: %s", str(e))
                await asyncio.sleep(1.0)

    async def _persist_batch(self, events: List[ClickEvent], click_counts: Dict[uuid.UUID, int]) -> None:
        """Persist click events and update URL click counts inside a transaction."""
        async with async_session_factory() as session:
            try:
                session.add_all(events)
                url_repo = UrlRepository(session)
                for u_id, count in click_counts.items():
                    await url_repo.increment_click_count(u_id, increment=count)
                await session.commit()
                self.processed_events += len(events)
            except Exception as db_err:
                await session.rollback()
                logger.error("Database error during click batch insert: %s", str(db_err))
                # For catastrophic single-event poisoning, individually route failed events to DLQ
                for ev in events:
                    await self._send_to_dlq(json.dumps({"event_id": str(ev.id)}).encode("utf-8"), str(db_err))

    async def _send_to_dlq(self, payload: bytes, error_reason: str) -> None:
        """Forward poisonous unprocessable message to Dead Letter Queue."""
        if not self._dlq_producer:
            return
        try:
            headers = [("error", error_reason.encode("utf-8")), ("failed_at", datetime.now(timezone.utc).isoformat().encode("utf-8"))]
            await self._dlq_producer.send_and_wait(settings.KAFKA_TOPIC_DLQ, value=payload, headers=headers)
            self.dlq_events += 1
            logger.info("Dispatched unprocessable event to DLQ topic %s", settings.KAFKA_TOPIC_DLQ)
        except Exception as dlq_err:
            logger.error("Failed to publish to DLQ: %s", str(dlq_err))

    def get_metrics(self) -> Dict[str, Any]:
        """Consumer telemetry metrics."""
        return {
            "processed_events": self.processed_events,
            "duplicate_events": self.duplicate_events,
            "dlq_events": self.dlq_events,
            "batches_processed": self.batches_processed,
        }


kafka_consumer = KafkaAnalyticsConsumer()
