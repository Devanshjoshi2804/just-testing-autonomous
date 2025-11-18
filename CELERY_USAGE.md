# Celery Task Queue Integration

Complete guide for using Celery tasks for production-ready background processing.

## Overview

AutoTest-RL supports two modes for background task execution:

1. **FastAPI BackgroundTasks** (Default) - Simple, embedded in API process
2. **Celery Tasks** (Production) - Distributed, scalable, persistent

## When to Use Celery

Use Celery tasks when you need:

- ✅ **Task persistence** - Tasks survive API restarts
- ✅ **Distributed execution** - Multiple workers across machines
- ✅ **Advanced monitoring** - Flower dashboard for task tracking
- ✅ **Automatic retries** - Built-in retry mechanisms
- ✅ **Priority queues** - Different queues for different task types
- ✅ **Scheduled tasks** - Periodic task execution
- ✅ **Resource isolation** - Heavy tasks don't block API

Use FastAPI BackgroundTasks when:

- ⚡ **Quick tasks** - Tasks complete in < 30 seconds
- ⚡ **Development** - Simpler setup, fewer moving parts
- ⚡ **Small scale** - Single instance deployment

---

## Architecture

### System Components

```
┌─────────────────┐
│   FastAPI API   │ ─────► [Dispatch Celery Task]
└────────┬────────┘
         │
         ├─────► Redis (Broker + Result Backend)
         │
         └─────► Celery Workers ─────► ChromaDB
                                 └────► Ollama LLM
```

### Data Flow

1. **API receives request** → Creates task in Redis
2. **Celery worker picks up task** → Executes background processing
3. **Task updates progress** → Stores state in Redis
4. **API polls status** → Reads from Redis
5. **Task completes** → Final results stored in Redis

---

## Setup

### 1. Start All Services

```bash
# Start API, Redis, Celery workers, Flower
docker compose up -d

# Verify services
docker compose ps
```

Expected services:
- `api` - FastAPI application
- `redis` - Task broker
- `celery_worker` - Task executor
- `celery_beat` - Scheduled tasks
- `flower` - Monitoring UI
- `ollama` - Local LLM
- `chromadb` - Vector database

### 2. Verify Celery is Running

```bash
# Check Celery worker logs
docker compose logs -f celery_worker

# You should see:
# ✅ Connected to redis://redis:6379/0
# ✅ Tasks registered: process_document, execute_api_tests, ...
```

### 3. Access Flower Monitoring

```bash
# Open Flower dashboard
open http://localhost:5555

# Or use curl
curl http://localhost:5555/api/workers
```

---

## Celery Tasks

### Document Processing Tasks

#### `process_document_task`

Processes uploaded API documentation in the background.

**What it does:**
1. Parses document (PDF/JSON/YAML)
2. Validates API documentation
3. Chunks text for RAG
4. Stores in ChromaDB
5. Analyzes endpoints with AI
6. Returns processing results

**Usage:**
```python
from src.tasks import process_document_task

# Dispatch task
task = process_document_task.apply_async(
    kwargs={
        "document_id": "doc_123",
        "file_path": "/uploads/api_doc.pdf",
        "base_url": "https://api.example.com"
    }
)

# Get task ID
task_id = task.id  # e.g., "process_document_abc123"

# Check status
from src.tasks import get_task_status
status = get_task_status(task_id)
print(status)
# {
#   "task_id": "process_document_abc123",
#   "state": "PROCESSING",
#   "status": "PROCESSING",
#   "result": {"step": "analyzing", "progress": 80, ...}
# }
```

**Progress States:**
- `PENDING` - Task queued, waiting to start
- `PROCESSING` - Task running
  - Step: `parsing` (10%)
  - Step: `validating` (25%)
  - Step: `chunking` (40%)
  - Step: `storing` (60%)
  - Step: `analyzing` (80%)
- `SUCCESS` - Task completed
- `FAILURE` - Task failed (will retry up to 3 times)

#### `analyze_endpoints_task`

Extract endpoints from document text using AI.

**Usage:**
```python
from src.tasks import analyze_endpoints_task

task = analyze_endpoints_task.apply_async(
    args=["doc_123", "API documentation text...", "https://api.example.com"]
)
```

#### `cleanup_document_task`

Cleanup document resources (ChromaDB, files).

**Usage:**
```python
from src.tasks import cleanup_document_task

task = cleanup_document_task.apply_async(args=["doc_123"])
```

---

### Test Execution Tasks

#### `execute_api_tests_task`

Execute comprehensive API testing with intelligent retry.

**What it does:**
1. Creates TestRunner with session ID
2. Tests all endpoints in optimal order
3. Uses AI agents for intelligent retry
4. Stores results in Flow DB and Redis
5. Returns complete test report

**Usage:**
```python
from src.tasks import execute_api_tests_task

task = execute_api_tests_task.apply_async(
    kwargs={
        "session_id": "session_xyz",
        "document_id": "doc_123",
        "base_url": "https://api.example.com",
        "endpoints": [...],  # List of endpoints
        "max_retries": 3,
        "use_optimal_order": True
    }
)
```

**Progress Updates:**
```python
status = get_task_status(task.id)
# {
#   "state": "PROCESSING",
#   "result": {
#     "session_id": "session_xyz",
#     "progress": 58,
#     "tested_endpoints": 7,
#     "total_endpoints": 12,
#     "passed": 6,
#     "failed": 1,
#     "current_endpoint": "/users",
#     "message": "Testing GET /users..."
#   }
# }
```

#### `test_single_endpoint_task`

Test a single API endpoint.

**Usage:**
```python
from src.tasks import test_single_endpoint_task

task = test_single_endpoint_task.apply_async(
    kwargs={
        "session_id": "session_xyz",
        "document_id": "doc_123",
        "base_url": "https://api.example.com",
        "endpoint": {"path": "/users", "method": "GET"},
        "max_retries": 3
    }
)
```

#### `retry_failed_tests_task`

Retry only failed tests from a previous session.

**Usage:**
```python
from src.tasks import retry_failed_tests_task

task = retry_failed_tests_task.apply_async(
    kwargs={
        "session_id": "session_xyz",
        "document_id": "doc_123",
        "base_url": "https://api.example.com",
        "failed_results": [...],  # List of failed results
        "max_retries": 3
    }
)
```

#### `cleanup_test_session_task`

Cleanup test session resources (Flow DB).

**Usage:**
```python
from src.tasks import cleanup_test_session_task

task = cleanup_test_session_task.apply_async(args=["session_xyz"])
```

---

## API Endpoints (Celery-based)

### Alternative Routes with Celery

The system provides alternative routes that use Celery tasks:

**File:** `src/api/routes/tests_celery.py`

**Endpoints:**
- `POST /api/v1/tests/start` - Start test with Celery
- `GET /api/v1/tests/{id}/status` - Get status from Redis
- `GET /api/v1/tests/{id}/report` - Get report from Redis
- `GET /api/v1/tests/` - List sessions from Redis
- `DELETE /api/v1/tests/{id}` - Delete session and revoke task
- `POST /api/v1/tests/{id}/cancel` - Cancel running test

### Using Celery Routes

To use Celery routes instead of BackgroundTasks routes:

**Option 1: Replace router in main.py**

```python
# In src/api/main.py, replace:
from src.api.routes import tests_router

# With:
from src.api.routes.tests_celery import router as tests_router
```

**Option 2: Add as separate prefix**

```python
# In src/api/main.py
from src.api.routes.tests_celery import router as tests_celery_router

app.include_router(
    tests_celery_router,
    prefix="/api/v1/tests-celery",
    tags=["Tests (Celery)"]
)
```

Now you have both:
- `/api/v1/tests/*` - FastAPI BackgroundTasks
- `/api/v1/tests-celery/*` - Celery tasks

---

## Redis Storage

### Document Storage

**Features:**
- Persistent document metadata
- Fast lookups
- Atomic operations
- Auto-indexing

**Usage:**
```python
from src.storage import DocumentStorage

doc_storage = DocumentStorage()

# Save document
doc_storage.save_document("doc_123", {
    "id": "doc_123",
    "filename": "api_doc.pdf",
    "doc_type": "pdf",
    "base_url": "https://api.example.com",
    "endpoints": [...],
    "uploaded_at": "2025-01-15T10:00:00Z"
})

# Get document
doc = doc_storage.get_document("doc_123")

# List all documents
docs = doc_storage.list_documents()

# Delete document
doc_storage.delete_document("doc_123")

# Check existence
exists = doc_storage.document_exists("doc_123")

# Get count
count = doc_storage.get_document_count()
```

### Test Session Storage

**Features:**
- Automatic expiration (24 hours)
- Progress tracking
- Result persistence
- Session cleanup

**Usage:**
```python
from src.storage import TestSessionStorage

session_storage = TestSessionStorage()

# Save session (expires in 24 hours)
session_storage.save_session("session_xyz", {
    "id": "session_xyz",
    "document_id": "doc_123",
    "status": "processing",
    "total_endpoints": 12,
    "tested_endpoints": 5,
    "passed": 4,
    "failed": 1,
    "started_at": "2025-01-15T10:00:00Z"
}, expire_hours=24)

# Update session
session_storage.update_session("session_xyz", {
    "tested_endpoints": 10,
    "passed": 8,
    "failed": 2
})

# Get session
session = session_storage.get_session("session_xyz")

# List sessions (newest first, limit 100)
sessions = session_storage.list_sessions(limit=100)

# Delete session
session_storage.delete_session("session_xyz")

# Cleanup expired sessions
cleaned = session_storage.cleanup_expired_sessions()
```

---

## Monitoring with Flower

### Access Flower Dashboard

```bash
# Open Flower web UI
open http://localhost:5555
```

### Flower Features

1. **Tasks View** - See all tasks (pending, active, completed, failed)
2. **Workers View** - Monitor Celery workers
3. **Task Details** - Inspect individual tasks
4. **Broker** - Redis connection status
5. **Monitor** - Real-time task execution

### Flower API

```bash
# Get workers
curl http://localhost:5555/api/workers

# Get tasks
curl http://localhost:5555/api/tasks

# Get specific task
curl http://localhost:5555/api/task/info/task_id_here
```

---

## Task Management

### Check Task Status

```python
from src.tasks import get_task_status

status = get_task_status("task_id_123")
print(status)
# {
#   "task_id": "task_id_123",
#   "state": "SUCCESS",
#   "status": "SUCCESS",
#   "result": {...},
#   "traceback": None
# }
```

### Revoke (Cancel) Task

```python
from src.tasks import revoke_task

# Soft revoke (task won't start if not started yet)
result = revoke_task("task_id_123", terminate=False)

# Hard revoke (terminate running task)
result = revoke_task("task_id_123", terminate=True)
```

### Retry Failed Task

```python
# Celery will automatically retry failed tasks up to 3 times
# You can manually retry:
from src.tasks import execute_api_tests_task

task = execute_api_tests_task.retry(
    args=[...],
    countdown=60  # Retry in 60 seconds
)
```

---

## Celery CLI Commands

### Inspect Workers

```bash
# List active workers
docker compose exec celery_worker celery -A src.tasks.celery_app inspect active

# List registered tasks
docker compose exec celery_worker celery -A src.tasks.celery_app inspect registered

# Worker stats
docker compose exec celery_worker celery -A src.tasks.celery_app inspect stats
```

### Control Workers

```bash
# Shutdown worker gracefully
docker compose exec celery_worker celery -A src.tasks.celery_app control shutdown

# Restart worker
docker compose restart celery_worker

# Increase worker pool size
docker compose exec celery_worker celery -A src.tasks.celery_app control pool_grow 2
```

### Purge Tasks

```bash
# Clear all pending tasks from queue
docker compose exec celery_worker celery -A src.tasks.celery_app purge

# This is destructive - use with caution!
```

---

## Configuration

### Celery Settings (src/config.py)

```python
# Broker & Backend
CELERY_BROKER_URL = "redis://redis:6379/0"
CELERY_RESULT_BACKEND = "redis://redis:6379/0"

# Task settings
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "UTC"
CELERY_ENABLE_UTC = True

# Execution limits
CELERY_TASK_TIME_LIMIT = 600  # 10 minutes hard limit
CELERY_TASK_TRACK_STARTED = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # One task at a time
```

### Task Queues

Different task types use different queues:

```python
# Configured in src/tasks/celery_app.py
task_routes = {
    "src.tasks.document_tasks.*": {"queue": "documents"},
    "src.tasks.test_tasks.*": {"queue": "tests"},
}
```

Start workers for specific queues:

```bash
# Worker for document tasks only
celery -A src.tasks.celery_app worker -Q documents -n doc_worker

# Worker for test tasks only
celery -A src.tasks.celery_app worker -Q tests -n test_worker
```

---

## Production Best Practices

### 1. Use Dedicated Workers

```yaml
# docker-compose.yml
celery_worker_documents:
  command: celery -A src.tasks.celery_app worker -Q documents --concurrency=2

celery_worker_tests:
  command: celery -A src.tasks.celery_app worker -Q tests --concurrency=4
```

### 2. Monitor Task Failures

```python
# Set up failure alerting in src/tasks/celery_app.py
@task_failure.connect
def task_failure_handler(task_id, exception, *args, **kwargs):
    # Send alert (email, Slack, etc.)
    send_alert(f"Task {task_id} failed: {exception}")
```

### 3. Set Proper Timeouts

```python
# In task definition
@celery_app.task(
    time_limit=300,  # 5 minutes hard limit
    soft_time_limit=270  # 4.5 minutes soft limit
)
def my_task():
    # Task code
    pass
```

### 4. Use Result Expiration

```python
# In src/tasks/celery_app.py
celery_app.conf.update(
    result_expires=3600,  # Results expire after 1 hour
)
```

### 5. Enable Persistent Results

Results are stored in Redis and survive worker restarts.

---

## Troubleshooting

### Tasks Not Executing

```bash
# Check if Celery worker is running
docker compose ps celery_worker

# Check worker logs
docker compose logs -f celery_worker

# Verify Redis connection
docker compose exec celery_worker celery -A src.tasks.celery_app inspect ping
```

### Tasks Stuck in PENDING

```bash
# Check if task is in queue
docker compose exec redis redis-cli KEYS "celery-task-meta-*"

# Purge and restart
docker compose exec celery_worker celery -A src.tasks.celery_app purge
docker compose restart celery_worker
```

### Memory Issues

```bash
# Check worker memory
docker stats celery_worker

# Restart worker after N tasks
# In celery_app.py:
worker_max_tasks_per_child = 100  # Restart after 100 tasks
```

---

## Comparison: BackgroundTasks vs Celery

| Feature | BackgroundTasks | Celery |
|---------|----------------|--------|
| Setup | Simple | Complex |
| Persistence | No | Yes (Redis) |
| Survives restart | No | Yes |
| Distributed | No | Yes |
| Monitoring | Basic | Flower |
| Retries | Manual | Automatic |
| Priority queues | No | Yes |
| Scheduled tasks | No | Yes (Beat) |
| Resource isolation | No | Yes |
| Best for | Development | Production |

---

## Next Steps

1. **Enable Celery routes** - Switch to Celery-based routes in production
2. **Setup monitoring** - Configure Flower alerts
3. **Optimize workers** - Tune concurrency and queue settings
4. **Add scheduled tasks** - Use Celery Beat for periodic cleanup
5. **Scale horizontally** - Add more workers across machines

For more information, see:
- Celery Documentation: https://docs.celeryproject.org/
- Flower Documentation: https://flower.readthedocs.io/
