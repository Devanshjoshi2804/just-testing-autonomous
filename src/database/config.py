"""
Database Configuration and Session Management
Handles database connection, session creation, and async support
"""
import os
from typing import AsyncGenerator, Generator
from contextlib import contextmanager, asynccontextmanager

from sqlalchemy import create_engine, event, pool
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from src.database.models import Base

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration"""

    def __init__(
        self,
        database_url: str = None,
        async_database_url: str = None,
        echo: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        pool_recycle: int = 3600
    ):
        """
        Initialize database configuration

        Args:
            database_url: Sync database URL (e.g., sqlite:///./autotest.db, postgresql://...)
            async_database_url: Async database URL (e.g., sqlite+aiosqlite:///./autotest.db)
            echo: Echo SQL statements (for debugging)
            pool_size: Size of connection pool
            max_overflow: Max connections beyond pool_size
            pool_timeout: Timeout for getting connection from pool
            pool_recycle: Recycle connections after N seconds
        """
        # Default to SQLite if not specified
        self.database_url = database_url or os.getenv(
            'DATABASE_URL',
            'sqlite:///./autotest.db'
        )

        self.async_database_url = async_database_url or os.getenv(
            'ASYNC_DATABASE_URL',
            'sqlite+aiosqlite:///./autotest.db'
        )

        self.echo = echo
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle

        # Create engines
        self._engine = None
        self._async_engine = None
        self._session_factory = None
        self._async_session_factory = None

    @property
    def engine(self):
        """Get or create synchronous engine"""
        if self._engine is None:
            # Use NullPool for SQLite, QueuePool for others
            if 'sqlite' in self.database_url:
                poolclass = NullPool
                connect_args = {"check_same_thread": False}
            else:
                poolclass = QueuePool
                connect_args = {}

            # Build engine kwargs
            engine_kwargs = {
                'echo': self.echo,
                'poolclass': poolclass,
                'connect_args': connect_args
            }

            # Only add pool arguments for QueuePool
            if poolclass == QueuePool:
                if self.pool_size is not None:
                    engine_kwargs['pool_size'] = self.pool_size
                if self.max_overflow is not None:
                    engine_kwargs['max_overflow'] = self.max_overflow
                if self.pool_timeout is not None:
                    engine_kwargs['pool_timeout'] = self.pool_timeout
                if self.pool_recycle is not None:
                    engine_kwargs['pool_recycle'] = self.pool_recycle

            self._engine = create_engine(self.database_url, **engine_kwargs)

            # Enable foreign keys for SQLite
            if 'sqlite' in self.database_url:
                @event.listens_for(self._engine, "connect")
                def set_sqlite_pragma(dbapi_conn, connection_record):
                    cursor = dbapi_conn.cursor()
                    cursor.execute("PRAGMA foreign_keys=ON")
                    cursor.close()

            logger.info(f"Created database engine: {self.database_url}")

        return self._engine

    @property
    def async_engine(self):
        """Get or create asynchronous engine"""
        if self._async_engine is None:
            # Use NullPool for async SQLite
            if 'sqlite' in self.async_database_url:
                poolclass = NullPool
                connect_args = {"check_same_thread": False}
            else:
                poolclass = QueuePool
                connect_args = {}

            self._async_engine = create_async_engine(
                self.async_database_url,
                echo=self.echo,
                poolclass=poolclass,
                connect_args=connect_args,
                pool_size=self.pool_size if poolclass == QueuePool else None,
                max_overflow=self.max_overflow if poolclass == QueuePool else None,
                pool_timeout=self.pool_timeout if poolclass == QueuePool else None,
                pool_recycle=self.pool_recycle if poolclass == QueuePool else None
            )

            logger.info(f"Created async database engine: {self.async_database_url}")

        return self._async_engine

    @property
    def session_factory(self):
        """Get or create session factory"""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
        return self._session_factory

    @property
    def async_session_factory(self):
        """Get or create async session factory"""
        if self._async_session_factory is None:
            self._async_session_factory = async_sessionmaker(
                bind=self.async_engine,
                class_=AsyncSession,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
        return self._async_session_factory

    def create_tables(self):
        """Create all database tables"""
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created successfully")

    async def create_tables_async(self):
        """Create all database tables (async)"""
        logger.info("Creating database tables (async)...")
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")

    def drop_tables(self):
        """Drop all database tables (USE WITH CAUTION)"""
        logger.warning("Dropping all database tables...")
        Base.metadata.drop_all(bind=self.engine)
        logger.info("Database tables dropped")

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get a database session (context manager for sync code)

        Usage:
            with db_config.get_session() as session:
                session.add(obj)
                session.commit()
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get an async database session

        Usage:
            async with db_config.get_async_session() as session:
                session.add(obj)
                await session.commit()
        """
        session = self.async_session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Async database session error: {e}")
            raise
        finally:
            await session.close()

    def close(self):
        """Close database connections"""
        if self._engine:
            self._engine.dispose()
            logger.info("Database engine disposed")

    async def close_async(self):
        """Close async database connections"""
        if self._async_engine:
            await self._async_engine.dispose()
            logger.info("Async database engine disposed")


# Global database configuration instance
_db_config: DatabaseConfig = None


def get_db_config() -> DatabaseConfig:
    """Get global database configuration instance"""
    global _db_config
    if _db_config is None:
        _db_config = DatabaseConfig()
    return _db_config


def init_database(
    database_url: str = None,
    async_database_url: str = None,
    create_tables: bool = True,
    **kwargs
) -> DatabaseConfig:
    """
    Initialize database

    Args:
        database_url: Database URL
        async_database_url: Async database URL
        create_tables: Create tables on initialization
        **kwargs: Additional DatabaseConfig parameters

    Returns:
        DatabaseConfig instance
    """
    global _db_config

    _db_config = DatabaseConfig(
        database_url=database_url,
        async_database_url=async_database_url,
        **kwargs
    )

    if create_tables:
        _db_config.create_tables()

    return _db_config


# Dependency injection for FastAPI
def get_db() -> Generator[Session, None, None]:
    """
    Get database session for dependency injection

    Usage in FastAPI:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db_config = get_db_config()
    with db_config.get_session() as session:
        yield session


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get async database session for dependency injection

    Usage in FastAPI:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_async_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    db_config = get_db_config()
    async with db_config.get_async_session() as session:
        yield session
