from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_user_id, require_admin
from app.database import get_db
from app.models.responder import Responder
import uuid
router = APIRouter()

@router.get("/", summary="List responders")
async def list_responders(db: AsyncSession = Depends(get_db), _=Depends(get_current_user_id)):
    result = await db.scalars(select(Responder).limit(50))
    return [{"id": str(r.id), "organization": r.organization, "is_available": r.is_available} for r in result.all()]

@router.patch("/{responder_id}/availability", summary="Update responder availability")
async def update_availability(responder_id: uuid.UUID, available: bool, db: AsyncSession = Depends(get_db), _=Depends(get_current_user_id)):
    r = await db.get(Responder, responder_id)
    if r:
        r.is_available = available
        await db.commit()
    return {"responder_id": str(responder_id), "is_available": available}
