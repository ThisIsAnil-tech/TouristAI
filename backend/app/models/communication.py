"""app/models/communication.py — Communication attempts (Internet/SMS/Mesh)."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class CommunicationChannel(str, PyEnum):
    INTERNET = "INTERNET"
    SMS = "SMS"
    MESH = "MESH"


class DeliveryStatus(str, PyEnum):
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


class CommunicationAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "communication_attempts"
    __table_args__ = (
        Index("ix_comm_attempts_sos_event_id", "sos_event_id"),
        Index("ix_comm_attempts_channel", "channel"),
        Index("ix_comm_attempts_status", "status"),
    )

    sos_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sos_events.id", ondelete="CASCADE"), nullable=False
    )

    channel: Mapped[CommunicationChannel] = mapped_column(
        SAEnum(CommunicationChannel, name="communicationchannel"), nullable=False
    )
    status: Mapped[DeliveryStatus] = mapped_column(
        SAEnum(DeliveryStatus, name="deliverystatus"),
        default=DeliveryStatus.PENDING,
        nullable=False,
    )

    destination: Mapped[str] = mapped_column(String(500), nullable=False)
    message_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timing
    attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Retry tracking
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    # Provider response
    provider_message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    sos_event: Mapped["SosEvent"] = relationship("SosEvent", back_populates="communication_attempts")
