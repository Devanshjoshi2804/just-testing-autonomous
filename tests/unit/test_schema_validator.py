"""
Unit Tests for SchemaValidator
Tests OpenAPI schema validation for API responses
"""
import pytest
from src.validation.schema_validator import (
    SchemaValidator,
    ValidationResult,
    SchemaViolation,
    ViolationType,
    Severity
)


@pytest.mark.unit
class TestSchemaValidator:
    """Test SchemaValidator functionality"""

    @pytest.fixture
    def validator(self):
        """Create a SchemaValidator instance"""
        return SchemaValidator(strict_mode=False)

    @pytest.fixture
    def strict_validator(self):
        """Create a strict mode SchemaValidator"""
        return SchemaValidator(strict_mode=True)

    # ========================================================================
    # Initialization Tests
    # ========================================================================

    def test_initialization_permissive(self, validator):
        """Test validator initializes in permissive mode"""
        assert validator is not None
        assert validator.strict_mode is False

    def test_initialization_strict(self, strict_validator):
        """Test validator initializes in strict mode"""
        assert strict_validator is not None
        assert strict_validator.strict_mode is True

    # ========================================================================
    # Type Validation Tests
    # ========================================================================

    def test_validate_string_type(self, validator):
        """Test validating string type"""
        data = "hello"
        schema = {"type": "string"}

        result = validator.validate(data, schema)

        assert result.valid is True
        assert len(result.violations) == 0

    def test_validate_wrong_string_type(self, validator):
        """Test detecting wrong type for string"""
        data = 123
        schema = {"type": "string"}

        result = validator.validate(data, schema)

        assert result.valid is False
        assert len(result.violations) > 0
        assert result.violations[0].violation_type == ViolationType.WRONG_TYPE

    def test_validate_integer_type(self, validator):
        """Test validating integer type"""
        data = 42
        schema = {"type": "integer"}

        result = validator.validate(data, schema)

        assert result.valid is True
        assert len(result.violations) == 0

    def test_validate_boolean_type(self, validator):
        """Test validating boolean type"""
        data = True
        schema = {"type": "boolean"}

        result = validator.validate(data, schema)

        assert result.valid is True
        assert len(result.violations) == 0

    def test_validate_array_type(self, validator):
        """Test validating array type"""
        data = [1, 2, 3]
        schema = {"type": "array"}

        result = validator.validate(data, schema)

        assert result.valid is True
        assert len(result.violations) == 0

    def test_validate_object_type(self, validator):
        """Test validating object type"""
        data = {"name": "John", "age": 30}
        schema = {"type": "object"}

        result = validator.validate(data, schema)

        assert result.valid is True
        assert len(result.violations) == 0

    # ========================================================================
    # Required Field Tests
    # ========================================================================

    def test_validate_required_fields_present(self, validator):
        """Test validation passes when required fields are present"""
        data = {
            "name": "John",
            "email": "john@example.com"
        }
        schema = {
            "type": "object",
            "required": ["name", "email"],
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"}
            }
        }

        result = validator.validate(data, schema)

        assert result.valid is True
        assert len(result.violations) == 0

    def test_validate_missing_required_field(self, validator):
        """Test detecting missing required field"""
        data = {
            "name": "John"
        }
        schema = {
            "type": "object",
            "required": ["name", "email"],
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"}
            }
        }

        result = validator.validate(data, schema)

        assert result.valid is False
        assert len(result.violations) > 0

        # Find the missing field violation
        missing_violations = [v for v in result.violations
                             if v.violation_type == ViolationType.MISSING_REQUIRED_FIELD]
        assert len(missing_violations) > 0
        assert missing_violations[0].severity == Severity.CRITICAL

    def test_validate_optional_field_missing(self, validator):
        """Test optional field can be missing"""
        data = {
            "name": "John"
        }
        schema = {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}  # Optional
            }
        }

        result = validator.validate(data, schema)

        assert result.valid is True
        assert len(result.violations) == 0

    # ========================================================================
    # Format Validation Tests
    # ========================================================================

    def test_validate_email_format(self, validator):
        """Test validating email format"""
        data = {"email": "john@example.com"}
        schema = {
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email"}
            }
        }

        result = validator.validate(data, schema)

        assert result.valid is True
        assert len(result.violations) == 0

    def test_validate_invalid_email_format(self, validator):
        """Test detecting invalid email format"""
        data = {"email": "not-an-email"}
        schema = {
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email"}
            }
        }

        result = validator.validate(data, schema)

        assert result.valid is False
        assert len(result.violations) > 0

        format_violations = [v for v in result.violations
                            if v.violation_type == ViolationType.INVALID_FORMAT]
        assert len(format_violations) > 0

    def test_validate_uuid_format(self, validator):
        """Test validating UUID format"""
        data = {"id": "123e4567-e89b-12d3-a456-426614174000"}
        schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string", "format": "uuid"}
            }
        }

        result = validator.validate(data, schema)

        assert result.valid is True
        assert len(result.violations) == 0

    def test_validate_invalid_uuid_format(self, validator):
        """Test detecting invalid UUID format"""
        data = {"id": "not-a-uuid"}
        schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string", "format": "uuid"}
            }
        }

        result = validator.validate(data, schema)

        assert result.valid is False
        assert len(result.violations) > 0

    def test_validate_date_format(self, validator):
        """Test validating date format"""
        data = {"created": "2025-01-18"}
        schema = {
            "type": "object",
            "properties": {
                "created": {"type": "string", "format": "date"}
            }
        }

        result = validator.validate(data, schema)

        assert result.valid is True
        assert len(result.violations) == 0

    def test_validate_datetime_format(self, validator):
        """Test validating date-time format"""
        data = {"created_at": "2025-01-18T10:30:00Z"}
        schema = {
            "type": "object",
            "properties": {
                "created_at": {"type": "string", "format": "date-time"}
            }
        }

        result = validator.validate(data, schema)

        assert result.valid is True
        assert len(result.violations) == 0

    def test_validate_uri_format(self, validator):
        """Test validating URI format"""
        data = {"url": "https://example.com/api"}
        schema = {
            "type": "object",
            "properties": {
                "url": {"type": "string", "format": "uri"}
            }
        }

        result = validator.validate(data, schema)

        assert result.valid is True
        assert len(result.violations) == 0

    # ========================================================================
    # Range Validation Tests
    # ========================================================================

    def test_validate_minimum_value(self, validator):
        """Test validating minimum value constraint"""
        data = {"age": 18}
        schema = {
            "type": "object",
            "properties": {
                "age": {"type": "integer", "minimum": 18}
            }
        }

        result = validator.validate(data, schema)

        assert result.valid is True
        assert len(result.violations) == 0

    def test_validate_below_minimum_value(self, validator):
        """Test detecting value below minimum"""
        data = {"age": 17}
        schema = {
            "type": "object",
            "properties": {
                "age": {"type": "integer", "minimum": 18}
            }
        }

        result = validator.validate(data, schema)

        assert result.valid is False
        assert len(result.violations) > 0

        range_violations = [v for v in result.violations
                           if v.violation_type == ViolationType.OUT_OF_RANGE]
        assert len(range_violations) > 0

    def test_validate_maximum_value(self, validator):
        """Test validating maximum value constraint"""
        data = {"age": 120}
        schema = {
            "type": "object",
            "properties": {
                "age": {"type": "integer", "maximum": 120}
            }
        }

        result = validator.validate(data, schema)

        assert result.valid is True
        assert len(result.violations) == 0

    def test_validate_above_maximum_value(self, validator):
        """Test detecting value above maximum"""
        data = {"age": 121}
        schema = {
            "type": "object",
            "properties": {
                "age": {"type": "integer", "maximum": 120}
            }
        }

        result = validator.validate(data, schema)

        assert result.valid is False
        assert len(result.violations) > 0

    # ========================================================================
    # Enum Validation Tests
    # ========================================================================

    def test_validate_valid_enum_value(self, validator):
        """Test validating value in enum"""
        data = {"status": "active"}
        schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["active", "inactive", "pending"]}
            }
        }

        result = validator.validate(data, schema)

        assert result.valid is True
        assert len(result.violations) == 0

    def test_validate_invalid_enum_value(self, validator):
        """Test detecting value not in enum"""
        data = {"status": "unknown"}
        schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["active", "inactive", "pending"]}
            }
        }

        result = validator.validate(data, schema)

        assert result.valid is False
        assert len(result.violations) > 0

        enum_violations = [v for v in result.violations
                          if v.violation_type == ViolationType.INVALID_ENUM_VALUE]
        assert len(enum_violations) > 0

    # ========================================================================
    # Array Validation Tests
    # ========================================================================

    def test_validate_array_items(self, validator):
        """Test validating array items"""
        data = {"tags": ["python", "api", "testing"]}
        schema = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        }

        result = validator.validate(data, schema)

        assert result.valid is True
        assert len(result.violations) == 0

    def test_validate_array_wrong_item_type(self, validator):
        """Test detecting wrong type in array items"""
        data = {"ids": [1, 2, "three"]}
        schema = {
            "type": "object",
            "properties": {
                "ids": {
                    "type": "array",
                    "items": {"type": "integer"}
                }
            }
        }

        result = validator.validate(data, schema)

        assert result.valid is False
        assert len(result.violations) > 0

    def test_validate_min_items(self, validator):
        """Test validating minItems constraint"""
        data = {"tags": ["tag1", "tag2"]}
        schema = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "minItems": 2
                }
            }
        }

        result = validator.validate(data, schema)

        assert result.valid is True
        assert len(result.violations) == 0

    def test_validate_below_min_items(self, validator):
        """Test detecting array with too few items"""
        data = {"tags": ["tag1"]}
        schema = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "minItems": 2
                }
            }
        }

        result = validator.validate(data, schema)

        assert result.valid is False
        assert len(result.violations) > 0

    def test_validate_max_items(self, validator):
        """Test validating maxItems constraint"""
        data = {"tags": ["tag1", "tag2", "tag3"]}
        schema = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "maxItems": 3
                }
            }
        }

        result = validator.validate(data, schema)

        assert result.valid is True
        assert len(result.violations) == 0

    def test_validate_above_max_items(self, validator):
        """Test detecting array with too many items"""
        data = {"tags": ["tag1", "tag2", "tag3", "tag4"]}
        schema = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "maxItems": 3
                }
            }
        }

        result = validator.validate(data, schema)

        assert result.valid is False
        assert len(result.violations) > 0

    # ========================================================================
    # Nested Object Tests
    # ========================================================================

    def test_validate_nested_object(self, validator):
        """Test validating nested objects"""
        data = {
            "user": {
                "name": "John",
                "email": "john@example.com"
            }
        }
        schema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "required": ["name", "email"],
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string", "format": "email"}
                    }
                }
            }
        }

        result = validator.validate(data, schema)

        assert result.valid is True
        assert len(result.violations) == 0

    def test_validate_nested_object_missing_field(self, validator):
        """Test detecting missing field in nested object"""
        data = {
            "user": {
                "name": "John"
            }
        }
        schema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "required": ["name", "email"],
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string"}
                    }
                }
            }
        }

        result = validator.validate(data, schema)

        assert result.valid is False
        assert len(result.violations) > 0

    # ========================================================================
    # Strict Mode Tests
    # ========================================================================

    def test_strict_mode_rejects_unexpected_fields(self, strict_validator):
        """Test strict mode rejects unexpected fields"""
        data = {
            "name": "John",
            "unexpected_field": "value"
        }
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"}
            }
        }

        result = strict_validator.validate(data, schema)

        assert result.valid is False
        assert len(result.violations) > 0

        unexpected_violations = [v for v in result.violations
                                if v.violation_type == ViolationType.UNEXPECTED_FIELD]
        assert len(unexpected_violations) > 0

    def test_permissive_mode_allows_unexpected_fields(self, validator):
        """Test permissive mode allows unexpected fields"""
        data = {
            "name": "John",
            "extra_field": "value"
        }
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"}
            }
        }

        result = validator.validate(data, schema)

        # In permissive mode, unexpected fields shouldn't cause failure
        # But may generate warnings
        assert result.valid is True or len(result.critical_violations) == 0

    # ========================================================================
    # ValidationResult Tests
    # ========================================================================

    def test_validation_result_summary_valid(self):
        """Test summary for valid result"""
        result = ValidationResult(valid=True, violations=[])

        summary = result.get_summary()

        assert "✅" in summary or "passed" in summary.lower()

    def test_validation_result_summary_invalid(self):
        """Test summary for invalid result"""
        violations = [
            SchemaViolation(
                violation_type=ViolationType.MISSING_REQUIRED_FIELD,
                severity=Severity.CRITICAL,
                field_path="root.email",
                expected="required field",
                actual="missing",
                description="Field 'email' is required"
            )
        ]
        result = ValidationResult(valid=False, violations=violations)

        summary = result.get_summary()

        assert "❌" in summary or "failed" in summary.lower()
        assert "1" in summary or "Critical" in summary

    def test_validation_result_critical_violations(self):
        """Test filtering critical violations"""
        violations = [
            SchemaViolation(
                violation_type=ViolationType.MISSING_REQUIRED_FIELD,
                severity=Severity.CRITICAL,
                field_path="root.email",
                expected="required",
                actual="missing",
                description="Missing"
            ),
            SchemaViolation(
                violation_type=ViolationType.UNEXPECTED_FIELD,
                severity=Severity.LOW,
                field_path="root.extra",
                expected="not present",
                actual="present",
                description="Extra field"
            )
        ]
        result = ValidationResult(valid=False, violations=violations)

        critical = result.critical_violations

        assert len(critical) == 1
        assert critical[0].severity == Severity.CRITICAL

    def test_validation_result_high_violations(self):
        """Test filtering high severity violations"""
        violations = [
            SchemaViolation(
                violation_type=ViolationType.WRONG_TYPE,
                severity=Severity.HIGH,
                field_path="root.age",
                expected="integer",
                actual="string",
                description="Wrong type"
            )
        ]
        result = ValidationResult(valid=False, violations=violations)

        high = result.high_violations

        assert len(high) == 1
        assert high[0].severity == Severity.HIGH
