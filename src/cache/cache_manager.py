"""
Cache Manager
High-level caching interface with TTL, namespacing, and invalidation
"""
import json
import hashlib
from typing import Optional, Any, Union, List
from datetime import timedelta
from loguru import logger
import pickle

from src.cache.redis_config import get_redis, get_async_redis


class CacheManager:
    """Synchronous cache manager with namespacing and TTL support"""

    def __init__(self, namespace: str = "autotest", default_ttl: int = 3600):
        """
        Initialize cache manager

        Args:
            namespace: Namespace prefix for all keys
            default_ttl: Default TTL in seconds (1 hour)
        """
        self.namespace = namespace
        self.default_ttl = default_ttl
        self.redis = get_redis()

    def _make_key(self, key: str) -> str:
        """Create namespaced key"""
        return f"{self.namespace}:{key}"

    def _serialize(self, value: Any, use_pickle: bool = False) -> Union[str, bytes]:
        """
        Serialize value for storage

        Args:
            value: Value to serialize
            use_pickle: Use pickle instead of JSON (for complex objects)

        Returns:
            Serialized value
        """
        if use_pickle:
            return pickle.dumps(value)
        else:
            return json.dumps(value, default=str)

    def _deserialize(self, value: Union[str, bytes], use_pickle: bool = False) -> Any:
        """
        Deserialize value from storage

        Args:
            value: Value to deserialize
            use_pickle: Use pickle instead of JSON

        Returns:
            Deserialized value
        """
        if value is None:
            return None

        if use_pickle:
            return pickle.loads(value)
        else:
            return json.loads(value)

    def get(self, key: str, use_pickle: bool = False) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key
            use_pickle: Use pickle deserialization

        Returns:
            Cached value or None if not found
        """
        try:
            full_key = self._make_key(key)
            value = self.redis.get(full_key)

            if value is None:
                logger.debug(f"Cache miss: {full_key}")
                return None

            logger.debug(f"Cache hit: {full_key}")
            return self._deserialize(value, use_pickle=use_pickle)

        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        use_pickle: bool = False
    ) -> bool:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (uses default if None)
            use_pickle: Use pickle serialization

        Returns:
            True if successful, False otherwise
        """
        try:
            full_key = self._make_key(key)
            serialized = self._serialize(value, use_pickle=use_pickle)
            ttl = ttl or self.default_ttl

            self.redis.setex(full_key, ttl, serialized)
            logger.debug(f"Cache set: {full_key} (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete value from cache

        Args:
            key: Cache key

        Returns:
            True if deleted, False otherwise
        """
        try:
            full_key = self._make_key(key)
            result = self.redis.delete(full_key)
            logger.debug(f"Cache delete: {full_key}")
            return result > 0

        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache

        Args:
            key: Cache key

        Returns:
            True if exists, False otherwise
        """
        try:
            full_key = self._make_key(key)
            return self.redis.exists(full_key) > 0

        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False

    def expire(self, key: str, ttl: int) -> bool:
        """
        Set expiration on existing key

        Args:
            key: Cache key
            ttl: TTL in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            full_key = self._make_key(key)
            return self.redis.expire(full_key, ttl)

        except Exception as e:
            logger.error(f"Cache expire error for key {key}: {e}")
            return False

    def get_ttl(self, key: str) -> Optional[int]:
        """
        Get remaining TTL for key

        Args:
            key: Cache key

        Returns:
            TTL in seconds or None if key doesn't exist
        """
        try:
            full_key = self._make_key(key)
            ttl = self.redis.ttl(full_key)
            return ttl if ttl > 0 else None

        except Exception as e:
            logger.error(f"Cache TTL error for key {key}: {e}")
            return None

    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching pattern

        Args:
            pattern: Key pattern (e.g., "documents:*")

        Returns:
            Number of keys deleted
        """
        try:
            full_pattern = self._make_key(pattern)
            keys = self.redis.keys(full_pattern)

            if not keys:
                return 0

            deleted = self.redis.delete(*keys)
            logger.info(f"Invalidated {deleted} keys matching pattern: {full_pattern}")
            return deleted

        except Exception as e:
            logger.error(f"Cache invalidate pattern error for {pattern}: {e}")
            return 0

    def clear_namespace(self) -> int:
        """
        Clear all keys in namespace

        Returns:
            Number of keys deleted
        """
        return self.invalidate_pattern("*")

    def get_many(self, keys: List[str], use_pickle: bool = False) -> dict:
        """
        Get multiple values from cache

        Args:
            keys: List of cache keys
            use_pickle: Use pickle deserialization

        Returns:
            Dictionary of key -> value (None for missing keys)
        """
        try:
            full_keys = [self._make_key(k) for k in keys]
            values = self.redis.mget(full_keys)

            result = {}
            for key, value in zip(keys, values):
                result[key] = self._deserialize(value, use_pickle=use_pickle) if value else None

            return result

        except Exception as e:
            logger.error(f"Cache get_many error: {e}")
            return {k: None for k in keys}

    def set_many(
        self,
        mapping: dict,
        ttl: Optional[int] = None,
        use_pickle: bool = False
    ) -> bool:
        """
        Set multiple values in cache

        Args:
            mapping: Dictionary of key -> value
            ttl: TTL in seconds (uses default if None)
            use_pickle: Use pickle serialization

        Returns:
            True if all successful, False otherwise
        """
        try:
            pipeline = self.redis.pipeline()
            ttl = ttl or self.default_ttl

            for key, value in mapping.items():
                full_key = self._make_key(key)
                serialized = self._serialize(value, use_pickle=use_pickle)
                pipeline.setex(full_key, ttl, serialized)

            pipeline.execute()
            logger.debug(f"Cache set_many: {len(mapping)} keys")
            return True

        except Exception as e:
            logger.error(f"Cache set_many error: {e}")
            return False

    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment integer value

        Args:
            key: Cache key
            amount: Amount to increment

        Returns:
            New value or None on error
        """
        try:
            full_key = self._make_key(key)
            return self.redis.incrby(full_key, amount)

        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return None

    def decrement(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Decrement integer value

        Args:
            key: Cache key
            amount: Amount to decrement

        Returns:
            New value or None on error
        """
        try:
            full_key = self._make_key(key)
            return self.redis.decrby(full_key, amount)

        except Exception as e:
            logger.error(f"Cache decrement error for key {key}: {e}")
            return None

    @staticmethod
    def hash_key(*args, **kwargs) -> str:
        """
        Generate consistent hash key from arguments

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            SHA256 hash string
        """
        # Create stable string representation
        data = json.dumps({
            'args': args,
            'kwargs': sorted(kwargs.items())
        }, sort_keys=True, default=str)

        return hashlib.sha256(data.encode()).hexdigest()


class AsyncCacheManager:
    """Asynchronous cache manager with namespacing and TTL support"""

    def __init__(self, namespace: str = "autotest", default_ttl: int = 3600):
        """
        Initialize async cache manager

        Args:
            namespace: Namespace prefix for all keys
            default_ttl: Default TTL in seconds (1 hour)
        """
        self.namespace = namespace
        self.default_ttl = default_ttl
        self.redis = get_async_redis()

    def _make_key(self, key: str) -> str:
        """Create namespaced key"""
        return f"{self.namespace}:{key}"

    def _serialize(self, value: Any, use_pickle: bool = False) -> Union[str, bytes]:
        """Serialize value for storage"""
        if use_pickle:
            return pickle.dumps(value)
        else:
            return json.dumps(value, default=str)

    def _deserialize(self, value: Union[str, bytes], use_pickle: bool = False) -> Any:
        """Deserialize value from storage"""
        if value is None:
            return None

        if use_pickle:
            return pickle.loads(value)
        else:
            return json.loads(value)

    async def get(self, key: str, use_pickle: bool = False) -> Optional[Any]:
        """Get value from cache (async)"""
        try:
            full_key = self._make_key(key)
            value = await self.redis.get(full_key)

            if value is None:
                logger.debug(f"Cache miss: {full_key}")
                return None

            logger.debug(f"Cache hit: {full_key}")
            return self._deserialize(value, use_pickle=use_pickle)

        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        use_pickle: bool = False
    ) -> bool:
        """Set value in cache (async)"""
        try:
            full_key = self._make_key(key)
            serialized = self._serialize(value, use_pickle=use_pickle)
            ttl = ttl or self.default_ttl

            await self.redis.setex(full_key, ttl, serialized)
            logger.debug(f"Cache set: {full_key} (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache (async)"""
        try:
            full_key = self._make_key(key)
            result = await self.redis.delete(full_key)
            logger.debug(f"Cache delete: {full_key}")
            return result > 0

        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists (async)"""
        try:
            full_key = self._make_key(key)
            return await self.redis.exists(full_key) > 0

        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern (async)"""
        try:
            full_pattern = self._make_key(pattern)
            keys = []

            # Scan for keys matching pattern
            cursor = 0
            while True:
                cursor, batch = await self.redis.scan(cursor, match=full_pattern, count=100)
                keys.extend(batch)
                if cursor == 0:
                    break

            if not keys:
                return 0

            deleted = await self.redis.delete(*keys)
            logger.info(f"Invalidated {deleted} keys matching pattern: {full_pattern}")
            return deleted

        except Exception as e:
            logger.error(f"Cache invalidate pattern error for {pattern}: {e}")
            return 0

    async def clear_namespace(self) -> int:
        """Clear all keys in namespace (async)"""
        return await self.invalidate_pattern("*")

    @staticmethod
    def hash_key(*args, **kwargs) -> str:
        """Generate consistent hash key from arguments"""
        return CacheManager.hash_key(*args, **kwargs)
