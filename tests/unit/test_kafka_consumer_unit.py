"""Unit tests for Kafka analytics consumer and producer internal mechanics."""

import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from app.events.consumer import KafkaAnalyticsConsumer, DeduplicationCache
from app.events.producer import KafkaProducerManager
from app.events.schema import ClickEventMessage


@pytest.mark.asyncio
async def test_deduplication_cache_lru_eviction():
    cache = DeduplicationCache(capacity=3)
    assert cache.is_duplicate_local("id1") is False
    assert cache.is_duplicate_local("id2") is False
    assert cache.is_duplicate_local("id3") is False

    # id1, id2, id3 are stored. id1 was accessed first
    assert cache.is_duplicate_local("id1") is True

    # Add id4, should evict least recently used (which is id2 now)
    assert cache.is_duplicate_local("id4") is False
    assert cache.is_duplicate_local("id2") is False  # Evicted, so reports False now


@pytest.mark.asyncio
async def test_consumer_metrics_and_dlq_dispatch():
    consumer = KafkaAnalyticsConsumer()
    mock_dlq = AsyncMock()
    consumer._dlq_producer = mock_dlq

    payload = b'{"bad_event": 123}'
    await consumer._send_to_dlq(payload, error_reason="Schema parse failure")

    assert consumer.dlq_events == 1
    mock_dlq.send_and_wait.assert_called_once()

    metrics = consumer.get_metrics()
    assert metrics["dlq_events"] == 1
    assert metrics["processed_events"] == 0


@pytest.mark.asyncio
async def test_producer_enqueue_spillover():
    import asyncio
    producer = KafkaProducerManager()
    producer._queue = asyncio.Queue(maxsize=1)

    dummy_event = ClickEventMessage(
        event_id=str(uuid.uuid4()),
        url_id=str(uuid.uuid4()),
        short_code="dummy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        ip_hash="hash",
        user_agent="agent",
    )
    producer._queue.put_nowait(dummy_event)

    event = ClickEventMessage(
        event_id=str(uuid.uuid4()),
        url_id=str(uuid.uuid4()),
        short_code="spillover1",
        timestamp=datetime.now(timezone.utc).isoformat(),
        ip_hash="testhash",
        user_agent="pytest",
    )

    mock_redis = AsyncMock()
    with patch("app.cache.redis_client.redis_manager.get_client", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_redis
        res = producer.enqueue_click_event(event)
        # Should initiate async spillover task
        assert res is True

    metrics = producer.get_metrics()
    assert metrics["max_queue_size"] == 1
