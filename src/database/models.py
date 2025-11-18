"""
Database Models for AutoTest-RL
SQLAlchemy ORM models for persisting test data
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func


Base = declarative_base()


class TestSession(Base):
    """Test session - groups related test executions"""
    __tablename__ = 'test_sessions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255))
    description = Column(Text)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    status = Column(String(50))  # pending, running, completed, failed
    total_tests = Column(Integer, default=0)
    passed_tests = Column(Integer, default=0)
    failed_tests = Column(Integer, default=0)

    metadata_json = Column(JSON)

    # Relationships
    endpoints = relationship("Endpoint", back_populates="session", cascade="all, delete-orphan")
    test_results = relationship("TestResult", back_populates="session", cascade="all, delete-orphan")
    coverage_reports = relationship("CoverageReport", back_populates="session", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_session_created', 'created_at'),
        Index('idx_session_status', 'status'),
    )

    def __repr__(self):
        return f"<TestSession(id={self.id}, session_id='{self.session_id}', status='{self.status}')>"


class Endpoint(Base):
    """API Endpoint definition"""
    __tablename__ = 'endpoints'

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey('test_sessions.id', ondelete='CASCADE'), nullable=False)

    path = Column(String(500), nullable=False)
    method = Column(String(10), nullable=False)  # GET, POST, PUT, DELETE, PATCH

    description = Column(Text)
    operation_id = Column(String(255))

    # Endpoint metadata
    parameters_json = Column(JSON)  # Parameter definitions
    request_body_json = Column(JSON)  # Request body schema
    responses_json = Column(JSON)  # Response schemas

    # Authentication
    requires_auth = Column(Boolean, default=False)
    auth_type = Column(String(50))  # bearer, basic, apikey, oauth2

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    session = relationship("TestSession", back_populates="endpoints")
    constraints = relationship("Constraint", back_populates="endpoint", cascade="all, delete-orphan")
    test_results = relationship("TestResult", back_populates="endpoint", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_endpoint_path_method', 'path', 'method'),
        Index('idx_endpoint_session', 'session_id'),
    )

    def __repr__(self):
        return f"<Endpoint(id={self.id}, method='{self.method}', path='{self.path}')>"


class Constraint(Base):
    """Parameter constraints"""
    __tablename__ = 'constraints'

    id = Column(Integer, primary_key=True, autoincrement=True)
    endpoint_id = Column(Integer, ForeignKey('endpoints.id', ondelete='CASCADE'), nullable=False)

    parameter_name = Column(String(255), nullable=False)
    parameter_type = Column(String(50))  # string, integer, number, boolean, array, object

    # Constraint details
    constraint_type = Column(String(50))  # min_value, max_value, min_length, max_length, pattern, enum, format
    constraint_value = Column(String(500))

    is_required = Column(Boolean, default=False)
    confidence = Column(Float, default=1.0)  # Confidence score (0.0 to 1.0)

    description = Column(Text)
    source = Column(String(100))  # openapi, documentation, learned

    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    endpoint = relationship("Endpoint", back_populates="constraints")

    # Indexes
    __table_args__ = (
        Index('idx_constraint_endpoint', 'endpoint_id'),
        Index('idx_constraint_param', 'parameter_name'),
    )

    def __repr__(self):
        return f"<Constraint(id={self.id}, param='{self.parameter_name}', type='{self.constraint_type}')>"


class TestResult(Base):
    """Individual test execution result"""
    __tablename__ = 'test_results'

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey('test_sessions.id', ondelete='CASCADE'), nullable=False)
    endpoint_id = Column(Integer, ForeignKey('endpoints.id', ondelete='CASCADE'))

    # Test identification
    test_name = Column(String(500))
    test_type = Column(String(50))  # positive, negative, boundary, security, etc.
    scenario_type = Column(String(50))  # happy_path, error, edge_case, etc.
    strategy = Column(String(50))  # constraint_aware, mutation, combinatorial, etc.

    # Execution details
    executed_at = Column(DateTime, server_default=func.now(), nullable=False)
    duration_ms = Column(Float)

    # Request
    request_method = Column(String(10))
    request_path = Column(String(500))
    request_params_json = Column(JSON)
    request_body_json = Column(JSON)
    request_headers_json = Column(JSON)

    # Response
    response_status_code = Column(Integer)
    response_body_json = Column(JSON)
    response_headers_json = Column(JSON)
    response_time_ms = Column(Float)

    # Result
    success = Column(Boolean, nullable=False)
    expected_status = Column(Integer)
    actual_status = Column(Integer)

    # Validation
    schema_valid = Column(Boolean)
    schema_violations_json = Column(JSON)

    # Error details
    error_message = Column(Text)
    error_type = Column(String(100))
    traceback = Column(Text)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    session = relationship("TestSession", back_populates="test_results")
    endpoint = relationship("Endpoint", back_populates="test_results")

    # Indexes
    __table_args__ = (
        Index('idx_result_session', 'session_id'),
        Index('idx_result_endpoint', 'endpoint_id'),
        Index('idx_result_success', 'success'),
        Index('idx_result_executed', 'executed_at'),
        Index('idx_result_type', 'test_type'),
    )

    def __repr__(self):
        return f"<TestResult(id={self.id}, test_type='{self.test_type}', success={self.success})>"


class CoverageReport(Base):
    """Test coverage metrics"""
    __tablename__ = 'coverage_reports'

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey('test_sessions.id', ondelete='CASCADE'), nullable=False)

    # Coverage percentages
    endpoint_coverage = Column(Float, default=0.0)
    parameter_coverage = Column(Float, default=0.0)
    status_code_coverage = Column(Float, default=0.0)
    scenario_coverage = Column(Float, default=0.0)
    overall_coverage = Column(Float, default=0.0)

    # Counts
    total_endpoints = Column(Integer, default=0)
    tested_endpoints = Column(Integer, default=0)
    total_parameters = Column(Integer, default=0)
    tested_parameters = Column(Integer, default=0)
    total_status_codes = Column(Integer, default=0)
    tested_status_codes = Column(Integer, default=0)

    # Detailed metrics (JSON)
    coverage_details_json = Column(JSON)

    generated_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    session = relationship("TestSession", back_populates="coverage_reports")

    # Indexes
    __table_args__ = (
        Index('idx_coverage_session', 'session_id'),
        Index('idx_coverage_overall', 'overall_coverage'),
    )

    def __repr__(self):
        return f"<CoverageReport(id={self.id}, overall={self.overall_coverage:.1f}%)>"


class ParsedDocument(Base):
    """Cached parsed API documentation"""
    __tablename__ = 'parsed_documents'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Document identification
    document_hash = Column(String(64), unique=True, nullable=False, index=True)  # SHA256 hash
    document_name = Column(String(500))
    document_type = Column(String(50))  # pdf, openapi_json, openapi_yaml
    document_path = Column(String(1000))

    # Parsed content
    parsed_content_json = Column(JSON, nullable=False)
    endpoints_count = Column(Integer, default=0)

    # Metadata
    parsed_at = Column(DateTime, server_default=func.now(), nullable=False)
    parse_duration_ms = Column(Float)
    parser_version = Column(String(50))

    # Cache management
    last_accessed = Column(DateTime, server_default=func.now(), onupdate=func.now())
    access_count = Column(Integer, default=0)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Indexes
    __table_args__ = (
        Index('idx_document_hash', 'document_hash'),
        Index('idx_document_accessed', 'last_accessed'),
    )

    def __repr__(self):
        return f"<ParsedDocument(id={self.id}, name='{self.document_name}', type='{self.document_type}')>"


class LearnedConstraint(Base):
    """Constraints learned from API responses"""
    __tablename__ = 'learned_constraints'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Endpoint identification
    endpoint_path = Column(String(500), nullable=False)
    endpoint_method = Column(String(10), nullable=False)
    parameter_name = Column(String(255), nullable=False)

    # Constraint details
    constraint_type = Column(String(50), nullable=False)
    constraint_value = Column(String(500))

    # Learning metadata
    confidence = Column(Float, default=0.5)  # Increases with repeated observations
    observation_count = Column(Integer, default=1)

    source = Column(String(100))  # error_message, response_validation, pattern_detection
    source_details_json = Column(JSON)

    first_observed = Column(DateTime, server_default=func.now(), nullable=False)
    last_observed = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Indexes
    __table_args__ = (
        Index('idx_learned_endpoint', 'endpoint_path', 'endpoint_method'),
        Index('idx_learned_param', 'parameter_name'),
        Index('idx_learned_confidence', 'confidence'),
    )

    def __repr__(self):
        return f"<LearnedConstraint(id={self.id}, param='{self.parameter_name}', confidence={self.confidence:.2f})>"
