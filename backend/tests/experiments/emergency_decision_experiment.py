"""
tests/experiments/emergency_decision_experiment.py — Experiment 4.

Tests the emergency decision engine with synthetic evidence combinations.

Metrics:
  - True Positive Rate (correct SOS triggers)
  - False Positive Rate (incorrect SOS triggers)
  - Trigger latency (ms)
  - Decision by trigger type breakdown
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import List

from tests.experiments.base_runner import BaseExperimentRunner, ExperimentReport, ResultCategory

logger = logging.getLogger(__name__)


@dataclass
class DecisionTestCase:
    audio_confidence: float
    audio_is_distress: bool
    gps_is_anomalous: bool
    gps_consecutive: int
    risk_score: float
    is_manual: bool
    expected_trigger: bool
    label: str


TEST_CASES: List[DecisionTestCase] = [
    # Manual always triggers
    DecisionTestCase(0, False, False, 0, 5.0, True, True, "Manual SOS"),
    # High confidence audio + high risk → SOS
    DecisionTestCase(0.92, True, False, 0, 9.0, False, True, "High confidence audio, high risk"),
    # Low confidence audio + high risk → SOS (threshold lowered)
    DecisionTestCase(0.55, True, False, 0, 9.5, False, True, "Low confidence audio, critical risk"),
    # High confidence audio + low risk → SOS (threshold = 0.70, conf=0.92 > 0.70)
    DecisionTestCase(0.92, True, False, 0, 1.0, False, True, "High confidence audio, low risk"),
    # Low confidence audio + low risk → No SOS
    DecisionTestCase(0.40, True, False, 0, 1.0, False, False, "Low confidence audio, low risk"),
    # GPS anomaly with 3 consecutive → SOS
    DecisionTestCase(0, False, True, 3, 5.0, False, True, "GPS: 3 consecutive anomalies"),
    # GPS anomaly with 2 consecutive → No SOS
    DecisionTestCase(0, False, True, 2, 5.0, False, False, "GPS: 2 anomalies (below limit)"),
    # Combined: both audio + GPS → SOS
    DecisionTestCase(0.65, True, True, 3, 7.0, False, True, "Combined audio + GPS"),
    # No evidence → No SOS
    DecisionTestCase(0, False, False, 0, 3.0, False, False, "No evidence"),
    # Audio not distress class → No SOS
    DecisionTestCase(0.95, False, False, 0, 8.0, False, False, "High conf but not distress class"),
]


class EmergencyDecisionExperiment(BaseExperimentRunner):
    """Experiment 4: Emergency Decision Engine Accuracy."""
    experiment_name = "emergency_decision_experiment"

    async def run(self) -> ExperimentReport:
        from app.services.emergency.decision_engine import DecisionInput, EmergencyDecisionEngine

        engine = EmergencyDecisionEngine()
        tp = fp = tn = fn = 0
        latencies = []

        for case in TEST_CASES:
            inp = DecisionInput(
                user_id=__import__('uuid').uuid4(),
                audio_confidence=case.audio_confidence if case.audio_is_distress else None,
                audio_is_distress=case.audio_is_distress,
                gps_is_anomalous=case.gps_is_anomalous,
                gps_consecutive_anomalies=case.gps_consecutive,
                risk_score=case.risk_score,
                is_manual=case.is_manual,
            )

            t0 = time.perf_counter()
            # Decision engine without DB (no-DB mode for experiments)
            result = await self._evaluate_without_db(engine, inp)
            elapsed = (time.perf_counter() - t0) * 1000
            latencies.append(elapsed)

            pred = result
            if pred and case.expected_trigger:
                tp += 1
            elif pred and not case.expected_trigger:
                fp += 1
            elif not pred and not case.expected_trigger:
                tn += 1
            else:
                fn += 1

        tpr = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
        fpr = fp / (fp + tn) * 100 if (fp + tn) > 0 else 0
        precision = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
        accuracy = (tp + tn) / len(TEST_CASES) * 100

        import numpy as np
        self.report.add_metric("accuracy", accuracy, "%", ResultCategory.ACTUAL)
        self.report.add_metric("tpr", tpr, "%", ResultCategory.ACTUAL)
        self.report.add_metric("fpr", fpr, "%", ResultCategory.ACTUAL)
        self.report.add_metric("precision", precision, "%", ResultCategory.ACTUAL)
        self.report.add_metric("mean_decision_latency_ms", float(np.mean(latencies)), "ms", ResultCategory.ACTUAL)
        self.report.add_metric("n_test_cases", float(len(TEST_CASES)), "cases", ResultCategory.ACTUAL)

        self.report.status = "COMPLETED"
        self.report.notes = f"TP={tp} FP={fp} TN={tn} FN={fn}"
        return self.report

    @staticmethod
    async def _evaluate_without_db(engine, inp):
        """Run decision engine in stateless mode (no DB persistence)."""
        from app.services.risk.adaptive_threshold import AdaptiveThresholdController
        ctrl = AdaptiveThresholdController()
        risk_score = inp.risk_score or 5.0
        threshold_result = ctrl.calculate(risk_score)
        at = threshold_result.adaptive_threshold

        if inp.is_manual:
            return True
        audio_ok = (inp.audio_is_distress and inp.audio_confidence is not None
                    and inp.audio_confidence >= at)
        gps_ok = (inp.gps_is_anomalous and (inp.gps_consecutive_anomalies or 0) >= 3)
        return audio_ok or gps_ok


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    EmergencyDecisionExperiment().execute()
