"""
Authentication routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timedelta

from app.database.db import get_db
from app.models.user import User
from app.models.access_token import AccessToken, TokenType
from app.security.password import hash_password, verify_password
from app.security.jwt_handler import (
    create_access_token,
    create_refresh_token,
    generate_share_link_token,
    create_share_link_payload
)
from app.security.oauth2 import get_current_manager_user
from app.config import settings
import hashlib

router = APIRouter()


# Pydantic schemas
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class GenerateShareLinkRequest(BaseModel):
    user_id: str
    expiration_hours: Optional[int] = None


class ShareLinkResponse(BaseModel):
    share_link: str
    token_id: str
    expires_at: str
    single_use: bool = True


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Manager/Admin login endpoint
    """
    # Find user by email
    result = await db.execute(
        select(User).filter(User.email == request.email)
    )
    user = result.scalar_one_or_none()

    # Verify user and password
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )

    # Create access and refresh tokens
    access_token = create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value
    })

    refresh_token = create_refresh_token({
        "sub": str(user.id),
        "type": "refresh"
    })

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": user.to_dict()
    }


@router.post("/generate-link", response_model=ShareLinkResponse)
async def generate_share_link(
    request: GenerateShareLinkRequest,
    current_user: User = Depends(get_current_manager_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate share link for employee check-in
    Manager/Admin only
    """
    # Verify employee exists
    result = await db.execute(
        select(User).filter(User.id == request.user_id)
    )
    employee = result.scalar_one_or_none()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )

    # Generate secure token
    token = generate_share_link_token()
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    # Set expiration
    expiration_hours = request.expiration_hours or settings.SHARE_LINK_EXPIRE_HOURS
    expires_at = datetime.utcnow() + timedelta(hours=expiration_hours)

    # Create access token record
    access_token = AccessToken(
        user_id=request.user_id,
        token_hash=token_hash,
        token_type=TokenType.SHARE_LINK,
        expires_at=expires_at
    )

    db.add(access_token)
    await db.commit()

    # Construct share link
    share_link = f"http://localhost:3000/checkin/{token}"

    return {
        "share_link": share_link,
        "token_id": str(access_token.id),
        "expires_at": expires_at.isoformat(),
        "single_use": True
    }


@router.post("/verify-token")
async def verify_share_token(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify share link token
    """
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    # Find token
    result = await db.execute(
        select(AccessToken, User)
        .join(User, AccessToken.user_id == User.id)
        .filter(
            AccessToken.token_hash == token_hash,
            AccessToken.token_type == TokenType.SHARE_LINK,
            AccessToken.revoked == False
        )
    )
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    access_token, user = row

    # Check expiration
    if datetime.utcnow() > access_token.expires_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )

    return {
        "valid": True,
        "user_id": str(user.id),
        "employee_name": user.full_name,
        "expires_at": access_token.expires_at.isoformat()
    }


@router.post("/revoke-link/{token_id}")
async def revoke_share_link(
    token_id: str,
    current_user: User = Depends(get_current_manager_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Revoke a share link
    Manager/Admin only
    """
    result = await db.execute(
        select(AccessToken).filter(
            AccessToken.id == token_id,
            AccessToken.token_type == TokenType.SHARE_LINK
        )
    )
    token = result.scalar_one_or_none()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )

    token.revoked = True
    token.revoked_at = datetime.utcnow()

    await db.commit()

    return {
        "success": True,
        "message": "Share link revoked successfully"
    }
