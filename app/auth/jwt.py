import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt

from app.config import settings


def create_access_token(user_id: int, role: str) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: Dict[str, Any] = { "sub": str(user_id), "role": role,
                               "type": "access", "iat": now, "exp": expires_at }
    return jwt.encode( payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM )


def create_refresh_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    payload: Dict[str, Any] = { "sub": str(user_id), "type": "refresh", "iat": now, 
                               "exp": expires_at }
    return jwt.encode( payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM )


def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode( token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM] )


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()