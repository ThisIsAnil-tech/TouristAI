"""app/models/audio.py — Audio detection results."""
from __future__ import annotations

import uuid
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class AudioClass(str, PyEnum):
    SCREAM = "SCREAM"
    GLASS_BREAK = "GLASS_BREAK"
    NORMAL = "NORMAL"
    UNKNOWN = "UNKNOWN"


class AudioDetectionMode(str, PyEnum):
    EDGE = "EDGE"        # mobile client sent result
    BACKEND = "BACKEND"  # backend performed inference


class AudioDetection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "audio_detections"
    __table_args__ = (
        Index("ix_audio_detections_user_id", "user_id"),
        Index("ix_audio_detections_is_distress", "is_distress"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Classification result
    predicted_class: Mapped[AudioClass] = mapped_column(
        SAEnum(AudioClass, name="audioclass"), nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Class probabilities (JSON string — not raw audio, just small floats)
    class_probabilities: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Threshold at time of decision
    adaptive_threshold_used: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    risk_score_at_detection: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Decision
    is_distress: Mapped[bool] = mapped_column(Boolean, nullable=False)
    detection_mode: Mapped[AudioDetectionMode] = mapped_column(
        SAEnum(AudioDetectionMode, name="audiodetectionmode"),
        default=AudioDetectionMode.EDGE,
        nullable=False,
    )

    # Location at time of detection
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Inference metadata
    inference_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Linked SOS (if triggered)
    sos_event_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sos_events.id", ondelete="SET NULL"), nullable=True
    )

    user: Mapped["User"] = relationship("User", back_populates="audio_detections")
