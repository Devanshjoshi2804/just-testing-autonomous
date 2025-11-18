"""
Mutation Test Generator
Generates security-focused mutation tests based on OWASP Top 10
"""
import copy
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

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

from src.testing.security_patterns import SecurityPatterns, SecurityPattern, VULNERABILITY_INDICATORS


@dataclass
class MutationTest:
    """Mutation test case"""
    name: str
    type: str  # 'security_injection', 'security_overflow', etc.
    source: str  # 'mutation_testing'
    confidence: str  # 'HIGH' for known patterns
    security_pattern: str  # Name of security pattern
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    cwe_id: str  # CWE identifier
    target_parameter: str  # Which parameter is being mutated
    payload: Dict[str, Any]  # The mutated payload
    expected_behavior: str  # What should happen
    expected_status: int  # Expected HTTP status
    vulnerability_indicators: List[str]  # Strings to look for in response


class MutationTestGenerator:
    """
    Generates security mutation tests for API endpoints

    Uses OWASP Top 10 patterns to systematically test for vulnerabilities
    """

    def __init__(self, max_tests_per_pattern: int = 3):
        """
        Initialize mutation test generator

        Args:
            max_tests_per_pattern: Maximum number of tests per security pattern
        """
        self.max_tests_per_pattern = max_tests_per_pattern
        self.security_patterns = SecurityPatterns()
        logger.info("MutationTestGenerator initialized")

    def generate_mutation_tests(
        self,
        endpoint: Dict[str, Any],
        base_payload: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate mutation tests for an endpoint

        Args:
            endpoint: Endpoint information (path, method, parameters)
            base_payload: Optional base payload to mutate

        Returns:
            List of mutation test cases
        """
        tests = []
        method = endpoint.get('method', 'GET').upper()
        path = endpoint.get('path', '')
        parameters = endpoint.get('parameters', [])

        logger.info(f"Generating mutation tests for {method} {path}")

        # Only generate mutation tests for methods that accept payloads
        if method not in ['POST', 'PUT', 'PATCH']:
            logger.debug(f"Skipping mutation tests for {method} (read-only method)")
            return tests

        # If no base payload provided, create one from parameters
        if not base_payload:
            base_payload = self._create_base_payload(parameters)

        # Generate mutation tests for each parameter
        for param in parameters:
            param_name = param.get('name', '')
            param_type = param.get('type', 'string')
            required = param.get('required', False)

            # Get relevant security patterns for this parameter
            relevant_patterns = self.security_patterns.get_patterns_for_parameter_type(
                param_type,
                param_name
            )

            logger.debug(
                f"Parameter '{param_name}' ({param_type}): "
                f"{len(relevant_patterns)} security patterns applicable"
            )

            # Generate tests for each relevant pattern
            for pattern in relevant_patterns:
                param_tests = self._generate_tests_for_parameter(
                    param_name,
                    param_type,
                    pattern,
                    base_payload,
                    endpoint
                )
                tests.extend(param_tests)

        logger.info(f"Generated {len(tests)} mutation tests for {method} {path}")
        return tests

    def _create_base_payload(self, parameters: List[Dict]) -> Dict[str, Any]:
        """Create a base payload from endpoint parameters"""
        payload = {}

        for param in parameters:
            name = param.get('name', '')
            param_type = param.get('type', 'string')
            required = param.get('required', False)

            # Only include required parameters in base payload
            if required:
                # Generate benign default value
                if param_type in ['integer', 'int', 'number']:
                    payload[name] = 1
                elif param_type in ['boolean', 'bool']:
                    payload[name] = True
                elif param_type in ['array', 'list']:
                    payload[name] = []
                elif param_type in ['object', 'dict']:
                    payload[name] = {}
                else:  # string, email, url, etc.
                    payload[name] = f"test_{name}"

        return payload

    def _generate_tests_for_parameter(
        self,
        param_name: str,
        param_type: str,
        pattern: SecurityPattern,
        base_payload: Dict[str, Any],
        endpoint: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate mutation tests for a specific parameter using a security pattern

        Args:
            param_name: Name of parameter to mutate
            param_type: Type of parameter
            pattern: Security pattern to use
            base_payload: Base payload to mutate
            endpoint: Endpoint information

        Returns:
            List of mutation test cases
        """
        tests = []
        method = endpoint.get('method', 'POST')
        path = endpoint.get('path', '')

        # Limit number of payloads to test
        payloads_to_test = pattern.payloads[:self.max_tests_per_pattern]

        for i, malicious_payload in enumerate(payloads_to_test):
            # Create mutated payload
            mutated = copy.deepcopy(base_payload)

            # Apply mutation based on parameter type
            if param_type in ['object', 'json', 'dict']:
                # For object types, try to parse JSON payloads
                try:
                    mutated[param_name] = json.loads(malicious_payload)
                except (json.JSONDecodeError, TypeError):
                    mutated[param_name] = malicious_payload
            elif param_type in ['integer', 'int', 'number']:
                # For numeric types, try to convert
                try:
                    mutated[param_name] = int(malicious_payload)
                except (ValueError, TypeError):
                    mutated[param_name] = malicious_payload
            else:
                # For string types, use as-is
                mutated[param_name] = malicious_payload

            # Determine expected behavior
            expected_status, expected_behavior = self._get_expected_behavior(pattern)

            # Get vulnerability indicators for detection
            indicators = self._get_vulnerability_indicators(pattern)

            # Create test case
            test = {
                'name': f"Security: {pattern.name} in '{param_name}' #{i+1}",
                'type': 'security',
                'source': 'mutation_testing',
                'confidence': 'HIGH',  # These are known attack patterns
                'security_pattern': pattern.name,
                'severity': pattern.severity,
                'cwe_id': pattern.cwe_id,
                'category': pattern.category,
                'target_parameter': param_name,
                'payload': mutated,
                'expected_status': expected_status,
                'expected_behavior': expected_behavior,
                'vulnerability_indicators': indicators,
                'description': f"Test {pattern.name} vulnerability in {param_name} parameter",
                'attack_payload': malicious_payload,  # Store original malicious payload
            }

            tests.append(test)

        return tests

    def _get_expected_behavior(self, pattern: SecurityPattern) -> tuple:
        """
        Get expected behavior for a security test

        Args:
            pattern: Security pattern being tested

        Returns:
            Tuple of (expected_status_code, behavior_description)
        """
        # Secure API should reject malicious input
        # Expected status codes for secure systems:
        # - 400 Bad Request (input validation failed)
        # - 403 Forbidden (security policy violation)
        # - 422 Unprocessable Entity (semantic validation failed)

        if pattern.severity == "CRITICAL":
            return (
                400,
                "Should reject with 400/403/422. If 200/201, potential vulnerability!"
            )
        elif pattern.severity == "HIGH":
            return (
                400,
                "Should reject with 400/403/422. If 200/201, potential vulnerability!"
            )
        else:
            return (
                400,
                "Should reject or sanitize input. Check response carefully."
            )

    def _get_vulnerability_indicators(self, pattern: SecurityPattern) -> List[str]:
        """
        Get vulnerability indicators for a security pattern

        Args:
            pattern: Security pattern

        Returns:
            List of strings to look for in response that indicate vulnerability
        """
        category = pattern.category.lower()

        # Get indicators from VULNERABILITY_INDICATORS dict
        for vuln_type, indicators in VULNERABILITY_INDICATORS.items():
            if vuln_type in pattern.name.lower():
                return indicators

        # Default indicators for injection attacks
        if 'injection' in category:
            return [
                "error",
                "exception",
                "stack trace",
                "warning",
                "syntax",
            ]

        return []

    def get_mutation_summary(self, endpoint: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get summary of mutation tests that would be generated

        Args:
            endpoint: Endpoint information

        Returns:
            Summary dict with test counts by severity and pattern
        """
        method = endpoint.get('method', 'GET').upper()
        parameters = endpoint.get('parameters', [])

        if method not in ['POST', 'PUT', 'PATCH']:
            return {
                'total_tests': 0,
                'reason': f'Mutation testing not applicable for {method} method',
                'by_severity': {},
                'by_pattern': {},
            }

        summary = {
            'total_tests': 0,
            'by_severity': {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0},
            'by_pattern': {},
            'by_parameter': {},
        }

        for param in parameters:
            param_name = param.get('name', '')
            param_type = param.get('type', 'string')

            patterns = self.security_patterns.get_patterns_for_parameter_type(
                param_type,
                param_name
            )

            param_test_count = 0
            for pattern in patterns:
                test_count = min(len(pattern.payloads), self.max_tests_per_pattern)

                summary['total_tests'] += test_count
                summary['by_severity'][pattern.severity] += test_count

                if pattern.name not in summary['by_pattern']:
                    summary['by_pattern'][pattern.name] = 0
                summary['by_pattern'][pattern.name] += test_count

                param_test_count += test_count

            summary['by_parameter'][param_name] = param_test_count

        return summary

    def analyze_mutation_test_result(
        self,
        test: Dict[str, Any],
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze mutation test result to detect vulnerabilities

        Args:
            test: The mutation test case
            response: API response

        Returns:
            Analysis dict with vulnerability assessment
        """
        status_code = response.get('status_code', 0)
        response_body = str(response.get('body', ''))
        response_headers = response.get('headers', {})

        expected_status = test.get('expected_status', 400)
        indicators = test.get('vulnerability_indicators', [])
        severity = test.get('severity', 'MEDIUM')
        pattern_name = test.get('security_pattern', 'Unknown')

        # Check if API accepted malicious input (BAD!)
        if status_code in [200, 201, 202, 204]:
            return {
                'vulnerable': True,
                'severity': severity,
                'pattern': pattern_name,
                'cwe_id': test.get('cwe_id'),
                'reason': f"API accepted malicious input (status {status_code})",
                'recommendation': f"API should reject {pattern_name} attempts with 400/403/422",
                'evidence': {
                    'status_code': status_code,
                    'expected_status': expected_status,
                },
                'risk_level': 'HIGH' if severity == 'CRITICAL' else 'MEDIUM',
            }

        # Check for vulnerability indicators in response
        found_indicators = []
        for indicator in indicators:
            if indicator.lower() in response_body.lower():
                found_indicators.append(indicator)

        if found_indicators:
            return {
                'vulnerable': True,
                'severity': severity,
                'pattern': pattern_name,
                'cwe_id': test.get('cwe_id'),
                'reason': f"Vulnerability indicators found in response: {', '.join(found_indicators)}",
                'recommendation': f"API should not expose internal details in error messages",
                'evidence': {
                    'indicators_found': found_indicators,
                    'response_snippet': response_body[:500],
                },
                'risk_level': 'MEDIUM',
            }

        # Check for error disclosure
        if any(word in response_body.lower() for word in ['stack trace', 'traceback', 'exception']):
            return {
                'vulnerable': True,
                'severity': 'MEDIUM',
                'pattern': 'Error Disclosure',
                'cwe_id': 'CWE-209',
                'reason': 'API disclosed internal error details',
                'recommendation': 'Use generic error messages for security inputs',
                'evidence': {
                    'response_snippet': response_body[:500],
                },
                'risk_level': 'LOW',
            }

        # API properly rejected malicious input
        if status_code in [400, 403, 422]:
            return {
                'vulnerable': False,
                'status': 'SECURE',
                'pattern': pattern_name,
                'reason': f'API properly rejected malicious input with status {status_code}',
                'recommendation': 'Keep input validation strict',
            }

        # Unexpected status code
        return {
            'vulnerable': False,
            'status': 'UNKNOWN',
            'pattern': pattern_name,
            'reason': f'Unexpected status code {status_code}, manual review recommended',
            'recommendation': f'Review why {pattern_name} resulted in status {status_code}',
        }
