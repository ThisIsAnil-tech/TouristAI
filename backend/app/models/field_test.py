"""app/models/field_test.py — Field test sessions and results."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class FieldTestStatus(str, PyEnum):
    PLANNED = "PLANNED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class FieldTest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "field_tests"
    __table_args__ = (
        Index("ix_field_tests_status", "status"),
        Index("ix_field_tests_created_at", "created_at"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scenario: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    location_description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    status: Mapped[FieldTestStatus] = mapped_column(
        SAEnum(FieldTestStatus, name="fieldteststatus"),
        default=FieldTestStatus.PLANNED,
        nullable=False,
    )

    # Clearly labelled if this is demo/seed data
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    results: Mapped[list["FieldTestResult"]] = relationship(
        "FieldTestResult", back_populates="field_test", cascade="all, delete-orphan"
    )


class FieldTestResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "field_test_results"
    __table_args__ = (
        Index("ix_ftr_field_test_id", "field_test_id"),
    )

    field_test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("field_tests.id", ondelete="CASCADE"), nullable=False
    )

    participant_identifier: Mapped[str] = mapped_column(String(100), nullable=False)  # anonymised
    event_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    success: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    response_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Survey
    user_satisfaction_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1–5
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    field_test: Mapped["FieldTest"] = relationship("FieldTest", back_populates="results")
