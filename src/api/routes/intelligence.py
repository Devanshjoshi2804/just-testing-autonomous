"""
Intelligence API Routes
Expose AI intelligence insights, learned patterns, and recommendations
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from loguru import logger

from src.intelligence import (
    get_hybrid_intelligence,
    get_semantic_analyzer,
    get_adaptive_learner,
    get_orchestrator
)

router = APIRouter()


@router.get(
    "/summary",
    summary="Intelligence Summary",
    description="Get summary of all AI intelligence components and their current state"
)
async def get_intelligence_summary():
    """
    Get comprehensive intelligence summary

    Returns information about:
    - Active intelligence modules (RL, LLM, Patterns)
    - Learning statistics
    - Recent insights
    - System capabilities
    """
    try:
        hybrid = get_hybrid_intelligence()
        summary = hybrid.get_intelligence_summary()

        return {
            "status": "active",
            "intelligence": summary,
            "capabilities": [
                "AI-driven test prioritization",
                "Semantic API understanding",
                "Pattern learning & adaptation",
                "Hybrid RL + LLM decision making",
                "Change detection & alerts",
                "Flakiness detection",
                "Performance baseline tracking"
            ]
        }

    except Exception as e:
        logger.error(f"Failed to get intelligence summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/patterns",
    summary="Learned Patterns",
    description="Get patterns learned from test execution"
)
async def get_learned_patterns(
    endpoint: Optional[str] = Query(None, description="Filter by endpoint (e.g., 'POST /users')"),
    pattern_type: Optional[str] = Query(None, description="Filter by type (failure_pattern, success_pattern, etc)"),
    min_confidence: float = Query(0.5, description="Minimum confidence threshold (0-1)")
):
    """
    Get learned patterns

    Filters:
    - endpoint: Specific endpoint to get patterns for
    - pattern_type: Type of pattern (failure, success, performance, flakiness)
    - min_confidence: Minimum confidence level
    """
    try:
        learner = get_adaptive_learner()

        # Filter patterns
        patterns = []
        for pattern_id, pattern in learner.patterns.items():
            # Apply filters
            if endpoint and pattern.endpoint_key != endpoint:
                continue

            if pattern_type and pattern.pattern_type != pattern_type:
                continue

            if pattern.confidence < min_confidence:
                continue

            patterns.append({
                'id': pattern_id,
                'endpoint': pattern.endpoint_key,
                'type': pattern.pattern_type,
                'conditions': pattern.conditions,
                'actions': pattern.actions,
                'confidence': pattern.confidence,
                'occurrences': pattern.occurrences,
                'last_seen': pattern.last_seen,
                'success_rate': pattern.success_rate
            })

        # Sort by confidence
        patterns.sort(key=lambda x: x['confidence'], reverse=True)

        return {
            "total_patterns": len(patterns),
            "patterns": patterns,
            "statistics": learner.get_statistics()
        }

    except Exception as e:
        logger.error(f"Failed to get patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/insights",
    summary="Generated Insights",
    description="Get high-level insights generated from learned patterns"
)
async def get_insights():
    """
    Get AI-generated insights

    Returns actionable insights like:
    - Endpoints with high failure rates
    - Flaky endpoints needing retry logic
    - Slow endpoints for monitoring
    """
    try:
        learner = get_adaptive_learner()

        # Generate fresh insights
        insights = learner.generate_insights()

        return {
            "total_insights": len(insights),
            "insights": [
                {
                    'type': i.insight_type,
                    'description': i.description,
                    'evidence': i.evidence,
                    'confidence': i.confidence,
                    'actionable': i.actionable,
                    'recommendation': i.recommendation
                }
                for i in insights
            ]
        }

    except Exception as e:
        logger.error(f"Failed to generate insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/recommendations/{endpoint_key:path}",
    summary="Get Recommendations",
    description="Get AI recommendations for testing a specific endpoint"
)
async def get_endpoint_recommendations(endpoint_key: str):
    """
    Get recommendations for testing an endpoint

    Based on learned patterns, provides:
    - Suggested test strategies
    - Known failure patterns to avoid
    - Successful approaches to replicate
    - Performance baselines to monitor
    """
    try:
        learner = get_adaptive_learner()

        recommendations = learner.get_recommendations(endpoint_key)

        if not recommendations:
            return {
                "endpoint": endpoint_key,
                "recommendations": [],
                "message": "No patterns learned yet for this endpoint"
            }

        return {
            "endpoint": endpoint_key,
            "total_recommendations": len(recommendations),
            "recommendations": recommendations
        }

    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api-structure",
    summary="API Structure Analysis",
    description="Get semantic analysis of API structure"
)
async def get_api_structure():
    """
    Get semantic understanding of API

    Returns:
    - Identified entities (users, orders, etc)
    - Data flow relationships
    - Critical paths
    - Knowledge graph
    """
    try:
        analyzer = get_semantic_analyzer()

        if not analyzer.entities:
            return {
                "status": "not_analyzed",
                "message": "No API structure analyzed yet. Upload a document first."
            }

        return {
            "status": "analyzed",
            "entities": {
                name: {
                    'name': entity.name,
                    'type': entity.entity_type.value,
                    'endpoints': entity.endpoints
                }
                for name, entity in analyzer.entities.items()
            },
            "endpoint_semantics": {
                key: {
                    'intent': sem.intent,
                    'business_value': sem.business_value,
                    'user_journey_stage': sem.user_journey_stage,
                    'entities_used': sem.entities_used,
                    'dependencies': sem.data_flow_in
                }
                for key, sem in analyzer.endpoint_semantics.items()
            },
            "data_flows": [
                {
                    'from': flow.from_endpoint,
                    'to': flow.to_endpoint,
                    'data': flow.data_name,
                    'required': flow.required
                }
                for flow in analyzer.data_flows
            ]
        }

    except Exception as e:
        logger.error(f"Failed to get API structure: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/change-signals",
    summary="API Change Signals",
    description="Get detected API change signals"
)
async def get_change_signals():
    """
    Get API change detection signals

    Returns:
    - Performance degradation signals
    - Behavior change signals
    - Schema evolution signals
    """
    try:
        orchestrator = get_orchestrator()

        signals = [
            {
                'endpoint': signal.endpoint_key,
                'type': signal.signal_type,
                'confidence': signal.confidence,
                'evidence': signal.evidence,
                'detected_at': signal.detected_at.isoformat()
            }
            for signal in orchestrator.change_signals[-20:]  # Last 20 signals
        ]

        return {
            "total_signals": len(signals),
            "signals": signals,
            "types": {
                "performance_degradation": "Endpoint is slower than baseline",
                "behavior_change": "Endpoint behavior changed (status code, etc)",
                "schema_change": "Response schema evolved"
            }
        }

    except Exception as e:
        logger.error(f"Failed to get change signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/performance-baselines",
    summary="Performance Baselines",
    description="Get tracked performance baselines for endpoints"
)
async def get_performance_baselines():
    """
    Get performance baselines

    Returns baseline latency for each endpoint
    """
    try:
        orchestrator = get_orchestrator()

        baselines = {
            endpoint: {
                'baseline_ms': latency * 1000,
                'alert_threshold_ms': latency * 1000 * 1.5
            }
            for endpoint, latency in orchestrator.performance_baseline.items()
        }

        return {
            "total_endpoints": len(baselines),
            "baselines": baselines
        }

    except Exception as e:
        logger.error(f"Failed to get performance baselines: {e}")
        raise HTTPException(status_code=500, detail=str(e))
