"""
Rate Limiting Middleware
Redis-based distributed rate limiting for API endpoints
"""
import time
from typing import Optional, Callable, Dict, Tuple
from functools import wraps

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from loguru import logger
from redis import Redis
from redis.exceptions import RedisError

from src.config import settings


class RateLimiter:
    """
    Redis-based rate limiter using sliding window algorithm

    Supports:
    - Per-IP rate limiting
    - Per-user rate limiting (if authenticated)
    - Configurable time windows and limits
    - Distributed rate limiting across multiple API instances
    """

    def __init__(
        self,
        redis_client: Optional[Redis] = None,
        default_limit: int = 100,
        default_window: int = 60
    ):
        """
        Initialize rate limiter

        Args:
            redis_client: Redis client instance (optional, will get from config if None)
            default_limit: Default number of requests allowed per window
            default_window: Default time window in seconds
        """
        self.redis_client = redis_client
        self.default_limit = default_limit
        self.default_window = default_window

        # Fallback to in-memory if Redis unavailable
        self.fallback_storage: Dict[str, list] = {}

    def _get_redis_client(self) -> Optional[Redis]:
        """Get Redis client, handling initialization gracefully"""
        if self.redis_client is not None:
            return self.redis_client

        try:
            from src.cache.redis_config import get_redis
            return get_redis()
        except Exception as e:
            logger.warning(f"Redis not available for rate limiting: {e}")
            return None

    def _get_client_identifier(self, request: Request) -> str:
        """
        Get unique identifier for rate limiting

        Uses client IP as identifier. In production, you might want to use:
        - API key
        - User ID (from authentication)
        - Combination of multiple factors
        """
        # Try to get real IP from X-Forwarded-For header (if behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get first IP in chain (original client)
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            # Use direct client IP
            client_ip = request.client.host if request.client else "unknown"

        return f"ratelimit:{client_ip}"

    def _check_rate_limit_redis(
        self,
        key: str,
        limit: int,
        window: int
    ) -> Tuple[bool, int, int]:
        """
        Check rate limit using Redis sliding window

        Returns:
            Tuple of (allowed, current_count, reset_time)
        """
        redis = self._get_redis_client()
        if redis is None:
            return self._check_rate_limit_fallback(key, limit, window)

        try:
            current_time = int(time.time())
            window_start = current_time - window

            # Redis sliding window implementation
            pipe = redis.pipeline()

            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, window_start)

            # Add current request
            pipe.zadd(key, {f"{current_time}:{time.time_ns()}": current_time})

            # Count requests in window
            pipe.zcard(key)

            # Set expiry to window duration
            pipe.expire(key, window + 1)

            # Execute pipeline
            results = pipe.execute()

            # Get count from results
            current_count = results[2]

            # Calculate reset time
            reset_time = current_time + window

            # Check if limit exceeded
            allowed = current_count <= limit

            return allowed, current_count, reset_time

        except RedisError as e:
            logger.error(f"Redis rate limit check failed: {e}")
            # Fallback to in-memory on Redis errors
            return self._check_rate_limit_fallback(key, limit, window)

    def _check_rate_limit_fallback(
        self,
        key: str,
        limit: int,
        window: int
    ) -> Tuple[bool, int, int]:
        """
        Fallback in-memory rate limiting

        NOT suitable for production with multiple instances!
        Only used when Redis is unavailable.
        """
        current_time = time.time()
        window_start = current_time - window

        # Get or create request list
        if key not in self.fallback_storage:
            self.fallback_storage[key] = []

        # Remove old entries
        self.fallback_storage[key] = [
            req_time for req_time in self.fallback_storage[key]
            if req_time > window_start
        ]

        # Add current request
        self.fallback_storage[key].append(current_time)

        # Count and check
        current_count = len(self.fallback_storage[key])
        reset_time = int(current_time + window)
        allowed = current_count <= limit

        # Cleanup old keys (prevent memory leak)
        if len(self.fallback_storage) > 10000:
            # Remove oldest 20% of keys
            keys_to_remove = list(self.fallback_storage.keys())[:2000]
            for k in keys_to_remove:
                del self.fallback_storage[k]

        return allowed, current_count, reset_time

    def check_rate_limit(
        self,
        request: Request,
        limit: Optional[int] = None,
        window: Optional[int] = None,
        key_prefix: Optional[str] = None
    ) -> Tuple[bool, int, int, int]:
        """
        Check if request is within rate limit

        Args:
            request: FastAPI request object
            limit: Max requests per window (None = use default)
            window: Time window in seconds (None = use default)
            key_prefix: Optional prefix for rate limit key (e.g., "upload:", "test:")

        Returns:
            Tuple of (allowed, current_count, limit, reset_time)
        """
        limit = limit or self.default_limit
        window = window or self.default_window

        # Build rate limit key
        client_id = self._get_client_identifier(request)
        key = f"{key_prefix}:{client_id}" if key_prefix else client_id

        # Check rate limit
        allowed, current_count, reset_time = self._check_rate_limit_redis(
            key, limit, window
        )

        return allowed, current_count, limit, reset_time


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(
            default_limit=getattr(settings, 'RATE_LIMIT_PER_MINUTE', 100),
            default_window=60
        )
    return _rate_limiter


def rate_limit(
    limit: int = 100,
    window: int = 60,
    key_prefix: Optional[str] = None
):
    """
    Decorator for rate limiting endpoints

    Usage:
        @router.post("/upload")
        @rate_limit(limit=10, window=60, key_prefix="upload")
        async def upload_endpoint():
            ...

    Args:
        limit: Maximum requests per window
        window: Time window in seconds
        key_prefix: Optional prefix for rate limit key
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if request is None:
                request = kwargs.get('request')

            if request is None:
                logger.warning("No request object found for rate limiting")
                return await func(*args, **kwargs)

            # Check rate limit
            limiter = get_rate_limiter()
            allowed, current, max_limit, reset_time = limiter.check_rate_limit(
                request,
                limit=limit,
                window=window,
                key_prefix=key_prefix
            )

            # Add rate limit headers to response
            # Note: This is a simplified version; in production you'd want to
            # ensure these headers are added to all responses

            if not allowed:
                # Rate limit exceeded
                logger.warning(
                    f"Rate limit exceeded for {limiter._get_client_identifier(request)}: "
                    f"{current}/{max_limit} requests in {window}s"
                )

                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "RateLimitExceeded",
                        "message": f"Rate limit exceeded: {max_limit} requests per {window} seconds",
                        "retry_after": reset_time - int(time.time()),
                        "limit": max_limit,
                        "window": window,
                        "current": current
                    },
                    headers={
                        "X-RateLimit-Limit": str(max_limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_time),
                        "Retry-After": str(reset_time - int(time.time()))
                    }
                )

            # Rate limit OK - proceed with request
            logger.debug(
                f"Rate limit OK: {current}/{max_limit} "
                f"for {limiter._get_client_identifier(request)}"
            )

            # Call the actual endpoint
            response = await func(*args, **kwargs)

            # TODO: Add rate limit headers to response
            # This would require middleware or response modification

            return response

        return wrapper
    return decorator


async def rate_limit_middleware(request: Request, call_next):
    """
    Global rate limiting middleware

    Applies a default rate limit to all endpoints.
    Individual endpoints can override with @rate_limit decorator.
    """
    # Skip rate limiting for health checks and metrics
    if request.url.path in ["/health", "/metrics", "/health/metrics"]:
        return await call_next(request)

    # Apply global rate limit
    limiter = get_rate_limiter()
    allowed, current, max_limit, reset_time = limiter.check_rate_limit(request)

    if not allowed:
        logger.warning(
            f"Global rate limit exceeded for {limiter._get_client_identifier(request)}"
        )
        return JSONResponse(
            status_code=429,
            content={
                "error": "RateLimitExceeded",
                "message": f"Too many requests: {max_limit} per minute",
                "retry_after": reset_time - int(time.time())
            },
            headers={
                "X-RateLimit-Limit": str(max_limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_time),
                "Retry-After": str(reset_time - int(time.time()))
            }
        )

    # Proceed with request
    response = await call_next(request)

    # Add rate limit headers
    remaining = max(0, max_limit - current)
    response.headers["X-RateLimit-Limit"] = str(max_limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset_time)

    return response
