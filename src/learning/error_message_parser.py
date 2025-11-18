"""
Error Message Parser
Parses API error messages and extracts constraint information
"""
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

try:
    from loguru import logger
except ImportError:
    class MockLogger:
        def info(self, msg, **kwargs): pass
        def warning(self, msg, **kwargs): pass
        def error(self, msg, **kwargs): pass
        def debug(self, msg, **kwargs): pass
    logger = MockLogger()


class ConstraintType(Enum):
    """Types of constraints that can be learned"""
    MINIMUM = "minimum"
    MAXIMUM = "maximum"
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    FORMAT = "format"
    ENUM = "enum"
    REQUIRED = "required"
    PATTERN = "pattern"
    TYPE = "type"
    UNIQUE = "unique"


@dataclass
class ParsedConstraint:
    """A constraint parsed from an error message"""
    constraint_type: ConstraintType
    field_name: str
    value: Any
    confidence: float  # 0.0 to 1.0
    error_message: str
    endpoint: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'constraint_type': self.constraint_type.value,
            'field_name': self.field_name,
            'value': self.value,
            'confidence': self.confidence,
            'error_message': self.error_message,
            'endpoint': self.endpoint
        }


class ErrorMessageParser:
    """
    Parse error messages and extract constraint information

    Patterns recognized:
    - Minimum/maximum values: "age must be >= 18", "price should be at least 0"
    - String length: "name must be at least 3 characters", "max length is 100"
    - Required fields: "field 'email' is required", "missing required field"
    - Format: "invalid email format", "must be a valid URL"
    - Enum: "status must be one of: active, inactive"
    - Type: "expected integer but got string"
    - Unique: "email already exists", "duplicate value"
    """

    # Regex patterns for constraint extraction
    PATTERNS = {
        # Minimum value patterns
        ConstraintType.MINIMUM: [
            r'(\w+)\s+must\s+be\s+>=?\s+(\d+\.?\d*)',
            r'(\w+)\s+should\s+be\s+at\s+least\s+(\d+\.?\d*)',
            r'(\w+)\s+cannot\s+be\s+less\s+than\s+(\d+\.?\d*)',
            r'minimum\s+(\w+)\s+is\s+(\d+\.?\d*)',
            r'(\w+)\s+minimum:\s+(\d+\.?\d*)',
        ],

        # Maximum value patterns
        ConstraintType.MAXIMUM: [
            r'(\w+)\s+must\s+be\s+<=?\s+(\d+\.?\d*)',
            r'(\w+)\s+should\s+be\s+at\s+most\s+(\d+\.?\d*)',
            r'(\w+)\s+cannot\s+exceed\s+(\d+\.?\d*)',
            r'maximum\s+(\w+)\s+is\s+(\d+\.?\d*)',
            r'(\w+)\s+maximum:\s+(\d+\.?\d*)',
        ],

        # Min length patterns
        ConstraintType.MIN_LENGTH: [
            r'(\w+)\s+must\s+be\s+at\s+least\s+(\d+)\s+characters?',
            r'(\w+)\s+length\s+must\s+be\s+>=?\s+(\d+)',
            r'minimum\s+length\s+for\s+(\w+)\s+is\s+(\d+)',
        ],

        # Max length patterns
        ConstraintType.MAX_LENGTH: [
            r'(\w+)\s+must\s+be\s+at\s+most\s+(\d+)\s+characters?',
            r'(\w+)\s+length\s+must\s+be\s+<=?\s+(\d+)',
            r'maximum\s+length\s+for\s+(\w+)\s+is\s+(\d+)',
            r'(\w+)\s+exceeds\s+maximum\s+length\s+of\s+(\d+)',
        ],

        # Format patterns
        ConstraintType.FORMAT: [
            r'invalid\s+(\w+)\s+format',
            r'(\w+)\s+must\s+be\s+a\s+valid\s+(\w+)',
            r'(\w+)\s+should\s+match\s+format:\s+(\w+)',
        ],

        # Enum patterns
        ConstraintType.ENUM: [
            r'(\w+)\s+must\s+be\s+one\s+of:\s+(.*)',
            r'(\w+)\s+should\s+be\s+one\s+of\s+\[(.*)\]',
            r'allowed\s+values\s+for\s+(\w+):\s+(.*)',
            r'(\w+)\s+must\s+be\s+(?:either\s+)?([^,]+(?:,\s*[^,]+)*)',
        ],

        # Required field patterns
        ConstraintType.REQUIRED: [
            r'field\s+[\'"]?(\w+)[\'"]?\s+is\s+required',
            r'missing\s+required\s+field:\s+[\'"]?(\w+)[\'"]?',
            r'(\w+)\s+is\s+required',
            r'required\s+field\s+[\'"]?(\w+)[\'"]?\s+not\s+provided',
        ],

        # Type patterns
        ConstraintType.TYPE: [
            r'(\w+)\s+must\s+be\s+(?:a|an)\s+(\w+)',
            r'expected\s+(\w+)\s+for\s+(\w+)',
            r'(\w+)\s+should\s+be\s+(?:a|an)\s+(\w+)',
        ],

        # Unique patterns
        ConstraintType.UNIQUE: [
            r'(\w+)\s+already\s+exists',
            r'duplicate\s+(\w+)',
            r'(\w+)\s+must\s+be\s+unique',
        ],
    }

    def __init__(self):
        """Initialize error message parser"""
        self.parsed_count = 0
        self.learned_constraints = []

    def parse_error_message(
        self,
        error_message: str,
        field_name: Optional[str] = None,
        endpoint: Optional[str] = None
    ) -> List[ParsedConstraint]:
        """
        Parse an error message and extract constraints

        Args:
            error_message: The error message text
            field_name: Optional field name if known
            endpoint: Optional endpoint where error occurred

        Returns:
            List of ParsedConstraint objects
        """
        constraints = []
        error_lower = error_message.lower()

        # Try each constraint type
        for constraint_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, error_lower, re.IGNORECASE)

                for match in matches:
                    try:
                        constraint = self._extract_constraint(
                            constraint_type,
                            match,
                            error_message,
                            field_name,
                            endpoint
                        )

                        if constraint:
                            constraints.append(constraint)
                            self.parsed_count += 1

                    except Exception as e:
                        logger.debug(f"Failed to extract constraint from match: {e}")

        return constraints

    def _extract_constraint(
        self,
        constraint_type: ConstraintType,
        match: re.Match,
        error_message: str,
        field_name: Optional[str],
        endpoint: Optional[str]
    ) -> Optional[ParsedConstraint]:
        """Extract constraint from regex match"""

        groups = match.groups()

        if constraint_type in [ConstraintType.MINIMUM, ConstraintType.MAXIMUM]:
            # Format: (field_name, value)
            if len(groups) >= 2:
                extracted_field = groups[0]
                value_str = groups[1]

                # Try to parse as number
                try:
                    value = float(value_str) if '.' in value_str else int(value_str)
                except ValueError:
                    return None

                return ParsedConstraint(
                    constraint_type=constraint_type,
                    field_name=field_name or extracted_field,
                    value=value,
                    confidence=0.9,
                    error_message=error_message,
                    endpoint=endpoint
                )

        elif constraint_type in [ConstraintType.MIN_LENGTH, ConstraintType.MAX_LENGTH]:
            # Format: (field_name, length)
            if len(groups) >= 2:
                extracted_field = groups[0]
                length_str = groups[1]

                try:
                    length = int(length_str)
                except ValueError:
                    return None

                return ParsedConstraint(
                    constraint_type=constraint_type,
                    field_name=field_name or extracted_field,
                    value=length,
                    confidence=0.9,
                    error_message=error_message,
                    endpoint=endpoint
                )

        elif constraint_type == ConstraintType.FORMAT:
            # Format: (field_name, format_type) or just (field_name,)
            if len(groups) >= 1:
                extracted_field = groups[0]
                format_type = groups[1] if len(groups) > 1 else self._infer_format(extracted_field)

                return ParsedConstraint(
                    constraint_type=constraint_type,
                    field_name=field_name or extracted_field,
                    value=format_type,
                    confidence=0.8,
                    error_message=error_message,
                    endpoint=endpoint
                )

        elif constraint_type == ConstraintType.ENUM:
            # Format: (field_name, values_string)
            if len(groups) >= 2:
                extracted_field = groups[0]
                values_str = groups[1]

                # Parse comma-separated values
                values = [v.strip().strip('\'"') for v in values_str.split(',')]
                values = [v for v in values if v]  # Remove empty

                if values:
                    return ParsedConstraint(
                        constraint_type=constraint_type,
                        field_name=field_name or extracted_field,
                        value=values,
                        confidence=0.85,
                        error_message=error_message,
                        endpoint=endpoint
                    )

        elif constraint_type == ConstraintType.REQUIRED:
            # Format: (field_name,)
            if len(groups) >= 1:
                extracted_field = groups[0]

                return ParsedConstraint(
                    constraint_type=constraint_type,
                    field_name=field_name or extracted_field,
                    value=True,
                    confidence=0.95,
                    error_message=error_message,
                    endpoint=endpoint
                )

        elif constraint_type == ConstraintType.TYPE:
            # Format: (field_name, type) or (type, field_name)
            if len(groups) >= 2:
                # Try to determine which group is field name vs type
                field1, field2 = groups[0], groups[1]

                if field2 in ['string', 'number', 'integer', 'boolean', 'array', 'object']:
                    extracted_field = field1
                    type_value = field2
                else:
                    extracted_field = field2
                    type_value = field1

                return ParsedConstraint(
                    constraint_type=constraint_type,
                    field_name=field_name or extracted_field,
                    value=type_value,
                    confidence=0.85,
                    error_message=error_message,
                    endpoint=endpoint
                )

        elif constraint_type == ConstraintType.UNIQUE:
            # Format: (field_name,)
            if len(groups) >= 1:
                extracted_field = groups[0]

                return ParsedConstraint(
                    constraint_type=constraint_type,
                    field_name=field_name or extracted_field,
                    value=True,
                    confidence=0.9,
                    error_message=error_message,
                    endpoint=endpoint
                )

        return None

    def _infer_format(self, field_name: str) -> str:
        """Infer format type from field name"""
        field_lower = field_name.lower()

        if 'email' in field_lower:
            return 'email'
        elif 'url' in field_lower or 'uri' in field_lower:
            return 'uri'
        elif 'uuid' in field_lower or 'guid' in field_lower:
            return 'uuid'
        elif 'date' in field_lower:
            return 'date'
        elif 'time' in field_lower:
            return 'date-time'
        elif 'phone' in field_lower:
            return 'phone'
        elif 'ip' in field_lower:
            return 'ipv4'
        else:
            return 'string'

    def parse_error_response(
        self,
        response_body: Dict[str, Any],
        status_code: int,
        endpoint: Optional[str] = None
    ) -> List[ParsedConstraint]:
        """
        Parse error response and extract constraints

        Args:
            response_body: Error response body (usually JSON)
            status_code: HTTP status code
            endpoint: Optional endpoint where error occurred

        Returns:
            List of ParsedConstraint objects
        """
        constraints = []

        # Extract error message
        error_message = self._extract_error_message(response_body)

        if error_message:
            # Parse main error message
            constraints.extend(
                self.parse_error_message(error_message, endpoint=endpoint)
            )

        # Check for field-specific errors in details
        if 'details' in response_body and isinstance(response_body['details'], dict):
            for field_name, field_error in response_body['details'].items():
                if isinstance(field_error, str):
                    constraints.extend(
                        self.parse_error_message(field_error, field_name, endpoint)
                    )

        # Check for validation errors array
        if 'errors' in response_body and isinstance(response_body['errors'], list):
            for error_item in response_body['errors']:
                if isinstance(error_item, dict):
                    field_name = error_item.get('field') or error_item.get('param')
                    message = error_item.get('message') or error_item.get('msg')

                    if message:
                        constraints.extend(
                            self.parse_error_message(message, field_name, endpoint)
                        )

        return constraints

    def _extract_error_message(self, response_body: Dict[str, Any]) -> Optional[str]:
        """Extract error message from response body"""
        # Try common fields
        for field in ['message', 'error', 'detail', 'description']:
            if field in response_body and isinstance(response_body[field], str):
                return response_body[field]

        # If response_body itself is a string
        if isinstance(response_body, str):
            return response_body

        return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get parsing statistics"""
        constraint_type_counts = {}

        for constraint in self.learned_constraints:
            ct = constraint.constraint_type.value
            constraint_type_counts[ct] = constraint_type_counts.get(ct, 0) + 1

        return {
            'total_parsed': self.parsed_count,
            'by_type': constraint_type_counts
        }
