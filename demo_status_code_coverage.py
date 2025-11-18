"""
Demo: Status Code Coverage Testing
Demonstrates generating test scenarios for all documented HTTP status codes
"""
from src.testing.status_code_scenario_generator import StatusCodeScenarioGenerator

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
            "path": "/api/users",
            "method": "GET",
            "description": "List all users",
            "auth_required": True
        },
        {
            "path": "/api/users",
            "method": "POST",
            "description": "Create a new user",
            "auth_required": True
        },
        {
            "path": "/api/users/{id}",
            "method": "GET",
            "description": "Get a specific user",
            "auth_required": True
        },
        {
            "path": "/api/users/{id}",
            "method": "PUT",
            "description": "Update a user",
            "auth_required": True
        },
        {
            "path": "/api/users/{id}",
            "method": "DELETE",
            "description": "Delete a user",
            "auth_required": True
        },
        {
            "path": "/api/products",
            "method": "POST",
            "description": "Create a product",
            "auth_required": True
        },
        {
            "path": "/api/products/{id}",
            "method": "GET",
            "description": "Get a product",
            "auth_required": False
        },
    ]


def main():
    """Run status code coverage demo"""
    logger.info("=" * 80)
    logger.info("STATUS CODE COVERAGE TESTING DEMO")
    logger.info("=" * 80)
    logger.info("")

    # Step 1: Create sample endpoints
    endpoints = create_sample_endpoints()
    logger.info(f"📊 Created {len(endpoints)} sample endpoints")
    logger.info("")

    # Step 2: Define documented status codes for endpoints
    documented_responses = {
        "GET /api/users": [200, 401, 403],
        "POST /api/users": [201, 400, 401, 403, 422, 409],
        "GET /api/users/{id}": [200, 404, 401, 403],
        "PUT /api/users/{id}": [200, 404, 400, 401, 403, 422],
        "DELETE /api/users/{id}": [204, 404, 401, 403],
        "POST /api/products": [201, 400, 422, 409],
        "GET /api/products/{id}": [200, 404],
    }

    logger.info("📋 Documented status codes:")
    for endpoint, codes in documented_responses.items():
        logger.info(f"   {endpoint}: {codes}")
    logger.info("")

    # Step 3: Generate status code scenarios
    logger.info("🔧 Generating status code test scenarios...")
    generator = StatusCodeScenarioGenerator(documented_responses)

    scenarios = generator.generate_all_scenarios(
        endpoints,
        documented_responses
    )

    # Step 4: Show summary
    summary = generator.get_summary(scenarios)
    logger.info(f"   Total scenarios generated: {summary['total_scenarios']}")
    logger.info(f"   Unique status codes: {summary['unique_status_codes']}")
    logger.info("")

    logger.info("📊 Scenarios by status code:")
    for code in sorted(summary['by_status_code'].keys()):
        count = summary['by_status_code'][code]
        code_desc = StatusCodeScenarioGenerator.STATUS_CODE_SCENARIOS.get(code, "Unknown")
        logger.info(f"   {code} ({code_desc}): {count} scenarios")
    logger.info("")

    logger.info("📊 Scenarios by type:")
    for stype, count in summary['by_type'].items():
        logger.info(f"   {stype}: {count} scenarios")
    logger.info("")

    # Step 5: Show detailed scenarios for each type
    logger.info("=" * 80)
    logger.info("DETAILED SCENARIO BREAKDOWN")
    logger.info("=" * 80)
    logger.info("")

    # Group scenarios by status code
    for status_code in sorted(summary['by_status_code'].keys()):
        code_scenarios = generator.get_scenarios_by_status_code(scenarios, status_code)

        logger.info(f"\n{status_code} - {StatusCodeScenarioGenerator.STATUS_CODE_SCENARIOS.get(status_code, 'Unknown')}")
        logger.info(f"{'=' * 80}")

        for i, scenario in enumerate(code_scenarios[:5], 1):  # Show first 5 per code
            logger.info(f"\n{i}. {scenario.description}")
            logger.info(f"   Endpoint: {scenario.endpoint_key}")
            logger.info(f"   Type: {scenario.scenario_type}")
            logger.info(f"   Expected behavior: {scenario.expected_behavior}")

            if scenario.path_modifications:
                logger.info(f"   Path modifications: {scenario.path_modifications}")

            if scenario.payload:
                logger.info(f"   Payload sample: {list(scenario.payload.keys())[:3]}")

            if scenario.headers:
                logger.info(f"   Headers: {list(scenario.headers.keys())}")

        if len(code_scenarios) > 5:
            logger.info(f"\n   ... and {len(code_scenarios) - 5} more scenarios for {status_code}")

    # Step 6: Show specific scenario types
    logger.info("\n\n" + "=" * 80)
    logger.info("SCENARIO TYPE EXAMPLES")
    logger.info("=" * 80)

    scenario_types = ['success', 'client_error', 'auth_error', 'not_found', 'validation_error']

    for stype in scenario_types:
        type_scenarios = generator.get_scenarios_by_type(scenarios, stype)
        if type_scenarios:
            logger.info(f"\n{stype.upper().replace('_', ' ')} ({len(type_scenarios)} scenarios):")
            for scenario in type_scenarios[:3]:  # Show first 3
                logger.info(f"   - {scenario.endpoint_key}: {scenario.description}")

    # Summary
    logger.info("\n\n" + "=" * 80)
    logger.info("DEMO COMPLETE")
    logger.info("=" * 80)
    logger.info("")
    logger.info("✅ Successfully generated status code test scenarios!")
    logger.info(f"📊 Total: {summary['total_scenarios']} scenarios covering {summary['unique_status_codes']} status codes")
    logger.info("")

    logger.info("💡 What happens during execution:")
    logger.info("   1. Each scenario is executed against the real API")
    logger.info("   2. Actual status code is compared to expected")
    logger.info("   3. Coverage is calculated (tested vs documented codes)")
    logger.info("   4. Missing scenarios are identified")
    logger.info("   5. Comprehensive coverage report is generated")
    logger.info("")

    logger.info("📈 Expected coverage metrics:")
    total_documented = sum(len(codes) for codes in documented_responses.values())
    logger.info(f"   Total documented status codes: {total_documented}")
    logger.info(f"   Scenarios generated: {summary['total_scenarios']}")
    logger.info(f"   Coverage when all pass: 100%")
    logger.info("")


if __name__ == "__main__":
    main()
