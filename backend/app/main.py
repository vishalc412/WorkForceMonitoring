"""
Main FastAPI application with comprehensive middleware and error handling
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database.db import init_db, close_db
from app.api import auth_routes, monitoring_routes, dashboard_routes, gdpr_routes
from app.utils.exceptions import AppException, ErrorResponse
from app.middleware.rate_limit import RateLimitMiddleware, get_redis_client

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global Redis client for rate limiting
redis_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    """
    global redis_client

    # Startup
    logger.info("Starting application...")
    await init_db()
    logger.info("Database initialized")

    # Initialize Redis for rate limiting
    redis_client = await get_redis_client()
    if redis_client:
        logger.info("Redis connected for rate limiting")
    else:
        logger.warning("Redis not available - rate limiting disabled")

    yield

    # Shutdown
    logger.info("Shutting down application...")
    await close_db()
    logger.info("Database connections closed")

    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Workforce Monitoring Application - Ethical Employee Tracking System",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None
)

# Add Security Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)  # Compress responses

if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure with actual domains in production
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Error-Code", "X-Request-ID"]
)

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware, redis_client=redis_client)


# Exception handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handle custom application exceptions"""
    logger.warning(f"Application exception: {exc.error_code} - {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_response().dict()
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    logger.warning(f"Validation error: {errors}")

    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error="validation_error",
            message="Invalid input data",
            code="VALIDATION_ERROR",
            timestamp=datetime.utcnow().isoformat() + "Z",
            details={"errors": errors}
        ).dict()
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTP exceptions"""
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="http_error",
            message=exc.detail,
            code=f"HTTP_{exc.status_code}",
            timestamp=datetime.utcnow().isoformat() + "Z"
        ).dict()
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="internal_server_error",
            message="An internal error occurred" if not settings.DEBUG else str(exc),
            code="INTERNAL_ERROR",
            timestamp=datetime.utcnow().isoformat() + "Z"
        ).dict()
    )


from datetime import datetime


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Workforce Monitoring API",
        "version": settings.APP_VERSION,
        "docs": "/api/docs" if settings.DEBUG else "Documentation disabled in production"
    }


# Include routers
app.include_router(auth_routes.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(monitoring_routes.router, prefix="/api/monitoring", tags=["Monitoring"])
app.include_router(dashboard_routes.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(gdpr_routes.router, prefix="/api/gdpr", tags=["GDPR Compliance"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
