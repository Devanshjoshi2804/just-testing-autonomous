"""
Rate Limiting Middleware
Protect API from abuse using Redis-based rate limiting
"""
import time
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger
import redis

from src.config import settings


class RateLimiter:
    """
    Redis-based rate limiter using sliding window algorithm

    Supports:
    - Per-IP rate limiting
    - Per-API-key rate limiting
    - Different limits for different endpoints
    - Burst protection
    """

    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        default_limit: int = 100,
        default_window: int = 60
    ):
        """
        Initialize rate limiter

        Args:
            redis_client: Redis client (optional, will create if not provided)
            default_limit: Default requests per window
            default_window: Window size in seconds
        """
        self.redis_client = redis_client or redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
        )
        self.default_limit = default_limit
        self.default_window = default_window

    def _get_client_identifier(self, request: Request) -> str:
        """
        Get unique identifier for client

        Priority:
        1. API key (if present)
        2. X-Forwarded-For header
        3. Client IP address
        """
        # Check for API key in header
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"apikey:{api_key}"

        # Check for forwarded IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Get first IP in chain
            return f"ip:{forwarded.split(',')[0].strip()}"

        # Use client IP
        if request.client:
            return f"ip:{request.client.host}"

        return "unknown"

    def is_allowed(
        self,
        request: Request,
        limit: Optional[int] = None,
        window: Optional[int] = None
    ) -> tuple[bool, dict]:
        """
        Check if request is allowed based on rate limit

        Args:
            request: FastAPI request
            limit: Requests per window (optional, uses default if not provided)
            window: Window size in seconds (optional, uses default if not provided)

        Returns:
            tuple: (is_allowed, rate_limit_info)
        """
        limit = limit or self.default_limit
        window = window or self.default_window

        # Get client identifier
        client_id = self._get_client_identifier(request)

        # Get current timestamp
        now = int(time.time())
        window_start = now - window

        # Redis key for this client
        key = f"ratelimit:{client_id}"

        try:
            # Remove old entries (outside window)
            self.redis_client.zremrangebyscore(key, 0, window_start)

            # Count requests in current window
            request_count = self.redis_client.zcard(key)

            # Check if limit exceeded
            if request_count >= limit:
                # Get window reset time
                oldest = self.redis_client.zrange(key, 0, 0, withscores=True)
                reset_time = int(oldest[0][1]) + window if oldest else now + window

                rate_limit_info = {
                    "limit": limit,
                    "remaining": 0,
                    "reset": reset_time,
                    "window": window,
                }

                return False, rate_limit_info

            # Add current request to window
            self.redis_client.zadd(key, {str(now): now})

            # Set expiration on key
            self.redis_client.expire(key, window)

            # Calculate remaining requests
            remaining = limit - (request_count + 1)

            # Calculate reset time
            reset_time = now + window

            rate_limit_info = {
                "limit": limit,
                "remaining": remaining,
                "reset": reset_time,
                "window": window,
            }

            return True, rate_limit_info

        except redis.RedisError as e:
            # Redis error - allow request but log error
            logger.error(f"Rate limiter Redis error: {e}")

            # Return permissive response on error
            return True, {
                "limit": limit,
                "remaining": limit,
                "reset": now + window,
                "window": window,
            }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting all requests
    """

    def __init__(
        self,
        app,
        limiter: Optional[RateLimiter] = None,
        limit: int = 100,
        window: int = 60,
        exclude_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.limiter = limiter or RateLimiter(default_limit=limit, default_window=window)
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/redoc", "/openapi.json"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Check rate limit
        is_allowed, rate_info = self.limiter.is_allowed(request)

        # Add rate limit headers to response
        response = None
        if is_allowed:
            response = await call_next(request)
        else:
            # Rate limit exceeded
            logger.warning(
                "Rate limit exceeded",
                client=self.limiter._get_client_identifier(request),
                path=request.url.path,
                limit=rate_info["limit"],
            )

            response = Response(
                content="Rate limit exceeded. Please try again later.",
                status_code=429,
            )

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(rate_info["reset"])

        return response


# Endpoint-specific rate limiting decorator
def rate_limit(limit: int = 10, window: int = 60):
    """
    Decorator for endpoint-specific rate limiting

    Usage:
        @app.post("/api/endpoint")
        @rate_limit(limit=10, window=60)
        async def endpoint():
            pass
    """
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            limiter = RateLimiter()
            is_allowed, rate_info = limiter.is_allowed(request, limit=limit, window=window)

            if not is_allowed:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded",
                    headers={
                        "X-RateLimit-Limit": str(rate_info["limit"]),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(rate_info["reset"]),
                    }
                )

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator
