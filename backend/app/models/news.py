"""app/models/news.py — News/safety intelligence events."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class NewsCategory(str, PyEnum):
    FLOOD = "FLOOD"
    LANDSLIDE = "LANDSLIDE"
    WILDLIFE = "WILDLIFE"
    CRIME = "CRIME"
    ROAD_CLOSURE = "ROAD_CLOSURE"
    FIRE = "FIRE"
    WEATHER_WARNING = "WEATHER_WARNING"
    CIVIL_UNREST = "CIVIL_UNREST"
    ACCIDENT = "ACCIDENT"
    MEDICAL = "MEDICAL"
    OTHER = "OTHER"


class NewsSeverity(str, PyEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class NewsEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "news_events"
    __table_args__ = (
        UniqueConstraint("source_url", "published_at", name="uq_news_url_time"),
        Index("ix_news_events_zone_id", "zone_id"),
        Index("ix_news_events_category", "category"),
        Index("ix_news_events_published_at", "published_at"),
        Index("ix_news_events_severity", "severity"),
    )

    zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("geographic_zones.id", ondelete="SET NULL"), nullable=True
    )

    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    content_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    category: Mapped[NewsCategory] = mapped_column(
        SAEnum(NewsCategory, name="newscategory"), nullable=False
    )
    severity: Mapped[NewsSeverity] = mapped_column(
        SAEnum(NewsSeverity, name="newsseverity"), nullable=False
    )

    # Normalised news risk score (0.0 – 1.0)
    severity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Raw metadata from scraping
    raw_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    zone: Mapped[Optional["GeographicZone"]] = relationship("GeographicZone", back_populates="news_events")
