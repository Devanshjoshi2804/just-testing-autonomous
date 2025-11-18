"""
Result Aggregator for Parallel Test Execution
Collects and aggregates results from concurrent test runs
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
from loguru import logger
import statistics


@dataclass
class TestResult:
    """Individual test result"""
    test_id: str
    test_name: str
    endpoint_path: str
    endpoint_method: str
    test_type: str
    success: bool
    status_code: Optional[int] = None
    expected_status: Optional[int] = None
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    executed_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AggregatedResults:
    """Aggregated test results"""
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    success_rate: float = 0.0

    # Performance metrics
    total_duration_ms: float = 0.0
    average_response_time_ms: float = 0.0
    min_response_time_ms: float = 0.0
    max_response_time_ms: float = 0.0
    median_response_time_ms: float = 0.0

    # Test type breakdown
    test_type_distribution: Dict[str, int] = field(default_factory=dict)
    test_type_success_rates: Dict[str, float] = field(default_factory=dict)

    # Endpoint breakdown
    endpoint_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Status code distribution
    status_code_distribution: Dict[int, int] = field(default_factory=dict)

    # Failed tests details
    failed_tests_details: List[Dict[str, Any]] = field(default_factory=list)

    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_elapsed_seconds: float = 0.0


class ResultAggregator:
    """
    Aggregates results from parallel test execution

    Features:
    - Real-time result collection
    - Statistical analysis
    - Test type breakdown
    - Endpoint-level metrics
    - Performance analysis
    """

    def __init__(self):
        """Initialize result aggregator"""
        self.results: List[TestResult] = []
        self.results_by_endpoint: Dict[str, List[TestResult]] = defaultdict(list)
        self.results_by_type: Dict[str, List[TestResult]] = defaultdict(list)
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

        logger.info("Initialized ResultAggregator")

    def start(self):
        """Mark start of test execution"""
        self.started_at = datetime.now()
        logger.info("Result aggregation started")

    def complete(self):
        """Mark completion of test execution"""
        self.completed_at = datetime.now()
        logger.info("Result aggregation completed")

    def add_result(self, result: TestResult):
        """
        Add a test result

        Args:
            result: TestResult object
        """
        self.results.append(result)

        # Index by endpoint
        endpoint_key = f"{result.endpoint_method}:{result.endpoint_path}"
        self.results_by_endpoint[endpoint_key].append(result)

        # Index by test type
        self.results_by_type[result.test_type].append(result)

        logger.debug(f"Added result for test {result.test_id}")

    def add_results_batch(self, results: List[TestResult]):
        """
        Add multiple results at once

        Args:
            results: List of TestResult objects
        """
        for result in results:
            self.add_result(result)

        logger.info(f"Added {len(results)} results")

    def get_aggregated_results(self) -> AggregatedResults:
        """
        Get aggregated statistics

        Returns:
            AggregatedResults object
        """
        if not self.results:
            return AggregatedResults()

        # Basic counts
        total = len(self.results)
        passed = sum(1 for r in self.results if r.success)
        failed = total - passed
        success_rate = (passed / total * 100) if total > 0 else 0.0

        # Response times
        response_times = [
            r.response_time_ms for r in self.results
            if r.response_time_ms is not None
        ]

        avg_response = statistics.mean(response_times) if response_times else 0.0
        min_response = min(response_times) if response_times else 0.0
        max_response = max(response_times) if response_times else 0.0
        median_response = statistics.median(response_times) if response_times else 0.0
        total_duration = sum(response_times) if response_times else 0.0

        # Test type distribution
        type_dist = {}
        type_success_rates = {}

        for test_type, results in self.results_by_type.items():
            type_dist[test_type] = len(results)
            type_passed = sum(1 for r in results if r.success)
            type_success_rates[test_type] = (
                type_passed / len(results) * 100
                if len(results) > 0 else 0.0
            )

        # Endpoint breakdown
        endpoint_results = {}

        for endpoint_key, results in self.results_by_endpoint.items():
            endpoint_passed = sum(1 for r in results if r.success)
            endpoint_response_times = [
                r.response_time_ms for r in results
                if r.response_time_ms is not None
            ]

            endpoint_results[endpoint_key] = {
                'total_tests': len(results),
                'passed_tests': endpoint_passed,
                'failed_tests': len(results) - endpoint_passed,
                'success_rate': (
                    endpoint_passed / len(results) * 100
                    if len(results) > 0 else 0.0
                ),
                'avg_response_time_ms': (
                    statistics.mean(endpoint_response_times)
                    if endpoint_response_times else 0.0
                )
            }

        # Status code distribution
        status_dist = defaultdict(int)
        for result in self.results:
            if result.status_code is not None:
                status_dist[result.status_code] += 1

        # Failed tests details
        failed_details = []
        for result in self.results:
            if not result.success:
                failed_details.append({
                    'test_id': result.test_id,
                    'test_name': result.test_name,
                    'endpoint': f"{result.endpoint_method} {result.endpoint_path}",
                    'test_type': result.test_type,
                    'status_code': result.status_code,
                    'expected_status': result.expected_status,
                    'error_message': result.error_message,
                    'executed_at': result.executed_at
                })

        # Calculate elapsed time
        elapsed_seconds = 0.0
        if self.started_at and self.completed_at:
            elapsed_seconds = (self.completed_at - self.started_at).total_seconds()

        return AggregatedResults(
            total_tests=total,
            passed_tests=passed,
            failed_tests=failed,
            success_rate=success_rate,
            total_duration_ms=total_duration,
            average_response_time_ms=avg_response,
            min_response_time_ms=min_response,
            max_response_time_ms=max_response,
            median_response_time_ms=median_response,
            test_type_distribution=dict(type_dist),
            test_type_success_rates=type_success_rates,
            endpoint_results=endpoint_results,
            status_code_distribution=dict(status_dist),
            failed_tests_details=failed_details,
            started_at=self.started_at,
            completed_at=self.completed_at,
            total_elapsed_seconds=elapsed_seconds
        )

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics

        Returns:
            Summary dictionary
        """
        aggregated = self.get_aggregated_results()

        return {
            'total_tests': aggregated.total_tests,
            'passed_tests': aggregated.passed_tests,
            'failed_tests': aggregated.failed_tests,
            'success_rate': f"{aggregated.success_rate:.2f}%",
            'average_response_time_ms': f"{aggregated.average_response_time_ms:.2f}",
            'total_duration_seconds': f"{aggregated.total_elapsed_seconds:.2f}",
            'throughput': (
                f"{aggregated.total_tests / aggregated.total_elapsed_seconds:.2f} tests/sec"
                if aggregated.total_elapsed_seconds > 0 else "N/A"
            )
        }

    def get_failed_tests(self) -> List[TestResult]:
        """
        Get all failed tests

        Returns:
            List of failed TestResult objects
        """
        return [r for r in self.results if not r.success]

    def get_passed_tests(self) -> List[TestResult]:
        """
        Get all passed tests

        Returns:
            List of passed TestResult objects
        """
        return [r for r in self.results if r.success]

    def get_tests_by_endpoint(
        self,
        method: str,
        path: str
    ) -> List[TestResult]:
        """
        Get all tests for a specific endpoint

        Args:
            method: HTTP method
            path: Endpoint path

        Returns:
            List of TestResult objects
        """
        endpoint_key = f"{method}:{path}"
        return self.results_by_endpoint.get(endpoint_key, [])

    def get_tests_by_type(self, test_type: str) -> List[TestResult]:
        """
        Get all tests of a specific type

        Args:
            test_type: Test type (e.g., "positive", "negative", "boundary")

        Returns:
            List of TestResult objects
        """
        return self.results_by_type.get(test_type, [])

    def get_slowest_tests(self, limit: int = 10) -> List[TestResult]:
        """
        Get slowest tests by response time

        Args:
            limit: Maximum number of tests to return

        Returns:
            List of TestResult objects
        """
        sorted_results = sorted(
            [r for r in self.results if r.response_time_ms is not None],
            key=lambda r: r.response_time_ms,
            reverse=True
        )

        return sorted_results[:limit]

    def get_fastest_tests(self, limit: int = 10) -> List[TestResult]:
        """
        Get fastest tests by response time

        Args:
            limit: Maximum number of tests to return

        Returns:
            List of TestResult objects
        """
        sorted_results = sorted(
            [r for r in self.results if r.response_time_ms is not None],
            key=lambda r: r.response_time_ms
        )

        return sorted_results[:limit]

    def export_results(self) -> List[Dict[str, Any]]:
        """
        Export all results as dictionaries

        Returns:
            List of result dictionaries
        """
        return [
            {
                'test_id': r.test_id,
                'test_name': r.test_name,
                'endpoint': f"{r.endpoint_method} {r.endpoint_path}",
                'test_type': r.test_type,
                'success': r.success,
                'status_code': r.status_code,
                'expected_status': r.expected_status,
                'response_time_ms': r.response_time_ms,
                'error_message': r.error_message,
                'executed_at': r.executed_at.isoformat(),
                'metadata': r.metadata
            }
            for r in self.results
        ]

    def clear(self):
        """Clear all results"""
        self.results.clear()
        self.results_by_endpoint.clear()
        self.results_by_type.clear()
        self.started_at = None
        self.completed_at = None

        logger.info("Results cleared")

    def count(self) -> int:
        """Get total result count"""
        return len(self.results)
