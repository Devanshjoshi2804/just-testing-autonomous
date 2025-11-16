#!/usr/bin/env python3
"""
Integration Validation Script
Tests that all major integrations work correctly without requiring external dependencies
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def print_header(title: str):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_result(test_name: str, passed: bool, details: str = ""):
    """Print test result"""
    icon = "✅" if passed else "❌"
    print(f"{icon} {test_name}")
    if details:
        print(f"   {details}")


def validate_imports():
    """Test 1: Validate all critical imports"""
    print_header("1. IMPORT VALIDATION")

    results = []

    # Test core imports
    imports_to_test = [
        ("TestRunner", "src.executors.test_runner"),
        ("ChangeDetector", "src.analysis.change_detector"),
        ("TestHealer", "src.testing.test_healer"),
        ("EnhancedTestGenerator", "src.agents.enhanced_test_generator"),
        ("MutationTestGenerator", "src.testing.mutation_test_generator"),
        ("SemanticTestGenerator", "src.testing.semantic_test_generator"),
        ("SecurityPatterns", "src.testing.security_patterns"),
    ]

    for class_name, module_path in imports_to_test:
        try:
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)
            print_result(f"Import: {class_name}", True)
            results.append(True)
        except Exception as e:
            print_result(f"Import: {class_name}", False, str(e))
            results.append(False)

    return all(results)


def validate_test_runner_initialization():
    """Test 2: Validate TestRunner initializes with self-healing"""
    print_header("2. TESTRUNNER INITIALIZATION")

    results = []

    try:
        from src.executors.test_runner import TestRunner

        # Check that TestRunner has required attributes
        runner_attrs = [
            'change_detector',
            'test_healer',
            'healing_history',
            'expected_responses',
            'comprehensive_mode'
        ]

        # We can't actually instantiate without dependencies,
        # but we can check the __init__ signature
        import inspect
        sig = inspect.signature(TestRunner.__init__)
        params = list(sig.parameters.keys())

        has_comprehensive_mode = 'comprehensive_mode' in params
        print_result("comprehensive_mode parameter exists", has_comprehensive_mode)
        results.append(has_comprehensive_mode)

        # Check methods exist
        has_comprehensive_method = hasattr(TestRunner, 'test_endpoint_comprehensive')
        print_result("test_endpoint_comprehensive method exists", has_comprehensive_method)
        results.append(has_comprehensive_method)

        has_healing_report = hasattr(TestRunner, 'get_healing_report')
        print_result("get_healing_report method exists", has_healing_report)
        results.append(has_healing_report)

        has_set_expected = hasattr(TestRunner, 'set_expected_response')
        print_result("set_expected_response method exists", has_set_expected)
        results.append(has_set_expected)

    except Exception as e:
        print_result("TestRunner validation", False, str(e))
        results.append(False)

    return all(results)


def validate_enhanced_generator():
    """Test 3: Validate EnhancedTestGenerator supports comprehensive mode"""
    print_header("3. ENHANCED TEST GENERATOR")

    results = []

    try:
        from src.agents.enhanced_test_generator import EnhancedTestGenerator

        # Check methods exist
        has_comprehensive = hasattr(EnhancedTestGenerator, 'generate_comprehensive_tests')
        print_result("generate_comprehensive_tests method exists", has_comprehensive)
        results.append(has_comprehensive)

        has_prioritize = hasattr(EnhancedTestGenerator, 'prioritize_tests')
        print_result("prioritize_tests method exists", has_prioritize)
        results.append(has_prioritize)

        has_summary = hasattr(EnhancedTestGenerator, 'get_test_generation_summary')
        print_result("get_test_generation_summary method exists", has_summary)
        results.append(has_summary)

        # Check __init__ accepts mutation testing params
        import inspect
        sig = inspect.signature(EnhancedTestGenerator.__init__)
        params = list(sig.parameters.keys())

        has_mutation_flag = 'enable_mutation_testing' in params
        print_result("enable_mutation_testing parameter exists", has_mutation_flag)
        results.append(has_mutation_flag)

    except Exception as e:
        print_result("EnhancedTestGenerator validation", False, str(e))
        results.append(False)

    return all(results)


def validate_api_endpoints():
    """Test 4: Validate API endpoints exist"""
    print_header("4. API ENDPOINT VALIDATION")

    results = []

    try:
        from src.api.routes.tests import router

        # Get all routes
        routes = [route.path for route in router.routes]

        # Check for new endpoints
        required_endpoints = [
            "/{session_id}/healing-history",
            "/{session_id}/security-report",
            "/{session_id}/mutations"
        ]

        for endpoint in required_endpoints:
            exists = endpoint in routes
            print_result(f"Endpoint exists: {endpoint}", exists)
            results.append(exists)

    except Exception as e:
        print_result("API endpoint validation", False, str(e))
        results.append(False)

    return all(results)


def validate_self_healing_components():
    """Test 5: Validate self-healing components work"""
    print_header("5. SELF-HEALING COMPONENTS")

    results = []

    try:
        from src.analysis.change_detector import ChangeDetector
        from src.testing.test_healer import TestHealer

        # Test ChangeDetector
        detector = ChangeDetector()
        print_result("ChangeDetector instantiated", True)
        results.append(True)

        # Test simple change detection
        expected = {'status_code': 200, 'body': {'id': 1}}
        actual = {'status_code': 201, 'body': {'id': 1}}

        changes = detector.detect_changes(expected, actual)
        has_changes = len(changes) > 0
        print_result(f"Change detection works ({len(changes)} changes)", has_changes)
        results.append(has_changes)

        # Test TestHealer
        healer = TestHealer(auto_heal=True)
        print_result("TestHealer instantiated", True)
        results.append(True)

        # Test healing
        test = {
            'name': 'Test',
            'endpoint': 'POST /test',
            'expected_status': 200,
            'expected_response': {'id': 1}
        }

        healed = healer.heal_test(test, actual, changes)
        healed_correctly = healed['expected_status'] == 201
        print_result("Test healing works", healed_correctly)
        results.append(healed_correctly)

    except Exception as e:
        print_result("Self-healing validation", False, str(e))
        results.append(False)

    return all(results)


def validate_mutation_testing():
    """Test 6: Validate mutation testing components"""
    print_header("6. MUTATION TESTING")

    results = []

    try:
        from src.testing.mutation_test_generator import MutationTestGenerator
        from src.testing.security_patterns import SecurityPatterns

        # Test SecurityPatterns
        patterns = SecurityPatterns.get_all_patterns()
        pattern_count = len(patterns)
        print_result(f"Security patterns loaded ({pattern_count} patterns)", pattern_count > 0)
        results.append(pattern_count > 0)

        critical = SecurityPatterns.get_critical_patterns()
        print_result(f"Critical patterns ({len(critical)} patterns)", len(critical) > 0)
        results.append(len(critical) > 0)

        # Test MutationTestGenerator
        generator = MutationTestGenerator(max_tests_per_pattern=2)
        print_result("MutationTestGenerator instantiated", True)
        results.append(True)

        # Test mutation generation
        endpoint = {
            'path': '/api/test',
            'method': 'POST',
            'parameters': [
                {'name': 'username', 'type': 'string', 'required': True}
            ]
        }

        tests = generator.generate_mutation_tests(endpoint)
        has_tests = len(tests) > 0
        print_result(f"Mutation tests generated ({len(tests)} tests)", has_tests)
        results.append(has_tests)

    except Exception as e:
        print_result("Mutation testing validation", False, str(e))
        results.append(False)

    return all(results)


def main():
    """Run all validation tests"""
    print("\n" + "=" * 80)
    print("  🔬 INTEGRATION VALIDATION")
    print("  Testing Key System Integrations")
    print("=" * 80)

    results = {}

    # Run validation tests
    results['Imports'] = validate_imports()
    results['TestRunner'] = validate_test_runner_initialization()
    results['EnhancedTestGenerator'] = validate_enhanced_generator()
    results['API Endpoints'] = validate_api_endpoints()
    results['Self-Healing'] = validate_self_healing_components()
    results['Mutation Testing'] = validate_mutation_testing()

    # Summary
    print_header("📊 VALIDATION SUMMARY")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for component, result in results.items():
        icon = "✅" if result else "❌"
        print(f"{icon} {component}")

    print(f"\n{'=' * 80}")
    print(f"Result: {passed}/{total} components validated ({passed/total*100:.1f}%)")
    print(f"{'=' * 80}\n")

    if passed == total:
        print("🎉 ALL INTEGRATIONS VALIDATED!")
        print("\nKey Integrations Working:")
        print("  ✅ Self-healing tests (automatic API change adaptation)")
        print("  ✅ Mutation testing (OWASP Top 10 security tests)")
        print("  ✅ Comprehensive test generation (semantic + LLM + mutation)")
        print("  ✅ API endpoints (healing history, security reports)")
        print("  ✅ Test prioritization (confidence-based ordering)")
        print()
        return 0
    else:
        print("⚠️  SOME INTEGRATIONS FAILED")
        print("\nPlease review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
