"""
Constraint-Aware Data Generator
Generates test data based on extracted parameter constraints
Produces valid, realistic, and boundary-testing data
"""
import re
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum


class DataGenerationStrategy(str, Enum):
    """Data generation strategies"""
    VALID = "valid"  # Valid data within constraints
    BOUNDARY_MIN = "boundary_min"  # At minimum boundary
    BOUNDARY_MAX = "boundary_max"  # At maximum boundary
    INVALID_BELOW_MIN = "invalid_below_min"  # Below minimum (for negative tests)
    INVALID_ABOVE_MAX = "invalid_above_max"  # Above maximum (for negative tests)
    INVALID_TYPE = "invalid_type"  # Wrong type
    INVALID_FORMAT = "invalid_format"  # Invalid format
    EMPTY = "empty"  # Empty value
    NULL = "null"  # Null value


class ConstraintAwareDataGenerator:
    """
    Generates test data based on parameter constraints

    This generator uses extracted constraints to produce:
    - Valid data that satisfies all constraints
    - Boundary values for testing edge cases
    - Invalid data for negative testing
    - Realistic data using proper formats
    """

    def __init__(self):
        # Format generators
        self.format_generators = {
            'email': self._generate_email,
            'url': self._generate_url,
            'uuid': self._generate_uuid,
            'date': self._generate_date,
            'datetime': self._generate_datetime,
        }

    def generate_value(
        self,
        param_name: str,
        param_type: str,
        constraints: List[Dict[str, Any]],
        strategy: DataGenerationStrategy = DataGenerationStrategy.VALID,
        example_values: List[Any] = None
    ) -> Any:
        """
        Generate value for a parameter based on constraints

        Args:
            param_name: Parameter name
            param_type: Parameter type (string, integer, number, boolean, array, object)
            constraints: List of constraints for this parameter
            strategy: Generation strategy
            example_values: Example values from documentation (prioritized)

        Returns:
            Generated value
        """
        # First, try to use example values from documentation (highest priority)
        if strategy == DataGenerationStrategy.VALID and example_values:
            return example_values[0]  # Use first example as "golden" data

        # Convert constraints list to dict for easier access
        constraints_dict = {c['type']: c for c in constraints}

        # Generate based on type
        if param_type == 'string':
            return self._generate_string(param_name, constraints_dict, strategy)
        elif param_type in ['integer', 'number']:
            return self._generate_number(param_name, constraints_dict, strategy, is_integer=(param_type == 'integer'))
        elif param_type == 'boolean':
            return self._generate_boolean(strategy)
        elif param_type == 'array':
            return self._generate_array(param_name, constraints_dict, strategy)
        elif param_type == 'object':
            return self._generate_object(param_name, constraints_dict, strategy)
        else:
            # Unknown type - generate string
            return self._generate_string(param_name, constraints_dict, strategy)

    def _generate_string(
        self,
        param_name: str,
        constraints: Dict[str, Dict],
        strategy: DataGenerationStrategy
    ) -> str:
        """Generate string value based on constraints"""

        # Check for format constraint first
        format_constraint = constraints.get('format')
        if format_constraint and strategy in [DataGenerationStrategy.VALID, DataGenerationStrategy.BOUNDARY_MIN, DataGenerationStrategy.BOUNDARY_MAX]:
            format_type = format_constraint['value']
            if format_type in self.format_generators:
                return self.format_generators[format_type](param_name)

        # Check for enum constraint
        enum_constraint = constraints.get('enum')
        if enum_constraint:
            values = enum_constraint['value']
            if strategy == DataGenerationStrategy.VALID:
                return values[0] if values else "value"
            elif strategy == DataGenerationStrategy.INVALID_FORMAT:
                return "INVALID_ENUM_VALUE"
            else:
                return values[0] if values else "value"

        # Check for pattern constraint
        pattern_constraint = constraints.get('pattern')
        if pattern_constraint and strategy == DataGenerationStrategy.VALID:
            # For now, generate generic string - could enhance with regex generation
            return self._generate_pattern_matching_string(pattern_constraint['value'])

        # Length constraints
        min_length = constraints.get('min_length', {}).get('value', 1)
        max_length = constraints.get('max_length', {}).get('value', 50)

        if strategy == DataGenerationStrategy.VALID:
            # Generate valid string within constraints
            length = min(min_length + 5, max_length)  # Slightly above minimum
            return self._generate_realistic_string(param_name, length)

        elif strategy == DataGenerationStrategy.BOUNDARY_MIN:
            # Exactly at minimum length
            return self._generate_realistic_string(param_name, min_length)

        elif strategy == DataGenerationStrategy.BOUNDARY_MAX:
            # Exactly at maximum length
            return self._generate_realistic_string(param_name, max_length)

        elif strategy == DataGenerationStrategy.INVALID_BELOW_MIN:
            # Below minimum length
            if min_length > 0:
                return self._generate_realistic_string(param_name, min_length - 1)
            else:
                return ""

        elif strategy == DataGenerationStrategy.INVALID_ABOVE_MAX:
            # Above maximum length
            return self._generate_realistic_string(param_name, max_length + 10)

        elif strategy == DataGenerationStrategy.EMPTY:
            return ""

        elif strategy == DataGenerationStrategy.NULL:
            return None

        else:
            return self._generate_realistic_string(param_name, min_length + 5)

    def _generate_number(
        self,
        param_name: str,
        constraints: Dict[str, Dict],
        strategy: DataGenerationStrategy,
        is_integer: bool = True
    ) -> float:
        """Generate numeric value based on constraints"""

        min_value = constraints.get('min_value', {}).get('value', 0)
        max_value = constraints.get('max_value', {}).get('value', 1000)

        if strategy == DataGenerationStrategy.VALID:
            # Generate valid number within constraints
            value = (min_value + max_value) / 2  # Middle value
            return int(value) if is_integer else value

        elif strategy == DataGenerationStrategy.BOUNDARY_MIN:
            # Exactly at minimum
            return int(min_value) if is_integer else min_value

        elif strategy == DataGenerationStrategy.BOUNDARY_MAX:
            # Exactly at maximum
            return int(max_value) if is_integer else max_value

        elif strategy == DataGenerationStrategy.INVALID_BELOW_MIN:
            # Below minimum
            value = min_value - 1
            return int(value) if is_integer else value

        elif strategy == DataGenerationStrategy.INVALID_ABOVE_MAX:
            # Above maximum
            value = max_value + 1
            return int(value) if is_integer else value

        elif strategy == DataGenerationStrategy.INVALID_TYPE:
            # Return string instead of number
            return "not_a_number"

        elif strategy == DataGenerationStrategy.NULL:
            return None

        else:
            value = (min_value + max_value) / 2
            return int(value) if is_integer else value

    def _generate_boolean(self, strategy: DataGenerationStrategy) -> bool:
        """Generate boolean value"""
        if strategy == DataGenerationStrategy.INVALID_TYPE:
            return "not_a_boolean"
        elif strategy == DataGenerationStrategy.NULL:
            return None
        else:
            return True

    def _generate_array(
        self,
        param_name: str,
        constraints: Dict[str, Dict],
        strategy: DataGenerationStrategy
    ) -> List:
        """Generate array value"""
        if strategy == DataGenerationStrategy.EMPTY:
            return []
        elif strategy == DataGenerationStrategy.NULL:
            return None
        else:
            # Generate simple array with one element
            return ["item1"]

    def _generate_object(
        self,
        param_name: str,
        constraints: Dict[str, Dict],
        strategy: DataGenerationStrategy
    ) -> Dict:
        """Generate object value"""
        if strategy == DataGenerationStrategy.EMPTY:
            return {}
        elif strategy == DataGenerationStrategy.NULL:
            return None
        else:
            # Generate simple object
            return {"key": "value"}

    # Format-specific generators

    def _generate_email(self, param_name: str = "user") -> str:
        """Generate valid email address"""
        # Use param name as username for realism
        username = param_name.lower().replace("_", ".")
        if username == "email":
            username = "user"
        return f"{username}@example.com"

    def _generate_url(self, param_name: str = "url") -> str:
        """Generate valid URL"""
        return "https://example.com/api/resource"

    def _generate_uuid(self, param_name: str = "id") -> str:
        """Generate valid UUID"""
        return str(uuid.uuid4())

    def _generate_date(self, param_name: str = "date") -> str:
        """Generate valid ISO date"""
        # Use today's date
        return datetime.now().strftime("%Y-%m-%d")

    def _generate_datetime(self, param_name: str = "datetime") -> str:
        """Generate valid ISO datetime"""
        # Use current datetime
        return datetime.now().isoformat()

    def _generate_realistic_string(self, param_name: str, length: int) -> str:
        """Generate realistic string based on parameter name"""
        # Use parameter name to generate contextually relevant string
        base = param_name.lower()

        # Common parameter name patterns
        if 'name' in base:
            return self._pad_string("John Doe", length)
        elif 'email' in base:
            return self._pad_string("user@example.com", length)
        elif 'password' in base:
            return self._pad_string("SecurePass123!", length)
        elif 'phone' in base:
            return self._pad_string("+1234567890", length)
        elif 'address' in base:
            return self._pad_string("123 Main Street", length)
        elif 'city' in base:
            return self._pad_string("New York", length)
        elif 'country' in base:
            return self._pad_string("USA", length)
        elif 'code' in base or 'token' in base:
            return self._pad_string("ABC123", length)
        elif 'description' in base or 'comment' in base:
            return self._pad_string("This is a description", length)
        elif 'id' in base:
            return self._pad_string("12345", length)
        else:
            # Generic string
            return self._pad_string("test_value", length)

    def _pad_string(self, base: str, target_length: int) -> str:
        """Pad or trim string to target length"""
        if len(base) >= target_length:
            return base[:target_length]
        else:
            # Pad with underscores and numbers
            padding_needed = target_length - len(base)
            padding = "_" + "x" * (padding_needed - 1)
            return base + padding

    def _generate_pattern_matching_string(self, pattern: str) -> str:
        """Generate string that might match regex pattern (basic implementation)"""
        # This is a simple implementation - could be enhanced with regex generation library
        # For now, return a sensible default
        return "pattern_match_test"

    def generate_boundary_test_values(
        self,
        param_name: str,
        param_type: str,
        constraints: List[Dict[str, Any]],
        example_values: List[Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate comprehensive set of boundary test values

        Returns list of test cases with:
        - description: What this test case checks
        - value: The generated value
        - expected_valid: Whether this should be accepted by API
        """
        test_cases = []

        # Valid value (use example if available)
        if example_values:
            test_cases.append({
                'description': 'Valid value from documentation example',
                'value': example_values[0],
                'expected_valid': True,
                'strategy': 'example'
            })

        # Generate valid value
        test_cases.append({
            'description': 'Valid value within constraints',
            'value': self.generate_value(param_name, param_type, constraints, DataGenerationStrategy.VALID),
            'expected_valid': True,
            'strategy': 'valid'
        })

        # For numeric/string types, test boundaries
        if param_type in ['integer', 'number', 'string']:
            # Minimum boundary
            test_cases.append({
                'description': 'At minimum boundary',
                'value': self.generate_value(param_name, param_type, constraints, DataGenerationStrategy.BOUNDARY_MIN),
                'expected_valid': True,
                'strategy': 'boundary_min'
            })

            # Maximum boundary
            test_cases.append({
                'description': 'At maximum boundary',
                'value': self.generate_value(param_name, param_type, constraints, DataGenerationStrategy.BOUNDARY_MAX),
                'expected_valid': True,
                'strategy': 'boundary_max'
            })

            # Below minimum (negative test)
            test_cases.append({
                'description': 'Below minimum (should fail)',
                'value': self.generate_value(param_name, param_type, constraints, DataGenerationStrategy.INVALID_BELOW_MIN),
                'expected_valid': False,
                'strategy': 'invalid_below_min'
            })

            # Above maximum (negative test)
            test_cases.append({
                'description': 'Above maximum (should fail)',
                'value': self.generate_value(param_name, param_type, constraints, DataGenerationStrategy.INVALID_ABOVE_MAX),
                'expected_valid': False,
                'strategy': 'invalid_above_max'
            })

        # Check for enum constraint
        constraints_dict = {c['type']: c for c in constraints}
        enum_constraint = constraints_dict.get('enum')
        if enum_constraint:
            # Test each enum value
            for enum_value in enum_constraint['value']:
                test_cases.append({
                    'description': f'Enum value: {enum_value}',
                    'value': enum_value,
                    'expected_valid': True,
                    'strategy': 'enum_value'
                })

        return test_cases

    def generate_payload_with_constraints(
        self,
        endpoint: Dict[str, Any],
        parameter_constraints: Dict[str, Dict],
        strategy: DataGenerationStrategy = DataGenerationStrategy.VALID
    ) -> Dict[str, Any]:
        """
        Generate complete request payload using constraints

        Args:
            endpoint: Endpoint definition
            parameter_constraints: Constraints for endpoint parameters
            strategy: Generation strategy

        Returns:
            Generated payload dict
        """
        payload = {}

        parameters = endpoint.get('parameters', [])

        for param in parameters:
            param_name = param.get('name', '')
            param_required = param.get('required', False)

            # Skip optional params for some strategies
            if not param_required and strategy in [DataGenerationStrategy.BOUNDARY_MIN]:
                continue

            # Get constraints for this parameter
            param_constraint = parameter_constraints.get(param_name, {})

            param_type = param_constraint.get('type', 'string')
            constraints = param_constraint.get('constraints', [])
            example_values = param_constraint.get('example_values', [])

            # Generate value
            value = self.generate_value(
                param_name,
                param_type,
                constraints,
                strategy,
                example_values
            )

            if value is not None or param_required:
                payload[param_name] = value

        return payload
