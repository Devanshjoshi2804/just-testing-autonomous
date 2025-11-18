"""
Redis Configuration
Connection pooling and client management for Redis caching
"""
import redis
from redis.asyncio import Redis as AsyncRedis
from typing import Optional
from loguru import logger
import json


class RedisConfig:
    """Redis connection configuration and client management"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_connections: int = 50,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
        decode_responses: bool = True
    ):
        """
        Initialize Redis configuration

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password (optional)
            max_connections: Maximum connections in pool
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Socket connect timeout in seconds
            decode_responses: Whether to decode responses to strings
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.decode_responses = decode_responses

        # Connection pools
        self._pool = None
        self._async_pool = None

        # Clients
        self._client = None
        self._async_client = None

    @property
    def pool(self) -> redis.ConnectionPool:
        """Get or create synchronous connection pool"""
        if self._pool is None:
            self._pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                max_connections=self.max_connections,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
                decode_responses=self.decode_responses
            )
            logger.info(f"Created Redis connection pool: {self.host}:{self.port}/{self.db}")

        return self._pool

    @property
    def client(self) -> redis.Redis:
        """Get or create synchronous Redis client"""
        if self._client is None:
            self._client = redis.Redis(connection_pool=self.pool)
            logger.info(f"Created Redis client: {self.host}:{self.port}/{self.db}")

        return self._client

    @property
    def async_client(self) -> AsyncRedis:
        """Get or create asynchronous Redis client"""
        if self._async_client is None:
            self._async_client = AsyncRedis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                max_connections=self.max_connections,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
                decode_responses=self.decode_responses
            )
            logger.info(f"Created async Redis client: {self.host}:{self.port}/{self.db}")

        return self._async_client

    def ping(self) -> bool:
        """Test Redis connection"""
        try:
            return self.client.ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False

    async def ping_async(self) -> bool:
        """Test async Redis connection"""
        try:
            return await self.async_client.ping()
        except Exception as e:
            logger.error(f"Async Redis ping failed: {e}")
            return False

    def close(self):
        """Close all connections"""
        if self._client:
            self._client.close()
            self._client = None

        if self._pool:
            self._pool.disconnect()
            self._pool = None

        logger.info("Closed Redis connections")

    async def close_async(self):
        """Close async connections"""
        if self._async_client:
            await self._async_client.close()
            self._async_client = None

        logger.info("Closed async Redis connections")

    def get_info(self) -> dict:
        """Get Redis server info"""
        try:
            return self.client.info()
        except Exception as e:
            logger.error(f"Failed to get Redis info: {e}")
            return {}


# Global Redis configuration instance
_redis_config: Optional[RedisConfig] = None


def init_redis(
    host: str = "localhost",
    port: int = 6379,
    db: int = 0,
    password: Optional[str] = None,
    **kwargs
) -> RedisConfig:
    """
    Initialize global Redis configuration

    Args:
        host: Redis host
        port: Redis port
        db: Redis database number
        password: Redis password
        **kwargs: Additional RedisConfig parameters

    Returns:
        RedisConfig instance
    """
    global _redis_config
    _redis_config = RedisConfig(
        host=host,
        port=port,
        db=db,
        password=password,
        **kwargs
    )
    logger.info(f"Initialized global Redis config: {host}:{port}/{db}")
    return _redis_config


def get_redis() -> redis.Redis:
    """
    Get global Redis client

    Returns:
        Redis client instance

    Raises:
        RuntimeError: If Redis not initialized
    """
    if _redis_config is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return _redis_config.client


def get_async_redis() -> AsyncRedis:
    """
    Get global async Redis client

    Returns:
        Async Redis client instance

    Raises:
        RuntimeError: If Redis not initialized
    """
    if _redis_config is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return _redis_config.async_client


def get_redis_config() -> RedisConfig:
    """
    Get global Redis configuration

    Returns:
        RedisConfig instance

    Raises:
        RuntimeError: If Redis not initialized
    """
    if _redis_config is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return _redis_config
