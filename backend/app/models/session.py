"""
Session model for check-in/check-out tracking
"""
from sqlalchemy import Column, String, Integer, DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum

from app.database.db import Base


class SessionStatus(str, enum.Enum):
    """Session status enumeration"""
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class Session(Base):
    """Session model for tracking employee work sessions"""

    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Check-in/Check-out times
    checkin_time = Column(DateTime(timezone=True), nullable=False, index=True)
    checkout_time = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(Integer, nullable=True)

    # Related resources
    checkin_photo_id = Column(UUID(as_uuid=True), ForeignKey("photos.id"), nullable=True)
    checkout_photo_id = Column(UUID(as_uuid=True), ForeignKey("photos.id"), nullable=True)
    checkin_location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True)
    checkout_location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True)

    # Status and notes
    status = Column(Enum(SessionStatus), default=SessionStatus.ACTIVE, nullable=False, index=True)
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<Session(id={self.id}, user_id={self.user_id}, status={self.status})>"

    def to_dict(self):
        """Convert session to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "checkin_time": self.checkin_time.isoformat() if self.checkin_time else None,
            "checkout_time": self.checkout_time.isoformat() if self.checkout_time else None,
            "duration_minutes": self.duration_minutes,
            "status": self.status.value,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
