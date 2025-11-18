"""
Negative Test Generator
Generates comprehensive negative/invalid test cases to verify API validation
Tests: invalid types, formats, missing fields, extra fields, constraint violations
"""
from typing import Dict, Any, List, Optional
from src.generators.constraint_aware_data_generator import (
    ConstraintAwareDataGenerator,
    DataGenerationStrategy
)

# Optional logger
try:
    from loguru import logger
except ImportError:
    class MockLogger:
        def info(self, msg, **kwargs): print(f"INFO: {msg}")
        def warning(self, msg, **kwargs): print(f"WARN: {msg}")
        def error(self, msg, **kwargs): print(f"ERROR: {msg}")
        def debug(self, msg, **kwargs): pass
    logger = MockLogger()


class NegativeTestGenerator:
    """
    Generates comprehensive negative/invalid test cases

    Tests for:
    1. Invalid types (string instead of number, number instead of boolean, etc.)
    2. Invalid formats (malformed email, UUID, date, URL, etc.)
    3. Missing required fields (omit each required field one at a time)
    4. Extra/unknown fields (add fields not in schema)
    5. Constraint violations (values outside min/max, wrong enum, etc.)
    6. Null/empty values for required fields

    Each negative test should return 400 Bad Request (or appropriate error)
    """

    def __init__(self):
        self.data_generator = ConstraintAwareDataGenerator()

    def generate_negative_test_suite(
        self,
        endpoint: Dict[str, Any],
        parameter_constraints: Dict[str, Dict]
    ) -> List[Dict[str, Any]]:
        """
        Generate comprehensive negative test suite for an endpoint

        Args:
            endpoint: Endpoint definition
            parameter_constraints: Constraints for all parameters

        Returns:
            List of negative test cases (all should fail with 400/422)
        """
        test_suite = []
        parameters = endpoint.get('parameters', [])

        if not parameters:
            logger.debug("No parameters to test for negative cases")
            return test_suite

        logger.info(f"  ⛔ Generating negative test cases...")

        # 1. Invalid type tests (for each parameter)
        type_tests = self._generate_invalid_type_tests(
            endpoint, parameters, parameter_constraints
        )
        test_suite.extend(type_tests)

        # 2. Invalid format tests (for formatted fields)
        format_tests = self._generate_invalid_format_tests(
            endpoint, parameters, parameter_constraints
        )
        test_suite.extend(format_tests)

        # 3. Missing required field tests
        missing_tests = self._generate_missing_required_tests(
            endpoint, parameters, parameter_constraints
        )
        test_suite.extend(missing_tests)

        # 4. Null value tests (for required fields)
        null_tests = self._generate_null_value_tests(
            endpoint, parameters, parameter_constraints
        )
        test_suite.extend(null_tests)

        # 5. Empty value tests (for required strings/arrays)
        empty_tests = self._generate_empty_value_tests(
            endpoint, parameters, parameter_constraints
        )
        test_suite.extend(empty_tests)

        # 6. Extra/unknown field tests
        extra_field_tests = self._generate_extra_field_tests(
            endpoint, parameters, parameter_constraints
        )
        test_suite.extend(extra_field_tests)

        # 7. Constraint violation tests (already covered by boundary testing)
        # Skip to avoid duplication

        logger.info(f"  ✅ Generated {len(test_suite)} negative test cases")

        return test_suite

    def _generate_invalid_type_tests(
        self,
        endpoint: Dict[str, Any],
        parameters: List[Dict[str, Any]],
        parameter_constraints: Dict[str, Dict]
    ) -> List[Dict[str, Any]]:
        """
        Generate tests with invalid types for each parameter

        Examples:
        - Send string "abc" for numeric field
        - Send number 123 for boolean field
        - Send boolean true for string field
        """
        tests = []

        for param in parameters:
            param_name = param.get('name', '')
            param_constraint = parameter_constraints.get(param_name, {})
            param_type = param_constraint.get('type', 'string')

            # Skip if no type info
            if not param_type:
                continue

            # Generate base payload with valid values for all other params
            base_payload = self._generate_base_payload(
                endpoint, parameter_constraints, exclude_param=param_name
            )

            # Generate invalid type value for this parameter
            invalid_value = self.data_generator.generate_value(
                param_name,
                param_type,
                param_constraint.get('constraints', []),
                DataGenerationStrategy.INVALID_TYPE
            )

            base_payload[param_name] = invalid_value

            tests.append({
                'name': f'Negative: {param_name} - Invalid type (expected {param_type})',
                'type': 'negative',
                'source': 'negative_testing',
                'payload': base_payload,
                'expected_status': 400,
                'confidence': 'HIGH',
                'negative_test_info': {
                    'category': 'invalid_type',
                    'parameter': param_name,
                    'expected_type': param_type,
                    'invalid_value': invalid_value
                }
            })

        return tests

    def _generate_invalid_format_tests(
        self,
        endpoint: Dict[str, Any],
        parameters: List[Dict[str, Any]],
        parameter_constraints: Dict[str, Dict]
    ) -> List[Dict[str, Any]]:
        """
        Generate tests with invalid formats for formatted fields

        Examples:
        - Send "not-an-email" for email field
        - Send "invalid-uuid" for UUID field
        - Send "2023-13-45" for date field
        - Send "not-a-url" for URL field
        """
        tests = []

        # Invalid format mappings
        invalid_formats = {
            'email': 'not-an-email',
            'uuid': 'invalid-uuid-format',
            'url': 'not-a-valid-url',
            'uri': 'invalid::uri',
            'date': '2023-13-45',  # Invalid month/day
            'datetime': '2023-13-45T99:99:99Z',  # Invalid datetime
            'ipv4': '999.999.999.999',  # Invalid IP
            'ipv6': 'gggg::hhhh',  # Invalid IPv6
        }

        for param in parameters:
            param_name = param.get('name', '')
            param_constraint = parameter_constraints.get(param_name, {})
            param_type = param_constraint.get('type', 'string')
            constraints = param_constraint.get('constraints', [])

            # Check if parameter has format constraint
            format_constraint = None
            for c in constraints:
                if c['type'] == 'format':
                    format_constraint = c
                    break

            if not format_constraint:
                continue

            format_type = format_constraint['value']
            invalid_value = invalid_formats.get(format_type, 'INVALID_FORMAT')

            # Generate base payload
            base_payload = self._generate_base_payload(
                endpoint, parameter_constraints, exclude_param=param_name
            )

            base_payload[param_name] = invalid_value

            tests.append({
                'name': f'Negative: {param_name} - Invalid {format_type} format',
                'type': 'negative',
                'source': 'negative_testing',
                'payload': base_payload,
                'expected_status': 400,
                'confidence': 'HIGH',
                'negative_test_info': {
                    'category': 'invalid_format',
                    'parameter': param_name,
                    'expected_format': format_type,
                    'invalid_value': invalid_value
                }
            })

        return tests

    def _generate_missing_required_tests(
        self,
        endpoint: Dict[str, Any],
        parameters: List[Dict[str, Any]],
        parameter_constraints: Dict[str, Dict]
    ) -> List[Dict[str, Any]]:
        """
        Generate tests with missing required fields

        For each required field, create a test that omits it
        """
        tests = []

        required_params = [p for p in parameters if p.get('required', False)]

        if len(required_params) == 0:
            return tests

        for param in required_params:
            param_name = param.get('name', '')

            # Generate payload without this required field
            base_payload = self._generate_base_payload(
                endpoint, parameter_constraints, exclude_param=param_name
            )

            tests.append({
                'name': f'Negative: Missing required field - {param_name}',
                'type': 'negative',
                'source': 'negative_testing',
                'payload': base_payload,
                'expected_status': 400,
                'confidence': 'HIGH',
                'negative_test_info': {
                    'category': 'missing_required',
                    'parameter': param_name,
                    'reason': 'Required field omitted'
                }
            })

        return tests

    def _generate_null_value_tests(
        self,
        endpoint: Dict[str, Any],
        parameters: List[Dict[str, Any]],
        parameter_constraints: Dict[str, Dict]
    ) -> List[Dict[str, Any]]:
        """
        Generate tests with null values for required fields

        This tests whether API properly rejects null for required fields
        """
        tests = []

        required_params = [p for p in parameters if p.get('required', False)]

        for param in required_params:
            param_name = param.get('name', '')

            # Generate base payload
            base_payload = self._generate_base_payload(
                endpoint, parameter_constraints, exclude_param=param_name
            )

            # Set this field to null
            base_payload[param_name] = None

            tests.append({
                'name': f'Negative: Null value for required field - {param_name}',
                'type': 'negative',
                'source': 'negative_testing',
                'payload': base_payload,
                'expected_status': 400,
                'confidence': 'HIGH',
                'negative_test_info': {
                    'category': 'null_value',
                    'parameter': param_name,
                    'reason': 'Required field set to null'
                }
            })

        return tests

    def _generate_empty_value_tests(
        self,
        endpoint: Dict[str, Any],
        parameters: List[Dict[str, Any]],
        parameter_constraints: Dict[str, Dict]
    ) -> List[Dict[str, Any]]:
        """
        Generate tests with empty values for required string/array fields

        Tests:
        - Empty string "" for string fields
        - Empty array [] for array fields
        """
        tests = []

        required_params = [p for p in parameters if p.get('required', False)]

        for param in required_params:
            param_name = param.get('name', '')
            param_constraint = parameter_constraints.get(param_name, {})
            param_type = param_constraint.get('type', 'string')

            # Only test empty for string and array types
            if param_type not in ['string', 'array']:
                continue

            # Generate base payload
            base_payload = self._generate_base_payload(
                endpoint, parameter_constraints, exclude_param=param_name
            )

            # Set empty value
            empty_value = "" if param_type == 'string' else []
            base_payload[param_name] = empty_value

            tests.append({
                'name': f'Negative: Empty value for required field - {param_name}',
                'type': 'negative',
                'source': 'negative_testing',
                'payload': base_payload,
                'expected_status': 400,
                'confidence': 'MEDIUM',  # Some APIs accept empty strings
                'negative_test_info': {
                    'category': 'empty_value',
                    'parameter': param_name,
                    'parameter_type': param_type,
                    'empty_value': empty_value
                }
            })

        return tests

    def _generate_extra_field_tests(
        self,
        endpoint: Dict[str, Any],
        parameters: List[Dict[str, Any]],
        parameter_constraints: Dict[str, Dict]
    ) -> List[Dict[str, Any]]:
        """
        Generate tests with extra/unknown fields

        Tests whether API properly handles unexpected fields
        (Some APIs ignore them, others reject with 400)
        """
        tests = []

        # Generate valid base payload
        base_payload = self._generate_base_payload(
            endpoint, parameter_constraints
        )

        # Add extra fields
        payload_with_extras = {
            **base_payload,
            'unknown_field_1': 'unexpected_value',
            'extra_param': 12345,
            'not_in_schema': True
        }

        tests.append({
            'name': 'Negative: Extra/unknown fields in request',
            'type': 'negative',
            'source': 'negative_testing',
            'payload': payload_with_extras,
            'expected_status': 400,  # Or 200 if API ignores extra fields
            'confidence': 'LOW',  # Many APIs ignore extra fields
            'negative_test_info': {
                'category': 'extra_fields',
                'extra_fields': ['unknown_field_1', 'extra_param', 'not_in_schema'],
                'reason': 'Testing if API rejects or ignores unknown fields'
            }
        })

        return tests

    def _generate_base_payload(
        self,
        endpoint: Dict[str, Any],
        parameter_constraints: Dict[str, Dict],
        exclude_param: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate base payload with valid values for all parameters except excluded one

        Args:
            endpoint: Endpoint definition
            parameter_constraints: Parameter constraints
            exclude_param: Parameter to exclude (for missing field tests)

        Returns:
            Payload dict with valid values
        """
        payload = {}
        parameters = endpoint.get('parameters', [])

        for param in parameters:
            param_name = param.get('name', '')

            # Skip excluded parameter
            if param_name == exclude_param:
                continue

            param_required = param.get('required', False)

            # Only include required params in base payload
            if not param_required:
                continue

            # Get constraints
            param_constraint = parameter_constraints.get(param_name, {})
            param_type = param_constraint.get('type', 'string')
            constraints = param_constraint.get('constraints', [])
            example_values = param_constraint.get('example_values', [])

            # Generate valid value
            value = self.data_generator.generate_value(
                param_name,
                param_type,
                constraints,
                DataGenerationStrategy.VALID,
                example_values
            )

            if value is not None:
                payload[param_name] = value

        return payload

    def get_negative_test_summary(
        self,
        endpoint: Dict[str, Any],
        parameter_constraints: Dict[str, Dict]
    ) -> Dict[str, Any]:
        """
        Get summary of negative tests that would be generated

        Args:
            endpoint: Endpoint definition
            parameter_constraints: Parameter constraints

        Returns:
            Summary dict with counts by category
        """
        parameters = endpoint.get('parameters', [])
        required_params = [p for p in parameters if p.get('required', False)]

        # Count testable params by category
        type_testable = len(parameters)
        format_testable = 0
        string_array_required = 0

        for param in parameters:
            param_name = param.get('name', '')
            param_constraint = parameter_constraints.get(param_name, {})
            param_type = param_constraint.get('type', 'string')
            constraints = param_constraint.get('constraints', [])

            # Check for format constraints
            has_format = any(c['type'] == 'format' for c in constraints)
            if has_format:
                format_testable += 1

            # Check for string/array required fields
            if param.get('required', False) and param_type in ['string', 'array']:
                string_array_required += 1

        estimated_tests = (
            type_testable +  # Invalid type for each param
            format_testable +  # Invalid format for formatted fields
            len(required_params) +  # Missing required field tests
            len(required_params) +  # Null value tests
            string_array_required +  # Empty value tests
            1  # Extra fields test
        )

        return {
            'total_parameters': len(parameters),
            'required_parameters': len(required_params),
            'estimated_tests': estimated_tests,
            'tests_by_category': {
                'invalid_type': type_testable,
                'invalid_format': format_testable,
                'missing_required': len(required_params),
                'null_value': len(required_params),
                'empty_value': string_array_required,
                'extra_fields': 1
            }
        }

    def should_use_negative_testing(
        self,
        endpoint: Dict[str, Any],
        parameter_constraints: Dict[str, Dict]
    ) -> bool:
        """
        Determine if negative testing is worthwhile for this endpoint

        Args:
            endpoint: Endpoint definition
            parameter_constraints: Parameter constraints

        Returns:
            True if negative testing should be used
        """
        parameters = endpoint.get('parameters', [])

        # Use negative testing if we have at least 1 parameter
        return len(parameters) > 0
