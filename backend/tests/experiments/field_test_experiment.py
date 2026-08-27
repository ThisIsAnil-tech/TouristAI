"""tests/experiments/field_test_experiment.py — Experiment 13: Field Test Results."""
from __future__ import annotations

import logging
from tests.experiments.base_runner import BaseExperimentRunner, ExperimentReport, ResultCategory

logger = logging.getLogger(__name__)


class FieldTestExperiment(BaseExperimentRunner):
    """
    Experiment 13: Field test analysis from real participant data.

    Reads FieldTestResult records from the database.
    All field test data must be collected from real participants.
    """
    experiment_name = "field_test_experiment"

    async def run(self) -> ExperimentReport:
        try:
            from app.database import get_db_context
            from app.models.field_test import FieldTest, FieldTestResult, FieldTestStatus
            from sqlalchemy import select, func
            import numpy as np

            async with get_db_context() as db:
                # Get completed non-demo field tests only
                tests_result = await db.scalars(
                    select(FieldTest).where(
                        FieldTest.status == FieldTestStatus.COMPLETED,
                        FieldTest.is_demo == False,
                    )
                )
                tests = tests_result.all()

                if not tests:
                    self.report.status = "NOT_RUN"
                    note = (
                        "No completed (non-demo) field tests found. "
                        "Conduct real field trials with participants and mark is_demo=False."
                    )
                    self.report.error_message = note
                    self.report.add_metric("success_rate", None, "%", ResultCategory.NOT_RUN, notes=note)
                    return self.report

                # Aggregate across all completed field tests
                all_success = []
                all_response_times = []
                all_satisfaction = []
                total_participants = 0

                for ft in tests:
                    results_q = await db.scalars(
                        select(FieldTestResult).where(FieldTestResult.field_test_id == ft.id)
                    )
                    results = results_q.all()
                    for r in results:
                        total_participants += 1
                        if r.success is not None:
                            all_success.append(1 if r.success else 0)
                        if r.response_time_ms is not None:
                            all_response_times.append(r.response_time_ms)
                        if r.user_satisfaction_score is not None:
                            all_satisfaction.append(r.user_satisfaction_score)

                cat = ResultCategory.ACTUAL
                self.report.add_metric("n_field_tests", float(len(tests)), "tests", cat)
                self.report.add_metric("total_participants", float(total_participants), "participants", cat)

                if all_success:
                    self.report.add_metric("success_rate", float(np.mean(all_success)) * 100, "%", cat,
                                           notes=f"n={len(all_success)}")
                if all_response_times:
                    self.report.add_metric("mean_response_time_ms", float(np.mean(all_response_times)), "ms", cat)
                    self.report.add_metric("p90_response_time_ms", float(np.percentile(all_response_times, 90)), "ms", cat)
                if all_satisfaction:
                    self.report.add_metric("mean_satisfaction_score", float(np.mean(all_satisfaction)), "/5", cat,
                                           notes=f"1=worst, 5=best, n={len(all_satisfaction)}")

            self.report.status = "COMPLETED"
            self.report.notes = "Real participant field test data only (is_demo=False)"

        except Exception as exc:
            self.report.status = "NOT_RUN"
            self.report.error_message = f"Database unavailable: {exc}"
            self.report.add_metric("success_rate", None, "%", ResultCategory.NOT_RUN)

        return self.report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    FieldTestExperiment().execute()
