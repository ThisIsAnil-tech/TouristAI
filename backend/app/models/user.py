"""app/models/user.py — User, EmergencyContact, UserRole."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class UserRole(str, PyEnum):
    TOURIST = "TOURIST"
    RESPONDER = "RESPONDER"
    ADMIN = "ADMIN"


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("phone_number", name="uq_users_phone"),
        Index("ix_users_email", "email"),
        Index("ix_users_role", "role"),
    )

    # Identity
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Auth
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="userrole"), default=UserRole.TOURIST, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Encrypted sensitive fields (Fernet)
    encrypted_passport_number: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    encrypted_medical_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    nationality: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Blockchain identity hash (SHA-256 of canonical identity — safe to store)
    identity_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    blockchain_registered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Last known GPS
    last_latitude: Mapped[Optional[float]] = mapped_column(nullable=True)
    last_longitude: Mapped[Optional[float]] = mapped_column(nullable=True)
    last_location_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Refresh token hash (one active session)
    refresh_token_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    emergency_contacts: Mapped[List["EmergencyContact"]] = relationship(
        "EmergencyContact", back_populates="user", cascade="all, delete-orphan"
    )
    gps_readings: Mapped[List["GpsReading"]] = relationship(
        "GpsReading", back_populates="user", cascade="all, delete-orphan",
        lazy="dynamic",
    )
    sos_events: Mapped[List["SosEvent"]] = relationship(
        "SosEvent", back_populates="user", cascade="all, delete-orphan",
        lazy="dynamic",
    )
    audio_detections: Mapped[List["AudioDetection"]] = relationship(
        "AudioDetection", back_populates="user", lazy="dynamic"
    )
    telemetry: Mapped[List["MobileTelemetry"]] = relationship(
        "MobileTelemetry", back_populates="user", lazy="dynamic"
    )


class EmergencyContact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "emergency_contacts"
    __table_args__ = (
        Index("ix_emergency_contacts_user_id", "user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    relation_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notify_on_sos: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="emergency_contacts")
