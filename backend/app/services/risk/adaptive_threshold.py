"""
app/services/risk/adaptive_threshold.py — Adaptive AI Confidence Threshold.

Patent requirement: The environmental risk score must mathematically
influence the AI confidence threshold for distress detection.

Formula (configurable, documented):
  threshold = BASE - (BASE - MIN) * (risk_score / 10.0) * scale

  Higher risk score → lower threshold required → easier to trigger SOS.
  Lower risk score  → higher threshold required → harder to trigger SOS.

This threshold is then used by the emergency decision engine to evaluate
whether audio confidence exceeds the requirement.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ThresholdResult:
    risk_score: float
    adaptive_threshold: float
    base_threshold: float
    min_threshold: float
    max_threshold: float
    interpretation: str


class AdaptiveThresholdController:
    """
    Converts environmental risk score (1–10) into an AI confidence threshold.

    The threshold controls how confident the audio distress classifier
    must be before the emergency decision engine treats it as a real alert.

    Configurable parameters (from settings):
      BASE  = ADAPTIVE_THRESHOLD_BASE  (default 0.70)
      MIN   = ADAPTIVE_THRESHOLD_MIN   (default 0.30)
      MAX   = ADAPTIVE_THRESHOLD_MAX   (default 0.90)

    Behaviour:
      risk=1  → threshold ≈ BASE  (conservative — need high confidence)
      risk=10 → threshold ≈ MIN   (sensitive — act on lower confidence)
    """

    def __init__(
        self,
        base: float | None = None,
        min_threshold: float | None = None,
        max_threshold: float | None = None,
    ) -> None:
        self.base = base if base is not None else settings.ADAPTIVE_THRESHOLD_BASE
        self.min_threshold = min_threshold if min_threshold is not None else settings.ADAPTIVE_THRESHOLD_MIN
        self.max_threshold = max_threshold if max_threshold is not None else settings.ADAPTIVE_THRESHOLD_MAX

    def calculate(self, risk_score: float) -> ThresholdResult:
        """
        Calculate the adaptive threshold for a given risk score.

        Args:
            risk_score: Environmental risk score on scale 1.0 – 10.0.

        Returns:
            ThresholdResult with the computed threshold and metadata.
        """
        # Clamp risk_score to valid range
        risk_score = max(1.0, min(10.0, risk_score))

        # Linear interpolation:
        # At risk=1.0  → threshold = BASE (strict)
        # At risk=10.0 → threshold = MIN  (lenient)
        normalised = (risk_score - 1.0) / 9.0  # Maps [1, 10] → [0, 1]
        threshold = self.base - (self.base - self.min_threshold) * normalised

        # Clamp to [MIN, MAX]
        threshold = max(self.min_threshold, min(self.max_threshold, threshold))

        interpretation = (
            f"Risk={risk_score:.1f}/10 → "
            f"confidence threshold={threshold:.3f} "
            f"({'lenient' if risk_score >= 7 else 'moderate' if risk_score >= 4 else 'strict'})"
        )

        logger.debug("Adaptive threshold: %s", interpretation)

        return ThresholdResult(
            risk_score=risk_score,
            adaptive_threshold=threshold,
            base_threshold=self.base,
            min_threshold=self.min_threshold,
            max_threshold=self.max_threshold,
            interpretation=interpretation,
        )

    def is_distress(self, confidence: float, risk_score: float) -> tuple[bool, float]:
        """
        Determine whether audio confidence exceeds the adaptive threshold.

        Args:
            confidence: Audio classifier confidence (0.0 – 1.0).
            risk_score: Current environmental risk score.

        Returns:
            Tuple of (is_distress: bool, threshold_used: float).
        """
        result = self.calculate(risk_score)
        return confidence >= result.adaptive_threshold, result.adaptive_threshold


# Module-level singleton (can be overridden in tests)
threshold_controller = AdaptiveThresholdController()
