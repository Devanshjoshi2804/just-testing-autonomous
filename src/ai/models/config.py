"""
AI Configuration Models
Defines settings for AI/LLM providers
"""
from typing import Literal, Optional
from pydantic import BaseModel, Field


class AIModelConfig(BaseModel):
    """Configuration for a specific AI model"""

    provider: Literal['ollama', 'openai', 'anthropic', 'groq', 'mistral']
    model_name: str
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, gt=0, le=128000)
    timeout: int = Field(default=120, gt=0)  # seconds

    class Config:
        frozen = True


class AIEngineConfig(BaseModel):
    """Configuration for AI Engine"""

    # Model selection by task complexity
    simple_task_model: AIModelConfig = Field(
        default=AIModelConfig(
            provider='ollama',
            model_name='llama3.1:8b',
            temperature=0.3,
            max_tokens=2048
        )
    )

    medium_task_model: AIModelConfig = Field(
        default=AIModelConfig(
            provider='ollama',
            model_name='llama3.1:70b',
            temperature=0.5,
            max_tokens=4096
        )
    )

    complex_task_model: AIModelConfig = Field(
        default=AIModelConfig(
            provider='anthropic',
            model_name='claude-sonnet-4-5-20250929',
            temperature=0.7,
            max_tokens=8000
        )
    )

    # Custom fine-tuned model (optional)
    custom_model: Optional[AIModelConfig] = None

    # Fallback strategy
    enable_fallback: bool = True
    fallback_to_cloud: bool = True

    # Performance
    enable_caching: bool = True
    cache_ttl: int = 3600  # 1 hour
    max_retries: int = 3
    retry_delay: float = 1.0  # seconds

    # Ollama configuration
    ollama_base_url: str = "http://localhost:11434"
    ollama_timeout: int = 120

    class Config:
        frozen = True


# Default configurations for different use cases
DEFAULT_LOCAL_ONLY = AIEngineConfig(
    simple_task_model=AIModelConfig(
        provider='ollama',
        model_name='llama3.1:8b',
        temperature=0.3
    ),
    medium_task_model=AIModelConfig(
        provider='ollama',
        model_name='qwen2.5:32b',
        temperature=0.5
    ),
    complex_task_model=AIModelConfig(
        provider='ollama',
        model_name='qwen2.5:72b',
        temperature=0.7
    ),
    fallback_to_cloud=False
)

DEFAULT_HYBRID = AIEngineConfig(
    simple_task_model=AIModelConfig(
        provider='ollama',
        model_name='llama3.1:8b',
        temperature=0.3
    ),
    medium_task_model=AIModelConfig(
        provider='ollama',
        model_name='llama3.1:70b',
        temperature=0.5
    ),
    complex_task_model=AIModelConfig(
        provider='anthropic',
        model_name='claude-sonnet-4-5-20250929',
        temperature=0.7
    ),
    fallback_to_cloud=True
)

DEFAULT_CLOUD_ONLY = AIEngineConfig(
    simple_task_model=AIModelConfig(
        provider='openai',
        model_name='gpt-3.5-turbo',
        temperature=0.3
    ),
    medium_task_model=AIModelConfig(
        provider='openai',
        model_name='gpt-4-turbo',
        temperature=0.5
    ),
    complex_task_model=AIModelConfig(
        provider='anthropic',
        model_name='claude-sonnet-4-5-20250929',
        temperature=0.7
    ),
    fallback_to_cloud=True
)
