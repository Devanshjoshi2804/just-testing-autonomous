"""
Error Response Validator
Validates error response quality and consistency
Ensures error messages are helpful and well-structured
"""
import httpx
import asyncio
import time
import re
from typing import Dict, Any, List, Optional, Set
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

from src.testing.error_scenario_generator import ErrorScenario, ErrorCategory


@dataclass
class ErrorQualityIssue:
    """Represents an issue with error response quality"""
    issue_type: str
    severity: str
    description: str
    field: Optional[str] = None
    expected: Optional[str] = None
    actual: Optional[str] = None


@dataclass
class ErrorTestResult:
    """Result of testing an error scenario"""
    scenario: ErrorScenario
    actual_status_code: int
    response_body: Dict[str, Any]
    status_code_matches: bool
    has_required_fields: bool
    message_quality_score: float  # 0.0 to 1.0
    quality_issues: List[ErrorQualityIssue]
    response_time_ms: float
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ErrorResponseValidator:
    """
    Validates error response quality

    Checks:
    1. Status code matches expectation
    2. Required fields are present
    3. Error message is helpful (not generic)
    4. Error format is consistent
    5. Error details provide context
    6. Field names are included for validation errors
    7. Constraints are specified for range errors
    """

    # Generic error messages (should be avoided)
    GENERIC_MESSAGES = [
        "an error occurred",
        "something went wrong",
        "error",
        "bad request",
        "invalid request",
        "validation error",
        "not found",
        "forbidden",
        "unauthorized"
    ]

    def __init__(
        self,
        base_url: str,
        default_headers: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ):
        """
        Initialize validator

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
        self.test_results: List[ErrorTestResult] = []

    async def validate_error_scenario(
        self,
        scenario: ErrorScenario
    ) -> ErrorTestResult:
        """
        Execute and validate an error scenario

        Args:
            scenario: ErrorScenario to test

        Returns:
            ErrorTestResult with validation details
        """
        start_time = time.time()

        # Build URL
        path = scenario.path
        if scenario.path_modifications:
            for placeholder, value in scenario.path_modifications.items():
                path = path.replace(placeholder, value)

        url = f"{self.base_url}{path}"

        # Build headers
        headers = self.default_headers.copy()
        if scenario.trigger_headers:
            headers.update(scenario.trigger_headers)

        if scenario.method in ['POST', 'PUT', 'PATCH'] and 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json'

        # Execute request
        try:
            logger.debug(
                f"Testing error: {scenario.error_condition.condition_name} "
                f"on {scenario.method} {path}"
            )

            response = await self._make_request(
                method=scenario.method,
                url=url,
                headers=headers,
                payload=scenario.trigger_payload
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

        # Validate response
        status_matches = actual_status == scenario.error_condition.expected_status_code
        has_required_fields = self._check_required_fields(
            response_body,
            scenario.error_condition.expected_fields
        )

        quality_issues = []
        message_score = 0.0

        if status_matches and has_required_fields:
            # Check error message quality
            message_score, quality_issues = self._assess_error_quality(
                response_body,
                scenario.error_condition
            )

        if status_matches and has_required_fields and message_score >= 0.7:
            logger.success(
                f"✅ {scenario.error_condition.condition_name} on {scenario.endpoint_key}: "
                f"Quality score {message_score:.0%}"
            )
        else:
            logger.warning(
                f"⚠️  {scenario.error_condition.condition_name} on {scenario.endpoint_key}: "
                f"Status {actual_status}, Quality {message_score:.0%}, Issues: {len(quality_issues)}"
            )

        result = ErrorTestResult(
            scenario=scenario,
            actual_status_code=actual_status,
            response_body=response_body,
            status_code_matches=status_matches,
            has_required_fields=has_required_fields,
            message_quality_score=message_score,
            quality_issues=quality_issues,
            response_time_ms=elapsed_ms,
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

    def _check_required_fields(
        self,
        response_body: Dict[str, Any],
        required_fields: List[str]
    ) -> bool:
        """Check if response has all required fields"""
        for field in required_fields:
            if field not in response_body:
                return False
        return True

    def _assess_error_quality(
        self,
        response_body: Dict[str, Any],
        error_condition
    ) -> tuple[float, List[ErrorQualityIssue]]:
        """
        Assess quality of error response

        Returns:
            (quality_score, list of issues)
        """
        issues = []
        score = 1.0

        # Check 1: Message is not generic
        message = response_body.get('message', '')
        if self._is_generic_message(message):
            issues.append(ErrorQualityIssue(
                issue_type='generic_message',
                severity='MEDIUM',
                description='Error message is too generic',
                field='message',
                actual=message,
                expected='Specific, helpful error message'
            ))
            score -= 0.3

        # Check 2: Message is not empty
        if not message or len(message.strip()) < 5:
            issues.append(ErrorQualityIssue(
                issue_type='empty_message',
                severity='HIGH',
                description='Error message is empty or too short',
                field='message',
                actual=message
            ))
            score -= 0.4

        # Check 3: For validation errors, field name should be mentioned
        if error_condition.category == ErrorCategory.VALIDATION:
            if 'field' in response_body:
                field_name = response_body.get('field', '')
                if not field_name:
                    issues.append(ErrorQualityIssue(
                        issue_type='missing_field_name',
                        severity='MEDIUM',
                        description='Validation error missing field name',
                        field='field'
                    ))
                    score -= 0.2
            else:
                issues.append(ErrorQualityIssue(
                    issue_type='missing_field_field',
                    severity='MEDIUM',
                    description='Validation error missing "field" attribute',
                    expected='field'
                ))
                score -= 0.2

        # Check 4: Error details should be present
        if 'details' not in response_body:
            issues.append(ErrorQualityIssue(
                issue_type='missing_details',
                severity='LOW',
                description='Error response missing details field',
                expected='details'
            ))
            score -= 0.1

        # Check 5: For range errors, constraints should be specified
        if 'range' in error_condition.condition_name.lower():
            if 'min' not in response_body and 'max' not in response_body:
                issues.append(ErrorQualityIssue(
                    issue_type='missing_constraints',
                    severity='MEDIUM',
                    description='Range validation error missing min/max constraints',
                    expected='min, max'
                ))
                score -= 0.2

        # Check 6: Message should be properly capitalized
        if message and not message[0].isupper():
            issues.append(ErrorQualityIssue(
                issue_type='poor_formatting',
                severity='LOW',
                description='Error message not properly capitalized',
                field='message'
            ))
            score -= 0.05

        # Ensure score is between 0 and 1
        score = max(0.0, min(1.0, score))

        return score, issues

    def _is_generic_message(self, message: str) -> bool:
        """Check if message is generic"""
        message_lower = message.lower().strip()

        # Exact matches
        if message_lower in self.GENERIC_MESSAGES:
            return True

        # Very short messages are likely generic
        if len(message_lower) < 10:
            return True

        return False

    async def validate_all_scenarios(
        self,
        scenarios: List[ErrorScenario]
    ) -> List[ErrorTestResult]:
        """
        Validate all error scenarios

        Args:
            scenarios: List of scenarios to test

        Returns:
            List of test results
        """
        logger.info(f"🧪 Validating {len(scenarios)} error scenarios...")

        results = []

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            self.client = client

            for i, scenario in enumerate(scenarios, 1):
                logger.debug(f"\nScenario {i}/{len(scenarios)}")
                result = await self.validate_error_scenario(scenario)
                results.append(result)

                # Small delay between requests
                await asyncio.sleep(0.1)

        # Calculate stats
        high_quality = sum(1 for r in results if r.message_quality_score >= 0.7)
        total = len(results)

        logger.info(f"\n✅ Validated {total} error scenarios")
        logger.info(f"   High quality: {high_quality}/{total} ({high_quality/total*100:.1f}%)")

        return results

    def generate_quality_report(self) -> str:
        """
        Generate error quality report

        Returns:
            Formatted quality report
        """
        lines = []
        lines.append("=" * 80)
        lines.append("ERROR RESPONSE QUALITY REPORT")
        lines.append("=" * 80)
        lines.append("")

        if not self.test_results:
            lines.append("No error scenarios tested.")
            return "\n".join(lines)

        # Overall stats
        total = len(self.test_results)
        high_quality = sum(1 for r in self.test_results if r.message_quality_score >= 0.7)
        medium_quality = sum(1 for r in self.test_results if 0.4 <= r.message_quality_score < 0.7)
        low_quality = sum(1 for r in self.test_results if r.message_quality_score < 0.4)

        avg_score = sum(r.message_quality_score for r in self.test_results) / total

        lines.append(f"Total Error Scenarios: {total}")
        lines.append(f"Average Quality Score: {avg_score:.0%}")
        lines.append("")
        lines.append(f"Quality Distribution:")
        lines.append(f"   High Quality (≥70%): {high_quality} ({high_quality/total*100:.1f}%)")
        lines.append(f"   Medium Quality (40-70%): {medium_quality} ({medium_quality/total*100:.1f}%)")
        lines.append(f"   Low Quality (<40%): {low_quality} ({low_quality/total*100:.1f}%)")
        lines.append("")

        # Common issues
        all_issues = []
        for result in self.test_results:
            all_issues.extend(result.quality_issues)

        if all_issues:
            issue_counts = {}
            for issue in all_issues:
                issue_counts[issue.issue_type] = issue_counts.get(issue.issue_type, 0) + 1

            lines.append("=" * 80)
            lines.append("COMMON QUALITY ISSUES")
            lines.append("=" * 80)
            lines.append("")

            for issue_type, count in sorted(issue_counts.items(), key=lambda x: -x[1]):
                lines.append(f"   {issue_type}: {count} occurrences")

        # Low quality errors detail
        low_quality_results = [r for r in self.test_results if r.message_quality_score < 0.4]

        if low_quality_results:
            lines.append("")
            lines.append("=" * 80)
            lines.append("LOW QUALITY ERROR RESPONSES (NEED IMPROVEMENT)")
            lines.append("=" * 80)
            lines.append("")

            for result in low_quality_results[:10]:  # Show first 10
                lines.append(f"Endpoint: {result.scenario.endpoint_key}")
                lines.append(f"Error: {result.scenario.error_condition.condition_name}")
                lines.append(f"Quality Score: {result.message_quality_score:.0%}")
                lines.append(f"Issues:")
                for issue in result.quality_issues:
                    lines.append(f"   - {issue.description}")
                lines.append("")

        return "\n".join(lines)

    def get_quality_summary(self) -> Dict[str, Any]:
        """Get summary of error quality"""
        if not self.test_results:
            return {'error': 'No tests run'}

        total = len(self.test_results)
        avg_score = sum(r.message_quality_score for r in self.test_results) / total

        high_quality = sum(1 for r in self.test_results if r.message_quality_score >= 0.7)
        medium_quality = sum(1 for r in self.test_results if 0.4 <= r.message_quality_score < 0.7)
        low_quality = sum(1 for r in self.test_results if r.message_quality_score < 0.4)

        # Count issues
        all_issues = []
        for result in self.test_results:
            all_issues.extend(result.quality_issues)

        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue.issue_type] = issue_counts.get(issue.issue_type, 0) + 1

        return {
            'total_scenarios': total,
            'average_quality_score': avg_score,
            'high_quality_count': high_quality,
            'medium_quality_count': medium_quality,
            'low_quality_count': low_quality,
            'total_issues': len(all_issues),
            'issue_breakdown': issue_counts
        }
