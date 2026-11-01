"""Integration tests for Kafka events, deduplication, and producer bounded queue backpressure."""

import asyncio
import pytest
from app.events.consumer import DeduplicationCache
from app.events.producer import KafkaProducerManager
from app.events.schema import ClickEventMessage


def test_click_event_schema_versioning():
    event = ClickEventMessage(
        url_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        short_code="py314",
        ip_hash="abc123hash",
        device_type="desktop",
        browser="Chrome",
        os="Windows",
    )
    assert event.event_version == "1.0"
    assert len(event.event_id) > 20
    assert event.short_code == "py314"


def test_consumer_deduplication_cache():
    dedup = DeduplicationCache(capacity=5)

    assert dedup.is_duplicate("evt-1") is False
    assert dedup.is_duplicate("evt-1") is True  # Duplicate!

    assert dedup.is_duplicate("evt-2") is False
    assert dedup.is_duplicate("evt-2") is True


def test_producer_bounded_queue_backpressure():
    """Verify that KafkaProducerManager respects bounded queue limits and drops excess items safely."""
    producer = KafkaProducerManager()
    # Replace internal queue with small bounded queue of size 3
    producer._queue = asyncio.Queue(maxsize=3)

    event = ClickEventMessage(
        url_id="1234",
        short_code="test",
        ip_hash="hash",
    )

    # Put 3 items (fills queue)
    assert producer.enqueue_click_event(event) is True
    assert producer.enqueue_click_event(event) is True
    assert producer.enqueue_click_event(event) is True

    # 4th item must be dropped safely without raising QueueFull
    assert producer.enqueue_click_event(event) is False
    assert producer.dropped_events == 1

    metrics = producer.get_metrics()
    assert metrics["queue_size"] == 3
    assert metrics["dropped_events"] == 1
