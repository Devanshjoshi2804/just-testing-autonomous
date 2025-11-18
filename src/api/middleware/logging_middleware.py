"""
Logging Middleware
Structured request/response logging with timing and context
"""
import time
import json
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured request/response logging

    Logs:
    - Request method, path, headers
    - Response status code, headers
    - Request processing time
    - Request/response body (if configured)
    - User agent, IP address
    - Errors and exceptions
    """

    def __init__(self, app, log_request_body: bool = False, log_response_body: bool = False):
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # Log request
        request_id = getattr(request.state, "request_id", "unknown")
        user_agent = request.headers.get("user-agent", "unknown")
        client_host = request.client.host if request.client else "unknown"

        log_data = {
            "event": "request_started",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_host": client_host,
            "user_agent": user_agent,
        }

        # Optionally log request body (be careful with sensitive data)
        if self.log_request_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    log_data["request_body"] = body.decode("utf-8")[:1000]  # Limit to 1000 chars
            except Exception as e:
                log_data["request_body_error"] = str(e)

        logger.info("Request started", **log_data)

        # Process request
        try:
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Log response
            response_log_data = {
                "event": "request_completed",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "process_time_ms": round(process_time * 1000, 2),
            }

            # Log level based on status code
            if response.status_code >= 500:
                logger.error("Request completed with server error", **response_log_data)
            elif response.status_code >= 400:
                logger.warning("Request completed with client error", **response_log_data)
            else:
                logger.info("Request completed successfully", **response_log_data)

            # Add process time to response header
            response.headers["X-Process-Time"] = str(process_time)

            return response

        except Exception as e:
            # Log exception
            process_time = time.time() - start_time

            logger.exception(
                "Request failed with exception",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                process_time_ms=round(process_time * 1000, 2),
                error=str(e),
                error_type=type(e).__name__,
            )

            raise


async def logging_middleware(request: Request, call_next: Callable) -> Response:
    """
    Functional logging middleware
    Simpler version without request/response body logging
    """
    start_time = time.time()
    request_id = getattr(request.state, "request_id", "unknown")

    logger.info(
        "request_started",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else "unknown",
    )

    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        logger.info(
            "request_completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            process_time_ms=round(process_time * 1000, 2),
        )

        response.headers["X-Process-Time"] = str(round(process_time, 4))

        return response

    except Exception as e:
        process_time = time.time() - start_time

        logger.exception(
            "request_failed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            process_time_ms=round(process_time * 1000, 2),
            error=str(e),
        )

        raise
