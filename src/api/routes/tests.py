"""
Test Execution Routes
Start test sessions, monitor progress, and retrieve results
"""
import asyncio
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path as FilePath

from fastapi import APIRouter, HTTPException, BackgroundTasks, Path, Request
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import ValidationError

from src.config import settings
from src.models import (
    TestExecutionRequest,
    TestSessionResponse,
    TestStatusResponse,
    TestReportResponse,
    TestResult,
    TestStatus,
    ErrorResponse,
    validate_session_id,
    validate_document_id
)
from src.api.middleware.rate_limiter import rate_limit
from src.executors.test_runner import TestRunner
from src.rag.doc_store import DocumentStore
from src.api.routes.documents import documents_db


router = APIRouter()

# In-memory storage for test sessions (use database/Redis in production)
test_sessions_db: Dict[str, Dict[str, Any]] = {}

# Thread-safety: Locks for concurrent access to test sessions
# Each session gets its own lock to prevent race conditions
from asyncio import Lock
from collections import defaultdict

class SessionLockManager:
    """
    Manages locks for test sessions to prevent race conditions

    Provides thread-safe access to test session data with automatic
    lock creation and cleanup.
    """
    def __init__(self):
        self._locks: Dict[str, Lock] = {}
        self._lock_creation_lock = Lock()  # Meta-lock for lock creation

    async def get_lock(self, session_id: str) -> Lock:
        """Get or create a lock for a session"""
        if session_id not in self._locks:
            async with self._lock_creation_lock:
                # Double-check pattern to avoid race in lock creation
                if session_id not in self._locks:
                    self._locks[session_id] = Lock()
        return self._locks[session_id]

    def cleanup_lock(self, session_id: str):
        """Remove lock after session completion"""
        if session_id in self._locks:
            del self._locks[session_id]

# Global lock manager instance
session_locks = SessionLockManager()


# Helper functions for thread-safe session access
async def get_session_safe(session_id: str) -> Dict[str, Any]:
    """
    Thread-safe session retrieval

    Args:
        session_id: Session ID to retrieve

    Returns:
        Session data dictionary (copy to prevent modifications outside lock)

    Raises:
        HTTPException: If session not found
    """
    if session_id not in test_sessions_db:
        raise HTTPException(status_code=404, detail=f"Test session not found: {session_id}")

    lock = await session_locks.get_lock(session_id)
    async with lock:
        # Return a copy to prevent external modifications
        return test_sessions_db[session_id].copy()


async def run_test_session_async(
    session_id: str,
    document_id: str,
    base_url: str,
    endpoints: list,
    max_retries: int,
    use_optimal_order: bool,
    comprehensive_mode: bool = True,
    semantic_contexts: dict = None,
    parameter_constraints: dict = None
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
        comprehensive_mode: Enable comprehensive test generation
        semantic_contexts: Optional semantic contexts from documentation
        parameter_constraints: Optional parameter constraints for test data generation
    """
    # THREAD-SAFETY: Acquire lock for this session to prevent race conditions
    lock = await session_locks.get_lock(session_id)

    try:
        logger.info(f"Starting background test session: {session_id}")

        # Update session status (thread-safe)
        async with lock:
            test_sessions_db[session_id]["status"] = TestStatus.PROCESSING
            test_sessions_db[session_id]["updated_at"] = datetime.now()

        # Create document store for RAG
        doc_store = DocumentStore(collection_name=f"doc_{document_id}")

        # Run tests with semantic contexts, comprehensive mode, and constraints
        async with TestRunner(
            base_url,
            session_id,
            doc_store,
            max_retries,
            semantic_contexts=semantic_contexts,
            comprehensive_mode=comprehensive_mode,
            parameter_constraints=parameter_constraints
        ) as runner:
            results = await runner.test_all_endpoints(endpoints, ordered=use_optimal_order)

            # Get summary
            summary = runner.get_results_summary()

            # Update session with results (thread-safe)
            async with lock:
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
                    "healing_report": summary.get("healing_report", {}),
                    "completed_at": datetime.now(),
                    "updated_at": datetime.now()
                })

            logger.info(f"✅ Test session completed: {session_id} ({summary['passed']}/{summary['total_tests']} passed)")

    except Exception as e:
        logger.error(f"Test session failed: {session_id} - {e}", exc_info=True)

        # Mark as failed (thread-safe)
        async with lock:
            test_sessions_db[session_id].update({
                "status": TestStatus.FAILED,
                "error": str(e),
                "updated_at": datetime.now(),
                "completed_at": datetime.now()
            })

    finally:
        # Clean up lock when session is done
        session_locks.cleanup_lock(session_id)


@router.post(
    "/start",
    response_model=TestSessionResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 429: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Start Test Execution",
    description="Start testing all endpoints in a document with intelligent retry"
)
@rate_limit(
    limit=settings.RATE_LIMIT_TEST_START,
    window=settings.RATE_LIMIT_WINDOW,
    key_prefix="test_start"
)
async def start_test_execution(
    http_request: Request,
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

        # Store session (thread-safe)
        lock = await session_locks.get_lock(session_id)
        async with lock:
            test_sessions_db[session_id] = session_metadata

        # Calculate estimated duration
        # Comprehensive mode: ~40 tests per endpoint * 0.5s = ~20s per endpoint
        # Basic mode: 1 test per endpoint * 3s (with retries) = ~3s per endpoint
        if request.comprehensive_mode:
            estimated_duration = len(endpoints) * 20
        else:
            estimated_duration = len(endpoints) * 3

        logger.info(f"Created test session: {session_id} for document: {request.document_id}")
        logger.info(f"Total endpoints: {len(endpoints)}, Max retries: {request.max_retries}")
        logger.info(f"Comprehensive mode: {'ENABLED' if request.comprehensive_mode else 'DISABLED'}")

        # Get semantic contexts if available
        semantic_contexts = doc_metadata.get("semantic_contexts", {})
        if semantic_contexts:
            logger.info(f"📚 Using semantic contexts for {len(semantic_contexts)} endpoints")

        # Get parameter constraints if available
        parameter_constraints = doc_metadata.get("parameter_constraints", {})
        if parameter_constraints:
            total_with_constraints = doc_metadata.get("constraints_coverage", {}).get("parameters_with_constraints", 0)
            logger.info(f"🔍 Using parameter constraints for {total_with_constraints} parameters")

        # Start background task
        background_tasks.add_task(
            run_test_session_async,
            session_id=session_id,
            document_id=request.document_id,
            base_url=base_url,
            endpoints=endpoints,
            max_retries=request.max_retries,
            use_optimal_order=request.use_optimal_order,
            comprehensive_mode=request.comprehensive_mode,
            semantic_contexts=semantic_contexts,
            parameter_constraints=parameter_constraints
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
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Get Test Session Status",
    description="Get real-time status and progress of a test session"
)
async def get_test_status(
    session_id: str = Path(
        ...,
        description="Test session ID (format: session_<hex>_<timestamp>)",
        min_length=10,
        max_length=100
    )
):
    """
    Get test session status and progress

    Returns real-time information about:
    - Current status (pending, processing, completed, failed)
    - Progress percentage
    - Number of tests passed/failed
    - Timestamps

    Use this endpoint to poll for updates while tests are running.
    """
    try:
        # VALIDATION: Validate session ID format
        try:
            validate_session_id(session_id)
        except ValueError as ve:
            logger.warning(f"Invalid session ID format: {session_id} - {ve}")
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "ValidationError",
                    "message": str(ve),
                    "field": "session_id"
                }
            )

        # Thread-safe session retrieval
        session = await get_session_safe(session_id)

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

    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
        raise
    except Exception as e:
        logger.error(f"Failed to get test status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{session_id}/report",
    response_model=TestReportResponse,
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Get Test Report",
    description="Get complete test results and detailed report"
)
async def get_test_report(
    session_id: str = Path(
        ...,
        description="Test session ID (format: session_<hex>_<timestamp>)",
        min_length=10,
        max_length=100
    )
):
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
    try:
        # VALIDATION: Validate session ID format
        try:
            validate_session_id(session_id)
        except ValueError as ve:
            logger.warning(f"Invalid session ID format: {session_id} - {ve}")
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "ValidationError",
                    "message": str(ve),
                    "field": "session_id"
                }
            )

        # Thread-safe session retrieval
        session = await get_session_safe(session_id)

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
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Delete Test Session",
    description="Delete a test session and cleanup resources"
)
async def delete_test_session(
    session_id: str = Path(
        ...,
        description="Test session ID (format: session_<hex>_<timestamp>)",
        min_length=10,
        max_length=100
    )
):
    """
    Delete test session and cleanup

    This will:
    - Remove session from storage
    - Delete Flow DB collection for this session
    - Clean up any temporary files
    """
    try:
        # VALIDATION: Validate session ID format
        try:
            validate_session_id(session_id)
        except ValueError as ve:
            logger.warning(f"Invalid session ID format: {session_id} - {ve}")
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "ValidationError",
                    "message": str(ve),
                    "field": "session_id"
                }
            )

        # Thread-safe session retrieval
        session = await get_session_safe(session_id)

        # Delete Flow DB collection (if exists)
        try:
            from src.rag.flow_store import FlowStore
            flow_store = FlowStore(session_id=session_id)
            flow_store.cleanup()
            logger.info(f"Cleaned up Flow DB for session: {session_id}")
        except Exception as e:
            logger.warning(f"Could not cleanup Flow DB: {e}")

        # Remove from storage (thread-safe)
        lock = await session_locks.get_lock(session_id)
        async with lock:
            del test_sessions_db[session_id]

        # Cleanup lock
        session_locks.cleanup_lock(session_id)

        logger.info(f"✅ Test session deleted: {session_id}")

        return {
            "message": "Test session deleted successfully",
            "session_id": session_id
        }

    except Exception as e:
        logger.error(f"Failed to delete test session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{session_id}/healing-history",
    summary="Get Self-Healing Report",
    description="Get detailed report of all self-healing actions for this test session"
)
async def get_healing_history(session_id: str):
    """
    Get self-healing report

    Returns detailed information about:
    - Total healing actions performed
    - Endpoints that were auto-healed
    - API changes detected (status code, schema, type changes)
    - Severity breakdown (BREAKING, NON_BREAKING, MINOR)
    - Complete healing history with timestamps

    This endpoint shows how tests automatically adapted to API changes.
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

        healing_report = session.get("healing_report", {
            "total_healing_actions": 0,
            "endpoints_healed": 0,
            "history": []
        })

        return {
            "session_id": session_id,
            "healing_report": healing_report,
            "message": "Self-healing allows tests to automatically adapt when APIs change",
            "capabilities": [
                "Automatic detection of API changes",
                "Status code adaptation",
                "Schema evolution (new/removed/renamed fields)",
                "Type change detection",
                "Smart auto-heal decisions",
                "Breaking change identification"
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get healing history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{session_id}/security-report",
    summary="Get Security Testing Report",
    description="Get detailed security mutation testing report"
)
async def get_security_report(session_id: str):
    """
    Get security testing report

    Returns detailed information about:
    - Security tests executed (SQL injection, XSS, etc.)
    - Vulnerabilities detected
    - OWASP Top 10 coverage
    - Attack patterns used
    - Severity of findings

    This endpoint shows results from automated security mutation testing.
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

        # Extract security-related results from test results
        results = session.get("results", [])
        security_tests = [
            r for r in results
            if r.get("test_type") == "mutation" or "mutation" in r.get("endpoint", "").lower()
        ]

        # Build security report
        security_report = {
            "total_security_tests": len(security_tests),
            "vulnerabilities_detected": sum(
                1 for r in security_tests
                if r.get("vulnerable", False) or not r.get("success", True)
            ),
            "security_tests_by_type": {},
            "owasp_coverage": [
                "SQL Injection", "XSS", "Command Injection", "Path Traversal",
                "LDAP Injection", "XML Injection", "XXE", "SSRF",
                "Template Injection", "Expression Language Injection",
                "NoSQL Injection", "Header Injection", "Open Redirect",
                "CSRF", "Mass Assignment", "Insecure Deserialization",
                "Authentication Bypass", "Authorization Bypass", "Information Disclosure"
            ],
            "tests": security_tests[:50]  # Limit to first 50 for performance
        }

        return {
            "session_id": session_id,
            "security_report": security_report,
            "message": "Security mutation testing automatically tests for OWASP Top 10 vulnerabilities",
            "capabilities": [
                "19 OWASP security patterns",
                "150+ attack payloads",
                "Intelligent pattern selection",
                "Automated vulnerability detection",
                "CWE mapping",
                "Severity classification"
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get security report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{session_id}/mutations",
    summary="Get Mutation Test Details",
    description="Get detailed information about mutation tests generated and executed"
)
async def get_mutation_tests(session_id: str):
    """
    Get mutation test details

    Returns information about:
    - Mutation tests generated per endpoint
    - Security patterns applied
    - Attack payloads used
    - Test results for each mutation

    This provides transparency into how mutation testing works.
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

        results = session.get("results", [])

        # Extract mutation-related metadata from results
        mutation_info = {
            "total_endpoints_tested": session["total_endpoints"],
            "mutation_tests_generated": len([
                r for r in results
                if r.get("test_type") == "mutation"
            ]),
            "patterns_applied": [],
            "by_endpoint": {}
        }

        return {
            "session_id": session_id,
            "mutation_info": mutation_info,
            "message": "Mutation testing generates variations of tests to find edge cases and vulnerabilities"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get mutation tests: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
