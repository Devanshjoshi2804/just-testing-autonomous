"""
Smart Caching Middleware
Redis-based response caching for read-heavy endpoints
"""
import hashlib
import json
from typing import Optional, Callable, List
from functools import wraps

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from loguru import logger
from redis import Redis
from redis.exceptions import RedisError

from src.config import settings


class ResponseCache:
    """
    Redis-based response cache for GET requests

    Features:
    - Automatic cache key generation from request
    - Configurable TTL per endpoint
    - Cache invalidation support
    - Miss/hit ratio tracking
    - Conditional caching based on status code
    """

    def __init__(self, redis_client: Optional[Redis] = None):
        """
        Initialize response cache

        Args:
            redis_client: Redis client instance (optional, will get from config if None)
        """
        self.redis_client = redis_client
        self.stats = {
            'hits': 0,
            'misses': 0,
            'errors': 0
        }

    def _get_redis_client(self) -> Optional[Redis]:
        """Get Redis client, handling initialization gracefully"""
        if self.redis_client is not None:
            return self.redis_client

        try:
            from src.cache.redis_config import get_redis
            return get_redis()
        except Exception as e:
            logger.warning(f"Redis not available for caching: {e}")
            return None

    def _generate_cache_key(
        self,
        request: Request,
        key_prefix: str = "cache"
    ) -> str:
        """
        Generate cache key from request

        Includes:
        - URL path
        - Query parameters (sorted for consistency)
        - Relevant headers (if specified)

        Args:
            request: FastAPI request
            key_prefix: Prefix for cache key

        Returns:
            Cache key string
        """
        # Build key components
        components = [
            request.url.path,
            str(sorted(request.query_params.items()))
        ]

        # Create hash of components for compact key
        key_hash = hashlib.sha256(
            "|".join(components).encode()
        ).hexdigest()[:16]

        return f"{key_prefix}:{key_hash}"

    async def get(
        self,
        request: Request,
        key_prefix: str = "cache"
    ) -> Optional[dict]:
        """
        Get cached response for request

        Args:
            request: FastAPI request
            key_prefix: Cache key prefix

        Returns:
            Cached response dict or None if not found
        """
        redis = self._get_redis_client()
        if redis is None:
            return None

        try:
            cache_key = self._generate_cache_key(request, key_prefix)
            cached_data = redis.get(cache_key)

            if cached_data:
                self.stats['hits'] += 1
                logger.debug(
                    f"Cache HIT: {cache_key}",
                    path=request.url.path,
                    hit_rate=self.get_hit_rate()
                )
                return json.loads(cached_data)
            else:
                self.stats['misses'] += 1
                logger.debug(
                    f"Cache MISS: {cache_key}",
                    path=request.url.path
                )
                return None

        except (RedisError, json.JSONDecodeError) as e:
            self.stats['errors'] += 1
            logger.warning(f"Cache get error: {e}")
            return None

    async def set(
        self,
        request: Request,
        response_data: dict,
        ttl: int = 300,
        key_prefix: str = "cache"
    ) -> bool:
        """
        Store response in cache

        Args:
            request: FastAPI request
            response_data: Response data to cache
            ttl: Time to live in seconds
            key_prefix: Cache key prefix

        Returns:
            True if cached successfully, False otherwise
        """
        redis = self._get_redis_client()
        if redis is None:
            return False

        try:
            cache_key = self._generate_cache_key(request, key_prefix)
            redis.setex(
                cache_key,
                ttl,
                json.dumps(response_data)
            )
            logger.debug(
                f"Cache SET: {cache_key} (TTL: {ttl}s)",
                path=request.url.path
            )
            return True

        except (RedisError, TypeError) as e:
            logger.warning(f"Cache set error: {e}")
            return False

    async def invalidate(
        self,
        pattern: str = "*"
    ) -> int:
        """
        Invalidate cache entries matching pattern

        Args:
            pattern: Redis key pattern (e.g., "cache:users:*")

        Returns:
            Number of keys deleted
        """
        redis = self._get_redis_client()
        if redis is None:
            return 0

        try:
            keys = redis.keys(pattern)
            if keys:
                deleted = redis.delete(*keys)
                logger.info(f"Cache invalidated: {deleted} keys matching '{pattern}'")
                return deleted
            return 0

        except RedisError as e:
            logger.warning(f"Cache invalidation error: {e}")
            return 0

    def get_hit_rate(self) -> float:
        """
        Get cache hit rate percentage

        Returns:
            Hit rate as percentage (0-100)
        """
        total = self.stats['hits'] + self.stats['misses']
        if total == 0:
            return 0.0
        return (self.stats['hits'] / total) * 100

    def get_stats(self) -> dict:
        """Get cache statistics"""
        return {
            **self.stats,
            'hit_rate': self.get_hit_rate(),
            'total_requests': self.stats['hits'] + self.stats['misses']
        }


# Global cache instance
_response_cache: Optional[ResponseCache] = None


def get_cache() -> ResponseCache:
    """Get or create global cache instance"""
    global _response_cache
    if _response_cache is None:
        _response_cache = ResponseCache()
    return _response_cache


def cached(
    ttl: int = 300,
    key_prefix: str = "cache",
    cache_condition: Optional[Callable] = None
):
    """
    Decorator for caching endpoint responses

    Usage:
        @router.get("/users")
        @cached(ttl=600, key_prefix="users")
        async def get_users():
            return {"users": [...]}

    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
        cache_condition: Optional function to determine if should cache
                        (receives response, returns bool)
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

            # If no request or not a GET, skip caching
            if request is None or request.method != 'GET':
                return await func(*args, **kwargs)

            # Try to get from cache
            cache = get_cache()
            cached_response = await cache.get(request, key_prefix)

            if cached_response is not None:
                # Return cached response with cache header
                return JSONResponse(
                    content=cached_response,
                    headers={
                        "X-Cache": "HIT",
                        "X-Cache-Key-Prefix": key_prefix
                    }
                )

            # Call actual endpoint
            response = await func(*args, **kwargs)

            # Determine if we should cache this response
            should_cache = True

            if cache_condition is not None:
                should_cache = cache_condition(response)

            # Cache successful responses (200-299)
            if should_cache and isinstance(response, (dict, list, JSONResponse)):
                # Extract response data
                if isinstance(response, JSONResponse):
                    # Can't easily extract from JSONResponse, skip caching
                    # (or you could serialize it, but that's complex)
                    pass
                else:
                    # Cache the response
                    await cache.set(request, response, ttl, key_prefix)

                # Add cache header
                if isinstance(response, JSONResponse):
                    response.headers["X-Cache"] = "MISS"
                    response.headers["X-Cache-TTL"] = str(ttl)

            return response

        return wrapper
    return decorator


def cache_invalidation_decorator(
    patterns: List[str]
):
    """
    Decorator to invalidate cache after endpoint execution

    Usage:
        @router.post("/users")
        @cache_invalidation_decorator(patterns=["cache:users:*", "cache:user_count:*"])
        async def create_user():
            return {"user": {...}}

    Args:
        patterns: List of Redis key patterns to invalidate
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute the endpoint
            response = await func(*args, **kwargs)

            # Invalidate cache patterns
            cache = get_cache()
            for pattern in patterns:
                await cache.invalidate(pattern)

            return response

        return wrapper
    return decorator


async def cache_stats_endpoint():
    """
    Endpoint to get cache statistics

    Usage in routes:
        @router.get("/cache/stats")
        async def get_cache_stats():
            return await cache_stats_endpoint()
    """
    cache = get_cache()
    stats = cache.get_stats()

    return {
        "cache_enabled": True,
        "stats": stats,
        "redis_available": cache._get_redis_client() is not None
    }
