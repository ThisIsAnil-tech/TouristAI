"""tests/experiments/internet_alert_experiment.py — Experiment 8."""
from __future__ import annotations

import logging, os, time
import numpy as np
from tests.experiments.base_runner import BaseExperimentRunner, ExperimentReport, ResultCategory

logger = logging.getLogger(__name__)


class InternetAlertExperiment(BaseExperimentRunner):
    """Experiment 8: Internet alert delivery latency and success rate."""
    experiment_name = "internet_alert_experiment"

    async def run(self) -> ExperimentReport:
        from app.config import settings
        if not settings.ALERT_PROVIDER_URL and not settings.ALERT_MOCK_MODE:
            self.report.status = "NOT_RUN"
            note = "ALERT_PROVIDER_URL not configured and ALERT_MOCK_MODE is false."
            self.report.error_message = note
            self.report.add_metric("latency_ms", None, "ms", ResultCategory.NOT_RUN, notes=note)
            return self.report

        from app.services.communication.internet_provider import InternetAlertProvider
        provider = InternetAlertProvider()
        latencies, successes = [], []
        n = 10

        for i in range(n):
            t0 = time.perf_counter()
            result = await provider.send_alert(f"Test alert #{i}", "http://test-destination")
            elapsed = (time.perf_counter() - t0) * 1000
            latencies.append(elapsed)
            successes.append(1 if result.success else 0)

        cat = ResultCategory.ACTUAL if not settings.ALERT_MOCK_MODE else ResultCategory.SIMULATED
        self.report.add_metric("mean_latency_ms", float(np.mean(latencies)), "ms", cat)
        self.report.add_metric("p95_latency_ms", float(np.percentile(latencies, 95)), "ms", cat)
        self.report.add_metric("success_rate", float(np.mean(successes)) * 100, "%", cat)
        self.report.status = "COMPLETED"
        if settings.ALERT_MOCK_MODE:
            self.report.notes = "MOCK MODE — not real network calls"
        return self.report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    InternetAlertExperiment().execute()
