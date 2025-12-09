"""
Geofence model for location boundaries
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.database.db import Base


class Geofence(Base):
    """Geofence model for defining authorized work locations"""

    __tablename__ = "geofences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), nullable=True)

    # Basic information
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Center coordinates
    latitude = Column(Numeric(10, 8), nullable=False, index=True)
    longitude = Column(Numeric(11, 8), nullable=False, index=True)

    # Radius in meters (circular geofence)
    radius_meters = Column(Integer, default=500, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<Geofence(id={self.id}, name={self.name}, radius={self.radius_meters})>"

    def to_dict(self):
        """Convert geofence to dictionary"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "latitude": float(self.latitude) if self.latitude else None,
            "longitude": float(self.longitude) if self.longitude else None,
            "radius_meters": self.radius_meters,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
