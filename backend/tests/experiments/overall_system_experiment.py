"""
tests/experiments/overall_system_experiment.py — Experiment 15: Overall System Summary.

Aggregates all 14 individual experiment results into one consolidated report.
This is the final master experiment that summarizes the research outcomes.
"""
from __future__ import annotations

import logging
from pathlib import Path
import json
from tests.experiments.base_runner import BaseExperimentRunner, ExperimentReport, ResultCategory

logger = logging.getLogger(__name__)

ALL_EXPERIMENTS = [
    "audio_experiment",
    "gps_experiment",
    "risk_experiment",
    "emergency_decision_experiment",
    "mesh_experiment",
    "blockchain_experiment",
    "edge_ai_experiment",
    "internet_alert_experiment",
    "sms_alert_experiment",
    "mobile_performance_experiment",
    "battery_experiment",
    "emergency_response_experiment",
    "field_test_experiment",
    "scalability_experiment",
]


class OverallSystemExperiment(BaseExperimentRunner):
    """
    Experiment 15: Overall System Evaluation.

    Aggregates key metrics from all 14 experiments.
    Runs all sub-experiments and collects top-level results.
    """
    experiment_name = "overall_system_experiment"

    def __init__(self, run_sub_experiments: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.run_sub_experiments = run_sub_experiments

    async def run(self) -> ExperimentReport:
        import importlib

        totals = {
            "completed": 0, "not_run": 0, "failed": 0,
            "actual_metrics": 0, "simulated_metrics": 0, "not_run_metrics": 0,
        }

        for exp_name in ALL_EXPERIMENTS:
            if self.run_sub_experiments:
                try:
                    module = importlib.import_module(f"tests.experiments.{exp_name}")
                    # Find the runner class
                    runner_class = None
                    for attr in dir(module):
                        obj = getattr(module, attr)
                        if (isinstance(obj, type) and
                                issubclass(obj, BaseExperimentRunner) and
                                obj is not BaseExperimentRunner):
                            runner_class = obj
                            break

                    if runner_class:
                        runner = runner_class()
                        sub_report = await runner.run()
                        self._aggregate_sub_report(sub_report, totals)
                except Exception as exc:
                    logger.error("Sub-experiment %s failed: %s", exp_name, exc)
                    totals["failed"] += 1
            else:
                # Collect from saved result files
                self._collect_from_saved(exp_name, totals)

        # Top-level summary metrics
        total_exp = len(ALL_EXPERIMENTS)
        self.report.add_metric(
            "experiments_completed", float(totals["completed"]), "count", ResultCategory.ACTUAL,
            notes=f"Out of {total_exp} total experiments"
        )
        self.report.add_metric(
            "experiments_not_run", float(totals["not_run"]), "count", ResultCategory.ACTUAL,
            notes="Require real data/hardware"
        )
        self.report.add_metric(
            "experiments_failed", float(totals["failed"]), "count", ResultCategory.ACTUAL
        )
        self.report.add_metric(
            "actual_metrics_collected", float(totals["actual_metrics"]), "count", ResultCategory.ACTUAL
        )
        self.report.add_metric(
            "simulated_metrics_collected", float(totals["simulated_metrics"]), "count", ResultCategory.ACTUAL
        )
        self.report.add_metric(
            "not_run_metrics", float(totals["not_run_metrics"]), "count", ResultCategory.ACTUAL
        )

        completion_rate = totals["completed"] / total_exp * 100
        self.report.add_metric(
            "experiment_completion_rate", completion_rate, "%", ResultCategory.ACTUAL
        )

        self.report.status = "COMPLETED"
        self.report.notes = (
            f"Overall system evaluation: {totals['completed']}/{total_exp} experiments completed. "
            f"Academic integrity: all NOT_RUN clearly documented."
        )
        return self.report

    def _aggregate_sub_report(self, sub_report: ExperimentReport, totals: dict):
        if sub_report.status == "COMPLETED":
            totals["completed"] += 1
        elif sub_report.status == "NOT_RUN":
            totals["not_run"] += 1
        else:
            totals["failed"] += 1

        for m in sub_report.metrics:
            if m.category == ResultCategory.ACTUAL:
                totals["actual_metrics"] += 1
            elif m.category == ResultCategory.SIMULATED:
                totals["simulated_metrics"] += 1
            else:
                totals["not_run_metrics"] += 1

        # Mirror key metrics
        for m in sub_report.metrics:
            self.report.add_metric(
                f"{sub_report.experiment_name}.{m.name}",
                m.value, m.unit, m.category,
                model_name=m.model_name,
                notes=f"From {sub_report.experiment_name}: {m.notes or ''}",
            )

    def _collect_from_saved(self, exp_name: str, totals: dict):
        """Scan results directory for latest JSON result file."""
        results_dir = self.results_dir / exp_name
        if not results_dir.exists():
            totals["not_run"] += 1
            return

        json_files = sorted(results_dir.glob("*.json"), reverse=True)
        if not json_files:
            totals["not_run"] += 1
            return

        try:
            with open(json_files[0]) as f:
                data = json.load(f)
            status = data.get("status", "UNKNOWN")
            if status == "COMPLETED":
                totals["completed"] += 1
            elif status == "NOT_RUN":
                totals["not_run"] += 1
            else:
                totals["failed"] += 1
            for m in data.get("metrics", []):
                cat = m.get("category", "NOT_RUN")
                if cat == "ACTUAL":
                    totals["actual_metrics"] += 1
                elif cat == "SIMULATED":
                    totals["simulated_metrics"] += 1
                else:
                    totals["not_run_metrics"] += 1
        except Exception as exc:
            logger.warning("Could not read result file for %s: %s", exp_name, exc)
            totals["failed"] += 1


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Overall system experiment runner")
    parser.add_argument("--run-all", action="store_true",
                        help="Run all sub-experiments (slow)")
    args = parser.parse_args()
    OverallSystemExperiment(run_sub_experiments=args.run_all).execute()
