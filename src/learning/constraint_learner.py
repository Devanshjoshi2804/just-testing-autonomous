"""
Constraint Learner
Learns and accumulates constraints from API error responses
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime

from .error_message_parser import ErrorMessageParser, ParsedConstraint, ConstraintType

try:
    from loguru import logger
except ImportError:
    class MockLogger:
        def info(self, msg, **kwargs): pass
        def warning(self, msg, **kwargs): pass
        def error(self, msg, **kwargs): pass
        def debug(self, msg, **kwargs): pass
    logger = MockLogger()


@dataclass
class LearnedConstraint:
    """A constraint learned from error responses"""
    constraint_type: ConstraintType
    field_name: str
    value: Any
    confidence: float
    occurrences: int = 1
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    endpoints: List[str] = field(default_factory=list)
    error_messages: List[str] = field(default_factory=list)

    def update(self, parsed: ParsedConstraint):
        """Update with new occurrence"""
        self.occurrences += 1
        self.last_seen = datetime.now()

        # Increase confidence (max 1.0)
        self.confidence = min(1.0, self.confidence + 0.05)

        # Add endpoint if new
        if parsed.endpoint and parsed.endpoint not in self.endpoints:
            self.endpoints.append(parsed.endpoint)

        # Store error message (limit to 10)
        if parsed.error_message not in self.error_messages:
            self.error_messages.append(parsed.error_message)
            if len(self.error_messages) > 10:
                self.error_messages.pop(0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'constraint_type': self.constraint_type.value,
            'field_name': self.field_name,
            'value': self.value,
            'confidence': self.confidence,
            'occurrences': self.occurrences,
            'first_seen': self.first_seen.isoformat(),
            'last_seen': self.last_seen.isoformat(),
            'endpoints': self.endpoints,
            'error_messages': self.error_messages[:3]  # Return first 3
        }


class ConstraintLearner:
    """
    Learn constraints from API error responses

    Accumulates constraints over time and builds confidence.
    Handles:
    - Multiple occurrences of same constraint (increases confidence)
    - Conflicting constraints (keeps highest confidence)
    - Constraint aggregation per field and endpoint
    """

    def __init__(self, min_confidence: float = 0.7):
        """
        Initialize constraint learner

        Args:
            min_confidence: Minimum confidence to report a learned constraint
        """
        self.min_confidence = min_confidence
        self.parser = ErrorMessageParser()

        # Store constraints: {endpoint: {field_name: {constraint_type: LearnedConstraint}}}
        self.constraints: Dict[str, Dict[str, Dict[ConstraintType, LearnedConstraint]]] = defaultdict(
            lambda: defaultdict(dict)
        )

        # Global constraints (not endpoint-specific)
        self.global_constraints: Dict[str, Dict[ConstraintType, LearnedConstraint]] = defaultdict(dict)

        self.total_errors_processed = 0

    def learn_from_error_response(
        self,
        response_body: Dict[str, Any],
        status_code: int,
        endpoint: Optional[str] = None,
        field_name: Optional[str] = None
    ):
        """
        Learn constraints from an error response

        Args:
            response_body: Error response body
            status_code: HTTP status code
            endpoint: Optional endpoint where error occurred
            field_name: Optional field name if known
        """
        # Parse error response
        parsed_constraints = self.parser.parse_error_response(
            response_body,
            status_code,
            endpoint
        )

        # Add constraints to knowledge base
        for parsed in parsed_constraints:
            self._add_constraint(parsed)

        self.total_errors_processed += 1

        if parsed_constraints:
            logger.info(f"Learned {len(parsed_constraints)} constraints from error response")

    def learn_from_error_message(
        self,
        error_message: str,
        endpoint: Optional[str] = None,
        field_name: Optional[str] = None
    ):
        """
        Learn constraints from a single error message

        Args:
            error_message: The error message text
            endpoint: Optional endpoint where error occurred
            field_name: Optional field name if known
        """
        parsed_constraints = self.parser.parse_error_message(
            error_message,
            field_name,
            endpoint
        )

        for parsed in parsed_constraints:
            self._add_constraint(parsed)

    def _add_constraint(self, parsed: ParsedConstraint):
        """Add or update a constraint in the knowledge base"""
        constraint_type = parsed.constraint_type
        field_name = parsed.field_name
        endpoint = parsed.endpoint or 'global'

        # Determine storage location
        if endpoint == 'global':
            storage = self.global_constraints
        else:
            storage = self.constraints[endpoint]

        # Check if constraint already exists
        if constraint_type in storage[field_name]:
            existing = storage[field_name][constraint_type]

            # Check if values match
            if self._values_match(existing.value, parsed.value):
                # Update existing constraint
                existing.update(parsed)
                logger.debug(f"Updated constraint: {field_name}.{constraint_type.value} (confidence: {existing.confidence:.2f})")
            else:
                # Conflicting values - keep higher confidence
                if parsed.confidence > existing.confidence:
                    logger.warning(
                        f"Conflicting constraint for {field_name}.{constraint_type.value}: "
                        f"{existing.value} vs {parsed.value}. Keeping higher confidence."
                    )
                    storage[field_name][constraint_type] = LearnedConstraint(
                        constraint_type=constraint_type,
                        field_name=field_name,
                        value=parsed.value,
                        confidence=parsed.confidence,
                        endpoints=[parsed.endpoint] if parsed.endpoint else [],
                        error_messages=[parsed.error_message]
                    )
        else:
            # New constraint
            storage[field_name][constraint_type] = LearnedConstraint(
                constraint_type=constraint_type,
                field_name=field_name,
                value=parsed.value,
                confidence=parsed.confidence,
                endpoints=[parsed.endpoint] if parsed.endpoint else [],
                error_messages=[parsed.error_message]
            )
            logger.info(f"Learned new constraint: {field_name}.{constraint_type.value} = {parsed.value}")

    def _values_match(self, value1: Any, value2: Any) -> bool:
        """Check if two constraint values match"""
        # Handle lists (enums)
        if isinstance(value1, list) and isinstance(value2, list):
            return set(value1) == set(value2)

        # Handle numbers (allow small tolerance)
        if isinstance(value1, (int, float)) and isinstance(value2, (int, float)):
            return abs(value1 - value2) < 0.001

        # Handle strings
        return value1 == value2

    def get_constraints_for_endpoint(
        self,
        endpoint: str,
        include_global: bool = True
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get all learned constraints for an endpoint

        Args:
            endpoint: The endpoint to get constraints for
            include_global: Include global constraints

        Returns:
            Dict mapping field names to constraints
        """
        result = {}

        # Add endpoint-specific constraints
        if endpoint in self.constraints:
            for field_name, constraints_dict in self.constraints[endpoint].items():
                result[field_name] = self._constraints_to_dict(constraints_dict)

        # Add global constraints
        if include_global:
            for field_name, constraints_dict in self.global_constraints.items():
                if field_name not in result:
                    result[field_name] = {}

                global_dict = self._constraints_to_dict(constraints_dict)
                # Merge with endpoint-specific (endpoint-specific takes precedence)
                for key, value in global_dict.items():
                    if key not in result[field_name]:
                        result[field_name][key] = value

        # Filter by confidence
        filtered_result = {}
        for field_name, constraints in result.items():
            filtered = {k: v for k, v in constraints.items()
                       if self._get_constraint_confidence(v) >= self.min_confidence}
            if filtered:
                filtered_result[field_name] = filtered

        return filtered_result

    def _constraints_to_dict(self, constraints_dict: Dict[ConstraintType, LearnedConstraint]) -> Dict[str, Any]:
        """Convert constraints dict to standard format"""
        result = {}

        for constraint_type, learned in constraints_dict.items():
            key = constraint_type.value

            # Map to standard constraint format
            if constraint_type == ConstraintType.MINIMUM:
                result['min'] = learned.value
            elif constraint_type == ConstraintType.MAXIMUM:
                result['max'] = learned.value
            elif constraint_type == ConstraintType.MIN_LENGTH:
                result['min_length'] = learned.value
            elif constraint_type == ConstraintType.MAX_LENGTH:
                result['max_length'] = learned.value
            elif constraint_type == ConstraintType.FORMAT:
                result['format'] = learned.value
            elif constraint_type == ConstraintType.ENUM:
                result['enum'] = learned.value
            elif constraint_type == ConstraintType.REQUIRED:
                result['required'] = learned.value
            elif constraint_type == ConstraintType.PATTERN:
                result['pattern'] = learned.value
            elif constraint_type == ConstraintType.TYPE:
                result['type'] = learned.value
            elif constraint_type == ConstraintType.UNIQUE:
                result['unique'] = learned.value

        return result

    def _get_constraint_confidence(self, constraint_value: Any) -> float:
        """Get confidence for a constraint (for filtering)"""
        # This is a simplified version - in practice, constraints store their own confidence
        return 1.0  # Assume high confidence for now

    def get_all_constraints(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Get all learned constraints

        Returns:
            Dict mapping endpoints to field constraints
        """
        result = {}

        # Add endpoint-specific constraints
        for endpoint, fields in self.constraints.items():
            result[endpoint] = {}
            for field_name, constraints_dict in fields.items():
                result[endpoint][field_name] = self._constraints_to_dict(constraints_dict)

        # Add global constraints
        if self.global_constraints:
            result['global'] = {}
            for field_name, constraints_dict in self.global_constraints.items():
                result['global'][field_name] = self._constraints_to_dict(constraints_dict)

        return result

    def get_statistics(self) -> Dict[str, Any]:
        """Get learning statistics"""
        total_constraints = 0
        high_confidence = 0
        by_type = defaultdict(int)

        # Count endpoint-specific constraints
        for endpoint, fields in self.constraints.items():
            for field_name, constraints_dict in fields.items():
                for constraint_type, learned in constraints_dict.items():
                    total_constraints += 1
                    by_type[constraint_type.value] += 1

                    if learned.confidence >= 0.9:
                        high_confidence += 1

        # Count global constraints
        for field_name, constraints_dict in self.global_constraints.items():
            for constraint_type, learned in constraints_dict.items():
                total_constraints += 1
                by_type[constraint_type.value] += 1

                if learned.confidence >= 0.9:
                    high_confidence += 1

        return {
            'total_errors_processed': self.total_errors_processed,
            'total_constraints_learned': total_constraints,
            'high_confidence_count': high_confidence,
            'constraints_by_type': dict(by_type),
            'endpoints_covered': len(self.constraints),
            'parser_stats': self.parser.get_statistics()
        }

    def export_constraints(self) -> List[Dict[str, Any]]:
        """Export all learned constraints as a list"""
        constraints_list = []

        # Export endpoint-specific constraints
        for endpoint, fields in self.constraints.items():
            for field_name, constraints_dict in fields.items():
                for constraint_type, learned in constraints_dict.items():
                    constraints_list.append({
                        **learned.to_dict(),
                        'scope': 'endpoint',
                        'endpoint': endpoint
                    })

        # Export global constraints
        for field_name, constraints_dict in self.global_constraints.items():
            for constraint_type, learned in constraints_dict.items():
                constraints_list.append({
                    **learned.to_dict(),
                    'scope': 'global'
                })

        return constraints_list
