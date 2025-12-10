# Workforce Monitoring - Quick Setup Guide

This guide will help you get the application running quickly for development and testing.

## Prerequisites Installation

### 1. Install PostgreSQL
```bash
# macOS
brew install postgresql@14
brew services start postgresql@14

# Ubuntu/Debian
sudo apt-get install postgresql-14

# Or use Docker
docker run --name workforce-postgres -e POSTGRES_PASSWORD=postgres123 -p 5432:5432 -d postgres:14
```

### 2. Install Redis
```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server

# Or use Docker
docker run --name workforce-redis -p 6379:6379 -d redis:7-alpine
```

### 3. Install Python 3.11+
```bash
# macOS
brew install python@3.11

# Ubuntu/Debian
sudo apt-get install python3.11 python3.11-venv
```

---

## Backend Setup (5 minutes)

### Step 1: Navigate to backend directory
```bash
cd backend
```

### Step 2: Create virtual environment
```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure environment
```bash
cp .env.example .env
```

Edit `.env` file with your database credentials:
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres123@localhost:5432/workforce_monitoring
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-change-this
JWT_SECRET_KEY=your-jwt-secret-change-this
DEBUG=True
```

### Step 5: Create database
```bash
# Using psql
createdb workforce_monitoring

# Or using psql command
psql -U postgres
CREATE DATABASE workforce_monitoring;
\q
```

### Step 6: Initialize database tables
```bash
# Create tables (Alembic migrations will be set up later)
python -c "from app.database.db import init_db; import asyncio; asyncio.run(init_db())"
```

### Step 7: Create admin user
```bash
python scripts/create_admin.py
```

Follow the prompts to create your admin account.

### Step 8: Run the application
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Step 9: Test the API
Open your browser and navigate to:
- **API Documentation**: http://localhost:8000/api/docs
- **Health Check**: http://localhost:8000/health

---

## Docker Setup (Alternative - 2 minutes)

If you have Docker installed, this is the easiest way:

### Step 1: Configure environment
```bash
cd backend
cp .env.example .env
# Edit .env if needed (defaults work for Docker)
```

### Step 2: Start all services
```bash
cd ..
docker-compose up -d
```

### Step 3: Initialize database
```bash
docker-compose exec backend python -c "from app.database.db import init_db; import asyncio; asyncio.run(init_db())"
```

### Step 4: Create admin user
```bash
docker-compose exec backend python scripts/create_admin.py
```

### Step 5: Access the application
- API: http://localhost:8000/api/docs
- Health: http://localhost:8000/health

### Stop services
```bash
docker-compose down
```

---

## Testing the Application

### 1. Login as Manager
Using the API documentation at http://localhost:8000/api/docs:

1. Click on `POST /api/auth/login`
2. Click "Try it out"
3. Enter your credentials:
```json
{
  "email": "manager@company.com",
  "password": "manager123"
}
```
4. Click "Execute"
5. Copy the `access_token` from the response

### 2. Generate Share Link for Employee
1. Click on the lock icon (🔒) at the top right
2. Paste your access token
3. Click "Authorize"
4. Find `POST /api/auth/generate-link`
5. Try it out with:
```json
{
  "user_id": "<employee_uuid_from_database>",
  "expiration_hours": 8
}
```
6. Copy the generated `share_link`

### 3. Test Check-in (Requires Frontend)
The check-in requires:
- Camera access (for photo capture)
- Geolocation access (for GPS coordinates)
- Base64 encoded photo

For now, you can test the endpoint using a sample base64 image.

---

## Project Structure

```
backend/
├── app/
│   ├── api/              # API routes
│   ├── models/           # Database models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   ├── security/         # Auth & security
│   ├── ml/               # Face detection
│   ├── database/         # DB connection
│   ├── utils/            # Utilities
│   ├── config.py         # Configuration
│   └── main.py           # FastAPI app
├── scripts/              # Helper scripts
├── tests/                # Tests
├── uploads/              # File storage
├── requirements.txt      # Dependencies
├── Dockerfile           # Docker config
└── .env                 # Environment variables

frontend/                 # (To be built)
├── src/
│   ├── pages/           # React pages
│   ├── components/      # React components
│   ├── services/        # API services
│   └── hooks/           # Custom hooks
└── package.json
```

---

## Common Issues & Solutions

### Issue: Database connection failed
**Solution:**
- Check PostgreSQL is running: `pg_isready`
- Check database exists: `psql -l | grep workforce_monitoring`
- Verify DATABASE_URL in .env file

### Issue: Redis connection failed
**Solution:**
- Check Redis is running: `redis-cli ping` (should return "PONG")
- Verify REDIS_URL in .env file

### Issue: Import errors
**Solution:**
- Activate virtual environment: `source venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`

### Issue: Port already in use
**Solution:**
- Find process: `lsof -i :8000`
- Kill process: `kill -9 <PID>`
- Or use different port: `uvicorn app.main:app --port 8001`

### Issue: Face detection not working
**Solution:**
- Ensure OpenCV and MediaPipe are installed correctly
- On macOS: `brew install opencv`
- Try reinstalling: `pip install --force-reinstall opencv-python mediapipe`

---

## Next Steps

### 1. Frontend Development
The frontend needs to be built with:
- React 18+
- Camera access component
- Geolocation component
- Map integration (Leaflet)
- Dashboard with real-time updates

### 2. Additional Backend Features
- WebSocket implementation for real-time dashboard
- Report generation (CSV/PDF export)
- Email notifications
- Advanced analytics

### 3. Production Deployment
- Set up AWS/Cloud infrastructure
- Configure SSL/HTTPS
- Set up monitoring (Sentry, CloudWatch)
- Configure automated backups
- Implement rate limiting with Redis

---

## Development Workflow

### Running in Development Mode
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

### Running Tests
```bash
pytest tests/ -v
pytest --cov=app tests/
```

### Code Formatting
```bash
black app/
flake8 app/
```

### Database Migrations (Alembic)
```bash
# Create migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## API Endpoints Summary

### Authentication
- `POST /api/auth/login` - Manager login
- `POST /api/auth/generate-link` - Generate employee share link
- `POST /api/auth/verify-token` - Verify share token
- `POST /api/auth/revoke-link/{token_id}` - Revoke share link

### Monitoring
- `POST /api/monitoring/checkin` - Employee check-in
- `POST /api/monitoring/checkout` - Employee check-out
- `GET /api/monitoring/session/{session_id}` - Get session details

### Dashboard
- `GET /api/dashboard/sessions/active` - Get active sessions
- `GET /api/dashboard/stats` - Get dashboard statistics

### System
- `GET /health` - Health check
- `GET /` - API information

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| DATABASE_URL | Yes | - | PostgreSQL connection string |
| REDIS_URL | No | redis://localhost:6379/0 | Redis connection string |
| SECRET_KEY | Yes | - | App secret key |
| JWT_SECRET_KEY | Yes | - | JWT signing key |
| DEBUG | No | False | Debug mode |
| ACCESS_TOKEN_EXPIRE_MINUTES | No | 15 | JWT expiration |
| SHARE_LINK_EXPIRE_HOURS | No | 8 | Share link expiration |
| PHOTO_RETENTION_DAYS | No | 30 | Photo retention period |
| FACE_CONFIDENCE_THRESHOLD | No | 0.6 | Face detection threshold |
| LIVENESS_THRESHOLD | No | 0.7 | Liveness threshold |

---

## Support & Resources

- **Documentation**: See README.md for full documentation
- **API Docs**: http://localhost:8000/api/docs (when running)
- **GitHub Issues**: Report bugs and request features
- **Tech Stack**:
  - FastAPI: https://fastapi.tiangolo.com/
  - SQLAlchemy: https://www.sqlalchemy.org/
  - MediaPipe: https://google.github.io/mediapipe/

---

**Happy Coding! 🚀**
