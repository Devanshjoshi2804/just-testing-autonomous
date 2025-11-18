"""
Test Result Repository
Data access layer for test execution results
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete, and_, or_, desc, func
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import TestResult


class TestResultRepository:
    """Repository for TestResult operations"""

    def __init__(self, session: Session):
        """
        Initialize repository

        Args:
            session: SQLAlchemy session
        """
        self.session = session

    def create(
        self,
        session_id: int,
        endpoint_id: Optional[int] = None,
        test_name: Optional[str] = None,
        test_type: Optional[str] = None,
        scenario_type: Optional[str] = None,
        strategy: Optional[str] = None,
        duration_ms: Optional[float] = None,
        request_method: Optional[str] = None,
        request_path: Optional[str] = None,
        request_params: Optional[dict] = None,
        request_body: Optional[dict] = None,
        request_headers: Optional[dict] = None,
        response_status_code: Optional[int] = None,
        response_body: Optional[dict] = None,
        response_headers: Optional[dict] = None,
        response_time_ms: Optional[float] = None,
        success: bool = False,
        expected_status: Optional[int] = None,
        actual_status: Optional[int] = None,
        schema_valid: Optional[bool] = None,
        schema_violations: Optional[list] = None,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
        traceback: Optional[str] = None
    ) -> TestResult:
        """
        Create a new test result

        Args:
            session_id: Parent test session ID
            endpoint_id: Associated endpoint ID
            test_name: Name of the test
            test_type: Type of test (positive, negative, boundary, security)
            scenario_type: Scenario type (happy_path, error, edge_case)
            strategy: Test generation strategy used
            duration_ms: Test execution duration in milliseconds
            request_method: HTTP method
            request_path: Request path
            request_params: Request parameters (JSON)
            request_body: Request body (JSON)
            request_headers: Request headers (JSON)
            response_status_code: HTTP status code
            response_body: Response body (JSON)
            response_headers: Response headers (JSON)
            response_time_ms: Response time in milliseconds
            success: Whether the test passed
            expected_status: Expected status code
            actual_status: Actual status code
            schema_valid: Whether response schema is valid
            schema_violations: List of schema violations
            error_message: Error message if test failed
            error_type: Type of error
            traceback: Error traceback

        Returns:
            Created TestResult
        """
        test_result = TestResult(
            session_id=session_id,
            endpoint_id=endpoint_id,
            test_name=test_name,
            test_type=test_type,
            scenario_type=scenario_type,
            strategy=strategy,
            duration_ms=duration_ms,
            request_method=request_method,
            request_path=request_path,
            request_params_json=request_params or {},
            request_body_json=request_body or {},
            request_headers_json=request_headers or {},
            response_status_code=response_status_code,
            response_body_json=response_body or {},
            response_headers_json=response_headers or {},
            response_time_ms=response_time_ms,
            success=success,
            expected_status=expected_status,
            actual_status=actual_status,
            schema_valid=schema_valid,
            schema_violations_json=schema_violations or [],
            error_message=error_message,
            error_type=error_type,
            traceback=traceback
        )

        self.session.add(test_result)
        self.session.flush()

        return test_result

    def get_by_id(self, id: int) -> Optional[TestResult]:
        """Get test result by ID"""
        return self.session.query(TestResult).filter(TestResult.id == id).first()

    def get_by_session(
        self,
        session_id: int,
        limit: int = 100,
        offset: int = 0
    ) -> List[TestResult]:
        """Get all test results for a session"""
        return self.session.query(TestResult).filter(
            TestResult.session_id == session_id
        ).order_by(desc(TestResult.executed_at)).limit(limit).offset(offset).all()

    def get_by_endpoint(
        self,
        endpoint_id: int,
        limit: int = 100,
        offset: int = 0
    ) -> List[TestResult]:
        """Get all test results for an endpoint"""
        return self.session.query(TestResult).filter(
            TestResult.endpoint_id == endpoint_id
        ).order_by(desc(TestResult.executed_at)).limit(limit).offset(offset).all()

    def get_failed_tests(
        self,
        session_id: int,
        limit: int = 100
    ) -> List[TestResult]:
        """Get all failed tests for a session"""
        return self.session.query(TestResult).filter(
            and_(
                TestResult.session_id == session_id,
                TestResult.success == False
            )
        ).order_by(desc(TestResult.executed_at)).limit(limit).all()

    def get_by_test_type(
        self,
        session_id: int,
        test_type: str,
        limit: int = 100
    ) -> List[TestResult]:
        """Get test results by test type"""
        return self.session.query(TestResult).filter(
            and_(
                TestResult.session_id == session_id,
                TestResult.test_type == test_type
            )
        ).order_by(desc(TestResult.executed_at)).limit(limit).all()

    def get_statistics(self, session_id: int) -> Dict[str, Any]:
        """
        Get test statistics for a session

        Returns:
            Dictionary with statistics:
            - total_tests: Total number of tests
            - passed_tests: Number of passed tests
            - failed_tests: Number of failed tests
            - avg_duration_ms: Average test duration
            - avg_response_time_ms: Average response time
            - success_rate: Success rate percentage
        """
        results = self.session.query(TestResult).filter(
            TestResult.session_id == session_id
        ).all()

        if not results:
            return {
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0,
                'avg_duration_ms': 0.0,
                'avg_response_time_ms': 0.0,
                'success_rate': 0.0
            }

        total = len(results)
        passed = sum(1 for r in results if r.success)
        failed = total - passed

        durations = [r.duration_ms for r in results if r.duration_ms is not None]
        response_times = [r.response_time_ms for r in results if r.response_time_ms is not None]

        avg_duration = sum(durations) / len(durations) if durations else 0.0
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0

        return {
            'total_tests': total,
            'passed_tests': passed,
            'failed_tests': failed,
            'avg_duration_ms': avg_duration,
            'avg_response_time_ms': avg_response_time,
            'success_rate': (passed / total * 100) if total > 0 else 0.0
        }

    def get_test_type_distribution(self, session_id: int) -> Dict[str, int]:
        """Get distribution of test types"""
        results = self.session.query(
            TestResult.test_type,
            func.count(TestResult.id)
        ).filter(
            TestResult.session_id == session_id
        ).group_by(TestResult.test_type).all()

        return {test_type: count for test_type, count in results}

    def get_slowest_tests(
        self,
        session_id: int,
        limit: int = 10
    ) -> List[TestResult]:
        """Get slowest tests by response time"""
        return self.session.query(TestResult).filter(
            TestResult.session_id == session_id
        ).order_by(desc(TestResult.response_time_ms)).limit(limit).all()

    def get_recent_failures(
        self,
        hours: int = 24,
        limit: int = 50
    ) -> List[TestResult]:
        """Get recent test failures across all sessions"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        return self.session.query(TestResult).filter(
            and_(
                TestResult.success == False,
                TestResult.executed_at >= cutoff_time
            )
        ).order_by(desc(TestResult.executed_at)).limit(limit).all()

    def delete(self, id: int) -> bool:
        """Delete test result"""
        result = self.session.query(TestResult).filter(
            TestResult.id == id
        ).delete()

        return result > 0

    def delete_by_session(self, session_id: int) -> int:
        """Delete all test results for a session"""
        result = self.session.query(TestResult).filter(
            TestResult.session_id == session_id
        ).delete()

        return result

    def count_by_session(self, session_id: int) -> int:
        """Count test results in a session"""
        return self.session.query(TestResult).filter(
            TestResult.session_id == session_id
        ).count()


class AsyncTestResultRepository:
    """Async repository for TestResult operations"""

    def __init__(self, session: AsyncSession):
        """
        Initialize async repository

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def create(
        self,
        session_id: int,
        endpoint_id: Optional[int] = None,
        test_name: Optional[str] = None,
        test_type: Optional[str] = None,
        scenario_type: Optional[str] = None,
        strategy: Optional[str] = None,
        duration_ms: Optional[float] = None,
        request_method: Optional[str] = None,
        request_path: Optional[str] = None,
        request_params: Optional[dict] = None,
        request_body: Optional[dict] = None,
        request_headers: Optional[dict] = None,
        response_status_code: Optional[int] = None,
        response_body: Optional[dict] = None,
        response_headers: Optional[dict] = None,
        response_time_ms: Optional[float] = None,
        success: bool = False,
        expected_status: Optional[int] = None,
        actual_status: Optional[int] = None,
        schema_valid: Optional[bool] = None,
        schema_violations: Optional[list] = None,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
        traceback: Optional[str] = None
    ) -> TestResult:
        """Create a new test result (async)"""
        test_result = TestResult(
            session_id=session_id,
            endpoint_id=endpoint_id,
            test_name=test_name,
            test_type=test_type,
            scenario_type=scenario_type,
            strategy=strategy,
            duration_ms=duration_ms,
            request_method=request_method,
            request_path=request_path,
            request_params_json=request_params or {},
            request_body_json=request_body or {},
            request_headers_json=request_headers or {},
            response_status_code=response_status_code,
            response_body_json=response_body or {},
            response_headers_json=response_headers or {},
            response_time_ms=response_time_ms,
            success=success,
            expected_status=expected_status,
            actual_status=actual_status,
            schema_valid=schema_valid,
            schema_violations_json=schema_violations or [],
            error_message=error_message,
            error_type=error_type,
            traceback=traceback
        )

        self.session.add(test_result)
        await self.session.flush()

        return test_result

    async def get_by_id(self, id: int) -> Optional[TestResult]:
        """Get test result by ID (async)"""
        result = await self.session.execute(
            select(TestResult).filter(TestResult.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_session(
        self,
        session_id: int,
        limit: int = 100,
        offset: int = 0
    ) -> List[TestResult]:
        """Get all test results for a session (async)"""
        result = await self.session.execute(
            select(TestResult)
            .filter(TestResult.session_id == session_id)
            .order_by(desc(TestResult.executed_at))
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def get_by_endpoint(
        self,
        endpoint_id: int,
        limit: int = 100,
        offset: int = 0
    ) -> List[TestResult]:
        """Get all test results for an endpoint (async)"""
        result = await self.session.execute(
            select(TestResult)
            .filter(TestResult.endpoint_id == endpoint_id)
            .order_by(desc(TestResult.executed_at))
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def get_failed_tests(
        self,
        session_id: int,
        limit: int = 100
    ) -> List[TestResult]:
        """Get all failed tests for a session (async)"""
        result = await self.session.execute(
            select(TestResult)
            .filter(
                and_(
                    TestResult.session_id == session_id,
                    TestResult.success == False
                )
            )
            .order_by(desc(TestResult.executed_at))
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_test_type(
        self,
        session_id: int,
        test_type: str,
        limit: int = 100
    ) -> List[TestResult]:
        """Get test results by test type (async)"""
        result = await self.session.execute(
            select(TestResult)
            .filter(
                and_(
                    TestResult.session_id == session_id,
                    TestResult.test_type == test_type
                )
            )
            .order_by(desc(TestResult.executed_at))
            .limit(limit)
        )
        return result.scalars().all()

    async def get_statistics(self, session_id: int) -> Dict[str, Any]:
        """Get test statistics for a session (async)"""
        result = await self.session.execute(
            select(TestResult).filter(TestResult.session_id == session_id)
        )
        results = result.scalars().all()

        if not results:
            return {
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0,
                'avg_duration_ms': 0.0,
                'avg_response_time_ms': 0.0,
                'success_rate': 0.0
            }

        total = len(results)
        passed = sum(1 for r in results if r.success)
        failed = total - passed

        durations = [r.duration_ms for r in results if r.duration_ms is not None]
        response_times = [r.response_time_ms for r in results if r.response_time_ms is not None]

        avg_duration = sum(durations) / len(durations) if durations else 0.0
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0

        return {
            'total_tests': total,
            'passed_tests': passed,
            'failed_tests': failed,
            'avg_duration_ms': avg_duration,
            'avg_response_time_ms': avg_response_time,
            'success_rate': (passed / total * 100) if total > 0 else 0.0
        }

    async def get_test_type_distribution(self, session_id: int) -> Dict[str, int]:
        """Get distribution of test types (async)"""
        result = await self.session.execute(
            select(TestResult.test_type, func.count(TestResult.id))
            .filter(TestResult.session_id == session_id)
            .group_by(TestResult.test_type)
        )
        rows = result.all()

        return {test_type: count for test_type, count in rows}

    async def get_slowest_tests(
        self,
        session_id: int,
        limit: int = 10
    ) -> List[TestResult]:
        """Get slowest tests by response time (async)"""
        result = await self.session.execute(
            select(TestResult)
            .filter(TestResult.session_id == session_id)
            .order_by(desc(TestResult.response_time_ms))
            .limit(limit)
        )
        return result.scalars().all()

    async def get_recent_failures(
        self,
        hours: int = 24,
        limit: int = 50
    ) -> List[TestResult]:
        """Get recent test failures (async)"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        result = await self.session.execute(
            select(TestResult)
            .filter(
                and_(
                    TestResult.success == False,
                    TestResult.executed_at >= cutoff_time
                )
            )
            .order_by(desc(TestResult.executed_at))
            .limit(limit)
        )
        return result.scalars().all()

    async def delete(self, id: int) -> bool:
        """Delete test result (async)"""
        result = await self.session.execute(
            delete(TestResult).where(TestResult.id == id)
        )

        return result.rowcount > 0

    async def delete_by_session(self, session_id: int) -> int:
        """Delete all test results for a session (async)"""
        result = await self.session.execute(
            delete(TestResult).where(TestResult.session_id == session_id)
        )

        return result.rowcount

    async def count_by_session(self, session_id: int) -> int:
        """Count test results in a session (async)"""
        result = await self.session.execute(
            select(TestResult).filter(TestResult.session_id == session_id)
        )
        return len(result.scalars().all())
