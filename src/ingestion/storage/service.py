"""
Document Storage Service
High-level service for storing, retrieving, and recognizing API documents
"""
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from sqlalchemy import create_engine, or_, and_
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from loguru import logger

from src.ingestion.models import UnifiedAPISpec, EndpointSpec
from src.ingestion.storage.models import (
    Base,
    APIDocumentModel,
    EndpointModel,
    TestRunModel
)
from src.ingestion.storage.hashing import (
    DocumentFingerprint,
    compute_content_hash,
    _normalize_path
)


class DocumentStorageService:
    """
    Document storage and recognition service
    Handles persistence, retrieval, and duplicate detection
    """

    def __init__(self, database_url: str = "sqlite:///./api_documents.db"):
        """
        Initialize storage service

        Args:
            database_url: SQLAlchemy database URL
        """
        # Create engine
        if database_url.startswith("sqlite"):
            # SQLite-specific settings
            self.engine = create_engine(
                database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool
            )
        else:
            self.engine = create_engine(database_url)

        # Create tables
        Base.metadata.create_all(self.engine)

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            expire_on_commit=False
        )

        logger.info(f"Initialized DocumentStorageService with {database_url}")

    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()

    def store_document(
        self,
        spec: UnifiedAPISpec,
        fingerprint: DocumentFingerprint,
        source_content: Optional[str] = None,
        uploaded_by: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> APIDocumentModel:
        """
        Store API document with its fingerprint

        Args:
            spec: Unified API specification
            fingerprint: Document fingerprint
            source_content: Optional raw source content
            uploaded_by: Optional user identifier
            session_id: Optional session identifier

        Returns:
            Stored API document model
        """
        session = self.get_session()

        try:
            # Check if document already exists (exact match)
            existing = session.query(APIDocumentModel).filter_by(
                content_hash=fingerprint.content_hash
            ).first()

            if existing:
                logger.info(f"Document already exists: {existing.id}")
                # Update access tracking
                existing.update_access()
                session.commit()
                return existing

            # Create new document
            doc = APIDocumentModel(
                content_hash=fingerprint.content_hash,
                semantic_hash=fingerprint.semantic_hash,
                title=spec.title,
                version=spec.version,
                description=spec.description,
                base_url=spec.base_url,
                source_format=spec.source_format,
                source_file=spec.source_file,
                source_content=source_content,
                endpoint_signatures=fingerprint.endpoint_signatures,
                endpoint_count=len(spec.endpoints),
                schema_count=len(spec.schemas),
                spec_data=spec.model_dump(exclude_none=True, mode='json'),
                uploaded_by=uploaded_by,
                session_id=session_id,
                extra_metadata=fingerprint.metadata
            )

            session.add(doc)
            session.flush()  # Get document ID

            # Store individual endpoints
            for endpoint in spec.endpoints:
                endpoint_model = self._create_endpoint_model(
                    document_id=doc.id,
                    endpoint=endpoint
                )
                session.add(endpoint_model)

            session.commit()
            logger.info(
                f"Stored new document: {doc.id} "
                f"({doc.endpoint_count} endpoints)"
            )

            return doc

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to store document: {e}")
            raise
        finally:
            session.close()

    def _create_endpoint_model(
        self,
        document_id: int,
        endpoint: EndpointSpec
    ) -> EndpointModel:
        """Create endpoint model from endpoint spec"""
        # Compute signature
        import hashlib
        import json

        sig_data = {
            'method': endpoint.method,
            'path': _normalize_path(endpoint.path),
            'parameters': sorted([
                f"{param.location}:{param.name}"
                for param in endpoint.parameters
            ])
        }
        signature = hashlib.md5(
            json.dumps(sig_data, sort_keys=True).encode()
        ).hexdigest()

        # Extract response codes
        response_codes = list(endpoint.responses.keys())

        # Extract required parameters
        required_params = [
            param.name for param in endpoint.parameters
            if param.required
        ]

        return EndpointModel(
            document_id=document_id,
            signature=signature,
            method=endpoint.method,
            path=endpoint.path,
            normalized_path=_normalize_path(endpoint.path),
            operation_id=endpoint.operation_id,
            summary=endpoint.summary,
            description=endpoint.description,
            tags=endpoint.tags,
            parameter_count=len(endpoint.parameters),
            required_params=required_params,
            has_request_body=endpoint.request_body is not None,
            request_content_type=(
                endpoint.request_body.content_type
                if endpoint.request_body else None
            ),
            response_codes=response_codes,
            endpoint_data=endpoint.model_dump(exclude_none=True, mode='json')
        )

    def find_by_content_hash(self, content_hash: str) -> Optional[APIDocumentModel]:
        """
        Find document by exact content hash

        Args:
            content_hash: Content hash to search for

        Returns:
            API document if found, None otherwise
        """
        session = self.get_session()
        try:
            doc = session.query(APIDocumentModel).filter_by(
                content_hash=content_hash
            ).first()

            if doc:
                doc.update_access()
                session.commit()

            return doc
        finally:
            session.close()

    def find_by_semantic_hash(
        self,
        semantic_hash: str
    ) -> List[APIDocumentModel]:
        """
        Find documents with same semantic hash (same structure)

        Args:
            semantic_hash: Semantic hash to search for

        Returns:
            List of matching documents
        """
        session = self.get_session()
        try:
            docs = session.query(APIDocumentModel).filter_by(
                semantic_hash=semantic_hash
            ).all()
            return docs
        finally:
            session.close()

    def find_similar_documents(
        self,
        fingerprint: DocumentFingerprint,
        similarity_threshold: float = 0.7
    ) -> List[Tuple[APIDocumentModel, float]]:
        """
        Find similar documents using endpoint signature matching

        Args:
            fingerprint: Document fingerprint to compare
            similarity_threshold: Minimum similarity score (0.0-1.0)

        Returns:
            List of (document, similarity_score) tuples, sorted by similarity
        """
        session = self.get_session()
        try:
            # Get all documents (we'll compute similarity in Python)
            # For large datasets, consider using specialized vector databases
            all_docs = session.query(APIDocumentModel).all()

            similar_docs = []

            for doc in all_docs:
                doc_fingerprint = DocumentFingerprint(
                    content_hash=doc.content_hash,
                    semantic_hash=doc.semantic_hash,
                    endpoint_signatures=doc.endpoint_signatures,
                    metadata=doc.extra_metadata or {}
                )

                similarity = fingerprint.compute_similarity(doc_fingerprint)

                if similarity >= similarity_threshold:
                    similar_docs.append((doc, similarity))

            # Sort by similarity (descending)
            similar_docs.sort(key=lambda x: x[1], reverse=True)

            return similar_docs

        finally:
            session.close()

    def search_by_title(
        self,
        title: str,
        exact: bool = False
    ) -> List[APIDocumentModel]:
        """
        Search documents by title

        Args:
            title: Title to search for
            exact: Whether to use exact match (default: partial match)

        Returns:
            List of matching documents
        """
        session = self.get_session()
        try:
            if exact:
                docs = session.query(APIDocumentModel).filter_by(
                    title=title
                ).all()
            else:
                docs = session.query(APIDocumentModel).filter(
                    APIDocumentModel.title.ilike(f'%{title}%')
                ).all()

            return docs
        finally:
            session.close()

    def search_endpoints(
        self,
        method: Optional[str] = None,
        path_pattern: Optional[str] = None,
        tag: Optional[str] = None
    ) -> List[EndpointModel]:
        """
        Search endpoints by criteria

        Args:
            method: HTTP method filter
            path_pattern: Path pattern to match (SQL LIKE)
            tag: Tag to filter by

        Returns:
            List of matching endpoints
        """
        session = self.get_session()
        try:
            query = session.query(EndpointModel)

            if method:
                query = query.filter_by(method=method.upper())

            if path_pattern:
                query = query.filter(
                    EndpointModel.path.ilike(f'%{path_pattern}%')
                )

            if tag:
                # JSON contains check (SQLite/PostgreSQL compatible)
                query = query.filter(
                    EndpointModel.tags.contains([tag])
                )

            return query.all()

        finally:
            session.close()

    def get_document_by_id(self, document_id: int) -> Optional[APIDocumentModel]:
        """Get document by ID"""
        session = self.get_session()
        try:
            doc = session.query(APIDocumentModel).filter_by(id=document_id).first()
            if doc:
                doc.update_access()
                session.commit()
            return doc
        finally:
            session.close()

    def get_all_documents(
        self,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[APIDocumentModel]:
        """
        Get all documents with optional pagination

        Args:
            limit: Maximum number of documents to return
            offset: Number of documents to skip

        Returns:
            List of documents
        """
        session = self.get_session()
        try:
            query = session.query(APIDocumentModel).order_by(
                APIDocumentModel.created_at.desc()
            )

            if limit:
                query = query.limit(limit)

            if offset:
                query = query.offset(offset)

            return query.all()

        finally:
            session.close()

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get storage statistics

        Returns:
            Dictionary with statistics
        """
        session = self.get_session()
        try:
            total_docs = session.query(APIDocumentModel).count()
            total_endpoints = session.query(EndpointModel).count()
            total_test_runs = session.query(TestRunModel).count()

            # Most accessed documents
            most_accessed = session.query(APIDocumentModel).order_by(
                APIDocumentModel.access_count.desc()
            ).limit(5).all()

            return {
                'total_documents': total_docs,
                'total_endpoints': total_endpoints,
                'total_test_runs': total_test_runs,
                'most_accessed': [
                    {
                        'id': doc.id,
                        'title': doc.title,
                        'access_count': doc.access_count
                    }
                    for doc in most_accessed
                ]
            }

        finally:
            session.close()

    def record_test_run(
        self,
        document_id: int,
        test_type: str,
        status: str,
        test_results: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> TestRunModel:
        """
        Record a test run for ML training

        Args:
            document_id: ID of the tested document
            test_type: Type of test (smoke, regression, etc.)
            status: Test status (success, failure, error)
            test_results: Detailed test results
            **kwargs: Additional test run attributes

        Returns:
            Created test run model
        """
        session = self.get_session()

        try:
            test_run = TestRunModel(
                document_id=document_id,
                test_type=test_type,
                status=status,
                test_results=test_results,
                started_at=kwargs.get('started_at', datetime.utcnow()),
                **{k: v for k, v in kwargs.items() if k != 'started_at'}
            )

            session.add(test_run)

            # Update document test run counter
            doc = session.query(APIDocumentModel).filter_by(id=document_id).first()
            if doc:
                doc.increment_test_runs()

            session.commit()

            logger.info(f"Recorded test run {test_run.id} for document {document_id}")

            return test_run

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to record test run: {e}")
            raise
        finally:
            session.close()

    def delete_document(self, document_id: int) -> bool:
        """
        Delete document and all related data

        Args:
            document_id: ID of document to delete

        Returns:
            True if deleted, False if not found
        """
        session = self.get_session()

        try:
            doc = session.query(APIDocumentModel).filter_by(id=document_id).first()

            if not doc:
                return False

            session.delete(doc)
            session.commit()

            logger.info(f"Deleted document {document_id}")

            return True

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete document: {e}")
            raise
        finally:
            session.close()

    def __repr__(self) -> str:
        stats = self.get_statistics()
        return (
            f"DocumentStorageService("
            f"docs={stats['total_documents']}, "
            f"endpoints={stats['total_endpoints']})"
        )
