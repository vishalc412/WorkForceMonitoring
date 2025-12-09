"""
Photo model for storing captured images
"""
from sqlalchemy import Column, String, Integer, Boolean, Date, DateTime, Enum, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
import enum

from app.database.db import Base


class PhotoType(str, enum.Enum):
    """Photo type enumeration"""
    CHECKIN = "checkin"
    CHECKOUT = "checkout"


class Photo(Base):
    """Photo model for face verification images"""

    __tablename__ = "photos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=True, index=True)

    # File information
    file_path = Column(String(500), nullable=False)
    file_size_kb = Column(Integer, nullable=True)
    image_hash = Column(String(255), nullable=True)

    # Face detection results
    face_detected = Column(Boolean, default=False, nullable=False)
    liveness_score = Column(Numeric(3, 2), nullable=True)
    liveness_verified = Column(Boolean, default=False, nullable=False)
    faces_count = Column(Integer, default=0, nullable=False)

    # Metadata
    metadata = Column(JSONB, nullable=True)
    photo_type = Column(Enum(PhotoType), default=PhotoType.CHECKIN, nullable=False)

    # Data retention
    expiry_date = Column(Date, nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<Photo(id={self.id}, user_id={self.user_id}, face_detected={self.face_detected})>"

    def to_dict(self):
        """Convert photo to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "session_id": str(self.session_id) if self.session_id else None,
            "file_path": self.file_path,
            "file_size_kb": self.file_size_kb,
            "face_detected": self.face_detected,
            "liveness_score": float(self.liveness_score) if self.liveness_score else None,
            "liveness_verified": self.liveness_verified,
            "faces_count": self.faces_count,
            "photo_type": self.photo_type.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
