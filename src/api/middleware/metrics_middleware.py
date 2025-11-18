"""
Metrics Middleware
Automatic Prometheus metrics collection for HTTP requests
Phase 10: Observability & Monitoring
"""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger

from src.observability.metrics import (
    record_http_request,
    http_requests_in_progress,
    update_active_sessions
)
from src.observability.tracing import (
    create_tracing_context,
    get_tracing_context,
    clear_tracing_context,
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic metrics collection

    Collects:
    - HTTP request counts by method, endpoint, and status code
    - Request duration histograms
    - Requests in progress gauge
    - Distributed tracing spans
    """

    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get request metadata
        method = request.method
        path = request.url.path

        # Normalize endpoint path (remove IDs)
        endpoint = self._normalize_path(path)

        # Get or create request ID
        request_id = getattr(request.state, "request_id", None)

        # Create tracing context
        trace_context = create_tracing_context(request_id=request_id)

        # Add to request state for use in handlers
        request.state.trace_context = trace_context

        # Create root span for this request
        root_span = trace_context.create_span(
            name=f"{method} {endpoint}",
            operation="http.request",
            http_method=method,
            http_path=path,
            http_endpoint=endpoint
        )

        # Track in-progress requests
        http_requests_in_progress.labels(
            method=method,
            endpoint=endpoint
        ).inc()

        # Start timing
        start_time = time.time()
        status_code = 500  # Default to 500 in case of exceptions

        try:
            # Process request
            response = await call_next(request)
            status_code = response.status_code

            # Add trace ID to response headers
            response.headers["X-Trace-ID"] = trace_context.trace_id

            return response

        except Exception as e:
            # Log error to span
            root_span.add_tag("error", True)
            root_span.add_tag("error.message", str(e))
            root_span.add_tag("error.type", type(e).__name__)

            logger.error(
                f"Request failed with exception",
                method=method,
                path=path,
                error=str(e),
                trace_id=trace_context.trace_id
            )

            raise

        finally:
            # Calculate duration
            duration = time.time() - start_time

            # Finish root span
            trace_context.finish_span(
                root_span,
                status="completed" if status_code < 500 else "error"
            )

            # Add status code tag
            root_span.add_tag("http.status_code", status_code)

            # Record metrics
            record_http_request(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                duration=duration
            )

            # Track in-progress requests
            http_requests_in_progress.labels(
                method=method,
                endpoint=endpoint
            ).dec()

            # Log trace summary for slow requests or errors
            if duration > 1.0 or status_code >= 500:
                trace_summary = trace_context.get_trace_summary()
                logger.warning(
                    f"Slow or error request",
                    **trace_summary,
                    duration_seconds=duration,
                    status_code=status_code
                )

            # Clear tracing context
            clear_tracing_context()

    def _normalize_path(self, path: str) -> str:
        """
        Normalize path to group similar endpoints

        Converts /api/v1/documents/abc123 to /api/v1/documents/{id}
        """
        parts = path.split("/")
        normalized_parts = []

        for i, part in enumerate(parts):
            # Check if this looks like an ID (UUID, hex, number)
            if self._looks_like_id(part):
                normalized_parts.append("{id}")
            else:
                normalized_parts.append(part)

        return "/".join(normalized_parts)

    def _looks_like_id(self, part: str) -> bool:
        """Check if a path part looks like an ID"""
        if not part:
            return False

        # Check for UUID pattern
        if len(part) == 36 and part.count("-") == 4:
            return True

        # Check for hex string (like session IDs)
        if len(part) >= 16 and all(c in "0123456789abcdef" for c in part.lower()):
            return True

        # Check for numeric ID
        if part.isdigit():
            return True

        # Check if starts with common prefixes
        if part.startswith(("doc_", "session_", "test_", "user_")):
            return True

        return False


# ============================================================================
# Metrics Endpoint
# ============================================================================

async def metrics_middleware(request: Request, call_next: Callable) -> Response:
    """
    Functional metrics middleware (lighter version)
    """
    method = request.method
    path = request.url.path
    start_time = time.time()

    # Normalize path
    endpoint = path
    for prefix in ["/api/v1/documents/", "/api/v1/tests/"]:
        if path.startswith(prefix) and len(path) > len(prefix):
            endpoint = prefix + "{id}"
            break

    try:
        response = await call_next(request)
        status_code = response.status_code

        # Record metrics
        duration = time.time() - start_time
        record_http_request(method, endpoint, status_code, duration)

        return response

    except Exception as e:
        duration = time.time() - start_time
        record_http_request(method, endpoint, 500, duration)
        raise
