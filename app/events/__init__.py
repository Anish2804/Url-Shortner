"""Events package exports."""

from app.events.consumer import KafkaAnalyticsConsumer, kafka_consumer
from app.events.producer import KafkaProducerManager, kafka_producer
from app.events.schema import ClickEventMessage

__all__ = [
    "ClickEventMessage",
    "KafkaProducerManager",
    "kafka_producer",
    "KafkaAnalyticsConsumer",
    "kafka_consumer",
]
