"""
Metrics API Routes
Prometheus metrics exposition endpoint
Phase 10: Observability & Monitoring
"""

from fastapi import APIRouter, Response
from loguru import logger

from src.observability.metrics import get_metrics
from src.config import settings


router = APIRouter()


@router.get(
    "/metrics",
    summary="Prometheus Metrics",
    description="Expose Prometheus metrics for scraping",
    response_class=Response,
    tags=["Monitoring"]
)
async def prometheus_metrics():
    """
    Expose Prometheus metrics in OpenMetrics format

    This endpoint is designed to be scraped by Prometheus.

    Returns:
        Prometheus-formatted metrics
    """
    if not settings.ENABLE_METRICS:
        return Response(
            content="Metrics collection is disabled",
            status_code=404
        )

    try:
        metrics_content, content_type = get_metrics()

        return Response(
            content=metrics_content,
            media_type=content_type
        )

    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}")
        return Response(
            content=f"Error generating metrics: {str(e)}",
            status_code=500
        )


@router.get(
    "/health/metrics",
    summary="Metrics Health Check",
    description="Check if metrics collection is working",
    tags=["Monitoring"]
)
async def metrics_health():
    """
    Check if metrics collection is enabled and working

    Returns:
        Health status of metrics system
    """
    return {
        "metrics_enabled": settings.ENABLE_METRICS,
        "metrics_port": settings.METRICS_PORT,
        "status": "healthy" if settings.ENABLE_METRICS else "disabled"
    }
