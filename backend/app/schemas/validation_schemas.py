"""
Enhanced validation schemas with comprehensive input validation
"""
from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional
from datetime import datetime


class CoordinatesValidator(BaseModel):
    """Validator for GPS coordinates"""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")
    accuracy: Optional[int] = Field(None, ge=0, le=1000, description="GPS accuracy in meters")
    altitude: Optional[float] = Field(None, description="Altitude in meters")

    @validator('accuracy')
    def validate_accuracy(cls, v):
        """Validate GPS accuracy is within acceptable range"""
        from app.config import settings
        if v and v > settings.LOCATION_ACCURACY_THRESHOLD_METERS:
            raise ValueError(
                f"GPS accuracy too low: {v}m. "
                f"Required: <{settings.LOCATION_ACCURACY_THRESHOLD_METERS}m"
            )
        return v


class PhotoValidator(BaseModel):
    """Validator for photo uploads"""
    photo_base64: str = Field(..., min_length=100, description="Base64 encoded photo")

    @validator('photo_base64')
    def validate_photo_format(cls, v):
        """Validate photo is properly formatted base64"""
        import re

        # Check for data URI format
        data_uri_pattern = r'^data:image/(jpeg|jpg|png);base64,'
        if not re.match(data_uri_pattern, v, re.IGNORECASE):
            # If no data URI, check if it's valid base64
            try:
                import base64
                if "," in v:
                    v = v.split(",")[1]
                base64.b64decode(v)
            except Exception:
                raise ValueError("Invalid image format. Must be base64 encoded JPEG or PNG")

        # Check size (rough estimate from base64 length)
        from app.config import settings
        estimated_size_mb = (len(v) * 3 / 4) / (1024 * 1024)
        if estimated_size_mb > settings.MAX_UPLOAD_SIZE_MB:
            raise ValueError(
                f"Image too large: ~{estimated_size_mb:.1f}MB. "
                f"Maximum: {settings.MAX_UPLOAD_SIZE_MB}MB"
            )

        return v


class UserIdValidator(BaseModel):
    """Validator for UUID fields"""
    user_id: str

    @validator('user_id')
    def validate_uuid(cls, v):
        """Validate user_id is a valid UUID"""
        import uuid
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError("Invalid user ID format. Must be a valid UUID")
        return v


class TokenValidator(BaseModel):
    """Validator for tokens"""
    token: str = Field(..., min_length=32, max_length=500)

    @validator('token')
    def validate_token_format(cls, v):
        """Validate token format"""
        # Check for dangerous characters
        import re
        if not re.match(r'^[A-Za-z0-9_-]+$', v):
            raise ValueError("Invalid token format")
        return v


class EmailValidator(BaseModel):
    """Validator for email fields"""
    email: EmailStr

    @validator('email')
    def validate_email_domain(cls, v):
        """Optional: Validate email domain if needed"""
        # You can add domain whitelist/blacklist here
        return v.lower()


class PasswordValidator(BaseModel):
    """Validator for passwords"""
    password: str = Field(..., min_length=8, max_length=128)

    @validator('password')
    def validate_password_strength(cls, v):
        """Validate password meets minimum security requirements"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        # Check for at least one number (optional - can be configured)
        # import re
        # if not re.search(r'\d', v):
        #     raise ValueError("Password must contain at least one number")

        # Check for at least one letter
        # if not re.search(r'[a-zA-Z]', v):
        #     raise ValueError("Password must contain at least one letter")

        return v


class DateRangeValidator(BaseModel):
    """Validator for date ranges"""
    start_date: datetime
    end_date: datetime

    @validator('end_date')
    def validate_date_range(cls, v, values):
        """Validate end date is after start date"""
        if 'start_date' in values and v < values['start_date']:
            raise ValueError("End date must be after start date")

        # Validate range is not too large (e.g., max 1 year)
        if 'start_date' in values:
            days_diff = (v - values['start_date']).days
            if days_diff > 365:
                raise ValueError("Date range cannot exceed 1 year")

        return v


class PaginationValidator(BaseModel):
    """Validator for pagination parameters"""
    page: int = Field(1, ge=1, le=10000, description="Page number")
    page_size: int = Field(50, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        """Calculate offset for database query"""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Get limit for database query"""
        return self.page_size
