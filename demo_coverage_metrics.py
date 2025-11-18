"""
Demo: Coverage Metrics and Reporting
Demonstrates test coverage tracking and reporting
"""
from src.metrics.coverage_tracker import CoverageTracker
from src.metrics.coverage_reporter import CoverageReporter

# Simple logger
class SimpleLogger:
    def info(self, msg, **kwargs): print(f"INFO: {msg}")
    def warning(self, msg, **kwargs): print(f"WARN: {msg}")
    def error(self, msg, **kwargs): print(f"ERROR: {msg}")
    def debug(self, msg, **kwargs): pass

logger = SimpleLogger()


def create_sample_endpoints():
    """Create sample API endpoints"""
    return [
        {
            "method": "GET",
            "path": "/api/users",
            "parameters": {"page": {}, "limit": {}, "search": {}},
            "responses": {"200": {}, "401": {}, "500": {}}
        },
        {
            "method": "POST",
            "path": "/api/users",
            "parameters": {"email": {}, "name": {}, "age": {}},
            "responses": {"201": {}, "400": {}, "401": {}, "422": {}}
        },
        {
            "method": "GET",
            "path": "/api/users/{id}",
            "parameters": {},
            "responses": {"200": {}, "404": {}, "401": {}}
        },
        {
            "method": "PUT",
            "path": "/api/users/{id}",
            "parameters": {"email": {}, "name": {}, "age": {}},
            "responses": {"200": {}, "400": {}, "404": {}, "422": {}}
        },
        {
            "method": "DELETE",
            "path": "/api/users/{id}",
            "parameters": {},
            "responses": {"204": {}, "404": {}, "401": {}}
        },
        {
            "method": "GET",
            "path": "/api/products",
            "parameters": {"category": {}, "sort": {}},
            "responses": {"200": {}, "401": {}}
        }
    ]


def simulate_test_execution(tracker):
    """Simulate some test execution"""
    logger.info("Simulating test execution...")
    logger.info("")

    # Test 1: GET /api/users (successful)
    tracker.record_test(
        endpoint_key="GET /api/users",
        status_code=200,
        parameters_tested=["page", "limit"],
        scenario_type="positive",
        passed=True
    )

    # Test 2: GET /api/users (unauthorized)
    tracker.record_test(
        endpoint_key="GET /api/users",
        status_code=401,
        parameters_tested=[],
        scenario_type="negative",
        passed=True
    )

    # Test 3: POST /api/users (successful)
    tracker.record_test(
        endpoint_key="POST /api/users",
        status_code=201,
        parameters_tested=["email", "name", "age"],
        scenario_type="positive",
        passed=True
    )

    # Test 4: POST /api/users (validation error)
    tracker.record_test(
        endpoint_key="POST /api/users",
        status_code=422,
        parameters_tested=["email"],
        scenario_type="negative",
        passed=True
    )

    # Test 5: GET /api/users/{id} (successful)
    tracker.record_test(
        endpoint_key="GET /api/users/{id}",
        status_code=200,
        parameters_tested=[],
        scenario_type="positive",
        passed=True
    )

    # Test 6: GET /api/users/{id} (not found)
    tracker.record_test(
        endpoint_key="GET /api/users/{id}",
        status_code=404,
        parameters_tested=[],
        scenario_type="negative",
        passed=True
    )

    # Test 7: PUT /api/users/{id} (successful)
    tracker.record_test(
        endpoint_key="PUT /api/users/{id}",
        status_code=200,
        parameters_tested=["name"],
        scenario_type="positive",
        passed=True
    )

    # Test 8: DELETE /api/users/{id} (successful)
    tracker.record_test(
        endpoint_key="DELETE /api/users/{id}",
        status_code=204,
        parameters_tested=[],
        scenario_type="positive",
        passed=True
    )

    # Note: /api/products not tested yet

    logger.info(f"Executed {tracker.coverage.total_tests_run} tests")
    logger.info("")


def demo_coverage_tracking():
    """Demo: Basic coverage tracking"""
    logger.info("=" * 80)
    logger.info("DEMO: COVERAGE TRACKING")
    logger.info("=" * 80)
    logger.info("")

    # Create tracker
    tracker = CoverageTracker(session_id="demo-session")

    # Register endpoints
    endpoints = create_sample_endpoints()
    tracker.register_endpoints(endpoints)

    logger.info(f"Registered {len(endpoints)} endpoints:")
    for ep in endpoints:
        logger.info(f"   • {ep['method']} {ep['path']}")
    logger.info("")

    # Simulate test execution
    simulate_test_execution(tracker)

    # Get summary
    summary = tracker.get_coverage_summary()

    logger.info("Coverage Summary:")
    logger.info(f"   Overall Coverage: {summary['overall_coverage']:.1f}%")
    logger.info(f"   Endpoint Coverage: {summary['endpoint_coverage']:.1f}%")
    logger.info(f"   Parameter Coverage: {summary['parameter_coverage']:.1f}%")
    logger.info(f"   Status Code Coverage: {summary['status_code_coverage']:.1f}%")
    logger.info("")

    logger.info(f"Endpoints: {summary['endpoints']['tested']}/{summary['endpoints']['total']} tested")
    logger.info(f"Tests: {summary['tests']['total']} total, {summary['tests']['passed']} passed")
    logger.info("")

    return tracker


def demo_endpoint_details():
    """Demo: Endpoint-level coverage details"""
    logger.info("=" * 80)
    logger.info("DEMO: ENDPOINT-LEVEL DETAILS")
    logger.info("=" * 80)
    logger.info("")

    # Create and populate tracker
    tracker = CoverageTracker(session_id="demo-session-2")
    endpoints = create_sample_endpoints()
    tracker.register_endpoints(endpoints)
    simulate_test_execution(tracker)

    # Show details for specific endpoint
    endpoint_key = "POST /api/users"
    details = tracker.get_endpoint_details(endpoint_key)

    logger.info(f"Details for: {endpoint_key}")
    logger.info("")

    logger.info(f"Parameter Coverage: {details['parameter_coverage']:.1f}%")
    logger.info(f"   Total parameters: {details['parameters']['total']}")
    logger.info(f"   Tested: {', '.join(details['parameters']['tested'])}")
    if details['parameters']['untested']:
        logger.info(f"   Untested: {', '.join(details['parameters']['untested'])}")
    logger.info("")

    logger.info(f"Status Code Coverage: {details['status_code_coverage']:.1f}%")
    logger.info(f"   Documented: {details['status_codes']['documented']}")
    logger.info(f"   Tested: {details['status_codes']['tested']}")
    if details['status_codes']['untested']:
        logger.info(f"   Untested: {details['status_codes']['untested']}")
    logger.info("")

    logger.info(f"Scenarios: {details['scenarios']['count']} types")
    logger.info(f"   Types: {', '.join(details['scenarios']['types'])}")
    logger.info("")


def demo_coverage_gaps():
    """Demo: Identify coverage gaps"""
    logger.info("=" * 80)
    logger.info("DEMO: COVERAGE GAPS")
    logger.info("=" * 80)
    logger.info("")

    # Create and populate tracker
    tracker = CoverageTracker(session_id="demo-session-3")
    endpoints = create_sample_endpoints()
    tracker.register_endpoints(endpoints)
    simulate_test_execution(tracker)

    # Get gaps
    gaps = tracker.get_coverage_gaps()

    logger.info("Coverage Gaps:")
    logger.info("")

    if gaps['untested_endpoints']:
        logger.info(f"⚠️  Untested Endpoints ({len(gaps['untested_endpoints'])}):")
        for endpoint in gaps['untested_endpoints']:
            logger.info(f"   • {endpoint}")
        logger.info("")

    if gaps['low_parameter_coverage']:
        logger.info(f"⚠️  Low Parameter Coverage ({len(gaps['low_parameter_coverage'])}):")
        for item in gaps['low_parameter_coverage']:
            logger.info(f"   • {item['endpoint']}: {item['coverage']:.0f}%")
        logger.info("")

    if gaps['missing_status_codes']:
        logger.info(f"⚠️  Missing Status Codes ({len(gaps['missing_status_codes'])}):")
        for item in gaps['missing_status_codes']:
            logger.info(f"   • {item['endpoint']}: {item['missing_codes']}")
        logger.info("")

    if gaps['low_scenario_coverage']:
        logger.info(f"⚠️  Low Scenario Coverage ({len(gaps['low_scenario_coverage'])}):")
        for item in gaps['low_scenario_coverage']:
            logger.info(f"   • {item['endpoint']}: {item['scenario_count']} scenarios")
        logger.info("")


def demo_coverage_report():
    """Demo: Generate full coverage report"""
    logger.info("=" * 80)
    logger.info("DEMO: FULL COVERAGE REPORT")
    logger.info("=" * 80)
    logger.info("")

    # Create and populate tracker
    tracker = CoverageTracker(session_id="demo-session-4")
    endpoints = create_sample_endpoints()
    tracker.register_endpoints(endpoints)
    simulate_test_execution(tracker)
    tracker.finalize()

    # Generate report
    reporter = CoverageReporter(tracker)

    logger.info("Generating comprehensive coverage report...")
    logger.info("")

    # Print full report
    reporter.print_report()


def demo_progress_bars():
    """Demo: Progress bar visualization"""
    logger.info("=" * 80)
    logger.info("DEMO: PROGRESS BAR VISUALIZATION")
    logger.info("=" * 80)
    logger.info("")

    # Create reporter with sample data
    tracker = CoverageTracker(session_id="demo-session-5")
    endpoints = create_sample_endpoints()
    tracker.register_endpoints(endpoints)
    simulate_test_execution(tracker)

    reporter = CoverageReporter(tracker)

    # Show progress bars for different coverage levels
    logger.info("Coverage Progress Bars:")
    logger.info("")

    percentages = [25, 50, 75, 90, 100]

    for pct in percentages:
        logger.info(f"Coverage: {pct}%")
        logger.info(reporter._create_progress_bar(pct))
        logger.info("")


def main():
    """Run all coverage metrics demos"""
    logger.info("=" * 80)
    logger.info("COVERAGE METRICS DEMO")
    logger.info("=" * 80)
    logger.info("")

    # Demo 1: Basic coverage tracking
    demo_coverage_tracking()

    # Demo 2: Endpoint-level details
    demo_endpoint_details()

    # Demo 3: Coverage gaps
    demo_coverage_gaps()

    # Demo 4: Progress bars
    demo_progress_bars()

    # Demo 5: Full coverage report
    demo_coverage_report()

    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("DEMO COMPLETE")
    logger.info("=" * 80)
    logger.info("")

    logger.info("✅ Coverage metrics features demonstrated:")
    logger.info("   1. Coverage tracking across dimensions")
    logger.info("   2. Endpoint-level detailed metrics")
    logger.info("   3. Coverage gap identification")
    logger.info("   4. Progress bar visualization")
    logger.info("   5. Comprehensive reporting")
    logger.info("")

    logger.info("📊 Coverage dimensions tracked:")
    logger.info("   • Endpoint coverage (which endpoints tested)")
    logger.info("   • Parameter coverage (which parameters tested)")
    logger.info("   • Status code coverage (which codes triggered)")
    logger.info("   • Scenario coverage (which test types run)")
    logger.info("")

    logger.info("🎯 Integration with TestRunner:")
    logger.info("   runner = TestRunner(...)")
    logger.info("   # Run tests and collect results")
    logger.info("   report = await runner.generate_coverage_report(")
    logger.info("       endpoints=endpoints,")
    logger.info("       test_results=results")
    logger.info("   )")
    logger.info("")

    logger.info("📈 Benefits:")
    logger.info("   ✓ Know exactly what has been tested")
    logger.info("   ✓ Identify coverage gaps")
    logger.info("   ✓ Track progress over time")
    logger.info("   ✓ Prioritize untested areas")
    logger.info("   ✓ Generate compliance reports")
    logger.info("")

    logger.info("📋 Report sections:")
    logger.info("   • Summary statistics with overall coverage")
    logger.info("   • Coverage breakdown by dimension")
    logger.info("   • Endpoint-level details")
    logger.info("   • Coverage gaps and warnings")
    logger.info("   • Actionable recommendations")
    logger.info("")


if __name__ == "__main__":
    main()
