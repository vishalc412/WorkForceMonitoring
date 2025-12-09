"""
Monitoring service for check-in/check-out workflow
"""
from datetime import datetime
from typing import Dict, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from fastapi import HTTPException, status

from app.models.session import Session, SessionStatus
from app.models.user import User
from app.models.location import LocationType
from app.models.photo import PhotoType
from app.services.camera_service import CameraService
from app.services.location_service import LocationService


class MonitoringService:
    """Service for managing employee check-in/check-out sessions"""

    @staticmethod
    async def checkin(
        db: AsyncSession,
        user_id: str,
        photo_base64: str,
        latitude: float,
        longitude: float,
        accuracy: Optional[int],
        altitude: Optional[float],
        ip_address: Optional[str],
        device_fingerprint: Optional[str]
    ) -> Dict[str, any]:
        """
        Process employee check-in

        Args:
            db: Database session
            user_id: User ID
            photo_base64: Base64 encoded photo
            latitude: GPS latitude
            longitude: GPS longitude
            accuracy: GPS accuracy in meters
            altitude: GPS altitude
            ip_address: Client IP address
            device_fingerprint: Device fingerprint

        Returns:
            Dictionary with check-in result
        """
        # Validate location accuracy
        is_valid, error_msg = await LocationService.validate_location_accuracy(
            latitude, longitude, accuracy
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

        # Check for existing active session
        result = await db.execute(
            select(Session).filter(
                and_(
                    Session.user_id == user_id,
                    Session.status == SessionStatus.ACTIVE
                )
            )
        )
        existing_session = result.scalar_one_or_none()

        if existing_session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Active session already exists. Please check out first."
            )

        # Create new session
        session = Session(
            user_id=user_id,
            checkin_time=datetime.utcnow(),
            status=SessionStatus.ACTIVE
        )
        db.add(session)
        await db.flush()

        # Process and verify photo
        photo_result = await CameraService.process_and_verify_photo(
            db=db,
            base64_image=photo_base64,
            user_id=user_id,
            session_id=str(session.id),
            photo_type=PhotoType.CHECKIN
        )

        if not photo_result.get("success"):
            # Rollback session if photo verification fails
            await db.delete(session)
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=photo_result.get("error", "Photo verification failed"),
                headers={"X-Error-Code": photo_result.get("error_code", "PHOTO_ERROR")}
            )

        # Create location record
        location = await LocationService.create_location_record(
            db=db,
            session_id=str(session.id),
            latitude=latitude,
            longitude=longitude,
            accuracy_meters=accuracy,
            altitude=altitude,
            ip_address=ip_address,
            location_type=LocationType.CHECKIN
        )

        # Update session with photo and location IDs
        session.checkin_photo_id = photo_result.get("photo_id")
        session.checkin_location_id = str(location.id)

        # Check for location anomalies
        is_anomaly, anomaly_data = await LocationService.detect_location_anomaly(
            db, user_id, latitude, longitude
        )

        await db.commit()

        return {
            "success": True,
            "session_id": str(session.id),
            "checkin_time": session.checkin_time.isoformat(),
            "status": session.status.value,
            "location": {
                "latitude": float(latitude),
                "longitude": float(longitude),
                "within_geofence": location.is_within_geofence,
                "address": location.address
            },
            "photo_verified": True,
            "liveness_score": photo_result.get("liveness_score"),
            "anomaly_detected": is_anomaly,
            "anomaly_data": anomaly_data if is_anomaly else None
        }

    @staticmethod
    async def checkout(
        db: AsyncSession,
        session_id: str,
        user_id: str,
        photo_base64: str,
        latitude: float,
        longitude: float,
        accuracy: Optional[int],
        altitude: Optional[float],
        ip_address: Optional[str]
    ) -> Dict[str, any]:
        """
        Process employee check-out

        Args:
            db: Database session
            session_id: Session ID
            user_id: User ID
            photo_base64: Base64 encoded photo
            latitude: GPS latitude
            longitude: GPS longitude
            accuracy: GPS accuracy
            altitude: GPS altitude
            ip_address: Client IP address

        Returns:
            Dictionary with check-out result
        """
        # Validate location
        is_valid, error_msg = await LocationService.validate_location_accuracy(
            latitude, longitude, accuracy
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

        # Get session
        result = await db.execute(
            select(Session).filter(
                and_(
                    Session.id == session_id,
                    Session.user_id == user_id,
                    Session.status == SessionStatus.ACTIVE
                )
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active session not found"
            )

        # Process and verify photo
        photo_result = await CameraService.process_and_verify_photo(
            db=db,
            base64_image=photo_base64,
            user_id=user_id,
            session_id=session_id,
            photo_type=PhotoType.CHECKOUT
        )

        if not photo_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=photo_result.get("error", "Photo verification failed"),
                headers={"X-Error-Code": photo_result.get("error_code", "PHOTO_ERROR")}
            )

        # Create location record
        location = await LocationService.create_location_record(
            db=db,
            session_id=session_id,
            latitude=latitude,
            longitude=longitude,
            accuracy_meters=accuracy,
            altitude=altitude,
            ip_address=ip_address,
            location_type=LocationType.CHECKOUT
        )

        # Update session
        session.checkout_time = datetime.utcnow()
        session.checkout_photo_id = photo_result.get("photo_id")
        session.checkout_location_id = str(location.id)
        session.status = SessionStatus.COMPLETED

        # Calculate duration
        duration = session.checkout_time - session.checkin_time
        session.duration_minutes = int(duration.total_seconds() / 60)

        await db.commit()

        return {
            "success": True,
            "session_id": str(session.id),
            "checkout_time": session.checkout_time.isoformat(),
            "duration_minutes": session.duration_minutes,
            "duration_hours": round(session.duration_minutes / 60, 2),
            "status": session.status.value,
            "location": {
                "latitude": float(latitude),
                "longitude": float(longitude),
                "within_geofence": location.is_within_geofence,
                "address": location.address
            }
        }

    @staticmethod
    async def get_active_sessions(
        db: AsyncSession,
        company_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Get all active sessions

        Args:
            db: Database session
            company_id: Optional company ID filter

        Returns:
            List of active sessions with user and location data
        """
        from app.models.location import Location

        query = (
            select(Session, User, Location)
            .join(User, Session.user_id == User.id)
            .outerjoin(Location, Session.checkin_location_id == Location.id)
            .filter(Session.status == SessionStatus.ACTIVE)
            .order_by(Session.checkin_time.desc())
        )

        result = await db.execute(query)
        rows = result.all()

        active_sessions = []
        for session, user, location in rows:
            # Calculate current duration
            duration = datetime.utcnow() - session.checkin_time
            duration_minutes = int(duration.total_seconds() / 60)

            active_sessions.append({
                "session_id": str(session.id),
                "user_id": str(user.id),
                "employee_name": user.full_name,
                "department": user.department,
                "checkin_time": session.checkin_time.isoformat(),
                "duration_minutes": duration_minutes,
                "current_location": {
                    "latitude": float(location.latitude) if location else None,
                    "longitude": float(location.longitude) if location else None,
                    "within_geofence": location.is_within_geofence if location else None,
                    "address": location.address if location else None
                } if location else None
            })

        return active_sessions

    @staticmethod
    async def get_session_details(
        db: AsyncSession,
        session_id: str
    ) -> Optional[Dict]:
        """
        Get detailed session information

        Args:
            db: Database session
            session_id: Session ID

        Returns:
            Session details dictionary or None
        """
        result = await db.execute(
            select(Session).filter(Session.id == session_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            return None

        return session.to_dict()
