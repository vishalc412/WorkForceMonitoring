"""
Dashboard routes for manager interface
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database.db import get_db
from app.models.user import User
from app.security.oauth2 import get_current_manager_user
from app.services.monitoring_service import MonitoringService

router = APIRouter()


@router.get("/sessions/active")
async def get_active_sessions(
    current_user: User = Depends(get_current_manager_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all active sessions for manager dashboard
    Manager/Admin only
    """
    sessions = await MonitoringService.get_active_sessions(db)

    return {
        "active_sessions": sessions,
        "total_active": len(sessions),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/stats")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_manager_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get dashboard statistics
    Manager/Admin only
    """
    from sqlalchemy import select, func
    from app.models.session import Session, SessionStatus
    from datetime import datetime, timedelta

    # Today's stats
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())

    # Total active employees
    active_count = await db.scalar(
        select(func.count(Session.id)).filter(
            Session.status == SessionStatus.ACTIVE
        )
    )

    # Today's check-ins
    today_checkins = await db.scalar(
        select(func.count(Session.id)).filter(
            Session.checkin_time >= today_start
        )
    )

    # Today's completed sessions
    today_completed = await db.scalar(
        select(func.count(Session.id)).filter(
            Session.checkin_time >= today_start,
            Session.status == SessionStatus.COMPLETED
        )
    )

    return {
        "active_employees": active_count or 0,
        "today_checkins": today_checkins or 0,
        "today_completed": today_completed or 0,
        "timestamp": datetime.utcnow().isoformat()
    }


from datetime import datetime
