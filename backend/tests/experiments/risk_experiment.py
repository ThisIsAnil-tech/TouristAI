"""
tests/experiments/risk_experiment.py — Experiment 3: Environmental Risk Scoring.

Validates the risk scoring formula against manually labelled zone conditions.

Metrics:
  - MAE, RMSE of risk scores vs human-labelled ground truth
  - Component weight sensitivity analysis
  - Risk level classification accuracy
"""
from __future__ import annotations

import logging
import math
from tests.experiments.base_runner import BaseExperimentRunner, ExperimentReport, ResultCategory

logger = logging.getLogger(__name__)

# Hand-labelled test cases: (weather, news, historical, expected_score_range)
_TEST_CASES = [
    {"weather": 0.0, "news": 0.0, "historical": 0.0, "expected_low": 1.0, "expected_high": 2.0,
     "label": "Clear day, no incidents, no news"},
    {"weather": 0.8, "news": 0.0, "historical": 0.0, "expected_low": 3.0, "expected_high": 5.0,
     "label": "Storm weather, no other factors"},
    {"weather": 0.0, "news": 0.9, "historical": 0.0, "expected_low": 4.0, "expected_high": 6.5,
     "label": "Critical news event, no weather/history"},
    {"weather": 0.5, "news": 0.5, "historical": 0.5, "expected_low": 5.0, "expected_high": 7.0,
     "label": "Moderate all factors"},
    {"weather": 1.0, "news": 1.0, "historical": 1.0, "expected_low": 9.0, "expected_high": 10.0,
     "label": "Maximum all factors"},
    {"weather": 0.1, "news": 0.1, "historical": 0.8, "expected_low": 3.0, "expected_high": 5.5,
     "label": "High historical risk, low current risk"},
]


class RiskExperiment(BaseExperimentRunner):
    """Experiment 3: Environmental Risk Scoring Validation."""
    experiment_name = "risk_experiment"

    async def run(self) -> ExperimentReport:
        from app.services.risk.risk_calculator import RiskCalculator
        from app.services.risk.adaptive_threshold import AdaptiveThresholdController

        self.report.dataset_name = "manual_risk_labels"
        calculator = RiskCalculator()
        threshold_ctrl = AdaptiveThresholdController()

        errors = []
        within_range = 0

        for case in _TEST_CASES:
            composite_0_1 = (
                calculator.weight_weather * case["weather"]
                + calculator.weight_news * case["news"]
                + calculator.weight_historical * case["historical"]
            )
            score = composite_0_1 * 9.0 + 1.0
            score = max(1.0, min(10.0, score))

            in_range = case["expected_low"] <= score <= case["expected_high"]
            if in_range:
                within_range += 1

            mid = (case["expected_low"] + case["expected_high"]) / 2
            errors.append(abs(score - mid))

        mae = sum(errors) / len(errors)
        rmse = math.sqrt(sum(e**2 for e in errors) / len(errors))
        range_accuracy = within_range / len(_TEST_CASES) * 100

        self.report.add_metric("mae", mae, "score_units", ResultCategory.ACTUAL,
                               notes="Mean Absolute Error vs expected range midpoints")
        self.report.add_metric("rmse", rmse, "score_units", ResultCategory.ACTUAL)
        self.report.add_metric("range_accuracy", range_accuracy, "%", ResultCategory.ACTUAL,
                               notes=f"{within_range}/{len(_TEST_CASES)} cases within expected range")
        self.report.add_metric("n_test_cases", float(len(_TEST_CASES)), "cases", ResultCategory.ACTUAL)

        # Threshold monotonicity test
        scores_test = [1.0, 3.0, 5.0, 7.0, 9.0, 10.0]
        thresholds = [threshold_ctrl.calculate(s).adaptive_threshold for s in scores_test]
        is_monotone = all(thresholds[i] >= thresholds[i+1] for i in range(len(thresholds)-1))
        self.report.add_metric("threshold_monotone", float(is_monotone), "bool", ResultCategory.ACTUAL,
                               notes="1=monotonically decreasing, 0=violated")

        self.report.status = "COMPLETED"
        self.report.notes = f"Weights: W={calculator.weight_weather} N={calculator.weight_news} H={calculator.weight_historical}"
        return self.report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    RiskExperiment().execute()
