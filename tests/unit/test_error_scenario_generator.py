"""
Unit Tests for ErrorScenarioGenerator
Tests error scenario generation for validation, authentication, and other error conditions
"""
import pytest
from src.testing.error_scenario_generator import (
    ErrorScenarioGenerator,
    ErrorCondition,
    ErrorCategory,
    ErrorScenario
)


@pytest.mark.unit
class TestErrorScenarioGenerator:
    """Test ErrorScenarioGenerator functionality"""

    @pytest.fixture
    def generator(self):
        """Create an ErrorScenarioGenerator instance"""
        return ErrorScenarioGenerator()

    @pytest.fixture
    def sample_endpoint(self):
        """Sample endpoint for testing"""
        return {
            "method": "POST",
            "path": "/api/users",
            "parameters": {
                "email": {
                    "type": "string",
                    "format": "email",
                    "required": True
                },
                "name": {
                    "type": "string",
                    "minLength": 2,
                    "required": True
                },
                "age": {
                    "type": "integer",
                    "minimum": 18,
                    "maximum": 120,
                    "required": False
                }
            },
            "responses": {
                "201": {"description": "Created"},
                "400": {"description": "Bad Request"},
                "422": {"description": "Validation Error"}
            }
        }

    # ========================================================================
    # Initialization Tests
    # ========================================================================

    def test_initialization(self, generator):
        """Test generator initializes with common error conditions"""
        assert generator is not None
        assert hasattr(generator, 'COMMON_ERROR_CONDITIONS')
        assert len(generator.COMMON_ERROR_CONDITIONS) > 0

    def test_common_error_conditions_exist(self, generator):
        """Test common error conditions are defined"""
        conditions = generator.COMMON_ERROR_CONDITIONS

        # Check we have error conditions for different categories
        categories = {cond.category for cond in conditions}

        assert ErrorCategory.VALIDATION in categories
        assert ErrorCategory.AUTHENTICATION in categories
        assert ErrorCategory.NOT_FOUND in categories

    # ========================================================================
    # Validation Error Scenario Tests
    # ========================================================================

    def test_generate_missing_required_field_scenario(self, generator, sample_endpoint):
        """Test generating scenario for missing required field"""
        scenarios = generator.generate_error_scenarios(
            endpoint=sample_endpoint,
            error_categories=[ErrorCategory.VALIDATION]
        )

        # Should have scenario for missing required field
        missing_field_scenarios = [
            s for s in scenarios
            if s.error_condition.condition_name == "missing_required_field"
        ]

        assert len(missing_field_scenarios) > 0

        # Check scenario structure
        scenario = missing_field_scenarios[0]
        assert scenario.method == "POST"
        assert scenario.path == "/api/users"
        assert scenario.trigger_payload is not None
        assert scenario.error_condition.expected_status_code == 422

    def test_generate_invalid_type_scenario(self, generator, sample_endpoint):
        """Test generating scenario for invalid field type"""
        scenarios = generator.generate_error_scenarios(
            endpoint=sample_endpoint,
            error_categories=[ErrorCategory.VALIDATION]
        )

        invalid_type_scenarios = [
            s for s in scenarios
            if s.error_condition.condition_name == "invalid_field_type"
        ]

        assert len(invalid_type_scenarios) > 0

    def test_generate_out_of_range_scenario(self, generator, sample_endpoint):
        """Test generating scenario for out-of-range value"""
        scenarios = generator.generate_error_scenarios(
            endpoint=sample_endpoint,
            error_categories=[ErrorCategory.VALIDATION]
        )

        out_of_range_scenarios = [
            s for s in scenarios
            if s.error_condition.condition_name == "field_out_of_range"
        ]

        assert len(out_of_range_scenarios) > 0

        # Check trigger payload has out-of-range value
        scenario = out_of_range_scenarios[0]
        if scenario.trigger_payload and "age" in scenario.trigger_payload:
            age_value = scenario.trigger_payload["age"]
            # Should be below 18 or above 120
            assert age_value < 18 or age_value > 120

    def test_generate_invalid_format_scenario(self, generator, sample_endpoint):
        """Test generating scenario for invalid format"""
        scenarios = generator.generate_error_scenarios(
            endpoint=sample_endpoint,
            error_categories=[ErrorCategory.VALIDATION]
        )

        format_scenarios = [
            s for s in scenarios
            if s.error_condition.condition_name == "invalid_field_format"
        ]

        assert len(format_scenarios) > 0

        # Check email field has invalid format
        scenario = format_scenarios[0]
        if scenario.trigger_payload and "email" in scenario.trigger_payload:
            email_value = scenario.trigger_payload["email"]
            # Should be invalid email
            assert "@" not in email_value or "." not in email_value

    # ========================================================================
    # Authentication Error Scenario Tests
    # ========================================================================

    def test_generate_auth_required_scenario(self, generator, sample_endpoint):
        """Test generating scenario for authentication required"""
        scenarios = generator.generate_error_scenarios(
            endpoint=sample_endpoint,
            error_categories=[ErrorCategory.AUTHENTICATION]
        )

        auth_scenarios = [
            s for s in scenarios
            if s.error_condition.category == ErrorCategory.AUTHENTICATION
        ]

        assert len(auth_scenarios) > 0

        # Should have scenarios with no auth token or invalid auth
        scenario = auth_scenarios[0]
        assert scenario.error_condition.expected_status_code == 401

    # ========================================================================
    # Not Found Error Scenario Tests
    # ========================================================================

    def test_generate_not_found_scenario(self, generator):
        """Test generating not found error scenario"""
        endpoint = {
            "method": "GET",
            "path": "/api/users/{id}",
            "parameters": {
                "id": {"type": "string", "format": "uuid", "in": "path"}
            },
            "responses": {
                "200": {"description": "Success"},
                "404": {"description": "Not Found"}
            }
        }

        scenarios = generator.generate_error_scenarios(
            endpoint=endpoint,
            error_categories=[ErrorCategory.NOT_FOUND]
        )

        not_found_scenarios = [
            s for s in scenarios
            if s.error_condition.category == ErrorCategory.NOT_FOUND
        ]

        assert len(not_found_scenarios) > 0
        assert not_found_scenarios[0].error_condition.expected_status_code == 404

    # ========================================================================
    # Multiple Category Tests
    # ========================================================================

    def test_generate_multiple_categories(self, generator, sample_endpoint):
        """Test generating scenarios for multiple error categories"""
        scenarios = generator.generate_error_scenarios(
            endpoint=sample_endpoint,
            error_categories=[ErrorCategory.VALIDATION, ErrorCategory.AUTHENTICATION]
        )

        # Should have scenarios from both categories
        categories = {s.error_condition.category for s in scenarios}

        assert ErrorCategory.VALIDATION in categories
        assert ErrorCategory.AUTHENTICATION in categories

    def test_generate_all_categories(self, generator, sample_endpoint):
        """Test generating scenarios for all error categories"""
        scenarios = generator.generate_error_scenarios(
            endpoint=sample_endpoint,
            error_categories=None  # None means all categories
        )

        # Should have scenarios from multiple categories
        assert len(scenarios) > 5

    # ========================================================================
    # Error Condition Structure Tests
    # ========================================================================

    def test_error_condition_structure(self):
        """Test ErrorCondition dataclass structure"""
        condition = ErrorCondition(
            condition_name="test_error",
            category=ErrorCategory.VALIDATION,
            trigger="Do something wrong",
            expected_status_code=400,
            expected_fields=["error", "message"],
            description="Test error condition"
        )

        assert condition.condition_name == "test_error"
        assert condition.category == ErrorCategory.VALIDATION
        assert condition.expected_status_code == 400
        assert len(condition.expected_fields) == 2

    def test_error_scenario_structure(self):
        """Test ErrorScenario dataclass structure"""
        condition = ErrorCondition(
            condition_name="test_error",
            category=ErrorCategory.VALIDATION,
            trigger="Test",
            expected_status_code=400,
            expected_fields=["error"],
            description="Test"
        )

        scenario = ErrorScenario(
            endpoint_key="POST /api/users",
            method="POST",
            path="/api/users",
            error_condition=condition,
            trigger_payload={"email": "invalid"},
            description="Test scenario"
        )

        assert scenario.method == "POST"
        assert scenario.path == "/api/users"
        assert scenario.trigger_payload is not None
        assert scenario.error_condition.condition_name == "test_error"

    # ========================================================================
    # Edge Cases Tests
    # ========================================================================

    def test_generate_scenarios_no_parameters(self, generator):
        """Test generating scenarios for endpoint with no parameters"""
        endpoint = {
            "method": "GET",
            "path": "/api/health",
            "responses": {"200": {"description": "OK"}}
        }

        scenarios = generator.generate_error_scenarios(
            endpoint=endpoint,
            error_categories=[ErrorCategory.VALIDATION]
        )

        # Should handle gracefully, may return empty or minimal scenarios
        assert isinstance(scenarios, list)

    def test_generate_scenarios_empty_categories(self, generator, sample_endpoint):
        """Test generating scenarios with empty category list"""
        scenarios = generator.generate_error_scenarios(
            endpoint=sample_endpoint,
            error_categories=[]
        )

        # Should return empty list or handle gracefully
        assert isinstance(scenarios, list)

    def test_error_category_enum(self):
        """Test ErrorCategory enum values"""
        assert ErrorCategory.VALIDATION.value == "validation"
        assert ErrorCategory.AUTHENTICATION.value == "authentication"
        assert ErrorCategory.AUTHORIZATION.value == "authorization"
        assert ErrorCategory.NOT_FOUND.value == "not_found"
        assert ErrorCategory.CONFLICT.value == "conflict"
        assert ErrorCategory.RATE_LIMIT.value == "rate_limit"
        assert ErrorCategory.SERVER_ERROR.value == "server_error"

    # ========================================================================
    # Scenario Validation Tests
    # ========================================================================

    def test_scenarios_have_required_fields(self, generator, sample_endpoint):
        """Test all generated scenarios have required fields"""
        scenarios = generator.generate_error_scenarios(
            endpoint=sample_endpoint,
            error_categories=[ErrorCategory.VALIDATION]
        )

        for scenario in scenarios:
            # Check required fields are present
            assert scenario.endpoint_key is not None
            assert scenario.method is not None
            assert scenario.path is not None
            assert scenario.error_condition is not None

            # Check error condition has required fields
            assert scenario.error_condition.condition_name is not None
            assert scenario.error_condition.category is not None
            assert scenario.error_condition.expected_status_code is not None

    def test_scenarios_have_unique_conditions(self, generator, sample_endpoint):
        """Test scenarios cover different error conditions"""
        scenarios = generator.generate_error_scenarios(
            endpoint=sample_endpoint,
            error_categories=[ErrorCategory.VALIDATION]
        )

        condition_names = [s.error_condition.condition_name for s in scenarios]

        # Should have multiple unique conditions
        assert len(set(condition_names)) > 1


@pytest.mark.unit
class TestErrorCategory:
    """Test ErrorCategory enum"""

    def test_all_categories_defined(self):
        """Test all expected error categories are defined"""
        categories = list(ErrorCategory)

        assert len(categories) == 7
        assert ErrorCategory.VALIDATION in categories
        assert ErrorCategory.AUTHENTICATION in categories
        assert ErrorCategory.AUTHORIZATION in categories
        assert ErrorCategory.NOT_FOUND in categories
        assert ErrorCategory.CONFLICT in categories
        assert ErrorCategory.RATE_LIMIT in categories
        assert ErrorCategory.SERVER_ERROR in categories

    def test_category_values(self):
        """Test category string values"""
        assert ErrorCategory.VALIDATION.value == "validation"
        assert ErrorCategory.AUTHENTICATION.value == "authentication"
        assert ErrorCategory.AUTHORIZATION.value == "authorization"
        assert ErrorCategory.NOT_FOUND.value == "not_found"
        assert ErrorCategory.CONFLICT.value == "conflict"
        assert ErrorCategory.RATE_LIMIT.value == "rate_limit"
        assert ErrorCategory.SERVER_ERROR.value == "server_error"
