"""
SLI/SLO Monitoring
Service Level Indicators and Objectives for production monitoring
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from loguru import logger
from redis import Redis
from redis.exceptions import RedisError


class SLIType(str, Enum):
    """Types of Service Level Indicators"""
    AVAILABILITY = "availability"
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"


class SLOStatus(str, Enum):
    """SLO compliance status"""
    HEALTHY = "healthy"
    WARNING = "warning"
    BREACHED = "breached"


@dataclass
class SLI:
    """Service Level Indicator"""
    name: str
    type: SLIType
    current_value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SLO:
    """Service Level Objective"""
    name: str
    description: str
    sli_type: SLIType
    target: float  # Target value (e.g., 99.9 for 99.9% availability)
    threshold_warning: float  # Warning threshold (e.g., 99.5)
    threshold_critical: float  # Critical threshold (e.g., 99.0)
    window_hours: int = 24  # Time window for measurement
    
    def evaluate(self, current_value: float) -> SLOStatus:
        """Evaluate SLO status based on current value"""
        if current_value >= self.target:
            return SLOStatus.HEALTHY
        elif current_value >= self.threshold_warning:
            return SLOStatus.WARNING
        else:
            return SLOStatus.BREACHED


class SLICollector:
    """
    Collects and tracks Service Level Indicators
    
    Features:
    - Real-time SLI tracking
    - Historical data in Redis
    - SLO compliance monitoring
    - Alert generation
    """
    
    def __init__(self, redis_client: Optional[Redis] = None):
        self.redis_client = redis_client
        
        # Define SLOs
        self.slos = {
            "api_availability": SLO(
                name="API Availability",
                description="Percentage of successful API requests",
                sli_type=SLIType.AVAILABILITY,
                target=99.9,
                threshold_warning=99.5,
                threshold_critical=99.0,
                window_hours=24
            ),
            "api_latency_p95": SLO(
                name="API Latency P95",
                description="95th percentile response time",
                sli_type=SLIType.LATENCY,
                target=500,  # ms
                threshold_warning=1000,
                threshold_critical=2000,
                window_hours=1
            ),
            "error_rate": SLO(
                name="Error Rate",
                description="Percentage of requests that result in errors",
                sli_type=SLIType.ERROR_RATE,
                target=1.0,  # Max 1% errors
                threshold_warning=2.0,
                threshold_critical=5.0,
                window_hours=1
            ),
            "llm_availability": SLO(
                name="LLM Service Availability",
                description="Percentage of successful LLM calls",
                sli_type=SLIType.AVAILABILITY,
                target=95.0,
                threshold_warning=90.0,
                threshold_critical=80.0,
                window_hours=1
            ),
        }
    
    def _get_redis_client(self) -> Optional[Redis]:
        """Get Redis client"""
        if self.redis_client is not None:
            return self.redis_client
        
        try:
            from src.cache.redis_config import get_redis
            return get_redis()
        except Exception as e:
            logger.warning(f"Redis not available for SLI tracking: {e}")
            return None
    
    def record_sli(self, sli_name: str, value: float):
        """Record SLI measurement"""
        redis = self._get_redis_client()
        if redis is None:
            return
        
        try:
            # Store in time-series (sorted set)
            key = f"sli:{sli_name}"
            timestamp = datetime.utcnow().timestamp()
            redis.zadd(key, {str(value): timestamp})
            
            # Keep only last 7 days
            cutoff = timestamp - (7 * 24 * 3600)
            redis.zremrangebyscore(key, 0, cutoff)
            
        except RedisError as e:
            logger.error(f"Failed to record SLI: {e}")
    
    def get_sli_current(self, sli_name: str, window_hours: int = 1) -> Optional[float]:
        """Get current SLI value"""
        redis = self._get_redis_client()
        if redis is None:
            return None
        
        try:
            key = f"sli:{sli_name}"
            now = datetime.utcnow().timestamp()
            start = now - (window_hours * 3600)
            
            # Get all values in window
            values = redis.zrangebyscore(key, start, now)
            
            if not values:
                return None
            
            # Calculate average (or other aggregation)
            numeric_values = [float(v) for v in values]
            return sum(numeric_values) / len(numeric_values)
            
        except RedisError as e:
            logger.error(f"Failed to get SLI: {e}")
            return None
    
    def evaluate_slos(self) -> Dict[str, Dict[str, Any]]:
        """Evaluate all SLOs"""
        results = {}
        
        for slo_name, slo in self.slos.items():
            current_value = self.get_sli_current(slo_name, slo.window_hours)
            
            if current_value is None:
                status = "unknown"
                message = "No data available"
            else:
                slo_status = slo.evaluate(current_value)
                status = slo_status.value
                
                if slo_status == SLOStatus.HEALTHY:
                    message = f"SLO met: {current_value:.2f} >= {slo.target}"
                elif slo_status == SLOStatus.WARNING:
                    message = f"SLO warning: {current_value:.2f} < {slo.target}"
                else:
                    message = f"SLO breached: {current_value:.2f} < {slo.threshold_critical}"
            
            results[slo_name] = {
                "name": slo.name,
                "description": slo.description,
                "status": status,
                "current_value": current_value,
                "target": slo.target,
                "message": message,
                "window_hours": slo.window_hours
            }
        
        return results
    
    def get_error_budget(self, slo_name: str) -> Optional[Dict[str, Any]]:
        """
        Calculate error budget
        
        Error budget = (100% - SLO target) of total requests
        E.g., for 99.9% SLO, error budget is 0.1% of requests
        """
        if slo_name not in self.slos:
            return None
        
        slo = self.slos[slo_name]
        current_value = self.get_sli_current(slo_name, slo.window_hours)
        
        if current_value is None:
            return None
        
        if slo.sli_type == SLIType.AVAILABILITY:
            # Error budget for availability
            allowed_error_rate = 100 - slo.target  # e.g., 0.1%
            actual_error_rate = 100 - current_value
            error_budget_remaining = allowed_error_rate - actual_error_rate
            error_budget_consumed_pct = (actual_error_rate / allowed_error_rate) * 100
            
            return {
                "slo_name": slo_name,
                "allowed_error_rate": f"{allowed_error_rate:.3f}%",
                "actual_error_rate": f"{actual_error_rate:.3f}%",
                "error_budget_remaining": f"{error_budget_remaining:.3f}%",
                "error_budget_consumed": f"{error_budget_consumed_pct:.1f}%",
                "status": "healthy" if error_budget_remaining > 0 else "exceeded"
            }
        
        return None


# Global SLI collector
_sli_collector: Optional[SLICollector] = None


def get_sli_collector() -> SLICollector:
    """Get or create global SLI collector"""
    global _sli_collector
    if _sli_collector is None:
        _sli_collector = SLICollector()
    return _sli_collector


def record_request_sli(success: bool, latency_ms: float):
    """
    Record SLI for API request
    
    Args:
        success: Whether request succeeded
        latency_ms: Request latency in milliseconds
    """
    collector = get_sli_collector()
    
    # Record availability
    collector.record_sli("api_availability", 100.0 if success else 0.0)
    
    # Record latency
    collector.record_sli("api_latency_p95", latency_ms)
    
    # Record error rate
    collector.record_sli("error_rate", 0.0 if success else 100.0)


def record_llm_sli(success: bool, tokens: int, cost_usd: float):
    """Record SLI for LLM call"""
    collector = get_sli_collector()
    
    # Record LLM availability
    collector.record_sli("llm_availability", 100.0 if success else 0.0)
    
    # Record token usage
    collector.record_sli("llm_tokens", tokens)
    
    # Record cost
    collector.record_sli("llm_cost", cost_usd)


# SLI/SLO helper for health checks
def get_slo_health_status() -> Dict[str, Any]:
    """Get SLO health status for health check endpoint"""
    collector = get_sli_collector()
    slo_results = collector.evaluate_slos()
    
    # Determine overall status
    statuses = [result["status"] for result in slo_results.values()]
    
    if "breached" in statuses:
        overall_status = "unhealthy"
    elif "warning" in statuses:
        overall_status = "degraded"
    elif "unknown" in statuses:
        overall_status = "unknown"
    else:
        overall_status = "healthy"
    
    return {
        "overall_status": overall_status,
        "slos": slo_results,
        "timestamp": datetime.utcnow().isoformat()
    }
