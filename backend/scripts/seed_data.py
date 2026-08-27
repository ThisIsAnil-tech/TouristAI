"""
scripts/seed_data.py — Seed database with initial development data.

Seeds:
  - 3 geographic zones (Kerala tourist regions)
  - 2 responder accounts
  - 2 tourist users
  - Sample incidents and weather observations

Usage:
    python scripts/seed_data.py

Prerequisites:
    - PostgreSQL running and DATABASE_URL set in .env
    - Alembic migrations applied (alembic upgrade head)
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import settings
from app.core.security import get_password_hash
from app.models.zone import GeographicZone, ZoneRiskLevel
from app.models.user import User, UserRole
from app.models.responder import Responder
from app.models.incident import Incident, IncidentSeverity, IncidentCategory
from app.models.weather import WeatherObservation


async def seed(db: AsyncSession) -> None:
    print("Seeding geographic zones...")
    zones = [
        GeographicZone(
            id=uuid.uuid4(),
            name="Munnar Hill Station",
            min_latitude=10.0, max_latitude=10.2,
            min_longitude=77.0, max_longitude=77.2,
            center_latitude=10.0889, center_longitude=77.0597,
            is_high_risk=False, risk_level=ZoneRiskLevel.LOW, is_active=True,
        ),
        GeographicZone(
            id=uuid.uuid4(),
            name="Varkala Cliff Beach",
            min_latitude=8.7, max_latitude=8.8,
            min_longitude=76.6, max_longitude=76.7,
            center_latitude=8.7379, center_longitude=76.7115,
            is_high_risk=True, risk_level=ZoneRiskLevel.HIGH, is_active=True,
        ),
        GeographicZone(
            id=uuid.uuid4(),
            name="Wayanad Wildlife Corridor",
            min_latitude=11.5, max_latitude=11.8,
            min_longitude=75.9, max_longitude=76.1,
            center_latitude=11.6854, center_longitude=76.1320,
            is_high_risk=True, risk_level=ZoneRiskLevel.MEDIUM, is_active=True,
        ),
    ]
    for z in zones:
        db.add(z)
    await db.flush()

    print("Seeding tourist users...")
    tourist1 = User(
        id=uuid.uuid4(),
        email="tourist1@example.com",
        full_name="Alice Tourist",
        hashed_password=get_password_hash("Tourist123!"),
        role=UserRole.TOURIST,
        phone_number="+919876543210",
        nationality="Indian",
        is_active=True, is_verified=True,
    )
    tourist2 = User(
        id=uuid.uuid4(),
        email="tourist2@example.com",
        full_name="Bob Traveller",
        hashed_password=get_password_hash("Traveller456!"),
        role=UserRole.TOURIST,
        phone_number="+447911123456",
        nationality="British",
        is_active=True, is_verified=True,
    )
    admin_user = User(
        id=uuid.uuid4(),
        email="admin@touristsafety.com",
        full_name="System Admin",
        hashed_password=get_password_hash("Admin@SuperSecret!"),
        role=UserRole.ADMIN,
        is_active=True, is_verified=True,
    )
    for u in [tourist1, tourist2, admin_user]:
        db.add(u)
    await db.flush()

    print("Seeding responders...")
    responders = [
        Responder(
            id=uuid.uuid4(),
            user_id=None,
            name="Kerala Police Emergency",
            organization="Kerala Police",
            contact_phone="+91-100",
            contact_email="emergency@keralapolice.gov.in",
            specialization="POLICE",
            zone_id=zones[0].id,
            is_available=True, is_verified=True,
        ),
        Responder(
            id=uuid.uuid4(),
            user_id=None,
            name="Wayanad Forest Rangers",
            organization="Kerala Forest Dept",
            contact_phone="+91-9496060900",
            contact_email="rangers@wayanad.gov.in",
            specialization="WILDLIFE_RESCUE",
            zone_id=zones[2].id,
            is_available=True, is_verified=True,
        ),
    ]
    for r in responders:
        db.add(r)
    await db.flush()

    print("Seeding sample incidents...")
    incidents = [
        Incident(
            id=uuid.uuid4(),
            zone_id=zones[1].id,
            title="Cliff edge fall risk",
            description="Slippery path near north cliff edge after rains",
            severity=IncidentSeverity.HIGH,
            category=IncidentCategory.ACCIDENT,
            latitude=8.7379, longitude=76.7115,
            occurred_at=datetime.now(timezone.utc),
            is_active=True,
        ),
        Incident(
            id=uuid.uuid4(),
            zone_id=zones[2].id,
            title="Wild elephant sighting",
            description="Elephant herd near tourist trail 3",
            severity=IncidentSeverity.CRITICAL,
            category=IncidentCategory.WILDLIFE,
            latitude=11.6854, longitude=76.1320,
            occurred_at=datetime.now(timezone.utc),
            is_active=True,
        ),
    ]
    for i in incidents:
        db.add(i)

    await db.commit()
    print("\n✅ Seed data inserted successfully!")
    print(f"   Zones: {len(zones)}")
    print(f"   Users: 3 (2 tourists + 1 admin)")
    print(f"   Responders: {len(responders)}")
    print(f"   Incidents: {len(incidents)}")
    print("\n   Admin login: admin@touristsafety.com / Admin@SuperSecret!")
    print("   Tourist login: tourist1@example.com / Tourist123!")


async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        try:
            await seed(db)
        except Exception as exc:
            await db.rollback()
            print(f"❌ Seed failed: {exc}")
            raise
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
