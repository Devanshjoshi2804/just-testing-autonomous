"""
Unit Tests for Document Storage System
Tests hashing, models, and storage service
"""
import pytest
import tempfile
import os
from datetime import datetime

from src.ingestion.storage.hashing import (
    compute_content_hash,
    compute_semantic_hash,
    compute_endpoint_signatures,
    DocumentFingerprint,
    _normalize_path
)
from src.ingestion.storage.models import (
    APIDocumentModel,
    EndpointModel,
    TestRunModel
)
from src.ingestion.storage.service import DocumentStorageService
from src.ingestion.models import (
    UnifiedAPISpec,
    EndpointSpec,
    ParameterSpec,
    ResponseSpec,
    SchemaSpec,
    HTTPMethod,
    ParameterLocation,
    DataType
)


@pytest.fixture
def sample_spec():
    """Create sample API spec"""
    return UnifiedAPISpec(
        title="Test API",
        version="1.0.0",
        description="A test API",
        endpoints=[
            EndpointSpec(
                method=HTTPMethod.GET,
                path="/users/{id}",
                summary="Get user",
                parameters=[
                    ParameterSpec(
                        name="id",
                        location=ParameterLocation.PATH,
                        required=True,
                        type=DataType.INTEGER
                    )
                ],
                responses={
                    200: ResponseSpec(status_code=200, description="Success")
                }
            ),
            EndpointSpec(
                method=HTTPMethod.POST,
                path="/users",
                summary="Create user",
                responses={
                    201: ResponseSpec(status_code=201, description="Created")
                }
            )
        ],
        schemas={
            "User": SchemaSpec(
                type=DataType.OBJECT,
                properties={}
            )
        }
    )


@pytest.fixture
def storage_service():
    """Create storage service with in-memory database"""
    # Use temporary file for SQLite
    db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    db_file.close()

    service = DocumentStorageService(f"sqlite:///{db_file.name}")

    yield service

    # Cleanup
    try:
        os.unlink(db_file.name)
    except:
        pass


class TestHashing:
    """Test hashing functions"""

    def test_content_hash_string(self):
        """Test content hashing with string"""
        content = "Hello, World!"
        hash1 = compute_content_hash(content)
        hash2 = compute_content_hash(content)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex

    def test_content_hash_dict(self):
        """Test content hashing with dict"""
        content = {"key": "value", "number": 42}
        hash1 = compute_content_hash(content)
        hash2 = compute_content_hash(content)

        assert hash1 == hash2

    def test_content_hash_dict_order_independent(self):
        """Test dict hashing is order-independent"""
        dict1 = {"a": 1, "b": 2, "c": 3}
        dict2 = {"c": 3, "b": 2, "a": 1}

        hash1 = compute_content_hash(dict1)
        hash2 = compute_content_hash(dict2)

        assert hash1 == hash2

    def test_content_hash_different_content(self):
        """Test different content produces different hashes"""
        hash1 = compute_content_hash("content1")
        hash2 = compute_content_hash("content2")

        assert hash1 != hash2

    def test_semantic_hash(self, sample_spec):
        """Test semantic hashing"""
        hash1 = compute_semantic_hash(sample_spec)

        assert isinstance(hash1, str)
        assert len(hash1) == 64

    def test_semantic_hash_consistency(self, sample_spec):
        """Test semantic hash is consistent"""
        hash1 = compute_semantic_hash(sample_spec)
        hash2 = compute_semantic_hash(sample_spec)

        assert hash1 == hash2

    def test_semantic_hash_ignores_descriptions(self):
        """Test semantic hash ignores descriptions"""
        spec1 = UnifiedAPISpec(
            title="Test API",
            version="1.0.0",
            description="Description 1",
            endpoints=[
                EndpointSpec(
                    method=HTTPMethod.GET,
                    path="/test",
                    summary="Summary 1",
                    responses={}
                )
            ]
        )

        spec2 = UnifiedAPISpec(
            title="Test API",
            version="1.0.0",
            description="Description 2",
            endpoints=[
                EndpointSpec(
                    method=HTTPMethod.GET,
                    path="/test",
                    summary="Summary 2",
                    responses={}
                )
            ]
        )

        # Semantic hash should be the same (structure is identical)
        hash1 = compute_semantic_hash(spec1)
        hash2 = compute_semantic_hash(spec2)

        assert hash1 == hash2

    def test_normalize_path(self):
        """Test path normalization"""
        assert _normalize_path("/users/{id}") == "/users/{param}"
        assert _normalize_path("/users/:id") == "/users/{param}"
        assert _normalize_path("/users/123") == "/users/{param}"
        assert _normalize_path("/users/123/posts/456") == "/users/{param}/posts/{param}"

    def test_normalize_path_uuid(self):
        """Test UUID normalization in paths"""
        uuid_path = "/resources/550e8400-e29b-41d4-a716-446655440000"
        normalized = _normalize_path(uuid_path)
        assert normalized == "/resources/{param}"

    def test_endpoint_signatures(self, sample_spec):
        """Test endpoint signature computation"""
        signatures = compute_endpoint_signatures(sample_spec)

        assert len(signatures) == 2  # Two endpoints
        assert all(isinstance(sig, str) for sig in signatures)
        assert all(len(sig) == 32 for sig in signatures)  # MD5 hex


class TestDocumentFingerprint:
    """Test DocumentFingerprint class"""

    def test_from_content_and_spec(self, sample_spec):
        """Test creating fingerprint from content and spec"""
        content = '{"test": "content"}'

        fingerprint = DocumentFingerprint.from_content_and_spec(
            content=content,
            spec=sample_spec
        )

        assert fingerprint.content_hash
        assert fingerprint.semantic_hash
        assert len(fingerprint.endpoint_signatures) == 2
        assert fingerprint.metadata['title'] == "Test API"
        assert fingerprint.metadata['endpoint_count'] == 2

    def test_from_spec_only(self, sample_spec):
        """Test creating fingerprint from spec only"""
        fingerprint = DocumentFingerprint.from_spec_only(spec=sample_spec)

        assert fingerprint.content_hash
        assert fingerprint.semantic_hash
        assert len(fingerprint.endpoint_signatures) == 2

    def test_is_exact_match(self, sample_spec):
        """Test exact match detection"""
        content = '{"test": "content"}'

        fp1 = DocumentFingerprint.from_content_and_spec(content, sample_spec)
        fp2 = DocumentFingerprint.from_content_and_spec(content, sample_spec)

        assert fp1.is_exact_match(fp2)

    def test_is_not_exact_match(self, sample_spec):
        """Test detecting non-exact match"""
        fp1 = DocumentFingerprint.from_content_and_spec("content1", sample_spec)
        fp2 = DocumentFingerprint.from_content_and_spec("content2", sample_spec)

        assert not fp1.is_exact_match(fp2)

    def test_is_semantic_match(self):
        """Test semantic match detection"""
        spec1 = UnifiedAPISpec(
            title="API 1",
            version="1.0.0",
            endpoints=[
                EndpointSpec(
                    method=HTTPMethod.GET,
                    path="/test",
                    responses={}
                )
            ]
        )

        spec2 = UnifiedAPISpec(
            title="API 2",  # Different title
            version="2.0.0",  # Different version
            endpoints=[
                EndpointSpec(
                    method=HTTPMethod.GET,
                    path="/test",
                    responses={}
                )
            ]
        )

        fp1 = DocumentFingerprint.from_spec_only(spec1)
        fp2 = DocumentFingerprint.from_spec_only(spec2)

        # Should be semantic match (same structure)
        assert fp1.is_semantic_match(fp2)

    def test_compute_similarity_identical(self, sample_spec):
        """Test similarity for identical specs"""
        fp1 = DocumentFingerprint.from_spec_only(sample_spec)
        fp2 = DocumentFingerprint.from_spec_only(sample_spec)

        similarity = fp1.compute_similarity(fp2)
        assert similarity == 1.0

    def test_compute_similarity_partial(self):
        """Test similarity for partially overlapping specs"""
        spec1 = UnifiedAPISpec(
            title="API 1",
            version="1.0.0",
            endpoints=[
                EndpointSpec(method=HTTPMethod.GET, path="/a", responses={}),
                EndpointSpec(method=HTTPMethod.GET, path="/b", responses={}),
            ]
        )

        spec2 = UnifiedAPISpec(
            title="API 2",
            version="1.0.0",
            endpoints=[
                EndpointSpec(method=HTTPMethod.GET, path="/b", responses={}),
                EndpointSpec(method=HTTPMethod.GET, path="/c", responses={}),
            ]
        )

        fp1 = DocumentFingerprint.from_spec_only(spec1)
        fp2 = DocumentFingerprint.from_spec_only(spec2)

        similarity = fp1.compute_similarity(fp2)

        # Should have some overlap but not 100%
        assert 0.0 < similarity < 1.0

    def test_compute_similarity_none(self):
        """Test similarity for completely different specs"""
        spec1 = UnifiedAPISpec(
            title="API 1",
            version="1.0.0",
            endpoints=[
                EndpointSpec(method=HTTPMethod.GET, path="/a", responses={})
            ]
        )

        spec2 = UnifiedAPISpec(
            title="API 2",
            version="1.0.0",
            endpoints=[
                EndpointSpec(method=HTTPMethod.GET, path="/b", responses={})
            ]
        )

        fp1 = DocumentFingerprint.from_spec_only(spec1)
        fp2 = DocumentFingerprint.from_spec_only(spec2)

        similarity = fp1.compute_similarity(fp2)

        assert similarity == 0.0

    def test_to_dict_from_dict(self, sample_spec):
        """Test serialization to/from dict"""
        fp1 = DocumentFingerprint.from_spec_only(sample_spec)

        data = fp1.to_dict()
        fp2 = DocumentFingerprint.from_dict(data)

        assert fp1.content_hash == fp2.content_hash
        assert fp1.semantic_hash == fp2.semantic_hash
        assert fp1.endpoint_signatures == fp2.endpoint_signatures


class TestStorageService:
    """Test DocumentStorageService"""

    def test_initialization(self, storage_service):
        """Test service initialization"""
        assert storage_service is not None

        stats = storage_service.get_statistics()
        assert stats['total_documents'] == 0
        assert stats['total_endpoints'] == 0

    def test_store_document(self, storage_service, sample_spec):
        """Test storing a document"""
        fingerprint = DocumentFingerprint.from_spec_only(sample_spec)

        doc = storage_service.store_document(
            spec=sample_spec,
            fingerprint=fingerprint,
            uploaded_by="test_user"
        )

        assert doc is not None
        assert doc.id is not None
        assert doc.title == "Test API"
        assert doc.version == "1.0.0"
        assert doc.endpoint_count == 2
        assert doc.schema_count == 1

    def test_store_duplicate_document(self, storage_service, sample_spec):
        """Test storing duplicate document returns existing"""
        fingerprint = DocumentFingerprint.from_spec_only(sample_spec)

        # Store first time
        doc1 = storage_service.store_document(spec=sample_spec, fingerprint=fingerprint)

        # Store again
        doc2 = storage_service.store_document(spec=sample_spec, fingerprint=fingerprint)

        # Should be same document
        assert doc1.id == doc2.id
        assert doc2.access_count > doc1.access_count  # Access count increased

    def test_find_by_content_hash(self, storage_service, sample_spec):
        """Test finding document by content hash"""
        fingerprint = DocumentFingerprint.from_spec_only(sample_spec)

        # Store document
        doc = storage_service.store_document(spec=sample_spec, fingerprint=fingerprint)

        # Find by hash
        found = storage_service.find_by_content_hash(fingerprint.content_hash)

        assert found is not None
        assert found.id == doc.id

    def test_find_by_content_hash_not_found(self, storage_service):
        """Test finding non-existent document"""
        found = storage_service.find_by_content_hash("nonexistent_hash")
        assert found is None

    def test_find_by_semantic_hash(self, storage_service):
        """Test finding documents by semantic hash"""
        spec1 = UnifiedAPISpec(
            title="API 1",
            version="1.0.0",
            description="Different description",
            endpoints=[
                EndpointSpec(method=HTTPMethod.GET, path="/test", responses={})
            ]
        )

        spec2 = UnifiedAPISpec(
            title="API 2",
            version="2.0.0",
            description="Another description",
            endpoints=[
                EndpointSpec(method=HTTPMethod.GET, path="/test", responses={})
            ]
        )

        fp1 = DocumentFingerprint.from_spec_only(spec1)
        fp2 = DocumentFingerprint.from_spec_only(spec2)

        # Store both
        storage_service.store_document(spec=spec1, fingerprint=fp1)
        storage_service.store_document(spec=spec2, fingerprint=fp2)

        # Find by semantic hash
        docs = storage_service.find_by_semantic_hash(fp1.semantic_hash)

        # Should find both (same structure)
        assert len(docs) == 2

    def test_find_similar_documents(self, storage_service):
        """Test finding similar documents"""
        spec1 = UnifiedAPISpec(
            title="API 1",
            version="1.0.0",
            endpoints=[
                EndpointSpec(method=HTTPMethod.GET, path="/a", responses={}),
                EndpointSpec(method=HTTPMethod.GET, path="/b", responses={}),
            ]
        )

        spec2 = UnifiedAPISpec(
            title="API 2",
            version="1.0.0",
            endpoints=[
                EndpointSpec(method=HTTPMethod.GET, path="/b", responses={}),
                EndpointSpec(method=HTTPMethod.GET, path="/c", responses={}),
            ]
        )

        fp1 = DocumentFingerprint.from_spec_only(spec1)
        fp2 = DocumentFingerprint.from_spec_only(spec2)

        # Store first spec
        storage_service.store_document(spec=spec1, fingerprint=fp1)

        # Find similar to second spec
        similar = storage_service.find_similar_documents(
            fingerprint=fp2,
            similarity_threshold=0.1
        )

        # Should find spec1 as similar
        assert len(similar) > 0
        assert similar[0][1] > 0.0  # Has some similarity

    def test_search_by_title_exact(self, storage_service, sample_spec):
        """Test searching by exact title"""
        fingerprint = DocumentFingerprint.from_spec_only(sample_spec)
        storage_service.store_document(spec=sample_spec, fingerprint=fingerprint)

        docs = storage_service.search_by_title("Test API", exact=True)

        assert len(docs) == 1
        assert docs[0].title == "Test API"

    def test_search_by_title_partial(self, storage_service, sample_spec):
        """Test searching by partial title"""
        fingerprint = DocumentFingerprint.from_spec_only(sample_spec)
        storage_service.store_document(spec=sample_spec, fingerprint=fingerprint)

        docs = storage_service.search_by_title("Test", exact=False)

        assert len(docs) == 1

    def test_get_document_by_id(self, storage_service, sample_spec):
        """Test getting document by ID"""
        fingerprint = DocumentFingerprint.from_spec_only(sample_spec)
        doc = storage_service.store_document(spec=sample_spec, fingerprint=fingerprint)

        found = storage_service.get_document_by_id(doc.id)

        assert found is not None
        assert found.id == doc.id

    def test_get_all_documents(self, storage_service):
        """Test getting all documents with pagination"""
        # Store multiple documents
        for i in range(5):
            spec = UnifiedAPISpec(
                title=f"API {i}",
                version="1.0.0",
                endpoints=[]
            )
            fp = DocumentFingerprint.from_spec_only(spec)
            storage_service.store_document(spec=spec, fingerprint=fp)

        # Get all
        all_docs = storage_service.get_all_documents()
        assert len(all_docs) == 5

        # Get with limit
        limited = storage_service.get_all_documents(limit=3)
        assert len(limited) == 3

        # Get with offset
        offset = storage_service.get_all_documents(limit=2, offset=3)
        assert len(offset) == 2

    def test_search_endpoints(self, storage_service, sample_spec):
        """Test searching endpoints"""
        fingerprint = DocumentFingerprint.from_spec_only(sample_spec)
        storage_service.store_document(spec=sample_spec, fingerprint=fingerprint)

        # Search by method
        get_endpoints = storage_service.search_endpoints(method="GET")
        assert len(get_endpoints) == 1
        assert get_endpoints[0].method == "GET"

        # Search by path pattern
        user_endpoints = storage_service.search_endpoints(path_pattern="users")
        assert len(user_endpoints) == 2

    def test_record_test_run(self, storage_service, sample_spec):
        """Test recording test run"""
        fingerprint = DocumentFingerprint.from_spec_only(sample_spec)
        doc = storage_service.store_document(spec=sample_spec, fingerprint=fingerprint)

        test_run = storage_service.record_test_run(
            document_id=doc.id,
            test_type="smoke",
            status="success",
            total_tests=10,
            passed_tests=10,
            test_results={"details": "All tests passed"}
        )

        assert test_run is not None
        assert test_run.document_id == doc.id
        assert test_run.test_type == "smoke"
        assert test_run.status == "success"

    def test_delete_document(self, storage_service, sample_spec):
        """Test deleting document"""
        fingerprint = DocumentFingerprint.from_spec_only(sample_spec)
        doc = storage_service.store_document(spec=sample_spec, fingerprint=fingerprint)

        # Delete
        deleted = storage_service.delete_document(doc.id)
        assert deleted is True

        # Verify deleted
        found = storage_service.get_document_by_id(doc.id)
        assert found is None

    def test_delete_nonexistent_document(self, storage_service):
        """Test deleting non-existent document"""
        deleted = storage_service.delete_document(99999)
        assert deleted is False

    def test_statistics(self, storage_service, sample_spec):
        """Test getting statistics"""
        fingerprint = DocumentFingerprint.from_spec_only(sample_spec)
        storage_service.store_document(spec=sample_spec, fingerprint=fingerprint)

        stats = storage_service.get_statistics()

        assert stats['total_documents'] == 1
        assert stats['total_endpoints'] == 2
        assert stats['total_test_runs'] == 0
