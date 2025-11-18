# Database Layer Documentation

Complete database persistence layer for AutoTest-RL with SQLAlchemy ORM, repository pattern, and Alembic migrations.

## Architecture

### Components

1. **Models** (`models.py`) - SQLAlchemy ORM models
2. **Configuration** (`config.py`) - Database connection and session management
3. **Repositories** (`repositories/`) - Repository pattern for data access
4. **Migrations** (`/alembic/`) - Alembic database migrations

### Database Schema

```
test_sessions
├── id (PK)
├── session_id (unique)
├── name
├── description
├── status
├── total_tests
├── passed_tests
├── failed_tests
├── metadata_json
└── timestamps

endpoints
├── id (PK)
├── session_id (FK -> test_sessions)
├── path
├── method
├── description
├── operation_id
├── parameters_json
├── request_body_json
├── responses_json
├── requires_auth
└── auth_type

constraints
├── id (PK)
├── endpoint_id (FK -> endpoints)
├── parameter_name
├── parameter_type
├── constraint_type
├── constraint_value
├── is_required
├── confidence
└── source

test_results
├── id (PK)
├── session_id (FK -> test_sessions)
├── endpoint_id (FK -> endpoints)
├── test_name
├── test_type
├── scenario_type
├── strategy
├── request_* (method, path, params, body, headers)
├── response_* (status, body, headers, time)
├── success
├── schema_valid
└── error details

coverage_reports
├── id (PK)
├── session_id (FK -> test_sessions)
├── endpoint_coverage
├── parameter_coverage
├── status_code_coverage
├── scenario_coverage
├── overall_coverage
├── coverage_details_json
└── generated_at

parsed_documents
├── id (PK)
├── document_hash (unique)
├── document_name
├── document_type
├── parsed_content_json
└── cache metadata

learned_constraints
├── id (PK)
├── endpoint_path
├── endpoint_method
├── parameter_name
├── constraint_type
├── confidence
└── observation metadata
```

## Quick Start

### 1. Initialize Database

```bash
# Initialize database with latest schema
./scripts/db_migrate.sh init
```

### 2. Using in Code

```python
from src.database import DatabaseConfig, get_db
from src.database.repositories import TestSessionRepository

# Get database configuration
db_config = DatabaseConfig(database_url="sqlite:///./autotest.db")

# Sync usage with context manager
with db_config.get_session() as session:
    repo = TestSessionRepository(session)

    # Create test session
    test_session = repo.create(
        session_id="test-123",
        name="API Test Run",
        description="Testing user endpoints"
    )

    # Query sessions
    sessions = repo.get_all(limit=10)

    # Session automatically commits on success, rolls back on error

# Async usage
async with db_config.get_async_session() as session:
    from src.database.repositories import AsyncTestSessionRepository

    repo = AsyncTestSessionRepository(session)
    test_session = await repo.create(
        session_id="test-456",
        name="Async Test Run"
    )
```

### 3. FastAPI Integration

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from src.database import get_db
from src.database.repositories import TestSessionRepository

@app.get("/sessions")
def list_sessions(db: Session = Depends(get_db)):
    repo = TestSessionRepository(db)
    return repo.get_all(limit=20)
```

## Repositories

All repositories follow the same pattern with both sync and async implementations.

### TestSessionRepository

```python
from src.database.repositories import TestSessionRepository

repo = TestSessionRepository(session)

# CRUD operations
session = repo.create(session_id="test-1", name="Test Run")
session = repo.get_by_session_id("test-1")
sessions = repo.get_all(limit=10, status="running")
repo.update_status("test-1", "completed")
repo.update_test_counts("test-1", total=100, passed=85, failed=15)
repo.delete("test-1")

# Special queries
session = repo.get_with_results("test-1")  # Eager load results
recent = repo.get_recent_sessions(limit=5)
```

### EndpointRepository

```python
from src.database.repositories import EndpointRepository

repo = EndpointRepository(session)

# Create endpoint
endpoint = repo.create(
    session_id=1,
    path="/api/users",
    method="GET",
    parameters={"page": {"type": "integer"}},
    requires_auth=True,
    auth_type="bearer"
)

# Query endpoints
endpoint = repo.get_by_path_and_method(1, "/api/users", "GET")
endpoints = repo.get_by_session(1)
endpoints = repo.search_by_path_pattern(1, "/api/users%")
count = repo.count_by_session(1)

# With relationships
endpoint = repo.get_with_constraints(endpoint_id)
endpoint = repo.get_with_test_results(endpoint_id)
```

### ConstraintRepository

```python
from src.database.repositories import ConstraintRepository

repo = ConstraintRepository(session)

# Create constraint
constraint = repo.create(
    endpoint_id=1,
    parameter_name="age",
    parameter_type="integer",
    constraint_type="min_value",
    constraint_value="18",
    is_required=True,
    confidence=0.95,
    source="openapi"
)

# Query constraints
constraints = repo.get_by_endpoint(1)
constraints = repo.get_by_parameter(1, "age")
required = repo.get_required_parameters(1)
high_conf = repo.get_by_confidence_threshold(1, min_confidence=0.8)

# Update confidence
repo.update_confidence(constraint_id, 0.98)

# Find or create (upsert pattern)
constraint = repo.find_or_create(
    endpoint_id=1,
    parameter_name="age",
    constraint_type="min_value",
    constraint_value="18",
    confidence=0.95
)
```

### TestResultRepository

```python
from src.database.repositories import TestResultRepository

repo = TestResultRepository(session)

# Create test result
result = repo.create(
    session_id=1,
    endpoint_id=1,
    test_name="Test GET /api/users",
    test_type="positive",
    scenario_type="happy_path",
    request_method="GET",
    request_path="/api/users",
    response_status_code=200,
    success=True
)

# Query results
results = repo.get_by_session(1, limit=50)
results = repo.get_by_endpoint(endpoint_id)
failures = repo.get_failed_tests(1)
positive_tests = repo.get_by_test_type(1, "positive")

# Statistics
stats = repo.get_statistics(1)
# Returns: {total_tests, passed_tests, failed_tests, avg_duration_ms,
#           avg_response_time_ms, success_rate}

distribution = repo.get_test_type_distribution(1)
# Returns: {"positive": 50, "negative": 30, "boundary": 20}

slowest = repo.get_slowest_tests(1, limit=10)
recent_failures = repo.get_recent_failures(hours=24, limit=50)
```

### CoverageReportRepository

```python
from src.database.repositories import CoverageReportRepository

repo = CoverageReportRepository(session)

# Create coverage report
report = repo.create(
    session_id=1,
    endpoint_coverage=85.5,
    parameter_coverage=78.3,
    status_code_coverage=92.0,
    overall_coverage=85.2,
    total_endpoints=20,
    tested_endpoints=17
)

# Query reports
reports = repo.get_by_session(1)
latest = repo.get_latest_by_session(1)
high_coverage = repo.get_high_coverage_reports(min_coverage=80.0)
low_coverage = repo.get_low_coverage_reports(max_coverage=50.0)

# Analytics
trends = repo.get_coverage_trends(1, limit=10)
averages = repo.get_average_coverage(1)
# Returns: {avg_overall, avg_endpoint, avg_parameter, avg_status_code, avg_scenario}
```

## Database Migrations

### Creating Migrations

```bash
# Create new migration with autogenerate
./scripts/db_migrate.sh create "Add email column to users"

# Apply migrations
./scripts/db_migrate.sh upgrade

# Rollback one migration
./scripts/db_migrate.sh downgrade -1

# Rollback to specific version
./scripts/db_migrate.sh downgrade abc123

# View current version
./scripts/db_migrate.sh current

# View migration history
./scripts/db_migrate.sh history
```

### Manual Migration Creation

```bash
# Create empty migration file
alembic revision -m "Custom migration"

# Edit the generated file in alembic/versions/
# Implement upgrade() and downgrade() functions
```

### Migration Best Practices

1. **Always review autogenerated migrations** - Alembic may not catch everything
2. **Test migrations** - Apply and rollback in development first
3. **Provide downgrade paths** - Every migration should be reversible
4. **Use batch mode for SQLite** - Already configured in `env.py`
5. **Backup before production migrations** - Always have a rollback plan

## Configuration

### Environment Variables

```bash
# Database URL (override default)
export DATABASE_URL="postgresql://user:pass@localhost/autotest"
export DATABASE_URL="mysql+pymysql://user:pass@localhost/autotest"
export DATABASE_URL="sqlite:///./autotest.db"  # Default

# Example .env file
DATABASE_URL=postgresql://postgres:password@localhost:5432/autotest_db
```

### Supported Databases

- **SQLite** - Development/testing (default)
- **PostgreSQL** - Production recommended
- **MySQL/MariaDB** - Supported

### Connection Pooling

```python
# Automatic connection pooling
db_config = DatabaseConfig(
    database_url="postgresql://...",
    pool_size=20,           # Max connections in pool
    max_overflow=10,        # Max connections beyond pool_size
    pool_pre_ping=True,     # Test connections before use
    echo=False              # Set True for SQL logging
)
```

## Testing

### In-Memory SQLite for Tests

```python
import pytest
from src.database import DatabaseConfig, Base
from src.database.repositories import TestSessionRepository

@pytest.fixture
def db_session():
    """Provide test database session"""
    config = DatabaseConfig(database_url="sqlite:///:memory:")

    # Create all tables
    Base.metadata.create_all(config.engine)

    with config.get_session() as session:
        yield session

    # Cleanup
    Base.metadata.drop_all(config.engine)

def test_create_session(db_session):
    repo = TestSessionRepository(db_session)
    session = repo.create(session_id="test-1", name="Test")

    assert session.session_id == "test-1"
    assert session.name == "Test"
```

### Transaction Isolation

```python
# Each test gets isolated transaction
@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()
```

## Performance Optimization

### Eager Loading

```python
# Load relationships in single query
session = repo.get_with_results(session_id)  # Uses joinedload
for result in session.test_results:
    print(result.test_name)  # No additional query

# Avoid N+1 queries
from sqlalchemy.orm import joinedload

sessions = session.query(TestSession).options(
    joinedload(TestSession.endpoints),
    joinedload(TestSession.test_results)
).all()
```

### Bulk Operations

```python
# Bulk insert
test_results = [
    TestResult(session_id=1, test_name=f"Test {i}", success=True)
    for i in range(1000)
]
session.bulk_save_objects(test_results)
session.commit()

# Bulk update
session.query(TestResult).filter(
    TestResult.session_id == 1
).update({"success": True})
```

### Indexes

All performance-critical fields have indexes:

- `session_id` - Unique lookups
- `created_at`, `executed_at` - Time-based queries
- `status` - Status filtering
- `path + method` - Endpoint lookups
- `confidence` - Threshold queries

## Maintenance

### Database Backup

```bash
# SQLite
cp autotest.db autotest.db.backup

# PostgreSQL
pg_dump autotest_db > backup.sql

# Restore
psql autotest_db < backup.sql
```

### Database Reset (Development Only)

```bash
# WARNING: Destroys all data!
./scripts/db_migrate.sh reset
```

### Vacuum (SQLite)

```bash
sqlite3 autotest.db "VACUUM;"
```

## Troubleshooting

### Migration Conflicts

```bash
# If migrations are out of sync
./scripts/db_migrate.sh current

# Force to specific version
./scripts/db_migrate.sh stamp head

# Or start fresh (dev only)
./scripts/db_migrate.sh reset
```

### Connection Issues

```python
# Enable SQL logging
config = DatabaseConfig(database_url="...", echo=True)

# Test connection
from sqlalchemy import text
with config.get_session() as session:
    result = session.execute(text("SELECT 1"))
    print("Database connected!")
```

### Foreign Key Issues (SQLite)

SQLite foreign keys are automatically enabled in `config.py`:

```python
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    if isinstance(dbapi_conn, sqlite3.Connection):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
```

## Additional Resources

- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)
