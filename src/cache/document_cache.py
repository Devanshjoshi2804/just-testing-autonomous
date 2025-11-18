"""
Document Cache
Caching layer for parsed API documentation
"""
import hashlib
from typing import Optional, Dict, Any
from loguru import logger

from src.cache.cache_manager import CacheManager, AsyncCacheManager


class DocumentCache:
    """Cache for parsed API documents"""

    def __init__(self, ttl: int = 86400):  # 24 hours default
        """
        Initialize document cache

        Args:
            ttl: Cache TTL in seconds (24 hours default)
        """
        self.cache = CacheManager(namespace="autotest:documents", default_ttl=ttl)
        self.ttl = ttl

    def _make_document_hash(self, content: str) -> str:
        """
        Generate hash for document content

        Args:
            content: Document content

        Returns:
            SHA256 hash
        """
        return hashlib.sha256(content.encode()).hexdigest()

    def get_by_hash(self, document_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get parsed document by hash

        Args:
            document_hash: Document content hash

        Returns:
            Parsed document data or None
        """
        key = f"hash:{document_hash}"
        result = self.cache.get(key)

        if result:
            logger.info(f"Document cache hit: {document_hash[:8]}...")
        else:
            logger.debug(f"Document cache miss: {document_hash[:8]}...")

        return result

    def get_by_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get parsed document by file path

        Args:
            file_path: Path to document file

        Returns:
            Parsed document data or None
        """
        key = f"path:{file_path}"
        result = self.cache.get(key)

        if result:
            logger.info(f"Document cache hit (path): {file_path}")
        else:
            logger.debug(f"Document cache miss (path): {file_path}")

        return result

    def set(
        self,
        document_hash: str,
        parsed_data: Dict[str, Any],
        file_path: Optional[str] = None
    ) -> bool:
        """
        Cache parsed document

        Args:
            document_hash: Document content hash
            parsed_data: Parsed document data
            file_path: Optional file path for secondary lookup

        Returns:
            True if successful
        """
        # Cache by hash
        hash_key = f"hash:{document_hash}"
        success = self.cache.set(hash_key, parsed_data, ttl=self.ttl)

        # Also cache by path if provided
        if file_path and success:
            path_key = f"path:{file_path}"
            self.cache.set(path_key, parsed_data, ttl=self.ttl)

        if success:
            logger.info(f"Cached document: {document_hash[:8]}... (path: {file_path})")

        return success

    def invalidate_by_hash(self, document_hash: str) -> bool:
        """
        Invalidate cached document by hash

        Args:
            document_hash: Document content hash

        Returns:
            True if deleted
        """
        key = f"hash:{document_hash}"
        result = self.cache.delete(key)

        if result:
            logger.info(f"Invalidated document: {document_hash[:8]}...")

        return result

    def invalidate_by_path(self, file_path: str) -> bool:
        """
        Invalidate cached document by path

        Args:
            file_path: Path to document file

        Returns:
            True if deleted
        """
        key = f"path:{file_path}"
        result = self.cache.delete(key)

        if result:
            logger.info(f"Invalidated document (path): {file_path}")

        return result

    def invalidate_all(self) -> int:
        """
        Invalidate all cached documents

        Returns:
            Number of documents invalidated
        """
        count = self.cache.clear_namespace()
        logger.info(f"Invalidated all documents: {count} entries")
        return count

    def get_stats(self) -> Dict[str, int]:
        """
        Get cache statistics

        Returns:
            Dictionary with cache stats
        """
        # Count documents by pattern
        hash_pattern = "hash:*"
        path_pattern = "path:*"

        # This is a simple implementation
        # In production, you might want to use Redis INFO or custom counters
        return {
            'total_documents': 0,  # Would need to scan keys
            'hash_entries': 0,
            'path_entries': 0
        }


class AsyncDocumentCache:
    """Async cache for parsed API documents"""

    def __init__(self, ttl: int = 86400):  # 24 hours default
        """
        Initialize async document cache

        Args:
            ttl: Cache TTL in seconds (24 hours default)
        """
        self.cache = AsyncCacheManager(namespace="autotest:documents", default_ttl=ttl)
        self.ttl = ttl

    def _make_document_hash(self, content: str) -> str:
        """Generate hash for document content"""
        return hashlib.sha256(content.encode()).hexdigest()

    async def get_by_hash(self, document_hash: str) -> Optional[Dict[str, Any]]:
        """Get parsed document by hash (async)"""
        key = f"hash:{document_hash}"
        result = await self.cache.get(key)

        if result:
            logger.info(f"Document cache hit: {document_hash[:8]}...")
        else:
            logger.debug(f"Document cache miss: {document_hash[:8]}...")

        return result

    async def get_by_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get parsed document by file path (async)"""
        key = f"path:{file_path}"
        result = await self.cache.get(key)

        if result:
            logger.info(f"Document cache hit (path): {file_path}")
        else:
            logger.debug(f"Document cache miss (path): {file_path}")

        return result

    async def set(
        self,
        document_hash: str,
        parsed_data: Dict[str, Any],
        file_path: Optional[str] = None
    ) -> bool:
        """Cache parsed document (async)"""
        # Cache by hash
        hash_key = f"hash:{document_hash}"
        success = await self.cache.set(hash_key, parsed_data, ttl=self.ttl)

        # Also cache by path if provided
        if file_path and success:
            path_key = f"path:{file_path}"
            await self.cache.set(path_key, parsed_data, ttl=self.ttl)

        if success:
            logger.info(f"Cached document: {document_hash[:8]}... (path: {file_path})")

        return success

    async def invalidate_by_hash(self, document_hash: str) -> bool:
        """Invalidate cached document by hash (async)"""
        key = f"hash:{document_hash}"
        result = await self.cache.delete(key)

        if result:
            logger.info(f"Invalidated document: {document_hash[:8]}...")

        return result

    async def invalidate_by_path(self, file_path: str) -> bool:
        """Invalidate cached document by path (async)"""
        key = f"path:{file_path}"
        result = await self.cache.delete(key)

        if result:
            logger.info(f"Invalidated document (path): {file_path}")

        return result

    async def invalidate_all(self) -> int:
        """Invalidate all cached documents (async)"""
        count = await self.cache.clear_namespace()
        logger.info(f"Invalidated all documents: {count} entries")
        return count
