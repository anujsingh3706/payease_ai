# backend/app/utils/jwt_handler.py

from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import JWTError, jwt
from app.config import settings
import logging

logger = logging.getLogger(__name__)


def create_access_token(data: Dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()

    expire = datetime.utcnow() + (
        expires_delta
        if expires_delta
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    to_encode.update({
        "exp": expire,
        "type": "access",
        "iat": datetime.utcnow()
    })

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: Dict) -> str:
    """Create JWT refresh token (longer lived)"""
    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "type": "refresh",
        "iat": datetime.utcnow()
    })

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[Dict]:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None


def verify_token_type(token: str, expected_type: str) -> Optional[Dict]:
    """Decode token and verify its type (access or refresh)"""
    payload = decode_token(token)
    if not payload:
        return None
    if payload.get("type") != expected_type:
        return None
    return payload