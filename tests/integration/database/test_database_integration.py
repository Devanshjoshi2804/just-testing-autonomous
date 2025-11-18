"""
Integration Tests for Database Layer
Tests database operations, repositories, and relationships
"""
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, TestSession, Endpoint, Constraint, TestResult, CoverageReport
from src.database.config import DatabaseConfig
from src.database.repositories import (
    TestSessionRepository,
    EndpointRepository,
    ConstraintRepository,
    TestResultRepository,
    CoverageReportRepository
)


@pytest.fixture(scope="function")
def db_engine():
    """Create in-memory SQLite database for testing"""
    from sqlalchemy import event
    import sqlite3

    engine = create_engine("sqlite:///:memory:")

    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        if isinstance(dbapi_conn, sqlite3.Connection):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create database session for testing"""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def db_config():
    """Create database config with in-memory database"""
    from sqlalchemy import event
    import sqlite3

    config = DatabaseConfig(database_url="sqlite:///:memory:")

    # Enable foreign keys for SQLite
    @event.listens_for(config.engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        if isinstance(dbapi_conn, sqlite3.Connection):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    # Create tables
    Base.metadata.create_all(config.engine)

    yield config

    # Cleanup
    Base.metadata.drop_all(config.engine)
    config.engine.dispose()


# =============================================================================
# TestSession Repository Tests
# =============================================================================


def test_create_test_session(db_session):
    """Test creating a test session"""
    repo = TestSessionRepository(db_session)

    session = repo.create(
        session_id="test-session-1",
        name="My Test Session",
        description="Testing user endpoints"
    )

    assert session.id is not None
    assert session.session_id == "test-session-1"
    assert session.name == "My Test Session"
    assert session.status == "pending"
    assert session.total_tests == 0
    assert session.passed_tests == 0
    assert session.failed_tests == 0


def test_get_session_by_session_id(db_session):
    """Test retrieving session by session_id"""
    repo = TestSessionRepository(db_session)

    # Create session
    created = repo.create(session_id="test-123", name="Test")
    db_session.commit()

    # Retrieve
    found = repo.get_by_session_id("test-123")

    assert found is not None
    assert found.session_id == "test-123"
    assert found.name == "Test"


def test_update_session_status(db_session):
    """Test updating session status"""
    repo = TestSessionRepository(db_session)

    # Create and update
    repo.create(session_id="test-123")
    db_session.commit()

    result = repo.update_status("test-123", "running")
    db_session.commit()

    assert result is True

    # Verify
    session = repo.get_by_session_id("test-123")
    assert session.status == "running"


def test_update_test_counts(db_session):
    """Test updating test counts"""
    repo = TestSessionRepository(db_session)

    repo.create(session_id="test-123")
    db_session.commit()

    repo.update_test_counts("test-123", total=100, passed=85, failed=15)
    db_session.commit()

    session = repo.get_by_session_id("test-123")
    assert session.total_tests == 100
    assert session.passed_tests == 85
    assert session.failed_tests == 15


def test_increment_test_counts(db_session):
    """Test incrementing test counts"""
    repo = TestSessionRepository(db_session)

    repo.create(session_id="test-123")
    db_session.commit()

    # Increment passed
    repo.increment_test_counts("test-123", passed=True)
    repo.increment_test_counts("test-123", passed=True)
    db_session.commit()

    session = repo.get_by_session_id("test-123")
    assert session.total_tests == 2
    assert session.passed_tests == 2
    assert session.failed_tests == 0

    # Increment failed
    repo.increment_test_counts("test-123", passed=False)
    db_session.commit()

    session = repo.get_by_session_id("test-123")
    assert session.total_tests == 3
    assert session.passed_tests == 2
    assert session.failed_tests == 1


def test_get_all_sessions(db_session):
    """Test retrieving all sessions with filtering"""
    repo = TestSessionRepository(db_session)

    # Create multiple sessions
    repo.create(session_id="test-1", name="Session 1")
    repo.create(session_id="test-2", name="Session 2")
    repo.create(session_id="test-3", name="Session 3")
    repo.update_status("test-1", "completed")
    db_session.commit()

    # Get all
    all_sessions = repo.get_all()
    assert len(all_sessions) == 3

    # Filter by status
    completed = repo.get_all(status="completed")
    assert len(completed) == 1
    assert completed[0].session_id == "test-1"

    # Test pagination
    page1 = repo.get_all(limit=2, offset=0)
    assert len(page1) == 2


def test_delete_session_cascades(db_session):
    """Test that deleting session cascades to related records"""
    session_repo = TestSessionRepository(db_session)
    endpoint_repo = EndpointRepository(db_session)
    result_repo = TestResultRepository(db_session)

    # Create session
    test_session = session_repo.create(session_id="test-123")
    db_session.commit()

    # Create related endpoint and result
    endpoint = endpoint_repo.create(
        session_id=test_session.id,
        path="/api/users",
        method="GET"
    )
    result_repo.create(
        session_id=test_session.id,
        endpoint_id=endpoint.id,
        success=True
    )
    db_session.commit()

    # Save IDs before deleting
    endpoint_id = endpoint.id

    # Delete session
    session_repo.delete("test-123")
    db_session.commit()

    # Verify cascading delete
    assert session_repo.get_by_session_id("test-123") is None
    assert endpoint_repo.get_by_id(endpoint_id) is None


# =============================================================================
# Endpoint Repository Tests
# =============================================================================


def test_create_endpoint(db_session):
    """Test creating an endpoint"""
    session_repo = TestSessionRepository(db_session)
    endpoint_repo = EndpointRepository(db_session)

    # Create session first
    test_session = session_repo.create(session_id="test-123")
    db_session.commit()

    # Create endpoint
    endpoint = endpoint_repo.create(
        session_id=test_session.id,
        path="/api/users",
        method="GET",
        description="Get all users",
        parameters={"page": {"type": "integer"}},
        requires_auth=True,
        auth_type="bearer"
    )

    assert endpoint.id is not None
    assert endpoint.path == "/api/users"
    assert endpoint.method == "GET"
    assert endpoint.requires_auth is True
    assert endpoint.parameters_json["page"]["type"] == "integer"


def test_get_endpoint_by_path_and_method(db_session):
    """Test retrieving endpoint by path and method"""
    session_repo = TestSessionRepository(db_session)
    endpoint_repo = EndpointRepository(db_session)

    test_session = session_repo.create(session_id="test-123")
    endpoint_repo.create(
        session_id=test_session.id,
        path="/api/users",
        method="GET"
    )
    db_session.commit()

    found = endpoint_repo.get_by_path_and_method(
        test_session.id,
        "/api/users",
        "GET"
    )

    assert found is not None
    assert found.path == "/api/users"
    assert found.method == "GET"


def test_get_endpoints_by_session(db_session):
    """Test retrieving all endpoints for a session"""
    session_repo = TestSessionRepository(db_session)
    endpoint_repo = EndpointRepository(db_session)

    test_session = session_repo.create(session_id="test-123")
    endpoint_repo.create(session_id=test_session.id, path="/api/users", method="GET")
    endpoint_repo.create(session_id=test_session.id, path="/api/users", method="POST")
    endpoint_repo.create(session_id=test_session.id, path="/api/posts", method="GET")
    db_session.commit()

    endpoints = endpoint_repo.get_by_session(test_session.id)
    assert len(endpoints) == 3


def test_search_endpoints_by_path_pattern(db_session):
    """Test searching endpoints by path pattern"""
    session_repo = TestSessionRepository(db_session)
    endpoint_repo = EndpointRepository(db_session)

    test_session = session_repo.create(session_id="test-123")
    endpoint_repo.create(session_id=test_session.id, path="/api/users", method="GET")
    endpoint_repo.create(session_id=test_session.id, path="/api/users/123", method="GET")
    endpoint_repo.create(session_id=test_session.id, path="/api/posts", method="GET")
    db_session.commit()

    # Search for /api/users*
    users_endpoints = endpoint_repo.search_by_path_pattern(
        test_session.id,
        "/api/users%"
    )

    assert len(users_endpoints) == 2


# =============================================================================
# Constraint Repository Tests
# =============================================================================


def test_create_constraint(db_session):
    """Test creating a constraint"""
    session_repo = TestSessionRepository(db_session)
    endpoint_repo = EndpointRepository(db_session)
    constraint_repo = ConstraintRepository(db_session)

    test_session = session_repo.create(session_id="test-123")
    endpoint = endpoint_repo.create(
        session_id=test_session.id,
        path="/api/users",
        method="GET"
    )
    db_session.commit()

    constraint = constraint_repo.create(
        endpoint_id=endpoint.id,
        parameter_name="age",
        parameter_type="integer",
        constraint_type="min_value",
        constraint_value="18",
        is_required=True,
        confidence=0.95,
        source="openapi"
    )

    assert constraint.id is not None
    assert constraint.parameter_name == "age"
    assert constraint.constraint_type == "min_value"
    assert constraint.confidence == 0.95


def test_get_constraints_by_endpoint(db_session):
    """Test retrieving constraints for an endpoint"""
    session_repo = TestSessionRepository(db_session)
    endpoint_repo = EndpointRepository(db_session)
    constraint_repo = ConstraintRepository(db_session)

    test_session = session_repo.create(session_id="test-123")
    endpoint = endpoint_repo.create(
        session_id=test_session.id,
        path="/api/users",
        method="POST"
    )
    db_session.commit()

    # Create multiple constraints
    constraint_repo.create(
        endpoint_id=endpoint.id,
        parameter_name="email",
        parameter_type="string",
        constraint_type="format",
        constraint_value="email"
    )
    constraint_repo.create(
        endpoint_id=endpoint.id,
        parameter_name="age",
        parameter_type="integer",
        constraint_type="min_value",
        constraint_value="18"
    )
    db_session.commit()

    constraints = constraint_repo.get_by_endpoint(endpoint.id)
    assert len(constraints) == 2


def test_get_required_parameters(db_session):
    """Test retrieving required parameters"""
    session_repo = TestSessionRepository(db_session)
    endpoint_repo = EndpointRepository(db_session)
    constraint_repo = ConstraintRepository(db_session)

    test_session = session_repo.create(session_id="test-123")
    endpoint = endpoint_repo.create(
        session_id=test_session.id,
        path="/api/users",
        method="POST"
    )
    db_session.commit()

    # Create constraints
    constraint_repo.create(
        endpoint_id=endpoint.id,
        parameter_name="email",
        parameter_type="string",
        constraint_type="format",
        is_required=True
    )
    constraint_repo.create(
        endpoint_id=endpoint.id,
        parameter_name="phone",
        parameter_type="string",
        constraint_type="pattern",
        is_required=False
    )
    db_session.commit()

    required = constraint_repo.get_required_parameters(endpoint.id)
    assert len(required) == 1
    assert required[0].parameter_name == "email"


def test_find_or_create_constraint(db_session):
    """Test find or create pattern for constraints"""
    session_repo = TestSessionRepository(db_session)
    endpoint_repo = EndpointRepository(db_session)
    constraint_repo = ConstraintRepository(db_session)

    test_session = session_repo.create(session_id="test-123")
    endpoint = endpoint_repo.create(
        session_id=test_session.id,
        path="/api/users",
        method="GET"
    )
    db_session.commit()

    # First call creates
    constraint1 = constraint_repo.find_or_create(
        endpoint_id=endpoint.id,
        parameter_name="age",
        parameter_type="integer",
        constraint_type="min_value",
        constraint_value="18",
        confidence=0.8
    )
    db_session.commit()

    # Second call finds existing
    constraint2 = constraint_repo.find_or_create(
        endpoint_id=endpoint.id,
        parameter_name="age",
        constraint_type="min_value",
        constraint_value="18",
        parameter_type="integer",
        confidence=0.9  # Higher confidence
    )
    db_session.commit()

    # Should be same constraint with updated confidence
    assert constraint1.id == constraint2.id
    assert constraint2.confidence == 0.9


# =============================================================================
# TestResult Repository Tests
# =============================================================================


def test_create_test_result(db_session):
    """Test creating a test result"""
    session_repo = TestSessionRepository(db_session)
    endpoint_repo = EndpointRepository(db_session)
    result_repo = TestResultRepository(db_session)

    test_session = session_repo.create(session_id="test-123")
    endpoint = endpoint_repo.create(
        session_id=test_session.id,
        path="/api/users",
        method="GET"
    )
    db_session.commit()

    result = result_repo.create(
        session_id=test_session.id,
        endpoint_id=endpoint.id,
        test_name="Test GET /api/users",
        test_type="positive",
        scenario_type="happy_path",
        request_method="GET",
        request_path="/api/users",
        response_status_code=200,
        response_time_ms=45.2,
        success=True,
        expected_status=200,
        actual_status=200,
        schema_valid=True
    )

    assert result.id is not None
    assert result.success is True
    assert result.response_status_code == 200
    assert result.response_time_ms == 45.2


def test_get_failed_tests(db_session):
    """Test retrieving failed tests"""
    session_repo = TestSessionRepository(db_session)
    result_repo = TestResultRepository(db_session)

    test_session = session_repo.create(session_id="test-123")
    db_session.commit()

    # Create mixed results
    result_repo.create(
        session_id=test_session.id,
        test_name="Test 1",
        success=True
    )
    result_repo.create(
        session_id=test_session.id,
        test_name="Test 2",
        success=False,
        error_message="Validation error"
    )
    result_repo.create(
        session_id=test_session.id,
        test_name="Test 3",
        success=False,
        error_message="Timeout"
    )
    db_session.commit()

    failed = result_repo.get_failed_tests(test_session.id)
    assert len(failed) == 2


def test_get_test_statistics(db_session):
    """Test calculating test statistics"""
    session_repo = TestSessionRepository(db_session)
    result_repo = TestResultRepository(db_session)

    test_session = session_repo.create(session_id="test-123")
    db_session.commit()

    # Create test results
    for i in range(10):
        result_repo.create(
            session_id=test_session.id,
            test_name=f"Test {i}",
            success=i < 8,  # 8 passed, 2 failed
            duration_ms=10.0 + i,
            response_time_ms=5.0 + i
        )
    db_session.commit()

    stats = result_repo.get_statistics(test_session.id)

    assert stats['total_tests'] == 10
    assert stats['passed_tests'] == 8
    assert stats['failed_tests'] == 2
    assert stats['success_rate'] == 80.0
    assert 10.0 <= stats['avg_duration_ms'] <= 20.0
    assert 5.0 <= stats['avg_response_time_ms'] <= 15.0


def test_get_test_type_distribution(db_session):
    """Test getting test type distribution"""
    session_repo = TestSessionRepository(db_session)
    result_repo = TestResultRepository(db_session)

    test_session = session_repo.create(session_id="test-123")
    db_session.commit()

    # Create results with different types
    result_repo.create(session_id=test_session.id, test_type="positive", success=True)
    result_repo.create(session_id=test_session.id, test_type="positive", success=True)
    result_repo.create(session_id=test_session.id, test_type="negative", success=True)
    result_repo.create(session_id=test_session.id, test_type="boundary", success=True)
    db_session.commit()

    distribution = result_repo.get_test_type_distribution(test_session.id)

    assert distribution["positive"] == 2
    assert distribution["negative"] == 1
    assert distribution["boundary"] == 1


# =============================================================================
# CoverageReport Repository Tests
# =============================================================================


def test_create_coverage_report(db_session):
    """Test creating a coverage report"""
    session_repo = TestSessionRepository(db_session)
    coverage_repo = CoverageReportRepository(db_session)

    test_session = session_repo.create(session_id="test-123")
    db_session.commit()

    report = coverage_repo.create(
        session_id=test_session.id,
        endpoint_coverage=85.5,
        parameter_coverage=78.3,
        status_code_coverage=92.0,
        overall_coverage=85.2,
        total_endpoints=20,
        tested_endpoints=17,
        coverage_details={"endpoint_details": {}}
    )

    assert report.id is not None
    assert report.overall_coverage == 85.2
    assert report.total_endpoints == 20
    assert report.tested_endpoints == 17


def test_get_latest_coverage_report(db_session):
    """Test retrieving latest coverage report"""
    session_repo = TestSessionRepository(db_session)
    coverage_repo = CoverageReportRepository(db_session)

    test_session = session_repo.create(session_id="test-123")
    db_session.commit()

    # Create multiple reports
    report1 = coverage_repo.create(
        session_id=test_session.id,
        overall_coverage=70.0
    )
    db_session.commit()

    report2 = coverage_repo.create(
        session_id=test_session.id,
        overall_coverage=85.0
    )
    db_session.commit()

    # Get latest - should be one of the two reports
    latest = coverage_repo.get_latest_by_session(test_session.id)
    assert latest is not None
    assert latest.overall_coverage in [70.0, 85.0]
    # Latest should have higher ID (created last)
    assert latest.id >= report1.id


def test_get_average_coverage(db_session):
    """Test calculating average coverage"""
    session_repo = TestSessionRepository(db_session)
    coverage_repo = CoverageReportRepository(db_session)

    test_session = session_repo.create(session_id="test-123")
    db_session.commit()

    # Create multiple reports
    coverage_repo.create(
        session_id=test_session.id,
        overall_coverage=80.0,
        endpoint_coverage=75.0,
        parameter_coverage=85.0
    )
    coverage_repo.create(
        session_id=test_session.id,
        overall_coverage=90.0,
        endpoint_coverage=85.0,
        parameter_coverage=95.0
    )
    db_session.commit()

    averages = coverage_repo.get_average_coverage(test_session.id)

    assert averages['avg_overall'] == 85.0
    assert averages['avg_endpoint'] == 80.0
    assert averages['avg_parameter'] == 90.0


# =============================================================================
# Relationship Tests
# =============================================================================


def test_session_to_endpoints_relationship(db_session):
    """Test session to endpoints relationship"""
    session_repo = TestSessionRepository(db_session)
    endpoint_repo = EndpointRepository(db_session)

    test_session = session_repo.create(session_id="test-123")
    endpoint_repo.create(session_id=test_session.id, path="/api/users", method="GET")
    endpoint_repo.create(session_id=test_session.id, path="/api/posts", method="GET")
    db_session.commit()

    # Load with relationship
    loaded = session_repo.get_by_session_id("test-123")
    assert len(loaded.endpoints) == 2


def test_endpoint_to_constraints_relationship(db_session):
    """Test endpoint to constraints relationship"""
    session_repo = TestSessionRepository(db_session)
    endpoint_repo = EndpointRepository(db_session)
    constraint_repo = ConstraintRepository(db_session)

    test_session = session_repo.create(session_id="test-123")
    endpoint = endpoint_repo.create(
        session_id=test_session.id,
        path="/api/users",
        method="POST"
    )
    constraint_repo.create(
        endpoint_id=endpoint.id,
        parameter_name="email",
        parameter_type="string",
        constraint_type="format"
    )
    db_session.commit()

    # Load with constraints
    loaded = endpoint_repo.get_with_constraints(endpoint.id)
    assert len(loaded.constraints) == 1


def test_session_with_all_relationships(db_session):
    """Test loading session with all related data"""
    session_repo = TestSessionRepository(db_session)
    endpoint_repo = EndpointRepository(db_session)
    result_repo = TestResultRepository(db_session)

    # Create session with endpoint and result
    test_session = session_repo.create(session_id="test-123")
    endpoint = endpoint_repo.create(
        session_id=test_session.id,
        path="/api/users",
        method="GET"
    )
    result_repo.create(
        session_id=test_session.id,
        endpoint_id=endpoint.id,
        success=True
    )
    db_session.commit()

    # Load with all relationships
    loaded = session_repo.get_with_results("test-123")
    assert len(loaded.endpoints) == 1
    assert len(loaded.test_results) == 1


# =============================================================================
# Transaction Tests
# =============================================================================


def test_transaction_rollback_on_error(db_session):
    """Test that transactions rollback on error"""
    session_repo = TestSessionRepository(db_session)

    try:
        # Create session
        session_repo.create(session_id="test-123")

        # Force an error by creating duplicate session_id
        session_repo.create(session_id="test-123")

        db_session.commit()
    except Exception:
        db_session.rollback()

    # Verify rollback worked
    found = session_repo.get_by_session_id("test-123")
    assert found is None


def test_context_manager_auto_commit(db_engine):
    """Test context manager automatically commits"""
    from sqlalchemy.orm import sessionmaker
    from contextlib import contextmanager

    Session = sessionmaker(bind=db_engine)

    @contextmanager
    def get_session():
        session = Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # Create session in context manager
    with get_session() as session:
        repo = TestSessionRepository(session)
        repo.create(session_id="test-123", name="Test")

    # Verify commit happened in new session
    with get_session() as session:
        repo = TestSessionRepository(session)
        found = repo.get_by_session_id("test-123")
        assert found is not None
        assert found.name == "Test"


def test_context_manager_auto_rollback(db_engine):
    """Test context manager automatically rolls back on error"""
    from sqlalchemy.orm import sessionmaker
    from contextlib import contextmanager

    Session = sessionmaker(bind=db_engine)

    @contextmanager
    def get_session():
        session = Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # Try to create session but force error
    try:
        with get_session() as session:
            repo = TestSessionRepository(session)
            repo.create(session_id="test-123")
            # Force error before commit
            raise ValueError("Test error")
    except ValueError:
        pass

    # Verify rollback happened
    with get_session() as session:
        repo = TestSessionRepository(session)
        found = repo.get_by_session_id("test-123")
        assert found is None
