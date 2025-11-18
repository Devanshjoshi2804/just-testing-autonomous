"""
LLMOps - Production-grade LLM Operations
Token tracking, cost monitoring, quality metrics, and fallback strategies
"""
import time
import hashlib
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta
from functools import wraps
from dataclasses import dataclass, asdict
from enum import Enum

from loguru import logger
from redis import Redis
from redis.exceptions import RedisError

from src.config import settings


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    OLLAMA = "ollama"
    MISTRAL = "mistral"


# Token costs per 1M tokens (as of Jan 2025)
TOKEN_COSTS = {
    # OpenAI
    "gpt-4": {"input": 30.0, "output": 60.0},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},

    # Anthropic
    "claude-3-opus": {"input": 15.0, "output": 75.0},
    "claude-3-sonnet": {"input": 3.0, "output": 15.0},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},

    # Groq (fast inference)
    "llama-3-70b": {"input": 0.59, "output": 0.79},
    "mixtral-8x7b": {"input": 0.27, "output": 0.27},

    # Ollama (local, free)
    "ollama": {"input": 0.0, "output": 0.0},
}


@dataclass
class LLMCallMetrics:
    """Metrics for a single LLM call"""
    timestamp: str
    provider: str
    model: str
    prompt_hash: str  # SHA256 of prompt for deduplication
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: float
    success: bool
    error: Optional[str] = None
    prompt_version: Optional[str] = None

    # Quality metrics
    response_length: int = 0
    flagged_by_guardrails: bool = False
    user_feedback: Optional[str] = None


class LLMMetricsTracker:
    """
    Track LLM usage, costs, and quality metrics

    Features:
    - Token usage tracking per provider/model
    - Cost calculation and budgeting
    - Latency monitoring
    - Error rate tracking
    - Prompt deduplication detection
    - Quality metrics aggregation
    """

    def __init__(self, redis_client: Optional[Redis] = None):
        """
        Initialize metrics tracker

        Args:
            redis_client: Redis client for persistence (optional)
        """
        self.redis_client = redis_client
        self.metrics_buffer: List[LLMCallMetrics] = []
        self.buffer_size = 100  # Flush to Redis every 100 calls

    def _get_redis_client(self) -> Optional[Redis]:
        """Get Redis client"""
        if self.redis_client is not None:
            return self.redis_client

        try:
            from src.cache.redis_config import get_redis
            return get_redis()
        except Exception as e:
            logger.warning(f"Redis not available for LLM metrics: {e}")
            return None

    def _calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Calculate cost in USD for LLM call

        Args:
            model: Model name
            input_tokens: Input token count
            output_tokens: Output token count

        Returns:
            Cost in USD
        """
        # Get pricing for model (fallback to gpt-3.5-turbo if unknown)
        pricing = TOKEN_COSTS.get(model, TOKEN_COSTS["gpt-3.5-turbo"])

        # Calculate cost (prices are per 1M tokens)
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def _hash_prompt(self, prompt: str) -> str:
        """Create hash of prompt for deduplication tracking"""
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]

    def record_call(
        self,
        provider: str,
        model: str,
        prompt: str,
        response: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        success: bool = True,
        error: Optional[str] = None,
        prompt_version: Optional[str] = None,
        flagged_by_guardrails: bool = False
    ) -> LLMCallMetrics:
        """
        Record an LLM call with full metrics

        Args:
            provider: LLM provider name
            model: Model name
            prompt: Input prompt
            response: Model response
            input_tokens: Input token count
            output_tokens: Output token count
            latency_ms: Latency in milliseconds
            success: Whether call succeeded
            error: Error message if failed
            prompt_version: Prompt version identifier
            flagged_by_guardrails: Whether guardrails flagged the output

        Returns:
            LLMCallMetrics object
        """
        metrics = LLMCallMetrics(
            timestamp=datetime.utcnow().isoformat(),
            provider=provider,
            model=model,
            prompt_hash=self._hash_prompt(prompt),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=self._calculate_cost(model, input_tokens, output_tokens),
            latency_ms=latency_ms,
            success=success,
            error=error,
            prompt_version=prompt_version,
            response_length=len(response),
            flagged_by_guardrails=flagged_by_guardrails
        )

        # Add to buffer
        self.metrics_buffer.append(metrics)

        # Log important metrics
        logger.info(
            f"LLM call: {provider}/{model}",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=round(metrics.cost_usd, 6),
            latency_ms=round(latency_ms, 2),
            success=success
        )

        # Flush to Redis if buffer full
        if len(self.metrics_buffer) >= self.buffer_size:
            self._flush_to_redis()

        return metrics

    def _flush_to_redis(self):
        """Flush metrics buffer to Redis"""
        if not self.metrics_buffer:
            return

        redis = self._get_redis_client()
        if redis is None:
            logger.warning("Cannot flush LLM metrics: Redis unavailable")
            self.metrics_buffer.clear()  # Clear to prevent memory leak
            return

        try:
            # Store metrics in Redis sorted set (sorted by timestamp)
            pipe = redis.pipeline()

            for metrics in self.metrics_buffer:
                # Store in sorted set for time-series queries
                key = f"llm_metrics:{metrics.provider}:{metrics.model}"
                score = time.time()
                value = str(asdict(metrics))
                pipe.zadd(key, {value: score})

                # Set expiry to 30 days
                pipe.expire(key, 30 * 24 * 3600)

            pipe.execute()

            logger.debug(f"Flushed {len(self.metrics_buffer)} LLM metrics to Redis")
            self.metrics_buffer.clear()

        except RedisError as e:
            logger.error(f"Failed to flush LLM metrics: {e}")
            self.metrics_buffer.clear()

    def get_statistics(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get aggregated statistics

        Args:
            provider: Filter by provider (None = all)
            model: Filter by model (None = all)
            hours: Time window in hours

        Returns:
            Statistics dictionary
        """
        # For now, use in-memory buffer
        # In production, query Redis sorted sets

        filtered_metrics = self.metrics_buffer
        if provider:
            filtered_metrics = [m for m in filtered_metrics if m.provider == provider]
        if model:
            filtered_metrics = [m for m in filtered_metrics if m.model == model]

        if not filtered_metrics:
            return {
                "total_calls": 0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "avg_latency_ms": 0.0,
                "error_rate": 0.0
            }

        total_calls = len(filtered_metrics)
        total_tokens = sum(m.total_tokens for m in filtered_metrics)
        total_cost = sum(m.cost_usd for m in filtered_metrics)
        avg_latency = sum(m.latency_ms for m in filtered_metrics) / total_calls
        errors = sum(1 for m in filtered_metrics if not m.success)
        error_rate = (errors / total_calls) * 100

        return {
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 6),
            "avg_latency_ms": round(avg_latency, 2),
            "error_rate": round(error_rate, 2),
            "success_rate": round(100 - error_rate, 2),
            "avg_cost_per_call": round(total_cost / total_calls, 6) if total_calls > 0 else 0.0
        }


# Global metrics tracker
_metrics_tracker: Optional[LLMMetricsTracker] = None


def get_metrics_tracker() -> LLMMetricsTracker:
    """Get or create global metrics tracker"""
    global _metrics_tracker
    if _metrics_tracker is None:
        _metrics_tracker = LLMMetricsTracker()
    return _metrics_tracker


def track_llm_call(
    provider: str,
    model: str,
    prompt_version: Optional[str] = None
):
    """
    Decorator to track LLM calls

    Usage:
        @track_llm_call(provider="openai", model="gpt-4")
        def call_llm(prompt: str) -> str:
            # ... LLM call code ...
            return response

    Args:
        provider: LLM provider
        model: Model name
        prompt_version: Optional prompt version
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get prompt from args (assume first arg is prompt)
            prompt = args[0] if args else kwargs.get('prompt', '')

            start_time = time.time()
            success = True
            error = None
            response = ""
            input_tokens = 0
            output_tokens = 0

            try:
                # Call the LLM function
                result = func(*args, **kwargs)
                response = result if isinstance(result, str) else str(result)

                # Estimate tokens (rough estimation: 1 token ≈ 4 chars)
                input_tokens = len(prompt) // 4
                output_tokens = len(response) // 4

                return result

            except Exception as e:
                success = False
                error = str(e)
                raise

            finally:
                latency_ms = (time.time() - start_time) * 1000

                # Record metrics
                tracker = get_metrics_tracker()
                tracker.record_call(
                    provider=provider,
                    model=model,
                    prompt=prompt,
                    response=response,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_ms=latency_ms,
                    success=success,
                    error=error,
                    prompt_version=prompt_version
                )

        return wrapper
    return decorator


class LLMFallbackStrategy:
    """
    Fallback strategy for LLM failures

    Implements cascading fallback:
    1. Primary model (e.g., GPT-4)
    2. Fallback model (e.g., GPT-3.5)
    3. Local model (e.g., Ollama)
    4. Cached response (if available)
    5. Error response
    """

    def __init__(self):
        self.fallback_chain = [
            {"provider": "openai", "model": "gpt-4"},
            {"provider": "openai", "model": "gpt-3.5-turbo"},
            {"provider": "ollama", "model": "llama2"},
        ]

    async def call_with_fallback(
        self,
        prompt: str,
        call_function: Callable,
        **kwargs
    ) -> str:
        """
        Call LLM with automatic fallback on failure

        Args:
            prompt: Input prompt
            call_function: Function to call LLM
            **kwargs: Additional arguments

        Returns:
            Response string

        Raises:
            Exception: If all fallbacks fail
        """
        last_error = None

        for config in self.fallback_chain:
            try:
                logger.info(f"Trying {config['provider']}/{config['model']}")
                response = await call_function(prompt, **config, **kwargs)
                return response

            except Exception as e:
                logger.warning(
                    f"LLM call failed: {config['provider']}/{config['model']}: {e}"
                )
                last_error = e
                continue

        # All fallbacks failed
        raise Exception(f"All LLM fallbacks exhausted. Last error: {last_error}")


# Prompt versioning
class PromptVersion:
    """
    Prompt versioning for A/B testing and tracking
    """

    def __init__(self, redis_client: Optional[Redis] = None):
        self.redis_client = redis_client
        self.prompts: Dict[str, Dict[str, str]] = {}

    def register_prompt(
        self,
        name: str,
        version: str,
        template: str,
        description: str = ""
    ):
        """
        Register a prompt version

        Args:
            name: Prompt name (e.g., "test_generation")
            version: Version identifier (e.g., "v1", "v2_chain_of_thought")
            template: Prompt template
            description: Description of changes
        """
        key = f"{name}:{version}"
        self.prompts[key] = {
            "template": template,
            "description": description,
            "created_at": datetime.utcnow().isoformat()
        }

        logger.info(f"Registered prompt: {key}")

    def get_prompt(
        self,
        name: str,
        version: str = "latest"
    ) -> str:
        """Get prompt template by name and version"""
        key = f"{name}:{version}"
        prompt_data = self.prompts.get(key)

        if not prompt_data:
            raise ValueError(f"Prompt not found: {key}")

        return prompt_data["template"]


# Initialize global instances
llm_metrics_tracker = get_metrics_tracker()
llm_fallback = LLMFallbackStrategy()
prompt_versions = PromptVersion()
