"""Unit tests for background analytics worker lifecycle and graceful termination."""

import asyncio
from unittest.mock import AsyncMock, patch
import pytest

from app.workers.analytics_worker import main


@pytest.mark.asyncio
async def test_analytics_worker_lifecycle():
    """Verify worker starts components and handles cancellation gracefully."""
    with patch("app.workers.analytics_worker.init_db", new_callable=AsyncMock) as mock_init_db, \
         patch("app.workers.analytics_worker.kafka_consumer.start", new_callable=AsyncMock) as mock_start, \
         patch("app.workers.analytics_worker.kafka_consumer.stop", new_callable=AsyncMock) as mock_stop, \
         patch("app.workers.analytics_worker.kafka_consumer.run_worker_loop", new_callable=AsyncMock) as mock_loop, \
         patch("app.workers.analytics_worker.engine") as mock_engine, \
         patch("asyncio.sleep", side_effect=[asyncio.CancelledError()]):

        mock_engine.dispose = AsyncMock()

        with pytest.raises(asyncio.CancelledError):
            await main()

        mock_init_db.assert_awaited_once()
        mock_start.assert_awaited_once()
        mock_loop.assert_called_once()
        mock_stop.assert_awaited_once()
        mock_engine.dispose.assert_awaited_once()
