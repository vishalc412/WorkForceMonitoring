"""
Tests for database models
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.models.user import User, UserRole
from app.models.session import Session, SessionStatus
from app.models.location import Location, LocationType
from app.models.photo import Photo, PhotoType
from app.models.geofence import Geofence
from app.models.access_token import AccessToken, TokenType
from app.models.audit_log import AuditLog, AuditStatus


class TestUserModel:
    """Test User model"""

    @pytest.mark.asyncio
    async def test_create_user(self, db_session: AsyncSession):
        """Test creating a user"""
        user = User(
            email="test@example.com",
            full_name="Test User",
            password_hash="hashed_password",
            role=UserRole.EMPLOYEE,
            department="Sales",
            is_active=True,
            consent_gdpr=True,
            consent_timestamp=datetime.utcnow()
        )

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.role == UserRole.EMPLOYEE
        assert user.is_active is True

    @pytest.mark.asyncio
    async def test_user_to_dict(self, test_employee_user: User):
        """Test user to_dict method"""
        user_dict = test_employee_user.to_dict()

        assert "id" in user_dict
        assert user_dict["email"] == test_employee_user.email
        assert user_dict["role"] == "employee"
        assert "password_hash" not in user_dict  # Should not expose password

    @pytest.mark.asyncio
    async def test_user_email_unique(self, db_session: AsyncSession, test_employee_user: User):
        """Test that email must be unique"""
        duplicate_user = User(
            email=test_employee_user.email,  # Same email
            full_name="Another User",
            password_hash="password",
            role=UserRole.EMPLOYEE
        )

        db_session.add(duplicate_user)

        with pytest.raises(Exception):  # Should raise IntegrityError
            await db_session.commit()


class TestSessionModel:
    """Test Session model"""

    @pytest.mark.asyncio
    async def test_create_session(
        self,
        db_session: AsyncSession,
        test_employee_user: User
    ):
        """Test creating a session"""
        session = Session(
            user_id=test_employee_user.id,
            checkin_time=datetime.utcnow(),
            status=SessionStatus.ACTIVE
        )

        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert session.id is not None
        assert session.user_id == test_employee_user.id
        assert session.status == SessionStatus.ACTIVE
        assert session.checkout_time is None

    @pytest.mark.asyncio
    async def test_complete_session(
        self,
        db_session: AsyncSession,
        test_employee_user: User
    ):
        """Test completing a session"""
        checkin = datetime.utcnow()
        checkout = checkin + timedelta(hours=8)

        session = Session(
            user_id=test_employee_user.id,
            checkin_time=checkin,
            checkout_time=checkout,
            duration_minutes=480,
            status=SessionStatus.COMPLETED
        )

        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert session.status == SessionStatus.COMPLETED
        assert session.duration_minutes == 480

    @pytest.mark.asyncio
    async def test_session_to_dict(
        self,
        db_session: AsyncSession,
        test_employee_user: User
    ):
        """Test session to_dict method"""
        session = Session(
            user_id=test_employee_user.id,
            checkin_time=datetime.utcnow(),
            status=SessionStatus.ACTIVE
        )

        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        session_dict = session.to_dict()

        assert "id" in session_dict
        assert "user_id" in session_dict
        assert session_dict["status"] == "active"


class TestLocationModel:
    """Test Location model"""

    @pytest.mark.asyncio
    async def test_create_location(
        self,
        db_session: AsyncSession,
        test_employee_user: User
    ):
        """Test creating a location record"""
        # Create session first
        session = Session(
            user_id=test_employee_user.id,
            checkin_time=datetime.utcnow(),
            status=SessionStatus.ACTIVE
        )
        db_session.add(session)
        await db_session.flush()

        # Create location
        location = Location(
            session_id=session.id,
            latitude=40.748817,
            longitude=-73.985428,
            accuracy_meters=10,
            altitude=100.5,
            is_within_geofence=True,
            location_type=LocationType.CHECKIN,
            captured_at=datetime.utcnow()
        )

        db_session.add(location)
        await db_session.commit()
        await db_session.refresh(location)

        assert location.id is not None
        assert float(location.latitude) == 40.748817
        assert location.is_within_geofence is True

    @pytest.mark.asyncio
    async def test_location_to_dict(
        self,
        db_session: AsyncSession,
        test_employee_user: User
    ):
        """Test location to_dict method"""
        session = Session(
            user_id=test_employee_user.id,
            checkin_time=datetime.utcnow(),
            status=SessionStatus.ACTIVE
        )
        db_session.add(session)
        await db_session.flush()

        location = Location(
            session_id=session.id,
            latitude=40.748817,
            longitude=-73.985428,
            location_type=LocationType.CHECKIN,
            captured_at=datetime.utcnow()
        )

        db_session.add(location)
        await db_session.commit()
        await db_session.refresh(location)

        location_dict = location.to_dict()

        assert "latitude" in location_dict
        assert "longitude" in location_dict
        assert location_dict["location_type"] == "checkin"


class TestPhotoModel:
    """Test Photo model"""

    @pytest.mark.asyncio
    async def test_create_photo(
        self,
        db_session: AsyncSession,
        test_employee_user: User
    ):
        """Test creating a photo record"""
        photo = Photo(
            user_id=test_employee_user.id,
            file_path="photos/2025/12/09/test.jpg",
            file_size_kb=150,
            face_detected=True,
            liveness_score=0.85,
            liveness_verified=True,
            faces_count=1,
            photo_type=PhotoType.CHECKIN,
            expiry_date=(datetime.utcnow() + timedelta(days=30)).date()
        )

        db_session.add(photo)
        await db_session.commit()
        await db_session.refresh(photo)

        assert photo.id is not None
        assert photo.face_detected is True
        assert float(photo.liveness_score) == 0.85

    @pytest.mark.asyncio
    async def test_photo_expiry(
        self,
        db_session: AsyncSession,
        test_employee_user: User
    ):
        """Test photo with expiry date"""
        expiry = (datetime.utcnow() + timedelta(days=30)).date()

        photo = Photo(
            user_id=test_employee_user.id,
            file_path="photos/test.jpg",
            photo_type=PhotoType.CHECKIN,
            expiry_date=expiry
        )

        db_session.add(photo)
        await db_session.commit()
        await db_session.refresh(photo)

        assert photo.expiry_date == expiry


class TestGeofenceModel:
    """Test Geofence model"""

    @pytest.mark.asyncio
    async def test_create_geofence(self, db_session: AsyncSession):
        """Test creating a geofence"""
        geofence = Geofence(
            name="Office Location",
            description="Main office",
            latitude=40.748817,
            longitude=-73.985428,
            radius_meters=500,
            is_active=True
        )

        db_session.add(geofence)
        await db_session.commit()
        await db_session.refresh(geofence)

        assert geofence.id is not None
        assert geofence.name == "Office Location"
        assert geofence.radius_meters == 500

    @pytest.mark.asyncio
    async def test_geofence_to_dict(self, test_geofence: Geofence):
        """Test geofence to_dict method"""
        geofence_dict = test_geofence.to_dict()

        assert "id" in geofence_dict
        assert "name" in geofence_dict
        assert "latitude" in geofence_dict
        assert geofence_dict["is_active"] is True


class TestAccessTokenModel:
    """Test AccessToken model"""

    @pytest.mark.asyncio
    async def test_create_access_token(
        self,
        db_session: AsyncSession,
        test_employee_user: User
    ):
        """Test creating an access token"""
        token = AccessToken(
            user_id=test_employee_user.id,
            token_hash="abc123hash",
            token_type=TokenType.SHARE_LINK,
            expires_at=datetime.utcnow() + timedelta(hours=8)
        )

        db_session.add(token)
        await db_session.commit()
        await db_session.refresh(token)

        assert token.id is not None
        assert token.token_type == TokenType.SHARE_LINK
        assert token.revoked is False

    @pytest.mark.asyncio
    async def test_revoke_token(
        self,
        db_session: AsyncSession,
        test_employee_user: User
    ):
        """Test revoking a token"""
        token = AccessToken(
            user_id=test_employee_user.id,
            token_hash="abc123hash",
            token_type=TokenType.SHARE_LINK,
            expires_at=datetime.utcnow() + timedelta(hours=8)
        )

        db_session.add(token)
        await db_session.commit()

        # Revoke token
        token.revoked = True
        token.revoked_at = datetime.utcnow()
        await db_session.commit()
        await db_session.refresh(token)

        assert token.revoked is True
        assert token.revoked_at is not None


class TestAuditLogModel:
    """Test AuditLog model"""

    @pytest.mark.asyncio
    async def test_create_audit_log(
        self,
        db_session: AsyncSession,
        test_employee_user: User
    ):
        """Test creating an audit log entry"""
        audit = AuditLog(
            user_id=test_employee_user.id,
            action="user_login",
            resource_type="user",
            resource_id=test_employee_user.id,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            status=AuditStatus.SUCCESS
        )

        db_session.add(audit)
        await db_session.commit()
        await db_session.refresh(audit)

        assert audit.id is not None
        assert audit.action == "user_login"
        assert audit.status == AuditStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_audit_log_with_changes(
        self,
        db_session: AsyncSession,
        test_employee_user: User
    ):
        """Test audit log with old/new values"""
        audit = AuditLog(
            user_id=test_employee_user.id,
            action="user_update",
            resource_type="user",
            resource_id=test_employee_user.id,
            old_values={"department": "Sales"},
            new_values={"department": "Marketing"},
            status=AuditStatus.SUCCESS
        )

        db_session.add(audit)
        await db_session.commit()
        await db_session.refresh(audit)

        assert audit.old_values["department"] == "Sales"
        assert audit.new_values["department"] == "Marketing"
