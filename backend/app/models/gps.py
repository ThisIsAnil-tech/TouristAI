"""app/models/gps.py — GPS readings, routes, route points."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class GpsReading(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One GPS observation submitted by the tourist's device."""

    __tablename__ = "gps_readings"
    __table_args__ = (
        Index("ix_gps_readings_user_id", "user_id"),
        Index("ix_gps_readings_recorded_at", "recorded_at"),
        Index("ix_gps_readings_user_recorded", "user_id", "recorded_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    altitude_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    accuracy_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    speed_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bearing_deg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Timestamp from the device (may differ from created_at)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Analysis flags
    is_anomalous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    anomaly_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    distance_from_previous_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    in_high_risk_zone: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("geographic_zones.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="gps_readings")
    zone: Mapped[Optional["GeographicZone"]] = relationship("GeographicZone")


class Route(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A planned route for a tourist trip."""

    __tablename__ = "routes"
    __table_args__ = (
        Index("ix_routes_user_id", "user_id"),
        Index("ix_routes_is_active", "is_active"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User")
    points: Mapped[List["RoutePoint"]] = relationship(
        "RoutePoint", back_populates="route", cascade="all, delete-orphan",
        order_by="RoutePoint.sequence_number"
    )


class RoutePoint(UUIDPrimaryKeyMixin, Base):
    """An ordered point in a planned route."""

    __tablename__ = "route_points"
    __table_args__ = (
        Index("ix_route_points_route_id", "route_id"),
    )

    route_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("routes.id", ondelete="CASCADE"), nullable=False
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    route: Mapped["Route"] = relationship("Route", back_populates="points")
