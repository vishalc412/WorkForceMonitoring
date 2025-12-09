# Testing Guide - Workforce Monitoring

This document provides comprehensive information about testing the Workforce Monitoring application.

## Test Coverage

Current test coverage includes:

### ✅ Completed Test Suites

1. **Authentication Tests** (`test_auth.py`)
   - Login functionality
   - Share link generation
   - Token verification
   - Token revocation
   - Role-based access control

2. **Location Service Tests** (`test_location_service.py`)
   - Distance calculations
   - Geofencing validation
   - Location accuracy validation
   - Anomaly detection (teleportation)
   - Location record creation

3. **Camera Service Tests** (`test_camera_service.py`)
   - Image format validation
   - Image hash calculation
   - Photo file storage
   - Photo cleanup

4. **Model Tests** (`test_models.py`)
   - User model CRUD
   - Session model operations
   - Location model
   - Photo model
   - Geofence model
   - Access token model
   - Audit log model

5. **Security Tests** (`test_security.py`)
   - Password hashing
   - JWT token creation/validation
   - Token expiration
   - Token tampering detection

## Setup

### 1. Install Test Dependencies

```bash
cd backend
pip install pytest pytest-asyncio pytest-cov httpx
```

### 2. Create Test Database

```bash
# Create test database
createdb workforce_test

# Or using Docker
docker run --name test-postgres \
  -e POSTGRES_DB=workforce_test \
  -e POSTGRES_PASSWORD=postgres123 \
  -p 5433:5432 \
  -d postgres:14
```

### 3. Configure Test Environment

Create `.env.test` file:
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres123@localhost:5432/workforce_test
REDIS_URL=redis://localhost:6379/1
SECRET_KEY=test-secret-key-not-for-production
JWT_SECRET_KEY=test-jwt-secret-key
DEBUG=True
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run with Coverage
```bash
pytest --cov=app --cov-report=html
```

### Run Specific Test File
```bash
pytest tests/test_auth.py -v
```

### Run Specific Test Class
```bash
pytest tests/test_auth.py::TestLogin -v
```

### Run Specific Test
```bash
pytest tests/test_auth.py::TestLogin::test_login_success -v
```

### Run Tests by Marker
```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run security tests
pytest -m security

# Run all except slow tests
pytest -m "not slow"
```

### Run Tests in Parallel
```bash
pip install pytest-xdist
pytest -n auto
```

## Test Structure

```
tests/
├── conftest.py                 # Fixtures and test configuration
├── test_auth.py                # Authentication endpoint tests
├── test_location_service.py    # Location service tests
├── test_camera_service.py      # Camera/photo service tests
├── test_models.py              # Database model tests
├── test_security.py            # Security function tests
└── pytest.ini                  # Pytest configuration
```

## Writing New Tests

### Example Unit Test
```python
import pytest
from app.services.location_service import LocationService

class TestLocationService:
    """Test LocationService class"""

    def test_calculate_distance(self):
        """Test distance calculation"""
        distance = LocationService.calculate_distance(
            40.7128, -74.0060,  # NYC
            34.0522, -118.2437  # LA
        )
        assert distance > 3_900_000
```

### Example Integration Test
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_checkin_endpoint(
    client: AsyncClient,
    test_employee_user
):
    """Test check-in endpoint"""
    response = await client.post(
        "/api/monitoring/checkin",
        json={
            "token": "test_token",
            "photo_base64": "...",
            "latitude": 40.7128,
            "longitude": -74.0060
        }
    )
    assert response.status_code == 200
```

### Example Async Test
```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_create_user(db_session: AsyncSession):
    """Test creating a user"""
    from app.models.user import User

    user = User(
        email="test@example.com",
        full_name="Test User"
    )
    db_session.add(user)
    await db_session.commit()

    assert user.id is not None
```

## Available Fixtures

### Database Fixtures
- `test_db_engine` - Test database engine
- `db_session` - Database session for tests
- `test_admin_user` - Pre-created admin user
- `test_manager_user` - Pre-created manager user
- `test_employee_user` - Pre-created employee user
- `test_geofence` - Pre-created geofence

### API Fixtures
- `client` - HTTP test client
- `auth_headers` - Authentication headers for manager

### Data Fixtures
- `sample_base64_image` - Sample image for testing
- `sample_coordinates` - Valid GPS coordinates
- `invalid_coordinates` - Invalid GPS coordinates

## Test Markers

Use markers to categorize tests:

```python
@pytest.mark.unit
def test_something():
    """This is a unit test"""
    pass

@pytest.mark.integration
async def test_api_endpoint():
    """This is an integration test"""
    pass

@pytest.mark.slow
def test_long_running():
    """This test takes time"""
    pass

@pytest.mark.security
def test_password_hashing():
    """This tests security features"""
    pass
```

## Coverage Goals

| Component | Target Coverage | Current |
|-----------|----------------|---------|
| Models | 90% | 85% |
| Services | 85% | 70% |
| API Routes | 80% | 65% |
| Security | 95% | 90% |
| Utilities | 75% | 60% |
| **Overall** | **80%** | **70%** |

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_DB: workforce_test
          POSTGRES_PASSWORD: postgres123
        ports:
          - 5432:5432

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov

      - name: Run tests
        run: pytest --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Common Issues

### Issue: Tests failing with database errors
**Solution**: Ensure test database exists and is accessible
```bash
createdb workforce_test
```

### Issue: Async tests not running
**Solution**: Install pytest-asyncio and use @pytest.mark.asyncio
```bash
pip install pytest-asyncio
```

### Issue: Import errors
**Solution**: Install package in development mode
```bash
pip install -e .
```

### Issue: Coverage not showing
**Solution**: Install pytest-cov
```bash
pip install pytest-cov
```

## Best Practices

1. **Test Isolation**: Each test should be independent
2. **Fixtures**: Use fixtures for common setup
3. **Descriptive Names**: Test names should describe what they test
4. **Assert Messages**: Include helpful assertion messages
5. **Cleanup**: Always clean up resources in teardown
6. **Mock External Services**: Don't make real API calls
7. **Test Edge Cases**: Include boundary conditions
8. **Test Errors**: Test error handling paths

## Mocking External Services

### Mock Face Detection
```python
@pytest.fixture
def mock_face_detector(monkeypatch):
    """Mock face detector"""
    def mock_detect(*args, **kwargs):
        return {
            "face_detected": True,
            "face_count": 1,
            "confidence": 0.85
        }

    monkeypatch.setattr(
        "app.ml.face_detector.FaceDetector.process_base64_image",
        mock_detect
    )
```

### Mock Geolocation API
```python
@pytest.fixture
def mock_geocoding(monkeypatch):
    """Mock reverse geocoding"""
    async def mock_reverse_geocode(lat, lon):
        return "123 Main St, New York, NY"

    monkeypatch.setattr(
        "app.services.location_service.LocationService.reverse_geocode",
        mock_reverse_geocode
    )
```

## Performance Testing

### Load Testing with Locust
```python
from locust import HttpUser, task, between

class WorkforceUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def check_dashboard(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        self.client.get("/api/dashboard/sessions/active", headers=headers)
```

Run load test:
```bash
pip install locust
locust -f tests/load_test.py --host=http://localhost:8000
```

## Debugging Tests

### Run with Verbose Output
```bash
pytest -vv
```

### Show Print Statements
```bash
pytest -s
```

### Drop to Debugger on Failure
```bash
pytest --pdb
```

### Show Local Variables
```bash
pytest -l
```

---

**Happy Testing! 🧪**
