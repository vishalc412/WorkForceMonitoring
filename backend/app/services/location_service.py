"""
Location tracking and geofencing service
"""
from typing import Dict, Optional, Tuple
from geopy.distance import geodesic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.models.location import Location, LocationType
from app.models.geofence import Geofence
from app.config import settings


class LocationService:
    """Service for location tracking and geofencing"""

    @staticmethod
    def calculate_distance(
        lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """
        Calculate distance between two GPS coordinates in meters

        Args:
            lat1, lon1: First coordinate
            lat2, lon2: Second coordinate

        Returns:
            Distance in meters
        """
        return geodesic((lat1, lon1), (lat2, lon2)).meters

    @staticmethod
    async def check_geofence(
        db: AsyncSession,
        latitude: float,
        longitude: float,
        company_id: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Check if location is within any active geofence

        Args:
            db: Database session
            latitude: GPS latitude
            longitude: GPS longitude
            company_id: Optional company ID filter

        Returns:
            Tuple of (is_within_geofence, geofence_data)
        """
        # Get all active geofences
        query = select(Geofence).filter(Geofence.is_active == True)

        if company_id:
            query = query.filter(Geofence.company_id == company_id)

        result = await db.execute(query)
        geofences = result.scalars().all()

        # Check each geofence
        for geofence in geofences:
            distance = LocationService.calculate_distance(
                latitude,
                longitude,
                float(geofence.latitude),
                float(geofence.longitude)
            )

            if distance <= geofence.radius_meters:
                return True, {
                    "geofence_id": str(geofence.id),
                    "geofence_name": geofence.name,
                    "distance_meters": distance,
                    "radius_meters": geofence.radius_meters
                }

        return False, None

    @staticmethod
    async def validate_location_accuracy(
        latitude: float,
        longitude: float,
        accuracy_meters: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate if location accuracy is acceptable

        Args:
            latitude: GPS latitude
            longitude: GPS longitude
            accuracy_meters: GPS accuracy in meters

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if coordinates are valid
        if not (-90 <= latitude <= 90):
            return False, "Invalid latitude"

        if not (-180 <= longitude <= 180):
            return False, "Invalid longitude"

        # Check accuracy threshold
        if accuracy_meters is not None:
            if accuracy_meters > settings.LOCATION_ACCURACY_THRESHOLD_METERS:
                return False, f"Location accuracy too low: {accuracy_meters}m"

        return True, None

    @staticmethod
    async def create_location_record(
        db: AsyncSession,
        session_id: str,
        latitude: float,
        longitude: float,
        accuracy_meters: Optional[int],
        altitude: Optional[float],
        ip_address: Optional[str],
        location_type: LocationType,
        address: Optional[str] = None
    ) -> Location:
        """
        Create location record in database

        Args:
            db: Database session
            session_id: Associated session ID
            latitude: GPS latitude
            longitude: GPS longitude
            accuracy_meters: GPS accuracy
            altitude: GPS altitude
            ip_address: Client IP address
            location_type: Type of location (checkin/checkout)
            address: Optional human-readable address

        Returns:
            Created Location object
        """
        # Check geofence
        is_within_geofence, geofence_data = await LocationService.check_geofence(
            db, latitude, longitude
        )

        # Create location record
        location = Location(
            session_id=session_id,
            latitude=latitude,
            longitude=longitude,
            accuracy_meters=accuracy_meters,
            altitude=altitude,
            ip_address=ip_address,
            is_within_geofence=is_within_geofence,
            location_type=location_type,
            address=address,
            captured_at=datetime.utcnow()
        )

        db.add(location)
        await db.flush()

        return location

    @staticmethod
    async def detect_location_anomaly(
        db: AsyncSession,
        user_id: str,
        current_latitude: float,
        current_longitude: float
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Detect impossible location changes (teleportation detection)

        Args:
            db: Database session
            user_id: User ID
            current_latitude: Current GPS latitude
            current_longitude: Current GPS longitude

        Returns:
            Tuple of (is_anomaly, anomaly_data)
        """
        # Get user's last location from recent sessions
        from app.models.session import Session

        query = (
            select(Location)
            .join(Session, Location.session_id == Session.id)
            .filter(Session.user_id == user_id)
            .order_by(Location.captured_at.desc())
            .limit(1)
        )

        result = await db.execute(query)
        last_location = result.scalar_one_or_none()

        if not last_location:
            return False, None

        # Calculate distance and time difference
        distance_meters = LocationService.calculate_distance(
            float(last_location.latitude),
            float(last_location.longitude),
            current_latitude,
            current_longitude
        )

        time_diff = datetime.utcnow() - last_location.captured_at
        time_diff_minutes = time_diff.total_seconds() / 60

        # Calculate maximum possible travel distance
        # Assuming max speed of 120 km/h (highway speed)
        max_possible_distance = (time_diff_minutes / 60) * 120000  # meters

        if distance_meters > max_possible_distance and distance_meters > 1000:  # 1km threshold
            return True, {
                "previous_location": {
                    "latitude": float(last_location.latitude),
                    "longitude": float(last_location.longitude),
                    "timestamp": last_location.captured_at.isoformat()
                },
                "distance_meters": distance_meters,
                "time_diff_minutes": time_diff_minutes,
                "max_possible_distance": max_possible_distance,
                "severity": "high" if distance_meters > 10000 else "medium"
            }

        return False, None

    @staticmethod
    async def reverse_geocode(latitude: float, longitude: float) -> Optional[str]:
        """
        Get human-readable address from coordinates
        Note: This requires an external API (Google Maps, OpenStreetMap, etc.)
        Placeholder implementation

        Args:
            latitude: GPS latitude
            longitude: GPS longitude

        Returns:
            Human-readable address or None
        """
        # TODO: Implement reverse geocoding with external API
        # For now, return formatted coordinates
        return f"{latitude:.6f}, {longitude:.6f}"
