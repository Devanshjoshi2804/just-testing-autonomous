"""
Unit Tests for Hybrid AI Engine
Tests AI engine with mocked providers
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from src.ai import (
    HybridAIEngine,
    get_ai_engine,
    reset_ai_engine,
    AIEngineConfig,
    AIModelConfig,
    ModelNotAvailableError,
    InferenceError,
    DEFAULT_LOCAL_ONLY,
    DEFAULT_HYBRID
)


@pytest.fixture
def mock_ollama_client():
    """Mock Ollama client"""
    client = AsyncMock()
    client.chat = AsyncMock(return_value={
        'message': {
            'content': 'Mocked Ollama response'
        }
    })
    return client


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client"""
    client = AsyncMock()
    message = Mock()
    message.content = [Mock(text='Mocked Claude response')]
    client.messages.create = AsyncMock(return_value=message)
    return client


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client"""
    client = AsyncMock()
    response = Mock()
    response.choices = [Mock(message=Mock(content='Mocked GPT response'))]
    client.chat.completions.create = AsyncMock(return_value=response)
    return client


@pytest.fixture
def ai_engine(mock_ollama_client, mock_anthropic_client, mock_openai_client):
    """Create AI engine with mocked clients"""
    with patch('src.ai.hybrid_engine.OLLAMA_AVAILABLE', True), \
         patch('src.ai.hybrid_engine.ANTHROPIC_AVAILABLE', True), \
         patch('src.ai.hybrid_engine.OPENAI_AVAILABLE', True):

        engine = HybridAIEngine(config=DEFAULT_HYBRID)

        # Replace clients with mocks
        engine.ollama_async_client = mock_ollama_client
        engine.anthropic_async_client = mock_anthropic_client
        engine.openai_async_client = mock_openai_client

        return engine


class TestAIEngineConfig:
    """Test AI engine configuration"""

    def test_default_hybrid_config(self):
        """Test default hybrid configuration"""
        config = DEFAULT_HYBRID

        assert config.simple_task_model.provider == 'ollama'
        assert config.medium_task_model.provider == 'ollama'
        assert config.complex_task_model.provider == 'anthropic'
        assert config.fallback_to_cloud is True

    def test_local_only_config(self):
        """Test local-only configuration"""
        config = DEFAULT_LOCAL_ONLY

        assert config.simple_task_model.provider == 'ollama'
        assert config.medium_task_model.provider == 'ollama'
        assert config.complex_task_model.provider == 'ollama'
        assert config.fallback_to_cloud is False

    def test_custom_config(self):
        """Test custom configuration"""
        config = AIEngineConfig(
            simple_task_model=AIModelConfig(
                provider='ollama',
                model_name='custom:latest',
                temperature=0.1,
                max_tokens=1024
            ),
            enable_caching=False,
            max_retries=5
        )

        assert config.simple_task_model.model_name == 'custom:latest'
        assert config.simple_task_model.temperature == 0.1
        assert config.enable_caching is False
        assert config.max_retries == 5


class TestHybridAIEngine:
    """Test hybrid AI engine"""

    def test_engine_initialization(self):
        """Test engine initialization"""
        with patch('src.ai.hybrid_engine.OLLAMA_AVAILABLE', True), \
             patch('src.ai.hybrid_engine.ANTHROPIC_AVAILABLE', True), \
             patch('src.ai.hybrid_engine.OPENAI_AVAILABLE', True):

            engine = HybridAIEngine()

            assert engine.config is not None
            assert isinstance(engine.cache, dict)

    @pytest.mark.asyncio
    async def test_simple_task_uses_small_model(self, ai_engine, mock_ollama_client):
        """Test simple task uses small local model"""
        response = await ai_engine.analyze(
            prompt="Simple question",
            task_complexity='simple'
        )

        assert response == 'Mocked Ollama response'
        mock_ollama_client.chat.assert_called_once()

        # Check correct model was used
        call_args = mock_ollama_client.chat.call_args
        assert call_args.kwargs['model'] == ai_engine.config.simple_task_model.model_name

    @pytest.mark.asyncio
    async def test_complex_task_uses_large_model(
        self,
        ai_engine,
        mock_anthropic_client
    ):
        """Test complex task uses large cloud model"""
        response = await ai_engine.analyze(
            prompt="Complex analysis required",
            task_complexity='complex'
        )

        assert response == 'Mocked Claude response'
        mock_anthropic_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_system_prompt_included(self, ai_engine, mock_ollama_client):
        """Test system prompt is included in request"""
        await ai_engine.analyze(
            prompt="User prompt",
            task_complexity='simple',
            system_prompt="You are a helpful assistant"
        )

        call_args = mock_ollama_client.chat.call_args
        messages = call_args.kwargs['messages']

        # Should have system message
        assert any(msg['role'] == 'system' for msg in messages)
        assert any('helpful assistant' in msg['content'] for msg in messages)

    @pytest.mark.asyncio
    async def test_caching_works(self, ai_engine, mock_ollama_client):
        """Test response caching"""
        prompt = "What is API testing?"

        # First call
        response1 = await ai_engine.analyze(prompt, task_complexity='simple')
        assert mock_ollama_client.chat.call_count == 1

        # Second call - should use cache
        response2 = await ai_engine.analyze(prompt, task_complexity='simple')
        assert response1 == response2
        # Should still be 1 (not called again)
        assert mock_ollama_client.chat.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_expiry(self, ai_engine, mock_ollama_client):
        """Test cache expires after TTL"""
        ai_engine.config = AIEngineConfig(
            cache_ttl=1  # 1 second TTL
        )

        prompt = "Test prompt"

        # First call
        await ai_engine.analyze(prompt, task_complexity='simple')
        assert mock_ollama_client.chat.call_count == 1

        # Wait for cache to expire
        import asyncio
        await asyncio.sleep(1.5)

        # Second call - cache expired, should call again
        await ai_engine.analyze(prompt, task_complexity='simple')
        assert mock_ollama_client.chat.call_count == 2

    @pytest.mark.asyncio
    async def test_fallback_to_cloud_on_local_failure(
        self,
        ai_engine,
        mock_ollama_client,
        mock_anthropic_client
    ):
        """Test fallback to cloud when local model fails"""
        # Make Ollama fail
        mock_ollama_client.chat = AsyncMock(
            side_effect=Exception("Ollama connection failed")
        )

        # Should fallback to Anthropic
        response = await ai_engine.analyze(
            prompt="Test prompt",
            task_complexity='simple'
        )

        assert response == 'Mocked Claude response'
        mock_anthropic_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_fallback_when_disabled(self, ai_engine, mock_ollama_client):
        """Test no fallback when disabled"""
        ai_engine.config = AIEngineConfig(
            enable_fallback=False
        )

        # Make Ollama fail
        mock_ollama_client.chat = AsyncMock(
            side_effect=Exception("Ollama connection failed")
        )

        # Should raise error, not fallback
        with pytest.raises(InferenceError):
            await ai_engine.analyze(
                prompt="Test prompt",
                task_complexity='simple'
            )

    @pytest.mark.asyncio
    async def test_cache_clearing(self, ai_engine, mock_ollama_client):
        """Test cache can be cleared"""
        prompt = "Test prompt"

        # First call
        await ai_engine.analyze(prompt, task_complexity='simple')
        assert len(ai_engine.cache) == 1

        # Clear cache
        ai_engine.clear_cache()
        assert len(ai_engine.cache) == 0

        # Should call model again
        await ai_engine.analyze(prompt, task_complexity='simple')
        assert mock_ollama_client.chat.call_count == 2

    def test_cache_key_generation(self, ai_engine):
        """Test cache key generation is consistent"""
        key1 = ai_engine._get_cache_key("prompt1", "system1")
        key2 = ai_engine._get_cache_key("prompt1", "system1")
        key3 = ai_engine._get_cache_key("prompt2", "system1")

        assert key1 == key2  # Same inputs = same key
        assert key1 != key3  # Different inputs = different key

    @pytest.mark.asyncio
    async def test_model_selection_by_complexity(self, ai_engine):
        """Test correct model selection based on task complexity"""
        # Simple
        model = ai_engine._select_model('simple')
        assert model == ai_engine.config.simple_task_model

        # Medium
        model = ai_engine._select_model('medium')
        assert model == ai_engine.config.medium_task_model

        # Complex
        model = ai_engine._select_model('complex')
        assert model == ai_engine.config.complex_task_model

    @pytest.mark.asyncio
    async def test_custom_model_priority(self, ai_engine, mock_ollama_client):
        """Test custom model is tried first when requested"""
        # Add custom model
        ai_engine.config = AIEngineConfig(
            custom_model=AIModelConfig(
                provider='ollama',
                model_name='custom-ft:latest',
                temperature=0.3,
                max_tokens=2048
            )
        )

        await ai_engine.analyze(
            prompt="Test",
            task_complexity='medium',
            use_custom_model=True
        )

        # Should use custom model
        call_args = mock_ollama_client.chat.call_args
        assert call_args.kwargs['model'] == 'custom-ft:latest'


class TestGlobalEngine:
    """Test global engine instance management"""

    def test_get_ai_engine_returns_instance(self):
        """Test getting global AI engine instance"""
        reset_ai_engine()  # Start fresh

        engine1 = get_ai_engine()
        engine2 = get_ai_engine()

        # Should return same instance
        assert engine1 is engine2

    def test_reset_ai_engine(self):
        """Test resetting global engine"""
        engine1 = get_ai_engine()
        reset_ai_engine()
        engine2 = get_ai_engine()

        # Should be different instances
        assert engine1 is not engine2


class TestErrorHandling:
    """Test error handling"""

    @pytest.mark.asyncio
    async def test_model_not_available_error(self):
        """Test error when model not available"""
        with patch('src.ai.hybrid_engine.OLLAMA_AVAILABLE', False), \
             patch('src.ai.hybrid_engine.ANTHROPIC_AVAILABLE', False), \
             patch('src.ai.hybrid_engine.OPENAI_AVAILABLE', False):

            engine = HybridAIEngine()

            with pytest.raises(ModelNotAvailableError):
                await engine.analyze("test", task_complexity='simple')

    @pytest.mark.asyncio
    async def test_all_providers_fail(self, ai_engine):
        """Test when all providers fail"""
        # Make all providers fail
        ai_engine.ollama_async_client.chat = AsyncMock(
            side_effect=Exception("Ollama failed")
        )
        ai_engine.anthropic_async_client.messages.create = AsyncMock(
            side_effect=Exception("Anthropic failed")
        )
        ai_engine.openai_async_client.chat.completions.create = AsyncMock(
            side_effect=Exception("OpenAI failed")
        )

        with pytest.raises(InferenceError):
            await ai_engine.analyze("test", task_complexity='simple')


class TestHealthCheck:
    """Test health check functionality"""

    @pytest.mark.asyncio
    async def test_health_check_reports_availability(self, ai_engine):
        """Test health check reports provider availability"""
        with patch('ollama.list', return_value={'models': [{'name': 'llama3.1:8b'}]}):
            health = await ai_engine.health_check()

            assert 'ollama' in health
            assert 'anthropic' in health
            assert 'openai' in health

            # All should be available (mocked)
            assert health['ollama']['available'] is True
            assert health['anthropic']['available'] is True
            assert health['openai']['available'] is True
