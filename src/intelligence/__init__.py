"""
Intelligence Module
Advanced AI capabilities for intelligent test orchestration and analysis
Similar to Claude Code's sophisticated understanding and decision-making
"""

from src.intelligence.test_orchestrator import (
    IntelligentTestOrchestrator,
    TestPriority,
    TestStrategy,
    TestDecision,
    ApiChangeSignal,
    get_orchestrator
)

from src.intelligence.semantic_analyzer import (
    SemanticAnalyzer,
    EntityType,
    RelationType,
    SemanticEntity,
    EndpointSemantics,
    DataFlow,
    get_semantic_analyzer
)

from src.intelligence.adaptive_learner import (
    AdaptiveLearner,
    Pattern,
    Insight,
    get_adaptive_learner
)

__all__ = [
    # Test Orchestrator
    'IntelligentTestOrchestrator',
    'TestPriority',
    'TestStrategy',
    'TestDecision',
    'ApiChangeSignal',
    'get_orchestrator',

    # Semantic Analyzer
    'SemanticAnalyzer',
    'EntityType',
    'RelationType',
    'SemanticEntity',
    'EndpointSemantics',
    'DataFlow',
    'get_semantic_analyzer',

    # Adaptive Learner
    'AdaptiveLearner',
    'Pattern',
    'Insight',
    'get_adaptive_learner',
]
