"""
Application configuration management
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings"""

    # Application
    APP_NAME: str = "WorkforceMonitoring"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    SHARE_LINK_EXPIRE_HOURS: int = 8

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 5
    PHOTO_RETENTION_DAYS: int = 30
    LOCATION_RETENTION_DAYS: int = 90

    # Face Detection
    FACE_DETECTION_MODEL: str = "mediapipe"
    FACE_CONFIDENCE_THRESHOLD: float = 0.6
    LIVENESS_THRESHOLD: float = 0.7

    # Geofencing
    DEFAULT_GEOFENCE_RADIUS_METERS: int = 500
    LOCATION_ACCURACY_THRESHOLD_METERS: int = 50

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    LOGIN_RATE_LIMIT_PER_15MIN: int = 5
    CHECKIN_RATE_LIMIT_PER_HOUR: int = 10

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@workforce-monitoring.com"

    # Monitoring
    SENTRY_DSN: str = ""
    LOG_LEVEL: str = "INFO"

    # AWS (Optional)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

# Create upload directory if it doesn't exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "photos"), exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "reports"), exist_ok=True)
