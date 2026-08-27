"""
scripts/run_all_experiments.py — Execute all 15 research benchmark experiment suites.

Generates reproducible raw result JSON/CSVs in tests/results/,
aggregates tables in research/tables/, and renders plots in research/plots/.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

# Ensure backend root is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.experiments.audio_experiment import AudioExperiment
from tests.experiments.gps_experiment import GpsExperiment
from tests.experiments.risk_experiment import RiskExperiment
from tests.experiments.emergency_decision_experiment import EmergencyDecisionExperiment
from tests.experiments.internet_alert_experiment import InternetAlertExperiment
from tests.experiments.sms_alert_experiment import SmsAlertExperiment
from tests.experiments.mesh_experiment import MeshExperiment
from tests.experiments.blockchain_experiment import BlockchainExperiment
from tests.experiments.mobile_performance_experiment import MobilePerformanceExperiment
from tests.experiments.edge_ai_experiment import EdgeAiExperiment
from tests.experiments.battery_experiment import BatteryExperiment
from tests.experiments.emergency_response_experiment import EmergencyResponseExperiment
from tests.experiments.field_test_experiment import FieldTestExperiment
from tests.experiments.scalability_experiment import ScalabilityExperiment
from tests.experiments.overall_system_experiment import OverallSystemExperiment

from research.generate_tables import generate_summary_tables
from research.generate_plots import plot_all

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

EXPERIMENT_CLASSES = [
    AudioExperiment,
    GpsExperiment,
    RiskExperiment,
    EmergencyDecisionExperiment,
    InternetAlertExperiment,
    SmsAlertExperiment,
    MeshExperiment,
    BlockchainExperiment,
    MobilePerformanceExperiment,
    EdgeAiExperiment,
    BatteryExperiment,
    EmergencyResponseExperiment,
    FieldTestExperiment,
    ScalabilityExperiment,
    OverallSystemExperiment,
]


async def main():
    logger.info("============================================================")
    logger.info("STARTING BATCH EXECUTION OF ALL 15 RESEARCH BENCHMARKS")
    logger.info("============================================================")

    results_summary = []

    for i, exp_cls in enumerate(EXPERIMENT_CLASSES, 1):
        exp_name = exp_cls.experiment_name
        logger.info("\n[%d/15] Running %s...", i, exp_name)
        runner = exp_cls()
        try:
            report = await runner.run()
            # Save raw report to tests/results/
            runner._export(report)
            status = report.status
            metric_count = len(report.metrics)
            logger.info("✅ Finished %s: status=%s (%d metrics)",
                        exp_name, status, metric_count)
            results_summary.append({
                "num": i,
                "name": exp_name,
                "status": status,
                "metrics_count": metric_count,
            })
        except Exception as exc:
            logger.exception("❌ Error running %s: %s", exp_name, exc)
            results_summary.append({
                "num": i,
                "name": exp_name,
                "status": "ERROR",
                "metrics_count": 0,
            })

    logger.info("\n============================================================")
    logger.info("AGGREGATING RESEARCH TABLES AND RENDERING FIGURES")
    logger.info("============================================================")
    generate_summary_tables()
    plot_all()

    logger.info("\n============================================================")
    logger.info("EXECUTION SUMMARY:")
    logger.info("============================================================")
    for res in results_summary:
        logger.info("  Exp %2d: %-35s -> %s (%d metrics)",
                    res["num"], res["name"], res["status"], res["metrics_count"])


if __name__ == "__main__":
    asyncio.run(main())
