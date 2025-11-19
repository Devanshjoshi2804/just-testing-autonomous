"""
LLM Operations Module
Advanced LLM management, monitoring, and safety
"""
from src.llm.llm_ops import (
    LLMMetricsTracker,
    LLMFallbackStrategy,
    PromptVersion,
    get_metrics_tracker,
    track_llm_call,
    llm_metrics_tracker,
    llm_fallback,
    prompt_versions
)
from src.llm.guardrails import (
    LLMGuardrails,
    GuardrailViolation,
    GuardrailResult,
    with_guardrails,
    get_guardrails,
    TestGenerationGuardrails
)
from src.llm.chain_of_thought import (
    ChainOfThoughtPrompt,
    TestGenerationCoT,
    create_cot_prompt_for_agent,
    get_cot_template,
    TEST_GENERATION_EXAMPLES
)

__all__ = [
    # Metrics & Monitoring
    "LLMMetricsTracker",
    "get_metrics_tracker",
    "track_llm_call",
    "llm_metrics_tracker",

    # Fallback & Resilience
    "LLMFallbackStrategy",
    "llm_fallback",

    # Prompt Management
    "PromptVersion",
    "prompt_versions",

    # Guardrails & Safety
    "LLMGuardrails",
    "GuardrailViolation",
    "GuardrailResult",
    "with_guardrails",
    "get_guardrails",
    "TestGenerationGuardrails",

    # Chain-of-Thought Prompting
    "ChainOfThoughtPrompt",
    "TestGenerationCoT",
    "create_cot_prompt_for_agent",
    "get_cot_template",
    "TEST_GENERATION_EXAMPLES",
]
