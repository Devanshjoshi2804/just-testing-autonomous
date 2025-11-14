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

# ============================================================================
# Application Lifespan Management
# ============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("🚀 Starting AutoTest-RL API...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER}")
    logger.info(f"LLM Model: {settings.LLM_MODEL}")

    yield

    # Shutdown
    logger.info("👋 Shutting down AutoTest-RL API...")


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
# Request Timing Middleware
# ============================================================================
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
async def health_check():
    """Health check endpoint for Docker"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "version": "0.1.0",
    }


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
# API Routes (to be imported)
# ============================================================================
# TODO: Add routers
# from src.api.routes import documents, tests, results
# app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
# app.include_router(tests.router, prefix="/api/v1/tests", tags=["Tests"])
# app.include_router(results.router, prefix="/api/v1/results", tags=["Results"])


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
