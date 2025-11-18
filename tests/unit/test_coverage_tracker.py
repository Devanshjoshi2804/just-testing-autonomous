"""
Unit Tests for CoverageTracker
Tests multi-dimensional coverage tracking (endpoints, parameters, status codes, scenarios)
"""
import pytest
from datetime import datetime
from src.metrics.coverage_tracker import (
    CoverageTracker,
    CoverageData
)


@pytest.mark.unit
class TestCoverageData:
    """Test CoverageData dataclass"""

    @pytest.fixture
    def coverage_data(self):
        """Create a CoverageData instance"""
        return CoverageData(session_id="test-session-123")

    # ========================================================================
    # Initialization Tests
    # ========================================================================

    def test_initialization(self, coverage_data):
        """Test CoverageData initializes with defaults"""
        assert coverage_data.session_id == "test-session-123"
        assert coverage_data.total_endpoints == 0
        assert len(coverage_data.tested_endpoints) == 0
        assert coverage_data.end_time is None
        assert isinstance(coverage_data.start_time, datetime)

    # ========================================================================
    # Endpoint Coverage Tests
    # ========================================================================

    def test_endpoint_coverage_zero_endpoints(self, coverage_data):
        """Test endpoint coverage with no endpoints"""
        assert coverage_data.get_endpoint_coverage() == 0.0

    def test_endpoint_coverage_all_tested(self, coverage_data):
        """Test endpoint coverage when all endpoints tested"""
        coverage_data.total_endpoints = 5
        coverage_data.tested_endpoints = {
            "GET /api/users",
            "POST /api/users",
            "GET /api/users/{id}",
            "PUT /api/users/{id}",
            "DELETE /api/users/{id}"
        }

        coverage = coverage_data.get_endpoint_coverage()
        assert coverage == 100.0

    def test_endpoint_coverage_partial(self, coverage_data):
        """Test endpoint coverage with partial testing"""
        coverage_data.total_endpoints = 10
        coverage_data.tested_endpoints = {
            "GET /api/users",
            "POST /api/users",
            "GET /api/posts"
        }

        coverage = coverage_data.get_endpoint_coverage()
        assert coverage == 30.0  # 3 out of 10

    def test_endpoint_coverage_none_tested(self, coverage_data):
        """Test endpoint coverage with no endpoints tested"""
        coverage_data.total_endpoints = 5
        coverage_data.tested_endpoints = set()

        coverage = coverage_data.get_endpoint_coverage()
        assert coverage == 0.0

    # ========================================================================
    # Parameter Coverage Tests
    # ========================================================================

    def test_parameter_coverage_specific_endpoint(self, coverage_data):
        """Test parameter coverage for specific endpoint"""
        endpoint = "GET /api/users"
        coverage_data.parameters_by_endpoint[endpoint] = {"page", "limit", "search"}
        coverage_data.tested_parameters[endpoint] = {"page", "limit"}

        coverage = coverage_data.get_parameter_coverage(endpoint)
        assert coverage == pytest.approx(66.67, rel=0.01)  # 2 out of 3

    def test_parameter_coverage_endpoint_no_parameters(self, coverage_data):
        """Test parameter coverage for endpoint with no parameters"""
        endpoint = "GET /api/health"

        coverage = coverage_data.get_parameter_coverage(endpoint)
        assert coverage == 0.0

    def test_parameter_coverage_all_parameters_tested(self, coverage_data):
        """Test parameter coverage when all parameters tested"""
        endpoint = "POST /api/users"
        coverage_data.parameters_by_endpoint[endpoint] = {"email", "name", "age"}
        coverage_data.tested_parameters[endpoint] = {"email", "name", "age"}

        coverage = coverage_data.get_parameter_coverage(endpoint)
        assert coverage == 100.0

    def test_overall_parameter_coverage(self, coverage_data):
        """Test overall parameter coverage across all endpoints"""
        # Endpoint 1: 2 out of 3 params tested
        coverage_data.parameters_by_endpoint["GET /api/users"] = {"page", "limit", "search"}
        coverage_data.tested_parameters["GET /api/users"] = {"page", "limit"}

        # Endpoint 2: 3 out of 3 params tested
        coverage_data.parameters_by_endpoint["POST /api/users"] = {"email", "name", "age"}
        coverage_data.tested_parameters["POST /api/users"] = {"email", "name", "age"}

        # Total: 5 out of 6 params tested
        coverage = coverage_data.get_overall_parameter_coverage()
        assert coverage == pytest.approx(83.33, rel=0.01)

    def test_overall_parameter_coverage_no_parameters(self, coverage_data):
        """Test overall parameter coverage with no parameters"""
        coverage = coverage_data.get_overall_parameter_coverage()
        assert coverage == 0.0

    # ========================================================================
    # Status Code Coverage Tests
    # ========================================================================

    def test_status_code_coverage_specific_endpoint(self, coverage_data):
        """Test status code coverage for specific endpoint"""
        endpoint = "GET /api/users"
        coverage_data.documented_codes_by_endpoint[endpoint] = {200, 400, 401, 404}
        coverage_data.tested_codes_by_endpoint[endpoint] = {200, 400}

        coverage = coverage_data.get_status_code_coverage(endpoint)
        assert coverage == 50.0  # 2 out of 4

    def test_status_code_coverage_all_codes_tested(self, coverage_data):
        """Test status code coverage when all codes tested"""
        endpoint = "POST /api/users"
        coverage_data.documented_codes_by_endpoint[endpoint] = {201, 400, 422}
        coverage_data.tested_codes_by_endpoint[endpoint] = {201, 400, 422}

        coverage = coverage_data.get_status_code_coverage(endpoint)
        assert coverage == 100.0

    def test_status_code_coverage_includes_undocumented(self, coverage_data):
        """Test status code coverage handles undocumented codes"""
        endpoint = "GET /api/users"
        coverage_data.documented_codes_by_endpoint[endpoint] = {200, 400}
        # Tested includes 500 which wasn't documented
        coverage_data.tested_codes_by_endpoint[endpoint] = {200, 400, 500}

        # Should only count intersection with documented codes
        coverage = coverage_data.get_status_code_coverage(endpoint)
        assert coverage == 100.0  # 2 out of 2 documented codes tested

    def test_overall_status_code_coverage(self, coverage_data):
        """Test overall status code coverage"""
        # Endpoint 1: 2 out of 3 codes tested
        coverage_data.documented_codes_by_endpoint["GET /api/users"] = {200, 400, 401}
        coverage_data.tested_codes_by_endpoint["GET /api/users"] = {200, 400}

        # Endpoint 2: 3 out of 3 codes tested
        coverage_data.documented_codes_by_endpoint["POST /api/users"] = {201, 400, 422}
        coverage_data.tested_codes_by_endpoint["POST /api/users"] = {201, 400, 422}

        # Total: 5 out of 6 codes tested
        coverage = coverage_data.get_overall_status_code_coverage()
        assert coverage == pytest.approx(83.33, rel=0.01)

    def test_overall_status_code_coverage_no_codes(self, coverage_data):
        """Test overall status code coverage with no documented codes"""
        coverage = coverage_data.get_overall_status_code_coverage()
        assert coverage == 0.0

    # ========================================================================
    # Scenario Coverage Tests
    # ========================================================================

    def test_scenario_coverage(self, coverage_data):
        """Test scenario coverage for endpoint"""
        endpoint = "GET /api/users"
        coverage_data.scenarios_by_endpoint[endpoint] = {
            "happy_path",
            "boundary_value",
            "negative"
        }

        scenario_count = coverage_data.get_scenario_coverage(endpoint)
        assert scenario_count == 3

    def test_scenario_coverage_no_scenarios(self, coverage_data):
        """Test scenario coverage for endpoint with no scenarios"""
        endpoint = "GET /api/health"

        scenario_count = coverage_data.get_scenario_coverage(endpoint)
        assert scenario_count == 0

    # ========================================================================
    # Overall Coverage Tests
    # ========================================================================

    def test_overall_coverage_perfect(self, coverage_data):
        """Test overall coverage with 100% on all dimensions"""
        # 100% endpoint coverage
        coverage_data.total_endpoints = 2
        coverage_data.tested_endpoints = {"GET /api/users", "POST /api/users"}

        # 100% parameter coverage
        coverage_data.parameters_by_endpoint["GET /api/users"] = {"page"}
        coverage_data.tested_parameters["GET /api/users"] = {"page"}

        # 100% status code coverage
        coverage_data.documented_codes_by_endpoint["GET /api/users"] = {200}
        coverage_data.tested_codes_by_endpoint["GET /api/users"] = {200}

        overall = coverage_data.get_overall_coverage()
        assert overall == 100.0

    def test_overall_coverage_weighted_average(self, coverage_data):
        """Test overall coverage uses weighted average"""
        # 50% endpoint coverage
        coverage_data.total_endpoints = 2
        coverage_data.tested_endpoints = {"GET /api/users"}

        # 100% parameter coverage
        coverage_data.parameters_by_endpoint["GET /api/users"] = {"page"}
        coverage_data.tested_parameters["GET /api/users"] = {"page"}

        # 100% status code coverage
        coverage_data.documented_codes_by_endpoint["GET /api/users"] = {200}
        coverage_data.tested_codes_by_endpoint["GET /api/users"] = {200}

        # Overall = (50 * 0.4) + (100 * 0.3) + (100 * 0.3) = 20 + 30 + 30 = 80
        overall = coverage_data.get_overall_coverage()
        assert overall == 80.0

    def test_overall_coverage_zero(self, coverage_data):
        """Test overall coverage with nothing tested"""
        overall = coverage_data.get_overall_coverage()
        assert overall == 0.0

    # ========================================================================
    # Test Statistics Tests
    # ========================================================================

    def test_test_statistics(self, coverage_data):
        """Test test statistics tracking"""
        coverage_data.total_tests_run = 100
        coverage_data.tests_passed = 85
        coverage_data.tests_failed = 15

        assert coverage_data.total_tests_run == 100
        assert coverage_data.tests_passed == 85
        assert coverage_data.tests_failed == 15


@pytest.mark.unit
class TestCoverageTracker:
    """Test CoverageTracker functionality"""

    @pytest.fixture
    def tracker(self):
        """Create a CoverageTracker instance"""
        return CoverageTracker(session_id="test-session-456")

    @pytest.fixture
    def sample_endpoints(self):
        """Sample endpoints for testing"""
        return [
            {
                "method": "GET",
                "path": "/api/users",
                "parameters": {
                    "page": {"type": "integer"},
                    "limit": {"type": "integer"}
                },
                "responses": {
                    "200": {"description": "Success"},
                    "400": {"description": "Bad Request"},
                    "401": {"description": "Unauthorized"}
                }
            },
            {
                "method": "POST",
                "path": "/api/users",
                "parameters": {
                    "email": {"type": "string"},
                    "name": {"type": "string"}
                },
                "responses": {
                    "201": {"description": "Created"},
                    "400": {"description": "Bad Request"},
                    "422": {"description": "Validation Error"}
                }
            }
        ]

    # ========================================================================
    # Initialization Tests
    # ========================================================================

    def test_initialization(self, tracker):
        """Test tracker initializes correctly"""
        assert tracker.coverage.session_id == "test-session-456"
        assert tracker.coverage.total_endpoints == 0

    # ========================================================================
    # Endpoint Registration Tests
    # ========================================================================

    def test_register_endpoints(self, tracker, sample_endpoints):
        """Test registering endpoints"""
        tracker.register_endpoints(sample_endpoints)

        assert tracker.coverage.total_endpoints == 2

        # Check parameters registered
        assert "page" in tracker.coverage.parameters_by_endpoint["GET /api/users"]
        assert "limit" in tracker.coverage.parameters_by_endpoint["GET /api/users"]
        assert "email" in tracker.coverage.parameters_by_endpoint["POST /api/users"]
        assert "name" in tracker.coverage.parameters_by_endpoint["POST /api/users"]

        # Check status codes registered
        assert 200 in tracker.coverage.documented_codes_by_endpoint["GET /api/users"]
        assert 400 in tracker.coverage.documented_codes_by_endpoint["GET /api/users"]
        assert 201 in tracker.coverage.documented_codes_by_endpoint["POST /api/users"]

    def test_register_empty_endpoints(self, tracker):
        """Test registering empty endpoint list"""
        tracker.register_endpoints([])
        assert tracker.coverage.total_endpoints == 0

    # ========================================================================
    # Test Recording Tests
    # ========================================================================

    def test_record_test_result(self, tracker, sample_endpoints):
        """Test recording a test result"""
        tracker.register_endpoints(sample_endpoints)

        test_result = {
            "endpoint": "/api/users",
            "method": "GET",
            "status_code": 200,
            "success": True,
            "parameters_tested": ["page", "limit"],
            "scenario_type": "happy_path"
        }

        tracker.record_test(test_result)

        # Check endpoint marked as tested
        assert "GET /api/users" in tracker.coverage.tested_endpoints

        # Check parameters marked as tested
        assert "page" in tracker.coverage.tested_parameters["GET /api/users"]
        assert "limit" in tracker.coverage.tested_parameters["GET /api/users"]

        # Check status code marked as tested
        assert 200 in tracker.coverage.tested_codes_by_endpoint["GET /api/users"]

        # Check scenario recorded
        assert "happy_path" in tracker.coverage.scenarios_by_endpoint["GET /api/users"]

        # Check test count
        assert tracker.coverage.total_tests_run == 1
        assert tracker.coverage.tests_passed == 1
        assert tracker.coverage.tests_failed == 0

    def test_record_failed_test(self, tracker, sample_endpoints):
        """Test recording a failed test"""
        tracker.register_endpoints(sample_endpoints)

        test_result = {
            "endpoint": "/api/users",
            "method": "GET",
            "status_code": 500,
            "success": False,
            "scenario_type": "error"
        }

        tracker.record_test(test_result)

        assert tracker.coverage.total_tests_run == 1
        assert tracker.coverage.tests_passed == 0
        assert tracker.coverage.tests_failed == 1

    def test_record_multiple_tests(self, tracker, sample_endpoints):
        """Test recording multiple test results"""
        tracker.register_endpoints(sample_endpoints)

        test_results = [
            {
                "endpoint": "/api/users",
                "method": "GET",
                "status_code": 200,
                "success": True,
                "parameters_tested": ["page"],
                "scenario_type": "happy_path"
            },
            {
                "endpoint": "/api/users",
                "method": "GET",
                "status_code": 400,
                "success": True,
                "parameters_tested": ["page"],
                "scenario_type": "negative"
            },
            {
                "endpoint": "/api/users",
                "method": "POST",
                "status_code": 201,
                "success": True,
                "parameters_tested": ["email", "name"],
                "scenario_type": "happy_path"
            }
        ]

        for result in test_results:
            tracker.record_test(result)

        assert tracker.coverage.total_tests_run == 3
        assert tracker.coverage.tests_passed == 3

        # Both endpoints tested
        assert len(tracker.coverage.tested_endpoints) == 2

        # Multiple status codes tested for GET endpoint
        assert 200 in tracker.coverage.tested_codes_by_endpoint["GET /api/users"]
        assert 400 in tracker.coverage.tested_codes_by_endpoint["GET /api/users"]

    # ========================================================================
    # Coverage Report Tests
    # ========================================================================

    def test_get_coverage_report(self, tracker, sample_endpoints):
        """Test generating coverage report"""
        tracker.register_endpoints(sample_endpoints)

        # Record some tests
        test_result = {
            "endpoint": "/api/users",
            "method": "GET",
            "status_code": 200,
            "success": True,
            "parameters_tested": ["page"],
            "scenario_type": "happy_path"
        }
        tracker.record_test(test_result)

        report = tracker.get_coverage_report()

        assert report is not None
        assert "endpoint_coverage" in report
        assert "parameter_coverage" in report
        assert "status_code_coverage" in report
        assert "overall_coverage" in report
        assert "test_statistics" in report

        # Check values
        assert report["endpoint_coverage"] == 50.0  # 1 out of 2
        assert report["overall_coverage"] > 0

    def test_coverage_report_empty(self, tracker):
        """Test coverage report with no tests"""
        report = tracker.get_coverage_report()

        assert report["endpoint_coverage"] == 0.0
        assert report["overall_coverage"] == 0.0
        assert report["test_statistics"]["total"] == 0

    # ========================================================================
    # Session Management Tests
    # ========================================================================

    def test_end_session(self, tracker):
        """Test ending a coverage tracking session"""
        tracker.end_session()

        assert tracker.coverage.end_time is not None
        assert isinstance(tracker.coverage.end_time, datetime)

    def test_session_duration(self, tracker):
        """Test calculating session duration"""
        import time
        time.sleep(0.1)  # Wait a bit
        tracker.end_session()

        duration = (tracker.coverage.end_time - tracker.coverage.start_time).total_seconds()
        assert duration >= 0.1

    # ========================================================================
    # Edge Cases Tests
    # ========================================================================

    def test_record_test_without_registration(self, tracker):
        """Test recording test without registering endpoints first"""
        test_result = {
            "endpoint": "/api/users",
            "method": "GET",
            "status_code": 200,
            "success": True
        }

        # Should not crash, just record what we can
        tracker.record_test(test_result)

        assert tracker.coverage.total_tests_run == 1

    def test_record_test_missing_fields(self, tracker):
        """Test recording test with missing fields"""
        test_result = {
            "endpoint": "/api/users",
            "method": "GET"
            # Missing status_code, success, etc.
        }

        # Should handle gracefully
        tracker.record_test(test_result)

        assert tracker.coverage.total_tests_run == 1

    def test_register_endpoint_without_parameters(self, tracker):
        """Test registering endpoint with no parameters"""
        endpoints = [
            {
                "method": "GET",
                "path": "/api/health",
                "responses": {"200": {"description": "OK"}}
            }
        ]

        tracker.register_endpoints(endpoints)

        assert tracker.coverage.total_endpoints == 1

    def test_register_endpoint_without_responses(self, tracker):
        """Test registering endpoint with no responses"""
        endpoints = [
            {
                "method": "GET",
                "path": "/api/data",
                "parameters": {"query": {"type": "string"}}
            }
        ]

        tracker.register_endpoints(endpoints)

        assert tracker.coverage.total_endpoints == 1
