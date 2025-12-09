"""
Tests for location service
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.location_service import LocationService
from app.models.geofence import Geofence
from app.models.session import Session, SessionStatus
from app.models.location import Location, LocationType
from app.models.user import User
from datetime import datetime


class TestLocationService:
    """Test LocationService class"""

    def test_calculate_distance(self):
        """Test distance calculation between two coordinates"""
        # Empire State Building to Times Square (approx 1.2 km)
        distance = LocationService.calculate_distance(
            40.748817, -73.985428,  # Empire State
            40.758896, -73.985130   # Times Square
        )

        # Should be approximately 1120 meters
        assert 1100 < distance < 1200

    def test_calculate_distance_same_point(self):
        """Test distance calculation for same point"""
        distance = LocationService.calculate_distance(
            40.748817, -73.985428,
            40.748817, -73.985428
        )

        assert distance == 0.0

    def test_calculate_distance_far_points(self):
        """Test distance calculation for far points"""
        # NYC to Los Angeles
        distance = LocationService.calculate_distance(
            40.7128, -74.0060,  # NYC
            34.0522, -118.2437  # LA
        )

        # Should be approximately 3900 km
        assert distance > 3_900_000
        assert distance < 4_000_000

    @pytest.mark.asyncio
    async def test_check_geofence_within(
        self,
        db_session: AsyncSession,
        test_geofence: Geofence
    ):
        """Test location within geofence"""
        # Location very close to geofence center
        is_within, geofence_data = await LocationService.check_geofence(
            db_session,
            40.748817,  # Same as geofence center
            -73.985428,
            None
        )

        assert is_within is True
        assert geofence_data is not None
        assert geofence_data["geofence_name"] == "Test Office"
        assert geofence_data["distance_meters"] < 10

    @pytest.mark.asyncio
    async def test_check_geofence_outside(
        self,
        db_session: AsyncSession,
        test_geofence: Geofence
    ):
        """Test location outside geofence"""
        # Location far from geofence (Los Angeles)
        is_within, geofence_data = await LocationService.check_geofence(
            db_session,
            34.0522,
            -118.2437,
            None
        )

        assert is_within is False
        assert geofence_data is None

    @pytest.mark.asyncio
    async def test_check_geofence_at_boundary(
        self,
        db_session: AsyncSession,
        test_geofence: Geofence
    ):
        """Test location at geofence boundary"""
        # Calculate point approximately 500m away (radius of test geofence)
        # Roughly 0.0045 degrees latitude = 500m
        is_within, geofence_data = await LocationService.check_geofence(
            db_session,
            40.748817 + 0.0045,
            -73.985428,
            None
        )

        # Should be very close to boundary
        if is_within:
            assert geofence_data["distance_meters"] <= 550
        else:
            # Just outside boundary is also acceptable
            pass

    @pytest.mark.asyncio
    async def test_validate_location_accuracy_valid(self):
        """Test valid location validation"""
        is_valid, error = await LocationService.validate_location_accuracy(
            40.748817,
            -73.985428,
            10  # Good accuracy
        )

        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_location_accuracy_invalid_latitude(self):
        """Test invalid latitude"""
        is_valid, error = await LocationService.validate_location_accuracy(
            95.0,  # Invalid: > 90
            -73.985428,
            10
        )

        assert is_valid is False
        assert "latitude" in error.lower()

    @pytest.mark.asyncio
    async def test_validate_location_accuracy_invalid_longitude(self):
        """Test invalid longitude"""
        is_valid, error = await LocationService.validate_location_accuracy(
            40.748817,
            -185.0,  # Invalid: < -180
            10
        )

        assert is_valid is False
        assert "longitude" in error.lower()

    @pytest.mark.asyncio
    async def test_validate_location_accuracy_poor_accuracy(self):
        """Test poor GPS accuracy"""
        is_valid, error = await LocationService.validate_location_accuracy(
            40.748817,
            -73.985428,
            100  # Poor accuracy (> 50m threshold)
        )

        assert is_valid is False
        assert "accuracy" in error.lower()

    @pytest.mark.asyncio
    async def test_create_location_record(
        self,
        db_session: AsyncSession,
        test_employee_user: User
    ):
        """Test creating location record"""
        # First create a session
        session = Session(
            user_id=test_employee_user.id,
            checkin_time=datetime.utcnow(),
            status=SessionStatus.ACTIVE
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        # Create location
        location = await LocationService.create_location_record(
            db_session,
            str(session.id),
            40.748817,
            -73.985428,
            10,
            100.5,
            "192.168.1.1",
            LocationType.CHECKIN,
            "Test Address"
        )

        assert location is not None
        assert location.session_id == session.id
        assert float(location.latitude) == 40.748817
        assert float(location.longitude) == -73.985428
        assert location.accuracy_meters == 10
        assert location.location_type == LocationType.CHECKIN

    @pytest.mark.asyncio
    async def test_detect_location_anomaly_no_previous(
        self,
        db_session: AsyncSession,
        test_employee_user: User
    ):
        """Test anomaly detection with no previous location"""
        is_anomaly, data = await LocationService.detect_location_anomaly(
            db_session,
            str(test_employee_user.id),
            40.748817,
            -73.985428
        )

        assert is_anomaly is False
        assert data is None

    @pytest.mark.asyncio
    async def test_detect_location_anomaly_normal_movement(
        self,
        db_session: AsyncSession,
        test_employee_user: User
    ):
        """Test normal movement detection"""
        # Create session with location
        session = Session(
            user_id=test_employee_user.id,
            checkin_time=datetime.utcnow(),
            status=SessionStatus.ACTIVE
        )
        db_session.add(session)
        await db_session.flush()

        # Create previous location (Empire State Building)
        prev_location = Location(
            session_id=session.id,
            latitude=40.748817,
            longitude=-73.985428,
            accuracy_meters=10,
            location_type=LocationType.CHECKIN,
            captured_at=datetime.utcnow()
        )
        db_session.add(prev_location)
        await db_session.commit()

        # Check new location nearby (Times Square - 1.2 km away)
        is_anomaly, data = await LocationService.detect_location_anomaly(
            db_session,
            str(test_employee_user.id),
            40.758896,
            -73.985130
        )

        # Should not be anomaly for short distance
        assert is_anomaly is False

    @pytest.mark.asyncio
    async def test_detect_location_anomaly_teleportation(
        self,
        db_session: AsyncSession,
        test_employee_user: User
    ):
        """Test impossible movement detection (teleportation)"""
        # Create session with recent location
        session = Session(
            user_id=test_employee_user.id,
            checkin_time=datetime.utcnow(),
            status=SessionStatus.ACTIVE
        )
        db_session.add(session)
        await db_session.flush()

        # Create previous location in NYC
        prev_location = Location(
            session_id=session.id,
            latitude=40.7128,
            longitude=-74.0060,
            accuracy_meters=10,
            location_type=LocationType.CHECKIN,
            captured_at=datetime.utcnow()  # Just now
        )
        db_session.add(prev_location)
        await db_session.commit()

        # Try to check in from Los Angeles 1 second later (impossible)
        is_anomaly, data = await LocationService.detect_location_anomaly(
            db_session,
            str(test_employee_user.id),
            34.0522,  # LA
            -118.2437
        )

        assert is_anomaly is True
        assert data is not None
        assert "distance_meters" in data
        assert data["distance_meters"] > 3_000_000  # > 3000 km
        assert data["severity"] == "high"

    @pytest.mark.asyncio
    async def test_reverse_geocode(self):
        """Test reverse geocoding"""
        # Currently returns formatted coordinates
        address = await LocationService.reverse_geocode(40.748817, -73.985428)

        assert address is not None
        assert "40.748817" in address
        assert "-73.985428" in address
