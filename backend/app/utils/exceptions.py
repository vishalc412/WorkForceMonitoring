"""
Custom exceptions and error handling
"""
from fastapi import HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class ErrorResponse(BaseModel):
    """Standardized error response schema"""
    error: str
    message: str
    code: str
    timestamp: str
    details: Optional[Dict[str, Any]] = None


class AppException(Exception):
    """Base application exception"""

    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)

    def to_response(self) -> ErrorResponse:
        """Convert exception to error response"""
        return ErrorResponse(
            error=self.error_code,
            message=self.message,
            code=self.error_code,
            timestamp=datetime.utcnow().isoformat() + "Z",
            details=self.details
        )


class ValidationException(AppException):
    """Validation error exception"""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            error_code="validation_error",
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class AuthenticationException(AppException):
    """Authentication error exception"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            error_code="authentication_failed",
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class AuthorizationException(AppException):
    """Authorization error exception"""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            error_code="authorization_failed",
            message=message,
            status_code=status.HTTP_403_FORBIDDEN
        )


class NotFoundException(AppException):
    """Resource not found exception"""

    def __init__(self, resource: str, identifier: str = None):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"

        super().__init__(
            error_code="not_found",
            message=message,
            status_code=status.HTTP_404_NOT_FOUND
        )


class FaceDetectionException(AppException):
    """Face detection error exception"""

    def __init__(self, message: str, rejection_reason: str = None):
        details = {"rejection_reason": rejection_reason} if rejection_reason else None
        super().__init__(
            error_code="face_detection_failed",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class LivenessException(AppException):
    """Liveness verification error exception"""

    def __init__(self, message: str, liveness_score: float = None):
        details = {"liveness_score": liveness_score} if liveness_score else None
        super().__init__(
            error_code="liveness_verification_failed",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class GeofenceException(AppException):
    """Geofence violation exception"""

    def __init__(self, message: str, location_data: Dict = None):
        super().__init__(
            error_code="geofence_violation",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=location_data
        )


class SessionException(AppException):
    """Session-related exception"""

    def __init__(self, message: str, session_id: str = None):
        details = {"session_id": session_id} if session_id else None
        super().__init__(
            error_code="session_error",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class RateLimitException(AppException):
    """Rate limit exceeded exception"""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None):
        details = {"retry_after": retry_after} if retry_after else None
        super().__init__(
            error_code="rate_limit_exceeded",
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details
        )
