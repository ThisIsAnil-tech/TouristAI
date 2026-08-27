"""tests/experiments/battery_experiment.py — Experiment 11: Battery Consumption."""
from __future__ import annotations

import logging
from tests.experiments.base_runner import BaseExperimentRunner, ExperimentReport, ResultCategory

logger = logging.getLogger(__name__)


class BatteryExperiment(BaseExperimentRunner):
    """
    Experiment 11: Battery consumption analysis.

    Sources real battery drain data from MobileTelemetry.
    If no real data, marked NOT_RUN.
    """
    experiment_name = "battery_experiment"

    async def run(self) -> ExperimentReport:
        try:
            from app.database import get_db_context
            from app.models.telemetry import MobileTelemetry
            from sqlalchemy import select, func
            import numpy as np

            async with get_db_context() as db:
                result = await db.scalars(
                    select(MobileTelemetry.battery_drain_per_hour)
                    .where(MobileTelemetry.battery_drain_per_hour.isnot(None))
                    .limit(1000)
                )
                drains = [d for d in result.all() if d is not None]

                if not drains:
                    self.report.status = "NOT_RUN"
                    note = "No battery_drain_per_hour data in MobileTelemetry. Requires real device runs."
                    self.report.error_message = note
                    self.report.add_metric("mean_drain_per_hour", None, "%/hr", ResultCategory.NOT_RUN, notes=note)
                    return self.report

                self.report.add_metric("mean_drain_per_hour", float(np.mean(drains)), "%/hr", ResultCategory.ACTUAL, notes=f"n={len(drains)}")
                self.report.add_metric("std_drain_per_hour", float(np.std(drains)), "%/hr", ResultCategory.ACTUAL)
                self.report.add_metric("max_drain_per_hour", float(np.max(drains)), "%/hr", ResultCategory.ACTUAL)
                self.report.add_metric("min_drain_per_hour", float(np.min(drains)), "%/hr", ResultCategory.ACTUAL)
                # Estimated device lifetime (assuming 100% battery start)
                avg = float(np.mean(drains))
                if avg > 0:
                    self.report.add_metric("estimated_lifetime_hours", 100.0 / avg, "hours", ResultCategory.ACTUAL)

            self.report.status = "COMPLETED"

        except Exception as exc:
            self.report.status = "NOT_RUN"
            self.report.error_message = f"Database unavailable: {exc}"
            self.report.add_metric("mean_drain_per_hour", None, "%/hr", ResultCategory.NOT_RUN)

        return self.report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    BatteryExperiment().execute()
