"""app/models/telemetry.py — Mobile device telemetry."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class MobileTelemetry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Telemetry submitted by the mobile client.

    The backend NEVER fabricates these values.
    If no real telemetry exists, experiments are marked NOT_RUN.
    """
    __tablename__ = "mobile_telemetry"
    __table_args__ = (
        Index("ix_telemetry_user_id", "user_id"),
        Index("ix_telemetry_created_at", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Performance metrics reported by mobile app
    fps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cpu_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ram_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    battery_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    battery_drain_per_hour: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    inference_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Device info
    device_model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    os_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    app_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Context
    session_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="telemetry")
