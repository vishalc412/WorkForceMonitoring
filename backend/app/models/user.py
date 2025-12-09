"""
User model
"""
from sqlalchemy import Column, String, Boolean, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import enum

from app.database.db import Base


class UserRole(str, enum.Enum):
    """User role enumeration"""
    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"


class User(Base):
    """User model for authentication and employee management"""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.EMPLOYEE, index=True)
    department = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    device_fingerprint = Column(String(255), nullable=True)

    # GDPR Consent
    consent_gdpr = Column(Boolean, default=False, nullable=False)
    consent_timestamp = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"

    def to_dict(self):
        """Convert user to dictionary"""
        return {
            "id": str(self.id),
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role.value,
            "department": self.department,
            "is_active": self.is_active,
            "consent_gdpr": self.consent_gdpr,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
