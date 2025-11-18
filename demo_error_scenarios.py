"""
Demo: Error Scenario Testing
Demonstrates validating error response quality and consistency
"""
from src.testing.error_scenario_generator import ErrorScenarioGenerator, ErrorCondition, ErrorCategory

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
            "auth_required": True,
            "parameters": {
                "email": {"type": "string", "format": "email", "required": True},
                "name": {"type": "string", "required": True},
                "age": {"type": "integer", "min": 0, "max": 150}
            }
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
            "auth_required": True,
            "parameters": {
                "email": {"type": "string", "format": "email"},
                "name": {"type": "string"},
                "age": {"type": "integer", "min": 0, "max": 150}
            }
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
            "auth_required": True,
            "parameters": {
                "name": {"type": "string", "required": True},
                "price": {"type": "number", "min": 0},
                "quantity": {"type": "integer", "min": 0}
            }
        }
    ]


def main():
    """Run error scenario testing demo"""
    logger.info("=" * 80)
    logger.info("ERROR SCENARIO TESTING DEMO")
    logger.info("=" * 80)
    logger.info("")

    # Step 1: Create sample endpoints
    endpoints = create_sample_endpoints()
    logger.info(f"📊 Created {len(endpoints)} sample endpoints")
    logger.info("")

    # Step 2: Show common error conditions
    logger.info("📋 Common Error Conditions:")
    logger.info("")

    conditions_by_category = {}
    for condition in ErrorScenarioGenerator.COMMON_ERROR_CONDITIONS:
        cat = condition.category.value
        if cat not in conditions_by_category:
            conditions_by_category[cat] = []
        conditions_by_category[cat].append(condition)

    for category, conditions in conditions_by_category.items():
        logger.info(f"\n{category.upper()} ({len(conditions)} conditions):")
        for cond in conditions:
            logger.info(f"   • {cond.condition_name}")
            logger.info(f"     Status: {cond.expected_status_code}")
            logger.info(f"     Trigger: {cond.trigger}")
            logger.info(f"     Required fields: {', '.join(cond.expected_fields)}")

    logger.info("")
    logger.info("")

    # Step 3: Generate error scenarios
    logger.info("🔧 Generating error scenarios...")
    generator = ErrorScenarioGenerator()

    all_scenarios = generator.generate_all_error_scenarios(endpoints)

    # Step 4: Show summary
    summary = generator.get_summary(all_scenarios)
    logger.info(f"   Total scenarios generated: {summary['total_scenarios']}")
    logger.info(f"   Unique categories: {summary['unique_categories']}")
    logger.info(f"   Unique status codes: {summary['unique_status_codes']}")
    logger.info("")

    logger.info("📊 Scenarios by category:")
    for category, count in summary['by_category'].items():
        logger.info(f"   {category}: {count} scenarios")
    logger.info("")

    logger.info("📊 Scenarios by status code:")
    for code, count in sorted(summary['by_status_code'].items()):
        logger.info(f"   {code}: {count} scenarios")
    logger.info("")

    # Step 5: Show detailed scenarios for each category
    logger.info("=" * 80)
    logger.info("DETAILED SCENARIO BREAKDOWN")
    logger.info("=" * 80)
    logger.info("")

    for category in ErrorCategory:
        category_scenarios = generator.get_scenarios_by_category(all_scenarios, category)

        if category_scenarios:
            logger.info(f"\n{category.value.upper()} ERRORS ({len(category_scenarios)} scenarios)")
            logger.info("=" * 80)

            for i, scenario in enumerate(category_scenarios[:3], 1):  # Show first 3
                logger.info(f"\n{i}. {scenario.error_condition.condition_name}")
                logger.info(f"   Endpoint: {scenario.endpoint_key}")
                logger.info(f"   Expected Status: {scenario.error_condition.expected_status_code}")
                logger.info(f"   Description: {scenario.error_condition.description}")
                logger.info(f"   How to trigger: {scenario.error_condition.trigger}")

                if scenario.trigger_payload:
                    logger.info(f"   Trigger payload: {scenario.trigger_payload}")

                if scenario.trigger_headers:
                    logger.info(f"   Trigger headers: {list(scenario.trigger_headers.keys())}")

                if scenario.path_modifications:
                    logger.info(f"   Path modifications: {scenario.path_modifications}")

            if len(category_scenarios) > 3:
                logger.info(f"\n   ... and {len(category_scenarios) - 3} more {category.value} scenarios")

    # Step 6: Show validation error examples
    logger.info("\n\n" + "=" * 80)
    logger.info("VALIDATION ERROR EXAMPLES")
    logger.info("=" * 80)

    validation_scenarios = generator.get_scenarios_by_category(all_scenarios, ErrorCategory.VALIDATION)

    if validation_scenarios:
        logger.info("\nThese scenarios test that validation errors provide helpful feedback:")
        logger.info("")

        for scenario in validation_scenarios[:5]:
            logger.info(f"• {scenario.error_condition.condition_name}")
            logger.info(f"  Expected: {scenario.error_condition.expected_status_code}")
            logger.info(f"  Required response fields: {', '.join(scenario.error_condition.expected_fields)}")
            logger.info("")

    # Step 7: Show authentication/authorization examples
    logger.info("=" * 80)
    logger.info("AUTHENTICATION & AUTHORIZATION EXAMPLES")
    logger.info("=" * 80)

    auth_scenarios = generator.get_scenarios_by_category(all_scenarios, ErrorCategory.AUTHENTICATION)
    authz_scenarios = generator.get_scenarios_by_category(all_scenarios, ErrorCategory.AUTHORIZATION)

    if auth_scenarios:
        logger.info(f"\nAuthentication Tests ({len(auth_scenarios)} scenarios):")
        for scenario in auth_scenarios[:3]:
            logger.info(f"   • {scenario.error_condition.condition_name}")
            logger.info(f"     Expected: {scenario.error_condition.expected_status_code}")
            if scenario.trigger_headers:
                logger.info(f"     Headers: {scenario.trigger_headers}")

    if authz_scenarios:
        logger.info(f"\nAuthorization Tests ({len(authz_scenarios)} scenarios):")
        for scenario in authz_scenarios[:3]:
            logger.info(f"   • {scenario.error_condition.condition_name}")
            logger.info(f"     Expected: {scenario.error_condition.expected_status_code}")

    # Step 8: Show error quality checks
    logger.info("\n\n" + "=" * 80)
    logger.info("ERROR QUALITY VALIDATION")
    logger.info("=" * 80)
    logger.info("")

    logger.info("When scenarios are executed, the ErrorResponseValidator checks:")
    logger.info("")
    logger.info("✅ Quality Checks:")
    logger.info("   1. Message is not generic (not 'an error occurred', 'something went wrong')")
    logger.info("   2. Message is not empty or too short (min 5 characters)")
    logger.info("   3. For validation errors: field name is included")
    logger.info("   4. Error details are provided")
    logger.info("   5. For range errors: min/max constraints are specified")
    logger.info("   6. Message is properly capitalized")
    logger.info("")

    logger.info("📊 Quality Scoring:")
    logger.info("   • High Quality (≥70%): Specific, helpful error messages")
    logger.info("   • Medium Quality (40-70%): Some issues, but usable")
    logger.info("   • Low Quality (<40%): Generic or missing information")
    logger.info("")

    # Summary
    logger.info("=" * 80)
    logger.info("DEMO COMPLETE")
    logger.info("=" * 80)
    logger.info("")
    logger.info("✅ Successfully generated error test scenarios!")
    logger.info(f"📊 Total: {summary['total_scenarios']} scenarios covering {summary['unique_status_codes']} error codes")
    logger.info("")

    logger.info("💡 What happens during execution:")
    logger.info("   1. Each scenario is executed against the real API")
    logger.info("   2. Actual response is validated for:")
    logger.info("      • Correct status code")
    logger.info("      • Required fields present")
    logger.info("      • Message quality (helpful, specific)")
    logger.info("      • Consistent error format")
    logger.info("   3. Quality score is calculated (0.0-1.0)")
    logger.info("   4. Issues are identified and categorized")
    logger.info("   5. Comprehensive quality report is generated")
    logger.info("")

    logger.info("📈 Example quality report sections:")
    logger.info("   • Overall quality distribution")
    logger.info("   • Common quality issues")
    logger.info("   • Low quality errors needing improvement")
    logger.info("   • Detailed issue breakdown with recommendations")
    logger.info("")

    logger.info("🎯 Benefits:")
    logger.info("   ✓ Ensures error messages are helpful to developers")
    logger.info("   ✓ Validates error response consistency")
    logger.info("   ✓ Identifies missing or generic error messages")
    logger.info("   ✓ Tests all documented error conditions")
    logger.info("   ✓ Improves API developer experience")
    logger.info("")


if __name__ == "__main__":
    main()
