"""tests/experiments/sms_alert_experiment.py — Experiment 9: SMS delivery."""
from __future__ import annotations

import logging, time
import numpy as np
from tests.experiments.base_runner import BaseExperimentRunner, ExperimentReport, ResultCategory

logger = logging.getLogger(__name__)


class SmsAlertExperiment(BaseExperimentRunner):
    """Experiment 9: SMS alert delivery latency and success rate."""
    experiment_name = "sms_alert_experiment"

    async def run(self) -> ExperimentReport:
        from app.config import settings
        if not settings.SMS_MOCK_MODE and not settings.SMS_ACCOUNT_SID:
            self.report.status = "NOT_RUN"
            note = "SMS_ACCOUNT_SID not configured and SMS_MOCK_MODE is false."
            self.report.error_message = note
            self.report.add_metric("latency_ms", None, "ms", ResultCategory.NOT_RUN, notes=note)
            return self.report

        from app.services.communication.sms_provider import get_sms_provider
        provider = get_sms_provider()
        latencies, successes = [], []
        n = 10

        for i in range(n):
            t0 = time.perf_counter()
            result = await provider.send_sms("+910000000000", f"EMERGENCY TEST #{i}")
            elapsed = (time.perf_counter() - t0) * 1000
            latencies.append(elapsed)
            successes.append(1 if result.success else 0)

        cat = ResultCategory.SIMULATED if settings.SMS_MOCK_MODE else ResultCategory.ACTUAL
        self.report.add_metric("mean_latency_ms", float(np.mean(latencies)), "ms", cat)
        self.report.add_metric("p95_latency_ms", float(np.percentile(latencies, 95)), "ms", cat)
        self.report.add_metric("success_rate", float(np.mean(successes)) * 100, "%", cat)
        self.report.status = "COMPLETED"
        if settings.SMS_MOCK_MODE:
            self.report.notes = "MOCK MODE — not real SMS delivery"
        return self.report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    SmsAlertExperiment().execute()
