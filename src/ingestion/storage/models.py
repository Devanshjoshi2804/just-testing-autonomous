"""
Database Models for API Documentation Storage
SQLAlchemy models for persisting parsed API specifications
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
import json

from sqlalchemy import (
    Column, String, Integer, Text, DateTime, Boolean,
    Float, ForeignKey, Index, JSON
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.hybrid import hybrid_property

Base = declarative_base()


class APIDocumentModel(Base):
    """
    Stored API documentation
    Represents a parsed API specification with its fingerprint
    """
    __tablename__ = 'api_documents'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Document identification
    content_hash = Column(String(64), unique=True, index=True, nullable=False)
    semantic_hash = Column(String(64), index=True, nullable=False)

    # API metadata
    title = Column(String(255), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    base_url = Column(String(500), nullable=True)

    # Source information
    source_format = Column(String(50), nullable=True)  # openapi, postman, text, etc.
    source_file = Column(String(500), nullable=True)
    source_content = Column(Text, nullable=True)  # Original raw content (optional)

    # Fingerprint data
    endpoint_signatures = Column(JSON, nullable=False, default=list)  # List of endpoint hashes

    # Statistics
    endpoint_count = Column(Integer, default=0)
    schema_count = Column(Integer, default=0)

    # Complete spec (JSON serialized)
    spec_data = Column(JSON, nullable=False)  # Full UnifiedAPISpec as JSON

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_accessed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Usage tracking
    access_count = Column(Integer, default=0)
    test_run_count = Column(Integer, default=0)

    # User/session tracking
    uploaded_by = Column(String(255), nullable=True)
    session_id = Column(String(255), nullable=True, index=True)

    # Additional metadata (extensible)
    extra_metadata = Column(JSON, nullable=True, default=dict)

    # Relationships
    endpoints = relationship(
        "EndpointModel",
        back_populates="document",
        cascade="all, delete-orphan"
    )
    test_runs = relationship(
        "TestRunModel",
        back_populates="document",
        cascade="all, delete-orphan"
    )

    # Indexes for common queries
    __table_args__ = (
        Index('idx_api_title_version', 'title', 'version'),
        Index('idx_source_format', 'source_format'),
        Index('idx_created_at', 'created_at'),
        Index('idx_semantic_hash', 'semantic_hash'),
    )

    def update_access(self):
        """Update last accessed timestamp and increment access count"""
        self.last_accessed_at = datetime.utcnow()
        self.access_count += 1

    def increment_test_runs(self):
        """Increment test run counter"""
        self.test_run_count += 1

    def __repr__(self) -> str:
        return (
            f"<APIDocument(id={self.id}, title='{self.title}', "
            f"version='{self.version}', endpoints={self.endpoint_count})>"
        )


class EndpointModel(Base):
    """
    Individual API endpoint
    Stored separately for efficient querying and similarity matching
    """
    __tablename__ = 'endpoints'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to document
    document_id = Column(Integer, ForeignKey('api_documents.id'), nullable=False)

    # Endpoint signature (for similarity matching)
    signature = Column(String(32), index=True, nullable=False)  # MD5 hash

    # Endpoint details
    method = Column(String(10), nullable=False, index=True)  # GET, POST, etc.
    path = Column(String(500), nullable=False, index=True)
    normalized_path = Column(String(500), nullable=False, index=True)  # With {param} placeholders

    # Endpoint metadata
    operation_id = Column(String(255), nullable=True)
    summary = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    tags = Column(JSON, default=list)  # List of tags

    # Parameters
    parameter_count = Column(Integer, default=0)
    required_params = Column(JSON, default=list)  # List of required parameter names

    # Request/Response
    has_request_body = Column(Boolean, default=False)
    request_content_type = Column(String(100), nullable=True)
    response_codes = Column(JSON, default=list)  # List of status codes

    # Complete endpoint data (JSON serialized)
    endpoint_data = Column(JSON, nullable=False)  # Full EndpointSpec as JSON

    # Testing statistics
    times_tested = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)  # 0.0 to 1.0
    last_test_status = Column(String(20), nullable=True)  # success, failure, error
    last_tested_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("APIDocumentModel", back_populates="endpoints")

    # Indexes
    __table_args__ = (
        Index('idx_endpoint_method_path', 'method', 'normalized_path'),
        Index('idx_endpoint_signature', 'signature'),
        Index('idx_document_id', 'document_id'),
    )

    def update_test_result(self, success: bool):
        """Update test statistics after a test run"""
        self.times_tested += 1
        self.last_tested_at = datetime.utcnow()
        self.last_test_status = 'success' if success else 'failure'

        # Update success rate (moving average)
        if self.times_tested == 1:
            self.success_rate = 1.0 if success else 0.0
        else:
            # Weighted moving average (recent tests have more weight)
            weight = 0.3
            new_value = 1.0 if success else 0.0
            self.success_rate = (
                weight * new_value + (1 - weight) * self.success_rate
            )

    def __repr__(self) -> str:
        return (
            f"<Endpoint(id={self.id}, method='{self.method}', "
            f"path='{self.path[:50]}')>"
        )


class TestRunModel(Base):
    """
    Test run history for ML training
    Stores test execution results for learning and improvement
    """
    __tablename__ = 'test_runs'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to document
    document_id = Column(Integer, ForeignKey('api_documents.id'), nullable=False)

    # Test execution details
    test_type = Column(String(50), nullable=False)  # smoke, regression, fuzzing, etc.
    status = Column(String(20), nullable=False)  # success, failure, error, skipped

    # Test results
    total_tests = Column(Integer, default=0)
    passed_tests = Column(Integer, default=0)
    failed_tests = Column(Integer, default=0)
    error_tests = Column(Integer, default=0)
    skipped_tests = Column(Integer, default=0)

    # Execution metrics
    duration_seconds = Column(Float, nullable=True)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Error/issue tracking
    errors = Column(JSON, default=list)  # List of error messages
    failures = Column(JSON, default=list)  # List of test failures

    # Test configuration
    test_config = Column(JSON, nullable=True)  # Configuration used for testing

    # Test results details (for ML training)
    test_results = Column(JSON, nullable=True)  # Detailed results per endpoint

    # AI/ML metadata
    model_version = Column(String(50), nullable=True)  # Which model version was used
    constraints_learned = Column(JSON, default=list)  # New constraints discovered
    bugs_found = Column(JSON, default=list)  # Bugs/issues discovered

    # Session tracking
    session_id = Column(String(255), nullable=True, index=True)
    run_by = Column(String(255), nullable=True)

    # Additional metadata
    extra_metadata = Column(JSON, nullable=True, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("APIDocumentModel", back_populates="test_runs")

    # Indexes
    __table_args__ = (
        Index('idx_test_document_id', 'document_id'),
        Index('idx_test_status', 'status'),
        Index('idx_test_started_at', 'started_at'),
        Index('idx_session_id', 'session_id'),
    )

    @hybrid_property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_tests == 0:
            return 0.0
        return self.passed_tests / self.total_tests

    def mark_complete(self, status: str = 'success'):
        """Mark test run as complete"""
        self.completed_at = datetime.utcnow()
        self.status = status
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.duration_seconds = delta.total_seconds()

    def __repr__(self) -> str:
        return (
            f"<TestRun(id={self.id}, document_id={self.document_id}, "
            f"status='{self.status}', tests={self.total_tests})>"
        )
