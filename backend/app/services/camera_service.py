"""
Camera and photo management service
"""
import base64
import hashlib
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
from PIL import Image
from io import BytesIO
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.photo import Photo, PhotoType
from app.config import settings
from app.ml.face_detector import get_face_detector, get_liveness_detector


class CameraService:
    """Service for camera capture and photo management"""

    @staticmethod
    def validate_image_format(base64_image: str) -> Tuple[bool, Optional[str]]:
        """
        Validate image format and size

        Args:
            base64_image: Base64 encoded image

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Remove data URI prefix if present
            if "base64," in base64_image:
                image_data = base64_image.split("base64,")[1]
            else:
                image_data = base64_image

            # Decode and check size
            decoded = base64.b64decode(image_data)
            size_kb = len(decoded) / 1024

            if size_kb > settings.MAX_UPLOAD_SIZE_MB * 1024:
                return False, f"Image too large: {size_kb:.1f}KB"

            # Check if it's a valid image
            image = Image.open(BytesIO(decoded))
            image.verify()

            # Check format
            if image.format not in ['JPEG', 'PNG', 'JPG']:
                return False, f"Invalid image format: {image.format}"

            return True, None

        except Exception as e:
            return False, f"Invalid image: {str(e)}"

    @staticmethod
    def calculate_image_hash(base64_image: str) -> str:
        """
        Calculate SHA-256 hash of image

        Args:
            base64_image: Base64 encoded image

        Returns:
            SHA-256 hash string
        """
        if "base64," in base64_image:
            image_data = base64_image.split("base64,")[1]
        else:
            image_data = base64_image

        decoded = base64.b64decode(image_data)
        return hashlib.sha256(decoded).hexdigest()

    @staticmethod
    async def save_photo_file(
        base64_image: str,
        user_id: str,
        photo_type: PhotoType
    ) -> Tuple[str, int]:
        """
        Save photo to file system

        Args:
            base64_image: Base64 encoded image
            user_id: User ID
            photo_type: Type of photo (checkin/checkout)

        Returns:
            Tuple of (file_path, file_size_kb)
        """
        # Remove data URI prefix
        if "base64," in base64_image:
            image_data = base64_image.split("base64,")[1]
        else:
            image_data = base64_image

        decoded = base64.b64decode(image_data)
        size_kb = len(decoded) // 1024

        # Generate unique filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{user_id}_{photo_type.value}_{timestamp}.jpg"

        # Create directory structure
        date_dir = datetime.utcnow().strftime("%Y/%m/%d")
        full_dir = os.path.join(settings.UPLOAD_DIR, "photos", date_dir)
        os.makedirs(full_dir, exist_ok=True)

        # Save file
        file_path = os.path.join(full_dir, filename)
        with open(file_path, "wb") as f:
            f.write(decoded)

        # Return relative path
        relative_path = os.path.join("photos", date_dir, filename)
        return relative_path, size_kb

    @staticmethod
    async def process_and_verify_photo(
        db: AsyncSession,
        base64_image: str,
        user_id: str,
        session_id: Optional[str],
        photo_type: PhotoType
    ) -> Dict[str, any]:
        """
        Process photo with face detection and liveness check

        Args:
            db: Database session
            base64_image: Base64 encoded image
            user_id: User ID
            session_id: Optional session ID
            photo_type: Type of photo

        Returns:
            Dictionary with processing results and photo record
        """
        # Validate image format
        is_valid, error_msg = CameraService.validate_image_format(base64_image)
        if not is_valid:
            return {
                "success": False,
                "error": error_msg,
                "error_code": "INVALID_IMAGE"
            }

        # Calculate image hash
        image_hash = CameraService.calculate_image_hash(base64_image)

        # Face detection
        face_detector = get_face_detector()
        face_result = face_detector.process_base64_image(base64_image)

        if not face_result.get("face_detected"):
            return {
                "success": False,
                "error": "Face detection failed",
                "error_code": "NO_FACE_DETECTED",
                "rejection_reason": face_result.get("rejection_reason"),
                "face_count": face_result.get("face_count", 0)
            }

        # Liveness detection
        liveness_detector = get_liveness_detector()
        liveness_result = liveness_detector.process_base64_image(base64_image)

        if not liveness_result.get("liveness_verified"):
            return {
                "success": False,
                "error": "Liveness verification failed",
                "error_code": "LIVENESS_FAILED",
                "liveness_score": liveness_result.get("liveness_score", 0.0)
            }

        # Save photo to file system
        file_path, file_size_kb = await CameraService.save_photo_file(
            base64_image, user_id, photo_type
        )

        # Calculate expiry date
        expiry_date = datetime.utcnow().date() + timedelta(days=settings.PHOTO_RETENTION_DAYS)

        # Create photo record in database
        photo = Photo(
            user_id=user_id,
            session_id=session_id,
            file_path=file_path,
            file_size_kb=file_size_kb,
            image_hash=image_hash,
            face_detected=True,
            liveness_score=liveness_result.get("liveness_score"),
            liveness_verified=True,
            faces_count=1,
            metadata={
                "confidence": face_result.get("confidence"),
                "z_variance": liveness_result.get("z_variance"),
                "brightness_variance": liveness_result.get("brightness_variance")
            },
            photo_type=photo_type,
            expiry_date=expiry_date
        )

        db.add(photo)
        await db.flush()

        return {
            "success": True,
            "photo_id": str(photo.id),
            "face_detected": True,
            "liveness_verified": True,
            "liveness_score": float(liveness_result.get("liveness_score", 0)),
            "confidence": float(face_result.get("confidence", 0)),
            "file_path": file_path
        }

    @staticmethod
    async def cleanup_expired_photos(db: AsyncSession) -> int:
        """
        Delete photos that have exceeded retention period

        Args:
            db: Database session

        Returns:
            Number of photos deleted
        """
        from sqlalchemy import select, delete

        # Find expired photos
        today = datetime.utcnow().date()
        result = await db.execute(
            select(Photo).filter(Photo.expiry_date < today)
        )
        expired_photos = result.scalars().all()

        deleted_count = 0
        for photo in expired_photos:
            # Delete file from filesystem
            full_path = os.path.join(settings.UPLOAD_DIR, photo.file_path)
            if os.path.exists(full_path):
                os.remove(full_path)
                deleted_count += 1

            # Delete database record
            await db.delete(photo)

        await db.commit()
        return deleted_count
