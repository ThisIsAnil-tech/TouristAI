"""app/api/v1/users/__init__.py — User profile endpoints."""
from __future__ import annotations

import uuid
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id, get_current_user_payload, require_admin
from app.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


class UserProfileResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone_number: Optional[str]
    nationality: Optional[str]
    role: str
    is_active: bool
    is_verified: bool
    blockchain_registered: bool
    last_latitude: Optional[float]
    last_longitude: Optional[float]
    last_location_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    nationality: Optional[str] = None


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current user profile",
)
async def get_my_profile(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    user = await db.get(User, uuid.UUID(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _to_response(user)


@router.patch(
    "/me",
    response_model=UserProfileResponse,
    summary="Update current user profile",
)
async def update_my_profile(
    body: UpdateProfileRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    user = await db.get(User, uuid.UUID(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if body.full_name is not None:
        user.full_name = body.full_name
    if body.phone_number is not None:
        user.phone_number = body.phone_number
    if body.nationality is not None:
        user.nationality = body.nationality

    await db.commit()
    await db.refresh(user)
    return _to_response(user)


@router.get(
    "/{user_id}",
    response_model=UserProfileResponse,
    summary="Get user by ID (admin only)",
    dependencies=[Depends(require_admin)],
)
async def get_user_by_id(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _to_response(user)


def _to_response(user: User) -> UserProfileResponse:
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone_number=user.phone_number,
        nationality=user.nationality,
        role=user.role,
        is_active=user.is_active,
        is_verified=user.is_verified,
        blockchain_registered=user.blockchain_registered,
        last_latitude=user.last_latitude,
        last_longitude=user.last_longitude,
        last_location_at=user.last_location_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
