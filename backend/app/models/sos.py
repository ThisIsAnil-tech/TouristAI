"""app/models/sos.py — SOS events."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class SosStatus(str, PyEnum):
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    FALSE_ALARM = "FALSE_ALARM"
    CANCELLED = "CANCELLED"


class SosTrigger(str, PyEnum):
    AUDIO_DISTRESS = "AUDIO_DISTRESS"
    GPS_ANOMALY = "GPS_ANOMALY"
    MANUAL = "MANUAL"
    COMBINED = "COMBINED"


class SosEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sos_events"
    __table_args__ = (
        Index("ix_sos_events_user_id", "user_id"),
        Index("ix_sos_events_status", "status"),
        Index("ix_sos_events_triggered_at", "triggered_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    trigger: Mapped[SosTrigger] = mapped_column(
        SAEnum(SosTrigger, name="sostrigger"), nullable=False
    )
    status: Mapped[SosStatus] = mapped_column(
        SAEnum(SosStatus, name="sosstatus"), default=SosStatus.ACTIVE, nullable=False
    )

    # Evidence
    audio_detection_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audio_detections.id", ondelete="SET NULL"), nullable=True
    )
    gps_reading_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gps_readings.id", ondelete="SET NULL"), nullable=True
    )
    risk_score_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("risk_scores.id", ondelete="SET NULL"), nullable=True
    )

    # Decision details
    decision_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    adaptive_threshold: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    risk_score_at_trigger: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Location
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("geographic_zones.id", ondelete="SET NULL"), nullable=True
    )

    # Timestamps for research experiment timelines
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Responder assignment
    assigned_responder_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("responders.id", ondelete="SET NULL"), nullable=True
    )

    # Idempotency key (from X-Idempotency-Key header)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sos_events")
    communication_attempts: Mapped[List["CommunicationAttempt"]] = relationship(
        "CommunicationAttempt", back_populates="sos_event", cascade="all, delete-orphan"
    )
    emergency_access_grants: Mapped[List["EmergencyAccessGrant"]] = relationship(
        "EmergencyAccessGrant", back_populates="sos_event"
    )
