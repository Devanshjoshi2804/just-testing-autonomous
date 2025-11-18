"""
Coverage Tracker
Tracks test coverage across endpoints, parameters, status codes, and scenarios
"""
from typing import Dict, Any, List, Set, Optional
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime

try:
    from loguru import logger
except ImportError:
    class MockLogger:
        def info(self, msg, **kwargs): pass
        def warning(self, msg, **kwargs): pass
        def error(self, msg, **kwargs): pass
        def debug(self, msg, **kwargs): pass
    logger = MockLogger()


@dataclass
class CoverageData:
    """Coverage data for a single test session"""
    session_id: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    # Endpoint coverage
    total_endpoints: int = 0
    tested_endpoints: Set[str] = field(default_factory=set)

    # Method coverage
    methods_by_endpoint: Dict[str, str] = field(default_factory=dict)

    # Parameter coverage
    parameters_by_endpoint: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    tested_parameters: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))

    # Status code coverage
    documented_codes_by_endpoint: Dict[str, Set[int]] = field(default_factory=lambda: defaultdict(set))
    tested_codes_by_endpoint: Dict[str, Set[int]] = field(default_factory=lambda: defaultdict(set))

    # Scenario coverage
    scenario_types: Set[str] = field(default_factory=set)
    scenarios_by_endpoint: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))

    # Test statistics
    total_tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0

    def get_endpoint_coverage(self) -> float:
        """Get endpoint coverage percentage"""
        if self.total_endpoints == 0:
            return 0.0
        return (len(self.tested_endpoints) / self.total_endpoints) * 100

    def get_parameter_coverage(self, endpoint: str) -> float:
        """Get parameter coverage for specific endpoint"""
        all_params = self.parameters_by_endpoint.get(endpoint, set())
        tested_params = self.tested_parameters.get(endpoint, set())

        if not all_params:
            return 0.0

        return (len(tested_params) / len(all_params)) * 100

    def get_overall_parameter_coverage(self) -> float:
        """Get overall parameter coverage across all endpoints"""
        total_params = sum(len(params) for params in self.parameters_by_endpoint.values())
        tested_params = sum(len(params) for params in self.tested_parameters.values())

        if total_params == 0:
            return 0.0

        return (tested_params / total_params) * 100

    def get_status_code_coverage(self, endpoint: str) -> float:
        """Get status code coverage for specific endpoint"""
        documented = self.documented_codes_by_endpoint.get(endpoint, set())
        tested = self.tested_codes_by_endpoint.get(endpoint, set())

        if not documented:
            return 0.0

        return (len(tested & documented) / len(documented)) * 100

    def get_overall_status_code_coverage(self) -> float:
        """Get overall status code coverage"""
        total_documented = sum(len(codes) for codes in self.documented_codes_by_endpoint.values())

        if total_documented == 0:
            return 0.0

        total_tested = 0
        for endpoint, documented in self.documented_codes_by_endpoint.items():
            tested = self.tested_codes_by_endpoint.get(endpoint, set())
            total_tested += len(tested & documented)

        return (total_tested / total_documented) * 100

    def get_scenario_coverage(self, endpoint: str) -> int:
        """Get number of scenario types tested for endpoint"""
        return len(self.scenarios_by_endpoint.get(endpoint, set()))

    def get_overall_coverage(self) -> float:
        """Get overall coverage score (weighted average)"""
        endpoint_cov = self.get_endpoint_coverage()
        param_cov = self.get_overall_parameter_coverage()
        status_cov = self.get_overall_status_code_coverage()

        # Weighted average: endpoints (40%), parameters (30%), status codes (30%)
        return (endpoint_cov * 0.4) + (param_cov * 0.3) + (status_cov * 0.3)


class CoverageTracker:
    """
    Track test coverage across multiple dimensions

    Tracks:
    - Endpoint coverage: Which endpoints have been tested
    - Parameter coverage: Which parameters have been tested
    - Status code coverage: Which status codes have been triggered
    - Scenario coverage: Which test scenarios have been executed
    """

    def __init__(self, session_id: str):
        """
        Initialize coverage tracker

        Args:
            session_id: Unique session ID for this test run
        """
        self.coverage = CoverageData(session_id=session_id)
        logger.info(f"Initialized coverage tracker for session: {session_id}")

    def register_endpoints(self, endpoints: List[Dict[str, Any]]):
        """
        Register all endpoints to track

        Args:
            endpoints: List of endpoint dicts with metadata
        """
        self.coverage.total_endpoints = len(endpoints)

        for endpoint in endpoints:
            method = endpoint.get('method', 'GET')
            path = endpoint.get('path', '')
            endpoint_key = f"{method} {path}"

            # Register method
            self.coverage.methods_by_endpoint[endpoint_key] = method

            # Register parameters
            params = endpoint.get('parameters', {})
            if params:
                self.coverage.parameters_by_endpoint[endpoint_key] = set(params.keys())

            # Register documented status codes
            responses = endpoint.get('responses', {})
            if responses:
                codes = {int(code) for code in responses.keys() if str(code).isdigit()}
                self.coverage.documented_codes_by_endpoint[endpoint_key] = codes

        logger.info(f"Registered {len(endpoints)} endpoints for coverage tracking")

    def record_test(
        self,
        endpoint_key: str,
        status_code: int,
        parameters_tested: Optional[List[str]] = None,
        scenario_type: Optional[str] = None,
        passed: bool = True
    ):
        """
        Record a test execution

        Args:
            endpoint_key: Endpoint identifier (METHOD path)
            status_code: HTTP status code received
            parameters_tested: List of parameter names tested
            scenario_type: Type of test scenario
            passed: Whether test passed
        """
        # Record endpoint tested
        self.coverage.tested_endpoints.add(endpoint_key)

        # Record status code
        self.coverage.tested_codes_by_endpoint[endpoint_key].add(status_code)

        # Record parameters
        if parameters_tested:
            self.coverage.tested_parameters[endpoint_key].update(parameters_tested)

        # Record scenario type
        if scenario_type:
            self.coverage.scenario_types.add(scenario_type)
            self.coverage.scenarios_by_endpoint[endpoint_key].add(scenario_type)

        # Update test statistics
        self.coverage.total_tests_run += 1
        if passed:
            self.coverage.tests_passed += 1
        else:
            self.coverage.tests_failed += 1

    def get_coverage_summary(self) -> Dict[str, Any]:
        """
        Get coverage summary

        Returns:
            Dict with coverage statistics
        """
        return {
            'session_id': self.coverage.session_id,
            'overall_coverage': round(self.coverage.get_overall_coverage(), 2),
            'endpoint_coverage': round(self.coverage.get_endpoint_coverage(), 2),
            'parameter_coverage': round(self.coverage.get_overall_parameter_coverage(), 2),
            'status_code_coverage': round(self.coverage.get_overall_status_code_coverage(), 2),
            'endpoints': {
                'total': self.coverage.total_endpoints,
                'tested': len(self.coverage.tested_endpoints),
                'untested': self.coverage.total_endpoints - len(self.coverage.tested_endpoints)
            },
            'tests': {
                'total': self.coverage.total_tests_run,
                'passed': self.coverage.tests_passed,
                'failed': self.coverage.tests_failed,
                'pass_rate': round(
                    (self.coverage.tests_passed / self.coverage.total_tests_run * 100)
                    if self.coverage.total_tests_run > 0 else 0,
                    2
                )
            },
            'scenario_types': len(self.coverage.scenario_types)
        }

    def get_endpoint_details(self, endpoint_key: str) -> Dict[str, Any]:
        """
        Get detailed coverage for specific endpoint

        Args:
            endpoint_key: Endpoint identifier

        Returns:
            Dict with endpoint coverage details
        """
        tested = endpoint_key in self.coverage.tested_endpoints

        all_params = self.coverage.parameters_by_endpoint.get(endpoint_key, set())
        tested_params = self.coverage.tested_parameters.get(endpoint_key, set())
        untested_params = all_params - tested_params

        documented_codes = self.coverage.documented_codes_by_endpoint.get(endpoint_key, set())
        tested_codes = self.coverage.tested_codes_by_endpoint.get(endpoint_key, set())
        untested_codes = documented_codes - tested_codes

        scenarios = self.coverage.scenarios_by_endpoint.get(endpoint_key, set())

        return {
            'endpoint': endpoint_key,
            'tested': tested,
            'parameter_coverage': round(self.coverage.get_parameter_coverage(endpoint_key), 2),
            'parameters': {
                'total': len(all_params),
                'tested': list(tested_params),
                'untested': list(untested_params)
            },
            'status_code_coverage': round(self.coverage.get_status_code_coverage(endpoint_key), 2),
            'status_codes': {
                'documented': list(documented_codes),
                'tested': list(tested_codes),
                'untested': list(untested_codes)
            },
            'scenarios': {
                'count': len(scenarios),
                'types': list(scenarios)
            }
        }

    def get_untested_endpoints(self) -> List[str]:
        """Get list of endpoints that haven't been tested"""
        all_endpoints = set(self.coverage.methods_by_endpoint.keys())
        return list(all_endpoints - self.coverage.tested_endpoints)

    def get_coverage_gaps(self) -> Dict[str, Any]:
        """
        Identify coverage gaps

        Returns:
            Dict with coverage gaps and recommendations
        """
        gaps = {
            'untested_endpoints': self.get_untested_endpoints(),
            'low_parameter_coverage': [],
            'missing_status_codes': [],
            'low_scenario_coverage': []
        }

        # Find endpoints with low parameter coverage
        for endpoint_key in self.coverage.tested_endpoints:
            param_cov = self.coverage.get_parameter_coverage(endpoint_key)
            if param_cov < 80:
                gaps['low_parameter_coverage'].append({
                    'endpoint': endpoint_key,
                    'coverage': round(param_cov, 2)
                })

        # Find endpoints with missing status codes
        for endpoint_key in self.coverage.tested_endpoints:
            documented = self.coverage.documented_codes_by_endpoint.get(endpoint_key, set())
            tested = self.coverage.tested_codes_by_endpoint.get(endpoint_key, set())
            missing = documented - tested

            if missing:
                gaps['missing_status_codes'].append({
                    'endpoint': endpoint_key,
                    'missing_codes': list(missing)
                })

        # Find endpoints with low scenario coverage
        for endpoint_key in self.coverage.tested_endpoints:
            scenario_count = self.coverage.get_scenario_coverage(endpoint_key)
            if scenario_count < 3:
                gaps['low_scenario_coverage'].append({
                    'endpoint': endpoint_key,
                    'scenario_count': scenario_count
                })

        return gaps

    def finalize(self):
        """Mark coverage tracking as complete"""
        self.coverage.end_time = datetime.now()
        logger.info(f"Finalized coverage tracking for session: {self.coverage.session_id}")

    def export_data(self) -> Dict[str, Any]:
        """
        Export all coverage data

        Returns:
            Dict with complete coverage data
        """
        return {
            'session_id': self.coverage.session_id,
            'start_time': self.coverage.start_time.isoformat(),
            'end_time': self.coverage.end_time.isoformat() if self.coverage.end_time else None,
            'summary': self.get_coverage_summary(),
            'endpoints': {
                endpoint: self.get_endpoint_details(endpoint)
                for endpoint in self.coverage.methods_by_endpoint.keys()
            },
            'gaps': self.get_coverage_gaps()
        }
