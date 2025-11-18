"""
Status Code Scenario Generator
Generates test scenarios to intentionally trigger each documented HTTP status code
Ensures comprehensive error handling coverage
"""
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
import uuid
import random

try:
    from loguru import logger
except ImportError:
    class MockLogger:
        def info(self, msg, **kwargs): print(f"INFO: {msg}")
        def warning(self, msg, **kwargs): print(f"WARN: {msg}")
        def error(self, msg, **kwargs): print(f"ERROR: {msg}")
        def debug(self, msg, **kwargs): pass
    logger = MockLogger()


@dataclass
class StatusCodeScenario:
    """Represents a test scenario designed to trigger a specific status code"""
    status_code: int
    scenario_type: str
    description: str
    endpoint_key: str
    method: str
    path: str
    headers: Dict[str, str] = field(default_factory=dict)
    payload: Optional[Dict[str, Any]] = None
    path_modifications: Optional[Dict[str, str]] = None  # e.g., {"{id}": "nonexistent-id"}
    expected_behavior: str = ""


class StatusCodeScenarioGenerator:
    """
    Generates test scenarios to trigger all documented HTTP status codes

    Supports:
    - 2xx: Success scenarios (200, 201, 204)
    - 4xx: Client error scenarios (400, 401, 403, 404, 409, 422)
    - 5xx: Server error scenarios (500, 503)
    """

    # Common status codes and their typical triggers
    STATUS_CODE_SCENARIOS = {
        200: "Successful GET/PUT request",
        201: "Successful POST (resource created)",
        204: "Successful DELETE (no content)",

        400: "Bad Request - Invalid payload",
        401: "Unauthorized - Missing/invalid auth",
        403: "Forbidden - Insufficient permissions",
        404: "Not Found - Resource doesn't exist",
        409: "Conflict - Duplicate resource",
        422: "Unprocessable Entity - Validation failed",

        500: "Internal Server Error",
        503: "Service Unavailable",
    }

    def __init__(self, documented_responses: Optional[Dict[str, List[int]]] = None):
        """
        Initialize generator

        Args:
            documented_responses: Dict mapping endpoint_key to list of documented status codes
                                 e.g., {"GET /users/{id}": [200, 404, 401]}
        """
        self.documented_responses = documented_responses or {}
        self.scenarios: List[StatusCodeScenario] = []

    def generate_scenarios_for_endpoint(
        self,
        endpoint: Dict[str, Any],
        documented_codes: Optional[List[int]] = None,
        auth_required: bool = False
    ) -> List[StatusCodeScenario]:
        """
        Generate test scenarios for all documented status codes of an endpoint

        Args:
            endpoint: Endpoint dict with path, method, parameters
            documented_codes: List of documented status codes (defaults to common codes)
            auth_required: Whether endpoint requires authentication

        Returns:
            List of test scenarios
        """
        method = endpoint.get('method', 'GET').upper()
        path = endpoint.get('path', '')
        endpoint_key = f"{method} {path}"

        # Get documented codes (or use defaults based on method)
        if documented_codes is None:
            documented_codes = self._get_default_status_codes(method)

        scenarios = []

        logger.debug(f"Generating scenarios for {endpoint_key} (codes: {documented_codes})")

        for status_code in documented_codes:
            scenario_generators = self._get_scenario_generators_for_code(status_code)

            for generator_func in scenario_generators:
                scenario = generator_func(
                    endpoint,
                    endpoint_key,
                    method,
                    path,
                    auth_required
                )
                if scenario:
                    scenarios.append(scenario)

        logger.info(f"Generated {len(scenarios)} status code scenarios for {endpoint_key}")
        return scenarios

    def _get_default_status_codes(self, method: str) -> List[int]:
        """Get default status codes to test based on HTTP method"""
        base_codes = [401, 403]  # Auth errors for all methods

        if method == 'GET':
            return base_codes + [200, 404]
        elif method == 'POST':
            return base_codes + [201, 400, 422, 409]
        elif method == 'PUT':
            return base_codes + [200, 404, 400, 422]
        elif method == 'PATCH':
            return base_codes + [200, 404, 400, 422]
        elif method == 'DELETE':
            return base_codes + [204, 404]
        else:
            return base_codes + [200, 404]

    def _get_scenario_generators_for_code(self, status_code: int) -> List[callable]:
        """Get scenario generator functions for a status code"""
        generators = {
            200: [self._generate_200_scenario],
            201: [self._generate_201_scenario],
            204: [self._generate_204_scenario],
            400: [
                self._generate_400_invalid_json,
                self._generate_400_wrong_type,
                self._generate_400_invalid_format
            ],
            401: [self._generate_401_no_auth, self._generate_401_invalid_token],
            403: [self._generate_403_insufficient_permissions],
            404: [self._generate_404_nonexistent_resource],
            409: [self._generate_409_duplicate],
            422: [
                self._generate_422_missing_required,
                self._generate_422_validation_failed
            ],
        }
        return generators.get(status_code, [])

    # Success scenarios (2xx)

    def _generate_200_scenario(
        self,
        endpoint: Dict[str, Any],
        endpoint_key: str,
        method: str,
        path: str,
        auth_required: bool
    ) -> Optional[StatusCodeScenario]:
        """Generate scenario for 200 OK"""
        if method not in ['GET', 'PUT', 'PATCH']:
            return None

        return StatusCodeScenario(
            status_code=200,
            scenario_type="success",
            description=f"Successful {method} request returns 200 OK",
            endpoint_key=endpoint_key,
            method=method,
            path=path,
            payload=self._generate_valid_payload(endpoint, method) if method in ['PUT', 'PATCH'] else None,
            expected_behavior="Returns valid response with 200 status"
        )

    def _generate_201_scenario(
        self,
        endpoint: Dict[str, Any],
        endpoint_key: str,
        method: str,
        path: str,
        auth_required: bool
    ) -> Optional[StatusCodeScenario]:
        """Generate scenario for 201 Created"""
        if method != 'POST':
            return None

        return StatusCodeScenario(
            status_code=201,
            scenario_type="success",
            description="Successful POST creates resource with 201",
            endpoint_key=endpoint_key,
            method=method,
            path=path,
            payload=self._generate_valid_payload(endpoint, method),
            expected_behavior="Creates resource and returns 201 with resource location"
        )

    def _generate_204_scenario(
        self,
        endpoint: Dict[str, Any],
        endpoint_key: str,
        method: str,
        path: str,
        auth_required: bool
    ) -> Optional[StatusCodeScenario]:
        """Generate scenario for 204 No Content"""
        if method != 'DELETE':
            return None

        return StatusCodeScenario(
            status_code=204,
            scenario_type="success",
            description="Successful DELETE returns 204 No Content",
            endpoint_key=endpoint_key,
            method=method,
            path=path,
            expected_behavior="Deletes resource and returns 204 with no body"
        )

    # Client error scenarios (4xx)

    def _generate_400_invalid_json(
        self,
        endpoint: Dict[str, Any],
        endpoint_key: str,
        method: str,
        path: str,
        auth_required: bool
    ) -> Optional[StatusCodeScenario]:
        """Generate scenario for 400 - Invalid JSON"""
        if method not in ['POST', 'PUT', 'PATCH']:
            return None

        # This would be handled at HTTP client level with invalid JSON string
        # For now, we'll use empty payload
        return StatusCodeScenario(
            status_code=400,
            scenario_type="client_error",
            description="Malformed request body triggers 400 Bad Request",
            endpoint_key=endpoint_key,
            method=method,
            path=path,
            payload={},  # Empty payload when data is required
            expected_behavior="Returns 400 with error message about malformed request"
        )

    def _generate_400_wrong_type(
        self,
        endpoint: Dict[str, Any],
        endpoint_key: str,
        method: str,
        path: str,
        auth_required: bool
    ) -> Optional[StatusCodeScenario]:
        """Generate scenario for 400 - Wrong data type"""
        if method not in ['POST', 'PUT', 'PATCH']:
            return None

        # Send wrong types (string where number expected, etc.)
        payload = {
            'id': 'not-a-number',  # String where ID might be expected as number
            'count': 'invalid',    # String where number expected
            'active': 'yes',       # String where boolean expected
            'price': 'free',       # String where float expected
        }

        return StatusCodeScenario(
            status_code=400,
            scenario_type="client_error",
            description="Wrong data types trigger 400 Bad Request",
            endpoint_key=endpoint_key,
            method=method,
            path=path,
            payload=payload,
            expected_behavior="Returns 400 with error about invalid data types"
        )

    def _generate_400_invalid_format(
        self,
        endpoint: Dict[str, Any],
        endpoint_key: str,
        method: str,
        path: str,
        auth_required: bool
    ) -> Optional[StatusCodeScenario]:
        """Generate scenario for 400 - Invalid format"""
        if method not in ['POST', 'PUT', 'PATCH']:
            return None

        payload = {
            'email': 'not-an-email',
            'url': 'not a url',
            'date': '32/13/2023',  # Invalid date
            'phone': 'abc-def-ghij',
            'uuid': 'not-a-uuid',
        }

        return StatusCodeScenario(
            status_code=400,
            scenario_type="client_error",
            description="Invalid formats trigger 400 Bad Request",
            endpoint_key=endpoint_key,
            method=method,
            path=path,
            payload=payload,
            expected_behavior="Returns 400 with error about invalid formats"
        )

    def _generate_401_no_auth(
        self,
        endpoint: Dict[str, Any],
        endpoint_key: str,
        method: str,
        path: str,
        auth_required: bool
    ) -> Optional[StatusCodeScenario]:
        """Generate scenario for 401 - No authentication"""
        if not auth_required:
            return None

        return StatusCodeScenario(
            status_code=401,
            scenario_type="auth_error",
            description="Request without authentication triggers 401 Unauthorized",
            endpoint_key=endpoint_key,
            method=method,
            path=path,
            headers={},  # No Authorization header
            payload=self._generate_valid_payload(endpoint, method) if method in ['POST', 'PUT', 'PATCH'] else None,
            expected_behavior="Returns 401 with error about missing authentication"
        )

    def _generate_401_invalid_token(
        self,
        endpoint: Dict[str, Any],
        endpoint_key: str,
        method: str,
        path: str,
        auth_required: bool
    ) -> Optional[StatusCodeScenario]:
        """Generate scenario for 401 - Invalid token"""
        if not auth_required:
            return None

        return StatusCodeScenario(
            status_code=401,
            scenario_type="auth_error",
            description="Request with invalid token triggers 401 Unauthorized",
            endpoint_key=endpoint_key,
            method=method,
            path=path,
            headers={'Authorization': 'Bearer invalid-token-12345'},
            payload=self._generate_valid_payload(endpoint, method) if method in ['POST', 'PUT', 'PATCH'] else None,
            expected_behavior="Returns 401 with error about invalid/expired token"
        )

    def _generate_403_insufficient_permissions(
        self,
        endpoint: Dict[str, Any],
        endpoint_key: str,
        method: str,
        path: str,
        auth_required: bool
    ) -> Optional[StatusCodeScenario]:
        """Generate scenario for 403 - Forbidden"""
        return StatusCodeScenario(
            status_code=403,
            scenario_type="permission_error",
            description="Request with insufficient permissions triggers 403 Forbidden",
            endpoint_key=endpoint_key,
            method=method,
            path=path,
            headers={'Authorization': 'Bearer user-token'},  # Regular user token
            payload=self._generate_valid_payload(endpoint, method) if method in ['POST', 'PUT', 'PATCH'] else None,
            expected_behavior="Returns 403 with error about insufficient permissions"
        )

    def _generate_404_nonexistent_resource(
        self,
        endpoint: Dict[str, Any],
        endpoint_key: str,
        method: str,
        path: str,
        auth_required: bool
    ) -> Optional[StatusCodeScenario]:
        """Generate scenario for 404 - Not Found"""
        # Only for endpoints with ID parameters
        if '{id}' not in path and '{' not in path:
            return None

        # Replace ID parameters with non-existent IDs
        path_mods = {}
        if '{id}' in path:
            path_mods['{id}'] = 'nonexistent-id-99999'
        if '{user_id}' in path:
            path_mods['{user_id}'] = 'nonexistent-user-99999'
        if '{order_id}' in path:
            path_mods['{order_id}'] = 'nonexistent-order-99999'

        return StatusCodeScenario(
            status_code=404,
            scenario_type="not_found",
            description="Request for non-existent resource triggers 404 Not Found",
            endpoint_key=endpoint_key,
            method=method,
            path=path,
            path_modifications=path_mods,
            payload=self._generate_valid_payload(endpoint, method) if method in ['PUT', 'PATCH'] else None,
            expected_behavior="Returns 404 with error about resource not found"
        )

    def _generate_409_duplicate(
        self,
        endpoint: Dict[str, Any],
        endpoint_key: str,
        method: str,
        path: str,
        auth_required: bool
    ) -> Optional[StatusCodeScenario]:
        """Generate scenario for 409 - Conflict (duplicate resource)"""
        if method != 'POST':
            return None

        # This requires creating resource first, then trying to create duplicate
        # We'll mark this scenario as requiring two-step execution
        return StatusCodeScenario(
            status_code=409,
            scenario_type="conflict",
            description="Attempting to create duplicate resource triggers 409 Conflict",
            endpoint_key=endpoint_key,
            method=method,
            path=path,
            payload=self._generate_valid_payload(endpoint, method),
            expected_behavior="Returns 409 when trying to create resource that already exists"
        )

    def _generate_422_missing_required(
        self,
        endpoint: Dict[str, Any],
        endpoint_key: str,
        method: str,
        path: str,
        auth_required: bool
    ) -> Optional[StatusCodeScenario]:
        """Generate scenario for 422 - Missing required fields"""
        if method not in ['POST', 'PUT', 'PATCH']:
            return None

        # Send payload missing required fields
        return StatusCodeScenario(
            status_code=422,
            scenario_type="validation_error",
            description="Missing required fields triggers 422 Unprocessable Entity",
            endpoint_key=endpoint_key,
            method=method,
            path=path,
            payload={},  # Empty payload (missing all required fields)
            expected_behavior="Returns 422 with error listing missing required fields"
        )

    def _generate_422_validation_failed(
        self,
        endpoint: Dict[str, Any],
        endpoint_key: str,
        method: str,
        path: str,
        auth_required: bool
    ) -> Optional[StatusCodeScenario]:
        """Generate scenario for 422 - Validation failed"""
        if method not in ['POST', 'PUT', 'PATCH']:
            return None

        # Send payload that fails validation rules
        payload = {
            'age': -5,  # Negative age
            'email': 'invalid',
            'password': '123',  # Too short
            'username': 'a',  # Too short
            'quantity': 0,  # Zero when positive required
            'price': -10.50,  # Negative price
        }

        return StatusCodeScenario(
            status_code=422,
            scenario_type="validation_error",
            description="Invalid field values trigger 422 Unprocessable Entity",
            endpoint_key=endpoint_key,
            method=method,
            path=path,
            payload=payload,
            expected_behavior="Returns 422 with validation errors for each invalid field"
        )

    def _generate_valid_payload(
        self,
        endpoint: Dict[str, Any],
        method: str
    ) -> Dict[str, Any]:
        """Generate a valid payload for the endpoint"""
        # Simple generic payload
        return {
            'name': f'Test {uuid.uuid4().hex[:8]}',
            'description': 'Test data for status code coverage',
            'active': True,
            'value': random.randint(1, 100)
        }

    def generate_all_scenarios(
        self,
        endpoints: List[Dict[str, Any]],
        documented_responses: Optional[Dict[str, List[int]]] = None
    ) -> List[StatusCodeScenario]:
        """
        Generate status code scenarios for all endpoints

        Args:
            endpoints: List of endpoint dicts
            documented_responses: Optional dict of documented status codes per endpoint

        Returns:
            List of all scenarios
        """
        all_scenarios = []

        for endpoint in endpoints:
            endpoint_key = f"{endpoint.get('method', 'GET')} {endpoint.get('path', '')}"

            # Get documented codes for this endpoint
            documented_codes = None
            if documented_responses and endpoint_key in documented_responses:
                documented_codes = documented_responses[endpoint_key]

            # Check if endpoint requires auth (simple heuristic)
            auth_required = endpoint.get('auth_required', False)

            scenarios = self.generate_scenarios_for_endpoint(
                endpoint,
                documented_codes,
                auth_required
            )

            all_scenarios.extend(scenarios)

        logger.info(f"Generated {len(all_scenarios)} total status code scenarios")
        return all_scenarios

    def get_scenarios_by_status_code(
        self,
        scenarios: List[StatusCodeScenario],
        status_code: int
    ) -> List[StatusCodeScenario]:
        """Filter scenarios by status code"""
        return [s for s in scenarios if s.status_code == status_code]

    def get_scenarios_by_type(
        self,
        scenarios: List[StatusCodeScenario],
        scenario_type: str
    ) -> List[StatusCodeScenario]:
        """Filter scenarios by type"""
        return [s for s in scenarios if s.scenario_type == scenario_type]

    def get_summary(self, scenarios: List[StatusCodeScenario]) -> Dict[str, Any]:
        """Get summary of scenarios"""
        by_code = {}
        by_type = {}

        for scenario in scenarios:
            # By status code
            code = scenario.status_code
            by_code[code] = by_code.get(code, 0) + 1

            # By type
            stype = scenario.scenario_type
            by_type[stype] = by_type.get(stype, 0) + 1

        return {
            'total_scenarios': len(scenarios),
            'by_status_code': by_code,
            'by_type': by_type,
            'unique_status_codes': len(by_code),
            'unique_types': len(by_type)
        }
