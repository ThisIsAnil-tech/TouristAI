"""app/api/v1/blockchain/__init__.py — Blockchain identity API endpoints."""
from __future__ import annotations

import hashlib
import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id, require_admin
from app.database import get_db
from app.models.blockchain import BlockchainTransaction, EmergencyAccessGrant
from app.models.responder import Responder
from app.models.sos import SosEvent
from app.models.user import User
from app.services.blockchain.identity_service import BlockchainIdentityService, BlockchainNotConfiguredError

logger = logging.getLogger(__name__)
router = APIRouter()
_svc = BlockchainIdentityService()


class RegisterIdentityRequest(BaseModel):
    """Optionally provide passport/medical data to build identity hash."""
    passport_number: Optional[str] = None
    nationality: Optional[str] = None


class RegisterIdentityResponse(BaseModel):
    success: bool
    tx_hash: Optional[str]
    block_number: Optional[int]
    gas_used: Optional[int]
    latency_ms: float
    identity_hash: Optional[str]
    error: Optional[str]


class GrantAccessResponse(BaseModel):
    success: bool
    grant_id: uuid.UUID
    tx_hash: Optional[str]
    latency_ms: float
    error: Optional[str]


@router.post(
    "/register",
    response_model=RegisterIdentityResponse,
    summary="Register identity on blockchain",
)
async def register_identity(
    user_id_str: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> RegisterIdentityResponse:
    uid = uuid.UUID(user_id_str)
    user = await db.get(User, uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.blockchain_registered:
        return RegisterIdentityResponse(
            success=True, tx_hash=None, block_number=None, gas_used=None,
            latency_ms=0.0, identity_hash=user.identity_hash,
            error="Already registered"
        )

    # Compute identity hash (SHA-256 of email + phone — public fields only)
    canonical = f"{user.id}:{user.email}:{user.phone_number or ''}:{user.nationality or ''}"
    identity_hash = hashlib.sha256(canonical.encode()).hexdigest()
    user.identity_hash = identity_hash

    try:
        result = await _svc.register_identity(user, db)
    except BlockchainNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    if result.success:
        user.blockchain_registered = True

    await db.commit()
    return RegisterIdentityResponse(
        success=result.success,
        tx_hash=result.tx_hash,
        block_number=result.block_number,
        gas_used=result.gas_used,
        latency_ms=result.latency_ms,
        identity_hash=identity_hash,
        error=result.error,
    )


@router.post(
    "/grant-access/{sos_event_id}/{responder_id}",
    response_model=GrantAccessResponse,
    summary="Grant emergency access to a responder (admin/system)",
)
async def grant_access(
    sos_event_id: uuid.UUID,
    responder_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
) -> GrantAccessResponse:
    sos = await db.get(SosEvent, sos_event_id)
    if not sos:
        raise HTTPException(status_code=404, detail="SOS event not found")

    responder = await db.get(Responder, responder_id)
    if not responder:
        raise HTTPException(status_code=404, detail="Responder not found")

    # For demo: use responder user_id as wallet address placeholder
    responder_wallet = settings_wallet(responder)

    try:
        tx_result = await _svc.grant_emergency_access(
            tourist_user_id=sos.user_id,
            responder_wallet=responder_wallet,
            sos_event_id=sos_event_id,
            db=db,
        )
    except BlockchainNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    from datetime import datetime, timezone
    grant = EmergencyAccessGrant(
        sos_event_id=sos_event_id,
        responder_id=responder_id,
        tourist_user_id=sos.user_id,
        grant_tx_hash=tx_result.tx_hash,
        is_active=tx_result.success,
        granted_at=datetime.now(timezone.utc),
    )
    db.add(grant)
    await db.commit()
    await db.refresh(grant)

    return GrantAccessResponse(
        success=tx_result.success,
        grant_id=grant.id,
        tx_hash=tx_result.tx_hash,
        latency_ms=tx_result.latency_ms,
        error=tx_result.error,
    )


@router.post(
    "/revoke-access/{grant_id}",
    summary="Revoke emergency access grant",
)
async def revoke_access(
    grant_id: uuid.UUID,
    reason: str = "SOS resolved",
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    grant = await db.get(EmergencyAccessGrant, grant_id)
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")
    if not grant.is_active:
        return {"message": "Grant already revoked"}

    responder = await db.get(Responder, grant.responder_id)
    responder_wallet = settings_wallet(responder) if responder else "0x0"

    try:
        tx_result = await _svc.revoke_emergency_access(
            tourist_user_id=grant.tourist_user_id,
            responder_wallet=responder_wallet,
            sos_event_id=grant.sos_event_id,
            db=db,
        )
    except BlockchainNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    from datetime import datetime, timezone
    grant.is_active = False
    grant.revoke_tx_hash = tx_result.tx_hash
    grant.revoked_at = datetime.now(timezone.utc)
    grant.revocation_reason = reason
    await db.commit()

    return {"success": tx_result.success, "grant_id": str(grant_id),
            "tx_hash": tx_result.tx_hash}


@router.get("/verify/{user_id_str}", summary="Verify if a user is registered on blockchain")
async def verify_identity(
    user_id_str: str,
    _=Depends(get_current_user_id),
):
    try:
        uid = uuid.UUID(user_id_str)
        registered = await _svc.is_registered(uid)
        return {"user_id": user_id_str, "blockchain_registered": registered}
    except BlockchainNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/transactions", summary="List blockchain transactions (admin)")
async def list_transactions(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    result = await db.scalars(
        select(BlockchainTransaction).order_by(BlockchainTransaction.created_at.desc()).limit(limit)
    )
    txs = result.all()
    return [{"id": str(t.id), "tx_type": t.tx_type, "tx_hash": t.tx_hash,
             "status": t.status, "latency_ms": t.latency_ms} for t in txs]


def settings_wallet(responder) -> str:
    """
    Derive a deterministic wallet address placeholder from responder ID.
    In production, responders register their actual wallet address.
    """
    from app.config import settings
    if not responder:
        return "0x0000000000000000000000000000000000000000"
    # Use keccak of responder ID as placeholder (40-char hex)
    h = hashlib.sha256(str(responder.id).encode()).hexdigest()[:40]
    return "0x" + h
