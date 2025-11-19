"""
Hybrid Intelligence Coordinator
Combines existing RL optimizer with new AI intelligence for best-of-both-worlds
Uses RL for low-level decisions, LLM for strategic reasoning, learning for patterns
"""
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger

from src.intelligence.test_orchestrator import get_orchestrator, TestPriority, TestStrategy
from src.intelligence.semantic_analyzer import get_semantic_analyzer
from src.intelligence.adaptive_learner import get_adaptive_learner
from src.rl.test_optimizer import TestOptimizer
from src.observability.tracing import start_span


class HybridIntelligence:
    """
    Coordinates existing RL optimizer with new AI intelligence modules

    Architecture:
    - RL Optimizer: Fast, proven Q-learning for action selection
    - LLM Orchestrator: Strategic reasoning and context understanding
    - Semantic Analyzer: Deep API structure analysis
    - Adaptive Learner: Pattern recognition and recommendations

    Decision Flow:
    1. Semantic Analyzer understands API structure
    2. Adaptive Learner provides pattern-based recommendations
    3. LLM Orchestrator makes strategic decisions
    4. RL Optimizer fine-tunes with learned Q-values
    5. Results fed back to both learners
    """

    def __init__(
        self,
        use_rl: bool = True,
        use_llm: bool = True,
        use_patterns: bool = True
    ):
        """
        Initialize hybrid intelligence system

        Args:
            use_rl: Enable RL optimizer (default True)
            use_llm: Enable LLM orchestrator (default True)
            use_patterns: Enable pattern learning (default True)
        """
        self.use_rl = use_rl
        self.use_llm = use_llm
        self.use_patterns = use_patterns

        # Initialize components
        self.rl_optimizer = TestOptimizer() if use_rl else None
        self.llm_orchestrator = get_orchestrator() if use_llm else None
        self.semantic_analyzer = get_semantic_analyzer()
        self.pattern_learner = get_adaptive_learner() if use_patterns else None

        logger.info(
            f"🧠 Hybrid Intelligence initialized: "
            f"RL={use_rl}, LLM={use_llm}, Patterns={use_patterns}"
        )

    async def analyze_and_prioritize(
        self,
        endpoints: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Hybrid analysis combining all intelligence sources

        Args:
            endpoints: List of endpoints to analyze
            context: Context information (session, previous results, etc)

        Returns:
            List of (endpoint_key, metadata) tuples sorted by priority
        """
        with start_span(
            "hybrid_intelligence.analyze",
            attributes={
                "endpoint_count": len(endpoints),
                "use_rl": self.use_rl,
                "use_llm": self.use_llm
            }
        ):
            logger.info(f"🧠 Hybrid Intelligence analyzing {len(endpoints)} endpoints...")

            # STEP 1: Semantic analysis (understand structure)
            semantic_results = await self._semantic_analysis(endpoints, context)

            # STEP 2: Pattern-based recommendations
            pattern_recommendations = self._get_pattern_recommendations(endpoints) if self.use_patterns else {}

            # STEP 3: LLM strategic decisions (if enabled)
            llm_decisions = await self._llm_strategic_decisions(endpoints, context, semantic_results) if self.use_llm else {}

            # STEP 4: RL tactical optimization (if enabled)
            rl_priorities = self._rl_tactical_optimization(endpoints, context, llm_decisions) if self.use_rl else {}

            # STEP 5: Combine all intelligence sources
            final_priorities = self._combine_intelligence(
                endpoints,
                semantic_results,
                pattern_recommendations,
                llm_decisions,
                rl_priorities
            )

            logger.info(f"✅ Hybrid Intelligence complete: {len(final_priorities)} endpoints prioritized")

            return final_priorities

    async def _semantic_analysis(
        self,
        endpoints: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use semantic analyzer to understand API structure"""

        # Only analyze if not already done
        if not self.semantic_analyzer.entities:
            logger.info("🔍 Running semantic analysis...")
            await self.semantic_analyzer.analyze_api_structure(endpoints)

        # Get insights
        results = {}
        for endpoint in endpoints:
            endpoint_key = f"{endpoint.get('method')} {endpoint.get('path')}"

            # Get dependencies
            dependencies = self.semantic_analyzer.get_endpoint_dependencies(endpoint_key)

            # Get semantics
            semantics = self.semantic_analyzer.endpoint_semantics.get(endpoint_key)

            results[endpoint_key] = {
                'dependencies': dependencies,
                'business_value': semantics.business_value if semantics else 0.5,
                'user_journey_stage': semantics.user_journey_stage if semantics else 'core_functionality',
                'has_dependencies': len(dependencies) > 0
            }

        return results

    def _get_pattern_recommendations(
        self,
        endpoints: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get recommendations from learned patterns"""

        recommendations = {}
        for endpoint in endpoints:
            endpoint_key = f"{endpoint.get('method')} {endpoint.get('path')}"
            recs = self.pattern_learner.get_recommendations(endpoint_key)
            if recs:
                recommendations[endpoint_key] = recs
                logger.debug(f"📚 {len(recs)} patterns found for {endpoint_key}")

        return recommendations

    async def _llm_strategic_decisions(
        self,
        endpoints: List[Dict[str, Any]],
        context: Dict[str, Any],
        semantic_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use LLM for high-level strategic decisions"""

        # Build enhanced context with semantic insights
        enhanced_context = {
            **context,
            'semantic_insights': semantic_results
        }

        # Get LLM decisions
        decisions = await self.llm_orchestrator.analyze_and_decide(
            endpoints,
            enhanced_context
        )

        # Convert to dict
        decision_map = {}
        for decision in decisions:
            decision_map[decision.endpoint_key] = {
                'priority': decision.priority,
                'strategy': decision.strategy,
                'test_count': decision.test_count,
                'reason': decision.reason,
                'confidence': decision.confidence,
                'risk_score': decision.risk_score
            }

        return decision_map

    def _rl_tactical_optimization(
        self,
        endpoints: List[Dict[str, Any]],
        context: Dict[str, Any],
        llm_decisions: Dict[str, Any]
    ) -> Dict[str, str]:
        """Use RL for fine-tuned tactical decisions"""

        # Enrich endpoint metadata with LLM insights
        enriched = []
        for endpoint in endpoints:
            endpoint_key = f"{endpoint.get('method')} {endpoint.get('path')}"
            endpoint_copy = endpoint.copy()

            # Add LLM insights to metadata
            if endpoint_key in llm_decisions:
                llm_decision = llm_decisions[endpoint_key]
                endpoint_copy['llm_priority'] = llm_decision['priority'].value
                endpoint_copy['llm_risk_score'] = llm_decision['risk_score']

            enriched.append(endpoint_copy)

        # Build RL context
        rl_context = self._build_rl_context(context)

        # Get RL priorities
        ordered = self.rl_optimizer.prioritize_endpoints(enriched, rl_context)

        # Extract RL priorities
        priorities = {}
        for ep in ordered:
            endpoint_key = f"{ep.get('method')} {ep.get('path')}"
            priorities[endpoint_key] = ep.get('rl_priority', 'normal')

        return priorities

    def _combine_intelligence(
        self,
        endpoints: List[Dict[str, Any]],
        semantic_results: Dict[str, Any],
        pattern_recommendations: Dict[str, List],
        llm_decisions: Dict[str, Any],
        rl_priorities: Dict[str, str]
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Combine all intelligence sources into final decision

        Priority hierarchy:
        1. Patterns showing critical failures → CRITICAL
        2. LLM strategic importance → Use LLM priority
        3. RL learned priorities → Fine-tune ordering
        4. Semantic business value → Tie-breaker
        """

        final_list = []

        for endpoint in endpoints:
            endpoint_key = f"{endpoint.get('method')} {endpoint.get('path')}"

            # Gather intelligence
            semantic = semantic_results.get(endpoint_key, {})
            patterns = pattern_recommendations.get(endpoint_key, [])
            llm_decision = llm_decisions.get(endpoint_key, {})
            rl_priority = rl_priorities.get(endpoint_key, 'normal')

            # Determine final priority
            final_priority = self._determine_final_priority(
                semantic, patterns, llm_decision, rl_priority
            )

            # Build metadata
            metadata = {
                'final_priority': final_priority,
                'business_value': semantic.get('business_value', 0.5),
                'has_dependencies': semantic.get('has_dependencies', False),
                'pattern_count': len(patterns),
                'llm_strategy': llm_decision.get('strategy'),
                'llm_confidence': llm_decision.get('confidence', 0.0),
                'rl_priority': rl_priority,
                'test_count': llm_decision.get('test_count', 5),
                'reason': self._build_reason(semantic, patterns, llm_decision, rl_priority)
            }

            final_list.append((endpoint_key, metadata))

        # Sort by priority and business value
        priority_order = {'critical': 0, 'high': 1, 'normal': 2, 'low': 3, 'skip': 4}
        final_list.sort(
            key=lambda x: (
                priority_order.get(x[1]['final_priority'], 2),
                -x[1]['business_value']
            )
        )

        return final_list

    def _determine_final_priority(
        self,
        semantic: Dict[str, Any],
        patterns: List[Dict[str, Any]],
        llm_decision: Dict[str, Any],
        rl_priority: str
    ) -> str:
        """Determine final priority from all sources"""

        # Check patterns for critical issues
        for pattern in patterns:
            if pattern['type'] == 'failure_pattern' and pattern['confidence'] > 0.7:
                return 'critical'  # High-confidence failure pattern → test ASAP

        # Use LLM decision if available and confident
        if llm_decision and llm_decision.get('confidence', 0) > 0.6:
            llm_priority = llm_decision['priority']
            if llm_priority == TestPriority.CRITICAL:
                return 'critical'
            elif llm_priority == TestPriority.HIGH:
                return 'high'
            elif llm_priority == TestPriority.SKIP:
                # Double-check with RL before skipping
                if rl_priority == 'skip':
                    return 'skip'
                else:
                    return 'low'  # RL says don't skip, so downgrade to low
            else:
                return rl_priority  # Use RL for normal/low decisions

        # Fallback to RL
        return rl_priority

    def _build_reason(
        self,
        semantic: Dict[str, Any],
        patterns: List[Dict[str, Any]],
        llm_decision: Dict[str, Any],
        rl_priority: str
    ) -> str:
        """Build human-readable explanation for decision"""

        reasons = []

        if patterns:
            reasons.append(f"{len(patterns)} learned patterns")

        if semantic.get('business_value', 0) > 0.7:
            reasons.append("high business value")

        if llm_decision.get('reason'):
            reasons.append(llm_decision['reason'])

        if rl_priority in ['critical', 'skip']:
            reasons.append(f"RL: {rl_priority}")

        return "; ".join(reasons) if reasons else "Standard testing"

    def _build_rl_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Build context dict for RL optimizer"""

        return {
            'session_id': context.get('session_id', 'unknown'),
            'time_budget': context.get('time_budget', 300),  # 5 minutes default
            'previous_failures': context.get('previous_failures', [])
        }

    def record_results(
        self,
        endpoint_key: str,
        test_config: Dict[str, Any],
        result: Dict[str, Any]
    ):
        """Record test results to all learners"""

        # Record to adaptive learner
        if self.pattern_learner:
            self.pattern_learner.learn_from_test_result(
                endpoint_key,
                test_config,
                result
            )

        # Record to LLM orchestrator
        if self.llm_orchestrator:
            self.llm_orchestrator.record_test_result(endpoint_key, result)

        # RL learning happens separately in test_runner

        logger.debug(f"📝 Recorded results for {endpoint_key} to all learners")

    def get_intelligence_summary(self) -> Dict[str, Any]:
        """Get summary of all intelligence components"""

        summary = {
            'enabled': {
                'rl': self.use_rl,
                'llm': self.use_llm,
                'patterns': self.use_patterns
            }
        }

        if self.rl_optimizer:
            summary['rl_metrics'] = self.rl_optimizer.metrics

        if self.llm_orchestrator:
            summary['llm_intelligence'] = self.llm_orchestrator.get_intelligence_summary()

        if self.pattern_learner:
            summary['pattern_stats'] = self.pattern_learner.get_statistics()
            summary['insights'] = [
                {
                    'type': i.insight_type,
                    'description': i.description,
                    'confidence': i.confidence,
                    'recommendation': i.recommendation
                }
                for i in self.pattern_learner.insights[-5:]  # Last 5 insights
            ]

        return summary


# Global instance
_hybrid_intelligence: Optional[HybridIntelligence] = None


def get_hybrid_intelligence(
    use_rl: bool = True,
    use_llm: bool = True,
    use_patterns: bool = True
) -> HybridIntelligence:
    """Get or create global hybrid intelligence instance"""
    global _hybrid_intelligence
    if _hybrid_intelligence is None:
        _hybrid_intelligence = HybridIntelligence(
            use_rl=use_rl,
            use_llm=use_llm,
            use_patterns=use_patterns
        )
    return _hybrid_intelligence
