"""
Celery Tasks Package
Background task processing for AutoTest-RL
"""

from src.tasks.celery_app import celery_app, get_task_status, revoke_task
from src.tasks.document_tasks import (
    process_document_task,
    analyze_endpoints_task,
    cleanup_document_task,
)
from src.tasks.test_tasks import (
    execute_api_tests_task,
    cleanup_test_session_task,
    test_single_endpoint_task,
    retry_failed_tests_task,
)

__all__ = [
    # Celery app
    "celery_app",
    "get_task_status",
    "revoke_task",
    # Document tasks
    "process_document_task",
    "analyze_endpoints_task",
    "cleanup_document_task",
    # Test tasks
    "execute_api_tests_task",
    "cleanup_test_session_task",
    "test_single_endpoint_task",
    "retry_failed_tests_task",
]
