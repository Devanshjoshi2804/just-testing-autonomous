"""
Endpoint Repository
Data access layer for API endpoints
"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Endpoint, Constraint, TestResult


class EndpointRepository:
    """Repository for Endpoint operations"""

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
        path: str,
        method: str,
        description: Optional[str] = None,
        operation_id: Optional[str] = None,
        parameters: Optional[dict] = None,
        request_body: Optional[dict] = None,
        responses: Optional[dict] = None,
        requires_auth: bool = False,
        auth_type: Optional[str] = None
    ) -> Endpoint:
        """
        Create a new endpoint

        Args:
            session_id: Parent test session ID
            path: Endpoint path (e.g., /api/users)
            method: HTTP method (GET, POST, etc.)
            description: Endpoint description
            operation_id: OpenAPI operation ID
            parameters: Parameter definitions (JSON)
            request_body: Request body schema (JSON)
            responses: Response schemas (JSON)
            requires_auth: Whether authentication is required
            auth_type: Type of authentication (bearer, basic, etc.)

        Returns:
            Created Endpoint
        """
        endpoint = Endpoint(
            session_id=session_id,
            path=path,
            method=method.upper(),
            description=description,
            operation_id=operation_id,
            parameters_json=parameters or {},
            request_body_json=request_body or {},
            responses_json=responses or {},
            requires_auth=requires_auth,
            auth_type=auth_type
        )

        self.session.add(endpoint)
        self.session.flush()

        return endpoint

    def get_by_id(self, id: int) -> Optional[Endpoint]:
        """Get endpoint by ID"""
        return self.session.query(Endpoint).filter(Endpoint.id == id).first()

    def get_by_path_and_method(
        self,
        session_id: int,
        path: str,
        method: str
    ) -> Optional[Endpoint]:
        """Get endpoint by path and method within a session"""
        return self.session.query(Endpoint).filter(
            and_(
                Endpoint.session_id == session_id,
                Endpoint.path == path,
                Endpoint.method == method.upper()
            )
        ).first()

    def get_by_session(self, session_id: int) -> List[Endpoint]:
        """Get all endpoints for a test session"""
        return self.session.query(Endpoint).filter(
            Endpoint.session_id == session_id
        ).all()

    def get_with_constraints(self, id: int) -> Optional[Endpoint]:
        """Get endpoint with all constraints loaded"""
        return self.session.query(Endpoint).filter(
            Endpoint.id == id
        ).options(
            joinedload(Endpoint.constraints)
        ).first()

    def get_with_test_results(self, id: int) -> Optional[Endpoint]:
        """Get endpoint with all test results loaded"""
        return self.session.query(Endpoint).filter(
            Endpoint.id == id
        ).options(
            joinedload(Endpoint.test_results)
        ).first()

    def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        method: Optional[str] = None,
        requires_auth: Optional[bool] = None
    ) -> List[Endpoint]:
        """
        Get all endpoints with optional filtering

        Args:
            limit: Max number of results
            offset: Number of results to skip
            method: Filter by HTTP method
            requires_auth: Filter by authentication requirement

        Returns:
            List of Endpoint objects
        """
        query = self.session.query(Endpoint)

        if method:
            query = query.filter(Endpoint.method == method.upper())

        if requires_auth is not None:
            query = query.filter(Endpoint.requires_auth == requires_auth)

        query = query.limit(limit).offset(offset)

        return query.all()

    def update(
        self,
        id: int,
        description: Optional[str] = None,
        parameters: Optional[dict] = None,
        request_body: Optional[dict] = None,
        responses: Optional[dict] = None,
        requires_auth: Optional[bool] = None,
        auth_type: Optional[str] = None
    ) -> bool:
        """
        Update endpoint details

        Args:
            id: Endpoint ID
            description: New description
            parameters: New parameters
            request_body: New request body schema
            responses: New response schemas
            requires_auth: New auth requirement
            auth_type: New auth type

        Returns:
            True if updated, False if not found
        """
        updates = {'updated_at': datetime.now()}

        if description is not None:
            updates['description'] = description
        if parameters is not None:
            updates['parameters_json'] = parameters
        if request_body is not None:
            updates['request_body_json'] = request_body
        if responses is not None:
            updates['responses_json'] = responses
        if requires_auth is not None:
            updates['requires_auth'] = requires_auth
        if auth_type is not None:
            updates['auth_type'] = auth_type

        result = self.session.query(Endpoint).filter(
            Endpoint.id == id
        ).update(updates)

        return result > 0

    def delete(self, id: int) -> bool:
        """Delete endpoint and all related data (cascades to constraints and test results)"""
        result = self.session.query(Endpoint).filter(
            Endpoint.id == id
        ).delete()

        return result > 0

    def count_by_session(self, session_id: int) -> int:
        """Count endpoints in a session"""
        return self.session.query(Endpoint).filter(
            Endpoint.session_id == session_id
        ).count()

    def search_by_path_pattern(
        self,
        session_id: int,
        pattern: str
    ) -> List[Endpoint]:
        """
        Search endpoints by path pattern

        Args:
            session_id: Test session ID
            pattern: Path pattern (SQL LIKE syntax, e.g., '/api/users%')

        Returns:
            List of matching endpoints
        """
        return self.session.query(Endpoint).filter(
            and_(
                Endpoint.session_id == session_id,
                Endpoint.path.like(pattern)
            )
        ).all()


class AsyncEndpointRepository:
    """Async repository for Endpoint operations"""

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
        path: str,
        method: str,
        description: Optional[str] = None,
        operation_id: Optional[str] = None,
        parameters: Optional[dict] = None,
        request_body: Optional[dict] = None,
        responses: Optional[dict] = None,
        requires_auth: bool = False,
        auth_type: Optional[str] = None
    ) -> Endpoint:
        """Create a new endpoint (async)"""
        endpoint = Endpoint(
            session_id=session_id,
            path=path,
            method=method.upper(),
            description=description,
            operation_id=operation_id,
            parameters_json=parameters or {},
            request_body_json=request_body or {},
            responses_json=responses or {},
            requires_auth=requires_auth,
            auth_type=auth_type
        )

        self.session.add(endpoint)
        await self.session.flush()

        return endpoint

    async def get_by_id(self, id: int) -> Optional[Endpoint]:
        """Get endpoint by ID (async)"""
        result = await self.session.execute(
            select(Endpoint).filter(Endpoint.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_path_and_method(
        self,
        session_id: int,
        path: str,
        method: str
    ) -> Optional[Endpoint]:
        """Get endpoint by path and method (async)"""
        result = await self.session.execute(
            select(Endpoint).filter(
                and_(
                    Endpoint.session_id == session_id,
                    Endpoint.path == path,
                    Endpoint.method == method.upper()
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_by_session(self, session_id: int) -> List[Endpoint]:
        """Get all endpoints for a session (async)"""
        result = await self.session.execute(
            select(Endpoint).filter(Endpoint.session_id == session_id)
        )
        return result.scalars().all()

    async def get_with_constraints(self, id: int) -> Optional[Endpoint]:
        """Get endpoint with constraints loaded (async)"""
        result = await self.session.execute(
            select(Endpoint)
            .filter(Endpoint.id == id)
            .options(joinedload(Endpoint.constraints))
        )
        return result.scalar_one_or_none()

    async def get_with_test_results(self, id: int) -> Optional[Endpoint]:
        """Get endpoint with test results loaded (async)"""
        result = await self.session.execute(
            select(Endpoint)
            .filter(Endpoint.id == id)
            .options(joinedload(Endpoint.test_results))
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        method: Optional[str] = None,
        requires_auth: Optional[bool] = None
    ) -> List[Endpoint]:
        """Get all endpoints with optional filtering (async)"""
        query = select(Endpoint)

        if method:
            query = query.filter(Endpoint.method == method.upper())

        if requires_auth is not None:
            query = query.filter(Endpoint.requires_auth == requires_auth)

        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def update(
        self,
        id: int,
        description: Optional[str] = None,
        parameters: Optional[dict] = None,
        request_body: Optional[dict] = None,
        responses: Optional[dict] = None,
        requires_auth: Optional[bool] = None,
        auth_type: Optional[str] = None
    ) -> bool:
        """Update endpoint details (async)"""
        updates = {'updated_at': datetime.now()}

        if description is not None:
            updates['description'] = description
        if parameters is not None:
            updates['parameters_json'] = parameters
        if request_body is not None:
            updates['request_body_json'] = request_body
        if responses is not None:
            updates['responses_json'] = responses
        if requires_auth is not None:
            updates['requires_auth'] = requires_auth
        if auth_type is not None:
            updates['auth_type'] = auth_type

        result = await self.session.execute(
            update(Endpoint)
            .where(Endpoint.id == id)
            .values(**updates)
        )

        return result.rowcount > 0

    async def delete(self, id: int) -> bool:
        """Delete endpoint (async)"""
        result = await self.session.execute(
            delete(Endpoint).where(Endpoint.id == id)
        )

        return result.rowcount > 0

    async def count_by_session(self, session_id: int) -> int:
        """Count endpoints in a session (async)"""
        result = await self.session.execute(
            select(Endpoint).filter(Endpoint.session_id == session_id)
        )
        return len(result.scalars().all())

    async def search_by_path_pattern(
        self,
        session_id: int,
        pattern: str
    ) -> List[Endpoint]:
        """Search endpoints by path pattern (async)"""
        result = await self.session.execute(
            select(Endpoint).filter(
                and_(
                    Endpoint.session_id == session_id,
                    Endpoint.path.like(pattern)
                )
            )
        )
        return result.scalars().all()
