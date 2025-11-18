"""
Celery Application Configuration
Production-ready task queue for background processing
"""
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure
from loguru import logger
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import settings


# ============================================================================
# Celery App Configuration
# ============================================================================

celery_app = Celery(
    "autotest_rl",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Celery Configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Result backend settings
    result_expires=3600,  # 1 hour
    result_persistent=True,

    # Task execution settings
    task_acks_late=True,  # Acknowledge task after completion
    task_reject_on_worker_lost=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes hard limit
    task_soft_time_limit=540,  # 9 minutes soft limit

    # Worker settings
    worker_prefetch_multiplier=1,  # One task at a time
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks

    # Retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,

    # Task routes (optional - for multiple queues)
    task_routes={
        "src.tasks.document_tasks.*": {"queue": "documents"},
        "src.tasks.test_tasks.*": {"queue": "tests"},
    },
)

# Auto-discover tasks from all task modules
celery_app.autodiscover_tasks([
    "src.tasks.document_tasks",
    "src.tasks.test_tasks",
])


# ============================================================================
# Celery Signal Handlers
# ============================================================================

@task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    """Log when task starts"""
    logger.info(f"🚀 Starting task: {task.name} (ID: {task_id})")


@task_postrun.connect
def task_postrun_handler(task_id, task, *args, **kwargs):
    """Log when task completes"""
    logger.info(f"✅ Completed task: {task.name} (ID: {task_id})")


@task_failure.connect
def task_failure_handler(task_id, exception, *args, **kwargs):
    """Log when task fails"""
    logger.error(f"❌ Task failed: {task_id} - {exception}")


# ============================================================================
# Health Check Task
# ============================================================================

@celery_app.task(name="health_check")
def health_check():
    """Simple health check task"""
    return {"status": "healthy", "message": "Celery is working!"}


# ============================================================================
# Task Helper Functions
# ============================================================================

def get_task_status(task_id: str):
    """
    Get status of a Celery task

    Args:
        task_id: Celery task ID

    Returns:
        dict: Task status info
    """
    from celery.result import AsyncResult

    result = AsyncResult(task_id, app=celery_app)

    return {
        "task_id": task_id,
        "state": result.state,
        "status": result.status,
        "result": result.result if result.ready() else None,
        "traceback": result.traceback if result.failed() else None,
    }


def revoke_task(task_id: str, terminate: bool = False):
    """
    Revoke (cancel) a Celery task

    Args:
        task_id: Celery task ID
        terminate: If True, terminate the task immediately

    Returns:
        dict: Revocation status
    """
    celery_app.control.revoke(task_id, terminate=terminate)

    return {
        "task_id": task_id,
        "revoked": True,
        "terminated": terminate,
    }


if __name__ == "__main__":
    # Start Celery worker
    celery_app.start()
