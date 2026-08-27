"""app/models/blockchain.py — Blockchain transactions and emergency access grants."""
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


class BlockchainTxType(str, PyEnum):
    REGISTER_IDENTITY = "REGISTER_IDENTITY"
    GRANT_ACCESS = "GRANT_ACCESS"
    REVOKE_ACCESS = "REVOKE_ACCESS"
    VERIFY_IDENTITY = "VERIFY_IDENTITY"


class BlockchainTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "blockchain_transactions"
    __table_args__ = (
        Index("ix_blockchain_tx_user_id", "user_id"),
        Index("ix_blockchain_tx_type", "tx_type"),
        Index("ix_blockchain_tx_hash", "tx_hash"),
    )

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    tx_type: Mapped[BlockchainTxType] = mapped_column(
        SAEnum(BlockchainTxType, name="blockchaintxtype"), nullable=False
    )

    # Real on-chain data — never fake
    tx_hash: Mapped[Optional[str]] = mapped_column(String(66), nullable=True, index=True)
    block_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gas_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)

    # Latency for research experiment
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Identity hash that was submitted (public info — not personal data)
    identity_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user: Mapped[Optional["User"]] = relationship("User")


class EmergencyAccessGrant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "emergency_access_grants"
    __table_args__ = (
        Index("ix_eag_sos_event_id", "sos_event_id"),
        Index("ix_eag_responder_id", "responder_id"),
        Index("ix_eag_is_active", "is_active"),
    )

    sos_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sos_events.id", ondelete="CASCADE"), nullable=False
    )
    responder_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("responders.id", ondelete="CASCADE"), nullable=False
    )
    tourist_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Blockchain grant details
    grant_tx_hash: Mapped[Optional[str]] = mapped_column(String(66), nullable=True)
    revoke_tx_hash: Mapped[Optional[str]] = mapped_column(String(66), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revocation_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    sos_event: Mapped["SosEvent"] = relationship("SosEvent", back_populates="emergency_access_grants")
    responder: Mapped["Responder"] = relationship("Responder", back_populates="emergency_access_grants")
