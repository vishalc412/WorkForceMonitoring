# Workforce Monitoring Application

An ethical workforce monitoring system with real-time employee location tracking, camera-based authentication, and comprehensive reporting capabilities.

## 🚀 Features

### Core Functionality
- ✅ **Real-time Employee Tracking** - Monitor employee check-in/check-out with GPS location
- ✅ **Camera Authentication** - Face detection and liveness verification using MediaPipe
- ✅ **Geofencing** - Define authorized work locations with radius-based validation
- ✅ **Share Link System** - Secure, time-limited access links for employees
- ✅ **Manager Dashboard** - Real-time monitoring of active sessions
- ✅ **Location Anomaly Detection** - Detect impossible location changes
- ⏳ **WebSocket Real-time Updates** - Live dashboard updates (pending)
- ⏳ **Reporting & Analytics** - CSV/PDF export functionality (pending)

### Security & Compliance
- 🔒 **JWT Authentication** - Secure token-based auth with role-based access control
- 🔒 **Data Encryption** - AES-256 for sensitive data, HTTPS for all communications
- 🔒 **GDPR Compliance** - Data retention policies, consent management, audit logging
- 🔒 **Rate Limiting** - Protection against brute force attacks
- 🔒 **Password Hashing** - Bcrypt with configurable cost factor

### Privacy Features
- 🛡️ **Explicit Consent** - GDPR-compliant consent management
- 🛡️ **Data Retention** - Automatic photo deletion after 30 days
- 🛡️ **Audit Logging** - Comprehensive audit trail of all actions
- 🛡️ **Access Control** - Role-based permissions (Admin/Manager/Employee)

---

## 📋 Prerequisites

- **Python 3.11+**
- **Node.js 18+** (for frontend)
- **PostgreSQL 14+**
- **Redis 7+**
- **Docker & Docker Compose** (optional)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                       │
│  ┌────────────────┐  ┌────────────────┐  ┌───────────────┐ │
│  │ Check-in Page  │  │ Manager Dash   │  │ Reports       │ │
│  │ - Camera       │  │ - Real-time    │  │ - Analytics   │ │
│  │ - Geolocation  │  │ - Map View     │  │ - Export      │ │
│  └────────────────┘  └────────────────┘  └───────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                    REST API + WebSocket
                              │
┌─────────────────────────────────────────────────────────────┐
│                   Backend (FastAPI)                         │
│  ┌────────────────┐  ┌────────────────┐  ┌───────────────┐ │
│  │ Auth Service   │  │ Monitoring     │  │ Location      │ │
│  │ Camera Service │  │ Face Detection │  │ Geofencing    │ │
│  └────────────────┘  └────────────────┘  └───────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼──────┐    ┌─────────▼────────┐    ┌──────▼───────┐
│  PostgreSQL  │    │  Redis Cache     │    │ File Storage │
│  - Sessions  │    │  - Real-time     │    │ - Photos     │
│  - Users     │    │  - Rate Limits   │    │ - Reports    │
└──────────────┘    └──────────────────┘    └──────────────┘
```

---

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

1. **Clone the repository**
```bash
git clone <repository-url>
cd WorkForceMonitoring
```

2. **Configure environment**
```bash
cd backend
cp .env.example .env
# Edit .env with your configuration
```

3. **Start services**
```bash
docker-compose up -d
```

4. **Initialize database**
```bash
docker-compose exec backend python -m alembic upgrade head
```

5. **Create admin user**
```bash
docker-compose exec backend python scripts/create_admin.py
```

6. **Access the application**
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/api/docs
- Frontend: http://localhost:3000 (when built)

### Option 2: Manual Setup

#### Backend Setup

1. **Install Python dependencies**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Set up PostgreSQL**
```bash
# Create database
createdb workforce_monitoring

# Or using psql
psql -U postgres
CREATE DATABASE workforce_monitoring;
\q
```

3. **Set up Redis**
```bash
# Install Redis (macOS)
brew install redis
brew services start redis

# Or using Docker
docker run -d -p 6379:6379 redis:7-alpine
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your database credentials
```

5. **Initialize database**
```bash
# Run migrations
alembic upgrade head
```

6. **Create admin user**
```bash
python scripts/create_admin.py
```

7. **Run the application**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 📚 API Documentation

### Authentication Endpoints

#### 1. Manager Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "manager@company.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "refresh_token_here",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "uuid",
    "email": "manager@company.com",
    "full_name": "John Manager",
    "role": "manager"
  }
}
```

#### 2. Generate Share Link
```http
POST /api/auth/generate-link
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "user_id": "employee_uuid",
  "expiration_hours": 8
}
```

**Response:**
```json
{
  "share_link": "http://localhost:3000/checkin/abc123xyz...",
  "token_id": "uuid",
  "expires_at": "2025-12-09T20:00:00Z",
  "single_use": true
}
```

### Monitoring Endpoints

#### 3. Employee Check-in
```http
POST /api/monitoring/checkin
Content-Type: application/json

{
  "token": "abc123xyz...",
  "photo_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "accuracy": 10,
  "altitude": 100.5,
  "device_fingerprint": "device_hash"
}
```

**Response:**
```json
{
  "success": true,
  "session_id": "session_uuid",
  "checkin_time": "2025-12-09T12:30:45Z",
  "status": "active",
  "location": {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "within_geofence": true,
    "address": "Office Location"
  },
  "photo_verified": true,
  "liveness_score": 0.85,
  "anomaly_detected": false
}
```

#### 4. Employee Check-out
```http
POST /api/monitoring/checkout
Content-Type: application/json

{
  "session_id": "session_uuid",
  "photo_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "accuracy": 10
}
```

**Response:**
```json
{
  "success": true,
  "session_id": "session_uuid",
  "checkout_time": "2025-12-09T17:30:45Z",
  "duration_minutes": 300,
  "duration_hours": 5.0,
  "status": "completed",
  "location": {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "within_geofence": true
  }
}
```

### Dashboard Endpoints

#### 5. Get Active Sessions
```http
GET /api/dashboard/sessions/active
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "active_sessions": [
    {
      "session_id": "uuid",
      "user_id": "uuid",
      "employee_name": "John Doe",
      "department": "Sales",
      "checkin_time": "2025-12-09T09:00:00Z",
      "duration_minutes": 210,
      "current_location": {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "within_geofence": true,
        "address": "Office Location"
      }
    }
  ],
  "total_active": 1,
  "timestamp": "2025-12-09T12:30:00Z"
}
```

#### 6. Dashboard Statistics
```http
GET /api/dashboard/stats
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "active_employees": 25,
  "today_checkins": 48,
  "today_completed": 23,
  "timestamp": "2025-12-09T12:30:00Z"
}
```

---

## 🗄️ Database Schema

### Users Table
```sql
id              UUID PRIMARY KEY
email           VARCHAR(255) UNIQUE
full_name       VARCHAR(255)
password_hash   VARCHAR(255)
role            ENUM('admin', 'manager', 'employee')
department      VARCHAR(255)
is_active       BOOLEAN
consent_gdpr    BOOLEAN
created_at      TIMESTAMP
```

### Sessions Table
```sql
id                  UUID PRIMARY KEY
user_id             UUID FOREIGN KEY
checkin_time        TIMESTAMP
checkout_time       TIMESTAMP
duration_minutes    INTEGER
status              ENUM('active', 'completed', 'abandoned')
checkin_photo_id    UUID
checkout_photo_id   UUID
checkin_location_id UUID
checkout_location_id UUID
```

### Locations Table
```sql
id                  UUID PRIMARY KEY
session_id          UUID FOREIGN KEY
latitude            DECIMAL(10, 8)
longitude           DECIMAL(11, 8)
accuracy_meters     INTEGER
is_within_geofence  BOOLEAN
location_type       ENUM('checkin', 'checkout')
captured_at         TIMESTAMP
```

### Photos Table
```sql
id                 UUID PRIMARY KEY
user_id            UUID FOREIGN KEY
session_id         UUID FOREIGN KEY
file_path          VARCHAR(500)
face_detected      BOOLEAN
liveness_score     DECIMAL(3, 2)
liveness_verified  BOOLEAN
faces_count        INTEGER
photo_type         ENUM('checkin', 'checkout')
expiry_date        DATE
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `SECRET_KEY` | Application secret key | Required |
| `JWT_SECRET_KEY` | JWT signing key | Required |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token expiration | `15` |
| `SHARE_LINK_EXPIRE_HOURS` | Share link expiration | `8` |
| `PHOTO_RETENTION_DAYS` | Photo retention period | `30` |
| `LOCATION_RETENTION_DAYS` | Location data retention | `90` |
| `FACE_CONFIDENCE_THRESHOLD` | Face detection threshold | `0.6` |
| `LIVENESS_THRESHOLD` | Liveness detection threshold | `0.7` |
| `DEFAULT_GEOFENCE_RADIUS_METERS` | Default geofence radius | `500` |

---

## 🧪 Testing

### Run Tests
```bash
cd backend
pytest tests/ -v
```

### Run Specific Test
```bash
pytest tests/test_camera.py -v
```

### Coverage Report
```bash
pytest --cov=app tests/
```

---

## 🛡️ Security Considerations

### Data Protection
- All passwords are hashed using bcrypt with cost factor 10
- JWT tokens expire after 15 minutes
- Share links are single-use and time-limited
- All API communication over HTTPS in production
- Data at rest encrypted using AES-256

### Privacy Compliance
- **GDPR**: Right to access, rectification, erasure, data portability
- **CCPA**: Consumer rights to know, delete, opt-out
- **Consent**: Explicit opt-in required before data collection
- **Retention**: Automated data cleanup after retention period

### Rate Limiting
- Login: 5 attempts per 15 minutes
- Check-in: 10 attempts per hour
- General API: 100 requests per minute

---

## 📊 Monitoring & Logging

### Structured Logging
```python
logger.info(
    "checkin_success",
    user_id="uuid",
    session_id="uuid",
    duration_ms=450,
    face_liveness=0.92
)
```

### Health Check
```bash
curl http://localhost:8000/health
```

---

## 🚢 Deployment

### Production Checklist

- [ ] Set strong `SECRET_KEY` and `JWT_SECRET_KEY`
- [ ] Configure PostgreSQL with SSL
- [ ] Enable Redis password authentication
- [ ] Set up HTTPS with valid SSL certificate
- [ ] Configure firewall rules
- [ ] Enable database backups
- [ ] Set up monitoring (Sentry, CloudWatch, etc.)
- [ ] Configure CORS for production domain
- [ ] Disable DEBUG mode
- [ ] Set up log aggregation
- [ ] Configure automated photo cleanup cron job

### AWS Deployment Example

```bash
# Create RDS PostgreSQL instance
# Create ElastiCache Redis cluster
# Deploy to ECS/Fargate or EC2
# Configure ALB with SSL certificate
# Set up S3 for photo storage
# Configure CloudWatch for logs
```

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## ⚠️ Ethical Considerations

This application is designed for **ethical workforce management** with employee consent. Usage must comply with:

- Local labor laws and regulations
- Data protection regulations (GDPR, CCPA, etc.)
- Employee privacy rights
- Transparency requirements
- Informed consent requirements

**Prohibited Uses:**
- Surveillance without consent
- Tracking during non-work hours
- Discrimination based on monitoring data
- Sharing data with third parties without consent

---

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

---

## 📞 Support

For issues and questions:
- GitHub Issues: [Create an issue](https://github.com/your-repo/issues)
- Documentation: See `/docs` folder
- Email: support@workforce-monitoring.com

---

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [MediaPipe Face Detection](https://google.github.io/mediapipe/)
- [GDPR Compliance Guide](https://gdpr.eu/)
- [OWASP Security Guidelines](https://owasp.org/)

---

**Version:** 1.0.0
**Last Updated:** 2025-12-09