"""
Unit Tests for BoundaryTestGenerator
Tests boundary value test generation for API parameters
"""
import pytest
from src.generators.boundary_test_generator import BoundaryTestGenerator


@pytest.mark.unit
class TestBoundaryTestGenerator:
    """Test BoundaryTestGenerator functionality"""

    @pytest.fixture
    def generator(self):
        """Create a BoundaryTestGenerator instance"""
        return BoundaryTestGenerator()

    # ========================================================================
    # Initialization Tests
    # ========================================================================

    def test_initialization(self, generator):
        """Test generator initializes with data generator"""
        assert generator is not None
        assert hasattr(generator, 'data_generator')
        assert generator.data_generator is not None

    # ========================================================================
    # Integer Boundary Tests
    # ========================================================================

    def test_generate_integer_boundary_tests(self, generator):
        """Test generating boundary tests for integer parameter"""
        endpoint = {
            "path": "/api/users",
            "method": "GET",
            "parameters": [
                {
                    "name": "page",
                    "in": "query",
                    "type": "integer"
                }
            ]
        }

        parameter_constraints = {
            "page": {
                "type": "integer",
                "constraints": [
                    {"constraint_type": "min_value", "value": 1},
                    {"constraint_type": "max_value", "value": 100}
                ]
            }
        }

        test_suite = generator.generate_boundary_test_suite(
            endpoint, parameter_constraints
        )

        assert len(test_suite) > 0

        # Should have tests for: min-1 (0), min (1), min+1 (2), max-1 (99), max (100), max+1 (101)
        # Total: 6 boundary test values
        assert len(test_suite) >= 6

        # Check that we have both valid and invalid tests
        valid_tests = [t for t in test_suite if t.get('boundary_info', {}).get('expected_valid')]
        invalid_tests = [t for t in test_suite if not t.get('boundary_info', {}).get('expected_valid')]

        assert len(valid_tests) > 0  # Should have valid boundary tests
        assert len(invalid_tests) > 0  # Should have invalid boundary tests

    def test_integer_boundary_below_minimum(self, generator):
        """Test generating boundary value below minimum"""
        endpoint = {
            "path": "/api/users",
            "method": "GET",
            "parameters": [{"name": "age", "in": "query", "type": "integer"}]
        }

        parameter_constraints = {
            "age": {
                "type": "integer",
                "constraints": [
                    {"constraint_type": "min_value", "value": 18}
                ]
            }
        }

        test_suite = generator.generate_boundary_test_suite(
            endpoint, parameter_constraints
        )

        # Find test with value below minimum (17)
        below_min_test = None
        for test in test_suite:
            if test.get('payload', {}).get('age') == 17:
                below_min_test = test
                break

        assert below_min_test is not None
        assert below_min_test['boundary_info']['expected_valid'] is False
        assert below_min_test['expected_status'] in [400, 422]

    def test_integer_boundary_at_minimum(self, generator):
        """Test generating boundary value at minimum"""
        endpoint = {
            "path": "/api/users",
            "method": "GET",
            "parameters": [{"name": "age", "in": "query", "type": "integer"}]
        }

        parameter_constraints = {
            "age": {
                "type": "integer",
                "constraints": [
                    {"constraint_type": "min_value", "value": 18}
                ]
            }
        }

        test_suite = generator.generate_boundary_test_suite(
            endpoint, parameter_constraints
        )

        # Find test with value at minimum (18)
        at_min_test = None
        for test in test_suite:
            if test.get('payload', {}).get('age') == 18:
                at_min_test = test
                break

        assert at_min_test is not None
        assert at_min_test['boundary_info']['expected_valid'] is True
        assert at_min_test['expected_status'] == 200

    # ========================================================================
    # String Length Boundary Tests
    # ========================================================================

    def test_generate_string_length_boundary_tests(self, generator):
        """Test generating boundary tests for string length constraints"""
        endpoint = {
            "path": "/api/users",
            "method": "POST",
            "parameters": [
                {
                    "name": "username",
                    "in": "body",
                    "type": "string"
                }
            ]
        }

        parameter_constraints = {
            "username": {
                "type": "string",
                "constraints": [
                    {"constraint_type": "min_length", "value": 3},
                    {"constraint_type": "max_length", "value": 20}
                ]
            }
        }

        test_suite = generator.generate_boundary_test_suite(
            endpoint, parameter_constraints
        )

        assert len(test_suite) > 0

        # Should have tests for various string lengths
        # Check for boundary tests (e.g., length 2, 3, 4, 19, 20, 21)
        payload_lengths = []
        for test in test_suite:
            username = test.get('payload', {}).get('username', '')
            if isinstance(username, str):
                payload_lengths.append(len(username))

        # Should have string with below minimum length
        assert any(length < 3 for length in payload_lengths)
        # Should have string at minimum length
        assert 3 in payload_lengths
        # Should have string at maximum length
        assert 20 in payload_lengths
        # Should have string above maximum length
        assert any(length > 20 for length in payload_lengths)

    def test_string_boundary_empty_string(self, generator):
        """Test generating empty string boundary test"""
        endpoint = {
            "path": "/api/users",
            "method": "POST",
            "parameters": [{"name": "name", "in": "body", "type": "string"}]
        }

        parameter_constraints = {
            "name": {
                "type": "string",
                "constraints": [
                    {"constraint_type": "min_length", "value": 1}
                ]
            }
        }

        test_suite = generator.generate_boundary_test_suite(
            endpoint, parameter_constraints
        )

        # Find test with empty string
        empty_string_test = None
        for test in test_suite:
            if test.get('payload', {}).get('name') == '':
                empty_string_test = test
                break

        assert empty_string_test is not None
        assert empty_string_test['boundary_info']['expected_valid'] is False

    # ========================================================================
    # Focus Parameter Tests
    # ========================================================================

    def test_focus_on_single_parameter(self, generator):
        """Test generating boundary tests for only one parameter"""
        endpoint = {
            "path": "/api/users",
            "method": "GET",
            "parameters": [
                {"name": "page", "in": "query", "type": "integer"},
                {"name": "limit", "in": "query", "type": "integer"}
            ]
        }

        parameter_constraints = {
            "page": {
                "type": "integer",
                "constraints": [{"constraint_type": "min_value", "value": 1}]
            },
            "limit": {
                "type": "integer",
                "constraints": [{"constraint_type": "min_value", "value": 1}]
            }
        }

        # Generate tests only for 'page' parameter
        test_suite = generator.generate_boundary_test_suite(
            endpoint, parameter_constraints, focus_param="page"
        )

        # All tests should be testing the 'page' parameter
        for test in test_suite:
            assert test['boundary_info']['parameter'] == 'page'

    # ========================================================================
    # Enum Boundary Tests
    # ========================================================================

    def test_generate_enum_boundary_tests(self, generator):
        """Test generating boundary tests for enum parameters"""
        endpoint = {
            "path": "/api/users",
            "method": "GET",
            "parameters": [
                {"name": "status", "in": "query", "type": "string"}
            ]
        }

        parameter_constraints = {
            "status": {
                "type": "string",
                "constraints": [
                    {"constraint_type": "enum", "value": ["active", "inactive", "pending"]}
                ]
            }
        }

        test_suite = generator.generate_boundary_test_suite(
            endpoint, parameter_constraints
        )

        assert len(test_suite) > 0

        # Should have tests for all valid enum values
        valid_values = []
        for test in test_suite:
            if test['boundary_info'].get('expected_valid'):
                status = test.get('payload', {}).get('status')
                valid_values.append(status)

        assert "active" in valid_values
        assert "inactive" in valid_values
        assert "pending" in valid_values

        # Should also have test with invalid enum value
        invalid_tests = [t for t in test_suite if not t['boundary_info'].get('expected_valid')]
        assert len(invalid_tests) > 0

    # ========================================================================
    # Multiple Parameters Tests
    # ========================================================================

    def test_generate_tests_for_multiple_parameters(self, generator):
        """Test generating boundary tests when multiple parameters have constraints"""
        endpoint = {
            "path": "/api/users",
            "method": "GET",
            "parameters": [
                {"name": "page", "in": "query", "type": "integer"},
                {"name": "limit", "in": "query", "type": "integer"},
                {"name": "search", "in": "query", "type": "string"}
            ]
        }

        parameter_constraints = {
            "page": {
                "type": "integer",
                "constraints": [
                    {"constraint_type": "min_value", "value": 1},
                    {"constraint_type": "max_value", "value": 100}
                ]
            },
            "limit": {
                "type": "integer",
                "constraints": [
                    {"constraint_type": "min_value", "value": 1},
                    {"constraint_type": "max_value", "value": 50}
                ]
            },
            "search": {
                "type": "string",
                "constraints": [
                    {"constraint_type": "min_length", "value": 2},
                    {"constraint_type": "max_length", "value": 100}
                ]
            }
        }

        test_suite = generator.generate_boundary_test_suite(
            endpoint, parameter_constraints
        )

        # Should have boundary tests for all three parameters
        tested_params = set()
        for test in test_suite:
            param = test['boundary_info']['parameter']
            tested_params.add(param)

        assert "page" in tested_params
        assert "limit" in tested_params
        assert "search" in tested_params

        # Total tests should be sum of boundary tests for all params
        assert len(test_suite) > 10  # At least 6 tests per param * 3 params

    # ========================================================================
    # Edge Cases Tests
    # ========================================================================

    def test_no_parameters(self, generator):
        """Test handling endpoint with no parameters"""
        endpoint = {
            "path": "/api/health",
            "method": "GET",
            "parameters": []
        }

        parameter_constraints = {}

        test_suite = generator.generate_boundary_test_suite(
            endpoint, parameter_constraints
        )

        assert isinstance(test_suite, list)
        assert len(test_suite) == 0

    def test_parameters_without_constraints(self, generator):
        """Test handling parameters without boundary-testable constraints"""
        endpoint = {
            "path": "/api/data",
            "method": "GET",
            "parameters": [
                {"name": "query", "in": "query", "type": "string"}
            ]
        }

        # No constraints defined
        parameter_constraints = {
            "query": {
                "type": "string",
                "constraints": []
            }
        }

        test_suite = generator.generate_boundary_test_suite(
            endpoint, parameter_constraints
        )

        # Should return empty or minimal suite since no boundaries to test
        assert isinstance(test_suite, list)

    def test_parameter_with_only_minimum(self, generator):
        """Test handling parameter with only minimum constraint"""
        endpoint = {
            "path": "/api/users",
            "method": "GET",
            "parameters": [{"name": "age", "in": "query", "type": "integer"}]
        }

        parameter_constraints = {
            "age": {
                "type": "integer",
                "constraints": [
                    {"constraint_type": "min_value", "value": 18}
                ]
            }
        }

        test_suite = generator.generate_boundary_test_suite(
            endpoint, parameter_constraints
        )

        assert len(test_suite) > 0

        # Should have tests for: min-1, min, min+1
        # (No max tests since max not defined)

    def test_parameter_with_only_maximum(self, generator):
        """Test handling parameter with only maximum constraint"""
        endpoint = {
            "path": "/api/users",
            "method": "GET",
            "parameters": [{"name": "limit", "in": "query", "type": "integer"}]
        }

        parameter_constraints = {
            "limit": {
                "type": "integer",
                "constraints": [
                    {"constraint_type": "max_value", "value": 100}
                ]
            }
        }

        test_suite = generator.generate_boundary_test_suite(
            endpoint, parameter_constraints
        )

        assert len(test_suite) > 0

        # Should have tests for: max-1, max, max+1

    # ========================================================================
    # Test Case Structure Tests
    # ========================================================================

    def test_test_case_structure(self, generator):
        """Test that generated test cases have correct structure"""
        endpoint = {
            "path": "/api/users",
            "method": "GET",
            "parameters": [{"name": "page", "in": "query", "type": "integer"}]
        }

        parameter_constraints = {
            "page": {
                "type": "integer",
                "constraints": [{"constraint_type": "min_value", "value": 1}]
            }
        }

        test_suite = generator.generate_boundary_test_suite(
            endpoint, parameter_constraints
        )

        assert len(test_suite) > 0

        # Check first test case has required fields
        test_case = test_suite[0]

        assert 'name' in test_case
        assert 'type' in test_case
        assert test_case['type'] == 'boundary'
        assert 'payload' in test_case
        assert 'expected_status' in test_case
        assert 'boundary_info' in test_case
        assert 'confidence' in test_case

        # Check boundary_info structure
        boundary_info = test_case['boundary_info']
        assert 'parameter' in boundary_info
        assert 'parameter_type' in boundary_info
        assert 'expected_valid' in boundary_info

    def test_test_case_names_are_descriptive(self, generator):
        """Test that test case names are descriptive"""
        endpoint = {
            "path": "/api/users",
            "method": "GET",
            "parameters": [{"name": "age", "in": "query", "type": "integer"}]
        }

        parameter_constraints = {
            "age": {
                "type": "integer",
                "constraints": [
                    {"constraint_type": "min_value", "value": 18}
                ]
            }
        }

        test_suite = generator.generate_boundary_test_suite(
            endpoint, parameter_constraints
        )

        # All test names should include parameter name
        for test in test_suite:
            name = test['name']
            assert 'age' in name.lower()
            assert 'Boundary' in name or 'boundary' in name
