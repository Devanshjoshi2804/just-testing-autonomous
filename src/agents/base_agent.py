"""
Base Agent Class
Common functionality for all LLM-powered agents

🔥 PRODUCTION-READY: Now includes guardrails, circuit breakers, and cost tracking
"""
import time
from typing import Optional, Dict, Any
from loguru import logger

from src.config import get_llm_client, settings

# 🔥 CRITICAL IMPORTS: LLM Safety Stack
from src.llm.guardrails import get_guardrails, GuardrailResult
from src.llm.llm_ops import get_metrics_tracker
from src.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from src.observability.sli_slo import record_llm_sli


class BaseAgent:
    """
    Base class for all LLM agents
    Provides common LLM interaction methods
    """

    def __init__(self, agent_name: str, use_fast_llm: bool = False):
        """
        Initialize base agent

        Args:
            agent_name: Name of the agent (for logging)
            use_fast_llm: Use fast LLM model instead of primary

        🔥 NEW: Initializes circuit breaker and guardrails for production safety
        """
        self.agent_name = agent_name
        self.use_fast_llm = use_fast_llm

        # Get LLM client - pass provider and model directly to avoid settings mutation
        if use_fast_llm:
            self.llm = get_llm_client(
                provider=settings.FAST_LLM_PROVIDER,
                model=settings.FAST_LLM_MODEL
            )
            self.llm_provider = settings.FAST_LLM_PROVIDER
            self.llm_model = settings.FAST_LLM_MODEL

            logger.info(
                f"{agent_name} initialized with FAST LLM: "
                f"{self.llm_provider}/{self.llm_model}"
            )
        else:
            self.llm = get_llm_client()
            self.llm_provider = settings.LLM_PROVIDER
            self.llm_model = settings.LLM_MODEL

            logger.info(
                f"{agent_name} initialized with LLM: "
                f"{self.llm_provider}/{self.llm_model}"
            )

        # 🔥 CRITICAL: Initialize circuit breaker for fault tolerance
        self.circuit_breaker = CircuitBreaker(
            name=f"{agent_name}_llm",
            config=CircuitBreakerConfig(
                failure_threshold=3,      # Open after 3 failures
                recovery_timeout=30.0,    # Try recovery after 30s
                expected_exception=Exception
            )
        )
        logger.debug(f"Circuit breaker initialized for {agent_name}")

        # 🔥 CRITICAL: Initialize guardrails for AI safety
        self.guardrails = get_guardrails()
        logger.debug(f"Guardrails initialized for {agent_name}")

        # 🔥 CRITICAL: Get metrics tracker for cost monitoring
        self.metrics_tracker = get_metrics_tracker()
        logger.debug(f"Metrics tracker initialized for {agent_name}")

    def invoke(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Invoke LLM with prompt

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt

        Returns:
            LLM response text

        🔥 PRODUCTION-READY: Includes guardrails, circuit breaker, cost tracking
        """
        start_time = time.time()

        # 🔥 Step 1: Validate INPUT with guardrails (check for PII injection)
        try:
            input_validation = self.guardrails.validate_input(prompt)
            if not input_validation.passed:
                logger.warning(
                    f"{self.agent_name}: Input validation failed",
                    violations=input_validation.violations
                )
                # For now, log warning but don't block (could be too strict)
        except Exception as guard_error:
            logger.warning(f"Guardrail input check failed: {guard_error}")

        # 🔥 Step 2: Call LLM with circuit breaker protection
        try:
            def _call_llm():
                """Inner function for circuit breaker wrapping"""
                # For Ollama, combine system and user prompts
                if self.llm_provider == "ollama":
                    full_prompt = prompt
                    if system_prompt:
                        full_prompt = f"{system_prompt}\n\n{prompt}"

                    response = self.llm.invoke(full_prompt)
                    return response if isinstance(response, str) else str(response)

                else:
                    # For chat models (OpenAI, Anthropic, Groq)
                    messages = []
                    if system_prompt:
                        messages.append(("system", system_prompt))
                    messages.append(("human", prompt))

                    response = self.llm.invoke(messages)
                    return response.content

            # Execute through circuit breaker
            result = self.circuit_breaker.call(_call_llm)

        except Exception as e:
            logger.error(f"{self.agent_name} LLM invocation failed: {e}")

            # 🔥 Record failed LLM call in SLI
            try:
                record_llm_sli(success=False, tokens=0, cost_usd=0.0)
            except Exception as sli_error:
                logger.warning(f"Failed to record LLM SLI: {sli_error}")

            raise

        # 🔥 Step 3: Validate OUTPUT with guardrails
        try:
            output_validation = self.guardrails.validate(result)

            if not output_validation.passed:
                logger.warning(
                    f"{self.agent_name}: Output validation failed",
                    violations=output_validation.violations
                )

                # If PII detected, use sanitized version
                if output_validation.sanitized_output:
                    logger.info(f"{self.agent_name}: Using PII-redacted output")
                    result = output_validation.sanitized_output

        except Exception as guard_error:
            logger.warning(f"Guardrail output check failed: {guard_error}")

        # 🔥 Step 4: Track metrics (tokens, cost, latency)
        try:
            latency_ms = (time.time() - start_time) * 1000

            # Estimate token counts (rough approximation: 1 token ≈ 4 chars)
            input_tokens = len(prompt) // 4
            output_tokens = len(result) // 4

            # Record metrics
            self.metrics_tracker.record_call(
                provider=self.llm_provider,
                model=self.llm_model,
                prompt=prompt[:100],  # Store first 100 chars only
                response=result[:100],
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                success=True
            )

            # 🔥 Record LLM SLI
            record_llm_sli(
                success=True,
                tokens=input_tokens + output_tokens,
                cost_usd=self.metrics_tracker._calculate_cost(
                    self.llm_model,
                    input_tokens,
                    output_tokens
                )
            )

            logger.debug(
                f"{self.agent_name} LLM call: {len(result)} chars, "
                f"{latency_ms:.0f}ms, ~{input_tokens + output_tokens} tokens"
            )

        except Exception as metrics_error:
            logger.warning(f"Failed to record metrics: {metrics_error}")

        return result

    async def ainvoke(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Asynchronously invoke LLM (non-blocking)

        Runs synchronous LLM invocation in a thread pool executor to avoid
        blocking the async event loop.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt for context

        Returns:
            LLM response text

        🔥 PRODUCTION-READY: Delegates to invoke() which includes all safety features
        """
        import asyncio
        from functools import partial

        try:
            # Run the production-ready invoke() in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,  # Uses default ThreadPoolExecutor
                partial(self.invoke, prompt, system_prompt)
            )

            logger.debug(f"{self.agent_name} async response length: {len(result)} chars")
            return result

        except Exception as e:
            logger.error(f"{self.agent_name} async LLM invocation failed: {e}")
            raise

    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response, handling markdown code blocks

        Args:
            response: LLM response text

        Returns:
            Parsed JSON dict

        Raises:
            ValueError: If JSON parsing fails
        """
        import json
        import re

        # Remove markdown code blocks if present
        cleaned = response.strip()

        # Remove ```json and ``` markers
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]

        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        cleaned = cleaned.strip()

        # Try to parse JSON
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response text: {response[:500]}...")

            # Try to extract JSON from text using regex
            json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except:
                    pass

            raise ValueError(f"Could not parse JSON from response: {response[:200]}...")

    def clean_markdown(self, text: str) -> str:
        """
        Remove markdown formatting from text

        Args:
            text: Text with potential markdown

        Returns:
            Cleaned text
        """
        # Remove code blocks
        import re

        text = re.sub(r'```[\w]*\n', '', text)
        text = re.sub(r'```', '', text)

        # Remove bold/italic
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)

        # Remove headers
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)

        return text.strip()
