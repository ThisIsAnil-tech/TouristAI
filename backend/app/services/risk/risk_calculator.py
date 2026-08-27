"""
app/services/risk/risk_calculator.py — Weighted environmental risk engine.

Implements the risk scoring algorithm from the project report:

  final_score = (W_weather × weather_score
               + W_news × news_score
               + W_historical × historical_score) × 9 + 1

  Maps [0,1] → [1, 10]

Default weights (configurable):
  weather:    0.30
  news:       0.40
  historical: 0.30

All component scores are 0.0–1.0 before weighting.
The final score is persisted to the risk_scores table.
Adaptive threshold is derived from the final score.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.incident import Incident, IncidentSeverity
from app.models.news import NewsEvent
from app.models.risk import RiskLevel, RiskScore
from app.models.weather import WeatherObservation
from app.models.zone import GeographicZone
from app.services.risk.adaptive_threshold import AdaptiveThresholdController

logger = logging.getLogger(__name__)

# Severity weight mapping for historical incidents
_INCIDENT_SEVERITY_WEIGHTS: dict[str, float] = {
    IncidentSeverity.LOW: 0.2,
    IncidentSeverity.MEDIUM: 0.5,
    IncidentSeverity.HIGH: 0.8,
    IncidentSeverity.CRITICAL: 1.0,
}


@dataclass
class RiskCalculationResult:
    zone_id: uuid.UUID
    weather_score: float
    news_score: float
    historical_score: float
    weight_weather: float
    weight_news: float
    weight_historical: float
    final_score: float        # 1.0 – 10.0
    risk_level: RiskLevel
    adaptive_threshold: float
    weather_observation_id: Optional[uuid.UUID]
    details: str


class HistoricalIncidentAnalyzer:
    """
    Calculate the historical incident risk component for a zone.

    Uses time-window weighting (recent incidents count more),
    frequency, and severity weighting.
    """

    async def compute(
        self,
        db: AsyncSession,
        zone_id: uuid.UUID,
        lookback_days: int = 90,
    ) -> float:
        """
        Return normalised historical risk score (0.0–1.0) for a zone.

        Scoring:
          - Counts incidents in the lookback window.
          - Applies time-decay: recent incidents weight more.
          - Applies severity weights.
          - Normalises against a reference count of 10 high-severity incidents.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        result = await db.execute(
            select(Incident).where(
                Incident.zone_id == zone_id,
                Incident.occurred_at >= cutoff,
            )
        )
        incidents = result.scalars().all()

        if not incidents:
            return 0.0

        now = datetime.now(timezone.utc)
        weighted_sum = 0.0

        for incident in incidents:
            # Time decay: exponential, half-life = 30 days
            age_days = max(0, (now - incident.occurred_at).days)
            decay = 2 ** (-age_days / 30.0)

            severity_w = _INCIDENT_SEVERITY_WEIGHTS.get(incident.severity, 0.5)
            weighted_sum += severity_w * decay

        # Normalise: assume 10 recent critical incidents = risk 1.0
        reference = 10.0 * 1.0 * 1.0  # 10 critical, no decay
        normalised = min(1.0, weighted_sum / reference)
        return normalised


class RiskCalculator:
    """
    Calculate the composite environmental risk score for a geographic zone.

    Pipeline:
      weather_provider → weather_score (0–1)
      news_events → news_score (0–1)
      historical_incidents → historical_score (0–1)
      → weighted sum → scale to 1–10 → risk_level → adaptive_threshold
    """

    def __init__(
        self,
        weight_weather: float | None = None,
        weight_news: float | None = None,
        weight_historical: float | None = None,
    ) -> None:
        self.weight_weather = weight_weather if weight_weather is not None else settings.RISK_WEIGHT_WEATHER
        self.weight_news = weight_news if weight_news is not None else settings.RISK_WEIGHT_NEWS
        self.weight_historical = weight_historical if weight_historical is not None else settings.RISK_WEIGHT_HISTORICAL
        self._historical_analyzer = HistoricalIncidentAnalyzer()
        self._threshold_ctrl = AdaptiveThresholdController()

    async def calculate_for_zone(
        self,
        db: AsyncSession,
        zone: GeographicZone,
        weather_score: Optional[float] = None,
        weather_obs_id: Optional[uuid.UUID] = None,
    ) -> RiskCalculationResult:
        """
        Calculate and persist the risk score for a zone.

        Args:
            db: Database session.
            zone: The geographic zone.
            weather_score: Pre-computed weather risk (0–1); fetched from
                           latest observation if not provided.
            weather_obs_id: ID of the WeatherObservation used.

        Returns:
            RiskCalculationResult with all components.
        """
        # ── Weather score ──────────────────────────────────────────────────
        if weather_score is None:
            latest_obs = await self._get_latest_weather_obs(db, zone.id)
            if latest_obs:
                weather_score = latest_obs.weather_risk_score or 0.0
                weather_obs_id = latest_obs.id
            else:
                weather_score = 0.0

        # ── News score ─────────────────────────────────────────────────────
        news_score = await self._compute_news_score(db, zone.id)

        # ── Historical score ───────────────────────────────────────────────
        historical_score = await self._historical_analyzer.compute(db, zone.id)

        # ── Weighted composite ─────────────────────────────────────────────
        composite_0_1 = (
            self.weight_weather * weather_score
            + self.weight_news * news_score
            + self.weight_historical * historical_score
        )

        # Scale from [0, 1] → [1, 10]
        final_score = composite_0_1 * 9.0 + 1.0
        final_score = round(max(1.0, min(10.0, final_score)), 2)

        # ── Risk level ─────────────────────────────────────────────────────
        risk_level = self._determine_risk_level(final_score)

        # ── Adaptive threshold ─────────────────────────────────────────────
        threshold_result = self._threshold_ctrl.calculate(final_score)

        details = (
            f"weather={weather_score:.3f}×{self.weight_weather} + "
            f"news={news_score:.3f}×{self.weight_news} + "
            f"historical={historical_score:.3f}×{self.weight_historical} "
            f"= {final_score:.2f}/10 [{risk_level}] "
            f"threshold={threshold_result.adaptive_threshold:.3f}"
        )
        logger.info("Risk for zone %s: %s", zone.id, details)

        return RiskCalculationResult(
            zone_id=zone.id,
            weather_score=weather_score,
            news_score=news_score,
            historical_score=historical_score,
            weight_weather=self.weight_weather,
            weight_news=self.weight_news,
            weight_historical=self.weight_historical,
            final_score=final_score,
            risk_level=risk_level,
            adaptive_threshold=threshold_result.adaptive_threshold,
            weather_observation_id=weather_obs_id,
            details=details,
        )

    async def persist(
        self,
        db: AsyncSession,
        result: RiskCalculationResult,
    ) -> RiskScore:
        """Save the risk calculation to the database."""
        score = RiskScore(
            zone_id=result.zone_id,
            weather_score=result.weather_score,
            news_score=result.news_score,
            historical_score=result.historical_score,
            weight_weather=result.weight_weather,
            weight_news=result.weight_news,
            weight_historical=result.weight_historical,
            final_score=result.final_score,
            risk_level=result.risk_level,
            adaptive_threshold=result.adaptive_threshold,
            weather_observation_id=result.weather_observation_id,
        )
        db.add(score)
        await db.flush()
        return score

    def compute_composite(
        self,
        weather: float,
        news: float,
        historical: float,
    ) -> float:
        """
        Synchronous composite score calculation (no DB required).
        Used by experiments, unit tests, and real-time scoring without DB.

        Args:
            weather: Weather risk score (0.0–1.0)
            news: News risk score (0.0–1.0)
            historical: Historical incident score (0.0–1.0)

        Returns:
            Final risk score (1.0–10.0)
        """
        composite = (
            self.weight_weather * weather
            + self.weight_news * news
            + self.weight_historical * historical
        )
        final = composite * 9.0 + 1.0
        return round(max(1.0, min(10.0, final)), 2)

    def classify(self, score: float) -> str:
        """Return risk level string for a given score (no DB required)."""
        level = self._determine_risk_level(score)
        return level.value if hasattr(level, "value") else str(level)

    @staticmethod
    def _determine_risk_level(score: float) -> RiskLevel:
        if score <= settings.RISK_LEVEL_LOW_MAX:
            return RiskLevel.LOW
        elif score <= settings.RISK_LEVEL_MEDIUM_MAX:
            return RiskLevel.MEDIUM
        elif score <= settings.RISK_LEVEL_HIGH_MAX:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    @staticmethod
    async def _get_latest_weather_obs(
        db: AsyncSession,
        zone_id: uuid.UUID,
    ) -> Optional[WeatherObservation]:
        result = await db.execute(
            select(WeatherObservation)
            .where(WeatherObservation.zone_id == zone_id)
            .order_by(WeatherObservation.observed_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def _compute_news_score(db: AsyncSession, zone_id: uuid.UUID) -> float:
        """
        Aggregate recent news severity scores for a zone.
        Uses the highest severity event in the last 24 hours.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        result = await db.execute(
            select(func.max(NewsEvent.severity_score)).where(
                NewsEvent.zone_id == zone_id,
                NewsEvent.published_at >= cutoff,
            )
        )
        max_score = result.scalar_one_or_none()
        return max_score or 0.0
