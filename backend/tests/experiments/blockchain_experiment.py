"""tests/experiments/blockchain_experiment.py — Experiment 6: Blockchain Operations."""
from __future__ import annotations

import logging
import time
import os
from tests.experiments.base_runner import BaseExperimentRunner, ExperimentReport, ResultCategory

logger = logging.getLogger(__name__)
BLOCKCHAIN_AVAILABLE = os.getenv("BLOCKCHAIN_PROVIDER_URL") and os.getenv("BLOCKCHAIN_PRIVATE_KEY")


class BlockchainExperiment(BaseExperimentRunner):
    """Experiment 6: Blockchain Identity Registration Performance."""
    experiment_name = "blockchain_experiment"

    async def run(self) -> ExperimentReport:
        if not BLOCKCHAIN_AVAILABLE:
            note = (
                "Blockchain node not configured (BLOCKCHAIN_PROVIDER_URL + BLOCKCHAIN_PRIVATE_KEY). "
                "Start: docker compose up blockchain && python scripts/deploy_contract.py"
            )
            self.report.status = "NOT_RUN"
            self.report.error_message = note
            self.report.add_metric("registration_latency_ms", None, "ms", ResultCategory.NOT_RUN, notes=note)
            self.report.add_metric("gas_used", None, "gas", ResultCategory.NOT_RUN, notes=note)
            return self.report

        from app.config import settings
        if settings.BLOCKCHAIN_MOCK_MODE:
            # Mock mode — SIMULATED results
            self.report.add_metric("registration_latency_ms", 85.0, "ms", ResultCategory.SIMULATED,
                                   notes="Mock mode — not a real blockchain transaction")
            self.report.add_metric("gas_used", 21000.0, "gas", ResultCategory.SIMULATED,
                                   notes="Mock mode estimate")
            self.report.add_metric("grant_access_latency_ms", 45.0, "ms", ResultCategory.SIMULATED)
            self.report.add_metric("revoke_access_latency_ms", 40.0, "ms", ResultCategory.SIMULATED)
            self.report.status = "COMPLETED"
            self.report.notes = "MOCK MODE — run with real blockchain for ACTUAL results"
            return self.report

        try:
            from app.services.blockchain.identity_service import BlockchainIdentityService
            import uuid
            svc = BlockchainIdentityService()

            # Registration latency (10 trials)
            latencies, gas_values = [], []
            for _ in range(10):
                from app.models.user import User
                user = User(
                    id=uuid.uuid4(), email="test@exp.com", full_name="Test",
                    hashed_password="x", identity_hash="a" * 64
                )

                class FakeDB:
                    def add(self, _): pass
                    async def flush(self): pass

                t0 = time.perf_counter()
                result = await svc.register_identity(user, FakeDB())
                elapsed = (time.perf_counter() - t0) * 1000
                latencies.append(elapsed)
                if result.gas_used:
                    gas_values.append(result.gas_used)

            import numpy as np
            self.report.add_metric("registration_latency_mean_ms", float(np.mean(latencies)), "ms", ResultCategory.ACTUAL)
            self.report.add_metric("registration_latency_std_ms", float(np.std(latencies)), "ms", ResultCategory.ACTUAL)
            if gas_values:
                self.report.add_metric("gas_used_mean", float(np.mean(gas_values)), "gas", ResultCategory.ACTUAL)

            self.report.status = "COMPLETED"

        except Exception as exc:
            self.report.status = "FAILED"
            self.report.error_message = str(exc)

        return self.report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    BlockchainExperiment().execute()
