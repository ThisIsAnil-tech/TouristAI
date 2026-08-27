"""app/models/incident.py — Historical safety incidents."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class IncidentSeverity(str, PyEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentType(str, PyEnum):
    CRIME = "CRIME"
    ACCIDENT = "ACCIDENT"
    NATURAL_DISASTER = "NATURAL_DISASTER"
    WILDLIFE = "WILDLIFE"
    MEDICAL = "MEDICAL"
    FIRE = "FIRE"
    FLOOD = "FLOOD"
    LANDSLIDE = "LANDSLIDE"
    CIVIL_UNREST = "CIVIL_UNREST"
    ROAD_CLOSURE = "ROAD_CLOSURE"
    OTHER = "OTHER"


class Incident(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "incidents"
    __table_args__ = (
        Index("ix_incidents_zone_id", "zone_id"),
        Index("ix_incidents_occurred_at", "occurred_at"),
        Index("ix_incidents_severity", "severity"),
        Index("ix_incidents_incident_type", "incident_type"),
    )

    zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("geographic_zones.id", ondelete="SET NULL"), nullable=True
    )
    incident_type: Mapped[IncidentType] = mapped_column(
        SAEnum(IncidentType, name="incidenttype"), nullable=False
    )
    severity: Mapped[IncidentSeverity] = mapped_column(
        SAEnum(IncidentSeverity, name="incidentseverity"), nullable=False
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Normalised severity weight for risk calculation (0.0 – 1.0)
    severity_weight: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)

    zone: Mapped[Optional["GeographicZone"]] = relationship("GeographicZone", back_populates="incidents")
