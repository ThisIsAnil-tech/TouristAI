"""
app/services/gps/anomaly_detector.py — GPS anomaly detection.

Implements the algorithm from the patent and project report:

  minimum movement threshold = 50 metres (configurable)
  check interval = 10 minutes (configurable)
  anomaly limit = 3 consecutive abnormal readings (configurable)

Detection types:
  1. STATIONARY — no significant movement in expected interval
  2. HIGH_RISK_ZONE — entered a configured high-risk geographic zone
  3. ROUTE_DEVIATION — deviated beyond allowed corridor
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.gps import GpsReading, Route, RoutePoint
from app.models.zone import GeographicZone
from app.services.gps.haversine import GpsPoint, haversine_distance, is_point_in_zone
from app.services.gps.route_deviation import RouteDeviationDetector

logger = logging.getLogger(__name__)


@dataclass
class AnomalyDetectionResult:
    is_anomalous: bool
    anomaly_type: Optional[str]  # "STATIONARY" | "HIGH_RISK_ZONE" | "ROUTE_DEVIATION" | None
    distance_from_previous_m: Optional[float]
    consecutive_anomalies: int
    in_high_risk_zone: bool
    zone_id: Optional[uuid.UUID]
    route_deviation_details: Optional[str]
    should_trigger_sos: bool
    reason: str


class GpsAnomalyDetector:
    """
    Full GPS anomaly detection engine.

    Evaluates each incoming GPS reading against:
    1. Movement threshold (stationary detection)
    2. High-risk zone membership
    3. Route corridor deviation

    Maintains an anomaly counter.  When consecutive anomalies reach
    the configured limit, SOS is triggered.
    """

    def __init__(
        self,
        movement_threshold_m: float | None = None,
        anomaly_limit: int | None = None,
        deviation_threshold_m: float | None = None,
        max_consecutive_deviations: int | None = None,
    ) -> None:
        self.movement_threshold_m = movement_threshold_m or settings.GPS_MOVEMENT_THRESHOLD_METERS
        self.anomaly_limit = anomaly_limit or settings.GPS_ANOMALY_LIMIT
        self._anomaly_counter: int = 0

        self._route_deviation_detector = RouteDeviationDetector(
            deviation_threshold_m=deviation_threshold_m or settings.GPS_ROUTE_DEVIATION_THRESHOLD_METERS,
            max_consecutive_deviations=max_consecutive_deviations or settings.GPS_MAX_CONSECUTIVE_DEVIATIONS,
        )

    async def analyze(
        self,
        current_reading: GpsReading,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> AnomalyDetectionResult:
        """
        Analyze a GPS reading for anomalies.

        Args:
            current_reading: The newly ingested GPS reading (already saved).
            db: Async database session.
            user_id: The tourist's user ID.

        Returns:
            AnomalyDetectionResult with all decision fields.
        """
        current_point = GpsPoint(
            latitude=current_reading.latitude,
            longitude=current_reading.longitude,
        )

        # ── 1. Retrieve previous reading ──────────────────────────────────
        previous_reading = await self._get_previous_reading(db, user_id, current_reading.id)
        distance_m: Optional[float] = None

        if previous_reading is not None:
            prev_point = GpsPoint(
                latitude=previous_reading.latitude,
                longitude=previous_reading.longitude,
            )
            distance_m = haversine_distance(current_point, prev_point)

        # ── 2. Stationary detection ───────────────────────────────────────
        is_stationary = (
            distance_m is not None
            and distance_m < self.movement_threshold_m
        )

        # ── 3. High-risk zone detection ───────────────────────────────────
        zone, in_high_risk = await self._check_high_risk_zone(db, current_point)
        zone_id = zone.id if zone else None

        # ── 4. Route deviation detection ──────────────────────────────────
        route_points = await self._get_active_route_points(db, user_id)
        deviation_result = None
        route_deviation_triggered = False

        if len(route_points) >= 2:
            deviation_result = self._route_deviation_detector.check(
                current_point, route_points
            )
            route_deviation_triggered = deviation_result.triggered_sos

        # ── 5. Determine anomaly ──────────────────────────────────────────
        is_anomalous = is_stationary or in_high_risk or (
            deviation_result is not None and deviation_result.is_deviated
        )

        anomaly_type: Optional[str] = None
        if is_stationary:
            anomaly_type = "STATIONARY"
        elif in_high_risk and not is_stationary:
            anomaly_type = "HIGH_RISK_ZONE"
        elif deviation_result and deviation_result.is_deviated:
            anomaly_type = "ROUTE_DEVIATION"

        # ── 6. Update anomaly counter ─────────────────────────────────────
        if is_anomalous:
            self._anomaly_counter += 1
        else:
            self._anomaly_counter = 0  # False-alarm prevention: reset on normal

        # ── 7. SOS decision ───────────────────────────────────────────────
        should_trigger_sos = (
            self._anomaly_counter >= self.anomaly_limit
            or route_deviation_triggered
        )

        reason_parts = []
        if is_stationary:
            reason_parts.append(f"No movement ({distance_m:.1f}m < {self.movement_threshold_m}m threshold)")
        if in_high_risk:
            reason_parts.append(f"In high-risk zone: {zone.name if zone else 'unknown'}")
        if deviation_result and deviation_result.is_deviated:
            reason_parts.append(deviation_result.details)
        if not reason_parts:
            reason_parts.append("Normal reading")

        result = AnomalyDetectionResult(
            is_anomalous=is_anomalous,
            anomaly_type=anomaly_type,
            distance_from_previous_m=distance_m,
            consecutive_anomalies=self._anomaly_counter,
            in_high_risk_zone=in_high_risk,
            zone_id=zone_id,
            route_deviation_details=deviation_result.details if deviation_result else None,
            should_trigger_sos=should_trigger_sos,
            reason="; ".join(reason_parts),
        )

        if should_trigger_sos:
            logger.warning(
                "GPS anomaly SOS trigger: user=%s anomalies=%d reason=%s",
                user_id, self._anomaly_counter, result.reason
            )

        return result

    async def _get_previous_reading(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        current_id: uuid.UUID,
    ) -> Optional[GpsReading]:
        """Get the most recent GPS reading before the current one."""
        result = await db.execute(
            select(GpsReading)
            .where(
                GpsReading.user_id == user_id,
                GpsReading.id != current_id,
            )
            .order_by(GpsReading.recorded_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _check_high_risk_zone(
        self,
        db: AsyncSession,
        point: GpsPoint,
    ) -> tuple[Optional[GeographicZone], bool]:
        """Check if the point falls within any high-risk zone."""
        result = await db.execute(
            select(GeographicZone).where(
                GeographicZone.is_high_risk == True,
                GeographicZone.is_active == True,
                GeographicZone.min_latitude <= point.latitude,
                GeographicZone.max_latitude >= point.latitude,
                GeographicZone.min_longitude <= point.longitude,
                GeographicZone.max_longitude >= point.longitude,
            )
        )
        zone = result.scalars().first()
        return zone, zone is not None

    async def _get_active_route_points(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> List[GpsPoint]:
        """Retrieve the current active route waypoints for a user."""
        result = await db.execute(
            select(RoutePoint)
            .join(Route, Route.id == RoutePoint.route_id)
            .where(
                Route.user_id == user_id,
                Route.is_active == True,
            )
            .order_by(RoutePoint.sequence_number)
        )
        points = result.scalars().all()
        return [GpsPoint(latitude=p.latitude, longitude=p.longitude) for p in points]

    def reset_counter(self) -> None:
        """Reset anomaly counter, e.g., after SOS is resolved."""
        self._anomaly_counter = 0
        self._route_deviation_detector.reset()
