"""
Unit Tests for ConstraintExtractor
Tests constraint extraction from API documentation and endpoint definitions
"""
import pytest
from src.analysis.constraint_extractor import (
    ConstraintExtractor,
    ConstraintType,
    ParameterConstraint,
    ParameterConstraints
)


@pytest.mark.unit
class TestConstraintExtractor:
    """Test ConstraintExtractor functionality"""

    @pytest.fixture
    def extractor(self):
        """Create a ConstraintExtractor instance"""
        return ConstraintExtractor()

    # ========================================================================
    # Initialization Tests
    # ========================================================================

    def test_initialization(self, extractor):
        """Test extractor initializes with patterns"""
        assert extractor is not None
        assert hasattr(extractor, 'patterns')
        assert 'min_value' in extractor.patterns
        assert 'max_value' in extractor.patterns
        assert 'email' in extractor.patterns

    # ========================================================================
    # Numeric Constraint Extraction Tests
    # ========================================================================

    def test_extract_min_value_from_description(self, extractor):
        """Test extracting minimum value from description"""
        documentation = "The page parameter must be at least 1"
        endpoint = {
            "path": "/api/users",
            "method": "GET",
            "parameters": {
                "page": {
                    "type": "integer",
                    "description": documentation
                }
            }
        }

        constraints = extractor.extract_constraints(endpoint, documentation)

        assert "page" in constraints
        assert constraints["page"].type == "integer"
        assert constraints["page"].has_constraint(ConstraintType.MIN_VALUE)

        min_constraint = constraints["page"].get_constraint(ConstraintType.MIN_VALUE)
        assert min_constraint.value == 1

    def test_extract_max_value_from_description(self, extractor):
        """Test extracting maximum value from description"""
        documentation = "The limit parameter maximum is 100"
        endpoint = {
            "path": "/api/users",
            "method": "GET",
            "parameters": {
                "limit": {
                    "type": "integer",
                    "description": documentation
                }
            }
        }

        constraints = extractor.extract_constraints(endpoint, documentation)

        assert "limit" in constraints
        assert constraints["limit"].has_constraint(ConstraintType.MAX_VALUE)

        max_constraint = constraints["limit"].get_constraint(ConstraintType.MAX_VALUE)
        assert max_constraint.value == 100

    def test_extract_range_constraint(self, extractor):
        """Test extracting range (min and max) from description"""
        documentation = "Age must be between 18 and 120"
        endpoint = {
            "path": "/api/users",
            "method": "POST",
            "parameters": {
                "age": {
                    "type": "integer",
                    "description": documentation
                }
            }
        }

        constraints = extractor.extract_constraints(endpoint, documentation)

        assert "age" in constraints
        assert constraints["age"].has_constraint(ConstraintType.MIN_VALUE)
        assert constraints["age"].has_constraint(ConstraintType.MAX_VALUE)

        min_constraint = constraints["age"].get_constraint(ConstraintType.MIN_VALUE)
        max_constraint = constraints["age"].get_constraint(ConstraintType.MAX_VALUE)

        assert min_constraint.value == 18
        assert max_constraint.value == 120

    # ========================================================================
    # String Length Constraint Tests
    # ========================================================================

    def test_extract_min_length(self, extractor):
        """Test extracting minimum length constraint"""
        documentation = "Name must be at least 2 characters"
        endpoint = {
            "path": "/api/users",
            "method": "POST",
            "parameters": {
                "name": {
                    "type": "string",
                    "description": documentation
                }
            }
        }

        constraints = extractor.extract_constraints(endpoint, documentation)

        assert "name" in constraints
        assert constraints["name"].has_constraint(ConstraintType.MIN_LENGTH)

        min_length = constraints["name"].get_constraint(ConstraintType.MIN_LENGTH)
        assert min_length.value == 2

    def test_extract_max_length(self, extractor):
        """Test extracting maximum length constraint"""
        documentation = "Username maximum length: 50"
        endpoint = {
            "path": "/api/users",
            "method": "POST",
            "parameters": {
                "username": {
                    "type": "string",
                    "description": documentation
                }
            }
        }

        constraints = extractor.extract_constraints(endpoint, documentation)

        assert "username" in constraints
        assert constraints["username"].has_constraint(ConstraintType.MAX_LENGTH)

        max_length = constraints["username"].get_constraint(ConstraintType.MAX_LENGTH)
        assert max_length.value == 50

    # ========================================================================
    # Format Constraint Tests
    # ========================================================================

    def test_extract_email_format(self, extractor):
        """Test extracting email format constraint"""
        documentation = "Must be a valid email address"
        endpoint = {
            "path": "/api/users",
            "method": "POST",
            "parameters": {
                "email": {
                    "type": "string",
                    "description": documentation
                }
            }
        }

        constraints = extractor.extract_constraints(endpoint, documentation)

        assert "email" in constraints
        assert constraints["email"].has_constraint(ConstraintType.FORMAT)

        format_constraint = constraints["email"].get_constraint(ConstraintType.FORMAT)
        assert format_constraint.value == "email"

    def test_extract_uuid_format(self, extractor):
        """Test extracting UUID format constraint"""
        documentation = "ID must be a valid UUID"
        endpoint = {
            "path": "/api/users/{id}",
            "method": "GET",
            "parameters": {
                "id": {
                    "type": "string",
                    "description": documentation
                }
            }
        }

        constraints = extractor.extract_constraints(endpoint, documentation)

        assert "id" in constraints
        assert constraints["id"].has_constraint(ConstraintType.FORMAT)

        format_constraint = constraints["id"].get_constraint(ConstraintType.FORMAT)
        assert format_constraint.value == "uuid"

    def test_extract_url_format(self, extractor):
        """Test extracting URL format constraint"""
        documentation = "Callback URL format required"
        endpoint = {
            "path": "/api/webhooks",
            "method": "POST",
            "parameters": {
                "callback_url": {
                    "type": "string",
                    "description": documentation
                }
            }
        }

        constraints = extractor.extract_constraints(endpoint, documentation)

        assert "callback_url" in constraints
        assert constraints["callback_url"].has_constraint(ConstraintType.FORMAT)

        format_constraint = constraints["callback_url"].get_constraint(ConstraintType.FORMAT)
        assert format_constraint.value == "url"

    def test_extract_date_format(self, extractor):
        """Test extracting date format constraint"""
        documentation = "Date must be in YYYY-MM-DD format"
        endpoint = {
            "path": "/api/events",
            "method": "GET",
            "parameters": {
                "start_date": {
                    "type": "string",
                    "description": documentation
                }
            }
        }

        constraints = extractor.extract_constraints(endpoint, documentation)

        assert "start_date" in constraints
        assert constraints["start_date"].has_constraint(ConstraintType.FORMAT)

        format_constraint = constraints["start_date"].get_constraint(ConstraintType.FORMAT)
        assert format_constraint.value == "date"

    # ========================================================================
    # Enum Constraint Tests
    # ========================================================================

    def test_extract_enum_values(self, extractor):
        """Test extracting enum values"""
        documentation = "Status must be one of: active, inactive, pending"
        endpoint = {
            "path": "/api/users",
            "method": "GET",
            "parameters": {
                "status": {
                    "type": "string",
                    "description": documentation
                }
            }
        }

        constraints = extractor.extract_constraints(endpoint, documentation)

        assert "status" in constraints
        assert constraints["status"].has_constraint(ConstraintType.ENUM)

        enum_constraint = constraints["status"].get_constraint(ConstraintType.ENUM)
        assert isinstance(enum_constraint.value, list)
        assert "active" in enum_constraint.value
        assert "inactive" in enum_constraint.value
        assert "pending" in enum_constraint.value

    # ========================================================================
    # Required/Optional Tests
    # ========================================================================

    def test_extract_required_constraint(self, extractor):
        """Test detecting required parameters"""
        documentation = "Email is required"
        endpoint = {
            "path": "/api/users",
            "method": "POST",
            "parameters": {
                "email": {
                    "type": "string",
                    "description": documentation
                }
            }
        }

        constraints = extractor.extract_constraints(endpoint, documentation)

        assert "email" in constraints
        assert constraints["email"].required is True

    def test_extract_optional_constraint(self, extractor):
        """Test detecting optional parameters"""
        documentation = "Phone number is optional"
        endpoint = {
            "path": "/api/users",
            "method": "POST",
            "parameters": {
                "phone": {
                    "type": "string",
                    "description": documentation
                }
            }
        }

        constraints = extractor.extract_constraints(endpoint, documentation)

        assert "phone" in constraints
        assert constraints["phone"].required is False

    # ========================================================================
    # OpenAPI Schema Tests
    # ========================================================================

    def test_extract_from_openapi_schema(self, extractor):
        """Test extracting constraints from OpenAPI schema"""
        endpoint = {
            "path": "/api/users",
            "method": "POST",
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["email", "name"],
                            "properties": {
                                "email": {
                                    "type": "string",
                                    "format": "email",
                                    "minLength": 5,
                                    "maxLength": 100
                                },
                                "name": {
                                    "type": "string",
                                    "minLength": 2,
                                    "maxLength": 50
                                },
                                "age": {
                                    "type": "integer",
                                    "minimum": 18,
                                    "maximum": 120
                                }
                            }
                        }
                    }
                }
            }
        }

        constraints = extractor.extract_constraints(endpoint)

        # Check email constraints
        assert "email" in constraints
        assert constraints["email"].type == "string"
        assert constraints["email"].required is True
        assert constraints["email"].has_constraint(ConstraintType.FORMAT)
        assert constraints["email"].has_constraint(ConstraintType.MIN_LENGTH)
        assert constraints["email"].has_constraint(ConstraintType.MAX_LENGTH)

        # Check name constraints
        assert "name" in constraints
        assert constraints["name"].required is True
        assert constraints["name"].get_constraint(ConstraintType.MIN_LENGTH).value == 2
        assert constraints["name"].get_constraint(ConstraintType.MAX_LENGTH).value == 50

        # Check age constraints
        assert "age" in constraints
        assert constraints["age"].required is False  # Not in required list
        assert constraints["age"].get_constraint(ConstraintType.MIN_VALUE).value == 18
        assert constraints["age"].get_constraint(ConstraintType.MAX_VALUE).value == 120

    # ========================================================================
    # Edge Cases Tests
    # ========================================================================

    def test_empty_endpoint(self, extractor):
        """Test handling empty endpoint"""
        endpoint = {}
        constraints = extractor.extract_constraints(endpoint)
        assert isinstance(constraints, dict)
        assert len(constraints) == 0

    def test_endpoint_with_no_parameters(self, extractor):
        """Test endpoint with no parameters"""
        endpoint = {
            "path": "/api/health",
            "method": "GET"
        }
        constraints = extractor.extract_constraints(endpoint)
        assert isinstance(constraints, dict)
        assert len(constraints) == 0

    def test_parameter_with_no_constraints(self, extractor):
        """Test parameter with no extractable constraints"""
        endpoint = {
            "path": "/api/data",
            "method": "GET",
            "parameters": {
                "query": {
                    "type": "string"
                }
            }
        }
        constraints = extractor.extract_constraints(endpoint)
        assert "query" in constraints
        assert constraints["query"].type == "string"
        assert len(constraints["query"].constraints) == 0

    def test_malformed_documentation(self, extractor):
        """Test handling malformed documentation"""
        documentation = "!!!Invalid##@@ documentation $%^&"
        endpoint = {
            "path": "/api/test",
            "method": "GET",
            "parameters": {
                "test": {"type": "string"}
            }
        }
        # Should not raise exception
        constraints = extractor.extract_constraints(endpoint, documentation)
        assert isinstance(constraints, dict)

    # ========================================================================
    # Multiple Constraints Tests
    # ========================================================================

    def test_extract_multiple_constraints_single_parameter(self, extractor):
        """Test extracting multiple constraints from a single parameter"""
        documentation = "Username is required, must be at least 3 characters, maximum 20 characters"
        endpoint = {
            "path": "/api/users",
            "method": "POST",
            "parameters": {
                "username": {
                    "type": "string",
                    "description": documentation
                }
            }
        }

        constraints = extractor.extract_constraints(endpoint, documentation)

        assert "username" in constraints
        assert constraints["username"].required is True
        assert constraints["username"].has_constraint(ConstraintType.MIN_LENGTH)
        assert constraints["username"].has_constraint(ConstraintType.MAX_LENGTH)

        min_length = constraints["username"].get_constraint(ConstraintType.MIN_LENGTH)
        max_length = constraints["username"].get_constraint(ConstraintType.MAX_LENGTH)

        assert min_length.value == 3
        assert max_length.value == 20


@pytest.mark.unit
class TestParameterConstraints:
    """Test ParameterConstraints data class"""

    def test_create_parameter_constraints(self):
        """Test creating ParameterConstraints"""
        param = ParameterConstraints(
            name="email",
            type="string",
            required=True
        )

        assert param.name == "email"
        assert param.type == "string"
        assert param.required is True
        assert len(param.constraints) == 0

    def test_add_constraint(self):
        """Test adding constraints"""
        param = ParameterConstraints(name="age", type="integer")

        min_constraint = ParameterConstraint(
            param_name="age",
            constraint_type=ConstraintType.MIN_VALUE,
            value=18,
            description="Must be adult"
        )

        param.constraints.append(min_constraint)

        assert len(param.constraints) == 1
        assert param.has_constraint(ConstraintType.MIN_VALUE)

    def test_get_constraint(self):
        """Test getting constraint by type"""
        param = ParameterConstraints(name="email", type="string")

        format_constraint = ParameterConstraint(
            param_name="email",
            constraint_type=ConstraintType.FORMAT,
            value="email"
        )

        param.constraints.append(format_constraint)

        retrieved = param.get_constraint(ConstraintType.FORMAT)

        assert retrieved is not None
        assert retrieved.value == "email"

    def test_get_nonexistent_constraint(self):
        """Test getting constraint that doesn't exist"""
        param = ParameterConstraints(name="test", type="string")

        retrieved = param.get_constraint(ConstraintType.MIN_LENGTH)

        assert retrieved is None

    def test_has_constraint(self):
        """Test checking if constraint exists"""
        param = ParameterConstraints(name="age", type="integer")

        assert param.has_constraint(ConstraintType.MIN_VALUE) is False

        min_constraint = ParameterConstraint(
            param_name="age",
            constraint_type=ConstraintType.MIN_VALUE,
            value=0
        )
        param.constraints.append(min_constraint)

        assert param.has_constraint(ConstraintType.MIN_VALUE) is True


@pytest.mark.unit
class TestParameterConstraint:
    """Test ParameterConstraint data class"""

    def test_create_constraint(self):
        """Test creating a constraint"""
        constraint = ParameterConstraint(
            param_name="age",
            constraint_type=ConstraintType.MIN_VALUE,
            value=18,
            description="Must be adult",
            confidence=0.95
        )

        assert constraint.param_name == "age"
        assert constraint.constraint_type == ConstraintType.MIN_VALUE
        assert constraint.value == 18
        assert constraint.description == "Must be adult"
        assert constraint.confidence == 0.95

    def test_default_confidence(self):
        """Test default confidence value"""
        constraint = ParameterConstraint(
            param_name="email",
            constraint_type=ConstraintType.FORMAT,
            value="email"
        )

        assert constraint.confidence == 1.0
