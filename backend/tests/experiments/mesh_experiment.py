"""tests/experiments/mesh_experiment.py — Experiment 5: A* Mesh Routing."""
from __future__ import annotations

import logging
import time
import uuid
import random
import math
from tests.experiments.base_runner import BaseExperimentRunner, ExperimentReport, ResultCategory
import numpy as np

logger = logging.getLogger(__name__)


def _gen_mesh(n_nodes=20, n_gateways=3, seed=42):
    random.seed(seed)
    from app.services.mesh.astar import GraphNode, GraphEdge
    nodes, edges, gw_ids = {}, {}, set()
    node_ids = [uuid.uuid4() for _ in range(n_nodes)]

    for i, nid in enumerate(node_ids):
        is_gw = i < n_gateways
        nodes[nid] = GraphNode(
            node_id=nid,
            latitude=10.0 + random.uniform(0, 0.5),
            longitude=76.0 + random.uniform(0, 0.5),
            is_gateway=is_gw,
        )
        if is_gw:
            gw_ids.add(nid)

    # Connect nodes in a grid-like pattern
    for i, src_id in enumerate(node_ids):
        neighbors = node_ids[max(0, i-3): i] + node_ids[i+1: i+4]
        for tgt_id in neighbors:
            edges.setdefault(src_id, []).append(
                __import__('app.services.mesh.astar', fromlist=['GraphEdge']).GraphEdge(
                    source_id=src_id, target_id=tgt_id,
                    hop_cost=1.0,
                    signal_quality=random.uniform(0.5, 1.0),
                    link_reliability=random.uniform(0.7, 1.0),
                )
            )

    return nodes, edges, gw_ids, node_ids


class MeshExperiment(BaseExperimentRunner):
    """Experiment 5: A* Mesh Network Routing Performance."""
    experiment_name = "mesh_experiment"

    async def run(self) -> ExperimentReport:
        from app.services.mesh.astar import AStarRouter

        router = AStarRouter()
        nodes, edges, gw_ids, node_ids = _gen_mesh(n_nodes=20, n_gateways=3)
        non_gw_ids = [n for n in node_ids if n not in gw_ids]

        latencies, hop_counts, success_count = [], [], 0
        n_trials = 50

        for _ in range(n_trials):
            src_id = random.choice(non_gw_ids)
            t0 = time.perf_counter()
            result = router.find_route(src_id, nodes, edges, gw_ids)
            elapsed = (time.perf_counter() - t0) * 1000
            latencies.append(elapsed)
            if result.success:
                success_count += 1
                hop_counts.append(result.hop_count)

        self.report.add_metric("routing_success_rate", success_count / n_trials * 100, "%", ResultCategory.SIMULATED,
                               notes=f"n={n_nodes}, gateways={3}, trials={n_trials}")
        self.report.add_metric("mean_routing_latency_ms", float(np.mean(latencies)), "ms", ResultCategory.SIMULATED)
        self.report.add_metric("mean_hop_count", float(np.mean(hop_counts)) if hop_counts else 0, "hops", ResultCategory.SIMULATED)
        self.report.add_metric("max_hop_count", float(max(hop_counts)) if hop_counts else 0, "hops", ResultCategory.SIMULATED)

        # Scale test
        for n in [10, 50, 100]:
            big_nodes, big_edges, big_gw, big_ids = _gen_mesh(n_nodes=n, n_gateways=max(2, n//10))
            non_gw = [nid for nid in big_ids if nid not in big_gw]
            times = []
            for _ in range(10):
                src = random.choice(non_gw)
                t0 = time.perf_counter()
                router.find_route(src, big_nodes, big_edges, big_gw)
                times.append((time.perf_counter() - t0) * 1000)
            self.report.add_metric(f"latency_n{n}_ms", float(np.mean(times)), "ms", ResultCategory.SIMULATED,
                                   notes=f"Average over 10 trials, mesh size={n}")

        self.report.status = "COMPLETED"
        self.report.notes = "Simulated mesh topology — real mesh requires deployed hardware nodes"
        return self.report

n_nodes = 20


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    MeshExperiment().execute()
