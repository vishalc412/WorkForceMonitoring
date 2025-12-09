"""
Tests for camera and photo management service
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
import os
import base64

from app.services.camera_service import CameraService
from app.models.user import User
from app.models.photo import PhotoType
from app.config import settings


class TestCameraService:
    """Test CameraService class"""

    def test_validate_image_format_valid(self, sample_base64_image: str):
        """Test validation of valid image"""
        is_valid, error = CameraService.validate_image_format(sample_base64_image)

        assert is_valid is True
        assert error is None

    def test_validate_image_format_too_large(self):
        """Test validation of oversized image"""
        # Create large fake base64 (> 5MB)
        large_data = "A" * (6 * 1024 * 1024)  # 6MB
        large_image = f"data:image/png;base64,{large_data}"

        is_valid, error = CameraService.validate_image_format(large_image)

        assert is_valid is False
        assert "large" in error.lower()

    def test_validate_image_format_invalid_data(self):
        """Test validation of invalid base64 data"""
        invalid_image = "data:image/png;base64,not-valid-base64!!!"

        is_valid, error = CameraService.validate_image_format(invalid_image)

        assert is_valid is False
        assert error is not None

    def test_calculate_image_hash(self, sample_base64_image: str):
        """Test image hash calculation"""
        hash1 = CameraService.calculate_image_hash(sample_base64_image)
        hash2 = CameraService.calculate_image_hash(sample_base64_image)

        # Same image should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 produces 64 hex characters

    def test_calculate_image_hash_different_images(self):
        """Test that different images produce different hashes"""
        image1 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        image2 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="

        hash1 = CameraService.calculate_image_hash(image1)
        hash2 = CameraService.calculate_image_hash(image2)

        assert hash1 != hash2

    @pytest.mark.asyncio
    async def test_save_photo_file(
        self,
        sample_base64_image: str,
        test_employee_user: User
    ):
        """Test saving photo to filesystem"""
        file_path, file_size_kb = await CameraService.save_photo_file(
            sample_base64_image,
            str(test_employee_user.id),
            PhotoType.CHECKIN
        )

        # Check file was created
        full_path = os.path.join(settings.UPLOAD_DIR, file_path)
        assert os.path.exists(full_path)

        # Check file size
        assert file_size_kb > 0

        # Check filename format
        assert "checkin" in file_path
        assert str(test_employee_user.id) in file_path

        # Cleanup
        os.remove(full_path)

    @pytest.mark.asyncio
    async def test_save_photo_file_creates_directory(
        self,
        sample_base64_image: str,
        test_employee_user: User
    ):
        """Test that save_photo_file creates directory structure"""
        # Remove photos directory if exists
        photos_dir = os.path.join(settings.UPLOAD_DIR, "photos")
        if os.path.exists(photos_dir):
            import shutil
            shutil.rmtree(photos_dir)

        file_path, _ = await CameraService.save_photo_file(
            sample_base64_image,
            str(test_employee_user.id),
            PhotoType.CHECKIN
        )

        # Check directory was created
        full_path = os.path.join(settings.UPLOAD_DIR, file_path)
        assert os.path.exists(os.path.dirname(full_path))

        # Cleanup
        os.remove(full_path)

    @pytest.mark.asyncio
    async def test_process_and_verify_photo_invalid_format(
        self,
        db_session: AsyncSession,
        test_employee_user: User
    ):
        """Test photo processing with invalid format"""
        result = await CameraService.process_and_verify_photo(
            db_session,
            "not-valid-base64",
            str(test_employee_user.id),
            None,
            PhotoType.CHECKIN
        )

        assert result["success"] is False
        assert result["error_code"] == "INVALID_IMAGE"

    @pytest.mark.asyncio
    async def test_cleanup_expired_photos(
        self,
        db_session: AsyncSession,
        test_employee_user: User,
        sample_base64_image: str
    ):
        """Test cleanup of expired photos"""
        from app.models.photo import Photo
        from datetime import datetime, timedelta

        # Create expired photo
        file_path, file_size = await CameraService.save_photo_file(
            sample_base64_image,
            str(test_employee_user.id),
            PhotoType.CHECKIN
        )

        photo = Photo(
            user_id=test_employee_user.id,
            file_path=file_path,
            file_size_kb=file_size,
            face_detected=True,
            liveness_verified=True,
            photo_type=PhotoType.CHECKIN,
            expiry_date=(datetime.utcnow() - timedelta(days=1)).date()  # Expired
        )
        db_session.add(photo)
        await db_session.commit()

        # Run cleanup
        deleted_count = await CameraService.cleanup_expired_photos(db_session)

        assert deleted_count == 1

        # Check file was deleted
        full_path = os.path.join(settings.UPLOAD_DIR, file_path)
        assert not os.path.exists(full_path)


class TestPhotoValidation:
    """Test photo validation logic"""

    def test_photo_size_validation(self):
        """Test photo size limits"""
        # Create 1x1 pixel image
        small_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

        is_valid, error = CameraService.validate_image_format(small_image)
        assert is_valid is True

    def test_photo_format_validation(self):
        """Test that only valid image formats are accepted"""
        # Valid PNG
        png_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        is_valid, _ = CameraService.validate_image_format(png_image)
        assert is_valid is True

    def test_photo_without_data_uri_prefix(self):
        """Test photo validation without data URI prefix"""
        # Base64 without prefix
        base64_only = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

        hash_result = CameraService.calculate_image_hash(base64_only)
        assert hash_result is not None
        assert len(hash_result) == 64


class TestPhotoMetadata:
    """Test photo metadata handling"""

    def test_photo_hash_consistency(self, sample_base64_image: str):
        """Test that photo hash is consistent"""
        hash1 = CameraService.calculate_image_hash(sample_base64_image)
        hash2 = CameraService.calculate_image_hash(sample_base64_image)

        assert hash1 == hash2

    def test_photo_hash_uniqueness(self):
        """Test that different photos have different hashes"""
        image1 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        image2 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="

        hash1 = CameraService.calculate_image_hash(image1)
        hash2 = CameraService.calculate_image_hash(image2)

        assert hash1 != hash2
