"""
Test Suite Cache
Caching layer for generated test suites
"""
from typing import Optional, Dict, Any, List
from loguru import logger

from src.cache.cache_manager import CacheManager, AsyncCacheManager


class TestSuiteCache:
    """Cache for generated test suites"""

    def __init__(self, ttl: int = 21600):  # 6 hours default
        """
        Initialize test suite cache

        Args:
            ttl: Cache TTL in seconds (6 hours default)
        """
        self.cache = CacheManager(namespace="autotest:testsuites", default_ttl=ttl)
        self.ttl = ttl

    def _make_suite_key(
        self,
        path: str,
        method: str,
        strategy: str
    ) -> str:
        """
        Create cache key for test suite

        Args:
            path: Endpoint path
            method: HTTP method
            strategy: Test generation strategy

        Returns:
            Cache key
        """
        return f"suite:{strategy}:{method}:{path}"

    def _make_endpoint_suites_key(self, path: str, method: str) -> str:
        """
        Create cache key for all suites of an endpoint

        Args:
            path: Endpoint path
            method: HTTP method

        Returns:
            Cache key
        """
        return f"endpoint:{method}:{path}"

    def get_suite(
        self,
        path: str,
        method: str,
        strategy: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached test suite

        Args:
            path: Endpoint path
            method: HTTP method
            strategy: Test generation strategy

        Returns:
            List of test cases or None
        """
        key = self._make_suite_key(path, method, strategy)
        result = self.cache.get(key)

        if result:
            logger.info(f"Test suite cache hit: {method} {path} ({strategy})")
        else:
            logger.debug(f"Test suite cache miss: {method} {path} ({strategy})")

        return result

    def set_suite(
        self,
        path: str,
        method: str,
        strategy: str,
        test_suite: List[Dict[str, Any]]
    ) -> bool:
        """
        Cache test suite

        Args:
            path: Endpoint path
            method: HTTP method
            strategy: Test generation strategy
            test_suite: List of test cases

        Returns:
            True if successful
        """
        key = self._make_suite_key(path, method, strategy)
        success = self.cache.set(key, test_suite, ttl=self.ttl)

        if success:
            logger.info(
                f"Cached test suite: {method} {path} ({strategy}, {len(test_suite)} tests)"
            )

        return success

    def get_all_suites(
        self,
        path: str,
        method: str
    ) -> Optional[Dict[str, List[Dict[str, Any]]]]:
        """
        Get all test suites for an endpoint (all strategies)

        Args:
            path: Endpoint path
            method: HTTP method

        Returns:
            Dictionary of strategy -> test suite
        """
        key = self._make_endpoint_suites_key(path, method)
        result = self.cache.get(key)

        if result:
            logger.info(f"All suites cache hit: {method} {path}")

        return result

    def set_all_suites(
        self,
        path: str,
        method: str,
        suites: Dict[str, List[Dict[str, Any]]]
    ) -> bool:
        """
        Cache all test suites for an endpoint

        Args:
            path: Endpoint path
            method: HTTP method
            suites: Dictionary of strategy -> test suite

        Returns:
            True if successful
        """
        key = self._make_endpoint_suites_key(path, method)
        success = self.cache.set(key, suites, ttl=self.ttl)

        if success:
            total_tests = sum(len(suite) for suite in suites.values())
            logger.info(
                f"Cached all suites: {method} {path} "
                f"({len(suites)} strategies, {total_tests} tests)"
            )

        return success

    def invalidate_suite(
        self,
        path: str,
        method: str,
        strategy: str
    ) -> bool:
        """
        Invalidate specific test suite

        Args:
            path: Endpoint path
            method: HTTP method
            strategy: Test generation strategy

        Returns:
            True if deleted
        """
        key = self._make_suite_key(path, method, strategy)
        result = self.cache.delete(key)

        if result:
            logger.info(f"Invalidated test suite: {method} {path} ({strategy})")

        return result

    def invalidate_endpoint(self, path: str, method: str) -> int:
        """
        Invalidate all test suites for an endpoint

        Args:
            path: Endpoint path
            method: HTTP method

        Returns:
            Number of suites invalidated
        """
        # Invalidate all strategies for this endpoint
        pattern = f"suite:*:{method}:{path}"
        count = self.cache.invalidate_pattern(pattern)

        # Also invalidate the combined suites cache
        endpoint_key = self._make_endpoint_suites_key(path, method)
        if self.cache.delete(endpoint_key):
            count += 1

        if count > 0:
            logger.info(f"Invalidated {count} test suites: {method} {path}")

        return count

    def invalidate_strategy(self, strategy: str) -> int:
        """
        Invalidate all test suites for a specific strategy

        Args:
            strategy: Test generation strategy

        Returns:
            Number of suites invalidated
        """
        pattern = f"suite:{strategy}:*"
        count = self.cache.invalidate_pattern(pattern)

        if count > 0:
            logger.info(f"Invalidated {count} test suites for strategy: {strategy}")

        return count

    def invalidate_path_pattern(self, path_pattern: str) -> int:
        """
        Invalidate all test suites matching path pattern

        Args:
            path_pattern: Path pattern (e.g., "/api/users*")

        Returns:
            Number of suites invalidated
        """
        pattern = f"*:{path_pattern}*"
        count = self.cache.invalidate_pattern(pattern)

        if count > 0:
            logger.info(f"Invalidated {count} test suites matching: {path_pattern}")

        return count

    def invalidate_all(self) -> int:
        """
        Invalidate all cached test suites

        Returns:
            Number of suites invalidated
        """
        count = self.cache.clear_namespace()
        logger.info(f"Invalidated all test suites: {count} entries")
        return count

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics for test suites

        Returns:
            Dictionary with cache stats
        """
        # This would require scanning keys or maintaining counters
        # For now, return placeholder
        return {
            'total_suites': 0,
            'total_tests': 0,
            'strategies': []
        }


class AsyncTestSuiteCache:
    """Async cache for generated test suites"""

    def __init__(self, ttl: int = 21600):  # 6 hours default
        """
        Initialize async test suite cache

        Args:
            ttl: Cache TTL in seconds (6 hours default)
        """
        self.cache = AsyncCacheManager(namespace="autotest:testsuites", default_ttl=ttl)
        self.ttl = ttl

    def _make_suite_key(
        self,
        path: str,
        method: str,
        strategy: str
    ) -> str:
        """Create cache key for test suite"""
        return f"suite:{strategy}:{method}:{path}"

    def _make_endpoint_suites_key(self, path: str, method: str) -> str:
        """Create cache key for all suites of an endpoint"""
        return f"endpoint:{method}:{path}"

    async def get_suite(
        self,
        path: str,
        method: str,
        strategy: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached test suite (async)"""
        key = self._make_suite_key(path, method, strategy)
        result = await self.cache.get(key)

        if result:
            logger.info(f"Test suite cache hit: {method} {path} ({strategy})")
        else:
            logger.debug(f"Test suite cache miss: {method} {path} ({strategy})")

        return result

    async def set_suite(
        self,
        path: str,
        method: str,
        strategy: str,
        test_suite: List[Dict[str, Any]]
    ) -> bool:
        """Cache test suite (async)"""
        key = self._make_suite_key(path, method, strategy)
        success = await self.cache.set(key, test_suite, ttl=self.ttl)

        if success:
            logger.info(
                f"Cached test suite: {method} {path} ({strategy}, {len(test_suite)} tests)"
            )

        return success

    async def invalidate_suite(
        self,
        path: str,
        method: str,
        strategy: str
    ) -> bool:
        """Invalidate specific test suite (async)"""
        key = self._make_suite_key(path, method, strategy)
        result = await self.cache.delete(key)

        if result:
            logger.info(f"Invalidated test suite: {method} {path} ({strategy})")

        return result

    async def invalidate_endpoint(self, path: str, method: str) -> int:
        """Invalidate all test suites for an endpoint (async)"""
        # Invalidate all strategies for this endpoint
        pattern = f"suite:*:{method}:{path}"
        count = await self.cache.invalidate_pattern(pattern)

        # Also invalidate the combined suites cache
        endpoint_key = self._make_endpoint_suites_key(path, method)
        if await self.cache.delete(endpoint_key):
            count += 1

        if count > 0:
            logger.info(f"Invalidated {count} test suites: {method} {path}")

        return count

    async def invalidate_path_pattern(self, path_pattern: str) -> int:
        """Invalidate all test suites matching path pattern (async)"""
        pattern = f"*:{path_pattern}*"
        count = await self.cache.invalidate_pattern(pattern)

        if count > 0:
            logger.info(f"Invalidated {count} test suites matching: {path_pattern}")

        return count

    async def invalidate_all(self) -> int:
        """Invalidate all cached test suites (async)"""
        count = await self.cache.clear_namespace()
        logger.info(f"Invalidated all test suites: {count} entries")
        return count
