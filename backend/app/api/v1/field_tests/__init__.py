from fastapi import APIRouter, Depends
from app.core.security import get_current_user_id
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.field_test import FieldTest
from pydantic import BaseModel
from typing import Optional
router = APIRouter()

class FieldTestCreate(BaseModel):
    name: str
    scenario: Optional[str] = None
    location_description: Optional[str] = None

@router.post("/", summary="Create field test")
async def create_field_test(body: FieldTestCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user_id)):
    ft = FieldTest(**body.model_dump())
    db.add(ft)
    await db.commit()
    await db.refresh(ft)
    return {"id": str(ft.id), "name": ft.name, "status": ft.status}

@router.get("/", summary="List field tests")
async def list_field_tests(db: AsyncSession = Depends(get_db), _=Depends(get_current_user_id)):
    from sqlalchemy import select
    result = await db.scalars(select(FieldTest).limit(50))
    return [{"id": str(f.id), "name": f.name, "status": f.status, "is_demo": f.is_demo} for f in result.all()]
