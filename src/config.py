"""
Configuration Management for AutoTest-RL
Loads settings from environment variables with validation
"""
import os
from pathlib import Path
from typing import List, Literal
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application Settings with Environment Variable Support"""

    # ========================================================================
    # Environment
    # ========================================================================
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True

    # ========================================================================
    # LLM API Keys
    # ========================================================================
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API Key")
    ANTHROPIC_API_KEY: str = Field(default="", description="Anthropic Claude API Key")
    GROQ_API_KEY: str = Field(default="", description="Groq API Key")
    MISTRAL_API_KEY: str = Field(default="", description="Mistral API Key")
    LLAMAPARSE_API_KEY: str = Field(default="", description="LlamaParse API Key")

    # ========================================================================
    # Ollama Configuration (Local LLM)
    # ========================================================================
    OLLAMA_HOST: str = "ollama"
    OLLAMA_PORT: int = 11434
    OLLAMA_BASE_URL: str = "http://ollama:11434"

    # ========================================================================
    # Database Configuration
    # ========================================================================
    CHROMA_HOST: str = "chromadb"
    CHROMA_PORT: int = 8001
    CHROMA_PERSIST_DIRECTORY: str = "./data/chroma_storage"

    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # ========================================================================
    # Celery Configuration
    # ========================================================================
    CELERY_BROKER_URL: str = Field(
        default="redis://redis:6379/0",
        description="Celery broker URL (Redis)"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://redis:6379/0",
        description="Celery result backend (Redis)"
    )
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: List[str] = ["json"]
    CELERY_TIMEZONE: str = "UTC"
    CELERY_ENABLE_UTC: bool = True
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_TIME_LIMIT: int = 600  # 10 minutes
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = 1

    # ========================================================================
    # API Configuration
    # ========================================================================
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4
    API_RELOAD: bool = True

    # ========================================================================
    # File Upload Settings
    # ========================================================================
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "json", "yaml", "yml"]
    UPLOAD_DIR: Path = Path("./uploads")

    # ========================================================================
    # RAG Configuration
    # ========================================================================
    CHUNK_SIZE: int = 2000
    CHUNK_OVERLAP: int = 400
    RAG_TOP_K: int = 5
    RAG_SIMILARITY_THRESHOLD: float = 0.7
    EMBEDDING_MODEL: str = "mistral-embed"

    # ========================================================================
    # LLM Model Selection
    # ========================================================================
    LLM_PROVIDER: Literal["ollama", "openai", "anthropic", "groq"] = "ollama"
    LLM_MODEL: str = "phi3.5:3.8b"  # Local: phi3.5:3.8b, llama3.2:3b, gemma2:2b
    FAST_LLM_PROVIDER: Literal["ollama", "openai", "anthropic", "groq"] = "ollama"
    FAST_LLM_MODEL: str = "llama3.2:3b"  # Fastest local model
    LLM_TEMPERATURE: float = 0.0
    LLM_MAX_TOKENS: int = 4096

    # ========================================================================
    # Test Execution Settings
    # ========================================================================
    MAX_RETRIES: int = 3
    RETRY_DELAY_SECONDS: int = 1
    HTTP_TIMEOUT_SECONDS: int = 30
    HTTP_MAX_CONNECTIONS: int = 100
    MAX_PARALLEL_TESTS: int = 5

    # ========================================================================
    # Reinforcement Learning Configuration
    # ========================================================================
    RL_ALGORITHM: Literal["PPO", "DQN", "A2C"] = "PPO"
    RL_LEARNING_RATE: float = 0.0003
    RL_GAMMA: float = 0.99
    RL_BATCH_SIZE: int = 64
    RL_N_STEPS: int = 2048
    RL_TOTAL_TIMESTEPS: int = 100000

    # Reward Weights
    REWARD_COVERAGE_WEIGHT: float = 10.0
    REWARD_BUG_DISCOVERY_WEIGHT: float = 50.0
    REWARD_SUCCESS_WEIGHT: float = 20.0
    REWARD_FAILURE_PENALTY: float = -5.0
    REWARD_RETRY_PENALTY: float = -1.0

    # Curiosity Configuration
    USE_CURIOSITY: bool = True
    CURIOSITY_WEIGHT: float = 5.0

    # ========================================================================
    # Logging Configuration
    # ========================================================================
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: Literal["json", "text"] = "json"
    LOG_DIR: Path = Path("./logs")
    LOG_FILE: str = "autotest-rl.log"
    LOG_MAX_BYTES: int = 10485760  # 10MB
    LOG_BACKUP_COUNT: int = 5

    # ========================================================================
    # Monitoring & Observability
    # ========================================================================
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    SENTRY_DSN: str = ""
    SENTRY_ENVIRONMENT: str = "development"

    # ========================================================================
    # Security
    # ========================================================================
    # API Authentication
    API_KEY_ENABLED: bool = False
    API_KEY: str = ""  # Deprecated: Use MASTER_API_KEY
    MASTER_API_KEY: str = Field(
        default="",
        description="Master API key for administrative access"
    )
    REQUIRE_AUTH: bool = Field(
        default=False,
        description="Require API key authentication for all endpoints (disabled in development)"
    )

    # CORS Configuration
    CORS_ALLOWED_ORIGINS: str = "*"
    CORS_ALLOW_CREDENTIALS: bool = True

    # Rate Limiting
    ENABLE_RATE_LIMITING: bool = Field(
        default=True,
        description="Enable rate limiting middleware"
    )
    DEFAULT_RATE_LIMIT: int = Field(
        default=100,
        description="Default rate limit (requests per minute)"
    )
    RATE_LIMIT_WINDOW: int = Field(
        default=60,
        description="Rate limit window in seconds"
    )

    # ========================================================================
    # Development Settings
    # ========================================================================
    AUTO_RELOAD: bool = True
    RANDOM_SEED: int = 42

    # ========================================================================
    # Validators
    # ========================================================================
    @validator("ALLOWED_EXTENSIONS", pre=True)
    def parse_extensions(cls, v):
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",")]
        return v

    @validator("CORS_ALLOWED_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if v == "*":
            return v
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# ============================================================================
# Singleton Settings Instance
# ============================================================================
settings = Settings()


def get_settings() -> Settings:
    """
    Get the global settings instance

    Returns:
        Settings instance
    """
    return settings


# ============================================================================
# Helper Functions
# ============================================================================
def get_llm_client(provider: str = None, model: str = None):
    """
    Get LLM client based on provider configuration

    Args:
        provider: Optional provider override (default: settings.LLM_PROVIDER)
        model: Optional model override (default: settings.LLM_MODEL)

    Returns:
        LLM client instance
    """
    provider = provider or settings.LLM_PROVIDER
    model = model or settings.LLM_MODEL

    if provider == "ollama":
        from langchain_community.llms import Ollama
        return Ollama(
            base_url=settings.OLLAMA_BASE_URL,
            model=model,
            temperature=settings.LLM_TEMPERATURE,
            num_ctx=settings.LLM_MAX_TOKENS,
        )
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )
    elif provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=model,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def get_embedding_client():
    """Get embedding client for vector database"""
    from mistralai import Mistral
    return Mistral(api_key=settings.MISTRAL_API_KEY)


def ensure_directories():
    """Ensure all required directories exist"""
    directories = [
        settings.UPLOAD_DIR,
        settings.LOG_DIR,
        Path("./data/doc_chroma_db"),
        Path("./data/flow_chroma_db"),
        Path("./data/rl_models"),
        Path("./results"),
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


# Ensure directories on import
ensure_directories()
