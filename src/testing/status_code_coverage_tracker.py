"""
Status Code Coverage Tracker
Tracks which HTTP status codes have been tested vs documented
Measures error handling coverage
"""
import httpx
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
import time

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

from src.testing.status_code_scenario_generator import StatusCodeScenario


@dataclass
class StatusCodeTestResult:
    """Result of executing a status code scenario"""
    scenario: StatusCodeScenario
    actual_status_code: int
    expected_status_code: int
    matched: bool
    response_body: Dict[str, Any]
    response_time_ms: float
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class EndpointCoverage:
    """Coverage tracking for a single endpoint"""
    endpoint_key: str
    documented_codes: Set[int]
    tested_codes: Set[int]
    missing_codes: Set[int] = field(default_factory=set)
    coverage_percentage: float = 0.0


class StatusCodeCoverageTracker:
    """
    Executes status code scenarios and tracks coverage

    Tracks:
    - Which status codes have been tested
    - Which status codes are documented but not tested
    - Which status codes were returned but not documented
    - Overall coverage percentage
    """

    def __init__(
        self,
        base_url: str,
        default_headers: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ):
        """
        Initialize tracker

        Args:
            base_url: API base URL
            default_headers: Default headers for requests
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.default_headers = default_headers or {}
        self.timeout = timeout
        self.client = None

        # Coverage tracking
        self.documented_codes: Dict[str, Set[int]] = {}  # endpoint_key -> set of codes
        self.tested_codes: Dict[str, Set[int]] = {}  # endpoint_key -> set of codes
        self.test_results: List[StatusCodeTestResult] = []

    async def execute_scenario(
        self,
        scenario: StatusCodeScenario
    ) -> StatusCodeTestResult:
        """
        Execute a single status code scenario

        Args:
            scenario: StatusCodeScenario to execute

        Returns:
            StatusCodeTestResult with execution details
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
        headers.update(scenario.headers)

        if scenario.method in ['POST', 'PUT', 'PATCH'] and 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json'

        # Execute request
        try:
            logger.debug(
                f"Executing: {scenario.method} {url} "
                f"(expecting {scenario.status_code})"
            )

            response = await self._make_request(
                method=scenario.method,
                url=url,
                headers=headers,
                payload=scenario.payload
            )

            actual_status = response.status_code
            response_body = self._parse_response(response)
            matched = actual_status == scenario.status_code
            error = None

            if matched:
                logger.success(
                    f"✅ {scenario.endpoint_key}: Got expected {actual_status}"
                )
            else:
                logger.warning(
                    f"⚠️  {scenario.endpoint_key}: Expected {scenario.status_code}, "
                    f"got {actual_status}"
                )

        except Exception as e:
            logger.error(f"❌ Request failed: {str(e)}")
            actual_status = 0
            response_body = {}
            matched = False
            error = str(e)

        # Calculate response time
        elapsed_ms = (time.time() - start_time) * 1000

        result = StatusCodeTestResult(
            scenario=scenario,
            actual_status_code=actual_status,
            expected_status_code=scenario.status_code,
            matched=matched,
            response_body=response_body,
            response_time_ms=elapsed_ms,
            error=error
        )

        self.test_results.append(result)

        # Track tested code
        endpoint_key = scenario.endpoint_key
        if endpoint_key not in self.tested_codes:
            self.tested_codes[endpoint_key] = set()
        self.tested_codes[endpoint_key].add(actual_status)

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

    async def execute_all_scenarios(
        self,
        scenarios: List[StatusCodeScenario]
    ) -> List[StatusCodeTestResult]:
        """
        Execute all status code scenarios

        Args:
            scenarios: List of scenarios to execute

        Returns:
            List of test results
        """
        logger.info(f"🧪 Executing {len(scenarios)} status code scenarios...")

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
        matched = sum(1 for r in results if r.matched)
        total = len(results)

        logger.info(f"\n✅ Executed {total} scenarios")
        logger.info(f"   Matched: {matched}/{total} ({matched/total*100:.1f}%)")

        return results

    def set_documented_codes(
        self,
        endpoint_key: str,
        codes: List[int]
    ):
        """
        Set documented status codes for an endpoint

        Args:
            endpoint_key: Endpoint identifier
            codes: List of documented status codes
        """
        self.documented_codes[endpoint_key] = set(codes)

    def get_endpoint_coverage(
        self,
        endpoint_key: str
    ) -> EndpointCoverage:
        """
        Get coverage statistics for a specific endpoint

        Args:
            endpoint_key: Endpoint identifier

        Returns:
            EndpointCoverage with stats
        """
        documented = self.documented_codes.get(endpoint_key, set())
        tested = self.tested_codes.get(endpoint_key, set())

        if not documented:
            # No documented codes, can't calculate coverage
            return EndpointCoverage(
                endpoint_key=endpoint_key,
                documented_codes=documented,
                tested_codes=tested,
                missing_codes=set(),
                coverage_percentage=0.0
            )

        missing = documented - tested
        coverage = (len(tested & documented) / len(documented)) * 100 if documented else 0

        return EndpointCoverage(
            endpoint_key=endpoint_key,
            documented_codes=documented,
            tested_codes=tested,
            missing_codes=missing,
            coverage_percentage=coverage
        )

    def get_overall_coverage(self) -> Dict[str, Any]:
        """
        Get overall status code coverage statistics

        Returns:
            Dict with coverage stats
        """
        all_documented = set()
        all_tested = set()
        endpoint_coverages = []

        for endpoint_key in self.documented_codes.keys():
            coverage = self.get_endpoint_coverage(endpoint_key)
            endpoint_coverages.append(coverage)

            all_documented.update(coverage.documented_codes)
            all_tested.update(coverage.tested_codes)

        # Calculate overall coverage
        if all_documented:
            overall_coverage = (len(all_tested & all_documented) / len(all_documented)) * 100
        else:
            overall_coverage = 0.0

        # Count results by match
        total_tests = len(self.test_results)
        matched_tests = sum(1 for r in self.test_results if r.matched)

        # Count by status code category
        success_tests = sum(1 for r in self.test_results if 200 <= r.expected_status_code < 300)
        client_error_tests = sum(1 for r in self.test_results if 400 <= r.expected_status_code < 500)
        server_error_tests = sum(1 for r in self.test_results if 500 <= r.expected_status_code < 600)

        return {
            'overall_coverage_percentage': overall_coverage,
            'total_documented_codes': len(all_documented),
            'total_tested_codes': len(all_tested & all_documented),
            'missing_codes': list(all_documented - all_tested),
            'total_tests': total_tests,
            'matched_tests': matched_tests,
            'match_rate': (matched_tests / total_tests * 100) if total_tests > 0 else 0,
            'test_breakdown': {
                'success': success_tests,
                'client_error': client_error_tests,
                'server_error': server_error_tests
            },
            'endpoint_coverages': [
                {
                    'endpoint': ec.endpoint_key,
                    'coverage': ec.coverage_percentage,
                    'documented': len(ec.documented_codes),
                    'tested': len(ec.tested_codes),
                    'missing': list(ec.missing_codes)
                }
                for ec in endpoint_coverages
            ]
        }

    def generate_coverage_report(self) -> str:
        """
        Generate human-readable coverage report

        Returns:
            Formatted coverage report
        """
        stats = self.get_overall_coverage()

        lines = []
        lines.append("=" * 80)
        lines.append("STATUS CODE COVERAGE REPORT")
        lines.append("=" * 80)
        lines.append("")

        # Overall stats
        lines.append(f"Overall Coverage: {stats['overall_coverage_percentage']:.1f}%")
        lines.append(f"Total Documented Codes: {stats['total_documented_codes']}")
        lines.append(f"Tested Codes: {stats['total_tested_codes']}")
        lines.append(f"Missing Codes: {len(stats['missing_codes'])}")

        if stats['missing_codes']:
            lines.append(f"   Missing: {sorted(stats['missing_codes'])}")

        lines.append("")

        # Test execution stats
        lines.append(f"Test Execution:")
        lines.append(f"   Total Tests: {stats['total_tests']}")
        lines.append(f"   Matched Expected: {stats['matched_tests']} ({stats['match_rate']:.1f}%)")
        lines.append(f"   Success Tests (2xx): {stats['test_breakdown']['success']}")
        lines.append(f"   Client Error Tests (4xx): {stats['test_breakdown']['client_error']}")
        lines.append(f"   Server Error Tests (5xx): {stats['test_breakdown']['server_error']}")
        lines.append("")

        # Per-endpoint coverage
        lines.append("=" * 80)
        lines.append("PER-ENDPOINT COVERAGE")
        lines.append("=" * 80)
        lines.append("")

        for ec in stats['endpoint_coverages']:
            coverage_icon = "✅" if ec['coverage'] == 100 else "⚠️" if ec['coverage'] >= 50 else "❌"

            lines.append(f"{coverage_icon} {ec['endpoint']}")
            lines.append(f"   Coverage: {ec['coverage']:.1f}%")
            lines.append(f"   Documented: {ec['documented']} codes")
            lines.append(f"   Tested: {ec['tested']} codes")

            if ec['missing']:
                lines.append(f"   Missing: {sorted(ec['missing'])}")

            lines.append("")

        return "\n".join(lines)

    def get_failed_scenarios(self) -> List[StatusCodeTestResult]:
        """Get scenarios that didn't return expected status code"""
        return [r for r in self.test_results if not r.matched]

    def get_scenarios_by_code(
        self,
        status_code: int
    ) -> List[StatusCodeTestResult]:
        """Get all test results for a specific status code"""
        return [r for r in self.test_results if r.expected_status_code == status_code]


# Add missing import at top of file
import asyncio
