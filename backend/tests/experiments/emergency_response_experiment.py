"""tests/experiments/emergency_response_experiment.py — Experiment 12."""
from __future__ import annotations

import logging
from tests.experiments.base_runner import BaseExperimentRunner, ExperimentReport, ResultCategory

logger = logging.getLogger(__name__)


class EmergencyResponseExperiment(BaseExperimentRunner):
    """
    Experiment 12: End-to-end emergency response time analysis.

    Reads real SOS event timelines from the database:
      triggered_at → acknowledged_at → resolved_at
    """
    experiment_name = "emergency_response_experiment"

    async def run(self) -> ExperimentReport:
        try:
            from app.database import get_db_context
            from app.models.sos import SosEvent, SosStatus
            from sqlalchemy import select
            import numpy as np

            async with get_db_context() as db:
                result = await db.scalars(
                    select(SosEvent).where(
                        SosEvent.status.in_([SosStatus.RESOLVED, SosStatus.ACKNOWLEDGED]),
                        SosEvent.acknowledged_at.isnot(None),
                    ).limit(500)
                )
                events = result.all()

                if not events:
                    self.report.status = "NOT_RUN"
                    note = "No resolved SOS events with acknowledgment timestamps in database."
                    self.report.error_message = note
                    self.report.add_metric("acknowledgment_time_s", None, "s", ResultCategory.NOT_RUN, notes=note)
                    return self.report

                ack_times = [(e.acknowledged_at - e.triggered_at).total_seconds()
                             for e in events if e.acknowledged_at and e.triggered_at]
                res_times = [(e.resolved_at - e.triggered_at).total_seconds()
                             for e in events if e.resolved_at and e.triggered_at]

                if ack_times:
                    self.report.add_metric("mean_acknowledgment_time_s", float(np.mean(ack_times)), "s", ResultCategory.ACTUAL, notes=f"n={len(ack_times)}")
                    self.report.add_metric("p90_acknowledgment_time_s", float(np.percentile(ack_times, 90)), "s", ResultCategory.ACTUAL)
                if res_times:
                    self.report.add_metric("mean_resolution_time_s", float(np.mean(res_times)), "s", ResultCategory.ACTUAL, notes=f"n={len(res_times)}")

                # Trigger type breakdown
                from collections import Counter
                trigger_counts = Counter(e.trigger for e in events)
                for trigger, count in trigger_counts.items():
                    self.report.add_metric(f"trigger_{trigger.lower()}_count", float(count), "events", ResultCategory.ACTUAL)

            self.report.status = "COMPLETED"

        except Exception as exc:
            self.report.status = "NOT_RUN"
            self.report.error_message = f"Database unavailable: {exc}"
            self.report.add_metric("acknowledgment_time_s", None, "s", ResultCategory.NOT_RUN)

        return self.report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    EmergencyResponseExperiment().execute()
