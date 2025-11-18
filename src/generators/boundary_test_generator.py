"""
Boundary Test Generator
Generates comprehensive boundary value tests for API parameters
Implements 6-point boundary testing: min-1, min, min+1, max-1, max, max+1
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


class BoundaryTestGenerator:
    """
    Generates comprehensive boundary value test suites

    For each parameter with constraints:
    - Numbers: min-1, min, min+1, max-1, max, max+1
    - Strings: empty, min length, min+1, max-1, max length, too long
    - Arrays: empty, min items, min+1, max-1, max items, too many
    - Enums: Each valid value + invalid value

    This finds off-by-one errors, edge cases, and validation bugs.
    """

    def __init__(self):
        self.data_generator = ConstraintAwareDataGenerator()

    def generate_boundary_test_suite(
        self,
        endpoint: Dict[str, Any],
        parameter_constraints: Dict[str, Dict],
        focus_param: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate comprehensive boundary test suite for an endpoint

        Args:
            endpoint: Endpoint definition
            parameter_constraints: Constraints for all parameters
            focus_param: If specified, only generate boundary tests for this parameter

        Returns:
            List of boundary test cases
        """
        test_suite = []
        parameters = endpoint.get('parameters', [])

        if not parameter_constraints:
            logger.warning("No parameter constraints available for boundary testing")
            return test_suite

        # Identify parameters that have boundary-testable constraints
        testable_params = self._identify_testable_parameters(
            parameters, parameter_constraints
        )

        if not testable_params:
            logger.debug("No parameters with boundary-testable constraints")
            return test_suite

        logger.info(
            f"  📊 Generating boundary tests for {len(testable_params)} parameters"
        )

        # Generate boundary tests for each parameter
        for param in testable_params:
            param_name = param['name']

            # Skip if focus_param is specified and this isn't it
            if focus_param and param_name != focus_param:
                continue

            param_constraint = parameter_constraints.get(param_name, {})
            param_type = param_constraint.get('type', 'string')
            constraints = param_constraint.get('constraints', [])
            example_values = param_constraint.get('example_values', [])

            # Generate boundary test values for this parameter
            boundary_tests = self.data_generator.generate_boundary_test_values(
                param_name=param_name,
                param_type=param_type,
                constraints=constraints,
                example_values=example_values
            )

            # For each boundary test value, generate a complete test case
            for i, boundary_test in enumerate(boundary_tests, 1):
                # Generate base payload with valid values for all other params
                base_payload = self._generate_base_payload(
                    endpoint, parameter_constraints, exclude_param=param_name
                )

                # Set the boundary test value for the focused parameter
                base_payload[param_name] = boundary_test['value']

                # Create test case
                test_case = {
                    'name': f'Boundary: {param_name} - {boundary_test["description"]}',
                    'type': 'boundary',
                    'source': 'boundary_testing',
                    'payload': base_payload,
                    'expected_status': 200 if boundary_test['expected_valid'] else 400,
                    'confidence': 'HIGH',  # Boundary tests are authoritative
                    'boundary_info': {
                        'parameter': param_name,
                        'parameter_type': param_type,
                        'test_point': boundary_test['strategy'],
                        'expected_valid': boundary_test['expected_valid'],
                        'test_value': boundary_test['value']
                    }
                }

                test_suite.append(test_case)

        logger.info(f"  ✅ Generated {len(test_suite)} boundary test cases")

        return test_suite

    def _identify_testable_parameters(
        self,
        parameters: List[Dict[str, Any]],
        parameter_constraints: Dict[str, Dict]
    ) -> List[Dict[str, Any]]:
        """
        Identify parameters that have boundary-testable constraints

        Returns parameters that have:
        - Min/max value constraints (for numbers)
        - Min/max length constraints (for strings)
        - Min/max items constraints (for arrays)
        - Enum constraints
        """
        testable = []

        for param in parameters:
            param_name = param.get('name', '')
            param_constraint = parameter_constraints.get(param_name, {})
            constraints = param_constraint.get('constraints', [])

            if not constraints:
                continue

            # Check if parameter has boundary-testable constraints
            constraint_types = {c['type'] for c in constraints}

            has_boundary_constraint = bool(
                constraint_types & {
                    'min_value', 'max_value',
                    'min_length', 'max_length',
                    'min_items', 'max_items',
                    'enum'
                }
            )

            if has_boundary_constraint:
                testable.append(param)

        return testable

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
            exclude_param: Parameter to exclude (will be set by boundary test)

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

            # Only include required params in base payload (to isolate boundary test)
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

    def get_boundary_test_summary(
        self,
        endpoint: Dict[str, Any],
        parameter_constraints: Dict[str, Dict]
    ) -> Dict[str, Any]:
        """
        Get summary of boundary tests that would be generated

        Args:
            endpoint: Endpoint definition
            parameter_constraints: Parameter constraints

        Returns:
            Summary dict with counts and coverage info
        """
        parameters = endpoint.get('parameters', [])
        testable_params = self._identify_testable_parameters(
            parameters, parameter_constraints
        )

        # Estimate test count
        estimated_tests = 0
        params_by_type = {
            'numeric': 0,
            'string': 0,
            'array': 0,
            'enum': 0
        }

        for param in testable_params:
            param_name = param.get('name', '')
            param_constraint = parameter_constraints.get(param_name, {})
            param_type = param_constraint.get('type', 'string')
            constraints = param_constraint.get('constraints', [])

            # Count boundary test points based on type
            if param_type in ['integer', 'number']:
                # 6-point boundary testing + 2 valid tests = 8 tests
                estimated_tests += 8
                params_by_type['numeric'] += 1
            elif param_type == 'string':
                # 6-point boundary + empty + 2 valid = 9 tests
                estimated_tests += 9
                params_by_type['string'] += 1
            elif param_type == 'array':
                # 6-point boundary + empty + 2 valid = 9 tests
                estimated_tests += 9
                params_by_type['array'] += 1

            # Check for enum
            constraints_dict = {c['type']: c for c in constraints}
            enum_constraint = constraints_dict.get('enum')
            if enum_constraint:
                # Test each enum value
                enum_count = len(enum_constraint.get('value', []))
                estimated_tests += enum_count
                params_by_type['enum'] += 1

        return {
            'total_parameters': len(parameters),
            'testable_parameters': len(testable_params),
            'estimated_tests': estimated_tests,
            'parameters_by_type': params_by_type,
            'coverage': {
                'has_boundary_testing': len(testable_params) > 0,
                'coverage_percentage': (len(testable_params) / len(parameters) * 100) if parameters else 0
            }
        }

    def should_use_boundary_testing(
        self,
        endpoint: Dict[str, Any],
        parameter_constraints: Dict[str, Dict]
    ) -> bool:
        """
        Determine if boundary testing is worthwhile for this endpoint

        Args:
            endpoint: Endpoint definition
            parameter_constraints: Parameter constraints

        Returns:
            True if boundary testing should be used
        """
        parameters = endpoint.get('parameters', [])
        testable_params = self._identify_testable_parameters(
            parameters, parameter_constraints
        )

        # Use boundary testing if we have at least 1 testable parameter
        return len(testable_params) > 0
