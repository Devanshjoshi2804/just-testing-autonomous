"""
Constraint Cache
Caching layer for extracted API constraints
"""
from typing import Optional, Dict, Any, List
from loguru import logger

from src.cache.cache_manager import CacheManager, AsyncCacheManager


class ConstraintCache:
    """Cache for extracted API constraints"""

    def __init__(self, ttl: int = 43200):  # 12 hours default
        """
        Initialize constraint cache

        Args:
            ttl: Cache TTL in seconds (12 hours default)
        """
        self.cache = CacheManager(namespace="autotest:constraints", default_ttl=ttl)
        self.ttl = ttl

    def _make_endpoint_key(self, path: str, method: str) -> str:
        """
        Create cache key for endpoint constraints

        Args:
            path: Endpoint path
            method: HTTP method

        Returns:
            Cache key
        """
        return f"endpoint:{method}:{path}"

    def _make_parameter_key(self, path: str, method: str, parameter: str) -> str:
        """
        Create cache key for parameter constraints

        Args:
            path: Endpoint path
            method: HTTP method
            parameter: Parameter name

        Returns:
            Cache key
        """
        return f"param:{method}:{path}:{parameter}"

    def get_endpoint_constraints(
        self,
        path: str,
        method: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get all constraints for an endpoint

        Args:
            path: Endpoint path
            method: HTTP method

        Returns:
            Constraints dictionary or None
        """
        key = self._make_endpoint_key(path, method)
        result = self.cache.get(key)

        if result:
            logger.info(f"Constraint cache hit: {method} {path}")
        else:
            logger.debug(f"Constraint cache miss: {method} {path}")

        return result

    def set_endpoint_constraints(
        self,
        path: str,
        method: str,
        constraints: Dict[str, Any]
    ) -> bool:
        """
        Cache constraints for an endpoint

        Args:
            path: Endpoint path
            method: HTTP method
            constraints: Constraints dictionary

        Returns:
            True if successful
        """
        key = self._make_endpoint_key(path, method)
        success = self.cache.set(key, constraints, ttl=self.ttl)

        if success:
            logger.info(f"Cached constraints: {method} {path}")

        return success

    def get_parameter_constraints(
        self,
        path: str,
        method: str,
        parameter: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get constraints for a specific parameter

        Args:
            path: Endpoint path
            method: HTTP method
            parameter: Parameter name

        Returns:
            List of constraints or None
        """
        key = self._make_parameter_key(path, method, parameter)
        result = self.cache.get(key)

        if result:
            logger.info(f"Parameter constraint cache hit: {method} {path}/{parameter}")

        return result

    def set_parameter_constraints(
        self,
        path: str,
        method: str,
        parameter: str,
        constraints: List[Dict[str, Any]]
    ) -> bool:
        """
        Cache constraints for a specific parameter

        Args:
            path: Endpoint path
            method: HTTP method
            parameter: Parameter name
            constraints: List of constraints

        Returns:
            True if successful
        """
        key = self._make_parameter_key(path, method, parameter)
        success = self.cache.set(key, constraints, ttl=self.ttl)

        if success:
            logger.info(f"Cached parameter constraints: {method} {path}/{parameter}")

        return success

    def invalidate_endpoint(self, path: str, method: str) -> bool:
        """
        Invalidate all constraints for an endpoint

        Args:
            path: Endpoint path
            method: HTTP method

        Returns:
            True if deleted
        """
        key = self._make_endpoint_key(path, method)
        result = self.cache.delete(key)

        if result:
            logger.info(f"Invalidated constraints: {method} {path}")

        return result

    def invalidate_parameter(
        self,
        path: str,
        method: str,
        parameter: str
    ) -> bool:
        """
        Invalidate constraints for a specific parameter

        Args:
            path: Endpoint path
            method: HTTP method
            parameter: Parameter name

        Returns:
            True if deleted
        """
        key = self._make_parameter_key(path, method, parameter)
        result = self.cache.delete(key)

        if result:
            logger.info(f"Invalidated parameter constraints: {method} {path}/{parameter}")

        return result

    def invalidate_path_pattern(self, path_pattern: str) -> int:
        """
        Invalidate all endpoints matching path pattern

        Args:
            path_pattern: Path pattern (e.g., "/api/users*")

        Returns:
            Number of entries invalidated
        """
        pattern = f"*:{path_pattern}*"
        count = self.cache.invalidate_pattern(pattern)

        if count > 0:
            logger.info(f"Invalidated {count} constraints matching: {path_pattern}")

        return count

    def invalidate_all(self) -> int:
        """
        Invalidate all cached constraints

        Returns:
            Number of entries invalidated
        """
        count = self.cache.clear_namespace()
        logger.info(f"Invalidated all constraints: {count} entries")
        return count


class AsyncConstraintCache:
    """Async cache for extracted API constraints"""

    def __init__(self, ttl: int = 43200):  # 12 hours default
        """
        Initialize async constraint cache

        Args:
            ttl: Cache TTL in seconds (12 hours default)
        """
        self.cache = AsyncCacheManager(namespace="autotest:constraints", default_ttl=ttl)
        self.ttl = ttl

    def _make_endpoint_key(self, path: str, method: str) -> str:
        """Create cache key for endpoint constraints"""
        return f"endpoint:{method}:{path}"

    def _make_parameter_key(self, path: str, method: str, parameter: str) -> str:
        """Create cache key for parameter constraints"""
        return f"param:{method}:{path}:{parameter}"

    async def get_endpoint_constraints(
        self,
        path: str,
        method: str
    ) -> Optional[Dict[str, Any]]:
        """Get all constraints for an endpoint (async)"""
        key = self._make_endpoint_key(path, method)
        result = await self.cache.get(key)

        if result:
            logger.info(f"Constraint cache hit: {method} {path}")
        else:
            logger.debug(f"Constraint cache miss: {method} {path}")

        return result

    async def set_endpoint_constraints(
        self,
        path: str,
        method: str,
        constraints: Dict[str, Any]
    ) -> bool:
        """Cache constraints for an endpoint (async)"""
        key = self._make_endpoint_key(path, method)
        success = await self.cache.set(key, constraints, ttl=self.ttl)

        if success:
            logger.info(f"Cached constraints: {method} {path}")

        return success

    async def invalidate_endpoint(self, path: str, method: str) -> bool:
        """Invalidate all constraints for an endpoint (async)"""
        key = self._make_endpoint_key(path, method)
        result = await self.cache.delete(key)

        if result:
            logger.info(f"Invalidated constraints: {method} {path}")

        return result

    async def invalidate_path_pattern(self, path_pattern: str) -> int:
        """Invalidate all endpoints matching path pattern (async)"""
        pattern = f"*:{path_pattern}*"
        count = await self.cache.invalidate_pattern(pattern)

        if count > 0:
            logger.info(f"Invalidated {count} constraints matching: {path_pattern}")

        return count

    async def invalidate_all(self) -> int:
        """Invalidate all cached constraints (async)"""
        count = await self.cache.clear_namespace()
        logger.info(f"Invalidated all constraints: {count} entries")
        return count
