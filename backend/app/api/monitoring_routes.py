"""
Monitoring routes for check-in/check-out
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.database.db import get_db
from app.services.monitoring_service import MonitoringService

router = APIRouter()


# Pydantic schemas
class CheckinRequest(BaseModel):
    token: str
    photo_base64: str
    latitude: float
    longitude: float
    accuracy: Optional[int] = None
    altitude: Optional[float] = None
    device_fingerprint: Optional[str] = None


class CheckoutRequest(BaseModel):
    session_id: str
    photo_base64: str
    latitude: float
    longitude: float
    accuracy: Optional[int] = None
    altitude: Optional[float] = None


@router.post("/checkin")
async def checkin(
    request: CheckinRequest,
    req: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Employee check-in endpoint
    """
    # Verify token first
    from app.api.auth_routes import verify_share_token

    token_data = await verify_share_token(request.token, db)
    user_id = token_data["user_id"]

    # Get client IP
    ip_address = req.client.host

    # Process check-in
    result = await MonitoringService.checkin(
        db=db,
        user_id=user_id,
        photo_base64=request.photo_base64,
        latitude=request.latitude,
        longitude=request.longitude,
        accuracy=request.accuracy,
        altitude=request.altitude,
        ip_address=ip_address,
        device_fingerprint=request.device_fingerprint
    )

    return result


@router.post("/checkout")
async def checkout(
    request: CheckoutRequest,
    req: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Employee check-out endpoint
    """
    # Get client IP
    ip_address = req.client.host

    # Extract user_id from session (simplified - should verify ownership)
    from sqlalchemy import select
    from app.models.session import Session

    session_result = await db.execute(
        select(Session).filter(Session.id == request.session_id)
    )
    session = session_result.scalar_one_or_none()

    if not session:
        return {"error": "Session not found"}

    user_id = str(session.user_id)

    # Process check-out
    result = await MonitoringService.checkout(
        db=db,
        session_id=request.session_id,
        user_id=user_id,
        photo_base64=request.photo_base64,
        latitude=request.latitude,
        longitude=request.longitude,
        accuracy=request.accuracy,
        altitude=request.altitude,
        ip_address=ip_address
    )

    return result


@router.get("/session/{session_id}")
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get session details
    """
    result = await MonitoringService.get_session_details(db, session_id)

    if not result:
        return {"error": "Session not found"}

    return result
