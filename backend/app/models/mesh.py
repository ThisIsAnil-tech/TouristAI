"""app/models/mesh.py — Mesh network nodes, edges, packets."""
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


class MeshNodeType(str, PyEnum):
    TOURIST_DEVICE = "TOURIST_DEVICE"
    GATEWAY = "GATEWAY"
    RELAY = "RELAY"


class MeshPacketStatus(str, PyEnum):
    QUEUED = "QUEUED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


class MeshNode(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A node in the offline mesh network."""
    __tablename__ = "mesh_nodes"
    __table_args__ = (
        Index("ix_mesh_nodes_zone_id", "zone_id"),
        Index("ix_mesh_nodes_is_gateway", "is_gateway"),
        Index("ix_mesh_nodes_is_active", "is_active"),
    )

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("geographic_zones.id", ondelete="SET NULL"), nullable=True
    )

    node_type: Mapped[MeshNodeType] = mapped_column(
        SAEnum(MeshNodeType, name="meshnodetype"),
        default=MeshNodeType.TOURIST_DEVICE,
        nullable=False,
    )
    device_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    is_gateway: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    battery_pct: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    zone: Mapped[Optional["GeographicZone"]] = relationship("GeographicZone", back_populates="mesh_nodes")


class MeshEdge(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A directed edge between two mesh nodes."""
    __tablename__ = "mesh_edges"
    __table_args__ = (
        Index("ix_mesh_edges_source_id", "source_node_id"),
        Index("ix_mesh_edges_target_id", "target_node_id"),
    )

    source_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mesh_nodes.id", ondelete="CASCADE"), nullable=False
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mesh_nodes.id", ondelete="CASCADE"), nullable=False
    )

    # Edge cost factors
    signal_quality: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-1
    hop_cost: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    link_reliability: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-1
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    source_node: Mapped["MeshNode"] = relationship("MeshNode", foreign_keys=[source_node_id])
    target_node: Mapped["MeshNode"] = relationship("MeshNode", foreign_keys=[target_node_id])


class MeshPacket(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A packet being routed through the mesh network."""
    __tablename__ = "mesh_packets"
    __table_args__ = (
        Index("ix_mesh_packets_sos_event_id", "sos_event_id"),
        Index("ix_mesh_packets_status", "status"),
    )

    sos_event_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sos_events.id", ondelete="SET NULL"), nullable=True
    )
    source_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mesh_nodes.id", ondelete="CASCADE"), nullable=False
    )
    destination_node_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mesh_nodes.id", ondelete="SET NULL"), nullable=True
    )

    payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    route_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of node IDs
    hop_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    status: Mapped[MeshPacketStatus] = mapped_column(
        SAEnum(MeshPacketStatus, name="meshpacketstatus"),
        default=MeshPacketStatus.QUEUED,
        nullable=False,
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
