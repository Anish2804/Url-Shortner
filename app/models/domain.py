"""Custom domain entity for branded URL shortening."""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, GUID, TimestampMixin, UUIDMixin


class CustomDomain(Base, UUIDMixin, TimestampMixin):
    """Branded domain configured by organization/user."""

    __tablename__ = "custom_domains"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    domain: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    verification_token: Mapped[str] = mapped_column(String(64), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


Index("ix_custom_domains_lookup", CustomDomain.domain, CustomDomain.is_verified, CustomDomain.is_active)
