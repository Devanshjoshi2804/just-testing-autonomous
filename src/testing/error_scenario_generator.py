"""
Error Scenario Generator
Generates test scenarios for documented error conditions
Validates error message quality and consistency
"""
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

try:
    from loguru import logger
except ImportError:
    class MockLogger:
        def info(self, msg, **kwargs): print(f"INFO: {msg}")
        def warning(self, msg, **kwargs): print(f"WARN: {msg}")
        def error(self, msg, **kwargs): print(f"ERROR: {msg}")
        def debug(self, msg, **kwargs): pass
    logger = MockLogger()


class ErrorCategory(Enum):
    """Categories of API errors"""
    VALIDATION = "validation"           # Invalid input data
    AUTHENTICATION = "authentication"   # Auth required or invalid
    AUTHORIZATION = "authorization"     # Insufficient permissions
    NOT_FOUND = "not_found"            # Resource doesn't exist
    CONFLICT = "conflict"              # Duplicate or conflicting resource
    RATE_LIMIT = "rate_limit"          # Too many requests
    SERVER_ERROR = "server_error"      # Internal server error


@dataclass
class ErrorCondition:
    """Represents a documented error condition"""
    condition_name: str
    category: ErrorCategory
    trigger: str                       # How to trigger this error
    expected_status_code: int
    expected_fields: List[str]         # Required fields in error response
    description: str


@dataclass
class ErrorScenario:
    """Test scenario for a specific error condition"""
    endpoint_key: str
    method: str
    path: str
    error_condition: ErrorCondition
    trigger_payload: Optional[Dict[str, Any]] = None
    trigger_headers: Optional[Dict[str, str]] = None
    path_modifications: Optional[Dict[str, str]] = None
    description: str = ""


class ErrorScenarioGenerator:
    """
    Generates test scenarios for error conditions

    Tests:
    1. Each documented error condition can be triggered
    2. Error responses have required fields
    3. Error messages are helpful (not generic)
    4. Error format is consistent
    5. Error details provide context
    """

    # Common error conditions
    COMMON_ERROR_CONDITIONS = [
        # Validation errors
        ErrorCondition(
            condition_name="missing_required_field",
            category=ErrorCategory.VALIDATION,
            trigger="Omit required field from request body",
            expected_status_code=422,
            expected_fields=["error", "message", "details", "field"],
            description="Missing required field triggers 422 with field name"
        ),
        ErrorCondition(
            condition_name="invalid_field_type",
            category=ErrorCategory.VALIDATION,
            trigger="Send wrong type for field (string instead of number)",
            expected_status_code=422,
            expected_fields=["error", "message", "details", "field", "expected_type"],
            description="Invalid field type triggers 422 with type info"
        ),
        ErrorCondition(
            condition_name="invalid_field_format",
            category=ErrorCategory.VALIDATION,
            trigger="Send invalid format (bad email, URL, date)",
            expected_status_code=422,
            expected_fields=["error", "message", "details", "field", "format"],
            description="Invalid format triggers 422 with format requirements"
        ),
        ErrorCondition(
            condition_name="field_out_of_range",
            category=ErrorCategory.VALIDATION,
            trigger="Send value outside allowed range (age: -5)",
            expected_status_code=422,
            expected_fields=["error", "message", "details", "field", "min", "max"],
            description="Out of range value triggers 422 with constraints"
        ),

        # Authentication errors
        ErrorCondition(
            condition_name="missing_authentication",
            category=ErrorCategory.AUTHENTICATION,
            trigger="Request without Authorization header",
            expected_status_code=401,
            expected_fields=["error", "message"],
            description="Missing auth triggers 401 with auth requirement message"
        ),
        ErrorCondition(
            condition_name="invalid_token",
            category=ErrorCategory.AUTHENTICATION,
            trigger="Request with invalid/expired token",
            expected_status_code=401,
            expected_fields=["error", "message", "auth_error_type"],
            description="Invalid token triggers 401 with specific error type"
        ),

        # Authorization errors
        ErrorCondition(
            condition_name="insufficient_permissions",
            category=ErrorCategory.AUTHORIZATION,
            trigger="Request endpoint without required role/permission",
            expected_status_code=403,
            expected_fields=["error", "message", "required_permission"],
            description="Insufficient permissions triggers 403 with required permission"
        ),

        # Not found errors
        ErrorCondition(
            condition_name="resource_not_found",
            category=ErrorCategory.NOT_FOUND,
            trigger="Request non-existent resource ID",
            expected_status_code=404,
            expected_fields=["error", "message", "resource_type", "resource_id"],
            description="Non-existent resource triggers 404 with resource info"
        ),

        # Conflict errors
        ErrorCondition(
            condition_name="duplicate_resource",
            category=ErrorCategory.CONFLICT,
            trigger="Create resource with duplicate unique field",
            expected_status_code=409,
            expected_fields=["error", "message", "conflicting_field", "conflicting_value"],
            description="Duplicate resource triggers 409 with conflict details"
        ),

        # Rate limit errors
        ErrorCondition(
            condition_name="rate_limit_exceeded",
            category=ErrorCategory.RATE_LIMIT,
            trigger="Exceed request rate limit",
            expected_status_code=429,
            expected_fields=["error", "message", "retry_after", "limit"],
            description="Rate limit triggers 429 with retry info"
        ),
    ]

    def __init__(
        self,
        documented_errors: Optional[Dict[str, List[ErrorCondition]]] = None
    ):
        """
        Initialize generator

        Args:
            documented_errors: Custom error conditions per endpoint
                              Format: {endpoint_key: [error_conditions]}
        """
        self.documented_errors = documented_errors or {}

    def generate_error_scenarios(
        self,
        endpoint: Dict[str, Any],
        error_conditions: Optional[List[ErrorCondition]] = None
    ) -> List[ErrorScenario]:
        """
        Generate error test scenarios for an endpoint

        Args:
            endpoint: Endpoint dict with path, method, parameters
            error_conditions: List of error conditions to test (defaults to common errors)

        Returns:
            List of error test scenarios
        """
        method = endpoint.get('method', 'GET').upper()
        path = endpoint.get('path', '')
        endpoint_key = f"{method} {path}"

        # Get error conditions to test
        if error_conditions is None:
            error_conditions = self._get_default_error_conditions(method)

        scenarios = []

        for condition in error_conditions:
            scenario = self._generate_scenario_for_condition(
                endpoint,
                endpoint_key,
                method,
                path,
                condition
            )

            if scenario:
                scenarios.append(scenario)

        logger.info(f"Generated {len(scenarios)} error scenarios for {endpoint_key}")
        return scenarios

    def _get_default_error_conditions(self, method: str) -> List[ErrorCondition]:
        """Get default error conditions to test based on HTTP method"""
        conditions = []

        # All methods: authentication and authorization
        conditions.extend([
            c for c in self.COMMON_ERROR_CONDITIONS
            if c.category in [ErrorCategory.AUTHENTICATION, ErrorCategory.AUTHORIZATION]
        ])

        # Methods with payloads: validation errors
        if method in ['POST', 'PUT', 'PATCH']:
            conditions.extend([
                c for c in self.COMMON_ERROR_CONDITIONS
                if c.category == ErrorCategory.VALIDATION
            ])

            # POST can have duplicates
            if method == 'POST':
                conditions.extend([
                    c for c in self.COMMON_ERROR_CONDITIONS
                    if c.category == ErrorCategory.CONFLICT
                ])

        # Methods with IDs: not found errors
        conditions.extend([
            c for c in self.COMMON_ERROR_CONDITIONS
            if c.category == ErrorCategory.NOT_FOUND
        ])

        return conditions

    def _generate_scenario_for_condition(
        self,
        endpoint: Dict[str, Any],
        endpoint_key: str,
        method: str,
        path: str,
        condition: ErrorCondition
    ) -> Optional[ErrorScenario]:
        """Generate test scenario for a specific error condition"""

        # Generate trigger payload/headers based on condition
        trigger_payload = None
        trigger_headers = None
        path_mods = None

        if condition.category == ErrorCategory.VALIDATION:
            if method in ['POST', 'PUT', 'PATCH']:
                trigger_payload = self._generate_validation_error_payload(condition)

        elif condition.category == ErrorCategory.AUTHENTICATION:
            trigger_headers = self._generate_auth_error_headers(condition)

        elif condition.category == ErrorCategory.AUTHORIZATION:
            trigger_headers = {'Authorization': 'Bearer user-token'}  # Non-admin token

        elif condition.category == ErrorCategory.NOT_FOUND:
            path_mods = self._generate_not_found_path_mods(path)

        elif condition.category == ErrorCategory.CONFLICT:
            if method == 'POST':
                trigger_payload = {'email': 'duplicate@example.com'}

        return ErrorScenario(
            endpoint_key=endpoint_key,
            method=method,
            path=path,
            error_condition=condition,
            trigger_payload=trigger_payload,
            trigger_headers=trigger_headers,
            path_modifications=path_mods,
            description=f"Test {condition.condition_name} on {endpoint_key}"
        )

    def _generate_validation_error_payload(
        self,
        condition: ErrorCondition
    ) -> Dict[str, Any]:
        """Generate payload to trigger validation error"""

        if condition.condition_name == "missing_required_field":
            return {}  # Empty payload

        elif condition.condition_name == "invalid_field_type":
            return {
                'id': 'not-a-number',
                'count': 'invalid',
                'active': 'yes',
                'price': 'free'
            }

        elif condition.condition_name == "invalid_field_format":
            return {
                'email': 'not-an-email',
                'url': 'not a url',
                'date': '32/13/2023',
                'phone': 'abc-def-ghij'
            }

        elif condition.condition_name == "field_out_of_range":
            return {
                'age': -5,
                'quantity': -10,
                'rating': 11,  # Assuming max is 10
                'price': -100.00
            }

        return {}

    def _generate_auth_error_headers(
        self,
        condition: ErrorCondition
    ) -> Dict[str, str]:
        """Generate headers to trigger auth error"""

        if condition.condition_name == "missing_authentication":
            return {}  # No Authorization header

        elif condition.condition_name == "invalid_token":
            return {'Authorization': 'Bearer invalid-token-xyz'}

        return {}

    def _generate_not_found_path_mods(
        self,
        path: str
    ) -> Dict[str, str]:
        """Generate path modifications to trigger 404"""

        mods = {}
        if '{id}' in path:
            mods['{id}'] = 'nonexistent-id-99999'
        if '{user_id}' in path:
            mods['{user_id}'] = 'nonexistent-user-99999'
        if '{order_id}' in path:
            mods['{order_id}'] = 'nonexistent-order-99999'

        return mods

    def generate_all_error_scenarios(
        self,
        endpoints: List[Dict[str, Any]]
    ) -> List[ErrorScenario]:
        """
        Generate error test scenarios for all endpoints

        Args:
            endpoints: List of endpoint dicts

        Returns:
            List of all error scenarios
        """
        all_scenarios = []

        for endpoint in endpoints:
            scenarios = self.generate_error_scenarios(endpoint)
            all_scenarios.extend(scenarios)

        logger.info(
            f"Generated {len(all_scenarios)} total error scenarios "
            f"for {len(endpoints)} endpoints"
        )

        return all_scenarios

    def get_scenarios_by_category(
        self,
        scenarios: List[ErrorScenario],
        category: ErrorCategory
    ) -> List[ErrorScenario]:
        """Filter scenarios by error category"""
        return [s for s in scenarios if s.error_condition.category == category]

    def get_scenarios_by_status_code(
        self,
        scenarios: List[ErrorScenario],
        status_code: int
    ) -> List[ErrorScenario]:
        """Filter scenarios by expected status code"""
        return [s for s in scenarios if s.error_condition.expected_status_code == status_code]

    def get_summary(
        self,
        scenarios: List[ErrorScenario]
    ) -> Dict[str, Any]:
        """Get summary of error scenarios"""
        by_category = {}
        by_status = {}

        for scenario in scenarios:
            # By category
            cat = scenario.error_condition.category.value
            by_category[cat] = by_category.get(cat, 0) + 1

            # By status code
            status = scenario.error_condition.expected_status_code
            by_status[status] = by_status.get(status, 0) + 1

        return {
            'total_scenarios': len(scenarios),
            'by_category': by_category,
            'by_status_code': by_status,
            'unique_categories': len(by_category),
            'unique_status_codes': len(by_status)
        }
