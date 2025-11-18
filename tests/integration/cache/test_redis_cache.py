"""
Integration Tests for Redis Cache Layer
Tests all caching components with mock Redis
"""
import pytest
import fakeredis
from unittest.mock import Mock, patch
from typing import Dict, Any

from src.cache.redis_config import RedisConfig, init_redis
from src.cache.cache_manager import CacheManager
from src.cache.document_cache import DocumentCache
from src.cache.constraint_cache import ConstraintCache
from src.cache.test_suite_cache import TestSuiteCache


@pytest.fixture(scope="function")
def fake_redis():
    """Create fake Redis server for testing"""
    server = fakeredis.FakeServer()
    redis_client = fakeredis.FakeRedis(server=server, decode_responses=True)
    yield redis_client
    redis_client.flushall()


@pytest.fixture(scope="function")
def redis_config(fake_redis):
    """Create Redis config with fake Redis"""
    config = RedisConfig()
    config._client = fake_redis
    return config


@pytest.fixture(scope="function")
def patched_get_redis(fake_redis):
    """Patch get_redis to return fake Redis"""
    with patch('src.cache.cache_manager.get_redis', return_value=fake_redis):
        with patch('src.cache.redis_config.get_redis', return_value=fake_redis):
            yield fake_redis


# =============================================================================
# Cache Manager Tests
# =============================================================================


def test_cache_manager_get_set(patched_get_redis):
    """Test basic get/set operations"""
    cache = CacheManager(namespace="test", default_ttl=60)

    # Set value
    success = cache.set("key1", {"data": "value1"})
    assert success is True

    # Get value
    result = cache.get("key1")
    assert result == {"data": "value1"}


def test_cache_manager_get_nonexistent(patched_get_redis):
    """Test getting nonexistent key returns None"""
    cache = CacheManager(namespace="test")

    result = cache.get("nonexistent")
    assert result is None


def test_cache_manager_delete(patched_get_redis):
    """Test deleting cached values"""
    cache = CacheManager(namespace="test")

    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"

    # Delete
    deleted = cache.delete("key1")
    assert deleted is True

    # Verify deleted
    assert cache.get("key1") is None


def test_cache_manager_exists(patched_get_redis):
    """Test checking if key exists"""
    cache = CacheManager(namespace="test")

    assert cache.exists("key1") is False

    cache.set("key1", "value1")
    assert cache.exists("key1") is True

    cache.delete("key1")
    assert cache.exists("key1") is False


def test_cache_manager_expire(patched_get_redis):
    """Test setting expiration on keys"""
    cache = CacheManager(namespace="test")

    cache.set("key1", "value1", ttl=3600)

    # Set shorter expiration
    success = cache.expire("key1", 60)
    assert success is True

    # Check TTL
    ttl = cache.get_ttl("key1")
    assert ttl is not None
    assert ttl <= 60


def test_cache_manager_get_many(patched_get_redis):
    """Test getting multiple values"""
    cache = CacheManager(namespace="test")

    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")

    result = cache.get_many(["key1", "key2", "key3", "key4"])

    assert result["key1"] == "value1"
    assert result["key2"] == "value2"
    assert result["key3"] == "value3"
    assert result["key4"] is None


def test_cache_manager_set_many(patched_get_redis):
    """Test setting multiple values"""
    cache = CacheManager(namespace="test")

    mapping = {
        "key1": "value1",
        "key2": "value2",
        "key3": "value3"
    }

    success = cache.set_many(mapping)
    assert success is True

    # Verify all set
    assert cache.get("key1") == "value1"
    assert cache.get("key2") == "value2"
    assert cache.get("key3") == "value3"


def test_cache_manager_increment(patched_get_redis):
    """Test incrementing integer values"""
    cache = CacheManager(namespace="test")

    # Increment non-existent key
    value = cache.increment("counter")
    assert value == 1

    # Increment existing key
    value = cache.increment("counter", amount=5)
    assert value == 6


def test_cache_manager_decrement(patched_get_redis):
    """Test decrementing integer values"""
    cache = CacheManager(namespace="test")

    cache.increment("counter", amount=10)

    value = cache.decrement("counter", amount=3)
    assert value == 7


def test_cache_manager_invalidate_pattern(patched_get_redis):
    """Test invalidating keys by pattern"""
    cache = CacheManager(namespace="test")

    # Set multiple keys
    cache.set("user:1", "data1")
    cache.set("user:2", "data2")
    cache.set("user:3", "data3")
    cache.set("post:1", "data4")

    # Invalidate user keys
    count = cache.invalidate_pattern("user:*")
    assert count == 3

    # Verify users deleted, post remains
    assert cache.get("user:1") is None
    assert cache.get("user:2") is None
    assert cache.get("user:3") is None
    assert cache.get("post:1") == "data4"


def test_cache_manager_clear_namespace(patched_get_redis):
    """Test clearing entire namespace"""
    cache = CacheManager(namespace="test")

    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")

    count = cache.clear_namespace()
    assert count == 3

    assert cache.get("key1") is None
    assert cache.get("key2") is None
    assert cache.get("key3") is None


def test_cache_manager_hash_key(patched_get_redis):
    """Test consistent hash key generation"""
    # Same inputs should generate same hash
    hash1 = CacheManager.hash_key("arg1", "arg2", kwarg1="value1")
    hash2 = CacheManager.hash_key("arg1", "arg2", kwarg1="value1")
    assert hash1 == hash2

    # Different inputs should generate different hash
    hash3 = CacheManager.hash_key("arg1", "arg3", kwarg1="value1")
    assert hash1 != hash3


@pytest.mark.skip(reason="Pickle serialization requires binary Redis connection")
def test_cache_manager_with_pickle(patched_get_redis):
    """Test caching complex objects with pickle"""
    cache = CacheManager(namespace="test")

    # Create complex object
    complex_obj = {
        "nested": {
            "data": [1, 2, 3],
            "set": {4, 5, 6}
        },
        "tuple": (7, 8, 9)
    }

    # Cache with pickle
    cache.set("complex", complex_obj, use_pickle=True)

    # Retrieve with pickle
    result = cache.get("complex", use_pickle=True)
    assert result["nested"]["data"] == [1, 2, 3]
    assert result["tuple"] == (7, 8, 9)


# =============================================================================
# Document Cache Tests
# =============================================================================


def test_document_cache_get_set_by_hash(patched_get_redis):
    """Test caching documents by hash"""
    doc_cache = DocumentCache(ttl=3600)

    doc_data = {
        "endpoints": [
            {"path": "/api/users", "method": "GET"}
        ],
        "version": "1.0"
    }

    doc_hash = "abc123def456"

    # Set document
    success = doc_cache.set(doc_hash, doc_data)
    assert success is True

    # Get document
    result = doc_cache.get_by_hash(doc_hash)
    assert result == doc_data


def test_document_cache_get_set_by_path(patched_get_redis):
    """Test caching documents by file path"""
    doc_cache = DocumentCache()

    doc_data = {
        "endpoints": [
            {"path": "/api/posts", "method": "POST"}
        ]
    }

    doc_hash = "xyz789"
    file_path = "/path/to/api-spec.yaml"

    # Set with path
    doc_cache.set(doc_hash, doc_data, file_path=file_path)

    # Get by path
    result = doc_cache.get_by_path(file_path)
    assert result == doc_data

    # Also get by hash
    result = doc_cache.get_by_hash(doc_hash)
    assert result == doc_data


def test_document_cache_invalidate_by_hash(patched_get_redis):
    """Test invalidating document by hash"""
    doc_cache = DocumentCache()

    doc_hash = "abc123"
    doc_cache.set(doc_hash, {"data": "test"})

    # Invalidate
    deleted = doc_cache.invalidate_by_hash(doc_hash)
    assert deleted is True

    # Verify deleted
    assert doc_cache.get_by_hash(doc_hash) is None


def test_document_cache_invalidate_by_path(patched_get_redis):
    """Test invalidating document by path"""
    doc_cache = DocumentCache()

    file_path = "/path/to/spec.json"
    doc_cache.set("hash123", {"data": "test"}, file_path=file_path)

    # Invalidate by path
    deleted = doc_cache.invalidate_by_path(file_path)
    assert deleted is True

    # Verify deleted
    assert doc_cache.get_by_path(file_path) is None


def test_document_cache_invalidate_all(patched_get_redis):
    """Test invalidating all documents"""
    doc_cache = DocumentCache()

    doc_cache.set("hash1", {"data": "1"})
    doc_cache.set("hash2", {"data": "2"})
    doc_cache.set("hash3", {"data": "3"}, file_path="/path/3")

    # Invalidate all
    count = doc_cache.invalidate_all()
    assert count >= 3  # At least 3 (hash1, hash2, hash3), possibly 4 (path3)


# =============================================================================
# Constraint Cache Tests
# =============================================================================


def test_constraint_cache_endpoint_constraints(patched_get_redis):
    """Test caching endpoint constraints"""
    constraint_cache = ConstraintCache()

    constraints = {
        "page": {
            "type": "integer",
            "min_value": 1,
            "max_value": 100
        },
        "limit": {
            "type": "integer",
            "min_value": 1,
            "max_value": 50
        }
    }

    # Set constraints
    success = constraint_cache.set_endpoint_constraints(
        "/api/users",
        "GET",
        constraints
    )
    assert success is True

    # Get constraints
    result = constraint_cache.get_endpoint_constraints("/api/users", "GET")
    assert result == constraints


def test_constraint_cache_parameter_constraints(patched_get_redis):
    """Test caching parameter-specific constraints"""
    constraint_cache = ConstraintCache()

    constraints = [
        {"type": "min_value", "value": 18},
        {"type": "max_value", "value": 120}
    ]

    # Set parameter constraints
    success = constraint_cache.set_parameter_constraints(
        "/api/users",
        "POST",
        "age",
        constraints
    )
    assert success is True

    # Get parameter constraints
    result = constraint_cache.get_parameter_constraints(
        "/api/users",
        "POST",
        "age"
    )
    assert result == constraints


def test_constraint_cache_invalidate_endpoint(patched_get_redis):
    """Test invalidating endpoint constraints"""
    constraint_cache = ConstraintCache()

    constraint_cache.set_endpoint_constraints(
        "/api/users",
        "GET",
        {"data": "test"}
    )

    # Invalidate
    deleted = constraint_cache.invalidate_endpoint("/api/users", "GET")
    assert deleted is True

    # Verify deleted
    assert constraint_cache.get_endpoint_constraints("/api/users", "GET") is None


def test_constraint_cache_invalidate_path_pattern(patched_get_redis):
    """Test invalidating constraints by path pattern"""
    constraint_cache = ConstraintCache()

    # Set multiple endpoint constraints
    constraint_cache.set_endpoint_constraints("/api/users", "GET", {"data": "1"})
    constraint_cache.set_endpoint_constraints("/api/users/123", "GET", {"data": "2"})
    constraint_cache.set_endpoint_constraints("/api/posts", "GET", {"data": "3"})

    # Invalidate /api/users* pattern
    count = constraint_cache.invalidate_path_pattern("/api/users")
    assert count >= 2  # At least users and users/123

    # Verify users deleted, posts remains
    assert constraint_cache.get_endpoint_constraints("/api/users", "GET") is None
    assert constraint_cache.get_endpoint_constraints("/api/posts", "GET") == {"data": "3"}


def test_constraint_cache_invalidate_all(patched_get_redis):
    """Test invalidating all constraints"""
    constraint_cache = ConstraintCache()

    constraint_cache.set_endpoint_constraints("/api/users", "GET", {"data": "1"})
    constraint_cache.set_endpoint_constraints("/api/posts", "GET", {"data": "2"})

    # Invalidate all
    count = constraint_cache.invalidate_all()
    assert count >= 2


# =============================================================================
# Test Suite Cache Tests
# =============================================================================


def test_test_suite_cache_get_set_suite(patched_get_redis):
    """Test caching test suites"""
    suite_cache = TestSuiteCache()

    test_suite = [
        {"test_name": "Test 1", "expected": 200},
        {"test_name": "Test 2", "expected": 404},
        {"test_name": "Test 3", "expected": 500}
    ]

    # Set suite
    success = suite_cache.set_suite(
        "/api/users",
        "GET",
        "boundary",
        test_suite
    )
    assert success is True

    # Get suite
    result = suite_cache.get_suite("/api/users", "GET", "boundary")
    assert result == test_suite
    assert len(result) == 3


def test_test_suite_cache_multiple_strategies(patched_get_redis):
    """Test caching multiple strategies for same endpoint"""
    suite_cache = TestSuiteCache()

    boundary_suite = [{"test": "boundary1"}]
    mutation_suite = [{"test": "mutation1"}, {"test": "mutation2"}]

    # Set different strategies
    suite_cache.set_suite("/api/users", "POST", "boundary", boundary_suite)
    suite_cache.set_suite("/api/users", "POST", "mutation", mutation_suite)

    # Get different strategies
    assert len(suite_cache.get_suite("/api/users", "POST", "boundary")) == 1
    assert len(suite_cache.get_suite("/api/users", "POST", "mutation")) == 2


def test_test_suite_cache_all_suites(patched_get_redis):
    """Test caching all suites for an endpoint"""
    suite_cache = TestSuiteCache()

    all_suites = {
        "boundary": [{"test": "b1"}, {"test": "b2"}],
        "mutation": [{"test": "m1"}],
        "combinatorial": [{"test": "c1"}, {"test": "c2"}, {"test": "c3"}]
    }

    # Set all suites
    success = suite_cache.set_all_suites("/api/users", "GET", all_suites)
    assert success is True

    # Get all suites
    result = suite_cache.get_all_suites("/api/users", "GET")
    assert result == all_suites
    assert len(result["boundary"]) == 2
    assert len(result["mutation"]) == 1
    assert len(result["combinatorial"]) == 3


def test_test_suite_cache_invalidate_suite(patched_get_redis):
    """Test invalidating specific test suite"""
    suite_cache = TestSuiteCache()

    suite_cache.set_suite("/api/users", "GET", "boundary", [{"test": "1"}])
    suite_cache.set_suite("/api/users", "GET", "mutation", [{"test": "2"}])

    # Invalidate boundary only
    deleted = suite_cache.invalidate_suite("/api/users", "GET", "boundary")
    assert deleted is True

    # Verify boundary deleted, mutation remains
    assert suite_cache.get_suite("/api/users", "GET", "boundary") is None
    assert suite_cache.get_suite("/api/users", "GET", "mutation") is not None


def test_test_suite_cache_invalidate_endpoint(patched_get_redis):
    """Test invalidating all suites for an endpoint"""
    suite_cache = TestSuiteCache()

    suite_cache.set_suite("/api/users", "GET", "boundary", [{"test": "1"}])
    suite_cache.set_suite("/api/users", "GET", "mutation", [{"test": "2"}])
    suite_cache.set_suite("/api/users", "GET", "combinatorial", [{"test": "3"}])

    # Invalidate all suites for endpoint
    count = suite_cache.invalidate_endpoint("/api/users", "GET")
    assert count >= 3

    # Verify all deleted
    assert suite_cache.get_suite("/api/users", "GET", "boundary") is None
    assert suite_cache.get_suite("/api/users", "GET", "mutation") is None
    assert suite_cache.get_suite("/api/users", "GET", "combinatorial") is None


def test_test_suite_cache_invalidate_strategy(patched_get_redis):
    """Test invalidating all suites for a strategy"""
    suite_cache = TestSuiteCache()

    suite_cache.set_suite("/api/users", "GET", "boundary", [{"test": "1"}])
    suite_cache.set_suite("/api/posts", "GET", "boundary", [{"test": "2"}])
    suite_cache.set_suite("/api/users", "GET", "mutation", [{"test": "3"}])

    # Invalidate all boundary suites
    count = suite_cache.invalidate_strategy("boundary")
    assert count >= 2

    # Verify boundary deleted, mutation remains
    assert suite_cache.get_suite("/api/users", "GET", "boundary") is None
    assert suite_cache.get_suite("/api/posts", "GET", "boundary") is None
    assert suite_cache.get_suite("/api/users", "GET", "mutation") is not None


def test_test_suite_cache_invalidate_path_pattern(patched_get_redis):
    """Test invalidating suites by path pattern"""
    suite_cache = TestSuiteCache()

    suite_cache.set_suite("/api/users", "GET", "boundary", [{"test": "1"}])
    suite_cache.set_suite("/api/users/123", "GET", "boundary", [{"test": "2"}])
    suite_cache.set_suite("/api/posts", "GET", "boundary", [{"test": "3"}])

    # Invalidate /api/users* pattern
    count = suite_cache.invalidate_path_pattern("/api/users")
    assert count >= 2

    # Verify users deleted, posts remains
    assert suite_cache.get_suite("/api/users", "GET", "boundary") is None
    assert suite_cache.get_suite("/api/posts", "GET", "boundary") is not None


def test_test_suite_cache_invalidate_all(patched_get_redis):
    """Test invalidating all test suites"""
    suite_cache = TestSuiteCache()

    suite_cache.set_suite("/api/users", "GET", "boundary", [{"test": "1"}])
    suite_cache.set_suite("/api/posts", "POST", "mutation", [{"test": "2"}])

    # Invalidate all
    count = suite_cache.invalidate_all()
    assert count >= 2
