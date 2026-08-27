"""app/models/zone.py — Geographic zones for risk scoring."""
from __future__ import annotations

from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import Boolean, Float, Index, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class ZoneRiskLevel(str, PyEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class GeographicZone(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "geographic_zones"
    __table_args__ = (
        Index("ix_zones_name", "name"),
        Index("ix_zones_risk_level", "risk_level"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Bounding box (simple rectangle for MVP; polygon via PostGIS in future)
    min_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    max_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    min_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    max_longitude: Mapped[float] = mapped_column(Float, nullable=False)

    # Centre point for quick distance calculations
    center_latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    center_longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Risk classification
    risk_level: Mapped[ZoneRiskLevel] = mapped_column(
        SAEnum(ZoneRiskLevel, name="zonerisklevel"),
        default=ZoneRiskLevel.LOW,
        nullable=False,
    )
    base_risk_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    is_high_risk: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    risk_scores: Mapped[List["RiskScore"]] = relationship(
        "RiskScore", back_populates="zone", lazy="dynamic"
    )
    incidents: Mapped[List["Incident"]] = relationship(
        "Incident", back_populates="zone", lazy="dynamic"
    )
    weather_observations: Mapped[List["WeatherObservation"]] = relationship(
        "WeatherObservation", back_populates="zone", lazy="dynamic"
    )
    news_events: Mapped[List["NewsEvent"]] = relationship(
        "NewsEvent", back_populates="zone", lazy="dynamic"
    )
    mesh_nodes: Mapped[List["MeshNode"]] = relationship(
        "MeshNode", back_populates="zone", lazy="dynamic"
    )
