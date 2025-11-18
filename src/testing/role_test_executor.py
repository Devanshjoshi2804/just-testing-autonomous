"""
Role Test Executor
Executes role-based test scenarios and validates access control
Detects permission violations and generates security reports
"""
import httpx
import asyncio
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

try:
    from loguru import logger
except ImportError:
    class MockLogger:
        def info(self, msg, **kwargs): print(f"INFO: {msg}")
        def warning(self, msg, **kwargs): print(f"WARN: {msg}")
        def error(self, msg, **kwargs): print(f"ERROR: {msg}")
        def debug(self, msg, **kwargs): pass
        def success(self, msg, **kwargs): print(f"SUCCESS: {msg}")
    logger = MockLogger()

from src.testing.role_based_scenario_generator import (
    RoleTestScenario,
    UserRole,
    AccessLevel
)


@dataclass
class RoleTestResult:
    """Result of executing a role test scenario"""
    scenario: RoleTestScenario
    actual_status_code: int
    expected_status_codes: List[int]
    access_correct: bool
    response_body: Dict[str, Any]
    response_time_ms: float
    violation_type: Optional[str] = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PermissionViolation:
    """Represents a permission violation"""
    endpoint_key: str
    role: UserRole
    expected_access: AccessLevel
    actual_status: int
    violation_type: str
    severity: str
    description: str


class RoleTestExecutor:
    """
    Executes role-based test scenarios and validates RBAC

    Detects violations:
    - Privilege escalation: User/Guest accessing admin-only endpoints
    - Insufficient protection: Unauthenticated accessing protected endpoints
    - Over-restriction: Authorized users getting 403 when should succeed
    """

    def __init__(
        self,
        base_url: str,
        default_headers: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ):
        """
        Initialize executor

        Args:
            base_url: API base URL
            default_headers: Default headers
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.default_headers = default_headers or {}
        self.timeout = timeout
        self.client = None

        # Results tracking
        self.test_results: List[RoleTestResult] = []
        self.violations: List[PermissionViolation] = []

    async def execute_scenario(
        self,
        scenario: RoleTestScenario
    ) -> RoleTestResult:
        """
        Execute a single role test scenario

        Args:
            scenario: RoleTestScenario to execute

        Returns:
            RoleTestResult with execution details
        """
        start_time = time.time()

        # Build URL
        url = f"{self.base_url}{scenario.path}"

        # Build headers
        headers = self.default_headers.copy()

        # Add authentication if role has token
        if scenario.auth_token:
            headers['Authorization'] = f'Bearer {scenario.auth_token}'

        if scenario.method in ['POST', 'PUT', 'PATCH'] and 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json'

        # Execute request
        try:
            logger.debug(
                f"Testing {scenario.role.value} on {scenario.method} {scenario.path} "
                f"(expect {scenario.access_level.value})"
            )

            response = await self._make_request(
                method=scenario.method,
                url=url,
                headers=headers,
                payload=scenario.payload
            )

            actual_status = response.status_code
            response_body = self._parse_response(response)
            error_msg = None

        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            actual_status = 0
            response_body = {}
            error_msg = str(e)

        # Calculate response time
        elapsed_ms = (time.time() - start_time) * 1000

        # Check if access control is correct
        access_correct = actual_status in scenario.expected_status_codes
        violation_type = None

        if not access_correct:
            violation_type = self._classify_violation(
                scenario.access_level,
                scenario.expected_status_codes,
                actual_status
            )

            # Log violation
            if violation_type:
                logger.warning(
                    f"⚠️  VIOLATION: {scenario.role.value} on {scenario.endpoint_key}: "
                    f"Expected {scenario.expected_status_codes}, got {actual_status} "
                    f"({violation_type})"
                )

                self._record_violation(scenario, actual_status, violation_type)
            else:
                logger.warning(
                    f"⚠️  Unexpected status: {scenario.role.value} on {scenario.endpoint_key}: "
                    f"Expected {scenario.expected_status_codes}, got {actual_status}"
                )
        else:
            logger.success(
                f"✅ {scenario.role.value} on {scenario.endpoint_key}: "
                f"Got expected {actual_status}"
            )

        result = RoleTestResult(
            scenario=scenario,
            actual_status_code=actual_status,
            expected_status_codes=scenario.expected_status_codes,
            access_correct=access_correct,
            response_body=response_body,
            response_time_ms=elapsed_ms,
            violation_type=violation_type,
            error=error_msg
        )

        self.test_results.append(result)
        return result

    async def _make_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        payload: Optional[Dict[str, Any]]
    ) -> httpx.Response:
        """Make HTTP request"""
        if method == 'GET':
            return await self.client.get(url, headers=headers)
        elif method == 'POST':
            return await self.client.post(url, json=payload, headers=headers)
        elif method == 'PUT':
            return await self.client.put(url, json=payload, headers=headers)
        elif method == 'PATCH':
            return await self.client.patch(url, json=payload, headers=headers)
        elif method == 'DELETE':
            return await self.client.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

    def _parse_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Parse response body"""
        try:
            return response.json()
        except:
            return {"_raw": response.text[:500]}

    def _classify_violation(
        self,
        expected_access: AccessLevel,
        expected_codes: List[int],
        actual_code: int
    ) -> Optional[str]:
        """
        Classify the type of permission violation

        Returns:
            Violation type string or None
        """
        if expected_access == AccessLevel.ALLOWED:
            if actual_code == 403:
                return "over_restriction"  # User should have access but got 403
            elif actual_code == 401:
                return "auth_required"     # Authentication required
            elif actual_code >= 400:
                return "unexpected_error"  # Some other error
            else:
                return None  # Success (but might be wrong success code)

        elif expected_access == AccessLevel.FORBIDDEN:
            if 200 <= actual_code < 300:
                return "privilege_escalation"  # User accessed forbidden resource!
            elif actual_code == 401:
                return "auth_instead_of_forbid"  # Should be 403 not 401
            else:
                return None  # Correctly rejected

        elif expected_access == AccessLevel.UNAUTHORIZED:
            if 200 <= actual_code < 300:
                return "missing_authentication"  # Unauthenticated access succeeded!
            elif actual_code == 403:
                return "forbid_instead_of_unauth"  # Should be 401 not 403
            else:
                return None  # Correctly rejected

        return "unknown"

    def _record_violation(
        self,
        scenario: RoleTestScenario,
        actual_status: int,
        violation_type: str
    ):
        """Record a permission violation"""
        # Determine severity
        if violation_type in ['privilege_escalation', 'missing_authentication']:
            severity = 'CRITICAL'
        elif violation_type in ['over_restriction', 'auth_instead_of_forbid']:
            severity = 'MEDIUM'
        else:
            severity = 'LOW'

        description = self._describe_violation(scenario, actual_status, violation_type)

        violation = PermissionViolation(
            endpoint_key=scenario.endpoint_key,
            role=scenario.role,
            expected_access=scenario.access_level,
            actual_status=actual_status,
            violation_type=violation_type,
            severity=severity,
            description=description
        )

        self.violations.append(violation)

    def _describe_violation(
        self,
        scenario: RoleTestScenario,
        actual_status: int,
        violation_type: str
    ) -> str:
        """Generate human-readable violation description"""
        role = scenario.role.value
        endpoint = scenario.endpoint_key

        descriptions = {
            'privilege_escalation': (
                f"{role.capitalize()} gained unauthorized access to {endpoint} "
                f"(got {actual_status} instead of 403)"
            ),
            'missing_authentication': (
                f"Unauthenticated access to {endpoint} succeeded "
                f"(got {actual_status} instead of 401)"
            ),
            'over_restriction': (
                f"{role.capitalize()} was denied access to {endpoint} "
                f"(got 403 but should succeed)"
            ),
            'auth_required': (
                f"{role.capitalize()} needs authentication for {endpoint} "
                f"(got 401)"
            ),
        }

        return descriptions.get(
            violation_type,
            f"Permission issue for {role} on {endpoint}: expected {scenario.expected_status_codes}, got {actual_status}"
        )

    async def execute_all_scenarios(
        self,
        scenarios: List[RoleTestScenario]
    ) -> List[RoleTestResult]:
        """
        Execute all role test scenarios

        Args:
            scenarios: List of scenarios to execute

        Returns:
            List of test results
        """
        logger.info(f"🧪 Executing {len(scenarios)} role test scenarios...")

        results = []

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            self.client = client

            for i, scenario in enumerate(scenarios, 1):
                logger.debug(f"\nScenario {i}/{len(scenarios)}")
                result = await self.execute_scenario(scenario)
                results.append(result)

                # Small delay between requests
                await asyncio.sleep(0.1)

        # Calculate stats
        correct = sum(1 for r in results if r.access_correct)
        total = len(results)

        logger.info(f"\n✅ Executed {total} scenarios")
        logger.info(f"   Correct access control: {correct}/{total} ({correct/total*100:.1f}%)")

        if self.violations:
            logger.warning(f"   ⚠️  {len(self.violations)} permission violations detected")

        return results

    def get_violations_by_severity(
        self,
        severity: str
    ) -> List[PermissionViolation]:
        """Get violations filtered by severity"""
        return [v for v in self.violations if v.severity == severity]

    def get_violations_by_type(
        self,
        violation_type: str
    ) -> List[PermissionViolation]:
        """Get violations filtered by type"""
        return [v for v in self.violations if v.violation_type == violation_type]

    def generate_security_report(self) -> str:
        """
        Generate security report for permission violations

        Returns:
            Formatted security report
        """
        lines = []
        lines.append("=" * 80)
        lines.append("ROLE-BASED ACCESS CONTROL (RBAC) SECURITY REPORT")
        lines.append("=" * 80)
        lines.append("")

        # Overall stats
        total_tests = len(self.test_results)
        correct = sum(1 for r in self.test_results if r.access_correct)
        total_violations = len(self.violations)

        lines.append(f"Total Tests: {total_tests}")
        lines.append(f"Correct Access Control: {correct}/{total_tests} ({correct/total_tests*100:.1f}%)")
        lines.append(f"Permission Violations: {total_violations}")
        lines.append("")

        if not self.violations:
            lines.append("✅ No permission violations detected!")
            lines.append("")
            return "\n".join(lines)

        # Violations by severity
        critical = self.get_violations_by_severity('CRITICAL')
        medium = self.get_violations_by_severity('MEDIUM')
        low = self.get_violations_by_severity('LOW')

        lines.append("VIOLATIONS BY SEVERITY:")
        lines.append(f"   🔴 CRITICAL: {len(critical)} (privilege escalation, missing auth)")
        lines.append(f"   🟠 MEDIUM: {len(medium)} (incorrect error codes)")
        lines.append(f"   🟡 LOW: {len(low)} (minor issues)")
        lines.append("")

        # Critical violations detail
        if critical:
            lines.append("=" * 80)
            lines.append("🔴 CRITICAL VIOLATIONS (IMMEDIATE ACTION REQUIRED)")
            lines.append("=" * 80)
            lines.append("")

            for v in critical:
                lines.append(f"Endpoint: {v.endpoint_key}")
                lines.append(f"Role: {v.role.value}")
                lines.append(f"Type: {v.violation_type}")
                lines.append(f"Issue: {v.description}")
                lines.append("")

        # Medium violations detail
        if medium:
            lines.append("=" * 80)
            lines.append("🟠 MEDIUM VIOLATIONS")
            lines.append("=" * 80)
            lines.append("")

            for v in medium:
                lines.append(f"Endpoint: {v.endpoint_key}")
                lines.append(f"Role: {v.role.value}")
                lines.append(f"Type: {v.violation_type}")
                lines.append(f"Issue: {v.description}")
                lines.append("")

        # Summary by violation type
        lines.append("=" * 80)
        lines.append("VIOLATIONS BY TYPE")
        lines.append("=" * 80)
        lines.append("")

        violation_types = {}
        for v in self.violations:
            violation_types[v.violation_type] = violation_types.get(v.violation_type, 0) + 1

        for vtype, count in sorted(violation_types.items(), key=lambda x: -x[1]):
            lines.append(f"   {vtype}: {count}")

        lines.append("")

        return "\n".join(lines)

    def get_role_summary(self) -> Dict[str, Any]:
        """
        Get summary of role test results

        Returns:
            Summary dict with statistics
        """
        by_role = {}
        for result in self.test_results:
            role = result.scenario.role.value
            if role not in by_role:
                by_role[role] = {'total': 0, 'correct': 0, 'violations': 0}

            by_role[role]['total'] += 1
            if result.access_correct:
                by_role[role]['correct'] += 1
            if result.violation_type:
                by_role[role]['violations'] += 1

        # Calculate percentages
        for role, stats in by_role.items():
            stats['correctness_rate'] = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0

        return {
            'total_tests': len(self.test_results),
            'total_violations': len(self.violations),
            'correctness_rate': (sum(1 for r in self.test_results if r.access_correct) / len(self.test_results) * 100) if self.test_results else 0,
            'by_role': by_role,
            'violations_by_severity': {
                'critical': len(self.get_violations_by_severity('CRITICAL')),
                'medium': len(self.get_violations_by_severity('MEDIUM')),
                'low': len(self.get_violations_by_severity('LOW'))
            }
        }
