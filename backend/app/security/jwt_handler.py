"""
JWT token generation and validation
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from app.config import settings
import secrets


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token

    Args:
        data: Data to encode in token
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "iss": settings.APP_NAME
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create JWT refresh token with longer expiration

    Args:
        data: Data to encode in token

    Returns:
        Encoded JWT refresh token
    """
    expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return create_access_token(data, expires_delta)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate JWT token

    Args:
        token: JWT token to decode

    Returns:
        Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_iss": True},
            issuer=settings.APP_NAME
        )
        return payload
    except JWTError:
        return None


def generate_share_link_token() -> str:
    """
    Generate a secure random token for share links

    Returns:
        Secure random token (URL-safe)
    """
    return secrets.token_urlsafe(32)


def create_share_link_payload(user_id: str, device_fingerprint: Optional[str] = None) -> Dict[str, Any]:
    """
    Create payload for share link token

    Args:
        user_id: User ID
        device_fingerprint: Optional device fingerprint

    Returns:
        Token payload dictionary
    """
    expires_delta = timedelta(hours=settings.SHARE_LINK_EXPIRE_HOURS)
    expire = datetime.utcnow() + expires_delta

    payload = {
        "sub": user_id,
        "type": "share_link",
        "exp": expire,
        "iat": datetime.utcnow(),
    }

    if device_fingerprint:
        payload["device"] = device_fingerprint

    return payload
