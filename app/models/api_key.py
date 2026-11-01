"""API Key entity for machine-to-machine authentication with scopes and expiry."""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, GUID, TimestampMixin, UUIDMixin


class ApiKey(Base, UUIDMixin, TimestampMixin):
    """Scoped API key credentials for programmatic platform access."""

    __tablename__ = "api_keys"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Stored as prefix for UI display (e.g., lks_8a1f)
    prefix: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    # SHA-256 hash of the complete raw secret key
    hashed_key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    # Comma-delimited scopes: e.g., 'urls:read,urls:write,analytics:read'
    scopes: Mapped[str] = mapped_column(String(255), default="urls:read,urls:write,analytics:read", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="api_keys")

    def has_scope(self, required_scope: str) -> bool:
        """Check if this API key grants the requested scope."""
        granted = [s.strip() for s in self.scopes.split(",") if s.strip()]
        return "*" in granted or required_scope in granted


Index("ix_api_keys_lookup", ApiKey.hashed_key, ApiKey.is_active)
