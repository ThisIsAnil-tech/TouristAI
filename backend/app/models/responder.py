"""app/models/responder.py — Emergency responder model."""
from __future__ import annotations

import uuid
from typing import Optional, List

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Responder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "responders"
    __table_args__ = (
        Index("ix_responders_user_id", "user_id"),
        Index("ix_responders_is_available", "is_available"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Professional info
    badge_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, unique=True)
    organization: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    specialization: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Status
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Current location
    current_latitude: Mapped[Optional[float]] = mapped_column(nullable=True)
    current_longitude: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User")
    emergency_access_grants: Mapped[List["EmergencyAccessGrant"]] = relationship(
        "EmergencyAccessGrant", back_populates="responder"
    )
