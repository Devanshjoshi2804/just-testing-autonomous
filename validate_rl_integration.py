#!/usr/bin/env python3
"""
RL Integration Validation
Validates that RL code is properly integrated (static analysis)
"""
import re
from pathlib import Path


def check_file_contains(filepath, pattern, description):
    """Check if file contains a pattern"""
    if not Path(filepath).exists():
        print(f"❌ File not found: {filepath}")
        return False

    with open(filepath, 'r') as f:
        content = f.read()

    if re.search(pattern, content, re.MULTILINE | re.DOTALL):
        print(f"✅ {description}")
        return True
    else:
        print(f"❌ MISSING: {description}")
        print(f"   File: {filepath}")
        print(f"   Pattern: {pattern}")
        return False


def main():
    """Validate RL integration"""
    print("\n" + "=" * 80)
    print("🔍 RL INTEGRATION VALIDATION")
    print("=" * 80)

    checks = []

    # Check 1: RL module files exist
    print("\n📦 RL Module Files:")
    rl_files = [
        "src/rl/__init__.py",
        "src/rl/test_optimizer.py",
        "src/rl/state_builder.py",
        "src/rl/reward_calculator.py",
    ]

    for file in rl_files:
        exists = Path(file).exists()
        status = "✅" if exists else "❌"
        print(f"   {status} {file}")
        checks.append(exists)

    # Check 2: TestRunner imports RL
    print("\n🔗 TestRunner Integration:")
    checks.append(check_file_contains(
        "src/executors/test_runner.py",
        r"from src\.rl\.test_optimizer import TestOptimizer",
        "TestRunner imports TestOptimizer"
    ))

    # Check 3: TestRunner initializes RL optimizer
    checks.append(check_file_contains(
        "src/executors/test_runner.py",
        r"self\.rl_optimizer = TestOptimizer\(\)",
        "TestRunner initializes RL optimizer"
    ))

    # Check 4: TestRunner uses RL for prioritization
    checks.append(check_file_contains(
        "src/executors/test_runner.py",
        r"self\.rl_optimizer\.prioritize_endpoints",
        "TestRunner uses RL prioritization"
    ))

    # Check 5: TestRunner learns from results
    checks.append(check_file_contains(
        "src/executors/test_runner.py",
        r"self\.rl_optimizer\.learn_from_results",
        "TestRunner learns from results"
    ))

    # Check 6: Endpoint metadata tracking
    checks.append(check_file_contains(
        "src/executors/test_runner.py",
        r"def _enrich_endpoint_metadata",
        "Endpoint metadata enrichment method exists"
    ))

    # Check 7: Context building for RL
    checks.append(check_file_contains(
        "src/executors/test_runner.py",
        r"def _build_test_context",
        "Test context builder method exists"
    ))

    # Check 8: Probe endpoint for skipped tests
    checks.append(check_file_contains(
        "src/executors/test_runner.py",
        r"async def _probe_endpoint",
        "Probe endpoint method exists for validation"
    ))

    # Check 9: RL metrics logging
    checks.append(check_file_contains(
        "src/executors/test_runner.py",
        r"RL Metrics:",
        "RL metrics are logged"
    ))

    # Check 10: Q-Learning implementation
    checks.append(check_file_contains(
        "src/rl/test_optimizer.py",
        r"class TestOptimizer:",
        "TestOptimizer class defined"
    ))

    checks.append(check_file_contains(
        "src/rl/test_optimizer.py",
        r"def update_q_value",
        "Q-value update method exists"
    ))

    checks.append(check_file_contains(
        "src/rl/test_optimizer.py",
        r"def choose_action",
        "Action selection method exists"
    ))

    # Check 11: State building
    checks.append(check_file_contains(
        "src/rl/state_builder.py",
        r"def build_state",
        "State builder method exists"
    ))

    # Check 12: Reward calculation
    checks.append(check_file_contains(
        "src/rl/reward_calculator.py",
        r"class RewardCalculator:",
        "RewardCalculator class defined"
    ))

    # Summary
    print("\n" + "=" * 80)
    passed = sum(checks)
    total = len(checks)

    if passed == total:
        print(f"✅ ALL CHECKS PASSED ({passed}/{total})")
        print("=" * 80)
        print("\n🎉 RL system is fully integrated!")
        print("\n📊 Integration Summary:")
        print("   ✅ RL module created (4 files)")
        print("   ✅ TestRunner imports RL")
        print("   ✅ RL optimizer initialized")
        print("   ✅ Endpoint prioritization enabled")
        print("   ✅ Learning from results implemented")
        print("   ✅ Metadata tracking added")
        print("   ✅ Context building implemented")
        print("   ✅ Validation probing added")
        print("   ✅ Metrics logging added")
        print("\n🚀 Next Step: Run with Docker to see it learn!")
        print("   docker compose up -d")
        print("   python demo_intelligent_testing.py")
        print()
        return 0
    else:
        print(f"❌ CHECKS FAILED ({passed}/{total})")
        print("=" * 80)
        print(f"\n{total - passed} integration issues found")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
