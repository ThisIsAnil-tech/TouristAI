"""app/api/v1/gps/__init__.py — GPS safety endpoints."""
from __future__ import annotations

import uuid
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id, require_responder
from app.database import get_db
from app.models.gps import GpsReading, Route, RoutePoint
from app.models.user import User
from app.services.gps.anomaly_detector import GpsAnomalyDetector

logger = logging.getLogger(__name__)
router = APIRouter()

_detectors: dict[uuid.UUID, GpsAnomalyDetector] = {}


def _get_detector(user_id: uuid.UUID) -> GpsAnomalyDetector:
    if user_id not in _detectors:
        _detectors[user_id] = GpsAnomalyDetector()
    return _detectors[user_id]


class LocationRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    altitude_m: Optional[float] = None
    accuracy_m: Optional[float] = None
    speed_ms: Optional[float] = None
    bearing_deg: Optional[float] = None
    recorded_at: datetime

    model_config = {"json_schema_extra": {"example": {
        "latitude": 10.5276, "longitude": 76.2144,
        "recorded_at": "2024-01-15T10:30:00Z"
    }}}


class LocationResponse(BaseModel):
    reading_id: uuid.UUID
    is_anomalous: bool
    anomaly_type: Optional[str]
    distance_from_previous_m: Optional[float]
    consecutive_anomalies: int
    in_high_risk_zone: bool
    should_trigger_sos: bool
    reason: str


class RouteDeviationRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    route_id: uuid.UUID


class GpsHistoryResponse(BaseModel):
    id: uuid.UUID
    latitude: float
    longitude: float
    recorded_at: datetime
    is_anomalous: bool
    anomaly_type: Optional[str]
    distance_from_previous_m: Optional[float]


@router.post(
    "/location",
    response_model=LocationResponse,
    summary="Submit GPS location and analyze for anomalies",
)
async def submit_location(
    body: LocationRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> LocationResponse:
    uid = uuid.UUID(user_id)

    # Save reading
    reading = GpsReading(
        user_id=uid,
        latitude=body.latitude,
        longitude=body.longitude,
        altitude_m=body.altitude_m,
        accuracy_m=body.accuracy_m,
        speed_ms=body.speed_ms,
        bearing_deg=body.bearing_deg,
        recorded_at=body.recorded_at,
    )
    db.add(reading)
    await db.flush()

    # Update user last location
    user = await db.get(User, uid)
    if user:
        user.last_latitude = body.latitude
        user.last_longitude = body.longitude
        user.last_location_at = body.recorded_at

    # Analyze
    detector = _get_detector(uid)
    result = await detector.analyze(reading, db, uid)

    # Persist anomaly flags
    reading.is_anomalous = result.is_anomalous
    reading.anomaly_type = result.anomaly_type
    reading.distance_from_previous_m = result.distance_from_previous_m
    reading.in_high_risk_zone = result.in_high_risk_zone
    reading.zone_id = result.zone_id

    return LocationResponse(
        reading_id=reading.id,
        is_anomalous=result.is_anomalous,
        anomaly_type=result.anomaly_type,
        distance_from_previous_m=result.distance_from_previous_m,
        consecutive_anomalies=result.consecutive_anomalies,
        in_high_risk_zone=result.in_high_risk_zone,
        should_trigger_sos=result.should_trigger_sos,
        reason=result.reason,
    )


@router.get(
    "/history/{user_id}",
    response_model=List[GpsHistoryResponse],
    summary="Get GPS history for a user",
)
async def get_gps_history(
    user_id: uuid.UUID,
    limit: int = 100,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> List[GpsHistoryResponse]:
    # Users can only see their own history; responders/admins can see anyone's
    result = await db.scalars(
        select(GpsReading)
        .where(GpsReading.user_id == user_id)
        .order_by(GpsReading.recorded_at.desc())
        .limit(limit)
    )
    readings = result.all()
    return [
        GpsHistoryResponse(
            id=r.id,
            latitude=r.latitude,
            longitude=r.longitude,
            recorded_at=r.recorded_at,
            is_anomalous=r.is_anomalous,
            anomaly_type=r.anomaly_type,
            distance_from_previous_m=r.distance_from_previous_m,
        )
        for r in readings
    ]


@router.post("/analyze", summary="Analyze a specific GPS reading for anomalies")
async def analyze_reading(
    reading_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    reading = await db.get(GpsReading, reading_id)
    if not reading or str(reading.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Reading not found")
    uid = uuid.UUID(user_id)
    detector = _get_detector(uid)
    result = await detector.analyze(reading, db, uid)
    return {"is_anomalous": result.is_anomalous, "reason": result.reason,
            "should_trigger_sos": result.should_trigger_sos}
