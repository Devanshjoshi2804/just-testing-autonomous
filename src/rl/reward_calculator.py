"""
Reward Calculator for RL Agent
Defines reward structure for reinforcement learning
"""
from typing import Dict, Any


class RewardCalculator:
    """
    Calculate rewards for RL agent actions

    Reward Philosophy:
    - High penalty for missed failures (false negatives are costly!)
    - Strong reward for correctly skipping stable endpoints (efficiency)
    - Moderate reward for finding failures in prioritized endpoints
    - Small penalty for wasting effort on stable endpoints
    """

    # Reward constants
    CORRECT_SKIP = 10.0          # Skipped stable endpoint, saved time
    FOUND_FAILURE_CRITICAL = 20.0  # Found failure in critical priority
    FOUND_FAILURE_HIGH = 15.0      # Found failure in high priority
    FOUND_FAILURE_NORMAL = 5.0     # Found failure in normal priority
    MISSED_FAILURE = -50.0         # Skipped endpoint that failed (CRITICAL!)
    WASTED_EFFORT = -1.0           # Tested stable endpoint unnecessarily
    CORRECT_PRIORITIZATION = 3.0   # Correctly deprioritized stable endpoint

    @classmethod
    def calculate(
        cls,
        action: str,
        test_result: Dict[str, Any],
        time_saved: float = 5.0
    ) -> float:
        """
        Calculate reward for action and outcome

        Args:
            action: Action taken (critical/high/normal/low/skip)
            test_result: Test execution result
            time_saved: Estimated time saved (seconds)

        Returns:
            Reward value
        """
        success = test_result.get('success', False)
        skipped = test_result.get('skipped', False)

        # Case 1: Skipped endpoint
        if action == 'skip':
            if skipped:
                would_fail = test_result.get('would_have_failed', False)

                if would_fail:
                    # FALSE NEGATIVE: Skipped failing endpoint - very bad!
                    return cls.MISSED_FAILURE
                else:
                    # TRUE NEGATIVE: Correctly skipped stable endpoint
                    # Scale reward by time saved
                    return cls.CORRECT_SKIP * (time_saved / 5.0)

        # Case 2: Found failure
        if not success:
            if action == 'critical':
                return cls.FOUND_FAILURE_CRITICAL
            elif action == 'high':
                return cls.FOUND_FAILURE_HIGH
            else:
                return cls.FOUND_FAILURE_NORMAL

        # Case 3: Tested and passed
        if success:
            if action in ['low', 'skip']:
                # Correctly identified as low priority
                return cls.CORRECT_PRIORITIZATION
            elif action in ['critical', 'high']:
                # Wasted effort on stable endpoint
                return cls.WASTED_EFFORT
            else:
                # Normal priority for stable endpoint - neutral
                return 0.0

        return 0.0

    @classmethod
    def explain_reward(
        cls,
        action: str,
        test_result: Dict[str, Any],
        reward: float
    ) -> str:
        """
        Explain why a reward was given

        Args:
            action: Action taken
            test_result: Test result
            reward: Calculated reward

        Returns:
            Human-readable explanation
        """
        success = test_result.get('success', False)
        skipped = test_result.get('skipped', False)

        if action == 'skip':
            if skipped:
                would_fail = test_result.get('would_have_failed', False)
                if would_fail:
                    return f"❌ MISSED FAILURE: Skipped failing endpoint (reward={reward})"
                else:
                    return f"✅ CORRECT SKIP: Saved time on stable endpoint (reward={reward})"

        if not success:
            return f"🎯 FOUND FAILURE: Prioritized as '{action}' (reward={reward})"

        if success:
            if action in ['low', 'skip']:
                return f"👍 CORRECT PRIORITY: Low priority for stable endpoint (reward={reward})"
            elif action in ['critical', 'high']:
                return f"⚠️  WASTED EFFORT: High priority for stable endpoint (reward={reward})"
            else:
                return f"➖ NEUTRAL: Normal priority for stable endpoint (reward={reward})"

        return f"Unknown scenario (reward={reward})"

    @classmethod
    def get_reward_stats(cls) -> Dict[str, float]:
        """Get all reward values for reference"""
        return {
            'correct_skip': cls.CORRECT_SKIP,
            'found_failure_critical': cls.FOUND_FAILURE_CRITICAL,
            'found_failure_high': cls.FOUND_FAILURE_HIGH,
            'found_failure_normal': cls.FOUND_FAILURE_NORMAL,
            'missed_failure': cls.MISSED_FAILURE,
            'wasted_effort': cls.WASTED_EFFORT,
            'correct_prioritization': cls.CORRECT_PRIORITIZATION,
        }
