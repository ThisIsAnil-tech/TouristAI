"""tests/unit/test_adaptive_threshold.py — Unit tests for adaptive threshold."""
import pytest
from app.services.risk.adaptive_threshold import AdaptiveThresholdController


class TestAdaptiveThreshold:
    def setup_method(self):
        self.ctrl = AdaptiveThresholdController(base=0.70, min_threshold=0.30, max_threshold=0.90)

    def test_low_risk_high_threshold(self):
        result = self.ctrl.calculate(risk_score=1.0)
        assert result.adaptive_threshold == pytest.approx(0.70, rel=0.01)

    def test_high_risk_low_threshold(self):
        result = self.ctrl.calculate(risk_score=10.0)
        assert result.adaptive_threshold == pytest.approx(0.30, rel=0.01)

    def test_mid_risk(self):
        result = self.ctrl.calculate(risk_score=5.5)
        assert 0.30 < result.adaptive_threshold < 0.70

    def test_clamp_below_min(self):
        result = self.ctrl.calculate(risk_score=10.0)
        assert result.adaptive_threshold >= 0.30

    def test_clamp_above_max(self):
        result = self.ctrl.calculate(risk_score=1.0)
        assert result.adaptive_threshold <= 0.90

    def test_monotonically_decreasing(self):
        """Higher risk → lower threshold."""
        scores = [1.0, 3.0, 5.0, 7.0, 10.0]
        thresholds = [self.ctrl.calculate(s).adaptive_threshold for s in scores]
        for i in range(len(thresholds) - 1):
            assert thresholds[i] >= thresholds[i + 1]

    def test_is_distress_above_threshold(self):
        is_dist, threshold = self.ctrl.is_distress(confidence=0.85, risk_score=5.0)
        assert is_dist is True

    def test_is_not_distress_below_threshold(self):
        is_dist, threshold = self.ctrl.is_distress(confidence=0.10, risk_score=1.0)
        assert is_dist is False
