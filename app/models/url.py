"""URL shortener ORM model with custom aliases, security flags, and life-cycle controls."""

import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, GUID, TimestampMixin, UUIDMixin


class Url(Base, UUIDMixin, TimestampMixin):
    """Core shortened URL entity."""

    __tablename__ = "urls"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    # The generated or custom short identifier
    short_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    custom_alias: Mapped[Optional[str]] = mapped_column(String(64), unique=True, index=True, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Redirection configuration
    redirect_http_code: Mapped[int] = mapped_column(SmallInteger, default=302, nullable=False)

    # Status and Lifecycle
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Advanced Security Features
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_one_time: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_consumed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Quick metric rollup
    click_count: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    # Relationships
    owner: Mapped[Optional["User"]] = relationship("User", back_populates="urls")
    click_events: Mapped[List["ClickEvent"]] = relationship(
        "ClickEvent",
        back_populates="url",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


# Composite indexes for high-throughput redirect queries and user dashboards
Index("ix_urls_redirect_lookup", Url.short_code, Url.is_active, Url.is_deleted)
Index("ix_urls_user_active", Url.user_id, Url.is_active, Url.is_deleted)
