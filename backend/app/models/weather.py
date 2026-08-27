"""app/models/weather.py — Stored weather observations."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class WeatherObservation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "weather_observations"
    __table_args__ = (
        Index("ix_weather_observations_zone_id", "zone_id"),
        Index("ix_weather_observations_observed_at", "observed_at"),
    )

    zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("geographic_zones.id", ondelete="SET NULL"), nullable=True
    )

    # Raw observation values from OpenWeatherMap
    temperature_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    feels_like_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    humidity_pct: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    wind_speed_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wind_direction_deg: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    visibility_m: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cloud_cover_pct: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rain_1h_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    snow_1h_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # OWM weather condition code and description
    weather_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    weather_main: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    weather_description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Normalised weather risk score (0.0 – 1.0) after processing
    weather_risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Location queried (may differ from zone centre)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    zone: Mapped[Optional["GeographicZone"]] = relationship(
        "GeographicZone", back_populates="weather_observations"
    )
