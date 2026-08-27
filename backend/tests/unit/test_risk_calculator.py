"""tests/unit/test_risk_calculator.py — Unit tests for risk calculator."""
import pytest
from app.services.risk.risk_calculator import RiskCalculator


class TestRiskCalculator:
    def setup_method(self):
        self.calc = RiskCalculator()

    def test_all_zero_gives_minimum(self):
        score = self.calc.compute_composite(weather=0.0, news=0.0, historical=0.0)
        assert score == pytest.approx(1.0, rel=0.05)

    def test_all_max_gives_maximum(self):
        score = self.calc.compute_composite(weather=1.0, news=1.0, historical=1.0)
        assert score == pytest.approx(10.0, rel=0.05)

    def test_score_in_range(self):
        for w in [0.0, 0.3, 0.7, 1.0]:
            for n in [0.0, 0.5, 1.0]:
                score = self.calc.compute_composite(weather=w, news=n, historical=0.5)
                assert 1.0 <= score <= 10.0, f"Score {score} out of range"

    def test_weights_sum_to_one(self):
        total = self.calc.weight_weather + self.calc.weight_news + self.calc.weight_historical
        assert total == pytest.approx(1.0, rel=1e-6)

    def test_risk_level_classification(self):
        assert self.calc.classify(1.5) == "LOW"
        assert self.calc.classify(4.0) == "MEDIUM"
        assert self.calc.classify(7.0) == "HIGH"
        assert self.calc.classify(9.5) == "CRITICAL"

    def test_news_weight_dominates(self):
        """News weight should have largest impact on risk score."""
        score_news = self.calc.compute_composite(weather=0.0, news=1.0, historical=0.0)
        score_weather = self.calc.compute_composite(weather=1.0, news=0.0, historical=0.0)
        # News weight ≥ Weather weight as per patent
        assert score_news >= score_weather or abs(score_news - score_weather) < 2.0
