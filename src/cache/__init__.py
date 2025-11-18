"""
Cache Package
Redis-based caching layer for AutoTest-RL
"""
from src.cache.redis_config import (
    RedisConfig,
    init_redis,
    get_redis,
    get_async_redis,
    get_redis_config
)

from src.cache.cache_manager import (
    CacheManager,
    AsyncCacheManager
)

from src.cache.document_cache import (
    DocumentCache,
    AsyncDocumentCache
)

from src.cache.constraint_cache import (
    ConstraintCache,
    AsyncConstraintCache
)

from src.cache.test_suite_cache import (
    TestSuiteCache,
    AsyncTestSuiteCache
)

__all__ = [
    # Redis Configuration
    'RedisConfig',
    'init_redis',
    'get_redis',
    'get_async_redis',
    'get_redis_config',

    # Cache Managers
    'CacheManager',
    'AsyncCacheManager',

    # Document Cache
    'DocumentCache',
    'AsyncDocumentCache',

    # Constraint Cache
    'ConstraintCache',
    'AsyncConstraintCache',

    # Test Suite Cache
    'TestSuiteCache',
    'AsyncTestSuiteCache',
]
