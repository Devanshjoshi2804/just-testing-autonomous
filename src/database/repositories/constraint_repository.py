"""
Constraint Repository
Data access layer for parameter constraints
"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, update, delete, and_, or_, desc
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Constraint


class ConstraintRepository:
    """Repository for Constraint operations"""

    def __init__(self, session: Session):
        """
        Initialize repository

        Args:
            session: SQLAlchemy session
        """
        self.session = session

    def create(
        self,
        endpoint_id: int,
        parameter_name: str,
        parameter_type: str,
        constraint_type: str,
        constraint_value: Optional[str] = None,
        is_required: bool = False,
        confidence: float = 1.0,
        description: Optional[str] = None,
        source: Optional[str] = None
    ) -> Constraint:
        """
        Create a new constraint

        Args:
            endpoint_id: Parent endpoint ID
            parameter_name: Parameter name
            parameter_type: Type (string, integer, number, boolean, array, object)
            constraint_type: Constraint type (min_value, max_value, min_length, max_length, pattern, enum, format)
            constraint_value: Constraint value
            is_required: Whether parameter is required
            confidence: Confidence score (0.0 to 1.0)
            description: Constraint description
            source: Source of constraint (openapi, documentation, learned)

        Returns:
            Created Constraint
        """
        constraint = Constraint(
            endpoint_id=endpoint_id,
            parameter_name=parameter_name,
            parameter_type=parameter_type,
            constraint_type=constraint_type,
            constraint_value=constraint_value,
            is_required=is_required,
            confidence=confidence,
            description=description,
            source=source
        )

        self.session.add(constraint)
        self.session.flush()

        return constraint

    def get_by_id(self, id: int) -> Optional[Constraint]:
        """Get constraint by ID"""
        return self.session.query(Constraint).filter(Constraint.id == id).first()

    def get_by_endpoint(self, endpoint_id: int) -> List[Constraint]:
        """Get all constraints for an endpoint"""
        return self.session.query(Constraint).filter(
            Constraint.endpoint_id == endpoint_id
        ).all()

    def get_by_parameter(
        self,
        endpoint_id: int,
        parameter_name: str
    ) -> List[Constraint]:
        """Get all constraints for a specific parameter"""
        return self.session.query(Constraint).filter(
            and_(
                Constraint.endpoint_id == endpoint_id,
                Constraint.parameter_name == parameter_name
            )
        ).all()

    def get_required_parameters(self, endpoint_id: int) -> List[Constraint]:
        """Get all required parameter constraints"""
        return self.session.query(Constraint).filter(
            and_(
                Constraint.endpoint_id == endpoint_id,
                Constraint.is_required == True
            )
        ).all()

    def get_by_source(
        self,
        endpoint_id: int,
        source: str
    ) -> List[Constraint]:
        """
        Get constraints by source

        Args:
            endpoint_id: Endpoint ID
            source: Source (openapi, documentation, learned)

        Returns:
            List of constraints
        """
        return self.session.query(Constraint).filter(
            and_(
                Constraint.endpoint_id == endpoint_id,
                Constraint.source == source
            )
        ).all()

    def get_by_confidence_threshold(
        self,
        endpoint_id: int,
        min_confidence: float = 0.7
    ) -> List[Constraint]:
        """Get constraints above a confidence threshold"""
        return self.session.query(Constraint).filter(
            and_(
                Constraint.endpoint_id == endpoint_id,
                Constraint.confidence >= min_confidence
            )
        ).all()

    def update_confidence(
        self,
        id: int,
        confidence: float
    ) -> bool:
        """
        Update constraint confidence score

        Args:
            id: Constraint ID
            confidence: New confidence score (0.0 to 1.0)

        Returns:
            True if updated, False if not found
        """
        result = self.session.query(Constraint).filter(
            Constraint.id == id
        ).update({'confidence': confidence})

        return result > 0

    def update(
        self,
        id: int,
        constraint_value: Optional[str] = None,
        is_required: Optional[bool] = None,
        confidence: Optional[float] = None,
        description: Optional[str] = None
    ) -> bool:
        """
        Update constraint details

        Args:
            id: Constraint ID
            constraint_value: New constraint value
            is_required: New required flag
            confidence: New confidence score
            description: New description

        Returns:
            True if updated, False if not found
        """
        updates = {}

        if constraint_value is not None:
            updates['constraint_value'] = constraint_value
        if is_required is not None:
            updates['is_required'] = is_required
        if confidence is not None:
            updates['confidence'] = confidence
        if description is not None:
            updates['description'] = description

        if not updates:
            return False

        result = self.session.query(Constraint).filter(
            Constraint.id == id
        ).update(updates)

        return result > 0

    def delete(self, id: int) -> bool:
        """Delete constraint"""
        result = self.session.query(Constraint).filter(
            Constraint.id == id
        ).delete()

        return result > 0

    def delete_by_endpoint(self, endpoint_id: int) -> int:
        """Delete all constraints for an endpoint"""
        result = self.session.query(Constraint).filter(
            Constraint.endpoint_id == endpoint_id
        ).delete()

        return result

    def count_by_endpoint(self, endpoint_id: int) -> int:
        """Count constraints for an endpoint"""
        return self.session.query(Constraint).filter(
            Constraint.endpoint_id == endpoint_id
        ).count()

    def find_or_create(
        self,
        endpoint_id: int,
        parameter_name: str,
        constraint_type: str,
        constraint_value: Optional[str] = None,
        **kwargs
    ) -> Constraint:
        """
        Find existing constraint or create new one

        Args:
            endpoint_id: Endpoint ID
            parameter_name: Parameter name
            constraint_type: Constraint type
            constraint_value: Constraint value
            **kwargs: Additional constraint attributes

        Returns:
            Existing or new Constraint
        """
        # Try to find existing
        existing = self.session.query(Constraint).filter(
            and_(
                Constraint.endpoint_id == endpoint_id,
                Constraint.parameter_name == parameter_name,
                Constraint.constraint_type == constraint_type
            )
        ).first()

        if existing:
            # Update confidence if it's higher
            if 'confidence' in kwargs and kwargs['confidence'] > existing.confidence:
                existing.confidence = kwargs['confidence']
            return existing

        # Create new
        return self.create(
            endpoint_id=endpoint_id,
            parameter_name=parameter_name,
            constraint_type=constraint_type,
            constraint_value=constraint_value,
            **kwargs
        )


class AsyncConstraintRepository:
    """Async repository for Constraint operations"""

    def __init__(self, session: AsyncSession):
        """
        Initialize async repository

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def create(
        self,
        endpoint_id: int,
        parameter_name: str,
        parameter_type: str,
        constraint_type: str,
        constraint_value: Optional[str] = None,
        is_required: bool = False,
        confidence: float = 1.0,
        description: Optional[str] = None,
        source: Optional[str] = None
    ) -> Constraint:
        """Create a new constraint (async)"""
        constraint = Constraint(
            endpoint_id=endpoint_id,
            parameter_name=parameter_name,
            parameter_type=parameter_type,
            constraint_type=constraint_type,
            constraint_value=constraint_value,
            is_required=is_required,
            confidence=confidence,
            description=description,
            source=source
        )

        self.session.add(constraint)
        await self.session.flush()

        return constraint

    async def get_by_id(self, id: int) -> Optional[Constraint]:
        """Get constraint by ID (async)"""
        result = await self.session.execute(
            select(Constraint).filter(Constraint.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_endpoint(self, endpoint_id: int) -> List[Constraint]:
        """Get all constraints for an endpoint (async)"""
        result = await self.session.execute(
            select(Constraint).filter(Constraint.endpoint_id == endpoint_id)
        )
        return result.scalars().all()

    async def get_by_parameter(
        self,
        endpoint_id: int,
        parameter_name: str
    ) -> List[Constraint]:
        """Get all constraints for a specific parameter (async)"""
        result = await self.session.execute(
            select(Constraint).filter(
                and_(
                    Constraint.endpoint_id == endpoint_id,
                    Constraint.parameter_name == parameter_name
                )
            )
        )
        return result.scalars().all()

    async def get_required_parameters(self, endpoint_id: int) -> List[Constraint]:
        """Get all required parameter constraints (async)"""
        result = await self.session.execute(
            select(Constraint).filter(
                and_(
                    Constraint.endpoint_id == endpoint_id,
                    Constraint.is_required == True
                )
            )
        )
        return result.scalars().all()

    async def get_by_source(
        self,
        endpoint_id: int,
        source: str
    ) -> List[Constraint]:
        """Get constraints by source (async)"""
        result = await self.session.execute(
            select(Constraint).filter(
                and_(
                    Constraint.endpoint_id == endpoint_id,
                    Constraint.source == source
                )
            )
        )
        return result.scalars().all()

    async def get_by_confidence_threshold(
        self,
        endpoint_id: int,
        min_confidence: float = 0.7
    ) -> List[Constraint]:
        """Get constraints above a confidence threshold (async)"""
        result = await self.session.execute(
            select(Constraint).filter(
                and_(
                    Constraint.endpoint_id == endpoint_id,
                    Constraint.confidence >= min_confidence
                )
            )
        )
        return result.scalars().all()

    async def update_confidence(
        self,
        id: int,
        confidence: float
    ) -> bool:
        """Update constraint confidence score (async)"""
        result = await self.session.execute(
            update(Constraint)
            .where(Constraint.id == id)
            .values(confidence=confidence)
        )

        return result.rowcount > 0

    async def update(
        self,
        id: int,
        constraint_value: Optional[str] = None,
        is_required: Optional[bool] = None,
        confidence: Optional[float] = None,
        description: Optional[str] = None
    ) -> bool:
        """Update constraint details (async)"""
        updates = {}

        if constraint_value is not None:
            updates['constraint_value'] = constraint_value
        if is_required is not None:
            updates['is_required'] = is_required
        if confidence is not None:
            updates['confidence'] = confidence
        if description is not None:
            updates['description'] = description

        if not updates:
            return False

        result = await self.session.execute(
            update(Constraint)
            .where(Constraint.id == id)
            .values(**updates)
        )

        return result.rowcount > 0

    async def delete(self, id: int) -> bool:
        """Delete constraint (async)"""
        result = await self.session.execute(
            delete(Constraint).where(Constraint.id == id)
        )

        return result.rowcount > 0

    async def delete_by_endpoint(self, endpoint_id: int) -> int:
        """Delete all constraints for an endpoint (async)"""
        result = await self.session.execute(
            delete(Constraint).where(Constraint.endpoint_id == endpoint_id)
        )

        return result.rowcount

    async def count_by_endpoint(self, endpoint_id: int) -> int:
        """Count constraints for an endpoint (async)"""
        result = await self.session.execute(
            select(Constraint).filter(Constraint.endpoint_id == endpoint_id)
        )
        return len(result.scalars().all())

    async def find_or_create(
        self,
        endpoint_id: int,
        parameter_name: str,
        constraint_type: str,
        constraint_value: Optional[str] = None,
        **kwargs
    ) -> Constraint:
        """Find existing constraint or create new one (async)"""
        # Try to find existing
        result = await self.session.execute(
            select(Constraint).filter(
                and_(
                    Constraint.endpoint_id == endpoint_id,
                    Constraint.parameter_name == parameter_name,
                    Constraint.constraint_type == constraint_type
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update confidence if it's higher
            if 'confidence' in kwargs and kwargs['confidence'] > existing.confidence:
                existing.confidence = kwargs['confidence']
                await self.session.flush()
            return existing

        # Create new
        return await self.create(
            endpoint_id=endpoint_id,
            parameter_name=parameter_name,
            constraint_type=constraint_type,
            constraint_value=constraint_value,
            **kwargs
        )
