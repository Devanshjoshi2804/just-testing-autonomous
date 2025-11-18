"""
Coverage Report Repository
Data access layer for test coverage metrics
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete, and_, desc
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import CoverageReport


class CoverageReportRepository:
    """Repository for CoverageReport operations"""

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
        endpoint_coverage: float = 0.0,
        parameter_coverage: float = 0.0,
        status_code_coverage: float = 0.0,
        scenario_coverage: float = 0.0,
        overall_coverage: float = 0.0,
        total_endpoints: int = 0,
        tested_endpoints: int = 0,
        total_parameters: int = 0,
        tested_parameters: int = 0,
        total_status_codes: int = 0,
        tested_status_codes: int = 0,
        coverage_details: Optional[dict] = None
    ) -> CoverageReport:
        """
        Create a new coverage report

        Args:
            session_id: Parent test session ID
            endpoint_coverage: Percentage of endpoints tested
            parameter_coverage: Percentage of parameters tested
            status_code_coverage: Percentage of status codes tested
            scenario_coverage: Percentage of scenarios covered
            overall_coverage: Overall coverage percentage
            total_endpoints: Total number of endpoints
            tested_endpoints: Number of tested endpoints
            total_parameters: Total number of parameters
            tested_parameters: Number of tested parameters
            total_status_codes: Total number of status codes
            tested_status_codes: Number of tested status codes
            coverage_details: Detailed coverage metrics (JSON)

        Returns:
            Created CoverageReport
        """
        coverage_report = CoverageReport(
            session_id=session_id,
            endpoint_coverage=endpoint_coverage,
            parameter_coverage=parameter_coverage,
            status_code_coverage=status_code_coverage,
            scenario_coverage=scenario_coverage,
            overall_coverage=overall_coverage,
            total_endpoints=total_endpoints,
            tested_endpoints=tested_endpoints,
            total_parameters=total_parameters,
            tested_parameters=tested_parameters,
            total_status_codes=total_status_codes,
            tested_status_codes=tested_status_codes,
            coverage_details_json=coverage_details or {}
        )

        self.session.add(coverage_report)
        self.session.flush()

        return coverage_report

    def get_by_id(self, id: int) -> Optional[CoverageReport]:
        """Get coverage report by ID"""
        return self.session.query(CoverageReport).filter(CoverageReport.id == id).first()

    def get_by_session(self, session_id: int) -> List[CoverageReport]:
        """Get all coverage reports for a session"""
        return self.session.query(CoverageReport).filter(
            CoverageReport.session_id == session_id
        ).order_by(desc(CoverageReport.generated_at)).all()

    def get_latest_by_session(self, session_id: int) -> Optional[CoverageReport]:
        """Get the most recent coverage report for a session"""
        return self.session.query(CoverageReport).filter(
            CoverageReport.session_id == session_id
        ).order_by(desc(CoverageReport.generated_at)).first()

    def get_high_coverage_reports(
        self,
        min_coverage: float = 80.0,
        limit: int = 100
    ) -> List[CoverageReport]:
        """
        Get coverage reports with high overall coverage

        Args:
            min_coverage: Minimum overall coverage percentage
            limit: Max number of results

        Returns:
            List of CoverageReport objects
        """
        return self.session.query(CoverageReport).filter(
            CoverageReport.overall_coverage >= min_coverage
        ).order_by(desc(CoverageReport.overall_coverage)).limit(limit).all()

    def get_low_coverage_reports(
        self,
        max_coverage: float = 50.0,
        limit: int = 100
    ) -> List[CoverageReport]:
        """
        Get coverage reports with low overall coverage

        Args:
            max_coverage: Maximum overall coverage percentage
            limit: Max number of results

        Returns:
            List of CoverageReport objects
        """
        return self.session.query(CoverageReport).filter(
            CoverageReport.overall_coverage <= max_coverage
        ).order_by(CoverageReport.overall_coverage).limit(limit).all()

    def get_recent_reports(
        self,
        hours: int = 24,
        limit: int = 50
    ) -> List[CoverageReport]:
        """Get recent coverage reports across all sessions"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        return self.session.query(CoverageReport).filter(
            CoverageReport.generated_at >= cutoff_time
        ).order_by(desc(CoverageReport.generated_at)).limit(limit).all()

    def get_coverage_trends(
        self,
        session_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get coverage trends over time for a session

        Args:
            session_id: Test session ID
            limit: Number of reports to analyze

        Returns:
            List of coverage metrics over time
        """
        reports = self.session.query(CoverageReport).filter(
            CoverageReport.session_id == session_id
        ).order_by(desc(CoverageReport.generated_at)).limit(limit).all()

        return [
            {
                'generated_at': report.generated_at,
                'overall_coverage': report.overall_coverage,
                'endpoint_coverage': report.endpoint_coverage,
                'parameter_coverage': report.parameter_coverage,
                'status_code_coverage': report.status_code_coverage,
                'scenario_coverage': report.scenario_coverage
            }
            for report in reversed(reports)  # Oldest to newest
        ]

    def get_average_coverage(self, session_id: int) -> Dict[str, float]:
        """
        Calculate average coverage metrics for a session

        Args:
            session_id: Test session ID

        Returns:
            Dictionary with average coverage percentages
        """
        reports = self.session.query(CoverageReport).filter(
            CoverageReport.session_id == session_id
        ).all()

        if not reports:
            return {
                'avg_overall': 0.0,
                'avg_endpoint': 0.0,
                'avg_parameter': 0.0,
                'avg_status_code': 0.0,
                'avg_scenario': 0.0
            }

        count = len(reports)

        return {
            'avg_overall': sum(r.overall_coverage for r in reports) / count,
            'avg_endpoint': sum(r.endpoint_coverage for r in reports) / count,
            'avg_parameter': sum(r.parameter_coverage for r in reports) / count,
            'avg_status_code': sum(r.status_code_coverage for r in reports) / count,
            'avg_scenario': sum(r.scenario_coverage for r in reports) / count
        }

    def update(
        self,
        id: int,
        endpoint_coverage: Optional[float] = None,
        parameter_coverage: Optional[float] = None,
        status_code_coverage: Optional[float] = None,
        scenario_coverage: Optional[float] = None,
        overall_coverage: Optional[float] = None,
        coverage_details: Optional[dict] = None
    ) -> bool:
        """
        Update coverage report metrics

        Args:
            id: Coverage report ID
            endpoint_coverage: New endpoint coverage
            parameter_coverage: New parameter coverage
            status_code_coverage: New status code coverage
            scenario_coverage: New scenario coverage
            overall_coverage: New overall coverage
            coverage_details: New coverage details

        Returns:
            True if updated, False if not found
        """
        updates = {}

        if endpoint_coverage is not None:
            updates['endpoint_coverage'] = endpoint_coverage
        if parameter_coverage is not None:
            updates['parameter_coverage'] = parameter_coverage
        if status_code_coverage is not None:
            updates['status_code_coverage'] = status_code_coverage
        if scenario_coverage is not None:
            updates['scenario_coverage'] = scenario_coverage
        if overall_coverage is not None:
            updates['overall_coverage'] = overall_coverage
        if coverage_details is not None:
            updates['coverage_details_json'] = coverage_details

        if not updates:
            return False

        result = self.session.query(CoverageReport).filter(
            CoverageReport.id == id
        ).update(updates)

        return result > 0

    def delete(self, id: int) -> bool:
        """Delete coverage report"""
        result = self.session.query(CoverageReport).filter(
            CoverageReport.id == id
        ).delete()

        return result > 0

    def delete_by_session(self, session_id: int) -> int:
        """Delete all coverage reports for a session"""
        result = self.session.query(CoverageReport).filter(
            CoverageReport.session_id == session_id
        ).delete()

        return result

    def count_by_session(self, session_id: int) -> int:
        """Count coverage reports for a session"""
        return self.session.query(CoverageReport).filter(
            CoverageReport.session_id == session_id
        ).count()


class AsyncCoverageReportRepository:
    """Async repository for CoverageReport operations"""

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
        endpoint_coverage: float = 0.0,
        parameter_coverage: float = 0.0,
        status_code_coverage: float = 0.0,
        scenario_coverage: float = 0.0,
        overall_coverage: float = 0.0,
        total_endpoints: int = 0,
        tested_endpoints: int = 0,
        total_parameters: int = 0,
        tested_parameters: int = 0,
        total_status_codes: int = 0,
        tested_status_codes: int = 0,
        coverage_details: Optional[dict] = None
    ) -> CoverageReport:
        """Create a new coverage report (async)"""
        coverage_report = CoverageReport(
            session_id=session_id,
            endpoint_coverage=endpoint_coverage,
            parameter_coverage=parameter_coverage,
            status_code_coverage=status_code_coverage,
            scenario_coverage=scenario_coverage,
            overall_coverage=overall_coverage,
            total_endpoints=total_endpoints,
            tested_endpoints=tested_endpoints,
            total_parameters=total_parameters,
            tested_parameters=tested_parameters,
            total_status_codes=total_status_codes,
            tested_status_codes=tested_status_codes,
            coverage_details_json=coverage_details or {}
        )

        self.session.add(coverage_report)
        await self.session.flush()

        return coverage_report

    async def get_by_id(self, id: int) -> Optional[CoverageReport]:
        """Get coverage report by ID (async)"""
        result = await self.session.execute(
            select(CoverageReport).filter(CoverageReport.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_session(self, session_id: int) -> List[CoverageReport]:
        """Get all coverage reports for a session (async)"""
        result = await self.session.execute(
            select(CoverageReport)
            .filter(CoverageReport.session_id == session_id)
            .order_by(desc(CoverageReport.generated_at))
        )
        return result.scalars().all()

    async def get_latest_by_session(self, session_id: int) -> Optional[CoverageReport]:
        """Get the most recent coverage report (async)"""
        result = await self.session.execute(
            select(CoverageReport)
            .filter(CoverageReport.session_id == session_id)
            .order_by(desc(CoverageReport.generated_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_high_coverage_reports(
        self,
        min_coverage: float = 80.0,
        limit: int = 100
    ) -> List[CoverageReport]:
        """Get coverage reports with high overall coverage (async)"""
        result = await self.session.execute(
            select(CoverageReport)
            .filter(CoverageReport.overall_coverage >= min_coverage)
            .order_by(desc(CoverageReport.overall_coverage))
            .limit(limit)
        )
        return result.scalars().all()

    async def get_low_coverage_reports(
        self,
        max_coverage: float = 50.0,
        limit: int = 100
    ) -> List[CoverageReport]:
        """Get coverage reports with low overall coverage (async)"""
        result = await self.session.execute(
            select(CoverageReport)
            .filter(CoverageReport.overall_coverage <= max_coverage)
            .order_by(CoverageReport.overall_coverage)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_recent_reports(
        self,
        hours: int = 24,
        limit: int = 50
    ) -> List[CoverageReport]:
        """Get recent coverage reports (async)"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        result = await self.session.execute(
            select(CoverageReport)
            .filter(CoverageReport.generated_at >= cutoff_time)
            .order_by(desc(CoverageReport.generated_at))
            .limit(limit)
        )
        return result.scalars().all()

    async def get_coverage_trends(
        self,
        session_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get coverage trends over time (async)"""
        result = await self.session.execute(
            select(CoverageReport)
            .filter(CoverageReport.session_id == session_id)
            .order_by(desc(CoverageReport.generated_at))
            .limit(limit)
        )
        reports = result.scalars().all()

        return [
            {
                'generated_at': report.generated_at,
                'overall_coverage': report.overall_coverage,
                'endpoint_coverage': report.endpoint_coverage,
                'parameter_coverage': report.parameter_coverage,
                'status_code_coverage': report.status_code_coverage,
                'scenario_coverage': report.scenario_coverage
            }
            for report in reversed(list(reports))  # Oldest to newest
        ]

    async def get_average_coverage(self, session_id: int) -> Dict[str, float]:
        """Calculate average coverage metrics (async)"""
        result = await self.session.execute(
            select(CoverageReport).filter(CoverageReport.session_id == session_id)
        )
        reports = result.scalars().all()

        if not reports:
            return {
                'avg_overall': 0.0,
                'avg_endpoint': 0.0,
                'avg_parameter': 0.0,
                'avg_status_code': 0.0,
                'avg_scenario': 0.0
            }

        count = len(reports)

        return {
            'avg_overall': sum(r.overall_coverage for r in reports) / count,
            'avg_endpoint': sum(r.endpoint_coverage for r in reports) / count,
            'avg_parameter': sum(r.parameter_coverage for r in reports) / count,
            'avg_status_code': sum(r.status_code_coverage for r in reports) / count,
            'avg_scenario': sum(r.scenario_coverage for r in reports) / count
        }

    async def update(
        self,
        id: int,
        endpoint_coverage: Optional[float] = None,
        parameter_coverage: Optional[float] = None,
        status_code_coverage: Optional[float] = None,
        scenario_coverage: Optional[float] = None,
        overall_coverage: Optional[float] = None,
        coverage_details: Optional[dict] = None
    ) -> bool:
        """Update coverage report metrics (async)"""
        updates = {}

        if endpoint_coverage is not None:
            updates['endpoint_coverage'] = endpoint_coverage
        if parameter_coverage is not None:
            updates['parameter_coverage'] = parameter_coverage
        if status_code_coverage is not None:
            updates['status_code_coverage'] = status_code_coverage
        if scenario_coverage is not None:
            updates['scenario_coverage'] = scenario_coverage
        if overall_coverage is not None:
            updates['overall_coverage'] = overall_coverage
        if coverage_details is not None:
            updates['coverage_details_json'] = coverage_details

        if not updates:
            return False

        result = await self.session.execute(
            update(CoverageReport)
            .where(CoverageReport.id == id)
            .values(**updates)
        )

        return result.rowcount > 0

    async def delete(self, id: int) -> bool:
        """Delete coverage report (async)"""
        result = await self.session.execute(
            delete(CoverageReport).where(CoverageReport.id == id)
        )

        return result.rowcount > 0

    async def delete_by_session(self, session_id: int) -> int:
        """Delete all coverage reports for a session (async)"""
        result = await self.session.execute(
            delete(CoverageReport).where(CoverageReport.session_id == session_id)
        )

        return result.rowcount

    async def count_by_session(self, session_id: int) -> int:
        """Count coverage reports for a session (async)"""
        result = await self.session.execute(
            select(CoverageReport).filter(CoverageReport.session_id == session_id)
        )
        return len(result.scalars().all())
