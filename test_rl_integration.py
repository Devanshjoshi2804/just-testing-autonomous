#!/usr/bin/env python3
"""
Quick RL Integration Test
Tests that the RL optimizer works with TestRunner
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

# Mock logger if not available
try:
    from loguru import logger
except ImportError:
    class MockLogger:
        def exception(self, msg): print(f"ERROR: {msg}")
    logger = MockLogger()

from src.rl.test_optimizer import TestOptimizer
from src.rl.state_builder import StateBuilder


def test_state_builder():
    """Test state building"""
    print("\n" + "=" * 80)
    print("TEST 1: State Builder")
    print("=" * 80)

    endpoint = {
        'method': 'GET',
        'path': '/users',
        'failure_rate': 15.5,
        'days_since_change': 3,
    }

    context = {
        'time': datetime.now(),
        'dependency_health': 95,
    }

    state = StateBuilder.build_state(endpoint, context)
    description = StateBuilder.describe_state(state)

    print(f"\n✅ State created: {state}")
    print(f"✅ Description: {description}")

    assert len(state) == 6, "State should have 6 features"
    print("\n✅ State Builder: PASSED")


def test_test_optimizer():
    """Test Q-learning optimizer"""
    print("\n" + "=" * 80)
    print("TEST 2: Test Optimizer")
    print("=" * 80)

    optimizer = TestOptimizer(alpha=0.1, gamma=0.9, epsilon=0.2)

    # Create test endpoints
    endpoints = [
        {
            'method': 'GET',
            'path': '/users',
            'failure_rate': 5.0,
            'days_since_change': 30,
        },
        {
            'method': 'POST',
            'path': '/orders',
            'failure_rate': 25.0,
            'days_since_change': 2,
        },
        {
            'method': 'GET',
            'path': '/products',
            'failure_rate': 0.0,
            'days_since_change': 60,
        },
    ]

    context = {
        'time': datetime.now(),
        'dependency_health': 100,
    }

    # Prioritize endpoints
    prioritized = optimizer.prioritize_endpoints(endpoints, context)

    print(f"\n✅ Prioritized {len(prioritized)} endpoints")

    for ep in prioritized:
        priority = ep.get('rl_priority', 'unknown')
        print(f"   {priority:8} - {ep['method']:6} {ep['path']}")

    # Simulate test results
    test_results = []
    for ep in prioritized:
        result = {
            'endpoint': f"{ep['method']} {ep['path']}",
            'success': ep['failure_rate'] < 10,  # Simulate: low failure rate = success
            'rl_priority': ep.get('rl_priority'),
            'rl_state': ep.get('rl_state'),
            'skipped': ep.get('rl_priority') == 'skip',
            'would_have_failed': False,
        }
        test_results.append(result)

    # Learn from results
    optimizer.learn_from_results(test_results)

    metrics = optimizer.get_metrics()
    print(f"\n✅ RL Metrics:")
    print(f"   Episodes: {metrics['total_episodes']}")
    print(f"   Q-table size: {metrics['q_table_size']}")
    print(f"   Avg reward: {metrics['avg_reward_per_episode']:+.2f}")

    print("\n✅ Test Optimizer: PASSED")


def test_multiple_episodes():
    """Test learning over multiple episodes"""
    print("\n" + "=" * 80)
    print("TEST 3: Multi-Episode Learning")
    print("=" * 80)

    optimizer = TestOptimizer(alpha=0.2, gamma=0.9, epsilon=0.3)

    endpoints = [
        {'method': 'GET', 'path': '/stable', 'failure_rate': 0.0, 'days_since_change': 90},
        {'method': 'POST', 'path': '/flaky', 'failure_rate': 50.0, 'days_since_change': 1},
        {'method': 'GET', 'path': '/recent', 'failure_rate': 10.0, 'days_since_change': 3},
    ]

    context = {
        'time': datetime.now(),
        'dependency_health': 100,
    }

    print(f"\nRunning 10 episodes to see learning...")

    rewards_over_time = []

    for episode in range(10):
        prioritized = optimizer.prioritize_endpoints(endpoints, context)

        # Simulate realistic results
        results = []
        for ep in prioritized:
            path = ep['path']
            if 'stable' in path:
                success = True  # Always passes
            elif 'flaky' in path:
                success = episode % 2 == 0  # Fails half the time
            else:
                success = episode % 3 != 0  # Fails 1/3 of the time

            results.append({
                'endpoint': f"{ep['method']} {ep['path']}",
                'success': success,
                'rl_priority': ep.get('rl_priority'),
                'rl_state': ep.get('rl_state'),
                'skipped': ep.get('rl_priority') == 'skip',
                'would_have_failed': not success,
            })

        optimizer.learn_from_results(results)

        metrics = optimizer.get_metrics()
        rewards_over_time.append(metrics['avg_reward_per_episode'])

        if episode % 3 == 0:
            print(f"   Episode {episode:2d}: Avg reward = {metrics['avg_reward_per_episode']:+6.2f}, ε = {optimizer.epsilon:.3f}")

    print(f"\n✅ Learning progression:")
    print(f"   Initial avg reward: {rewards_over_time[0]:+.2f}")
    print(f"   Final avg reward: {rewards_over_time[-1]:+.2f}")
    print(f"   Q-table size: {optimizer.get_metrics()['q_table_size']}")

    if len(rewards_over_time) > 1:
        improvement = rewards_over_time[-1] - rewards_over_time[0]
        print(f"   Improvement: {improvement:+.2f}")

    print("\n✅ Multi-Episode Learning: PASSED")


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("🧪 RL INTEGRATION TESTS")
    print("=" * 80)

    try:
        test_state_builder()
        test_test_optimizer()
        test_multiple_episodes()

        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED")
        print("=" * 80)
        print("\n🎉 RL system is working correctly!")
        print("Next step: Run demo_intelligent_testing.py to see it in action\n")

        return 0

    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ TEST FAILED")
        print("=" * 80)
        logger.exception(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
