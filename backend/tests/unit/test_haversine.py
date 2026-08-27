"""tests/unit/test_haversine.py — Unit tests for GPS distance calculations."""
import math
import pytest

from app.services.gps.haversine import (
    GpsPoint,
    haversine_distance,
    is_point_in_zone,
    point_to_line_distance,
)


class TestHaversineDistance:
    def test_same_point_is_zero(self):
        p = GpsPoint(10.5276, 76.2144)
        assert haversine_distance(p, p) == pytest.approx(0.0, abs=0.001)

    def test_known_distance(self):
        # Kochi to Munnar, Kerala — straight-line (haversine) ~88.5 km
        kochi = GpsPoint(9.9312, 76.2673)
        munnar = GpsPoint(10.0889, 77.0597)
        dist = haversine_distance(kochi, munnar)
        assert 80_000 < dist < 100_000, f"Expected ~88.5km, got {dist/1000:.1f}km"

    def test_small_movement_50m(self):
        p1 = GpsPoint(10.0, 76.0)
        # Move ~50m north: 1 degree lat ≈ 111km → 50m ≈ 0.00045 degrees
        p2 = GpsPoint(10.00045, 76.0)
        dist = haversine_distance(p1, p2)
        assert 40 < dist < 60, f"Expected ~50m, got {dist:.1f}m"

    def test_symmetry(self):
        p1 = GpsPoint(10.0, 76.0)
        p2 = GpsPoint(11.0, 77.0)
        assert haversine_distance(p1, p2) == pytest.approx(haversine_distance(p2, p1), rel=1e-6)


class TestPointToLineDistance:
    def test_point_on_line(self):
        start = GpsPoint(10.0, 76.0)
        end = GpsPoint(10.0, 77.0)
        mid = GpsPoint(10.0, 76.5)
        dist = point_to_line_distance(mid, start, end)
        assert dist < 10, f"Point on line should have near-zero distance, got {dist:.2f}m"

    def test_point_perpendicular(self):
        start = GpsPoint(10.0, 76.0)
        end = GpsPoint(10.0, 77.0)
        # Point 1 degree north of midpoint ≈ 111km perpendicular
        off = GpsPoint(11.0, 76.5)
        dist = point_to_line_distance(off, start, end)
        assert 100_000 < dist < 120_000

    def test_point_beyond_endpoint(self):
        start = GpsPoint(10.0, 76.0)
        end = GpsPoint(10.0, 77.0)
        beyond = GpsPoint(10.0, 78.0)  # Past the end
        dist = point_to_line_distance(beyond, start, end)
        # Should be distance from point to nearest endpoint (end)
        expected = haversine_distance(beyond, end)
        assert dist == pytest.approx(expected, rel=0.01)


class TestIsPointInZone:
    def test_point_inside(self):
        p = GpsPoint(10.5, 76.5)
        assert is_point_in_zone(p, 10.0, 11.0, 76.0, 77.0)

    def test_point_outside(self):
        p = GpsPoint(12.0, 76.5)
        assert not is_point_in_zone(p, 10.0, 11.0, 76.0, 77.0)

    def test_point_on_boundary(self):
        p = GpsPoint(10.0, 76.0)
        assert is_point_in_zone(p, 10.0, 11.0, 76.0, 77.0)
