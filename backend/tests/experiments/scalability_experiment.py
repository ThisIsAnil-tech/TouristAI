"""tests/experiments/scalability_experiment.py — Experiment 14: System Scalability."""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from tests.experiments.base_runner import BaseExperimentRunner, ExperimentReport, ResultCategory

logger = logging.getLogger(__name__)


class ScalabilityExperiment(BaseExperimentRunner):
    """
    Experiment 14: System scalability under concurrent load.

    Tests:
      - Haversine calculation throughput (pure compute)
      - GPS anomaly detection throughput
      - Risk score calculation throughput
      - Concurrent request simulation
    """
    experiment_name = "scalability_experiment"

    async def run(self) -> ExperimentReport:
        import numpy as np
        from app.services.gps.haversine import GpsPoint, haversine_distance
        from app.services.risk.adaptive_threshold import AdaptiveThresholdController
        from app.services.mesh.astar import AStarRouter, GraphNode, GraphEdge

        # ── 1. Haversine throughput ────────────────────────────────────────
        p1, p2 = GpsPoint(10.0, 76.0), GpsPoint(11.0, 77.0)
        n = 100_000
        t0 = time.perf_counter()
        for _ in range(n):
            haversine_distance(p1, p2)
        elapsed = (time.perf_counter() - t0)
        throughput = n / elapsed
        self.report.add_metric(
            "haversine_throughput", throughput, "ops/sec",
            ResultCategory.ACTUAL, notes=f"n={n} sequential calls"
        )
        self.report.add_metric(
            "haversine_mean_us", elapsed / n * 1_000_000, "μs",
            ResultCategory.ACTUAL
        )

        # ── 2. Adaptive threshold throughput ──────────────────────────────
        ctrl = AdaptiveThresholdController()
        t0 = time.perf_counter()
        for i in range(n):
            ctrl.calculate(float(i % 10 + 1))
        elapsed = time.perf_counter() - t0
        self.report.add_metric(
            "threshold_calc_throughput", n / elapsed, "ops/sec",
            ResultCategory.ACTUAL, notes=f"n={n}"
        )

        # ── 3. Concurrent coroutine simulation ────────────────────────────
        async def _simulate_gps_submit():
            from app.services.gps.haversine import haversine_distance, GpsPoint
            import random
            p = GpsPoint(10.0 + random.uniform(-1, 1), 76.0 + random.uniform(-1, 1))
            haversine_distance(p1, p)
            await asyncio.sleep(0)  # Yield event loop

        for concurrency in [10, 50, 100, 500]:
            t0 = time.perf_counter()
            await asyncio.gather(*[_simulate_gps_submit() for _ in range(concurrency)])
            elapsed = (time.perf_counter() - t0) * 1000
            self.report.add_metric(
                f"concurrent_{concurrency}_ms", elapsed, "ms",
                ResultCategory.ACTUAL,
                notes=f"{concurrency} concurrent GPS submissions (simulated async)"
            )

        # ── 4. A* routing throughput ──────────────────────────────────────
        import random
        random.seed(99)
        router = AStarRouter()
        n_nodes = 50
        node_ids = [uuid.uuid4() for _ in range(n_nodes)]
        nodes = {nid: GraphNode(nid, 10 + random.uniform(0, 1), 76 + random.uniform(0, 1), i < 5)
                 for i, nid in enumerate(node_ids)}
        gateway_ids = {node_ids[i] for i in range(5)}
        edges = {}
        for i, src in enumerate(node_ids):
            for tgt in node_ids[max(0, i-3):i] + node_ids[i+1:i+4]:
                edges.setdefault(src, []).append(
                    GraphEdge(src, tgt, 1.0, random.uniform(0.5, 1), random.uniform(0.7, 1))
                )

        non_gw = [n for n in node_ids if n not in gateway_ids]
        times_astar = []
        for _ in range(100):
            src = random.choice(non_gw)
            t0 = time.perf_counter()
            router.find_route(src, nodes, edges, gateway_ids)
            times_astar.append((time.perf_counter() - t0) * 1000)

        self.report.add_metric("astar_mean_ms", float(np.mean(times_astar)), "ms",
                               ResultCategory.ACTUAL, notes="n=100 trials, 50-node mesh")
        self.report.add_metric("astar_p99_ms", float(np.percentile(times_astar, 99)), "ms",
                               ResultCategory.ACTUAL)

        self.report.status = "COMPLETED"
        self.report.notes = "Pure compute scalability tests — no DB required"
        return self.report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ScalabilityExperiment().execute()
