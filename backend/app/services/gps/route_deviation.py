"""
app/services/gps/route_deviation.py — Route deviation detection.

Implements:
  - Minimum distance from point to planned route corridor
  - Consecutive deviation counter
  - Maximum allowed deviation threshold (configurable)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from app.services.gps.haversine import GpsPoint, point_to_line_distance, haversine_distance

logger = logging.getLogger(__name__)


@dataclass
class RouteDeviationResult:
    is_deviated: bool
    min_distance_to_route_m: float
    deviation_threshold_m: float
    closest_segment_index: Optional[int]
    consecutive_deviations: int
    triggered_sos: bool
    details: str


class RouteDeviationDetector:
    """
    Checks whether a GPS point has deviated from a planned route.

    Algorithm (from project specification):
    1. For each consecutive pair of route points, compute point-to-segment distance.
    2. Take the minimum distance across all segments (nearest corridor point).
    3. If minimum distance > threshold → deviation detected.
    4. Track consecutive deviations; if >= max_consecutive → trigger SOS.
    """

    def __init__(
        self,
        deviation_threshold_m: float = 200.0,
        max_consecutive_deviations: int = 3,
    ) -> None:
        self.deviation_threshold_m = deviation_threshold_m
        self.max_consecutive_deviations = max_consecutive_deviations
        self._consecutive_count: int = 0

    def check(
        self,
        current: GpsPoint,
        route_points: List[GpsPoint],
    ) -> RouteDeviationResult:
        """
        Check whether current position deviates from the planned route.

        Args:
            current: Current GPS position.
            route_points: Ordered list of planned route waypoints (≥ 2 needed for segments).

        Returns:
            RouteDeviationResult with all decision fields populated.
        """
        if len(route_points) < 2:
            # Cannot evaluate deviation without at least 2 waypoints
            return RouteDeviationResult(
                is_deviated=False,
                min_distance_to_route_m=0.0,
                deviation_threshold_m=self.deviation_threshold_m,
                closest_segment_index=None,
                consecutive_deviations=self._consecutive_count,
                triggered_sos=False,
                details="Route has fewer than 2 waypoints — deviation check skipped",
            )

        min_dist = float("inf")
        closest_seg = 0

        for i in range(len(route_points) - 1):
            dist = point_to_line_distance(
                current, route_points[i], route_points[i + 1]
            )
            if dist < min_dist:
                min_dist = dist
                closest_seg = i

        is_deviated = min_dist > self.deviation_threshold_m

        if is_deviated:
            self._consecutive_count += 1
        else:
            self._consecutive_count = 0  # Reset on normal reading

        triggered_sos = self._consecutive_count >= self.max_consecutive_deviations

        details = (
            f"Distance to route: {min_dist:.1f}m "
            f"(threshold: {self.deviation_threshold_m}m), "
            f"consecutive deviations: {self._consecutive_count}"
        )

        if triggered_sos:
            logger.warning(
                "Route deviation SOS triggered: %d consecutive deviations "
                "(%.1fm from route)",
                self._consecutive_count, min_dist
            )

        return RouteDeviationResult(
            is_deviated=is_deviated,
            min_distance_to_route_m=min_dist,
            deviation_threshold_m=self.deviation_threshold_m,
            closest_segment_index=closest_seg,
            consecutive_deviations=self._consecutive_count,
            triggered_sos=triggered_sos,
            details=details,
        )

    def reset(self) -> None:
        """Reset consecutive deviation counter (e.g., after SOS resolved)."""
        self._consecutive_count = 0
