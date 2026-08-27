"""
app/services/mesh/astar.py — A* routing algorithm for mesh network.

Implements actual A* on the mesh node/edge graph stored in PostgreSQL.

Cost function (configurable):
  edge_cost = hop_cost / (signal_quality * link_reliability)

Heuristic:
  h(n) = Haversine distance from n to gateway / avg_range_m

Returns path, total cost, hop count, gateway node, route quality.
"""
from __future__ import annotations

import heapq
import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID

from app.services.gps.haversine import GpsPoint, haversine_distance

logger = logging.getLogger(__name__)

_DEFAULT_SIGNAL = 1.0
_DEFAULT_RELIABILITY = 1.0
_AVG_RANGE_M = 100.0  # Estimated Bluetooth/mesh range


@dataclass
class GraphNode:
    node_id: UUID
    latitude: Optional[float]
    longitude: Optional[float]
    is_gateway: bool
    battery_pct: Optional[int] = None

    @property
    def gps_point(self) -> Optional[GpsPoint]:
        if self.latitude is not None and self.longitude is not None:
            return GpsPoint(self.latitude, self.longitude)
        return None


@dataclass
class GraphEdge:
    source_id: UUID
    target_id: UUID
    hop_cost: float = 1.0
    signal_quality: float = 1.0
    link_reliability: float = 1.0

    @property
    def cost(self) -> float:
        """Composite edge cost — lower is better."""
        sq = max(0.01, self.signal_quality)
        lr = max(0.01, self.link_reliability)
        return self.hop_cost / (sq * lr)


@dataclass
class AStarResult:
    success: bool
    path: List[UUID]           # Ordered list of node IDs from source to gateway
    total_cost: float
    hop_count: int
    gateway_id: Optional[UUID]
    route_quality: float        # 0.0–1.0 (1.0 = optimal)
    details: str


# A* priority queue entry
@dataclass(order=True)
class _PQEntry:
    f_score: float
    node_id: UUID = field(compare=False)


class AStarRouter:
    """
    A* shortest-path routing on the mesh network graph.

    Works purely with in-memory GraphNode / GraphEdge objects
    (built from DB records by MeshRoutingService).
    """

    def find_route(
        self,
        source_id: UUID,
        nodes: Dict[UUID, GraphNode],
        edges: Dict[UUID, List[GraphEdge]],
        gateway_ids: Set[UUID],
    ) -> AStarResult:
        """
        Run A* from source_id to the nearest gateway node.

        Args:
            source_id: Starting node (tourist's device).
            nodes: All known mesh nodes keyed by ID.
            edges: Adjacency list keyed by source node ID.
            gateway_ids: Set of gateway node IDs (targets).

        Returns:
            AStarResult with path, cost, hops, quality.
        """
        if not nodes:
            return AStarResult(
                success=False, path=[], total_cost=float("inf"),
                hop_count=0, gateway_id=None, route_quality=0.0,
                details="No mesh nodes available"
            )

        if source_id in gateway_ids:
            return AStarResult(
                success=True, path=[source_id], total_cost=0.0,
                hop_count=0, gateway_id=source_id, route_quality=1.0,
                details="Source is a gateway"
            )

        if not gateway_ids:
            return AStarResult(
                success=False, path=[], total_cost=float("inf"),
                hop_count=0, gateway_id=None, route_quality=0.0,
                details="No gateways available in mesh"
            )

        # ── Nearest gateway location for heuristic ─────────────────────────
        target_gateway = self._nearest_gateway_to_source(source_id, nodes, gateway_ids)

        # ── A* initialisation ──────────────────────────────────────────────
        open_set: List[_PQEntry] = []
        heapq.heappush(open_set, _PQEntry(f_score=0.0, node_id=source_id))

        came_from: Dict[UUID, UUID] = {}
        g_score: Dict[UUID, float] = {source_id: 0.0}
        closed_set: Set[UUID] = set()

        while open_set:
            current_entry = heapq.heappop(open_set)
            current_id = current_entry.node_id

            if current_id in closed_set:
                continue
            closed_set.add(current_id)

            # ── Goal check ────────────────────────────────────────────────
            if current_id in gateway_ids:
                path = self._reconstruct_path(came_from, current_id)
                total_cost = g_score[current_id]
                quality = self._route_quality(path, total_cost, nodes)
                logger.info(
                    "A* route found: %d hops, cost=%.3f, quality=%.2f",
                    len(path) - 1, total_cost, quality
                )
                return AStarResult(
                    success=True,
                    path=path,
                    total_cost=total_cost,
                    hop_count=len(path) - 1,
                    gateway_id=current_id,
                    route_quality=quality,
                    details=f"A* route: {len(path)-1} hops, cost={total_cost:.3f}",
                )

            # ── Expand neighbours ─────────────────────────────────────────
            for edge in edges.get(current_id, []):
                neighbour_id = edge.target_id
                if neighbour_id in closed_set:
                    continue

                tentative_g = g_score[current_id] + edge.cost

                if tentative_g < g_score.get(neighbour_id, float("inf")):
                    came_from[neighbour_id] = current_id
                    g_score[neighbour_id] = tentative_g
                    h = self._heuristic(neighbour_id, target_gateway, nodes)
                    f = tentative_g + h
                    heapq.heappush(open_set, _PQEntry(f_score=f, node_id=neighbour_id))

        return AStarResult(
            success=False, path=[], total_cost=float("inf"),
            hop_count=0, gateway_id=None, route_quality=0.0,
            details="No route found to any gateway"
        )

    def _heuristic(
        self,
        node_id: UUID,
        target_node: Optional[GraphNode],
        nodes: Dict[UUID, GraphNode],
    ) -> float:
        """Euclidean distance heuristic (in mesh hops)."""
        if target_node is None:
            return 0.0
        node = nodes.get(node_id)
        if node is None or node.gps_point is None or target_node.gps_point is None:
            return 0.0
        dist_m = haversine_distance(node.gps_point, target_node.gps_point)
        return dist_m / _AVG_RANGE_M  # Estimated hop count

    @staticmethod
    def _nearest_gateway_to_source(
        source_id: UUID,
        nodes: Dict[UUID, GraphNode],
        gateway_ids: Set[UUID],
    ) -> Optional[GraphNode]:
        source = nodes.get(source_id)
        if source is None or source.gps_point is None:
            return next((nodes[gid] for gid in gateway_ids if gid in nodes), None)
        best = None
        best_dist = float("inf")
        for gid in gateway_ids:
            gnode = nodes.get(gid)
            if gnode and gnode.gps_point:
                d = haversine_distance(source.gps_point, gnode.gps_point)
                if d < best_dist:
                    best_dist = d
                    best = gnode
        return best

    @staticmethod
    def _reconstruct_path(came_from: Dict[UUID, UUID], current: UUID) -> List[UUID]:
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path

    @staticmethod
    def _route_quality(
        path: List[UUID],
        total_cost: float,
        nodes: Dict[UUID, GraphNode],
    ) -> float:
        """Quality metric: 1.0 = single hop to gateway, decreases with cost."""
        if not path or total_cost <= 0:
            return 1.0
        hop_count = len(path) - 1
        # Penalise by hop count and cost
        return max(0.0, 1.0 - (hop_count * 0.1) - (total_cost * 0.05))
