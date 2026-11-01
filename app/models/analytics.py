"""Analytics ORM models: raw click events and pre-aggregated rollups."""

import uuid
from datetime import date, datetime
from typing import Optional
from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, GUID, TimestampMixin, UUIDMixin


class ClickEvent(Base, UUIDMixin):
    """Raw click event captured asynchronously from Kafka stream."""

    __tablename__ = "click_events"

    url_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("urls.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    short_code: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    clicked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)

    # Privacy-conscious visitor tracking (HMAC hashed IP, raw IP never stored)
    ip_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    anonymized_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    # Geographic metrics
    country_code: Mapped[Optional[str]] = mapped_column(String(2), index=True, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Device & Client categorization
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    device_type: Mapped[str] = mapped_column(String(32), default="desktop", index=True, nullable=False)
    browser: Mapped[str] = mapped_column(String(64), default="other", index=True, nullable=False)
    os: Mapped[str] = mapped_column(String(64), default="other", index=True, nullable=False)

    # Referrer details
    referrer: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    referrer_domain: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)

    # Bot & Abuse flags
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)

    url: Mapped["Url"] = relationship("Url", back_populates="click_events")


class DailyAggregate(Base, UUIDMixin, TimestampMixin):
    """Pre-computed daily analytics rollup for lightning-fast dashboard queries."""

    __tablename__ = "daily_aggregates"

    url_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("urls.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    total_clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unique_visitors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bot_clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Serialized JSON breakdowns for fast charts
    browser_breakdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    os_breakdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    device_breakdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    country_breakdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    referrer_breakdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class HourlyAggregate(Base, UUIDMixin, TimestampMixin):
    """Hourly click bucket aggregation for real-time trend visualization."""

    __tablename__ = "hourly_aggregates"

    url_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("urls.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    hour_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    total_clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unique_visitors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


# Composite indexes for range filters
Index("ix_click_events_url_time", ClickEvent.url_id, ClickEvent.clicked_at)
Index("ix_daily_aggregates_url_date", DailyAggregate.url_id, DailyAggregate.date, unique=True)
Index("ix_hourly_aggregates_url_hour", HourlyAggregate.url_id, HourlyAggregate.hour_timestamp, unique=True)
