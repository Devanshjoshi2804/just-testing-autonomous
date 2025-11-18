"""
AI Package
Hybrid AI engine supporting local and cloud models
"""
from src.ai.hybrid_engine import (
    HybridAIEngine,
    get_ai_engine,
    reset_ai_engine,
    AIEngineError,
    ModelNotAvailableError,
    InferenceError
)

from src.ai.models import (
    AIModelConfig,
    AIEngineConfig,
    DEFAULT_LOCAL_ONLY,
    DEFAULT_HYBRID,
    DEFAULT_CLOUD_ONLY
)

__all__ = [
    # Engine
    'HybridAIEngine',
    'get_ai_engine',
    'reset_ai_engine',

    # Exceptions
    'AIEngineError',
    'ModelNotAvailableError',
    'InferenceError',

    # Config
    'AIModelConfig',
    'AIEngineConfig',
    'DEFAULT_LOCAL_ONLY',
    'DEFAULT_HYBRID',
    'DEFAULT_CLOUD_ONLY'
]
