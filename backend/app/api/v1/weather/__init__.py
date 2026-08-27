"""app/api/v1/weather/__init__.py — Weather endpoints."""
from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id, require_admin
from app.database import get_db
from app.models.weather import WeatherObservation
from app.models.zone import GeographicZone
from app.services.risk.weather_provider import OpenWeatherMapProvider, WeatherProviderUnavailableError

logger = logging.getLogger(__name__)
router = APIRouter()
_provider = OpenWeatherMapProvider()


class WeatherResponse(BaseModel):
    temperature_c: Optional[float]
    humidity_pct: Optional[int]
    wind_speed_ms: Optional[float]
    weather_main: Optional[str]
    weather_description: Optional[str]
    weather_risk_score: float
    is_mock: bool
    observed_at: str


@router.get("/location", response_model=WeatherResponse, summary="Get weather for a GPS coordinate")
async def get_weather_for_location(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> WeatherResponse:
    try:
        data = await _provider.get_weather(lat, lon)
    except WeatherProviderUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    obs = WeatherObservation(
        latitude=lat, longitude=lon,
        temperature_c=data.temperature_c,
        humidity_pct=data.humidity_pct,
        wind_speed_ms=data.wind_speed_ms,
        weather_code=data.weather_code,
        weather_main=data.weather_main,
        weather_description=data.weather_description,
        weather_risk_score=data.risk_score,
        observed_at=datetime.now(timezone.utc),
    )
    db.add(obs)
    await db.commit()

    return WeatherResponse(
        temperature_c=data.temperature_c,
        humidity_pct=data.humidity_pct,
        wind_speed_ms=data.wind_speed_ms,
        weather_main=data.weather_main,
        weather_description=data.weather_description,
        weather_risk_score=data.risk_score,
        is_mock=data.is_mock,
        observed_at=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/update/{zone_id}", summary="Update weather for a zone (admin)")
async def update_zone_weather(
    zone_id: uuid.UUID,
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    zone = await db.get(GeographicZone, zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    if zone.center_latitude is None:
        raise HTTPException(status_code=400, detail="Zone has no center coordinates")
    try:
        data = await _provider.get_weather(zone.center_latitude, zone.center_longitude)
    except WeatherProviderUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    obs = WeatherObservation(
        zone_id=zone_id,
        latitude=zone.center_latitude,
        longitude=zone.center_longitude,
        temperature_c=data.temperature_c,
        humidity_pct=data.humidity_pct,
        wind_speed_ms=data.wind_speed_ms,
        weather_code=data.weather_code,
        weather_main=data.weather_main,
        weather_description=data.weather_description,
        weather_risk_score=data.risk_score,
        observed_at=datetime.now(timezone.utc),
    )
    db.add(obs)
    await db.commit()
    return {"message": "Weather updated", "risk_score": data.risk_score}
