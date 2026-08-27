"""app/models/risk.py — Environmental risk scores."""
from __future__ import annotations

import uuid
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import Float, ForeignKey, Index, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class RiskLevel(str, PyEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskScore(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    One environmental risk calculation for a geographic zone.

    Stores each component score, the final weighted score (1-10),
    the risk level, and the adaptive AI threshold derived from it.
    """
    __tablename__ = "risk_scores"
    __table_args__ = (
        Index("ix_risk_scores_zone_id", "zone_id"),
        Index("ix_risk_scores_created_at", "created_at"),
    )

    zone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("geographic_zones.id", ondelete="CASCADE"), nullable=False
    )

    # Component scores (all 0.0 – 1.0 before scaling)
    weather_score: Mapped[float] = mapped_column(Float, nullable=False)
    news_score: Mapped[float] = mapped_column(Float, nullable=False)
    historical_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Weights used for this calculation (stored for reproducibility)
    weight_weather: Mapped[float] = mapped_column(Float, nullable=False)
    weight_news: Mapped[float] = mapped_column(Float, nullable=False)
    weight_historical: Mapped[float] = mapped_column(Float, nullable=False)

    # Final composite score (1.0 – 10.0)
    final_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(
        SAEnum(RiskLevel, name="risklevel"), nullable=False
    )

    # Adaptive AI confidence threshold derived from this risk score
    adaptive_threshold: Mapped[float] = mapped_column(Float, nullable=False)

    # Optional: weather observation / news event IDs that contributed
    weather_observation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("weather_observations.id", ondelete="SET NULL"), nullable=True
    )

    zone: Mapped["GeographicZone"] = relationship("GeographicZone", back_populates="risk_scores")
