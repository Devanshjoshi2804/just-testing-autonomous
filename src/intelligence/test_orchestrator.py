"""
Intelligent Test Orchestrator
AI-powered test execution engine that makes smart decisions about testing strategy
Similar to how Claude Code intelligently orchestrates development workflows
"""
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from loguru import logger

from src.agents.base_agent import BaseAgent
from src.observability.tracing import start_span


class TestPriority(Enum):
    """Test priority levels"""
    CRITICAL = "critical"  # Must test immediately
    HIGH = "high"          # Test soon
    MEDIUM = "medium"      # Test when convenient
    LOW = "low"            # Can defer
    SKIP = "skip"          # Safe to skip


class TestStrategy(Enum):
    """Test execution strategies"""
    COMPREHENSIVE = "comprehensive"  # Full deep testing
    TARGETED = "targeted"           # Focus on changed areas
    SMOKE = "smoke"                 # Quick validation
    REGRESSION = "regression"       # Focus on previous failures
    ADAPTIVE = "adaptive"           # AI decides strategy


@dataclass
class TestDecision:
    """AI decision about how to test an endpoint"""
    endpoint_key: str
    priority: TestPriority
    strategy: TestStrategy
    test_count: int  # How many tests to generate
    reason: str      # Why this decision was made
    confidence: float  # 0-1 confidence in decision
    estimated_duration: float  # Seconds
    risk_score: float  # 0-1 risk if not tested


@dataclass
class ApiChangeSignal:
    """Signal indicating API might have changed"""
    endpoint_key: str
    signal_type: str  # "schema_change", "behavior_change", "performance_degradation"
    confidence: float
    evidence: Dict[str, Any]
    detected_at: datetime


class IntelligentTestOrchestrator(BaseAgent):
    """
    AI-powered test orchestrator that makes intelligent decisions about testing

    Similar to Claude Code's intelligent workflow orchestration:
    - Analyzes context to decide what needs testing
    - Prioritizes tests based on risk and value
    - Adapts strategy based on results
    - Learns from patterns over time
    - Optimizes for efficiency and coverage
    """

    def __init__(self):
        super().__init__(agent_name="TestOrchestrator", use_fast_llm=False)
        self.test_history: Dict[str, List[Dict]] = {}  # endpoint -> test results
        self.change_signals: List[ApiChangeSignal] = []
        self.performance_baseline: Dict[str, float] = {}  # endpoint -> avg latency

    async def analyze_and_decide(
        self,
        endpoints: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[TestDecision]:
        """
        Analyze endpoints and make intelligent testing decisions

        Args:
            endpoints: List of endpoints to consider
            context: Context about the testing session

        Returns:
            List of decisions for each endpoint
        """
        with start_span(
            "orchestrator.analyze_and_decide",
            attributes={
                "endpoint_count": len(endpoints),
                "has_previous_tests": len(self.test_history) > 0
            }
        ):
            logger.info(f"🧠 Orchestrator analyzing {len(endpoints)} endpoints...")

            decisions = []

            for endpoint in endpoints:
                decision = await self._decide_for_endpoint(endpoint, context)
                decisions.append(decision)

            # Sort by priority and risk
            decisions.sort(
                key=lambda d: (d.priority.value, -d.risk_score),
                reverse=False
            )

            # Log summary
            priority_counts = {}
            for d in decisions:
                priority_counts[d.priority.value] = priority_counts.get(d.priority.value, 0) + 1

            logger.info(f"📊 Test decisions: {priority_counts}")

            return decisions

    async def _decide_for_endpoint(
        self,
        endpoint: Dict[str, Any],
        context: Dict[str, Any]
    ) -> TestDecision:
        """Make intelligent decision for a single endpoint"""
        endpoint_key = f"{endpoint.get('method')} {endpoint.get('path')}"

        # Gather intelligence
        has_previous_failures = self._has_recent_failures(endpoint_key)
        has_change_signals = self._has_change_signals(endpoint_key)
        is_critical_path = self._is_critical_path(endpoint)
        complexity_score = self._assess_complexity(endpoint)
        time_since_last_test = self._time_since_last_test(endpoint_key)

        # Build analysis prompt for AI
        analysis = await self._ai_analyze_endpoint(
            endpoint,
            has_previous_failures,
            has_change_signals,
            is_critical_path,
            complexity_score,
            time_since_last_test
        )

        # Parse AI decision
        decision = self._parse_ai_decision(endpoint_key, analysis, endpoint)

        logger.debug(
            f"Decision for {endpoint_key}: {decision.priority.value} "
            f"({decision.strategy.value}, {decision.test_count} tests, "
            f"risk={decision.risk_score:.2f})"
        )

        return decision

    async def _ai_analyze_endpoint(
        self,
        endpoint: Dict[str, Any],
        has_previous_failures: bool,
        has_change_signals: bool,
        is_critical_path: bool,
        complexity_score: float,
        time_since_last_test: Optional[float]
    ) -> str:
        """Use AI to analyze endpoint and decide testing approach"""

        endpoint_key = f"{endpoint.get('method')} {endpoint.get('path')}"

        prompt = f"""Analyze this API endpoint and decide the optimal testing strategy.

ENDPOINT: {endpoint_key}
Method: {endpoint.get('method')}
Summary: {endpoint.get('summary', 'N/A')}
Parameters: {len(endpoint.get('parameters', []))}
Auth Required: {endpoint.get('auth_required', False)}

INTELLIGENCE:
- Previous Failures: {'YES - needs attention' if has_previous_failures else 'No'}
- Change Signals: {'YES - API may have changed' if has_change_signals else 'No'}
- Critical Path: {'YES - high business impact' if is_critical_path else 'No'}
- Complexity Score: {complexity_score:.2f}/1.0 (higher = more complex)
- Time Since Last Test: {time_since_last_test or 'Never tested'}

Based on this intelligence, decide:
1. PRIORITY: critical/high/medium/low/skip
2. STRATEGY: comprehensive/targeted/smoke/regression/adaptive
3. TEST_COUNT: How many test variations to generate (1-50)
4. REASON: 1-2 sentence explanation
5. RISK_SCORE: 0-1 score of risk if not tested

Respond ONLY with JSON:
{{"priority": "...", "strategy": "...", "test_count": N, "reason": "...", "risk_score": 0.X, "confidence": 0.X}}"""

        try:
            response = self.invoke(prompt)
            return response
        except Exception as e:
            logger.warning(f"AI analysis failed for {endpoint_key}: {e}")
            # Fallback to safe defaults
            return '{"priority": "medium", "strategy": "targeted", "test_count": 5, "reason": "Default fallback", "risk_score": 0.5, "confidence": 0.3}'

    def _parse_ai_decision(
        self,
        endpoint_key: str,
        ai_response: str,
        endpoint: Dict[str, Any]
    ) -> TestDecision:
        """Parse AI response into TestDecision"""
        import json
        import re

        try:
            # Extract JSON from response (might have markdown)
            json_match = re.search(r'\{[^{}]*\}', ai_response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(ai_response)

            priority = TestPriority(data.get('priority', 'medium'))
            strategy = TestStrategy(data.get('strategy', 'targeted'))
            test_count = min(50, max(1, int(data.get('test_count', 5))))
            reason = data.get('reason', 'AI decision')
            risk_score = float(data.get('risk_score', 0.5))
            confidence = float(data.get('confidence', 0.5))

            # Estimate duration (rough: 2s per test)
            estimated_duration = test_count * 2.0

            return TestDecision(
                endpoint_key=endpoint_key,
                priority=priority,
                strategy=strategy,
                test_count=test_count,
                reason=reason,
                confidence=confidence,
                estimated_duration=estimated_duration,
                risk_score=risk_score
            )

        except Exception as e:
            logger.warning(f"Failed to parse AI decision: {e}")
            # Fallback
            return TestDecision(
                endpoint_key=endpoint_key,
                priority=TestPriority.MEDIUM,
                strategy=TestStrategy.TARGETED,
                test_count=5,
                reason="Fallback decision",
                confidence=0.3,
                estimated_duration=10.0,
                risk_score=0.5
            )

    def _has_recent_failures(self, endpoint_key: str) -> bool:
        """Check if endpoint has recent test failures"""
        if endpoint_key not in self.test_history:
            return False

        recent_tests = self.test_history[endpoint_key][-5:]  # Last 5 tests
        failures = [t for t in recent_tests if not t.get('success', False)]
        return len(failures) > 0

    def _has_change_signals(self, endpoint_key: str) -> bool:
        """Check if there are signals indicating API changes"""
        for signal in self.change_signals:
            if signal.endpoint_key == endpoint_key:
                # Check if signal is recent (last 24 hours)
                if (datetime.now() - signal.detected_at) < timedelta(hours=24):
                    return True
        return False

    def _is_critical_path(self, endpoint: Dict[str, Any]) -> bool:
        """Determine if endpoint is on critical business path"""
        path = endpoint.get('path', '')
        method = endpoint.get('method', 'GET')

        # Heuristics for critical paths
        critical_keywords = ['payment', 'order', 'checkout', 'auth', 'login', 'register']
        critical_methods = ['POST', 'PUT', 'DELETE']

        is_critical = any(kw in path.lower() for kw in critical_keywords)
        is_critical = is_critical or (method in critical_methods)

        return is_critical

    def _assess_complexity(self, endpoint: Dict[str, Any]) -> float:
        """Assess endpoint complexity (0-1 score)"""
        score = 0.0

        # More parameters = more complex
        param_count = len(endpoint.get('parameters', []))
        score += min(0.3, param_count * 0.05)

        # Auth required = more complex
        if endpoint.get('auth_required', False):
            score += 0.2

        # POST/PUT/DELETE more complex than GET
        if endpoint.get('method') in ['POST', 'PUT', 'DELETE']:
            score += 0.3

        # Path parameters add complexity
        if '{' in endpoint.get('path', ''):
            score += 0.2

        return min(1.0, score)

    def _time_since_last_test(self, endpoint_key: str) -> Optional[float]:
        """Get hours since last test of this endpoint"""
        if endpoint_key not in self.test_history:
            return None

        if not self.test_history[endpoint_key]:
            return None

        last_test = self.test_history[endpoint_key][-1]
        last_time = last_test.get('tested_at')

        if not last_time:
            return None

        if isinstance(last_time, str):
            last_time = datetime.fromisoformat(last_time)

        delta = datetime.now() - last_time
        return delta.total_seconds() / 3600  # Return hours

    def record_test_result(
        self,
        endpoint_key: str,
        result: Dict[str, Any]
    ):
        """Record test result for learning"""
        if endpoint_key not in self.test_history:
            self.test_history[endpoint_key] = []

        result['tested_at'] = datetime.now().isoformat()
        self.test_history[endpoint_key].append(result)

        # Keep only last 100 results per endpoint
        self.test_history[endpoint_key] = self.test_history[endpoint_key][-100:]

        # Update performance baseline
        if 'elapsed_time' in result:
            self._update_performance_baseline(endpoint_key, result['elapsed_time'])

        # Detect change signals
        self._detect_changes(endpoint_key, result)

    def _update_performance_baseline(self, endpoint_key: str, latency: float):
        """Update rolling average of performance"""
        if endpoint_key not in self.performance_baseline:
            self.performance_baseline[endpoint_key] = latency
        else:
            # Exponential moving average
            alpha = 0.3
            self.performance_baseline[endpoint_key] = (
                alpha * latency + (1 - alpha) * self.performance_baseline[endpoint_key]
            )

    def _detect_changes(self, endpoint_key: str, result: Dict[str, Any]):
        """Detect if API behavior has changed"""
        # Performance degradation detection
        if 'elapsed_time' in result and endpoint_key in self.performance_baseline:
            baseline = self.performance_baseline[endpoint_key]
            current = result['elapsed_time']

            # If 50% slower than baseline, signal performance degradation
            if current > baseline * 1.5:
                signal = ApiChangeSignal(
                    endpoint_key=endpoint_key,
                    signal_type="performance_degradation",
                    confidence=min(1.0, (current - baseline) / baseline),
                    evidence={
                        "baseline_ms": baseline * 1000,
                        "current_ms": current * 1000,
                        "degradation_percent": ((current - baseline) / baseline) * 100
                    },
                    detected_at=datetime.now()
                )
                self.change_signals.append(signal)
                logger.warning(
                    f"⚠️ Performance degradation detected: {endpoint_key} "
                    f"({current*1000:.0f}ms vs baseline {baseline*1000:.0f}ms)"
                )

        # Schema change detection (status code changed)
        if endpoint_key in self.test_history and len(self.test_history[endpoint_key]) > 1:
            prev_status = self.test_history[endpoint_key][-2].get('status_code')
            curr_status = result.get('status_code')

            if prev_status and curr_status and prev_status != curr_status:
                signal = ApiChangeSignal(
                    endpoint_key=endpoint_key,
                    signal_type="behavior_change",
                    confidence=0.8,
                    evidence={
                        "previous_status": prev_status,
                        "current_status": curr_status
                    },
                    detected_at=datetime.now()
                )
                self.change_signals.append(signal)
                logger.warning(
                    f"⚠️ Behavior change detected: {endpoint_key} "
                    f"(status {prev_status} → {curr_status})"
                )

    def get_intelligence_summary(self) -> Dict[str, Any]:
        """Get summary of orchestrator's intelligence"""
        return {
            "endpoints_tracked": len(self.test_history),
            "total_tests_recorded": sum(len(tests) for tests in self.test_history.values()),
            "change_signals": len(self.change_signals),
            "recent_signals": [
                {
                    "endpoint": s.endpoint_key,
                    "type": s.signal_type,
                    "confidence": s.confidence,
                    "detected_at": s.detected_at.isoformat()
                }
                for s in self.change_signals[-10:]  # Last 10 signals
            ],
            "performance_baselines": len(self.performance_baseline)
        }


# Global orchestrator instance
_orchestrator: Optional[IntelligentTestOrchestrator] = None


def get_orchestrator() -> IntelligentTestOrchestrator:
    """Get or create global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = IntelligentTestOrchestrator()
    return _orchestrator
