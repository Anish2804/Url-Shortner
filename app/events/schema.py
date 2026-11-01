"""Event schema definition and versioning for distributed click tracking."""

import uuid
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class ClickEventMessage(BaseModel):
    """Versioned click event published to Kafka click stream."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Globally unique event ID")
    event_version: str = Field(default="1.0", description="Schema version for forward/backward compatibility")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Event creation timestamp in ISO 8601 UTC",
    )

    url_id: str = Field(..., description="Target shortened URL UUID")
    short_code: str = Field(..., description="Short code used as Kafka partition key")

    # Privacy-conscious client telemetry
    ip_hash: str = Field(..., description="HMAC-SHA256 salted hash of client IP")
    anonymized_ip: Optional[str] = Field(default=None, description="Masked IP subnet (e.g., 192.168.1.0/24)")

    # Client environment
    user_agent: Optional[str] = Field(default=None)
    device_type: str = Field(default="desktop")
    browser: str = Field(default="other")
    os: str = Field(default="other")

    # Geographic location
    country_code: Optional[str] = Field(default=None)
    city: Optional[str] = Field(default=None)

    # Traffic attribution
    referrer: Optional[str] = Field(default=None)
    referrer_domain: Optional[str] = Field(default=None)
    is_bot: bool = Field(default=False)
