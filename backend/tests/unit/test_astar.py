"""tests/unit/test_astar.py — Unit tests for A* mesh routing."""
import uuid
import pytest
from app.services.mesh.astar import AStarRouter, GraphNode, GraphEdge, AStarResult


def _make_node(lat, lon, is_gateway=False) -> tuple[uuid.UUID, GraphNode]:
    nid = uuid.uuid4()
    return nid, GraphNode(node_id=nid, latitude=lat, longitude=lon, is_gateway=is_gateway)


class TestAStarRouter:
    def setup_method(self):
        self.router = AStarRouter()

    def test_direct_to_gateway(self):
        """Source node directly connects to gateway."""
        src_id, src = _make_node(10.0, 76.0)
        gw_id, gw = _make_node(10.001, 76.001, is_gateway=True)

        nodes = {src_id: src, gw_id: gw}
        edges = {
            src_id: [GraphEdge(source_id=src_id, target_id=gw_id, hop_cost=1.0)],
        }
        result = self.router.find_route(src_id, nodes, edges, {gw_id})

        assert result.success
        assert result.hop_count == 1
        assert result.path == [src_id, gw_id]
        assert result.gateway_id == gw_id

    def test_multi_hop_route(self):
        """A* finds shortest path through intermediate nodes."""
        ids = [uuid.uuid4() for _ in range(4)]
        a, b, c, gw = ids
        nodes = {
            a: GraphNode(a, 10.0, 76.0, False),
            b: GraphNode(b, 10.001, 76.001, False),
            c: GraphNode(c, 10.002, 76.002, False),
            gw: GraphNode(gw, 10.003, 76.003, True),
        }
        edges = {
            a: [GraphEdge(a, b, hop_cost=1.0), GraphEdge(a, c, hop_cost=5.0)],
            b: [GraphEdge(b, gw, hop_cost=1.0)],
            c: [GraphEdge(c, gw, hop_cost=1.0)],
        }
        result = self.router.find_route(a, nodes, edges, {gw})
        assert result.success
        assert result.hop_count == 2
        assert result.path == [a, b, gw]

    def test_no_gateways(self):
        src_id, src = _make_node(10.0, 76.0)
        result = self.router.find_route(src_id, {src_id: src}, {}, set())
        assert not result.success

    def test_source_is_gateway(self):
        src_id, src = _make_node(10.0, 76.0, is_gateway=True)
        result = self.router.find_route(src_id, {src_id: src}, {}, {src_id})
        assert result.success
        assert result.hop_count == 0

    def test_disconnected_graph(self):
        src_id, src = _make_node(10.0, 76.0)
        gw_id, gw = _make_node(20.0, 80.0, is_gateway=True)
        # No edge between src and gw
        nodes = {src_id: src, gw_id: gw}
        result = self.router.find_route(src_id, nodes, {}, {gw_id})
        assert not result.success
