"""
Adaptive Learning System
Learns from test patterns, failures, and successes to continuously improve
Similar to how Claude Code learns from user interactions and code patterns
"""
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict
from loguru import logger

from src.cache.cache_manager import CacheManager


@dataclass
class Pattern:
    """Learned pattern from test execution"""
    pattern_type: str  # "failure_pattern", "success_pattern", "performance_pattern"
    endpoint_key: str
    conditions: Dict[str, Any]  # Conditions when pattern applies
    actions: Dict[str, Any]  # Recommended actions
    confidence: float  # 0-1 confidence score
    occurrences: int  # How many times seen
    last_seen: str  # ISO timestamp
    success_rate: float  # How often this pattern's action succeeds


@dataclass
class Insight:
    """Learned insight about the API or testing strategy"""
    insight_type: str  # "test_strategy", "data_generation", "endpoint_behavior"
    description: str
    evidence: List[Dict[str, Any]]
    confidence: float
    actionable: bool  # Can we act on this insight?
    recommendation: Optional[str]


class AdaptiveLearner:
    """
    Learns from test execution patterns to continuously improve

    Learning capabilities:
    - Identifies failure patterns (when/why tests fail)
    - Learns successful test strategies
    - Detects API behavior patterns
    - Predicts optimal test data
    - Adapts testing approach based on results
    - Recognizes flaky tests
    - Learns performance baselines
    """

    def __init__(self):
        self.cache = CacheManager(namespace="autotest:learning", default_ttl=86400 * 30)  # 30 days
        self.patterns: Dict[str, Pattern] = {}
        self.insights: List[Insight] = []
        self.load_learned_patterns()

    def learn_from_test_result(
        self,
        endpoint_key: str,
        test_config: Dict[str, Any],
        result: Dict[str, Any]
    ):
        """
        Learn from a test result

        Args:
            endpoint_key: Endpoint that was tested
            test_config: How the test was configured
            result: Test result (success, failures, timing, etc)
        """
        success = result.get('success', False)
        status_code = result.get('status_code', 0)
        elapsed_time = result.get('elapsed_time', 0)
        payload = result.get('final_payload', {})
        attempts = result.get('attempts', 1)

        # Learn different aspects
        self._learn_failure_patterns(endpoint_key, test_config, result, success)
        self._learn_success_patterns(endpoint_key, test_config, result, success)
        self._learn_performance_patterns(endpoint_key, result, elapsed_time)
        self._learn_data_patterns(endpoint_key, payload, success)
        self._detect_flakiness(endpoint_key, result, attempts)

        # Persist patterns periodically
        self._persist_patterns()

    def _learn_failure_patterns(
        self,
        endpoint_key: str,
        test_config: Dict[str, Any],
        result: Dict[str, Any],
        success: bool
    ):
        """Learn patterns from test failures"""
        if success:
            return  # Only learn from failures

        pattern_id = f"failure:{endpoint_key}"

        # Extract failure conditions
        conditions = {
            'status_code': result.get('status_code'),
            'error_type': result.get('error', {}).get('type') if isinstance(result.get('error'), dict) else None,
            'payload_type': type(result.get('final_payload', {})).__name__
        }

        # Determine recommended action
        status = result.get('status_code', 0)
        if status == 400:
            action = {'type': 'validate_payload', 'reason': 'Bad request - payload validation issue'}
        elif status == 401:
            action = {'type': 'add_authentication', 'reason': 'Unauthorized - missing or invalid auth'}
        elif status == 404:
            action = {'type': 'create_prerequisite', 'reason': 'Not found - may need to create resource first'}
        elif status == 422:
            action = {'type': 'fix_data_format', 'reason': 'Unprocessable - data format issue'}
        else:
            action = {'type': 'investigate', 'reason': f'Unexpected status {status}'}

        # Update or create pattern
        if pattern_id in self.patterns:
            pattern = self.patterns[pattern_id]
            pattern.occurrences += 1
            pattern.last_seen = datetime.now().isoformat()
            # Update confidence based on consistency
            pattern.confidence = min(1.0, pattern.confidence + 0.05)
        else:
            pattern = Pattern(
                pattern_type="failure_pattern",
                endpoint_key=endpoint_key,
                conditions=conditions,
                actions=action,
                confidence=0.3,
                occurrences=1,
                last_seen=datetime.now().isoformat(),
                success_rate=0.0
            )
            self.patterns[pattern_id] = pattern

        logger.debug(f"Learned failure pattern for {endpoint_key}: {action['reason']}")

    def _learn_success_patterns(
        self,
        endpoint_key: str,
        test_config: Dict[str, Any],
        result: Dict[str, Any],
        success: bool
    ):
        """Learn patterns from successful tests"""
        if not success:
            return  # Only learn from successes

        pattern_id = f"success:{endpoint_key}"

        # Extract success conditions
        conditions = {
            'test_type': test_config.get('test_type', 'positive'),
            'has_auth': bool(result.get('request_headers', {}).get('Authorization')),
            'payload_structure': self._extract_payload_structure(result.get('final_payload', {}))
        }

        actions = {
            'type': 'repeat_strategy',
            'reason': 'This approach works reliably',
            'template': result.get('final_payload', {})
        }

        # Update or create pattern
        if pattern_id in self.patterns:
            pattern = self.patterns[pattern_id]
            pattern.occurrences += 1
            pattern.last_seen = datetime.now().isoformat()
            pattern.success_rate = (pattern.success_rate * (pattern.occurrences - 1) + 1.0) / pattern.occurrences
            pattern.confidence = min(1.0, pattern.success_rate)
        else:
            pattern = Pattern(
                pattern_type="success_pattern",
                endpoint_key=endpoint_key,
                conditions=conditions,
                actions=actions,
                confidence=0.5,
                occurrences=1,
                last_seen=datetime.now().isoformat(),
                success_rate=1.0
            )
            self.patterns[pattern_id] = pattern

    def _learn_performance_patterns(
        self,
        endpoint_key: str,
        result: Dict[str, Any],
        elapsed_time: float
    ):
        """Learn performance characteristics"""
        pattern_id = f"performance:{endpoint_key}"

        # Classify performance
        if elapsed_time < 0.5:
            perf_class = "fast"
        elif elapsed_time < 2.0:
            perf_class = "normal"
        elif elapsed_time < 5.0:
            perf_class = "slow"
        else:
            perf_class = "very_slow"

        conditions = {
            'performance_class': perf_class,
            'avg_time_ms': elapsed_time * 1000
        }

        actions = {
            'type': 'performance_baseline',
            'baseline_ms': elapsed_time * 1000,
            'alert_threshold_ms': elapsed_time * 1000 * 1.5  # Alert if 50% slower
        }

        # Update or create pattern
        if pattern_id in self.patterns:
            pattern = self.patterns[pattern_id]
            # Update rolling average
            old_avg = pattern.conditions.get('avg_time_ms', elapsed_time * 1000)
            new_avg = (old_avg * pattern.occurrences + elapsed_time * 1000) / (pattern.occurrences + 1)
            pattern.conditions['avg_time_ms'] = new_avg
            pattern.actions['baseline_ms'] = new_avg
            pattern.actions['alert_threshold_ms'] = new_avg * 1.5
            pattern.occurrences += 1
            pattern.last_seen = datetime.now().isoformat()
        else:
            pattern = Pattern(
                pattern_type="performance_pattern",
                endpoint_key=endpoint_key,
                conditions=conditions,
                actions=actions,
                confidence=0.5,
                occurrences=1,
                last_seen=datetime.now().isoformat(),
                success_rate=1.0
            )
            self.patterns[pattern_id] = pattern

    def _learn_data_patterns(
        self,
        endpoint_key: str,
        payload: Dict[str, Any],
        success: bool
    ):
        """Learn what kind of test data works"""
        if not success or not payload:
            return

        pattern_id = f"data:{endpoint_key}"

        # Extract data characteristics
        data_profile = {
            'fields': list(payload.keys()),
            'field_types': {k: type(v).__name__ for k, v in payload.items()},
            'complexity': len(payload)
        }

        actions = {
            'type': 'use_similar_data',
            'template': payload,
            'profile': data_profile
        }

        if pattern_id in self.patterns:
            pattern = self.patterns[pattern_id]
            pattern.occurrences += 1
            pattern.last_seen = datetime.now().isoformat()
        else:
            pattern = Pattern(
                pattern_type="data_pattern",
                endpoint_key=endpoint_key,
                conditions=data_profile,
                actions=actions,
                confidence=0.5,
                occurrences=1,
                last_seen=datetime.now().isoformat(),
                success_rate=1.0
            )
            self.patterns[pattern_id] = pattern

    def _detect_flakiness(
        self,
        endpoint_key: str,
        result: Dict[str, Any],
        attempts: int
    ):
        """Detect if an endpoint is flaky (intermittent failures)"""
        pattern_id = f"flakiness:{endpoint_key}"

        # If it took multiple attempts, it might be flaky
        if attempts > 1:
            if pattern_id in self.patterns:
                pattern = self.patterns[pattern_id]
                pattern.occurrences += 1
                pattern.last_seen = datetime.now().isoformat()
                pattern.confidence = min(1.0, pattern.occurrences / 10.0)  # High confidence after 10 occurrences
            else:
                pattern = Pattern(
                    pattern_type="flakiness_pattern",
                    endpoint_key=endpoint_key,
                    conditions={'attempts_needed': attempts},
                    actions={
                        'type': 'increase_retries',
                        'reason': 'Endpoint shows flaky behavior',
                        'recommended_retries': min(attempts + 2, 10)
                    },
                    confidence=0.1,
                    occurrences=1,
                    last_seen=datetime.now().isoformat(),
                    success_rate=0.0
                )
                self.patterns[pattern_id] = pattern

            logger.warning(f"⚠️ Flakiness detected for {endpoint_key} (needed {attempts} attempts)")

    def get_recommendations(self, endpoint_key: str) -> List[Dict[str, Any]]:
        """
        Get learned recommendations for testing an endpoint

        Args:
            endpoint_key: Endpoint to get recommendations for

        Returns:
            List of recommendations based on learned patterns
        """
        recommendations = []

        # Check all patterns for this endpoint
        for pattern_id, pattern in self.patterns.items():
            if pattern.endpoint_key == endpoint_key and pattern.confidence > 0.5:
                recommendations.append({
                    'type': pattern.pattern_type,
                    'action': pattern.actions,
                    'confidence': pattern.confidence,
                    'based_on': f"{pattern.occurrences} occurrences"
                })

        # Sort by confidence
        recommendations.sort(key=lambda x: x['confidence'], reverse=True)

        return recommendations

    def generate_insights(self) -> List[Insight]:
        """
        Generate high-level insights from learned patterns

        Returns:
            List of actionable insights
        """
        insights = []

        # Find endpoints with high failure rates
        failure_endpoints = defaultdict(int)
        success_endpoints = defaultdict(int)

        for pattern_id, pattern in self.patterns.items():
            if pattern.pattern_type == "failure_pattern":
                failure_endpoints[pattern.endpoint_key] += pattern.occurrences
            elif pattern.pattern_type == "success_pattern":
                success_endpoints[pattern.endpoint_key] += pattern.occurrences

        # Identify problematic endpoints
        for endpoint, failures in failure_endpoints.items():
            successes = success_endpoints.get(endpoint, 0)
            total = failures + successes
            if total > 5 and failures / total > 0.5:  # More than 50% failure rate
                insight = Insight(
                    insight_type="test_strategy",
                    description=f"{endpoint} has high failure rate ({failures}/{total})",
                    evidence=[{'failures': failures, 'successes': successes}],
                    confidence=min(1.0, total / 20.0),
                    actionable=True,
                    recommendation="Review test data generation or API expectations for this endpoint"
                )
                insights.append(insight)

        # Find flaky endpoints
        flaky_count = sum(1 for p in self.patterns.values() if p.pattern_type == "flakiness_pattern" and p.confidence > 0.5)
        if flaky_count > 0:
            insight = Insight(
                insight_type="endpoint_behavior",
                description=f"Found {flaky_count} flaky endpoints requiring retries",
                evidence=[{'flaky_endpoints': flaky_count}],
                confidence=0.8,
                actionable=True,
                recommendation="Consider implementing retry logic with exponential backoff for these endpoints"
            )
            insights.append(insight)

        # Performance insights
        slow_endpoints = [
            p for p in self.patterns.values()
            if p.pattern_type == "performance_pattern"
            and p.conditions.get('avg_time_ms', 0) > 2000
        ]
        if slow_endpoints:
            insight = Insight(
                insight_type="endpoint_behavior",
                description=f"Found {len(slow_endpoints)} slow endpoints (>2s average)",
                evidence=[{
                    'endpoint': p.endpoint_key,
                    'avg_ms': p.conditions.get('avg_time_ms')
                } for p in slow_endpoints[:5]],
                confidence=0.9,
                actionable=True,
                recommendation="Monitor these endpoints for performance degradation"
            )
            insights.append(insight)

        self.insights = insights
        return insights

    def _extract_payload_structure(self, payload: Dict[str, Any]) -> str:
        """Extract structural signature of payload"""
        if not payload:
            return "empty"

        fields = sorted(payload.keys())
        return f"{len(fields)}_fields:{','.join(fields[:5])}"  # First 5 fields

    def _persist_patterns(self):
        """Save learned patterns to cache"""
        try:
            patterns_data = {
                pattern_id: asdict(pattern)
                for pattern_id, pattern in self.patterns.items()
            }
            self.cache.set('learned_patterns', patterns_data, ttl=86400 * 30)  # 30 days
        except Exception as e:
            logger.warning(f"Failed to persist patterns: {e}")

    def load_learned_patterns(self):
        """Load previously learned patterns from cache"""
        try:
            patterns_data = self.cache.get('learned_patterns')
            if patterns_data:
                self.patterns = {
                    pattern_id: Pattern(**pattern_dict)
                    for pattern_id, pattern_dict in patterns_data.items()
                }
                logger.info(f"✅ Loaded {len(self.patterns)} learned patterns")
            else:
                logger.info("No previous patterns found, starting fresh")
        except Exception as e:
            logger.warning(f"Failed to load patterns: {e}")
            self.patterns = {}

    def get_statistics(self) -> Dict[str, Any]:
        """Get learning statistics"""
        pattern_types = defaultdict(int)
        for pattern in self.patterns.values():
            pattern_types[pattern.pattern_type] += 1

        total_occurrences = sum(p.occurrences for p in self.patterns.values())

        return {
            'total_patterns': len(self.patterns),
            'total_occurrences': total_occurrences,
            'pattern_types': dict(pattern_types),
            'high_confidence_patterns': sum(1 for p in self.patterns.values() if p.confidence > 0.7),
            'insights_generated': len(self.insights)
        }


# Global learner instance
_learner: Optional[AdaptiveLearner] = None


def get_adaptive_learner() -> AdaptiveLearner:
    """Get or create global learner instance"""
    global _learner
    if _learner is None:
        _learner = AdaptiveLearner()
    return _learner
