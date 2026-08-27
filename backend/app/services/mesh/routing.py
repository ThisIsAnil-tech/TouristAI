"""
app/services/mesh/routing.py — MeshRoutingService.

Loads mesh graph from DB, runs A*, creates MeshPacket records.
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mesh import MeshEdge, MeshNode, MeshPacket, MeshPacketStatus
from app.models.sos import SosEvent
from app.services.mesh.astar import AStarRouter, GraphEdge, GraphNode

logger = logging.getLogger(__name__)
_router = AStarRouter()


@dataclass
class RoutingResult:
    success: bool
    packet_id: Optional[uuid.UUID]
    hop_count: int
    total_cost: float
    route_path: List[str]   # node IDs as strings
    gateway_id: Optional[uuid.UUID]
    route_quality: float
    latency_ms: Optional[float]
    error: Optional[str]


class MeshRoutingService:
    """
    End-to-end mesh routing:
      1. Load all active nodes/edges from DB.
      2. Run A* to nearest gateway.
      3. Persist MeshPacket record.
    """

    async def route_emergency(
        self,
        sos_event: SosEvent,
        db: AsyncSession,
        source_node_id: Optional[uuid.UUID] = None,
    ) -> RoutingResult:
        """Route an SOS packet through the mesh to a gateway."""
        import time
        start = time.perf_counter()

        # ── Load graph ────────────────────────────────────────────────────
        nodes, edges, gateway_ids = await self._load_graph(db)

        if not nodes:
            return RoutingResult(False, None, 0, 0, [], None, 0.0, None,
                                 "No mesh nodes available")
        if not gateway_ids:
            return RoutingResult(False, None, 0, 0, [], None, 0.0, None,
                                 "No gateway nodes available")

        # ── Find source node ───────────────────────────────────────────────
        if source_node_id is None:
            source_node_id = await self._find_nearest_node(db, sos_event)

        if source_node_id is None or source_node_id not in nodes:
            return RoutingResult(False, None, 0, 0, [], None, 0.0, None,
                                 "Cannot identify source mesh node for this SOS event")

        # ── Run A* ────────────────────────────────────────────────────────
        result = _router.find_route(source_node_id, nodes, edges, gateway_ids)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # ── Persist packet ─────────────────────────────────────────────────
        packet = MeshPacket(
            sos_event_id=sos_event.id,
            source_node_id=source_node_id,
            destination_node_id=result.gateway_id,
            payload=json.dumps({"sos_event_id": str(sos_event.id),
                                "user_id": str(sos_event.user_id),
                                "latitude": sos_event.latitude,
                                "longitude": sos_event.longitude}),
            route_path=json.dumps([str(n) for n in result.path]),
            hop_count=result.hop_count,
            total_cost=result.total_cost,
            status=MeshPacketStatus.DELIVERED if result.success else MeshPacketStatus.FAILED,
            delivered_at=datetime.now(timezone.utc) if result.success else None,
            latency_ms=elapsed_ms,
        )
        db.add(packet)
        await db.flush()

        logger.info(
            "Mesh routing SOS %s: success=%s hops=%d latency=%.1fms",
            sos_event.id, result.success, result.hop_count, elapsed_ms
        )

        return RoutingResult(
            success=result.success,
            packet_id=packet.id,
            hop_count=result.hop_count,
            total_cost=result.total_cost,
            route_path=[str(n) for n in result.path],
            gateway_id=result.gateway_id,
            route_quality=result.route_quality,
            latency_ms=elapsed_ms,
            error=None if result.success else result.details,
        )

    async def get_graph_stats(self, db: AsyncSession) -> dict:
        nodes, edges, gateways = await self._load_graph(db)
        total_edges = sum(len(e) for e in edges.values())
        return {
            "total_nodes": len(nodes),
            "total_edges": total_edges,
            "gateway_count": len(gateways),
            "tourist_devices": sum(1 for n in nodes.values() if not n.is_gateway),
        }

    @staticmethod
    async def _load_graph(
        db: AsyncSession,
    ) -> tuple[Dict[uuid.UUID, GraphNode], Dict[uuid.UUID, List[GraphEdge]], Set[uuid.UUID]]:
        node_result = await db.scalars(
            select(MeshNode).where(MeshNode.is_active == True)
        )
        db_nodes = node_result.all()

        nodes: Dict[uuid.UUID, GraphNode] = {
            n.id: GraphNode(
                node_id=n.id,
                latitude=n.latitude,
                longitude=n.longitude,
                is_gateway=n.is_gateway,
                battery_pct=n.battery_pct,
            )
            for n in db_nodes
        }
        gateway_ids: Set[uuid.UUID] = {n.id for n in db_nodes if n.is_gateway}

        edge_result = await db.scalars(
            select(MeshEdge).where(MeshEdge.is_active == True)
        )
        db_edges = edge_result.all()

        edges: Dict[uuid.UUID, List[GraphEdge]] = {}
        for e in db_edges:
            edges.setdefault(e.source_node_id, []).append(
                GraphEdge(
                    source_id=e.source_node_id,
                    target_id=e.target_node_id,
                    hop_cost=e.hop_cost,
                    signal_quality=e.signal_quality or 1.0,
                    link_reliability=e.link_reliability or 1.0,
                )
            )

        return nodes, edges, gateway_ids

    @staticmethod
    async def _find_nearest_node(
        db: AsyncSession,
        sos_event: SosEvent,
    ) -> Optional[uuid.UUID]:
        """Find the active mesh node nearest to the SOS event location."""
        if sos_event.latitude is None:
            result = await db.scalar(
                select(MeshNode.id).where(MeshNode.is_active == True).limit(1)
            )
            return result

        node_result = await db.scalars(
            select(MeshNode).where(
                MeshNode.is_active == True,
                MeshNode.latitude.isnot(None),
            )
        )
        nodes = node_result.all()
        if not nodes:
            return None

        from app.services.gps.haversine import GpsPoint, haversine_distance
        sos_point = GpsPoint(sos_event.latitude, sos_event.longitude)
        best = min(
            nodes,
            key=lambda n: haversine_distance(sos_point, GpsPoint(n.latitude, n.longitude))
        )
        return best.id
