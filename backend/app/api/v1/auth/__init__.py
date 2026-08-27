"""app/api/v1/auth/router.py — Authentication endpoints."""
from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    UserRole, create_access_token, create_refresh_token,
    decode_token, get_current_user_payload, hash_password, verify_password,
)
from app.database import get_db
from app.models.user import User
from app.models.audit import AuditLog

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="Password (min 8 chars)")
    full_name: str = Field(..., min_length=2, max_length=255)
    phone_number: str | None = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    nationality: str | None = None
    role: UserRole = UserRole.TOURIST

    model_config = {"json_schema_extra": {"example": {
        "email": "tourist@example.com",
        "password": "SecurePass123!",
        "full_name": "Anil Kumar",
        "phone_number": "+919876543210",
        "nationality": "Indian",
        "role": "TOURIST"
    }}}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    model_config = {"json_schema_extra": {"example": {
        "email": "tourist@example.com",
        "password": "SecurePass123!"
    }}}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    role: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserPublicResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
async def _audit(
    db: AsyncSession,
    action: str,
    user_id: uuid.UUID | None,
    request: Request,
    outcome: str = "SUCCESS",
    error: str | None = None,
) -> None:
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type="auth",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        request_id=request.headers.get("x-request-id"),
        outcome=outcome,
        error_message=error,
    )
    db.add(log)
    # commit happens via get_db dependency


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post(
    "/register",
    response_model=UserPublicResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    body: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> UserPublicResponse:
    # Check duplicate email
    existing = await db.scalar(select(User).where(User.email == body.email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=body.email,
        full_name=body.full_name,
        phone_number=body.phone_number,
        nationality=body.nationality,
        role=body.role,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.flush()  # get id before commit
    await _audit(db, "USER_REGISTER", user.id, request)
    await db.commit()
    await db.refresh(user)

    logger.info("New user registered: %s role=%s", user.id, user.role)
    return UserPublicResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive JWT tokens",
)
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    from app.config import settings as s

    user = await db.scalar(select(User).where(User.email == body.email))
    if not user or not verify_password(body.password, user.hashed_password):
        await _audit(db, "USER_LOGIN_FAILED", None, request, "FAILURE", "Invalid credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    access_token = create_access_token(str(user.id), user.role)
    refresh_token = create_refresh_token(str(user.id), user.role)

    # Store hashed refresh token
    user.refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    await _audit(db, "USER_LOGIN", user.id, request)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=s.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=str(user.id),
        role=user.role,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token using refresh token",
)
async def refresh_token(
    body: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    from app.core.security import TokenType
    from app.config import settings as s

    payload = decode_token(body.refresh_token)
    if payload.get("type") != TokenType.REFRESH:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not a refresh token")

    user_id = payload.get("sub")
    user = await db.get(User, uuid.UUID(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # Validate stored hash
    incoming_hash = hashlib.sha256(body.refresh_token.encode()).hexdigest()
    if user.refresh_token_hash != incoming_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token reuse detected")

    new_access = create_access_token(str(user.id), user.role)
    new_refresh = create_refresh_token(str(user.id), user.role)
    user.refresh_token_hash = hashlib.sha256(new_refresh.encode()).hexdigest()
    await _audit(db, "TOKEN_REFRESH", user.id, request)

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="bearer",
        expires_in=s.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=str(user.id),
        role=user.role,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout (invalidate refresh token)",
)
async def logout(
    request: Request,
    payload: dict = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db),
) -> None:
    user_id = uuid.UUID(payload["sub"])
    user = await db.get(User, user_id)
    if user:
        user.refresh_token_hash = None
    await _audit(db, "USER_LOGOUT", user_id, request)
