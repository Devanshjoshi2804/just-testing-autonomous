"""
Q-Learning Test Optimizer
Learns optimal test execution strategy through reinforcement learning
"""
import numpy as np
import pickle
from pathlib import Path
from typing import Dict, Tuple, List, Any
from datetime import datetime
from loguru import logger


class TestOptimizer:
    """
    Q-Learning agent that optimizes test execution order and selection

    State Space:
        - endpoint_hash: Unique identifier for endpoint
        - hour_of_day: 0-23 (temporal patterns)
        - day_of_week: 0-6 (weekly patterns)
        - days_since_change: 0-30 (code recency)
        - recent_failure_rate: 0-100 (historical reliability)
        - dependency_health: 0-100 (related endpoints health)

    Action Space:
        - CRITICAL: Test immediately, highest priority
        - HIGH: Test early in sequence
        - NORMAL: Test in standard order
        - LOW: Test if time permits
        - SKIP: Don't test (high confidence stable)

    Reward Structure:
        - CORRECT_SKIP: +10 (saved time, endpoint was stable)
        - FOUND_FAILURE_HIGH_PRIORITY: +20 (caught critical failure early)
        - FOUND_FAILURE_NORMAL: +5 (caught failure)
        - MISSED_FAILURE: -50 (skipped endpoint that failed - critical error!)
        - WASTED_EFFORT_SKIP: -1 (ran stable endpoint unnecessarily)
        - CORRECT_LOW_PRIORITY: +3 (deprioritized stable endpoint correctly)
    """

    # Action space
    ACTIONS = ['critical', 'high', 'normal', 'low', 'skip']

    # Reward values
    REWARDS = {
        'correct_skip': 10,
        'found_failure_critical': 20,
        'found_failure_high': 15,
        'found_failure_normal': 5,
        'missed_failure': -50,
        'wasted_effort': -1,
        'correct_prioritization': 3,
    }

    def __init__(
        self,
        alpha: float = 0.1,
        gamma: float = 0.9,
        epsilon: float = 0.1,
        epsilon_decay: float = 0.995,
        min_epsilon: float = 0.01
    ):
        """
        Initialize Q-Learning optimizer

        Args:
            alpha: Learning rate (how much to update Q-values)
            gamma: Discount factor (importance of future rewards)
            epsilon: Exploration rate (probability of random action)
            epsilon_decay: Decay rate for epsilon after each episode
            min_epsilon: Minimum epsilon value
        """
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.min_epsilon = min_epsilon

        # Q-table: {(state, action): Q-value}
        self.q_table = self._load_q_table()

        # Metrics tracking
        self.metrics = {
            'time_saved': 0.0,
            'failures_caught': 0,
            'failures_missed': 0,
            'correct_skips': 0,
            'total_episodes': 0,
            'avg_reward_per_episode': 0.0,
        }

        # Episode history for analysis
        self.episode_rewards = []

        logger.info(
            f"TestOptimizer initialized: α={alpha}, γ={gamma}, ε={epsilon}, "
            f"Q-table size={len(self.q_table)}"
        )

    def _load_q_table(self) -> Dict[Tuple, float]:
        """Load persisted Q-table from disk"""
        path = Path('src/rl/models/q_table.pkl')
        if path.exists():
            try:
                with open(path, 'rb') as f:
                    q_table = pickle.load(f)
                logger.info(f"Loaded Q-table with {len(q_table)} entries")
                return q_table
            except Exception as e:
                logger.warning(f"Failed to load Q-table: {e}, starting fresh")
                return {}
        return {}

    def _save_q_table(self):
        """Persist Q-table to disk"""
        path = Path('src/rl/models/q_table.pkl')
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(path, 'wb') as f:
                pickle.dump(self.q_table, f)
            logger.debug(f"Saved Q-table with {len(self.q_table)} entries")
        except Exception as e:
            logger.error(f"Failed to save Q-table: {e}")

    def get_q_value(self, state: Tuple, action: str) -> float:
        """
        Get Q-value for state-action pair

        Args:
            state: State tuple
            action: Action string

        Returns:
            Q-value (defaults to 0.0 for unseen state-actions)
        """
        return self.q_table.get((state, action), 0.0)

    def choose_action(self, state: Tuple, explore: bool = True) -> str:
        """
        Choose action using ε-greedy policy

        Args:
            state: Current state
            explore: Whether to use exploration (set False for production)

        Returns:
            Selected action
        """
        # Exploration: random action
        if explore and np.random.random() < self.epsilon:
            action = np.random.choice(self.ACTIONS)
            logger.debug(f"Exploring: random action '{action}'")
            return action

        # Exploitation: best known action
        q_values = {a: self.get_q_value(state, a) for a in self.ACTIONS}
        best_action = max(q_values, key=q_values.get)
        best_q = q_values[best_action]

        logger.debug(
            f"Exploiting: action '{best_action}' (Q={best_q:.2f}) "
            f"Q-values={{{', '.join(f'{a}: {v:.2f}' for a, v in q_values.items())}}}"
        )

        return best_action

    def update_q_value(
        self,
        state: Tuple,
        action: str,
        reward: float,
        next_state: Tuple
    ):
        """
        Update Q-value using Q-learning update rule

        Q(s,a) ← Q(s,a) + α[r + γ max_a' Q(s',a') - Q(s,a)]

        Args:
            state: Current state
            action: Action taken
            reward: Reward received
            next_state: Next state after action
        """
        current_q = self.get_q_value(state, action)

        # Max Q-value for next state (best action in next state)
        max_next_q = max(
            self.get_q_value(next_state, a)
            for a in self.ACTIONS
        )

        # Q-learning update
        new_q = current_q + self.alpha * (
            reward + self.gamma * max_next_q - current_q
        )

        self.q_table[(state, action)] = new_q

        logger.debug(
            f"Q-update: {action} @ {state[:2]}... "
            f"{current_q:.2f} → {new_q:.2f} "
            f"(r={reward:+.1f}, max_next={max_next_q:.2f})"
        )

    def calculate_reward(
        self,
        action: str,
        test_result: Dict[str, Any]
    ) -> float:
        """
        Calculate reward based on action taken and test outcome

        Args:
            action: Action that was taken
            test_result: Test execution result

        Returns:
            Reward value
        """
        success = test_result.get('success', False)
        skipped = test_result.get('skipped', False)

        # Case 1: Skipped endpoint
        if action == 'skip':
            if skipped:
                # Check if endpoint would have failed (we still probe it)
                would_fail = test_result.get('would_have_failed', False)

                if would_fail:
                    # CRITICAL ERROR: Skipped a failing endpoint
                    self.metrics['failures_missed'] += 1
                    return self.REWARDS['missed_failure']
                else:
                    # CORRECT: Skipped stable endpoint, saved time
                    self.metrics['correct_skips'] += 1
                    time_saved = test_result.get('estimated_time', 5)
                    self.metrics['time_saved'] += time_saved
                    return self.REWARDS['correct_skip']

        # Case 2: Tested and found failure
        if not success:
            self.metrics['failures_caught'] += 1

            if action == 'critical':
                return self.REWARDS['found_failure_critical']
            elif action == 'high':
                return self.REWARDS['found_failure_high']
            else:
                return self.REWARDS['found_failure_normal']

        # Case 3: Tested and passed (stable endpoint)
        if success:
            if action in ['low', 'skip']:
                # Correctly identified as low priority
                return self.REWARDS['correct_prioritization']
            elif action in ['critical', 'high']:
                # Wasted effort on stable endpoint
                return self.REWARDS['wasted_effort']
            else:
                # Normal priority, normal outcome
                return 0

        return 0

    def prioritize_endpoints(
        self,
        endpoints: List[Dict],
        context: Dict
    ) -> List[Dict]:
        """
        Prioritize endpoints using RL policy

        Args:
            endpoints: List of endpoint metadata
            context: Test execution context (time, changes, etc.)

        Returns:
            Prioritized endpoints with assigned actions
        """
        from src.rl.state_builder import StateBuilder

        prioritized = []

        for endpoint in endpoints:
            # Build state vector
            state = StateBuilder.build_state(endpoint, context)

            # Choose action (explore during training)
            action = self.choose_action(state, explore=True)

            prioritized.append({
                **endpoint,
                'rl_priority': action,
                'rl_state': state,  # Store for learning later
            })

        # Sort by priority level
        priority_order = {
            'critical': 0,
            'high': 1,
            'normal': 2,
            'low': 3,
            'skip': 4,
        }

        prioritized.sort(key=lambda e: priority_order[e['rl_priority']])

        # Log prioritization
        logger.info("🧠 RL Test Prioritization:")
        for ep in prioritized:
            priority_icon = {
                'critical': '🔴',
                'high': '🟠',
                'normal': '🟡',
                'low': '🟢',
                'skip': '⏭️ ',
            }[ep['rl_priority']]

            logger.info(
                f"  {priority_icon} {ep['rl_priority']:8} - "
                f"{ep.get('method', 'GET'):6} {ep.get('path', 'unknown')}"
            )

        return prioritized

    def learn_from_results(self, test_results: List[Dict]):
        """
        Update Q-values from test execution results

        Args:
            test_results: List of test results with states and outcomes
        """
        if not test_results:
            return

        episode_reward = 0

        for i, result in enumerate(test_results):
            state = result.get('rl_state')
            action = result.get('rl_priority')

            if not state or not action:
                continue

            # Calculate reward
            reward = self.calculate_reward(action, result)
            episode_reward += reward

            # Determine next state (terminal if last result)
            if i < len(test_results) - 1:
                next_state = test_results[i + 1].get('rl_state', state)
            else:
                next_state = state  # Terminal state

            # Update Q-value
            self.update_q_value(state, action, reward, next_state)

        # Update metrics
        self.metrics['total_episodes'] += 1
        self.episode_rewards.append(episode_reward)

        # Calculate running average
        self.metrics['avg_reward_per_episode'] = np.mean(
            self.episode_rewards[-100:]  # Last 100 episodes
        )

        # Decay exploration rate
        self.epsilon = max(
            self.min_epsilon,
            self.epsilon * self.epsilon_decay
        )

        # Persist learning
        self._save_q_table()

        logger.info(
            f"📚 Episode complete: "
            f"reward={episode_reward:+.1f}, "
            f"avg={self.metrics['avg_reward_per_episode']:+.1f}, "
            f"ε={self.epsilon:.3f}, "
            f"Q-table={len(self.q_table)} entries"
        )

    def get_metrics(self) -> Dict:
        """Get current performance metrics"""
        return {
            **self.metrics,
            'q_table_size': len(self.q_table),
            'exploration_rate': self.epsilon,
            'recent_avg_reward': np.mean(self.episode_rewards[-10:]) if self.episode_rewards else 0,
        }

    def reset_metrics(self):
        """Reset performance metrics (but keep Q-table)"""
        self.metrics = {
            'time_saved': 0.0,
            'failures_caught': 0,
            'failures_missed': 0,
            'correct_skips': 0,
            'total_episodes': self.metrics['total_episodes'],
            'avg_reward_per_episode': self.metrics['avg_reward_per_episode'],
        }
