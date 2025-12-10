"""
Access Token model for share links and authentication
"""
from sqlalchemy import Column, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import enum

from app.database.db import Base


class TokenType(str, enum.Enum):
    """Token type enumeration"""
    LOGIN = "login"
    SHARE_LINK = "share_link"


class AccessToken(Base):
    """Access Token model for managing share links and refresh tokens"""

    __tablename__ = "access_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Token information
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    token_type = Column(Enum(TokenType), default=TokenType.LOGIN, nullable=False)

    # Expiration and revocation
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    revoked = Column(Boolean, default=False, nullable=False, index=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<AccessToken(id={self.id}, type={self.token_type}, revoked={self.revoked})>"

    def to_dict(self):
        """Convert token to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "token_type": self.token_type.value,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "revoked": self.revoked,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
