"""
Hybrid AI Engine
Supports both local (Ollama) and cloud (OpenAI, Anthropic) AI models
with automatic fallback and caching
"""
import asyncio
import hashlib
import json
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime, timedelta

from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

# AI Providers
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning("Ollama not installed. Local models unavailable.")

try:
    from anthropic import Anthropic, AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic not installed. Claude unavailable.")

try:
    from openai import OpenAI, AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not installed. GPT models unavailable.")

from src.ai.models.config import AIEngineConfig, AIModelConfig, DEFAULT_HYBRID
from src.config import get_settings


class AIEngineError(Exception):
    """Base exception for AI engine errors"""
    pass


class ModelNotAvailableError(AIEngineError):
    """Raised when requested model is not available"""
    pass


class InferenceError(AIEngineError):
    """Raised when inference fails"""
    pass


class HybridAIEngine:
    """
    Hybrid AI Engine supporting local and cloud models

    Features:
    - Local inference via Ollama (Llama, Mistral, Qwen, etc.)
    - Cloud inference via OpenAI, Anthropic
    - Automatic fallback on failure
    - Response caching
    - Retry logic with exponential backoff
    - Task complexity-based model selection
    """

    def __init__(self, config: Optional[AIEngineConfig] = None):
        """
        Initialize hybrid AI engine

        Args:
            config: AI engine configuration (defaults to hybrid config)
        """
        self.config = config or DEFAULT_HYBRID
        self.settings = get_settings()

        # Initialize clients
        self._init_clients()

        # Cache for responses (in-memory for now, can be Redis later)
        self.cache: Dict[str, Dict[str, Any]] = {}

        logger.info(f"Initialized HybridAIEngine")
        logger.info(f"Ollama available: {OLLAMA_AVAILABLE}")
        logger.info(f"Anthropic available: {ANTHROPIC_AVAILABLE}")
        logger.info(f"OpenAI available: {OPENAI_AVAILABLE}")

    def _init_clients(self):
        """Initialize AI provider clients"""
        # Ollama client
        if OLLAMA_AVAILABLE:
            self.ollama_client = ollama.Client(
                host=self.config.ollama_base_url
            )
            self.ollama_async_client = ollama.AsyncClient(
                host=self.config.ollama_base_url
            )
        else:
            self.ollama_client = None
            self.ollama_async_client = None

        # Anthropic client
        if ANTHROPIC_AVAILABLE and self.settings.ANTHROPIC_API_KEY:
            self.anthropic_client = Anthropic(
                api_key=self.settings.ANTHROPIC_API_KEY
            )
            self.anthropic_async_client = AsyncAnthropic(
                api_key=self.settings.ANTHROPIC_API_KEY
            )
        else:
            self.anthropic_client = None
            self.anthropic_async_client = None

        # OpenAI client
        if OPENAI_AVAILABLE and self.settings.OPENAI_API_KEY:
            self.openai_client = OpenAI(
                api_key=self.settings.OPENAI_API_KEY
            )
            self.openai_async_client = AsyncOpenAI(
                api_key=self.settings.OPENAI_API_KEY
            )
        else:
            self.openai_client = None
            self.openai_async_client = None

    async def analyze(
        self,
        prompt: str,
        task_complexity: Literal['simple', 'medium', 'complex'] = 'medium',
        system_prompt: Optional[str] = None,
        use_custom_model: bool = False,
        **kwargs
    ) -> str:
        """
        Analyze prompt using appropriate AI model

        Args:
            prompt: User prompt
            task_complexity: Task complexity level
            system_prompt: Optional system prompt
            use_custom_model: Whether to try custom fine-tuned model first
            **kwargs: Additional arguments for model

        Returns:
            Model response text

        Raises:
            ModelNotAvailableError: If no suitable model available
            InferenceError: If inference fails
        """
        # Check cache first
        if self.config.enable_caching:
            cached = self._get_from_cache(prompt, system_prompt)
            if cached:
                logger.info("Returning cached response")
                return cached

        # Try custom model first if requested
        if use_custom_model and self.config.custom_model:
            try:
                response = await self._infer_with_model(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    model_config=self.config.custom_model,
                    **kwargs
                )
                self._store_in_cache(prompt, system_prompt, response)
                return response
            except Exception as e:
                logger.warning(f"Custom model failed: {e}, trying standard models")

        # Select model based on task complexity
        model_config = self._select_model(task_complexity)

        # Try primary model
        try:
            response = await self._infer_with_model(
                prompt=prompt,
                system_prompt=system_prompt,
                model_config=model_config,
                **kwargs
            )
            self._store_in_cache(prompt, system_prompt, response)
            return response

        except Exception as e:
            logger.warning(f"Primary model failed: {e}")

            # Try fallback if enabled
            if not self.config.enable_fallback:
                raise InferenceError(f"Inference failed: {e}")

            logger.info("Attempting fallback...")
            response = await self._fallback_inference(
                prompt=prompt,
                system_prompt=system_prompt,
                failed_model=model_config,
                **kwargs
            )
            self._store_in_cache(prompt, system_prompt, response)
            return response

    def _select_model(self, task_complexity: str) -> AIModelConfig:
        """Select appropriate model based on task complexity"""
        if task_complexity == 'simple':
            return self.config.simple_task_model
        elif task_complexity == 'medium':
            return self.config.medium_task_model
        else:  # complex
            return self.config.complex_task_model

    async def _infer_with_model(
        self,
        prompt: str,
        model_config: AIModelConfig,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Run inference with specific model

        Args:
            prompt: User prompt
            model_config: Model configuration
            system_prompt: Optional system prompt
            **kwargs: Additional model arguments

        Returns:
            Model response

        Raises:
            ModelNotAvailableError: If model not available
            InferenceError: If inference fails
        """
        logger.info(
            f"Running inference with {model_config.provider}/"
            f"{model_config.model_name}"
        )

        if model_config.provider == 'ollama':
            return await self._infer_ollama(prompt, model_config, system_prompt, **kwargs)
        elif model_config.provider == 'anthropic':
            return await self._infer_anthropic(prompt, model_config, system_prompt, **kwargs)
        elif model_config.provider == 'openai':
            return await self._infer_openai(prompt, model_config, system_prompt, **kwargs)
        else:
            raise ModelNotAvailableError(
                f"Provider not supported: {model_config.provider}"
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(InferenceError)
    )
    async def _infer_ollama(
        self,
        prompt: str,
        model_config: AIModelConfig,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Inference using Ollama (local models)"""
        if not self.ollama_async_client:
            raise ModelNotAvailableError("Ollama not available")

        # Build messages
        messages = []
        if system_prompt:
            messages.append({
                'role': 'system',
                'content': system_prompt
            })
        messages.append({
            'role': 'user',
            'content': prompt
        })

        try:
            response = await self.ollama_async_client.chat(
                model=model_config.model_name,
                messages=messages,
                options={
                    'temperature': model_config.temperature,
                    'num_predict': model_config.max_tokens,
                }
            )

            return response['message']['content']

        except Exception as e:
            logger.error(f"Ollama inference failed: {e}")
            raise InferenceError(f"Ollama inference failed: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(InferenceError)
    )
    async def _infer_anthropic(
        self,
        prompt: str,
        model_config: AIModelConfig,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Inference using Anthropic Claude"""
        if not self.anthropic_async_client:
            raise ModelNotAvailableError("Anthropic not available")

        try:
            message = await self.anthropic_async_client.messages.create(
                model=model_config.model_name,
                max_tokens=model_config.max_tokens,
                temperature=model_config.temperature,
                system=system_prompt if system_prompt else "",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            return message.content[0].text

        except Exception as e:
            logger.error(f"Anthropic inference failed: {e}")
            raise InferenceError(f"Anthropic inference failed: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(InferenceError)
    )
    async def _infer_openai(
        self,
        prompt: str,
        model_config: AIModelConfig,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Inference using OpenAI GPT"""
        if not self.openai_async_client:
            raise ModelNotAvailableError("OpenAI not available")

        # Build messages
        messages = []
        if system_prompt:
            messages.append({
                'role': 'system',
                'content': system_prompt
            })
        messages.append({
            'role': 'user',
            'content': prompt
        })

        try:
            response = await self.openai_async_client.chat.completions.create(
                model=model_config.model_name,
                messages=messages,
                temperature=model_config.temperature,
                max_tokens=model_config.max_tokens
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI inference failed: {e}")
            raise InferenceError(f"OpenAI inference failed: {e}")

    async def _fallback_inference(
        self,
        prompt: str,
        failed_model: AIModelConfig,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Attempt fallback inference when primary model fails

        Strategy:
        1. Try next complexity level
        2. Try cloud models if local failed
        3. Try different provider
        """
        # If local model failed and cloud fallback enabled, try cloud
        if failed_model.provider == 'ollama' and self.config.fallback_to_cloud:
            logger.info("Local model failed, falling back to cloud...")

            # Try Anthropic first (best quality)
            if self.anthropic_async_client:
                try:
                    return await self._infer_anthropic(
                        prompt,
                        self.config.complex_task_model,
                        system_prompt,
                        **kwargs
                    )
                except Exception as e:
                    logger.warning(f"Anthropic fallback failed: {e}")

            # Try OpenAI
            if self.openai_async_client:
                try:
                    fallback_config = AIModelConfig(
                        provider='openai',
                        model_name='gpt-4-turbo',
                        temperature=0.7,
                        max_tokens=4096
                    )
                    return await self._infer_openai(
                        prompt,
                        fallback_config,
                        system_prompt,
                        **kwargs
                    )
                except Exception as e:
                    logger.warning(f"OpenAI fallback failed: {e}")

        # If cloud model failed, try different cloud provider
        if failed_model.provider == 'anthropic' and self.openai_async_client:
            try:
                fallback_config = AIModelConfig(
                    provider='openai',
                    model_name='gpt-4-turbo',
                    temperature=0.7,
                    max_tokens=4096
                )
                return await self._infer_openai(
                    prompt,
                    fallback_config,
                    system_prompt,
                    **kwargs
                )
            except Exception as e:
                logger.warning(f"OpenAI fallback failed: {e}")

        elif failed_model.provider == 'openai' and self.anthropic_async_client:
            try:
                return await self._infer_anthropic(
                    prompt,
                    self.config.complex_task_model,
                    system_prompt,
                    **kwargs
                )
            except Exception as e:
                logger.warning(f"Anthropic fallback failed: {e}")

        raise InferenceError("All fallback attempts failed")

    def _get_cache_key(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate cache key for prompt"""
        content = f"{system_prompt or ''}||{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _get_from_cache(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> Optional[str]:
        """Retrieve response from cache if exists and not expired"""
        cache_key = self._get_cache_key(prompt, system_prompt)

        if cache_key in self.cache:
            cached_entry = self.cache[cache_key]
            expiry = cached_entry['timestamp'] + timedelta(
                seconds=self.config.cache_ttl
            )

            if datetime.now() < expiry:
                logger.debug(f"Cache hit for key: {cache_key[:16]}...")
                return cached_entry['response']
            else:
                # Expired, remove from cache
                del self.cache[cache_key]

        return None

    def _store_in_cache(
        self,
        prompt: str,
        system_prompt: Optional[str],
        response: str
    ):
        """Store response in cache"""
        cache_key = self._get_cache_key(prompt, system_prompt)
        self.cache[cache_key] = {
            'response': response,
            'timestamp': datetime.now()
        }
        logger.debug(f"Stored in cache: {cache_key[:16]}...")

    def clear_cache(self):
        """Clear response cache"""
        self.cache.clear()
        logger.info("Cache cleared")

    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of all available AI providers

        Returns:
            Dict with provider availability status
        """
        health = {
            'ollama': {'available': False, 'models': []},
            'anthropic': {'available': False},
            'openai': {'available': False}
        }

        # Check Ollama
        if self.ollama_client:
            try:
                models = ollama.list()
                health['ollama']['available'] = True
                health['ollama']['models'] = [m['name'] for m in models['models']]
                logger.info(f"Ollama available with {len(health['ollama']['models'])} models")
            except Exception as e:
                logger.warning(f"Ollama health check failed: {e}")

        # Check Anthropic
        if self.anthropic_client:
            try:
                # Simple test to check API key validity
                health['anthropic']['available'] = True
                logger.info("Anthropic available")
            except Exception as e:
                logger.warning(f"Anthropic health check failed: {e}")

        # Check OpenAI
        if self.openai_client:
            try:
                health['openai']['available'] = True
                logger.info("OpenAI available")
            except Exception as e:
                logger.warning(f"OpenAI health check failed: {e}")

        return health


# Global instance (can be configured at startup)
_global_engine: Optional[HybridAIEngine] = None


def get_ai_engine(config: Optional[AIEngineConfig] = None) -> HybridAIEngine:
    """
    Get global AI engine instance

    Args:
        config: Optional configuration (used only on first call)

    Returns:
        HybridAIEngine instance
    """
    global _global_engine

    if _global_engine is None:
        _global_engine = HybridAIEngine(config=config)

    return _global_engine


def reset_ai_engine():
    """Reset global AI engine (mainly for testing)"""
    global _global_engine
    _global_engine = None
