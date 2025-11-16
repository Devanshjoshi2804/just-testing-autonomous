"""
Test Execution Routes with Celery Integration
Production-ready routes using Celery tasks and Redis storage
"""
from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException
from loguru import logger

from src.config import settings
from src.models import (
    TestExecutionRequest,
    TestSessionResponse,
    TestStatusResponse,
    TestReportResponse,
    TestResult,
    TestStatus,
    ErrorResponse
)
from src.storage import DocumentStorage, TestSessionStorage
from src.tasks import (
    execute_api_tests_task,
    cleanup_test_session_task,
    get_task_status,
    revoke_task,
)


router = APIRouter()

# Use Redis for production-ready storage
document_storage = DocumentStorage()
session_storage = TestSessionStorage()


@router.post(
    "/start",
    response_model=TestSessionResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Start Test Execution (Celery)",
    description="Start testing with Celery background tasks and Redis persistence"
)
async def start_test_execution_celery(request: TestExecutionRequest):
    """
    Start test execution using Celery tasks

    This endpoint:
    1. Validates document exists in Redis
    2. Creates test session in Redis
    3. Dispatches Celery task for background execution
    4. Returns session ID and Celery task ID
    5. Tracks progress in Redis

    Benefits over BackgroundTasks:
    - Survives API restarts
    - Better monitoring with Flower
    - Distributed task execution
    - Automatic retries
    - Result persistence
    """
    try:
        # Validate document exists in Redis
        document = document_storage.get_document(request.document_id)
        if not document:
            raise HTTPException(
                status_code=404,
                detail=f"Document not found: {request.document_id}"
            )

        # Check if document has endpoints
        endpoints = document.get("endpoints", [])
        if not endpoints:
            raise HTTPException(
                status_code=400,
                detail="Document has no endpoints to test"
            )

        # Validate base URL
        base_url = document.get("base_url")
        if not base_url:
            raise HTTPException(
                status_code=400,
                detail="Document has no base URL. Cannot execute tests."
            )

        # Generate session ID
        import uuid
        import time
        session_id = f"session_{uuid.uuid4().hex[:16]}_{int(time.time())}"

        # Create session metadata in Redis
        session_metadata = {
            "id": session_id,
            "document_id": request.document_id,
            "status": TestStatus.PENDING,
            "total_endpoints": len(endpoints),
            "tested_endpoints": 0,
            "passed": 0,
            "failed": 0,
            "success_rate": 0.0,
            "total_time": 0.0,
            "avg_time": 0.0,
            "total_attempts": 0,
            "max_retries": request.max_retries,
            "use_optimal_order": request.use_optimal_order,
            "started_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "completed_at": None,
            "celery_task_id": None,  # Will be set below
            "results": [],
            "flow_stats": {},
            "base_url": base_url,
            "endpoints": endpoints
        }

        # Dispatch Celery task
        celery_task = execute_api_tests_task.apply_async(
            kwargs={
                "session_id": session_id,
                "document_id": request.document_id,
                "base_url": base_url,
                "endpoints": endpoints,
                "max_retries": request.max_retries,
                "use_optimal_order": request.use_optimal_order,
            },
            task_id=f"test_{session_id}",
        )

        # Update session with Celery task ID
        session_metadata["celery_task_id"] = celery_task.id

        # Save session to Redis (expires after 24 hours)
        session_storage.save_session(session_id, session_metadata, expire_hours=24)

        # Calculate estimated duration
        estimated_duration = len(endpoints) * 3

        logger.info(f"🚀 Started Celery test execution: {session_id} (Task ID: {celery_task.id})")
        logger.info(f"Total endpoints: {len(endpoints)}, Max retries: {request.max_retries}")

        return TestSessionResponse(
            session_id=session_id,
            document_id=request.document_id,
            status=TestStatus.PENDING,
            total_endpoints=len(endpoints),
            started_at=datetime.fromisoformat(session_metadata["started_at"]),
            estimated_duration=estimated_duration
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start test execution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start test: {str(e)}")


@router.get(
    "/{session_id}/status",
    response_model=TestStatusResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get Test Session Status (Celery)",
    description="Get real-time status from Redis and Celery task"
)
async def get_test_status_celery(session_id: str):
    """
    Get test session status from Redis

    This endpoint:
    1. Retrieves session from Redis
    2. Checks Celery task status
    3. Returns combined status information

    The status is updated by the Celery task during execution.
    """
    # Get session from Redis
    session = session_storage.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Test session not found: {session_id}")

    try:
        # Calculate progress
        total = session["total_endpoints"]
        tested = session["tested_endpoints"]
        progress = (tested / total * 100) if total > 0 else 0

        # Get Celery task status if available
        celery_task_id = session.get("celery_task_id")
        if celery_task_id:
            task_status = get_task_status(celery_task_id)

            # Update session status based on Celery task state
            if task_status["state"] == "PROCESSING":
                # Update from task meta if available
                task_meta = task_status.get("result", {})
                if isinstance(task_meta, dict):
                    session["tested_endpoints"] = task_meta.get("tested_endpoints", tested)
                    session["passed"] = task_meta.get("passed", session.get("passed", 0))
                    session["failed"] = task_meta.get("failed", session.get("failed", 0))

            elif task_status["state"] == "SUCCESS":
                # Task completed - update session from result
                result = task_status.get("result", {})
                if isinstance(result, dict):
                    session.update(result)
                    session["status"] = TestStatus.COMPLETED

                    # Save updated session to Redis
                    session_storage.update_session(session_id, session)

            elif task_status["state"] == "FAILURE":
                session["status"] = TestStatus.FAILED
                session_storage.update_session(session_id, {"status": TestStatus.FAILED})

        # Recalculate progress
        total = session["total_endpoints"]
        tested = session["tested_endpoints"]
        progress = (tested / total * 100) if total > 0 else 0

        return TestStatusResponse(
            session_id=session_id,
            status=session["status"],
            progress=progress,
            total_endpoints=total,
            tested_endpoints=tested,
            passed=session["passed"],
            failed=session["failed"],
            started_at=datetime.fromisoformat(session["started_at"]),
            updated_at=datetime.fromisoformat(session["updated_at"]),
            completed_at=datetime.fromisoformat(session["completed_at"]) if session.get("completed_at") else None
        )

    except Exception as e:
        logger.error(f"Failed to get test status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{session_id}/report",
    response_model=TestReportResponse,
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
    summary="Get Test Report (Celery)",
    description="Get complete test results from Redis"
)
async def get_test_report_celery(session_id: str):
    """
    Get complete test report from Redis

    The report is stored in Redis by the Celery task upon completion.
    """
    # Get session from Redis
    session = session_storage.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Test session not found: {session_id}")

    try:
        # Check if completed
        if session["status"] not in [TestStatus.COMPLETED, TestStatus.FAILED]:
            raise HTTPException(
                status_code=400,
                detail=f"Test session still in progress. Current status: {session['status']}. "
                       f"Use GET /tests/{session_id}/status to check progress."
            )

        # Convert results to TestResult models
        results = [
            TestResult(
                endpoint=r.get("endpoint", ""),
                method=r.get("method", ""),
                url=r.get("url", ""),
                status_code=r.get("status_code", 0),
                success=r.get("success", False),
                attempts=r.get("attempts", 1),
                elapsed_time=r.get("elapsed_time", 0.0),
                final_payload=r.get("final_payload", {}),
                response=r.get("response", {}),
                error=r.get("error")
            )
            for r in session.get("results", [])
        ]

        return TestReportResponse(
            session_id=session_id,
            document_id=session["document_id"],
            status=session["status"],
            total_tests=session["total_endpoints"],
            passed=session["passed"],
            failed=session["failed"],
            success_rate=session["success_rate"],
            total_time=session["total_time"],
            avg_time=session["avg_time"],
            total_attempts=session["total_attempts"],
            started_at=datetime.fromisoformat(session["started_at"]),
            completed_at=datetime.fromisoformat(session.get("completed_at", session["started_at"])),
            results=results,
            flow_stats=session.get("flow_stats", {})
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get test report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/",
    summary="List Test Sessions (Celery)",
    description="Get list of all test sessions from Redis"
)
async def list_test_sessions_celery(limit: int = 100):
    """List all test sessions from Redis storage"""
    try:
        # Cleanup expired sessions first
        session_storage.cleanup_expired_sessions()

        # Get sessions from Redis
        sessions = session_storage.list_sessions(limit=limit)

        # Convert to response format
        response_sessions = []
        for session in sessions:
            response_sessions.append({
                "session_id": session["id"],
                "document_id": session["document_id"],
                "status": session["status"],
                "total_endpoints": session["total_endpoints"],
                "tested_endpoints": session["tested_endpoints"],
                "passed": session["passed"],
                "failed": session["failed"],
                "started_at": session["started_at"],
                "completed_at": session.get("completed_at"),
                "celery_task_id": session.get("celery_task_id")
            })

        return {
            "sessions": response_sessions,
            "total": len(response_sessions)
        }

    except Exception as e:
        logger.error(f"Failed to list test sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/{session_id}",
    summary="Delete Test Session (Celery)",
    description="Delete test session from Redis and revoke Celery task"
)
async def delete_test_session_celery(session_id: str, revoke_if_running: bool = False):
    """
    Delete test session and cleanup

    This will:
    - Revoke Celery task if still running (optional)
    - Remove session from Redis
    - Delete Flow DB collection
    - Clean up any temporary files
    """
    # Get session from Redis
    session = session_storage.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Test session not found: {session_id}")

    try:
        # Revoke Celery task if requested and still running
        celery_task_id = session.get("celery_task_id")
        if celery_task_id and revoke_if_running:
            task_status = get_task_status(celery_task_id)
            if task_status["state"] in ["PENDING", "PROCESSING"]:
                revoke_task(celery_task_id, terminate=True)
                logger.info(f"Revoked Celery task: {celery_task_id}")

        # Delete Flow DB collection (async task)
        cleanup_task = cleanup_test_session_task.apply_async(
            args=[session_id],
            countdown=2  # Wait 2 seconds before cleanup
        )

        # Delete session from Redis
        session_storage.delete_session(session_id)

        logger.info(f"✅ Test session deleted: {session_id}")

        return {
            "message": "Test session deleted successfully",
            "session_id": session_id,
            "cleanup_task_id": cleanup_task.id
        }

    except Exception as e:
        logger.error(f"Failed to delete test session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{session_id}/cancel",
    summary="Cancel Running Test",
    description="Cancel a running Celery test task"
)
async def cancel_test_execution(session_id: str):
    """
    Cancel a running test execution

    This will:
    - Revoke the Celery task
    - Update session status to FAILED
    - Keep partial results
    """
    # Get session from Redis
    session = session_storage.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Test session not found: {session_id}")

    try:
        # Check if task is running
        celery_task_id = session.get("celery_task_id")
        if not celery_task_id:
            raise HTTPException(status_code=400, detail="No Celery task associated with this session")

        task_status = get_task_status(celery_task_id)
        if task_status["state"] not in ["PENDING", "PROCESSING"]:
            raise HTTPException(
                status_code=400,
                detail=f"Task is not running (state: {task_status['state']})"
            )

        # Revoke task
        revoke_task(celery_task_id, terminate=True)

        # Update session status
        session_storage.update_session(session_id, {
            "status": TestStatus.FAILED,
            "updated_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat(),
        })

        logger.info(f"✅ Cancelled test execution: {session_id}")

        return {
            "message": "Test execution cancelled",
            "session_id": session_id,
            "celery_task_id": celery_task_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel test execution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
