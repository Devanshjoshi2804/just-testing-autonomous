#!/usr/bin/env python3
"""
Self-Healing Tests Demonstration
Shows how tests automatically adapt when APIs change
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

from src.analysis.change_detector import ChangeDetector, APIChange
from src.testing.test_healer import TestHealer, HealingAction


def print_header(title: str):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_section(title: str):
    """Print formatted section"""
    print(f"\n--- {title} ---\n")


def demonstrate_status_code_changes():
    """Demonstrate detection and healing of status code changes"""
    print_header("🔄 SCENARIO 1: Status Code Changes")

    detector = ChangeDetector()
    healer = TestHealer(auto_heal=True)

    # Original test expects 200
    original_test = {
        'name': 'Create User',
        'endpoint': 'POST /api/users',
        'expected_status': 200,
        'expected_response': {
            'id': 1,
            'email': 'test@example.com'
        }
    }

    print("Original Test:")
    print(f"  Expected Status: {original_test['expected_status']}")
    print(f"  Expected Response: {json.dumps(original_test['expected_response'], indent=4)}\n")

    # API changed to return 201 (Created) instead of 200
    actual_response = {
        'status_code': 201,
        'body': {
            'id': 1,
            'email': 'test@example.com'
        }
    }

    print("API Response:")
    print(f"  Actual Status: {actual_response['status_code']}")
    print(f"  Response Body: {json.dumps(actual_response['body'], indent=4)}\n")

    # Detect changes
    expected = {
        'status_code': original_test['expected_status'],
        'body': original_test['expected_response']
    }

    changes = detector.detect_changes(expected, actual_response)

    print(f"Changes Detected: {len(changes)}")
    for change in changes:
        print(f"  • {change.change_type}: {change.description}")
        print(f"    Severity: {change.severity}")
        print(f"    💡 {change.suggestion}\n")

    # Heal test
    healed_test = healer.heal_test(original_test, actual_response, changes)

    print("Healed Test:")
    print(f"  Expected Status: {healed_test['expected_status']}")
    print(f"  Expected Response: {json.dumps(healed_test['expected_response'], indent=4)}\n")

    print("✅ Test automatically adapted to new status code!")


def demonstrate_schema_evolution():
    """Demonstrate detection and healing of schema changes"""
    print_header("🔄 SCENARIO 2: Schema Evolution (New Fields Added)")

    detector = ChangeDetector()
    healer = TestHealer(auto_heal=True)

    # Original test
    original_test = {
        'name': 'Get User Profile',
        'endpoint': 'GET /api/users/1',
        'expected_status': 200,
        'expected_response': {
            'id': 1,
            'email': 'john@example.com',
            'name': 'John Doe'
        }
    }

    print("Original Test (API v1):")
    print(json.dumps(original_test['expected_response'], indent=2))
    print()

    # API v2 added new fields
    actual_response = {
        'status_code': 200,
        'body': {
            'id': 1,
            'email': 'john@example.com',
            'name': 'John Doe',
            'avatar_url': 'https://example.com/avatars/john.jpg',  # NEW!
            'created_at': '2024-01-01T00:00:00Z',  # NEW!
            'verified': True  # NEW!
        }
    }

    print("API Response (API v2 - New Fields):")
    print(json.dumps(actual_response['body'], indent=2))
    print()

    # Detect and heal
    changes = detector.detect_changes(
        {'status_code': 200, 'body': original_test['expected_response']},
        actual_response
    )

    print(f"Changes Detected: {len(changes)}")
    for change in changes:
        print(f"  • {change.change_type}: {change.field_path}")
        print(f"    Value: {change.actual_value}")
        print(f"    Severity: {change.severity}\n")

    healed_test = healer.heal_test(original_test, actual_response, changes)

    print("Healed Test:")
    print(json.dumps(healed_test['expected_response'], indent=2))
    print()

    print("✅ Test automatically updated with new fields!")


def demonstrate_breaking_changes():
    """Demonstrate detection of breaking changes"""
    print_header("🔄 SCENARIO 3: Breaking Changes (Field Removed)")

    detector = ChangeDetector()
    healer = TestHealer(auto_heal=True)

    # Original test
    original_test = {
        'name': 'Get User',
        'endpoint': 'GET /api/users/1',
        'expected_status': 200,
        'expected_response': {
            'id': 1,
            'username': 'johndoe',
            'email': 'john@example.com',
            'phone': '+1234567890'  # This field will be removed
        }
    }

    print("Original Test:")
    print(json.dumps(original_test['expected_response'], indent=2))
    print()

    # API removed 'phone' field (BREAKING CHANGE!)
    actual_response = {
        'status_code': 200,
        'body': {
            'id': 1,
            'username': 'johndoe',
            'email': 'john@example.com'
            # 'phone' field removed!
        }
    }

    print("API Response (Field Removed):")
    print(json.dumps(actual_response['body'], indent=2))
    print()

    # Detect changes
    changes = detector.detect_changes(
        {'status_code': 200, 'body': original_test['expected_response']},
        actual_response
    )

    print(detector.generate_change_report(changes))

    # Heal test
    healed_test = healer.heal_test(original_test, actual_response, changes)

    print("\nHealed Test:")
    print(json.dumps(healed_test['expected_response'], indent=2))
    print()

    print("⚠️  Breaking change detected and test updated!")


def demonstrate_type_changes():
    """Demonstrate detection of type changes"""
    print_header("🔄 SCENARIO 4: Type Changes")

    detector = ChangeDetector()
    healer = TestHealer(auto_heal=True)

    # Original test
    original_test = {
        'name': 'Get Order',
        'endpoint': 'GET /api/orders/1',
        'expected_status': 200,
        'expected_response': {
            'id': 1,
            'total': '99.99',  # String
            'items_count': '5'  # String
        }
    }

    print("Original Test (String Types):")
    print(json.dumps(original_test['expected_response'], indent=2))
    print()

    # API changed to return numbers instead of strings
    actual_response = {
        'status_code': 200,
        'body': {
            'id': 1,
            'total': 99.99,  # Now float
            'items_count': 5  # Now int
        }
    }

    print("API Response (Numeric Types):")
    print(json.dumps(actual_response['body'], indent=2))
    print()

    # Detect and report
    changes = detector.detect_changes(
        {'status_code': 200, 'body': original_test['expected_response']},
        actual_response
    )

    print(detector.generate_change_report(changes))

    # Heal test
    healed_test = healer.heal_test(original_test, actual_response, changes)

    print("\nHealed Test:")
    print(json.dumps(healed_test['expected_response'], indent=2))
    print()

    print("✅ Test updated to expect numeric types!")


def demonstrate_nested_changes():
    """Demonstrate detection of nested object changes"""
    print_header("🔄 SCENARIO 5: Nested Schema Changes")

    detector = ChangeDetector()
    healer = TestHealer(auto_heal=True)

    # Original test
    original_test = {
        'name': 'Get Product',
        'endpoint': 'GET /api/products/1',
        'expected_status': 200,
        'expected_response': {
            'id': 1,
            'name': 'Widget',
            'price': {
                'amount': 29.99,
                'currency': 'USD'
            }
        }
    }

    print("Original Test:")
    print(json.dumps(original_test['expected_response'], indent=2))
    print()

    # API added tax information
    actual_response = {
        'status_code': 200,
        'body': {
            'id': 1,
            'name': 'Widget',
            'price': {
                'amount': 29.99,
                'currency': 'USD',
                'tax': 2.40,  # NEW nested field
                'total': 32.39  # NEW nested field
            }
        }
    }

    print("API Response (New Nested Fields):")
    print(json.dumps(actual_response['body'], indent=2))
    print()

    # Detect and heal
    changes = detector.detect_changes(
        {'status_code': 200, 'body': original_test['expected_response']},
        actual_response
    )

    print(f"Changes Detected: {len(changes)}")
    for change in changes:
        print(f"  • {change.field_path}: {change.actual_value}")
        print(f"    Type: {change.change_type}")
        print(f"    Severity: {change.severity}\n")

    healed_test = healer.heal_test(original_test, actual_response, changes)

    print("Healed Test:")
    print(json.dumps(healed_test['expected_response'], indent=2))
    print()

    print("✅ Nested schema changes detected and healed!")


def demonstrate_healing_history():
    """Demonstrate healing history tracking"""
    print_header("📊 HEALING HISTORY")

    healer = TestHealer(auto_heal=True)

    # Simulate multiple healing sessions
    scenarios = [
        {
            'test': {
                'name': 'Test 1',
                'endpoint': 'POST /api/users',
                'expected_status': 200
            },
            'response': {'status_code': 201, 'body': {}}
        },
        {
            'test': {
                'name': 'Test 2',
                'endpoint': 'GET /api/products',
                'expected_status': 200,
                'expected_response': {'id': 1}
            },
            'response': {
                'status_code': 200,
                'body': {'id': 1, 'new_field': 'value'}
            }
        },
        {
            'test': {
                'name': 'Test 3',
                'endpoint': 'DELETE /api/items/1',
                'expected_status': 200
            },
            'response': {'status_code': 204, 'body': None}
        }
    ]

    for scenario in scenarios:
        healer.heal_test(scenario['test'], scenario['response'])

    # Generate report
    print(healer.get_healing_report())

    # Export history
    print("\n\nHealing History (JSON Export):")
    history = healer.export_healing_history()
    print(json.dumps(history, indent=2))


def demonstrate_auto_heal_decision():
    """Demonstrate auto-heal decision making"""
    print_header("🤖 AUTO-HEAL DECISION LOGIC")

    detector = ChangeDetector()

    scenarios = [
        {
            'name': 'Safe Changes (Non-Breaking)',
            'expected': {
                'status_code': 200,
                'body': {'id': 1, 'name': 'Test'}
            },
            'actual': {
                'status_code': 200,
                'body': {'id': 1, 'name': 'Test', 'email': 'test@example.com'}
            }
        },
        {
            'name': 'Breaking Changes (Field Removed)',
            'expected': {
                'status_code': 200,
                'body': {'id': 1, 'name': 'Test', 'email': 'test@example.com'}
            },
            'actual': {
                'status_code': 200,
                'body': {'id': 1, 'name': 'Test'}
            }
        },
        {
            'name': 'Minor Changes (Status Code)',
            'expected': {
                'status_code': 200,
                'body': {}
            },
            'actual': {
                'status_code': 201,
                'body': {}
            }
        }
    ]

    for scenario in scenarios:
        print(f"\n{scenario['name']}:")
        changes = detector.detect_changes(scenario['expected'], scenario['actual'])

        categorized = detector.categorize_changes(changes)
        print(f"  BREAKING: {len(categorized['BREAKING'])}")
        print(f"  NON_BREAKING: {len(categorized['NON_BREAKING'])}")
        print(f"  MINOR: {len(categorized['MINOR'])}")

        should_heal = detector.should_auto_heal(changes)
        print(f"  Auto-Heal: {'✅ YES' if should_heal else '⚠️  REQUIRES REVIEW'}")


def main():
    """Run all demonstrations"""
    print("\n" + "=" * 80)
    print("  ✨ SELF-HEALING TESTS DEMONSTRATION")
    print("  Tests That Automatically Adapt When APIs Change")
    print("=" * 80)

    try:
        # Scenario 1: Status code changes
        demonstrate_status_code_changes()

        # Scenario 2: Schema evolution
        demonstrate_schema_evolution()

        # Scenario 3: Breaking changes
        demonstrate_breaking_changes()

        # Scenario 4: Type changes
        demonstrate_type_changes()

        # Scenario 5: Nested changes
        demonstrate_nested_changes()

        # Healing history
        demonstrate_healing_history()

        # Auto-heal decision logic
        demonstrate_auto_heal_decision()

        # Summary
        print_header("✅ DEMO COMPLETE")

        print("Self-Healing Test Capabilities:")
        print("  ✓ Automatic detection of API changes")
        print("  ✓ Classification by severity (BREAKING/NON_BREAKING/MINOR)")
        print("  ✓ Smart auto-heal decisions")
        print("  ✓ Status code adaptation")
        print("  ✓ Schema evolution (new/removed/renamed fields)")
        print("  ✓ Type change detection and healing")
        print("  ✓ Nested object change support")
        print("  ✓ Healing history tracking")
        print()
        print("Benefits:")
        print("  ✓ Tests stay green when APIs evolve")
        print("  ✓ Reduces test maintenance burden")
        print("  ✓ Identifies breaking changes automatically")
        print("  ✓ Provides actionable suggestions")
        print("  ✓ Maintains test reliability")
        print()
        print("Next Steps:")
        print("  1. Integrate into TestRunner")
        print("  2. Add healing history to FlowStore")
        print("  3. Create healing analytics dashboard")
        print("  4. Add ML-based change prediction")
        print()

    except Exception as e:
        logger.error(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
