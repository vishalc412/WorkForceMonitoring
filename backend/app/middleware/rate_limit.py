"""
Rate limiting middleware using Redis
"""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import redis.asyncio as aioredis
import time

from app.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using sliding window algorithm
    """

    def __init__(self, app, redis_client: aioredis.Redis = None):
        super().__init__(app)
        self.redis_client = redis_client

    async def dispatch(self, request: Request, call_next: Callable):
        """
        Apply rate limiting based on endpoint and client IP
        """
        # Skip rate limiting for health check
        if request.url.path == "/health":
            return await call_next(request)

        # Get client IP
        client_ip = request.client.host

        # Determine rate limit based on endpoint
        rate_limit_key, limit, window = self._get_rate_limit_config(request.url.path)

        if rate_limit_key and self.redis_client:
            # Check rate limit
            is_allowed = await self._check_rate_limit(
                client_ip,
                rate_limit_key,
                limit,
                window
            )

            if not is_allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Maximum {limit} requests per {window} seconds.",
                    headers={"Retry-After": str(window)}
                )

        response = await call_next(request)
        return response

    def _get_rate_limit_config(self, path: str) -> tuple:
        """
        Get rate limit configuration for specific endpoint

        Returns:
            Tuple of (key, limit, window_seconds)
        """
        # Login endpoint: 5 requests per 15 minutes
        if "/api/auth/login" in path:
            return "login", 5, 900  # 15 minutes

        # Check-in endpoint: 10 requests per hour
        if "/api/monitoring/checkin" in path:
            return "checkin", 10, 3600  # 1 hour

        # Check-out endpoint: 10 requests per hour
        if "/api/monitoring/checkout" in path:
            return "checkout", 10, 3600

        # General API: 100 requests per minute
        if path.startswith("/api/"):
            return "general", 100, 60

        return None, None, None

    async def _check_rate_limit(
        self,
        client_ip: str,
        endpoint: str,
        limit: int,
        window: int
    ) -> bool:
        """
        Check if request is within rate limit using sliding window

        Args:
            client_ip: Client IP address
            endpoint: Endpoint identifier
            limit: Maximum requests allowed
            window: Time window in seconds

        Returns:
            True if allowed, False if rate limit exceeded
        """
        if not self.redis_client:
            return True  # Allow if Redis not available

        key = f"rate_limit:{endpoint}:{client_ip}"
        current_time = int(time.time())
        window_start = current_time - window

        try:
            # Remove old entries outside the window
            await self.redis_client.zremrangebyscore(key, 0, window_start)

            # Count requests in current window
            request_count = await self.redis_client.zcard(key)

            if request_count >= limit:
                return False

            # Add current request
            await self.redis_client.zadd(key, {str(current_time): current_time})

            # Set expiration on the key
            await self.redis_client.expire(key, window)

            return True

        except Exception as e:
            # Log error but don't block request if Redis fails
            print(f"Rate limit check failed: {e}")
            return True


async def get_redis_client() -> aioredis.Redis:
    """
    Get Redis client for rate limiting
    """
    try:
        redis_client = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        return redis_client
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")
        return None
