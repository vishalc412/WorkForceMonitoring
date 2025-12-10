"""
Audit Log model for tracking system actions
"""
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.sql import func
import uuid
import enum

from app.database.db import Base


class AuditStatus(str, enum.Enum):
    """Audit status enumeration"""
    SUCCESS = "success"
    FAILURE = "failure"


class AuditLog(Base):
    """Audit Log model for tracking all system actions"""

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)

    # Action information
    action = Column(String(255), nullable=False, index=True)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(UUID(as_uuid=True), nullable=True)

    # Data changes
    old_values = Column(JSONB, nullable=True)
    new_values = Column(JSONB, nullable=True)

    # Request metadata
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)

    # Status
    status = Column(Enum(AuditStatus), default=AuditStatus.SUCCESS, nullable=False)
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, status={self.status})>"

    def to_dict(self):
        """Convert audit log to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": str(self.resource_id) if self.resource_id else None,
            "status": self.status.value,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
