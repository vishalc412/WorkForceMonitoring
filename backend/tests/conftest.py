"""
Test configuration and fixtures
"""
import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from httpx import AsyncClient

from app.database.db import Base
from app.main import app
from app.models.user import User, UserRole
from app.models.geofence import Geofence
from app.security.password import hash_password
from datetime import datetime
import uuid

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres123@localhost:5432/workforce_test"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db_engine():
    """Create test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for tests"""
    async_session = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Create test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_admin_user(db_session) -> User:
    """Create test admin user"""
    admin = User(
        id=uuid.uuid4(),
        email="admin@test.com",
        full_name="Test Admin",
        password_hash=hash_password("admin123"),
        role=UserRole.ADMIN,
        department="IT",
        is_active=True,
        consent_gdpr=True,
        consent_timestamp=datetime.utcnow()
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture
async def test_manager_user(db_session) -> User:
    """Create test manager user"""
    manager = User(
        id=uuid.uuid4(),
        email="manager@test.com",
        full_name="Test Manager",
        password_hash=hash_password("manager123"),
        role=UserRole.MANAGER,
        department="Management",
        is_active=True,
        consent_gdpr=True,
        consent_timestamp=datetime.utcnow()
    )
    db_session.add(manager)
    await db_session.commit()
    await db_session.refresh(manager)
    return manager


@pytest.fixture
async def test_employee_user(db_session) -> User:
    """Create test employee user"""
    employee = User(
        id=uuid.uuid4(),
        email="employee@test.com",
        full_name="Test Employee",
        password_hash=hash_password("employee123"),
        role=UserRole.EMPLOYEE,
        department="Sales",
        is_active=True,
        consent_gdpr=True,
        consent_timestamp=datetime.utcnow()
    )
    db_session.add(employee)
    await db_session.commit()
    await db_session.refresh(employee)
    return employee


@pytest.fixture
async def test_geofence(db_session) -> Geofence:
    """Create test geofence (Empire State Building, NYC)"""
    geofence = Geofence(
        id=uuid.uuid4(),
        name="Test Office",
        description="Test office location",
        latitude=40.748817,
        longitude=-73.985428,
        radius_meters=500,
        is_active=True
    )
    db_session.add(geofence)
    await db_session.commit()
    await db_session.refresh(geofence)
    return geofence


@pytest.fixture
def sample_base64_image() -> str:
    """Sample base64 encoded image for testing"""
    # 1x1 pixel PNG image
    return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="


@pytest.fixture
def sample_coordinates() -> dict:
    """Sample GPS coordinates (near Empire State Building)"""
    return {
        "latitude": 40.748817,
        "longitude": -73.985428,
        "accuracy": 10,
        "altitude": 100.5
    }


@pytest.fixture
def invalid_coordinates() -> dict:
    """Invalid GPS coordinates for testing"""
    return {
        "latitude": 95.0,  # Invalid: > 90
        "longitude": -73.985428,
        "accuracy": 10
    }


@pytest.fixture
async def auth_headers(test_manager_user) -> dict:
    """Generate authentication headers for manager"""
    from app.security.jwt_handler import create_access_token

    token = create_access_token({
        "sub": str(test_manager_user.id),
        "email": test_manager_user.email,
        "role": test_manager_user.role.value
    })

    return {"Authorization": f"Bearer {token}"}
