"""
Main FastAPI Application
Intelligent API Testing System with Reinforcement Learning
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
from loguru import logger

from src.config import settings
from src.api.health import comprehensive_health_check, readiness_check, liveness_check
from src.api.middleware.request_id import request_id_middleware
from src.api.middleware.logging_middleware import logging_middleware
from src.api.middleware.security import security_headers_middleware
from src.api.middleware.rate_limiter import rate_limit_middleware
from src.api.middleware.error_handler import register_error_handlers
from src.api.middleware.compression import add_compression_middleware
from src.api.middleware.cache import cached
from src.observability.audit import audit_middleware
from src.observability.tracing import init_tracing
from src.exceptions import AutoTestException, create_error_response

# ============================================================================
# Application Lifespan Management
# ============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events with proper resource initialization"""
    # ============================================================================
    # STARTUP
    # ============================================================================
    logger.info("🚀 Starting AutoTest-RL API...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER}")
    logger.info(f"LLM Model: {settings.LLM_MODEL}")

    # Initialize Redis for caching
    try:
        from src.cache.redis_config import init_redis

        init_redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=getattr(settings, 'REDIS_PASSWORD', None),
            max_connections=50
        )
        logger.info("✅ Redis initialized successfully")

        # Test connection
        from src.cache.redis_config import get_redis
        redis_client = get_redis()
        redis_client.ping()
        logger.info(f"✅ Redis connection verified: {settings.REDIS_HOST}:{settings.REDIS_PORT}")

    except Exception as e:
        logger.error(f"❌ Redis initialization failed: {e}")
        logger.warning("⚠️  Cache features will be disabled")
        logger.warning("⚠️  Application will continue without caching")

    # Initialize Database
    try:
        from src.database.config import init_db

        await init_db()
        logger.info("✅ Database initialized successfully")
        logger.info(f"✅ Database connection verified: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'configured'}")

    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        logger.warning("⚠️  Database features will be disabled")
        logger.warning("⚠️  Application will continue with in-memory storage")

    # Log security status
    if settings.REQUIRE_AUTH:
        logger.info("🔒 Authentication: ENABLED")
    else:
        logger.warning("⚠️  Authentication: DISABLED (not recommended for production)")

    # Log rate limiting status
    if settings.ENABLE_RATE_LIMITING:
        logger.info(f"🛡️  Rate Limiting: ENABLED ({settings.DEFAULT_RATE_LIMIT} req/min default)")
        logger.info(f"   - Upload: {settings.RATE_LIMIT_UPLOAD} req/min")
        logger.info(f"   - Test Start: {settings.RATE_LIMIT_TEST_START} req/min")
    else:
        logger.warning("⚠️  Rate Limiting: DISABLED (not recommended for production)")

    if settings.ENVIRONMENT.lower() in ('production', 'prod') and not settings.REQUIRE_AUTH:
        logger.error("🚨 SECURITY WARNING: Authentication disabled in production!")

    # Initialize observability features
    try:
        # Initialize distributed tracing
        tracer = init_tracing(
            service_name="autotest-rl",
            environment=settings.ENVIRONMENT,
            enable_console=(settings.ENVIRONMENT == "development")
        )
        logger.info("✅ Distributed tracing initialized")

        # Initialize audit logging
        from src.observability.audit import get_audit_logger
        audit_logger = get_audit_logger()
        logger.info(f"✅ Audit logging initialized (retention: {audit_logger.retention_days} days)")

    except Exception as e:
        logger.warning(f"⚠️  Observability initialization warning: {e}")

    logger.info("✅ AutoTest-RL API startup complete")

    # ============================================================================
    # APPLICATION RUNNING
    # ============================================================================
    yield

    # ============================================================================
    # SHUTDOWN
    # ============================================================================
    logger.info("👋 Shutting down AutoTest-RL API...")

    # Cleanup Redis connections
    try:
        from src.cache.redis_config import get_redis_config
        redis_config = get_redis_config()
        redis_config.close()
        await redis_config.close_async()
        logger.info("✅ Redis connections closed")
    except Exception as e:
        logger.warning(f"Redis cleanup warning: {e}")

    # Cleanup Database connections
    try:
        from src.database.config import close_db
        await close_db()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.warning(f"Database cleanup warning: {e}")

    logger.info("✅ Shutdown complete")


# ============================================================================
# FastAPI Application
# ============================================================================
app = FastAPI(
    title="AutoTest-RL API",
    description="Intelligent API Testing System with Reinforcement Learning",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Register enhanced error handlers
register_error_handlers(app)
logger.info("✅ Enhanced error handlers registered")

# Add response compression
add_compression_middleware(app, minimum_size=1024, compression_level=6)

# ============================================================================
# CORS Middleware
# ============================================================================
if isinstance(settings.CORS_ALLOWED_ORIGINS, str):
    origins = [settings.CORS_ALLOWED_ORIGINS] if settings.CORS_ALLOWED_ORIGINS != "*" else ["*"]
else:
    origins = settings.CORS_ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Custom Middleware Stack
# ============================================================================
# CRITICAL: Middleware order matters! Applied in REVERSE order (last = outermost)
# Execution order: request_id → security → audit → rate_limit → logging → handler

# Request ID tracking (MUST BE FIRST - generates correlation ID for all other middleware)
app.middleware("http")(request_id_middleware)

# Security headers (applied early for all requests)
app.middleware("http")(security_headers_middleware)

# Audit logging (uses request_id from above)
app.middleware("http")(audit_middleware)

# Rate limiting (applied early to reject bad requests quickly)
if settings.ENABLE_RATE_LIMITING:
    app.middleware("http")(rate_limit_middleware)

# Structured logging (uses request_id and records SLI metrics)
app.middleware("http")(logging_middleware)

# Request timing
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# ============================================================================
# Exception Handlers
# ============================================================================
@app.exception_handler(AutoTestException)
async def autotest_exception_handler(request: Request, exc: AutoTestException):
    """Handler for custom AutoTest exceptions"""
    logger.warning(f"AutoTest exception: {exc.message}", extra={"details": exc.details})
    error_response = create_error_response(exc, status_code=400)
    return JSONResponse(
        status_code=400,
        content=error_response,
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An error occurred",
        },
    )


# ============================================================================
# Health Check Endpoints
# ============================================================================
@app.get("/health")
@cached(ttl=5, key_prefix="health:basic")  # Cache for 5 seconds
async def health_check(request: Request):
    """
    Simple health check endpoint for Docker

    🔥 CACHED: Results cached for 5s to reduce load from frequent polling
    """
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "version": "0.1.0",
    }


@app.get("/health/detailed")
@cached(ttl=10, key_prefix="health:detailed")  # Cache for 10 seconds
async def health_detailed(request: Request):
    """
    Comprehensive health check with all service statuses

    🔥 CACHED: Results cached for 10s to reduce dependency checks
    """
    return await comprehensive_health_check()


@app.get("/health/ready")
@cached(ttl=5, key_prefix="health:ready")  # Cache for 5 seconds
async def health_ready(request: Request):
    """
    Readiness check - are all dependencies ready?

    🔥 CACHED: Results cached for 5s for frequent K8s probes
    """
    result = await readiness_check()
    status_code = 200 if result["ready"] else 503
    return JSONResponse(status_code=status_code, content=result)


@app.get("/health/live")
async def health_live():
    """Liveness check - is the service alive?"""
    return await liveness_check()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AutoTest-RL API - Intelligent API Testing with Reinforcement Learning",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


# ============================================================================
# API Routes
# ============================================================================
from src.api.routes import documents_router, tests_router, metrics_router

app.include_router(
    documents_router,
    prefix="/api/v1/documents",
    tags=["Documents"]
)

app.include_router(
    tests_router,
    prefix="/api/v1/tests",
    tags=["Tests"]
)

app.include_router(
    metrics_router,
    tags=["Monitoring"]
)


# ============================================================================
# Development Info Endpoint
# ============================================================================
@app.get("/api/v1/info")
async def api_info():
    """API information and configuration (development only)"""
    if not settings.DEBUG:
        return {"error": "Endpoint only available in debug mode"}

    return {
        "environment": settings.ENVIRONMENT,
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.LLM_MODEL,
        "embedding_model": settings.EMBEDDING_MODEL,
        "rl_algorithm": settings.RL_ALGORITHM,
        "max_retries": settings.MAX_RETRIES,
        "rag_top_k": settings.RAG_TOP_K,
        "chunk_size": settings.CHUNK_SIZE,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
        workers=1 if settings.API_RELOAD else settings.API_WORKERS,
    )
