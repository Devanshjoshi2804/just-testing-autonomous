"""
Test Execution Celery Tasks
Background tasks for API testing with intelligent retry
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import asyncio
from celery import Task
from loguru import logger
from typing import Dict, Any, List
import time
from datetime import datetime

from src.tasks.celery_app import celery_app
from src.executors.test_runner import TestRunner
from src.rag.doc_store import DocumentStore
from src.rag.flow_store import FlowStore


class TestExecutionTask(Task):
    """Base task for test execution with progress tracking"""

    def on_success(self, retval, task_id, args, kwargs):
        """Called on task success"""
        logger.info(f"✅ Test execution {task_id} completed successfully")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called on task failure"""
        logger.error(f"❌ Test execution {task_id} failed: {exc}")


@celery_app.task(
    name="execute_api_tests",
    base=TestExecutionTask,
    bind=True,
    max_retries=1,
    time_limit=600,  # 10 minutes
)
def execute_api_tests_task(
    self,
    session_id: str,
    document_id: str,
    base_url: str,
    endpoints: List[Dict[str, Any]],
    max_retries: int = 3,
    use_optimal_order: bool = True,
) -> Dict[str, Any]:
    """
    Execute API tests for all endpoints with intelligent retry

    This task:
    1. Creates TestRunner with session ID
    2. Executes tests for all endpoints
    3. Uses AI agents for intelligent retry
    4. Stores results in Flow DB
    5. Returns complete test report

    Args:
        self: Celery task instance
        session_id: Unique test session ID
        document_id: Document being tested
        base_url: API base URL
        endpoints: List of endpoints to test
        max_retries: Max retry attempts per endpoint
        use_optimal_order: Use optimal testing order

    Returns:
        dict: Complete test results and statistics
    """
    try:
        logger.info(
            f"🧪 Starting test execution: {session_id} "
            f"({len(endpoints)} endpoints, max_retries={max_retries})"
        )

        # Update task state
        self.update_state(
            state="PROCESSING",
            meta={
                "session_id": session_id,
                "step": "initializing",
                "progress": 0,
                "total_endpoints": len(endpoints),
                "tested_endpoints": 0,
                "passed": 0,
                "failed": 0,
                "message": "Initializing test execution...",
            },
        )

        start_time = time.time()

        # Create document store for RAG
        doc_store = DocumentStore(collection_name=f"doc_{document_id}")

        # Run async tests
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Execute tests with progress callback
            async def run_tests():
                async with TestRunner(
                    base_url, session_id, doc_store, max_retries
                ) as runner:
                    # Test all endpoints with progress tracking
                    results = []
                    for i, endpoint in enumerate(
                        (
                            runner._get_ordered_endpoints(endpoints)
                            if use_optimal_order
                            else endpoints
                        )
                    ):
                        # Update progress
                        progress = int((i / len(endpoints)) * 100)

                        # Test endpoint
                        result = await runner.test_endpoint(endpoint)
                        results.append(result)

                        # Update task state with progress
                        passed = sum(1 for r in results if r.get("success", False))
                        failed = len(results) - passed

                        self.update_state(
                            state="PROCESSING",
                            meta={
                                "session_id": session_id,
                                "step": "testing",
                                "progress": progress,
                                "total_endpoints": len(endpoints),
                                "tested_endpoints": i + 1,
                                "passed": passed,
                                "failed": failed,
                                "current_endpoint": endpoint.get("path", ""),
                                "message": f"Testing {endpoint.get('method', '')} {endpoint.get('path', '')}...",
                            },
                        )

                        logger.info(
                            f"Progress: {i+1}/{len(endpoints)} - "
                            f"{endpoint.get('method', '')} {endpoint.get('path', '')} "
                            f"[{'✅' if result.get('success') else '❌'}]"
                        )

                    # Get summary
                    summary = runner.get_results_summary()

                    return {"results": results, "summary": summary}

            # Run async function
            test_data = loop.run_until_complete(run_tests())
            results = test_data["results"]
            summary = test_data["summary"]

        finally:
            loop.close()

        # Calculate final statistics
        total_time = time.time() - start_time

        final_result = {
            "session_id": session_id,
            "document_id": document_id,
            "status": "completed",
            "total_endpoints": len(endpoints),
            "tested_endpoints": len(results),
            "passed": summary["passed"],
            "failed": summary["failed"],
            "success_rate": summary["success_rate"],
            "total_time": total_time,
            "avg_time": summary.get("avg_time", 0),
            "total_attempts": summary.get("total_attempts", 0),
            "results": results,
            "flow_stats": summary.get("flow_stats", {}),
            "started_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat(),
        }

        logger.info(
            f"✅ Test execution complete: {session_id} - "
            f"{summary['passed']}/{summary['total_tests']} passed "
            f"({summary['success_rate']:.1f}% success rate, {total_time:.2f}s)"
        )

        return final_result

    except Exception as e:
        logger.exception(f"Error executing tests for session {session_id}: {e}")

        # Update state to FAILURE
        self.update_state(
            state="FAILURE",
            meta={
                "session_id": session_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )

        raise


@celery_app.task(name="cleanup_test_session")
def cleanup_test_session_task(session_id: str):
    """
    Cleanup test session resources

    Deletes Flow DB collection and associated data

    Args:
        session_id: Test session ID to cleanup

    Returns:
        dict: Cleanup status
    """
    try:
        logger.info(f"🧹 Cleaning up test session: {session_id}")

        # Cleanup FlowStore
        flow_store = FlowStore(session_id=session_id)
        flow_store.cleanup()

        logger.info(f"✅ Test session cleanup complete: {session_id}")

        return {"session_id": session_id, "status": "cleaned_up"}

    except Exception as e:
        logger.exception(f"Error cleaning up test session: {e}")
        raise


@celery_app.task(name="test_single_endpoint")
def test_single_endpoint_task(
    session_id: str,
    document_id: str,
    base_url: str,
    endpoint: Dict[str, Any],
    max_retries: int = 3,
) -> Dict[str, Any]:
    """
    Test a single API endpoint

    Args:
        session_id: Test session ID
        document_id: Document ID
        base_url: API base URL
        endpoint: Endpoint configuration
        max_retries: Max retry attempts

    Returns:
        dict: Test result for the endpoint
    """
    try:
        logger.info(
            f"🧪 Testing single endpoint: {endpoint.get('method', '')} "
            f"{endpoint.get('path', '')} (session: {session_id})"
        )

        # Create document store
        doc_store = DocumentStore(collection_name=f"doc_{document_id}")

        # Run async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:

            async def run_test():
                async with TestRunner(
                    base_url, session_id, doc_store, max_retries
                ) as runner:
                    result = await runner.test_endpoint(endpoint)
                    return result

            result = loop.run_until_complete(run_test())

        finally:
            loop.close()

        logger.info(
            f"{'✅' if result.get('success') else '❌'} "
            f"Test complete: {endpoint.get('method', '')} {endpoint.get('path', '')}"
        )

        return result

    except Exception as e:
        logger.exception(f"Error testing endpoint: {e}")
        raise


@celery_app.task(name="retry_failed_tests")
def retry_failed_tests_task(
    session_id: str,
    document_id: str,
    base_url: str,
    failed_results: List[Dict[str, Any]],
    max_retries: int = 3,
) -> Dict[str, Any]:
    """
    Retry only failed tests from a previous session

    Args:
        session_id: Original test session ID
        document_id: Document ID
        base_url: API base URL
        failed_results: List of failed test results to retry
        max_retries: Max retry attempts

    Returns:
        dict: Retry results
    """
    try:
        logger.info(
            f"🔄 Retrying {len(failed_results)} failed tests for session: {session_id}"
        )

        # Extract endpoints from failed results
        endpoints = [
            {
                "path": result.get("endpoint", "").split(" ", 1)[-1],
                "method": result.get("method", ""),
            }
            for result in failed_results
        ]

        # Create new session ID for retry
        retry_session_id = f"{session_id}_retry_{int(time.time())}"

        # Execute retry tests
        doc_store = DocumentStore(collection_name=f"doc_{document_id}")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:

            async def run_retries():
                async with TestRunner(
                    base_url, retry_session_id, doc_store, max_retries
                ) as runner:
                    results = await runner.test_all_endpoints(endpoints, ordered=False)
                    summary = runner.get_results_summary()
                    return {"results": results, "summary": summary}

            retry_data = loop.run_until_complete(run_retries())

        finally:
            loop.close()

        logger.info(
            f"✅ Retry complete: {retry_data['summary']['passed']} passed, "
            f"{retry_data['summary']['failed']} still failed"
        )

        return {
            "original_session_id": session_id,
            "retry_session_id": retry_session_id,
            "total_retried": len(endpoints),
            "passed": retry_data["summary"]["passed"],
            "failed": retry_data["summary"]["failed"],
            "results": retry_data["results"],
        }

    except Exception as e:
        logger.exception(f"Error retrying failed tests: {e}")
        raise
