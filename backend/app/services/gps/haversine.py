"""
app/services/gps/haversine.py — Haversine distance calculation.

Implements the actual Haversine formula to compute great-circle
distance between two GPS coordinates in metres.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple


# Earth's mean radius in metres
EARTH_RADIUS_M: float = 6_371_000.0


@dataclass(frozen=True)
class GpsPoint:
    latitude: float
    longitude: float


def haversine_distance(p1: GpsPoint, p2: GpsPoint) -> float:
    """
    Calculate the Haversine great-circle distance between two GPS points.

    Args:
        p1: First coordinate (lat/lon in decimal degrees).
        p2: Second coordinate (lat/lon in decimal degrees).

    Returns:
        Distance in metres.
    """
    lat1 = math.radians(p1.latitude)
    lat2 = math.radians(p2.latitude)
    dlat = math.radians(p2.latitude - p1.latitude)
    dlon = math.radians(p2.longitude - p1.longitude)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_M * c


def point_to_line_distance(
    point: GpsPoint,
    line_start: GpsPoint,
    line_end: GpsPoint,
) -> float:
    """
    Calculate the perpendicular distance (in metres) from a GPS point
    to a line segment defined by two GPS points.

    Uses an equirectangular approximation valid for short distances
    (< 100 km), then falls back to point-to-endpoint distance.

    Returns:
        Minimum distance in metres from the point to the line segment.
    """
    # Convert all points to Cartesian (metres) relative to line_start
    def to_xy(p: GpsPoint, origin: GpsPoint) -> Tuple[float, float]:
        dlat = math.radians(p.latitude - origin.latitude)
        dlon = math.radians(p.longitude - origin.longitude)
        lat_avg = math.radians((p.latitude + origin.latitude) / 2)
        x = dlon * EARTH_RADIUS_M * math.cos(lat_avg)
        y = dlat * EARTH_RADIUS_M
        return x, y

    origin = line_start
    ax, ay = 0.0, 0.0
    bx, by = to_xy(line_end, origin)
    px, py = to_xy(point, origin)

    # Segment length squared
    seg_len_sq = (bx - ax) ** 2 + (by - ay) ** 2

    if seg_len_sq == 0:
        # Line segment is a single point
        return haversine_distance(point, line_start)

    # Parameter t for the projection of point onto the line segment
    t = ((px - ax) * (bx - ax) + (py - ay) * (by - ay)) / seg_len_sq
    t = max(0.0, min(1.0, t))  # Clamp to [0, 1]

    # Closest point on the segment
    closest_x = ax + t * (bx - ax)
    closest_y = ay + t * (by - ay)

    return math.sqrt((px - closest_x) ** 2 + (py - closest_y) ** 2)


def is_point_in_zone(
    point: GpsPoint,
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float,
) -> bool:
    """Return True if point is within the given bounding box."""
    return (
        min_lat <= point.latitude <= max_lat
        and min_lon <= point.longitude <= max_lon
    )
