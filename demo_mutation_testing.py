#!/usr/bin/env python3
"""
Mutation Testing Demo
Demonstrates security mutation testing with OWASP Top 10 patterns
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Optional logger
try:
    from loguru import logger
except ImportError:
    class MockLogger:
        def info(self, msg, **kwargs): print(f"INFO: {msg}")
        def warning(self, msg, **kwargs): print(f"WARN: {msg}")
        def error(self, msg, **kwargs): print(f"ERROR: {msg}")
    logger = MockLogger()

from src.testing.security_patterns import SecurityPatterns, SecurityPattern
from src.testing.mutation_test_generator import MutationTestGenerator


def print_header(title: str):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_section(title: str):
    """Print formatted section"""
    print(f"\n--- {title} ---\n")


def demonstrate_security_patterns():
    """Demonstrate available security patterns"""
    print_header("🛡️  SECURITY PATTERNS (OWASP Top 10)")

    patterns = SecurityPatterns.get_all_patterns()

    print(f"Total patterns available: {len(patterns)}\n")

    # Group by severity
    by_severity = {}
    for pattern in patterns:
        if pattern.severity not in by_severity:
            by_severity[pattern.severity] = []
        by_severity[pattern.severity].append(pattern)

    for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        if severity in by_severity:
            print(f"\n{severity} Severity ({len(by_severity[severity])} patterns):")
            for pattern in by_severity[severity]:
                print(f"  • {pattern.name} ({pattern.cwe_id})")
                print(f"    Category: {pattern.category}")
                print(f"    Payloads: {len(pattern.payloads)}")
                print(f"    Description: {pattern.description[:80]}...")
                print()


def demonstrate_pattern_selection():
    """Demonstrate intelligent pattern selection based on parameter types"""
    print_header("🎯 INTELLIGENT PATTERN SELECTION")

    test_parameters = [
        {'name': 'username', 'type': 'string'},
        {'name': 'age', 'type': 'integer'},
        {'name': 'email', 'type': 'email'},
        {'name': 'redirect_url', 'type': 'url'},
        {'name': 'file_path', 'type': 'string'},
        {'name': 'user_data', 'type': 'object'},
        {'name': 'query', 'type': 'string'},
    ]

    patterns_obj = SecurityPatterns()

    for param in test_parameters:
        print(f"Parameter: {param['name']} ({param['type']})")

        relevant_patterns = patterns_obj.get_patterns_for_parameter_type(
            param['type'],
            param['name']
        )

        print(f"  Recommended patterns: {len(relevant_patterns)}")
        for pattern in relevant_patterns:
            print(f"    • {pattern.name} ({pattern.severity})")

        print()


def demonstrate_mutation_test_generation():
    """Demonstrate mutation test generation for an endpoint"""
    print_header("🧪 MUTATION TEST GENERATION")

    # Sample API endpoint
    endpoint = {
        'path': '/api/users',
        'method': 'POST',
        'parameters': [
            {'name': 'email', 'type': 'email', 'required': True},
            {'name': 'username', 'type': 'string', 'required': True},
            {'name': 'age', 'type': 'integer', 'required': False},
            {'name': 'redirect_url', 'type': 'url', 'required': False},
        ]
    }

    print(f"Endpoint: {endpoint['method']} {endpoint['path']}")
    print(f"Parameters: {len(endpoint['parameters'])}")
    print()

    generator = MutationTestGenerator(max_tests_per_pattern=2)

    # Get summary first
    print_section("Test Generation Summary")
    summary = generator.get_mutation_summary(endpoint)

    print(f"Total security tests: {summary['total_tests']}")
    print(f"\nBy severity:")
    for severity, count in summary['by_severity'].items():
        print(f"  {severity}: {count}")

    print(f"\nBy pattern:")
    for pattern_name, count in summary['by_pattern'].items():
        print(f"  {pattern_name}: {count}")

    print(f"\nBy parameter:")
    for param_name, count in summary['by_parameter'].items():
        print(f"  {param_name}: {count}")

    # Generate actual tests
    print_section("Generated Security Tests")

    tests = generator.generate_mutation_tests(endpoint)

    print(f"\nGenerated {len(tests)} security mutation tests:\n")

    # Show first 5 tests in detail
    for i, test in enumerate(tests[:5], 1):
        print(f"Test #{i}: {test['name']}")
        print(f"  Type: {test['type']}")
        print(f"  Severity: {test['severity']} ({test['cwe_id']})")
        print(f"  Target: {test['target_parameter']}")
        print(f"  Pattern: {test['security_pattern']}")
        print(f"  Expected: {test['expected_status']} ({test['expected_behavior']})")
        print(f"  Attack payload: {test['attack_payload'][:60]}...")
        print()

    # Group tests by severity
    critical_tests = [t for t in tests if t['severity'] == 'CRITICAL']
    high_tests = [t for t in tests if t['severity'] == 'HIGH']
    medium_tests = [t for t in tests if t['severity'] == 'MEDIUM']

    print("\nTest distribution:")
    print(f"  CRITICAL: {len(critical_tests)}")
    print(f"  HIGH: {len(high_tests)}")
    print(f"  MEDIUM: {len(medium_tests)}")


def demonstrate_vulnerability_detection():
    """Demonstrate vulnerability detection from test results"""
    print_header("🔍 VULNERABILITY DETECTION")

    generator = MutationTestGenerator()

    # Test case: SQL Injection
    sql_injection_test = {
        'name': "SQL Injection Test",
        'severity': 'CRITICAL',
        'security_pattern': 'SQL Injection',
        'cwe_id': 'CWE-89',
        'expected_status': 400,
        'vulnerability_indicators': ['SQL syntax', 'mysql_fetch', 'syntax error'],
    }

    # Scenario 1: Vulnerable API (accepts malicious input)
    print_section("Scenario 1: Vulnerable API")

    vulnerable_response = {
        'status_code': 200,
        'body': '{"id": 1, "message": "User created"}',
        'headers': {},
    }

    analysis = generator.analyze_mutation_test_result(
        sql_injection_test,
        vulnerable_response
    )

    print("Test Result Analysis:")
    print(f"  Vulnerable: {analysis['vulnerable']}")
    print(f"  Risk Level: {analysis.get('risk_level', 'N/A')}")
    print(f"  Reason: {analysis['reason']}")
    print(f"  Recommendation: {analysis['recommendation']}")
    print()

    # Scenario 2: Error disclosure
    print_section("Scenario 2: Error Disclosure")

    error_disclosure_response = {
        'status_code': 500,
        'body': '''
        SQL syntax error near "' OR '1'='1" at line 1
        Stack trace:
        File "app.py", line 45, in create_user
            cursor.execute("SELECT * FROM users WHERE email = '" + email + "'")
        ''',
        'headers': {},
    }

    analysis = generator.analyze_mutation_test_result(
        sql_injection_test,
        error_disclosure_response
    )

    print("Test Result Analysis:")
    print(f"  Vulnerable: {analysis['vulnerable']}")
    print(f"  Risk Level: {analysis.get('risk_level', 'N/A')}")
    print(f"  Reason: {analysis['reason']}")
    print(f"  Recommendation: {analysis['recommendation']}")
    if 'indicators_found' in analysis.get('evidence', {}):
        print(f"  Indicators Found: {', '.join(analysis['evidence']['indicators_found'])}")
    print()

    # Scenario 3: Secure API (properly rejects)
    print_section("Scenario 3: Secure API")

    secure_response = {
        'status_code': 400,
        'body': '{"error": "Invalid input", "message": "Email validation failed"}',
        'headers': {},
    }

    analysis = generator.analyze_mutation_test_result(
        sql_injection_test,
        secure_response
    )

    print("Test Result Analysis:")
    print(f"  Vulnerable: {analysis['vulnerable']}")
    print(f"  Status: {analysis.get('status', 'N/A')}")
    print(f"  Reason: {analysis['reason']}")
    print(f"  Recommendation: {analysis['recommendation']}")
    print()


def demonstrate_comprehensive_coverage():
    """Demonstrate comprehensive security coverage"""
    print_header("📊 COMPREHENSIVE SECURITY COVERAGE")

    endpoint = {
        'path': '/api/admin/execute',
        'method': 'POST',
        'parameters': [
            {'name': 'command', 'type': 'string', 'required': True},
            {'name': 'target_file', 'type': 'string', 'required': True},
            {'name': 'user_id', 'type': 'integer', 'required': True},
        ]
    }

    print(f"Testing: {endpoint['method']} {endpoint['path']}")
    print("⚠️  This endpoint looks dangerous! Let's security test it.\n")

    generator = MutationTestGenerator(max_tests_per_pattern=3)

    tests = generator.generate_mutation_tests(endpoint)

    # Analyze coverage
    patterns_tested = set(t['security_pattern'] for t in tests)
    categories_tested = set(t['category'] for t in tests)

    print(f"Generated {len(tests)} security tests")
    print(f"\nSecurity patterns tested: {len(patterns_tested)}")
    for pattern in sorted(patterns_tested):
        count = sum(1 for t in tests if t['security_pattern'] == pattern)
        print(f"  • {pattern}: {count} tests")

    print(f"\nVulnerability categories covered: {len(categories_tested)}")
    for category in sorted(categories_tested):
        count = sum(1 for t in tests if t['category'] == category)
        print(f"  • {category}: {count} tests")

    # Show severity distribution
    print("\nSeverity distribution:")
    for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        count = sum(1 for t in tests if t['severity'] == severity)
        if count > 0:
            print(f"  • {severity}: {count} tests")

    # Show CWE coverage
    cwe_ids = set(t['cwe_id'] for t in tests if t.get('cwe_id'))
    print(f"\nCWE vulnerabilities tested: {len(cwe_ids)}")
    for cwe in sorted(cwe_ids):
        print(f"  • {cwe}")


def main():
    """Run all demonstrations"""
    print("\n" + "=" * 80)
    print("  🛡️  MUTATION TESTING DEMONSTRATION")
    print("  OWASP Top 10 Security Testing with Intelligent Pattern Selection")
    print("=" * 80)

    try:
        # Part 1: Show available security patterns
        demonstrate_security_patterns()

        # Part 2: Show intelligent pattern selection
        demonstrate_pattern_selection()

        # Part 3: Show mutation test generation
        demonstrate_mutation_test_generation()

        # Part 4: Show vulnerability detection
        demonstrate_vulnerability_detection()

        # Part 5: Show comprehensive coverage
        demonstrate_comprehensive_coverage()

        # Summary
        print_header("✅ DEMO COMPLETE")

        print("Mutation Testing Capabilities:")
        print("  ✓ 19 security patterns (OWASP Top 10)")
        print("  ✓ Intelligent pattern selection by parameter type")
        print("  ✓ Automatic test generation with payloads")
        print("  ✓ Vulnerability detection from responses")
        print("  ✓ Severity-based prioritization")
        print("  ✓ CWE mapping for all patterns")
        print()
        print("Integration Status:")
        print("  ✓ Integrated into EnhancedTestGenerator")
        print("  ✓ Automatic activation for POST/PUT/PATCH endpoints")
        print("  ✓ Configurable test count per pattern")
        print("  ✓ Security tests prioritized by severity")
        print()
        print("Next Steps:")
        print("  1. Test against real APIs")
        print("  2. Collect vulnerability detection metrics")
        print("  3. Fine-tune patterns based on results")
        print("  4. Add custom security patterns")
        print()

    except Exception as e:
        logger.error(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
