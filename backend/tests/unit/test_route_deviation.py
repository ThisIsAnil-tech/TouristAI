"""tests/unit/test_route_deviation.py — Unit tests for route deviation detector."""
import pytest
from app.services.gps.haversine import GpsPoint
from app.services.gps.route_deviation import RouteDeviationDetector, DeviationResult


def _make_route(*coords):
    return [GpsPoint(lat, lon) for lat, lon in coords]


class TestRouteDeviationDetector:
    def setup_method(self):
        self.detector = RouteDeviationDetector(
            deviation_threshold_m=200.0, max_consecutive_deviations=3
        )

    def test_on_route_not_deviated(self):
        route = _make_route((10.0, 76.0), (10.0, 76.1), (10.0, 76.2))
        on_route = GpsPoint(10.0, 76.1)  # Exactly on segment
        result = self.detector.check(on_route, route)
        assert result is None or not result.is_deviated

    def test_far_off_route_deviated(self):
        route = _make_route((10.0, 76.0), (10.0, 76.5))
        far_off = GpsPoint(12.0, 76.25)  # ~222km north of route
        result = self.detector.check(far_off, route)
        assert result is not None
        assert result.is_deviated

    def test_empty_route_returns_none(self):
        result = self.detector.check(GpsPoint(10.0, 76.0), [])
        assert result is None

    def test_single_point_route_returns_none(self):
        result = self.detector.check(GpsPoint(10.0, 76.0), [GpsPoint(10.0, 76.0)])
        assert result is None

    def test_consecutive_counter_increments(self):
        route = _make_route((10.0, 76.0), (10.0, 76.5))
        far_off = GpsPoint(12.0, 76.25)
        for i in range(3):
            result = self.detector.check(far_off, route)
        assert result is not None
        assert result.consecutive_deviations == 3

    def test_consecutive_counter_resets_on_return(self):
        route = _make_route((10.0, 76.0), (10.0, 76.5))
        far_off = GpsPoint(12.0, 76.25)
        on_route = GpsPoint(10.0, 76.25)
        self.detector.check(far_off, route)
        self.detector.check(far_off, route)
        self.detector.check(on_route, route)  # Returns to route
        result = self.detector.check(far_off, route)
        if result:
            assert result.consecutive_deviations <= 1

    def test_distance_reported(self):
        route = _make_route((10.0, 76.0), (10.0, 76.5))
        far_off = GpsPoint(12.0, 76.25)
        result = self.detector.check(far_off, route)
        assert result is not None
        assert result.distance_from_route_m > 0
