"""
Enhanced Health Checks
Check status of all system dependencies
"""
import httpx
import redis
import asyncio
from typing import Dict, Any
from datetime import datetime
from loguru import logger

from src.config import settings


async def check_redis() -> Dict[str, Any]:
    """
    Check Redis connectivity

    Returns:
        dict: Redis health status
    """
    try:
        client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            socket_connect_timeout=2,
        )

        # Ping Redis
        start_time = asyncio.get_event_loop().time()
        client.ping()
        latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000

        # Get Redis info
        info = client.info()

        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
            "version": info.get("redis_version"),
            "used_memory_human": info.get("used_memory_human"),
            "connected_clients": info.get("connected_clients"),
        }

    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "error_type": type(e).__name__,
        }


async def check_chromadb() -> Dict[str, Any]:
    """
    Check ChromaDB connectivity

    Returns:
        dict: ChromaDB health status
    """
    try:
        url = f"http://{settings.CHROMA_HOST}:{settings.CHROMA_PORT}/api/v1/heartbeat"

        async with httpx.AsyncClient(timeout=5.0) as client:
            start_time = asyncio.get_event_loop().time()
            response = await client.get(url)
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "latency_ms": round(latency_ms, 2),
                    "heartbeat": response.json(),
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": f"HTTP {response.status_code}",
                    "response": response.text[:200],
                }

    except Exception as e:
        logger.error(f"ChromaDB health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "error_type": type(e).__name__,
        }


async def check_ollama() -> Dict[str, Any]:
    """
    Check Ollama LLM service

    Returns:
        dict: Ollama health status
    """
    try:
        url = f"{settings.OLLAMA_BASE_URL}/api/tags"

        async with httpx.AsyncClient(timeout=5.0) as client:
            start_time = asyncio.get_event_loop().time()
            response = await client.get(url)
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])

                return {
                    "status": "healthy",
                    "latency_ms": round(latency_ms, 2),
                    "models_loaded": len(models),
                    "models": [m.get("name") for m in models[:5]],  # First 5 models
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": f"HTTP {response.status_code}",
                }

    except Exception as e:
        logger.error(f"Ollama health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "error_type": type(e).__name__,
        }


async def check_celery() -> Dict[str, Any]:
    """
    Check Celery worker status

    Returns:
        dict: Celery health status
    """
    try:
        from src.tasks.celery_app import celery_app

        # Ping workers
        start_time = asyncio.get_event_loop().time()
        result = celery_app.control.ping(timeout=2.0)
        latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000

        if result:
            workers = list(result)
            return {
                "status": "healthy",
                "latency_ms": round(latency_ms, 2),
                "workers_online": len(workers),
                "workers": [list(w.keys())[0] for w in workers],
            }
        else:
            return {
                "status": "unhealthy",
                "error": "No workers responding",
            }

    except Exception as e:
        logger.error(f"Celery health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "error_type": type(e).__name__,
        }


async def get_system_stats() -> Dict[str, Any]:
    """
    Get system statistics

    Returns:
        dict: System stats
    """
    try:
        import psutil

        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)

        # Memory usage
        memory = psutil.virtual_memory()

        # Disk usage
        disk = psutil.disk_usage('/')

        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_used_gb": round(memory.used / (1024**3), 2),
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "disk_percent": disk.percent,
            "disk_used_gb": round(disk.used / (1024**3), 2),
            "disk_total_gb": round(disk.total / (1024**3), 2),
        }

    except Exception as e:
        logger.error(f"System stats failed: {e}")
        return {
            "error": str(e),
        }


async def comprehensive_health_check() -> Dict[str, Any]:
    """
    Perform comprehensive health check of all services

    Returns:
        dict: Complete health status
    """
    # Run all checks in parallel
    redis_check, chromadb_check, ollama_check, celery_check, system_stats = await asyncio.gather(
        check_redis(),
        check_chromadb(),
        check_ollama(),
        check_celery(),
        get_system_stats(),
        return_exceptions=True
    )

    # Handle exceptions
    def safe_result(result, name):
        if isinstance(result, Exception):
            return {"status": "error", "error": str(result)}
        return result

    redis_result = safe_result(redis_check, "redis")
    chromadb_result = safe_result(chromadb_check, "chromadb")
    ollama_result = safe_result(ollama_check, "ollama")
    celery_result = safe_result(celery_check, "celery")
    stats_result = safe_result(system_stats, "system")

    # Determine overall status
    all_healthy = all([
        redis_result.get("status") == "healthy",
        chromadb_result.get("status") == "healthy",
        ollama_result.get("status") == "healthy",
        celery_result.get("status") == "healthy",
    ])

    overall_status = "healthy" if all_healthy else "degraded"

    return {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "version": "0.2.0",
        "environment": settings.ENVIRONMENT,
        "services": {
            "redis": redis_result,
            "chromadb": chromadb_result,
            "ollama": ollama_result,
            "celery": celery_result,
        },
        "system": stats_result,
    }


async def basic_health_check() -> Dict[str, Any]:
    """
    Basic health check (just API is alive)

    Returns:
        dict: Basic health status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "0.2.0",
        "environment": settings.ENVIRONMENT,
    }


async def readiness_check() -> Dict[str, Any]:
    """
    Readiness check (can API accept requests?)

    Checks critical services:
    - Redis (required for sessions)
    - ChromaDB (required for RAG)

    Returns:
        dict: Readiness status
    """
    redis_check, chromadb_check = await asyncio.gather(
        check_redis(),
        check_chromadb(),
        return_exceptions=True
    )

    redis_ready = not isinstance(redis_check, Exception) and redis_check.get("status") == "healthy"
    chromadb_ready = not isinstance(chromadb_check, Exception) and chromadb_check.get("status") == "healthy"

    is_ready = redis_ready and chromadb_ready

    return {
        "status": "ready" if is_ready else "not_ready",
        "timestamp": datetime.now().isoformat(),
        "checks": {
            "redis": "ready" if redis_ready else "not_ready",
            "chromadb": "ready" if chromadb_ready else "not_ready",
        }
    }


async def liveness_check() -> Dict[str, Any]:
    """
    Liveness check (is API process alive?)

    Returns:
        dict: Liveness status
    """
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
    }
