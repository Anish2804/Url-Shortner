"""Dedicated background worker process consuming Kafka click events and writing analytics."""

import asyncio
import signal
import sys

from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.database.session import engine, init_db
from app.events.consumer import kafka_consumer

logger = get_logger("analytics_worker")


async def main() -> None:
    """Worker entry point."""
    setup_logging(log_level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)
    logger.info("Starting Analytics Kafka Consumer Worker...")

    # Initialize DB tables if not present
    await init_db()

    # Start Kafka consumer
    await kafka_consumer.start()

    stop_event = asyncio.Event()

    def handle_stop():
        logger.info("Received termination signal. Shutting down worker gracefully...")
        stop_event.set()

    loop = asyncio.get_running_loop()
    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, handle_stop)

    # Launch consumer loop task
    worker_task = asyncio.create_task(kafka_consumer.run_worker_loop())

    try:
        if sys.platform == "win32":
            # On Windows signal handlers are limited in asyncio
            while not stop_event.is_set():
                await asyncio.sleep(1.0)
        else:
            await stop_event.wait()
    except (KeyboardInterrupt, SystemExit):
        handle_stop()
    finally:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

        await kafka_consumer.stop()
        await engine.dispose()
        logger.info("Analytics Consumer Worker stopped cleanly.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
