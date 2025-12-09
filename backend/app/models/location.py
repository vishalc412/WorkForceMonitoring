"""
Location model for tracking employee locations
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Enum, ForeignKey, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.sql import func
import uuid
import enum

from app.database.db import Base


class LocationType(str, enum.Enum):
    """Location type enumeration"""
    CHECKIN = "checkin"
    CHECKOUT = "checkout"
    MANUAL = "manual"


class Location(Base):
    """Location model for GPS coordinates tracking"""

    __tablename__ = "locations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)

    # GPS Coordinates
    latitude = Column(Numeric(10, 8), nullable=False, index=True)
    longitude = Column(Numeric(11, 8), nullable=False, index=True)
    accuracy_meters = Column(Integer, nullable=True)
    altitude = Column(Numeric(10, 2), nullable=True)

    # Network Information
    ip_address = Column(INET, nullable=True)

    # Geofencing
    is_within_geofence = Column(Boolean, default=False, nullable=False, index=True)

    # Location metadata
    location_type = Column(Enum(LocationType), default=LocationType.CHECKIN, nullable=False)
    address = Column(Text, nullable=True)

    # Timestamps
    captured_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<Location(id={self.id}, lat={self.latitude}, lon={self.longitude})>"

    def to_dict(self):
        """Convert location to dictionary"""
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "latitude": float(self.latitude) if self.latitude else None,
            "longitude": float(self.longitude) if self.longitude else None,
            "accuracy_meters": self.accuracy_meters,
            "altitude": float(self.altitude) if self.altitude else None,
            "is_within_geofence": self.is_within_geofence,
            "location_type": self.location_type.value,
            "address": self.address,
            "captured_at": self.captured_at.isoformat() if self.captured_at else None,
        }
