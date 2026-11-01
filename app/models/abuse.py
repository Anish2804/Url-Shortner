"""Abuse reporting and domain blocklist ORM models."""

import uuid
from typing import Optional
from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, GUID, TimestampMixin, UUIDMixin


class AbuseReport(Base, UUIDMixin, TimestampMixin):
    """User-submitted abuse report for malicious or suspicious shortened links."""

    __tablename__ = "abuse_reports"

    short_code: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    reporter_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reason: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True, nullable=False)
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class BlockedDomain(Base, UUIDMixin, TimestampMixin):
    """Administrative blocklist for phishing, malware, or spam domains."""

    __tablename__ = "blocked_domains"

    domain: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
