"""
app/core/security.py — JWT, password hashing, RBAC.

Implements:
- bcrypt password hashing (never stores plaintext)
- JWT access + refresh token generation and verification
- Role-based access control dependency
- Fernet symmetric encryption for sensitive data at rest
"""
from __future__ import annotations

import base64
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
import bcrypt

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Password hashing (direct bcrypt to avoid passlib 4.x compatibility issues)
# ---------------------------------------------------------------------------
def hash_password(plain: str) -> str:
    """Hash a plaintext password using bcrypt."""
    pwd_bytes = plain.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the bcrypt hash."""
    try:
        pwd_bytes = plain.encode("utf-8")[:72]
        hashed_bytes = hashed.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


def create_access_token(
    subject: str,
    role: str,
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a short-lived JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload: Dict[str, Any] = {
        "sub": subject,
        "role": role,
        "type": TokenType.ACCESS,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str, role: str) -> str:
    """Create a long-lived JWT refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload: Dict[str, Any] = {
        "sub": subject,
        "role": role,
        "type": TokenType.REFRESH,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token. Raises HTTPException on failure."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as exc:
        logger.warning("JWT decode error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# HTTP Bearer scheme
# ---------------------------------------------------------------------------
_bearer = HTTPBearer(auto_error=True)


def get_current_user_payload(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> Dict[str, Any]:
    """FastAPI dependency — decode Bearer token, return payload."""
    payload = decode_token(credentials.credentials)
    if payload.get("type") != TokenType.ACCESS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not an access token",
        )
    return payload


def get_current_user_id(
    payload: Dict[str, Any] = Depends(get_current_user_payload),
) -> str:
    """FastAPI dependency — return the authenticated user ID (str UUID)."""
    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
    return user_id


def get_current_role(
    payload: Dict[str, Any] = Depends(get_current_user_payload),
) -> str:
    """FastAPI dependency — return the authenticated user role."""
    return payload.get("role", "TOURIST")


# ---------------------------------------------------------------------------
# RBAC — Role Enum & Dependency Factories
# ---------------------------------------------------------------------------
class UserRole(str, Enum):
    TOURIST = "TOURIST"
    RESPONDER = "RESPONDER"
    ADMIN = "ADMIN"


def require_roles(*roles: UserRole):
    """Return a FastAPI dependency that enforces one of the given roles."""

    def _check(payload: Dict[str, Any] = Depends(get_current_user_payload)) -> Dict[str, Any]:
        user_role = payload.get("role", "")
        if user_role not in [r.value for r in roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in roles]}",
            )
        return payload

    return _check


require_tourist = require_roles(UserRole.TOURIST, UserRole.RESPONDER, UserRole.ADMIN)
require_responder = require_roles(UserRole.RESPONDER, UserRole.ADMIN)
require_admin = require_roles(UserRole.ADMIN)


# ---------------------------------------------------------------------------
# Fernet encryption for sensitive data at rest
# ---------------------------------------------------------------------------
def _get_fernet() -> Optional[Fernet]:
    if not settings.ENCRYPTION_KEY:
        return None
    try:
        return Fernet(settings.ENCRYPTION_KEY.encode())
    except Exception as exc:
        logger.error("Failed to initialise Fernet: %s", exc)
        return None


def encrypt_sensitive(plaintext: str) -> str:
    """Encrypt a plaintext string. Returns base64-encoded ciphertext."""
    fernet = _get_fernet()
    if fernet is None:
        raise RuntimeError("ENCRYPTION_KEY not configured — cannot encrypt sensitive data")
    return fernet.encrypt(plaintext.encode()).decode()


def decrypt_sensitive(ciphertext: str) -> str:
    """Decrypt a previously encrypted string."""
    fernet = _get_fernet()
    if fernet is None:
        raise RuntimeError("ENCRYPTION_KEY not configured — cannot decrypt sensitive data")
    try:
        return fernet.decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Decryption failed — invalid or tampered data") from exc


# ---------------------------------------------------------------------------
# Identity hash for blockchain (SHA-256 of canonical encrypted identity blob)
# ---------------------------------------------------------------------------
def compute_identity_hash(user_id: str, full_name: str, passport_hash: str) -> str:
    """
    Compute a SHA-256 hash of the canonical identity representation.
    This hash is stored on-chain; personal data never leaves PostgreSQL.
    """
    canonical = f"{user_id}:{full_name.strip().upper()}:{passport_hash}"
    return hashlib.sha256(canonical.encode()).hexdigest()
