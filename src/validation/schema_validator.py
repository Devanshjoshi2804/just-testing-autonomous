"""
Schema Validator
Validates API responses against OpenAPI schemas
"""
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
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


class ViolationType(Enum):
    """Types of schema violations"""
    MISSING_REQUIRED_FIELD = "missing_required_field"
    WRONG_TYPE = "wrong_type"
    UNEXPECTED_FIELD = "unexpected_field"
    INVALID_FORMAT = "invalid_format"
    OUT_OF_RANGE = "out_of_range"
    INVALID_ENUM_VALUE = "invalid_enum_value"
    ARRAY_ITEM_INVALID = "array_item_invalid"
    MISSING_PROPERTY = "missing_property"


class Severity(Enum):
    """Severity levels for violations"""
    CRITICAL = "critical"  # Missing required field, wrong type for required field
    HIGH = "high"  # Wrong type for optional field, invalid format
    MEDIUM = "medium"  # Unexpected field in strict mode
    LOW = "low"  # Unexpected field in permissive mode


@dataclass
class SchemaViolation:
    """A single schema validation violation"""
    violation_type: ViolationType
    severity: Severity
    field_path: str
    expected: str
    actual: str
    description: str


@dataclass
class ValidationResult:
    """Result of schema validation"""
    valid: bool
    violations: List[SchemaViolation] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def critical_violations(self) -> List[SchemaViolation]:
        """Get critical severity violations"""
        return [v for v in self.violations if v.severity == Severity.CRITICAL]

    @property
    def high_violations(self) -> List[SchemaViolation]:
        """Get high severity violations"""
        return [v for v in self.violations if v.severity == Severity.HIGH]

    def get_summary(self) -> str:
        """Get human-readable summary"""
        if self.valid:
            return "✅ Schema validation passed"

        summary = f"❌ Schema validation failed with {len(self.violations)} violation(s):\n"
        summary += f"  • Critical: {len(self.critical_violations)}\n"
        summary += f"  • High: {len(self.high_violations)}\n"
        summary += f"  • Medium: {len([v for v in self.violations if v.severity == Severity.MEDIUM])}\n"
        summary += f"  • Low: {len([v for v in self.violations if v.severity == Severity.LOW])}"

        return summary


class SchemaValidator:
    """
    Validate API responses against OpenAPI schemas

    Features:
    - Type validation (string, number, integer, boolean, array, object)
    - Required field validation
    - Format validation (email, uri, uuid, date-time, etc.)
    - Enum validation
    - Range validation (minimum, maximum)
    - Array validation (items, minItems, maxItems)
    - Nested object validation
    - Strict mode (reject unexpected fields)
    """

    # Format validators
    FORMAT_PATTERNS = {
        'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        'uri': r'^https?://',
        'uuid': r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        'date': r'^\d{4}-\d{2}-\d{2}$',
        'date-time': r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',
        'ipv4': r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$',
        'ipv6': r'^[0-9a-fA-F:]+$',
    }

    def __init__(self, strict_mode: bool = False):
        """
        Initialize schema validator

        Args:
            strict_mode: If True, reject unexpected fields not in schema
        """
        self.strict_mode = strict_mode

    def validate(
        self,
        data: Any,
        schema: Dict[str, Any],
        field_path: str = "root"
    ) -> ValidationResult:
        """
        Validate data against schema

        Args:
            data: Data to validate
            schema: OpenAPI schema
            field_path: Current field path for error messages

        Returns:
            ValidationResult with violations
        """
        violations = []
        warnings = []

        # Handle empty schema
        if not schema:
            warnings.append(f"No schema provided for {field_path}")
            return ValidationResult(valid=True, violations=[], warnings=warnings)

        # Validate type
        schema_type = schema.get('type')
        if schema_type:
            type_violations = self._validate_type(data, schema_type, schema, field_path)
            violations.extend(type_violations)

        # If type is wrong, don't validate further properties
        if type_violations:
            return ValidationResult(
                valid=len([v for v in violations if v.severity in [Severity.CRITICAL, Severity.HIGH]]) == 0,
                violations=violations,
                warnings=warnings
            )

        # Validate based on type
        if schema_type == 'object' and isinstance(data, dict):
            object_violations = self._validate_object(data, schema, field_path)
            violations.extend(object_violations)

        elif schema_type == 'array' and isinstance(data, list):
            array_violations = self._validate_array(data, schema, field_path)
            violations.extend(array_violations)

        elif schema_type in ['string', 'number', 'integer']:
            value_violations = self._validate_value(data, schema, field_path)
            violations.extend(value_violations)

        # Check if valid (no critical or high severity violations)
        valid = len([v for v in violations if v.severity in [Severity.CRITICAL, Severity.HIGH]]) == 0

        return ValidationResult(valid=valid, violations=violations, warnings=warnings)

    def _validate_type(
        self,
        data: Any,
        schema_type: Union[str, List[str]],
        schema: Dict[str, Any],
        field_path: str
    ) -> List[SchemaViolation]:
        """Validate data type"""
        violations = []

        # Handle multiple types
        if isinstance(schema_type, list):
            # Check if data matches any of the types
            for type_option in schema_type:
                if self._check_type(data, type_option):
                    return []  # Valid for at least one type

            violations.append(SchemaViolation(
                violation_type=ViolationType.WRONG_TYPE,
                severity=Severity.CRITICAL if field_path != "root" else Severity.HIGH,
                field_path=field_path,
                expected=f"one of {schema_type}",
                actual=type(data).__name__,
                description=f"Expected one of {schema_type} but got {type(data).__name__}"
            ))

        else:
            # Single type
            if not self._check_type(data, schema_type):
                # Check if field is required
                is_required = schema.get('required', False)

                violations.append(SchemaViolation(
                    violation_type=ViolationType.WRONG_TYPE,
                    severity=Severity.CRITICAL if is_required else Severity.HIGH,
                    field_path=field_path,
                    expected=schema_type,
                    actual=type(data).__name__,
                    description=f"Expected {schema_type} but got {type(data).__name__}"
                ))

        return violations

    def _check_type(self, data: Any, schema_type: str) -> bool:
        """Check if data matches schema type"""
        if schema_type == 'string':
            return isinstance(data, str)
        elif schema_type == 'number':
            return isinstance(data, (int, float)) and not isinstance(data, bool)
        elif schema_type == 'integer':
            return isinstance(data, int) and not isinstance(data, bool)
        elif schema_type == 'boolean':
            return isinstance(data, bool)
        elif schema_type == 'array':
            return isinstance(data, list)
        elif schema_type == 'object':
            return isinstance(data, dict)
        elif schema_type == 'null':
            return data is None
        else:
            return True  # Unknown type, be permissive

    def _validate_object(
        self,
        data: Dict[str, Any],
        schema: Dict[str, Any],
        field_path: str
    ) -> List[SchemaViolation]:
        """Validate object against schema"""
        violations = []

        properties = schema.get('properties', {})
        required = schema.get('required', [])

        # Check required fields
        for req_field in required:
            if req_field not in data:
                violations.append(SchemaViolation(
                    violation_type=ViolationType.MISSING_REQUIRED_FIELD,
                    severity=Severity.CRITICAL,
                    field_path=f"{field_path}.{req_field}",
                    expected=f"required field '{req_field}'",
                    actual="missing",
                    description=f"Required field '{req_field}' is missing"
                ))

        # Validate each property
        for prop_name, prop_value in data.items():
            if prop_name in properties:
                # Validate against property schema
                prop_schema = properties[prop_name]
                prop_result = self.validate(prop_value, prop_schema, f"{field_path}.{prop_name}")
                violations.extend(prop_result.violations)

            else:
                # Unexpected field
                if self.strict_mode:
                    violations.append(SchemaViolation(
                        violation_type=ViolationType.UNEXPECTED_FIELD,
                        severity=Severity.MEDIUM,
                        field_path=f"{field_path}.{prop_name}",
                        expected="field not in schema",
                        actual=f"unexpected field '{prop_name}'",
                        description=f"Field '{prop_name}' not defined in schema (strict mode)"
                    ))

        return violations

    def _validate_array(
        self,
        data: List[Any],
        schema: Dict[str, Any],
        field_path: str
    ) -> List[SchemaViolation]:
        """Validate array against schema"""
        violations = []

        # Validate array constraints
        min_items = schema.get('minItems')
        max_items = schema.get('maxItems')

        if min_items is not None and len(data) < min_items:
            violations.append(SchemaViolation(
                violation_type=ViolationType.OUT_OF_RANGE,
                severity=Severity.HIGH,
                field_path=field_path,
                expected=f"at least {min_items} items",
                actual=f"{len(data)} items",
                description=f"Array has {len(data)} items but minimum is {min_items}"
            ))

        if max_items is not None and len(data) > max_items:
            violations.append(SchemaViolation(
                violation_type=ViolationType.OUT_OF_RANGE,
                severity=Severity.HIGH,
                field_path=field_path,
                expected=f"at most {max_items} items",
                actual=f"{len(data)} items",
                description=f"Array has {len(data)} items but maximum is {max_items}"
            ))

        # Validate items
        items_schema = schema.get('items', {})
        if items_schema:
            for i, item in enumerate(data):
                item_result = self.validate(item, items_schema, f"{field_path}[{i}]")
                violations.extend(item_result.violations)

        return violations

    def _validate_value(
        self,
        data: Any,
        schema: Dict[str, Any],
        field_path: str
    ) -> List[SchemaViolation]:
        """Validate primitive value against schema"""
        violations = []

        # Validate format
        if 'format' in schema and isinstance(data, str):
            format_violations = self._validate_format(data, schema['format'], field_path)
            violations.extend(format_violations)

        # Validate enum
        if 'enum' in schema:
            if data not in schema['enum']:
                violations.append(SchemaViolation(
                    violation_type=ViolationType.INVALID_ENUM_VALUE,
                    severity=Severity.HIGH,
                    field_path=field_path,
                    expected=f"one of {schema['enum']}",
                    actual=str(data),
                    description=f"Value '{data}' not in allowed enum values: {schema['enum']}"
                ))

        # Validate number ranges
        if isinstance(data, (int, float)) and not isinstance(data, bool):
            if 'minimum' in schema and data < schema['minimum']:
                violations.append(SchemaViolation(
                    violation_type=ViolationType.OUT_OF_RANGE,
                    severity=Severity.HIGH,
                    field_path=field_path,
                    expected=f">= {schema['minimum']}",
                    actual=str(data),
                    description=f"Value {data} is less than minimum {schema['minimum']}"
                ))

            if 'maximum' in schema and data > schema['maximum']:
                violations.append(SchemaViolation(
                    violation_type=ViolationType.OUT_OF_RANGE,
                    severity=Severity.HIGH,
                    field_path=field_path,
                    expected=f"<= {schema['maximum']}",
                    actual=str(data),
                    description=f"Value {data} exceeds maximum {schema['maximum']}"
                ))

        # Validate string length
        if isinstance(data, str):
            if 'minLength' in schema and len(data) < schema['minLength']:
                violations.append(SchemaViolation(
                    violation_type=ViolationType.OUT_OF_RANGE,
                    severity=Severity.HIGH,
                    field_path=field_path,
                    expected=f"length >= {schema['minLength']}",
                    actual=f"length {len(data)}",
                    description=f"String length {len(data)} is less than minimum {schema['minLength']}"
                ))

            if 'maxLength' in schema and len(data) > schema['maxLength']:
                violations.append(SchemaViolation(
                    violation_type=ViolationType.OUT_OF_RANGE,
                    severity=Severity.HIGH,
                    field_path=field_path,
                    expected=f"length <= {schema['maxLength']}",
                    actual=f"length {len(data)}",
                    description=f"String length {len(data)} exceeds maximum {schema['maxLength']}"
                ))

        return violations

    def _validate_format(self, data: str, format_type: str, field_path: str) -> List[SchemaViolation]:
        """Validate string format"""
        violations = []

        if format_type in self.FORMAT_PATTERNS:
            import re
            pattern = self.FORMAT_PATTERNS[format_type]

            if not re.match(pattern, data):
                violations.append(SchemaViolation(
                    violation_type=ViolationType.INVALID_FORMAT,
                    severity=Severity.HIGH,
                    field_path=field_path,
                    expected=f"format: {format_type}",
                    actual=data,
                    description=f"Value '{data}' does not match format '{format_type}'"
                ))

        return violations
