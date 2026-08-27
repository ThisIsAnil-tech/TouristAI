"""app/api/v1/contacts/__init__.py — Emergency contacts endpoints."""
from __future__ import annotations

import uuid
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.database import get_db
from app.models.user import EmergencyContact

logger = logging.getLogger(__name__)
router = APIRouter()


class ContactRequest(BaseModel):
    name: str
    relationship: Optional[str] = None
    phone_number: str
    email: Optional[str] = None
    is_primary: bool = False
    notify_on_sos: bool = True


class ContactResponse(BaseModel):
    id: uuid.UUID
    name: str
    relationship: Optional[str]
    phone_number: str
    email: Optional[str]
    is_primary: bool
    notify_on_sos: bool


@router.get("/", response_model=List[ContactResponse], summary="List emergency contacts")
async def list_contacts(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> List[ContactResponse]:
    result = await db.scalars(
        select(EmergencyContact).where(EmergencyContact.user_id == uuid.UUID(user_id))
    )
    contacts = result.all()
    return [_to_response(c) for c in contacts]


@router.post("/", response_model=ContactResponse, status_code=status.HTTP_201_CREATED,
             summary="Add emergency contact")
async def add_contact(
    body: ContactRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ContactResponse:
    contact = EmergencyContact(
        user_id=uuid.UUID(user_id),
        name=body.name,
        relationship=body.relationship,
        phone_number=body.phone_number,
        email=body.email,
        is_primary=body.is_primary,
        notify_on_sos=body.notify_on_sos,
    )
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return _to_response(contact)


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Remove emergency contact")
async def remove_contact(
    contact_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    contact = await db.get(EmergencyContact, contact_id)
    if not contact or str(contact.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Contact not found")
    await db.delete(contact)
    await db.commit()


def _to_response(c: EmergencyContact) -> ContactResponse:
    return ContactResponse(
        id=c.id,
        name=c.name,
        relationship=c.relationship,
        phone_number=c.phone_number,
        email=c.email,
        is_primary=c.is_primary,
        notify_on_sos=c.notify_on_sos,
    )
