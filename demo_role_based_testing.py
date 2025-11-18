"""
Demo: Role-Based Access Control (RBAC) Testing
Demonstrates testing endpoints with different user roles
"""
from src.testing.role_based_scenario_generator import (
    RoleBasedScenarioGenerator,
    UserRole,
    AccessLevel
)

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
        # User management (admin only for modifications)
        {
            "path": "/api/users",
            "method": "GET",
            "description": "List all users"
        },
        {
            "path": "/api/users",
            "method": "POST",
            "description": "Create a new user (admin only)"
        },
        {
            "path": "/api/users/{id}",
            "method": "GET",
            "description": "Get a specific user"
        },
        {
            "path": "/api/users/{id}",
            "method": "PUT",
            "description": "Update a user"
        },
        {
            "path": "/api/users/{id}",
            "method": "DELETE",
            "description": "Delete a user (admin only)"
        },
        # Products (public read, authenticated write)
        {
            "path": "/api/products",
            "method": "GET",
            "description": "List products (public)"
        },
        {
            "path": "/api/products",
            "method": "POST",
            "description": "Create product"
        },
        # Orders (user can manage own orders)
        {
            "path": "/api/orders",
            "method": "GET",
            "description": "List own orders"
        },
        {
            "path": "/api/orders",
            "method": "POST",
            "description": "Create order"
        },
    ]


def main():
    """Run role-based access control testing demo"""
    logger.info("=" * 100)
    logger.info("ROLE-BASED ACCESS CONTROL (RBAC) TESTING DEMO")
    logger.info("=" * 100)
    logger.info("")

    # Step 1: Create sample endpoints
    endpoints = create_sample_endpoints()
    logger.info(f"📊 Created {len(endpoints)} sample endpoints")
    logger.info("")

    # Step 2: Define custom permissions for some endpoints
    logger.info("🔧 Setting up custom permission model...")
    logger.info("")

    custom_permissions = {
        # Public product listing
        "GET /api/products": {
            UserRole.ADMIN: AccessLevel.ALLOWED,
            UserRole.USER: AccessLevel.ALLOWED,
            UserRole.GUEST: AccessLevel.ALLOWED,
            UserRole.UNAUTHENTICATED: AccessLevel.ALLOWED,  # Public!
        },
        # Admin-only user creation
        "POST /api/users": {
            UserRole.ADMIN: AccessLevel.ALLOWED,
            UserRole.USER: AccessLevel.FORBIDDEN,
            UserRole.GUEST: AccessLevel.FORBIDDEN,
            UserRole.UNAUTHENTICATED: AccessLevel.UNAUTHORIZED,
        },
        # Admin-only user deletion
        "DELETE /api/users/{id}": {
            UserRole.ADMIN: AccessLevel.ALLOWED,
            UserRole.USER: AccessLevel.FORBIDDEN,
            UserRole.GUEST: AccessLevel.FORBIDDEN,
            UserRole.UNAUTHENTICATED: AccessLevel.UNAUTHORIZED,
        },
    }

    logger.info("Custom permissions:")
    logger.info("  - GET /api/products: Public (all roles allowed)")
    logger.info("  - POST /api/users: Admin only")
    logger.info("  - DELETE /api/users/{id}: Admin only")
    logger.info("")

    # Step 3: Generate role-based test scenarios
    logger.info("🔄 Generating role-based test scenarios...")
    generator = RoleBasedScenarioGenerator(custom_permissions=custom_permissions)

    scenarios = generator.generate_all_role_scenarios(endpoints)

    # Step 4: Show summary
    summary = generator.get_summary(scenarios)
    logger.info(f"   Total scenarios generated: {summary['total_scenarios']}")
    logger.info(f"   Unique roles: {summary['unique_roles']}")
    logger.info("")

    logger.info("📊 Scenarios by role:")
    for role, count in summary['by_role'].items():
        logger.info(f"   {role}: {count} scenarios")
    logger.info("")

    logger.info("📊 Scenarios by access level:")
    for access, count in summary['by_access_level'].items():
        logger.info(f"   {access}: {count} scenarios")
    logger.info("")

    # Step 5: Show permission matrix
    logger.info("=" * 100)
    logger.info("PERMISSION MATRIX VISUALIZATION")
    logger.info("=" * 100)
    logger.info("")

    permission_matrix_viz = generator.visualize_permission_matrix(endpoints)
    logger.info(permission_matrix_viz)
    logger.info("")

    # Step 6: Show sample scenarios for each role
    logger.info("=" * 100)
    logger.info("SAMPLE SCENARIOS BY ROLE")
    logger.info("=" * 100)
    logger.info("")

    for role in UserRole:
        role_scenarios = generator.get_scenarios_by_role(scenarios, role)
        logger.info(f"\n{role.value.upper()} ROLE ({len(role_scenarios)} scenarios):")
        logger.info("-" * 100)

        for i, scenario in enumerate(role_scenarios[:5], 1):  # Show first 5
            access_icon = {
                AccessLevel.ALLOWED: "✅",
                AccessLevel.FORBIDDEN: "🚫",
                AccessLevel.UNAUTHORIZED: "🔒"
            }.get(scenario.access_level, "❓")

            logger.info(
                f"{i}. {access_icon} {scenario.method:6} {scenario.path:30} "
                f"→ Expected: {scenario.expected_status_codes}"
            )
            logger.info(f"   {scenario.description}")

        if len(role_scenarios) > 5:
            logger.info(f"   ... and {len(role_scenarios) - 5} more scenarios")

    # Step 7: Show scenarios by access level
    logger.info("\n\n" + "=" * 100)
    logger.info("SCENARIOS BY ACCESS LEVEL")
    logger.info("=" * 100)
    logger.info("")

    for access_level in AccessLevel:
        access_scenarios = generator.get_scenarios_by_access_level(scenarios, access_level)

        if access_scenarios:
            icon = {
                AccessLevel.ALLOWED: "✅",
                AccessLevel.FORBIDDEN: "🚫",
                AccessLevel.UNAUTHORIZED: "🔒"
            }.get(access_level, "❓")

            logger.info(f"\n{icon} {access_level.value.upper()} ({len(access_scenarios)} scenarios):")

            # Group by endpoint
            by_endpoint = {}
            for s in access_scenarios:
                if s.endpoint_key not in by_endpoint:
                    by_endpoint[s.endpoint_key] = []
                by_endpoint[s.endpoint_key].append(s.role.value)

            for endpoint, roles in list(by_endpoint.items())[:5]:  # Show first 5
                logger.info(f"   {endpoint}: {', '.join(roles)}")

            if len(by_endpoint) > 5:
                logger.info(f"   ... and {len(by_endpoint) - 5} more endpoints")

    # Step 8: Show potential security issues
    logger.info("\n\n" + "=" * 100)
    logger.info("SECURITY TESTING SCENARIOS")
    logger.info("=" * 100)
    logger.info("")

    logger.info("🔒 Testing for common security vulnerabilities:")
    logger.info("")

    # Privilege escalation tests
    logger.info("1. PRIVILEGE ESCALATION TESTS")
    logger.info("   Testing if regular users can access admin-only endpoints...")
    admin_only = [s for s in scenarios if s.access_level == AccessLevel.FORBIDDEN and s.role in [UserRole.USER, UserRole.GUEST]]
    logger.info(f"   Generated {len(admin_only)} tests to detect privilege escalation")
    for scenario in admin_only[:3]:
        logger.info(f"   - {scenario.role.value} → {scenario.endpoint_key} (expect 403)")
    logger.info("")

    # Missing authentication tests
    logger.info("2. MISSING AUTHENTICATION TESTS")
    logger.info("   Testing if unauthenticated users are properly blocked...")
    unauth_tests = [s for s in scenarios if s.role == UserRole.UNAUTHENTICATED and s.access_level == AccessLevel.UNAUTHORIZED]
    logger.info(f"   Generated {len(unauth_tests)} tests to detect missing authentication")
    for scenario in unauth_tests[:3]:
        logger.info(f"   - unauthenticated → {scenario.endpoint_key} (expect 401)")
    logger.info("")

    # Authorization tests
    logger.info("3. AUTHORIZATION TESTS")
    logger.info("   Testing if authenticated users have proper access...")
    allowed_tests = [s for s in scenarios if s.access_level == AccessLevel.ALLOWED]
    logger.info(f"   Generated {len(allowed_tests)} tests to verify proper access")
    logger.info("")

    # Summary
    logger.info("=" * 100)
    logger.info("DEMO COMPLETE")
    logger.info("=" * 100)
    logger.info("")
    logger.info("✅ Successfully generated role-based access control test scenarios!")
    logger.info(f"📊 Total: {summary['total_scenarios']} scenarios across {summary['unique_roles']} roles")
    logger.info("")

    logger.info("💡 What happens during execution:")
    logger.info("   1. Each scenario is executed with appropriate role credentials")
    logger.info("   2. Actual response status is compared to expected access level")
    logger.info("   3. Permission violations are detected and classified by severity")
    logger.info("   4. Security report is generated with:")
    logger.info("      - Privilege escalation attempts")
    logger.info("      - Missing authentication checks")
    logger.info("      - Over-restriction issues")
    logger.info("   5. Comprehensive RBAC compliance report")
    logger.info("")

    logger.info("📈 Security benefits:")
    logger.info("   - Detects privilege escalation vulnerabilities")
    logger.info("   - Ensures proper authentication enforcement")
    logger.info("   - Validates role-based access control")
    logger.info("   - Identifies over-restrictive permissions")
    logger.info("   - Generates permission compliance reports")
    logger.info("")


if __name__ == "__main__":
    main()
