"""
Redis-based Storage Layer
Production-ready persistence for documents and test sessions
"""
import json
import redis
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger

from src.config import settings


class RedisStorage:
    """Base Redis storage with common operations"""

    def __init__(self, prefix: str = "autotest"):
        """
        Initialize Redis storage

        Args:
            prefix: Key prefix for namespacing
        """
        self.prefix = prefix
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
        )

        # Test connection
        try:
            self.redis_client.ping()
            logger.info(f"✅ Connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        except redis.ConnectionError as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            raise

    def _make_key(self, key: str) -> str:
        """Create prefixed key"""
        return f"{self.prefix}:{key}"

    def set(self, key: str, value: Any, expire: int = None) -> bool:
        """
        Set a value in Redis

        Args:
            key: Key name
            value: Value (will be JSON serialized)
            expire: Optional expiration in seconds

        Returns:
            bool: Success status
        """
        try:
            redis_key = self._make_key(key)
            serialized = json.dumps(value, default=str)

            if expire:
                self.redis_client.setex(redis_key, expire, serialized)
            else:
                self.redis_client.set(redis_key, serialized)

            return True
        except Exception as e:
            logger.error(f"Error setting Redis key {key}: {e}")
            return False

    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from Redis

        Args:
            key: Key name

        Returns:
            Deserialized value or None
        """
        try:
            redis_key = self._make_key(key)
            value = self.redis_client.get(redis_key)

            if value is None:
                return None

            return json.loads(value)
        except Exception as e:
            logger.error(f"Error getting Redis key {key}: {e}")
            return None

    def delete(self, key: str) -> bool:
        """
        Delete a key from Redis

        Args:
            key: Key name

        Returns:
            bool: Success status
        """
        try:
            redis_key = self._make_key(key)
            self.redis_client.delete(redis_key)
            return True
        except Exception as e:
            logger.error(f"Error deleting Redis key {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists"""
        redis_key = self._make_key(key)
        return bool(self.redis_client.exists(redis_key))

    def keys(self, pattern: str = "*") -> List[str]:
        """
        Get all keys matching pattern

        Args:
            pattern: Key pattern (e.g., "doc:*")

        Returns:
            List of keys (without prefix)
        """
        redis_pattern = self._make_key(pattern)
        keys = self.redis_client.keys(redis_pattern)
        prefix_len = len(self.prefix) + 1
        return [key[prefix_len:] for key in keys]

    def increment(self, key: str, amount: int = 1) -> int:
        """Increment a counter"""
        redis_key = self._make_key(key)
        return self.redis_client.incrby(redis_key, amount)

    def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on existing key"""
        redis_key = self._make_key(key)
        return bool(self.redis_client.expire(redis_key, seconds))


class DocumentStorage(RedisStorage):
    """Storage for API documentation metadata"""

    def __init__(self):
        super().__init__(prefix="autotest:doc")

    def save_document(self, document_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Save document metadata

        Args:
            document_id: Unique document ID
            metadata: Document metadata

        Returns:
            bool: Success status
        """
        metadata["updated_at"] = datetime.now().isoformat()

        # Store document metadata
        success = self.set(document_id, metadata)

        if success:
            # Add to document index
            self.redis_client.sadd(self._make_key("index"), document_id)
            logger.info(f"✅ Saved document metadata: {document_id}")

        return success

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get document metadata

        Args:
            document_id: Document ID

        Returns:
            Document metadata or None
        """
        return self.get(document_id)

    def list_documents(self) -> List[Dict[str, Any]]:
        """
        List all documents

        Returns:
            List of document metadata
        """
        # Get all document IDs from index
        index_key = self._make_key("index")
        document_ids = self.redis_client.smembers(index_key)

        documents = []
        for doc_id in document_ids:
            metadata = self.get_document(doc_id)
            if metadata:
                documents.append(metadata)

        # Sort by upload time (newest first)
        documents.sort(
            key=lambda x: x.get("uploaded_at", ""), reverse=True
        )

        return documents

    def delete_document(self, document_id: str) -> bool:
        """
        Delete document metadata

        Args:
            document_id: Document ID

        Returns:
            bool: Success status
        """
        # Remove from index
        index_key = self._make_key("index")
        self.redis_client.srem(index_key, document_id)

        # Delete metadata
        success = self.delete(document_id)

        if success:
            logger.info(f"✅ Deleted document: {document_id}")

        return success

    def document_exists(self, document_id: str) -> bool:
        """Check if document exists"""
        return self.exists(document_id)

    def get_document_count(self) -> int:
        """Get total document count"""
        index_key = self._make_key("index")
        return self.redis_client.scard(index_key)


class TestSessionStorage(RedisStorage):
    """Storage for test session data"""

    def __init__(self):
        super().__init__(prefix="autotest:session")

    def save_session(
        self,
        session_id: str,
        metadata: Dict[str, Any],
        expire_hours: int = 24
    ) -> bool:
        """
        Save test session metadata

        Args:
            session_id: Unique session ID
            metadata: Session metadata
            expire_hours: Auto-expire after N hours

        Returns:
            bool: Success status
        """
        metadata["updated_at"] = datetime.now().isoformat()

        # Store session metadata with expiration
        expire_seconds = expire_hours * 3600
        success = self.set(session_id, metadata, expire=expire_seconds)

        if success:
            # Add to session index
            self.redis_client.sadd(self._make_key("index"), session_id)
            # Set expiration on index entry too
            self.expire("index", expire_seconds)
            logger.info(f"✅ Saved test session: {session_id}")

        return success

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get test session metadata

        Args:
            session_id: Session ID

        Returns:
            Session metadata or None
        """
        return self.get(session_id)

    def update_session(
        self,
        session_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update test session metadata

        Args:
            session_id: Session ID
            updates: Fields to update

        Returns:
            bool: Success status
        """
        # Get existing session
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Session not found: {session_id}")
            return False

        # Merge updates
        session.update(updates)
        session["updated_at"] = datetime.now().isoformat()

        # Save back
        return self.set(session_id, session)

    def list_sessions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List all test sessions

        Args:
            limit: Max number of sessions to return

        Returns:
            List of session metadata
        """
        # Get all session IDs from index
        index_key = self._make_key("index")
        session_ids = self.redis_client.smembers(index_key)

        sessions = []
        for session_id in session_ids:
            metadata = self.get_session(session_id)
            if metadata:
                sessions.append(metadata)

        # Sort by start time (newest first)
        sessions.sort(
            key=lambda x: x.get("started_at", ""), reverse=True
        )

        return sessions[:limit]

    def delete_session(self, session_id: str) -> bool:
        """
        Delete test session

        Args:
            session_id: Session ID

        Returns:
            bool: Success status
        """
        # Remove from index
        index_key = self._make_key("index")
        self.redis_client.srem(index_key, session_id)

        # Delete metadata
        success = self.delete(session_id)

        if success:
            logger.info(f"✅ Deleted test session: {session_id}")

        return success

    def session_exists(self, session_id: str) -> bool:
        """Check if session exists"""
        return self.exists(session_id)

    def get_session_count(self) -> int:
        """Get total session count"""
        index_key = self._make_key("index")
        return self.redis_client.scard(index_key)

    def cleanup_expired_sessions(self) -> int:
        """
        Cleanup expired sessions from index

        Returns:
            int: Number of sessions cleaned up
        """
        index_key = self._make_key("index")
        session_ids = self.redis_client.smembers(index_key)

        cleaned = 0
        for session_id in session_ids:
            # Check if session still exists (not expired)
            if not self.exists(session_id):
                # Remove from index
                self.redis_client.srem(index_key, session_id)
                cleaned += 1

        if cleaned > 0:
            logger.info(f"🧹 Cleaned up {cleaned} expired sessions")

        return cleaned
