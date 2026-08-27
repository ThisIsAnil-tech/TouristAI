"""app/workers/scheduler.py — APScheduler background tasks."""
from __future__ import annotations

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.config import settings

logger = logging.getLogger(__name__)
_scheduler: AsyncIOScheduler | None = None


async def _update_all_zone_weather() -> None:
    """Fetch fresh weather for all active zones."""
    from app.database import get_db_context
    from app.models.zone import GeographicZone
    from app.services.risk.weather_provider import OpenWeatherMapProvider, WeatherProviderUnavailableError
    from app.models.weather import WeatherObservation
    from datetime import datetime, timezone
    from sqlalchemy import select

    async with get_db_context() as db:
        result = await db.scalars(
            select(GeographicZone).where(
                GeographicZone.is_active == True,
                GeographicZone.center_latitude.isnot(None),
            )
        )
        zones = result.all()
        provider = OpenWeatherMapProvider()
        for zone in zones:
            try:
                data = await provider.get_weather(zone.center_latitude, zone.center_longitude)
                obs = WeatherObservation(
                    zone_id=zone.id,
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
            except WeatherProviderUnavailableError:
                logger.warning("Weather provider unavailable — skipping zone %s", zone.id)
            except Exception as exc:
                logger.error("Weather update failed for zone %s: %s", zone.id, exc)
        logger.info("Weather update completed for %d zones", len(zones))


async def _recalculate_all_zone_risks() -> None:
    """Recalculate risk scores for all active zones."""
    from app.database import get_db_context
    from app.models.zone import GeographicZone
    from app.services.risk.risk_calculator import RiskCalculator
    from sqlalchemy import select

    async with get_db_context() as db:
        result = await db.scalars(select(GeographicZone).where(GeographicZone.is_active == True))
        zones = result.all()
        calculator = RiskCalculator()
        for zone in zones:
            try:
                calc_result = await calculator.calculate_for_zone(db, zone)
                await calculator.persist(db, calc_result)
            except Exception as exc:
                logger.error("Risk recalculation failed for zone %s: %s", zone.id, exc)
        logger.info("Risk recalculation completed for %d zones", len(zones))


async def _cleanup_expired_access() -> None:
    """Revoke expired emergency access grants."""
    from app.database import get_db_context
    from app.models.blockchain import EmergencyAccessGrant
    from app.models.sos import SosEvent, SosStatus
    from datetime import datetime, timezone
    from sqlalchemy import select

    async with get_db_context() as db:
        # Revoke grants where SOS is resolved/cancelled
        result = await db.scalars(
            select(EmergencyAccessGrant).where(EmergencyAccessGrant.is_active == True)
        )
        grants = result.all()
        for grant in grants:
            sos = await db.get(SosEvent, grant.sos_event_id)
            if sos and sos.status in (SosStatus.RESOLVED, SosStatus.FALSE_ALARM, SosStatus.CANCELLED):
                grant.is_active = False
                grant.revoked_at = datetime.now(timezone.utc)
                grant.revocation_reason = "SOS resolved"
        logger.info("Expired access cleanup completed")


async def start_scheduler() -> None:
    global _scheduler
    _scheduler = AsyncIOScheduler()

    _scheduler.add_job(
        _update_all_zone_weather,
        trigger=IntervalTrigger(minutes=settings.WEATHER_UPDATE_INTERVAL_MINUTES),
        id="weather_update",
        replace_existing=True,
    )
    _scheduler.add_job(
        _recalculate_all_zone_risks,
        trigger=IntervalTrigger(minutes=settings.RISK_RECALC_INTERVAL_MINUTES),
        id="risk_recalculation",
        replace_existing=True,
    )
    _scheduler.add_job(
        _cleanup_expired_access,
        trigger=IntervalTrigger(hours=settings.CLEANUP_INTERVAL_HOURS),
        id="access_cleanup",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("APScheduler started with %d jobs", len(_scheduler.get_jobs()))


async def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    logger.info("APScheduler stopped")
