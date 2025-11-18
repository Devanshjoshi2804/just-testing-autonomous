"""
Request ID Middleware
Adds unique request ID to all requests for tracing and debugging
"""
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add unique request ID to all requests

    Features:
    - Generates UUID for each request
    - Preserves incoming X-Request-ID if present
    - Adds X-Request-ID to response headers
    - Stores request_id in request.state for use in routes
    - Logs request ID with all log messages
    """

    async def dispatch(self, request: Request, call_next):
        # Get request ID from header or generate new one
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Store in request state for use in routes
        request.state.request_id = request_id

        # Add to logger context
        with logger.contextualize(request_id=request_id):
            # Process request
            response = await call_next(request)

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response


async def request_id_middleware(request: Request, call_next):
    """
    Functional middleware for request ID
    Alternative to class-based middleware
    """
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    with logger.contextualize(request_id=request_id):
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def get_request_id(request: Request) -> str:
    """
    Get request ID from request state

    Args:
        request: FastAPI request

    Returns:
        Request ID string
    """
    return getattr(request.state, "request_id", "unknown")
