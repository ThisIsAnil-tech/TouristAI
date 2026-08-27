"""Incidents router."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_user_id
from app.database import get_db
from app.models.incident import Incident

router = APIRouter()

@router.get("/", summary="List incidents")
async def list_incidents(db: AsyncSession = Depends(get_db), _=Depends(get_current_user_id)):
    result = await db.scalars(select(Incident).limit(100))
    incidents = result.all()
    return [{"id": str(i.id), "title": i.title, "severity": i.severity, "occurred_at": i.occurred_at.isoformat()} for i in incidents]
