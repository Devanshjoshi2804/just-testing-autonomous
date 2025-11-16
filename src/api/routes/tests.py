"""
Test Execution Routes
Start test sessions, monitor progress, and retrieve results
"""
import asyncio
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
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
from src.executors.test_runner import TestRunner
from src.rag.doc_store import DocumentStore
from src.api.routes.documents import documents_db


router = APIRouter()

# In-memory storage for test sessions (use database/Redis in production)
test_sessions_db: Dict[str, Dict[str, Any]] = {}


async def run_test_session_async(
    session_id: str,
    document_id: str,
    base_url: str,
    endpoints: list,
    max_retries: int,
    use_optimal_order: bool,
    semantic_contexts: dict = None
):
    """
    Background task to run test session asynchronously

    Args:
        session_id: Unique session ID
        document_id: Document being tested
        base_url: API base URL
        endpoints: List of endpoints to test
        max_retries: Max retry attempts
        use_optimal_order: Use optimal testing order
        semantic_contexts: Optional semantic contexts from documentation
    """
    try:
        logger.info(f"Starting background test session: {session_id}")

        # Update session status
        test_sessions_db[session_id]["status"] = TestStatus.PROCESSING
        test_sessions_db[session_id]["updated_at"] = datetime.now()

        # Create document store for RAG
        doc_store = DocumentStore(collection_name=f"doc_{document_id}")

        # Run tests with semantic contexts
        async with TestRunner(
            base_url,
            session_id,
            doc_store,
            max_retries,
            semantic_contexts=semantic_contexts
        ) as runner:
            results = await runner.test_all_endpoints(endpoints, ordered=use_optimal_order)

            # Get summary
            summary = runner.get_results_summary()

            # Update session with results
            test_sessions_db[session_id].update({
                "status": TestStatus.COMPLETED,
                "tested_endpoints": len(results),
                "passed": summary["passed"],
                "failed": summary["failed"],
                "success_rate": summary["success_rate"],
                "total_time": summary["total_time"],
                "avg_time": summary["avg_time"],
                "total_attempts": summary["total_attempts"],
                "results": results,
                "flow_stats": summary["flow_stats"],
                "completed_at": datetime.now(),
                "updated_at": datetime.now()
            })

            logger.info(f"✅ Test session completed: {session_id} ({summary['passed']}/{summary['total_tests']} passed)")

    except Exception as e:
        logger.error(f"Test session failed: {session_id} - {e}", exc_info=True)

        # Mark as failed
        test_sessions_db[session_id].update({
            "status": TestStatus.FAILED,
            "error": str(e),
            "updated_at": datetime.now(),
            "completed_at": datetime.now()
        })


@router.post(
    "/start",
    response_model=TestSessionResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Start Test Execution",
    description="Start testing all endpoints in a document with intelligent retry"
)
async def start_test_execution(
    request: TestExecutionRequest,
    background_tasks: BackgroundTasks
):
    """
    Start test execution for a document

    This endpoint starts an asynchronous test session that will:
    1. Load the document's endpoints from storage
    2. Create a test session with unique ID
    3. Run intelligent API tests in background
    4. Use AI agents for test generation and error fixing
    5. Store results for later retrieval

    The test execution runs in the background. Use the session_id to:
    - Check progress: GET /tests/{session_id}/status
    - Get results: GET /tests/{session_id}/report
    """
    try:
        # Validate document exists
        if request.document_id not in documents_db:
            raise HTTPException(
                status_code=404,
                detail=f"Document not found: {request.document_id}"
            )

        doc_metadata = documents_db[request.document_id]

        # Check if document has endpoints
        endpoints = doc_metadata.get("endpoints", [])
        if not endpoints:
            raise HTTPException(
                status_code=400,
                detail=f"Document has no endpoints to test. Please upload a valid API documentation."
            )

        # Validate base URL
        base_url = doc_metadata.get("base_url")
        if not base_url:
            raise HTTPException(
                status_code=400,
                detail="Document has no base URL. Cannot execute tests."
            )

        # Generate session ID
        session_id = f"session_{uuid.uuid4().hex[:16]}_{int(time.time())}"

        # Create session metadata
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
            "started_at": datetime.now(),
            "updated_at": datetime.now(),
            "completed_at": None,
            "results": [],
            "flow_stats": {},
            "base_url": base_url,
            "endpoints": endpoints
        }

        # Store session
        test_sessions_db[session_id] = session_metadata

        # Calculate estimated duration (rough estimate: 3s per endpoint)
        estimated_duration = len(endpoints) * 3

        logger.info(f"Created test session: {session_id} for document: {request.document_id}")
        logger.info(f"Total endpoints: {len(endpoints)}, Max retries: {request.max_retries}")

        # Get semantic contexts if available
        semantic_contexts = doc_metadata.get("semantic_contexts", {})
        if semantic_contexts:
            logger.info(f"📚 Using semantic contexts for {len(semantic_contexts)} endpoints")

        # Start background task
        background_tasks.add_task(
            run_test_session_async,
            session_id=session_id,
            document_id=request.document_id,
            base_url=base_url,
            endpoints=endpoints,
            max_retries=request.max_retries,
            use_optimal_order=request.use_optimal_order,
            semantic_contexts=semantic_contexts
        )

        logger.info(f"🚀 Started background test execution: {session_id}")

        # Return session response
        return TestSessionResponse(
            session_id=session_id,
            document_id=request.document_id,
            status=TestStatus.PENDING,
            total_endpoints=len(endpoints),
            started_at=session_metadata["started_at"],
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
    summary="Get Test Session Status",
    description="Get real-time status and progress of a test session"
)
async def get_test_status(session_id: str):
    """
    Get test session status and progress

    Returns real-time information about:
    - Current status (pending, processing, completed, failed)
    - Progress percentage
    - Number of tests passed/failed
    - Timestamps

    Use this endpoint to poll for updates while tests are running.
    """
    if session_id not in test_sessions_db:
        raise HTTPException(status_code=404, detail=f"Test session not found: {session_id}")

    try:
        session = test_sessions_db[session_id]

        # Calculate progress
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
            started_at=session["started_at"],
            updated_at=session["updated_at"],
            completed_at=session.get("completed_at")
        )

    except Exception as e:
        logger.error(f"Failed to get test status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{session_id}/report",
    response_model=TestReportResponse,
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
    summary="Get Test Report",
    description="Get complete test results and detailed report"
)
async def get_test_report(session_id: str):
    """
    Get complete test report

    Returns detailed test results including:
    - Overall statistics (passed/failed, success rate, timing)
    - Individual endpoint test results
    - Retry attempts and errors
    - Flow DB statistics

    Note: Only available after test session is completed.
    For in-progress sessions, use GET /tests/{session_id}/status
    """
    if session_id not in test_sessions_db:
        raise HTTPException(status_code=404, detail=f"Test session not found: {session_id}")

    try:
        session = test_sessions_db[session_id]

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
            started_at=session["started_at"],
            completed_at=session.get("completed_at", datetime.now()),
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
    summary="List Test Sessions",
    description="Get list of all test sessions"
)
async def list_test_sessions():
    """List all test sessions"""
    try:
        sessions = []
        for session_id, session in test_sessions_db.items():
            sessions.append({
                "session_id": session_id,
                "document_id": session["document_id"],
                "status": session["status"],
                "total_endpoints": session["total_endpoints"],
                "tested_endpoints": session["tested_endpoints"],
                "passed": session["passed"],
                "failed": session["failed"],
                "started_at": session["started_at"].isoformat(),
                "completed_at": session["completed_at"].isoformat() if session.get("completed_at") else None
            })

        return {
            "sessions": sorted(sessions, key=lambda x: x["started_at"], reverse=True),
            "total": len(sessions)
        }

    except Exception as e:
        logger.error(f"Failed to list test sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/{session_id}",
    summary="Delete Test Session",
    description="Delete a test session and cleanup resources"
)
async def delete_test_session(session_id: str):
    """
    Delete test session and cleanup

    This will:
    - Remove session from storage
    - Delete Flow DB collection for this session
    - Clean up any temporary files
    """
    if session_id not in test_sessions_db:
        raise HTTPException(status_code=404, detail=f"Test session not found: {session_id}")

    try:
        # Get session data
        session = test_sessions_db[session_id]

        # Delete Flow DB collection (if exists)
        try:
            from src.rag.flow_store import FlowStore
            flow_store = FlowStore(session_id=session_id)
            flow_store.cleanup()
            logger.info(f"Cleaned up Flow DB for session: {session_id}")
        except Exception as e:
            logger.warning(f"Could not cleanup Flow DB: {e}")

        # Remove from storage
        del test_sessions_db[session_id]

        logger.info(f"✅ Test session deleted: {session_id}")

        return {
            "message": "Test session deleted successfully",
            "session_id": session_id
        }

    except Exception as e:
        logger.error(f"Failed to delete test session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
