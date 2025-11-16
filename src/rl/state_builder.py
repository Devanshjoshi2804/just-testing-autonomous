"""
State Builder for RL Agent
Converts endpoint and context information into state vectors
"""
import hashlib
from datetime import datetime
from typing import Dict, Tuple, Any


class StateBuilder:
    """Build state representations for Q-learning"""

    @staticmethod
    def build_state(endpoint: Dict, context: Dict) -> Tuple:
        """
        Build state tuple from endpoint and context

        State features:
        1. endpoint_hash: Hash of endpoint identifier (for indexing)
        2. hour_of_day: 0-23 (temporal patterns)
        3. day_of_week: 0-6 (weekly patterns)
        4. days_since_change: Bucketed (0-2, 3-7, 8-14, 15-30, 30+)
        5. recent_failure_rate: Bucketed (0-10%, 10-30%, 30-50%, 50%+)
        6. dependency_health: Bucketed (0-50%, 50-80%, 80-95%, 95%+)

        Args:
            endpoint: Endpoint metadata
            context: Test execution context

        Returns:
            State tuple
        """
        # Feature 1: Endpoint identifier (hashed for compact representation)
        endpoint_id = f"{endpoint.get('method', 'GET')} {endpoint.get('path', '')}"
        endpoint_hash = StateBuilder._hash_to_bucket(endpoint_id, num_buckets=100)

        # Feature 2: Hour of day (0-23)
        current_time = context.get('time', datetime.now())
        hour_of_day = current_time.hour

        # Feature 3: Day of week (0-6, Monday=0)
        day_of_week = current_time.weekday()

        # Feature 4: Days since code change (bucketed)
        days_since_change = endpoint.get('days_since_change', 30)
        days_bucket = StateBuilder._bucket_days_since_change(days_since_change)

        # Feature 5: Recent failure rate (bucketed)
        failure_rate = endpoint.get('failure_rate', 0.0)
        failure_bucket = StateBuilder._bucket_failure_rate(failure_rate)

        # Feature 6: Dependency health (bucketed)
        dep_health = context.get('dependency_health', 100)
        health_bucket = StateBuilder._bucket_health(dep_health)

        # Return state tuple
        state = (
            endpoint_hash,
            hour_of_day,
            day_of_week,
            days_bucket,
            failure_bucket,
            health_bucket
        )

        return state

    @staticmethod
    def _hash_to_bucket(text: str, num_buckets: int = 100) -> int:
        """Hash string to bucket index"""
        hash_digest = hashlib.md5(text.encode()).hexdigest()
        hash_int = int(hash_digest, 16)
        return hash_int % num_buckets

    @staticmethod
    def _bucket_days_since_change(days: int) -> str:
        """Bucket days since change into categories"""
        if days <= 2:
            return 'very_recent'  # Just changed
        elif days <= 7:
            return 'recent'       # Changed this week
        elif days <= 14:
            return 'moderate'     # Changed last 2 weeks
        elif days <= 30:
            return 'old'          # Changed last month
        else:
            return 'stable'       # Haven't changed in a while

    @staticmethod
    def _bucket_failure_rate(rate: float) -> str:
        """Bucket failure rate (0-100) into categories"""
        if rate < 10:
            return 'very_stable'
        elif rate < 30:
            return 'mostly_stable'
        elif rate < 50:
            return 'unstable'
        else:
            return 'very_unstable'

    @staticmethod
    def _bucket_health(health: int) -> str:
        """Bucket health score (0-100) into categories"""
        if health >= 95:
            return 'excellent'
        elif health >= 80:
            return 'good'
        elif health >= 50:
            return 'degraded'
        else:
            return 'critical'

    @staticmethod
    def describe_state(state: Tuple) -> str:
        """
        Human-readable description of state

        Args:
            state: State tuple

        Returns:
            Readable description
        """
        endpoint_hash, hour, day, days_bucket, failure_bucket, health_bucket = state

        day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

        return (
            f"endpoint#{endpoint_hash}, "
            f"{day_names[day]} {hour:02d}:00, "
            f"changed:{days_bucket}, "
            f"failures:{failure_bucket}, "
            f"deps:{health_bucket}"
        )
