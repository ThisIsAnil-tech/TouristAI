"""tests/experiments/mobile_performance_experiment.py — Experiment 10: Mobile Performance."""
from __future__ import annotations

import logging
from tests.experiments.base_runner import BaseExperimentRunner, ExperimentReport, ResultCategory

logger = logging.getLogger(__name__)


class MobilePerformanceExperiment(BaseExperimentRunner):
    """
    Experiment 10: Mobile application performance metrics.

    Metrics come from MobileTelemetry submitted by real devices.
    If no telemetry exists, marked NOT_RUN.
    """
    experiment_name = "mobile_performance_experiment"

    async def run(self) -> ExperimentReport:
        try:
            from app.database import get_db_context
            from app.models.telemetry import MobileTelemetry
            from sqlalchemy import select, func
            import numpy as np

            async with get_db_context() as db:
                result = await db.execute(
                    select(
                        func.count(MobileTelemetry.id).label("count"),
                        func.avg(MobileTelemetry.fps).label("avg_fps"),
                        func.avg(MobileTelemetry.cpu_pct).label("avg_cpu"),
                        func.avg(MobileTelemetry.ram_mb).label("avg_ram"),
                        func.avg(MobileTelemetry.battery_drain_per_hour).label("avg_drain"),
                        func.avg(MobileTelemetry.inference_time_ms).label("avg_inf"),
                    )
                )
                row = result.one()

                if not row.count or row.count == 0:
                    self.report.status = "NOT_RUN"
                    note = "No mobile telemetry in database. Deploy app and collect real device data."
                    self.report.error_message = note
                    self.report.add_metric("avg_fps", None, "fps", ResultCategory.NOT_RUN, notes=note)
                    return self.report

                cat = ResultCategory.ACTUAL
                self.report.add_metric("avg_fps", float(row.avg_fps or 0), "fps", cat, notes=f"n={row.count}")
                self.report.add_metric("avg_cpu_pct", float(row.avg_cpu or 0), "%", cat)
                self.report.add_metric("avg_ram_mb", float(row.avg_ram or 0), "MB", cat)
                self.report.add_metric("avg_battery_drain_per_hour", float(row.avg_drain or 0), "%/hr", cat)
                self.report.add_metric("avg_inference_time_ms", float(row.avg_inf or 0), "ms", cat)
                self.report.add_metric("n_telemetry_records", float(row.count), "records", cat)

            self.report.status = "COMPLETED"
            self.report.notes = "Data from real device telemetry submissions"

        except Exception as exc:
            self.report.status = "NOT_RUN"
            self.report.error_message = f"Database unavailable: {exc}"
            self.report.add_metric("avg_fps", None, "fps", ResultCategory.NOT_RUN,
                                   notes="Database not available for experiment")

        return self.report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    MobilePerformanceExperiment().execute()
