"""
Test Session Repository
Data access layer for test sessions
"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, update, delete, and_, or_, desc
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import TestSession, Endpoint, TestResult, CoverageReport


class TestSessionRepository:
    """Repository for TestSession operations"""

    def __init__(self, session: Session):
        """
        Initialize repository

        Args:
            session: SQLAlchemy session
        """
        self.session = session

    def create(
        self,
        session_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> TestSession:
        """
        Create a new test session

        Args:
            session_id: Unique session identifier
            name: Session name
            description: Session description
            metadata: Additional metadata

        Returns:
            Created TestSession
        """
        test_session = TestSession(
            session_id=session_id,
            name=name,
            description=description,
            status='pending',
            started_at=datetime.now(),
            metadata_json=metadata or {}
        )

        self.session.add(test_session)
        self.session.flush()

        return test_session

    def get_by_id(self, id: int) -> Optional[TestSession]:
        """Get test session by ID"""
        return self.session.query(TestSession).filter(TestSession.id == id).first()

    def get_by_session_id(self, session_id: str) -> Optional[TestSession]:
        """Get test session by session_id"""
        return self.session.query(TestSession).filter(TestSession.session_id == session_id).first()

    def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None
    ) -> List[TestSession]:
        """
        Get all test sessions with optional filtering

        Args:
            limit: Max number of results
            offset: Number of results to skip
            status: Filter by status

        Returns:
            List of TestSession objects
        """
        query = self.session.query(TestSession)

        if status:
            query = query.filter(TestSession.status == status)

        query = query.order_by(desc(TestSession.created_at))
        query = query.limit(limit).offset(offset)

        return query.all()

    def update_status(self, session_id: str, status: str) -> bool:
        """Update session status"""
        result = self.session.query(TestSession).filter(
            TestSession.session_id == session_id
        ).update({
            'status': status,
            'completed_at': datetime.now() if status == 'completed' else None
        })

        return result > 0

    def update_test_counts(
        self,
        session_id: str,
        total: int,
        passed: int,
        failed: int
    ) -> bool:
        """Update test counts"""
        result = self.session.query(TestSession).filter(
            TestSession.session_id == session_id
        ).update({
            'total_tests': total,
            'passed_tests': passed,
            'failed_tests': failed
        })

        return result > 0

    def increment_test_counts(
        self,
        session_id: str,
        passed: bool = True
    ) -> bool:
        """Increment test counts"""
        session = self.get_by_session_id(session_id)
        if not session:
            return False

        session.total_tests += 1
        if passed:
            session.passed_tests += 1
        else:
            session.failed_tests += 1

        return True

    def delete(self, session_id: str) -> bool:
        """Delete test session and all related data"""
        result = self.session.query(TestSession).filter(
            TestSession.session_id == session_id
        ).delete()

        return result > 0

    def get_with_results(self, session_id: str) -> Optional[TestSession]:
        """Get session with all test results loaded"""
        return self.session.query(TestSession).filter(
            TestSession.session_id == session_id
        ).options(
            joinedload(TestSession.test_results),
            joinedload(TestSession.endpoints)
        ).first()

    def get_recent_sessions(self, limit: int = 10) -> List[TestSession]:
        """Get most recent test sessions"""
        return self.session.query(TestSession).order_by(
            desc(TestSession.created_at)
        ).limit(limit).all()


class AsyncTestSessionRepository:
    """Async repository for TestSession operations"""

    def __init__(self, session: AsyncSession):
        """
        Initialize async repository

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def create(
        self,
        session_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> TestSession:
        """Create a new test session (async)"""
        test_session = TestSession(
            session_id=session_id,
            name=name,
            description=description,
            status='pending',
            started_at=datetime.now(),
            metadata_json=metadata or {}
        )

        self.session.add(test_session)
        await self.session.flush()

        return test_session

    async def get_by_id(self, id: int) -> Optional[TestSession]:
        """Get test session by ID (async)"""
        result = await self.session.execute(
            select(TestSession).filter(TestSession.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_session_id(self, session_id: str) -> Optional[TestSession]:
        """Get test session by session_id (async)"""
        result = await self.session.execute(
            select(TestSession).filter(TestSession.session_id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None
    ) -> List[TestSession]:
        """Get all test sessions with optional filtering (async)"""
        query = select(TestSession)

        if status:
            query = query.filter(TestSession.status == status)

        query = query.order_by(desc(TestSession.created_at))
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def update_status(self, session_id: str, status: str) -> bool:
        """Update session status (async)"""
        result = await self.session.execute(
            update(TestSession)
            .where(TestSession.session_id == session_id)
            .values(
                status=status,
                completed_at=datetime.now() if status == 'completed' else None
            )
        )

        return result.rowcount > 0

    async def update_test_counts(
        self,
        session_id: str,
        total: int,
        passed: int,
        failed: int
    ) -> bool:
        """Update test counts (async)"""
        result = await self.session.execute(
            update(TestSession)
            .where(TestSession.session_id == session_id)
            .values(
                total_tests=total,
                passed_tests=passed,
                failed_tests=failed
            )
        )

        return result.rowcount > 0

    async def delete(self, session_id: str) -> bool:
        """Delete test session (async)"""
        result = await self.session.execute(
            delete(TestSession).where(TestSession.session_id == session_id)
        )

        return result.rowcount > 0

    async def get_with_results(self, session_id: str) -> Optional[TestSession]:
        """Get session with all test results loaded (async)"""
        result = await self.session.execute(
            select(TestSession)
            .filter(TestSession.session_id == session_id)
            .options(
                joinedload(TestSession.test_results),
                joinedload(TestSession.endpoints)
            )
        )
        return result.scalar_one_or_none()

    async def get_recent_sessions(self, limit: int = 10) -> List[TestSession]:
        """Get most recent test sessions (async)"""
        result = await self.session.execute(
            select(TestSession)
            .order_by(desc(TestSession.created_at))
            .limit(limit)
        )
        return result.scalars().all()
