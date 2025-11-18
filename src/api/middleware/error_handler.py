"""
Enhanced Error Handler Middleware
Provides structured error responses with correlation IDs for debugging
"""
import traceback
import sys
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from loguru import logger

from src.config import settings


class ErrorResponse:
    """
    Structured error response format

    Provides consistent error responses across the API with:
    - Unique correlation ID for tracking
    - User-friendly error messages
    - Debug information (in dev mode)
    - Timestamp for audit trail
    """

    def __init__(
        self,
        error_type: str,
        message: str,
        correlation_id: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        debug_info: Optional[Dict[str, Any]] = None
    ):
        self.error_type = error_type
        self.message = message
        self.correlation_id = correlation_id
        self.status_code = status_code
        self.details = details or {}
        self.debug_info = debug_info if settings.DEBUG else None
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response"""
        response = {
            "error": self.error_type,
            "message": self.message,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp
        }

        if self.details:
            response["details"] = self.details

        if self.debug_info and settings.DEBUG:
            response["debug"] = self.debug_info

        return response


def get_correlation_id(request: Request) -> str:
    """
    Get or generate correlation ID for request

    Tries to use X-Request-ID if present, otherwise generates new one
    """
    return getattr(request.state, 'request_id', 'unknown')


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle Pydantic validation errors

    Returns 422 with detailed field-level validation errors
    """
    correlation_id = get_correlation_id(request)

    # Extract validation errors
    errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error['loc'])
        errors.append({
            "field": field_path,
            "message": error['msg'],
            "type": error['type']
        })

    logger.warning(
        f"Validation error: {len(errors)} field(s) failed",
        correlation_id=correlation_id,
        errors=errors,
        path=request.url.path
    )

    error_response = ErrorResponse(
        error_type="ValidationError",
        message=f"Request validation failed: {len(errors)} error(s)",
        correlation_id=correlation_id,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details={"validation_errors": errors}
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.to_dict(),
        headers={
            "X-Correlation-ID": correlation_id,
            "X-Error-Type": "ValidationError"
        }
    )


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """
    Handle ValueError exceptions (typically from custom validators)

    Returns 422 with error message
    """
    correlation_id = get_correlation_id(request)

    logger.warning(
        f"ValueError: {str(exc)}",
        correlation_id=correlation_id,
        path=request.url.path
    )

    error_response = ErrorResponse(
        error_type="ValidationError",
        message=str(exc),
        correlation_id=correlation_id,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.to_dict(),
        headers={
            "X-Correlation-ID": correlation_id,
            "X-Error-Type": "ValidationError"
        }
    )


async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle 404 Not Found errors

    Returns user-friendly 404 message
    """
    correlation_id = get_correlation_id(request)

    logger.info(
        f"Resource not found: {request.url.path}",
        correlation_id=correlation_id,
        method=request.method
    )

    error_response = ErrorResponse(
        error_type="NotFound",
        message=f"The requested resource was not found: {request.url.path}",
        correlation_id=correlation_id,
        status_code=status.HTTP_404_NOT_FOUND,
        details={
            "path": request.url.path,
            "method": request.method
        }
    )

    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=error_response.to_dict(),
        headers={
            "X-Correlation-ID": correlation_id,
            "X-Error-Type": "NotFound"
        }
    )


async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle internal server errors (500)

    Logs full traceback and returns safe error message to client
    """
    correlation_id = get_correlation_id(request)

    # Get exception details
    exc_type = type(exc).__name__
    exc_message = str(exc)

    # Get traceback
    tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
    tb_string = "".join(tb)

    # Log with full details
    logger.error(
        f"Internal server error: {exc_type}: {exc_message}",
        correlation_id=correlation_id,
        path=request.url.path,
        method=request.method,
        exc_info=True
    )

    # Build debug info (only in DEBUG mode)
    debug_info = None
    if settings.DEBUG:
        debug_info = {
            "exception_type": exc_type,
            "exception_message": exc_message,
            "traceback": tb_string,
            "path": request.url.path,
            "method": request.method
        }

    # User-friendly message (don't leak implementation details in production)
    user_message = (
        f"An internal error occurred. Please contact support with correlation ID: {correlation_id}"
        if not settings.DEBUG
        else f"{exc_type}: {exc_message}"
    )

    error_response = ErrorResponse(
        error_type="InternalServerError",
        message=user_message,
        correlation_id=correlation_id,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        debug_info=debug_info
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.to_dict(),
        headers={
            "X-Correlation-ID": correlation_id,
            "X-Error-Type": "InternalServerError"
        }
    )


async def rate_limit_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle rate limit exceeded errors (429)

    Returns retry information
    """
    correlation_id = get_correlation_id(request)

    # Extract retry information from exception if available
    retry_after = getattr(exc, 'retry_after', 60)

    logger.warning(
        f"Rate limit exceeded",
        correlation_id=correlation_id,
        path=request.url.path,
        client=request.client.host if request.client else "unknown"
    )

    error_response = ErrorResponse(
        error_type="RateLimitExceeded",
        message="Too many requests. Please try again later.",
        correlation_id=correlation_id,
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        details={
            "retry_after_seconds": retry_after,
            "message": "Rate limit exceeded. Please slow down your requests."
        }
    )

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=error_response.to_dict(),
        headers={
            "X-Correlation-ID": correlation_id,
            "X-Error-Type": "RateLimitExceeded",
            "Retry-After": str(retry_after)
        }
    )


async def unauthorized_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle authentication errors (401)

    Returns authentication required message
    """
    correlation_id = get_correlation_id(request)

    logger.warning(
        f"Unauthorized access attempt",
        correlation_id=correlation_id,
        path=request.url.path,
        client=request.client.host if request.client else "unknown"
    )

    error_response = ErrorResponse(
        error_type="Unauthorized",
        message="Authentication required. Please provide valid credentials.",
        correlation_id=correlation_id,
        status_code=status.HTTP_401_UNAUTHORIZED,
        details={
            "authentication_required": True
        }
    )

    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content=error_response.to_dict(),
        headers={
            "X-Correlation-ID": correlation_id,
            "X-Error-Type": "Unauthorized",
            "WWW-Authenticate": "Bearer"
        }
    )


async def forbidden_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle authorization errors (403)

    Returns permission denied message
    """
    correlation_id = get_correlation_id(request)

    logger.warning(
        f"Forbidden access attempt",
        correlation_id=correlation_id,
        path=request.url.path,
        client=request.client.host if request.client else "unknown"
    )

    error_response = ErrorResponse(
        error_type="Forbidden",
        message="You don't have permission to access this resource.",
        correlation_id=correlation_id,
        status_code=status.HTTP_403_FORBIDDEN
    )

    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content=error_response.to_dict(),
        headers={
            "X-Correlation-ID": correlation_id,
            "X-Error-Type": "Forbidden"
        }
    )


def register_error_handlers(app):
    """
    Register all error handlers with FastAPI app

    Call this in main.py after creating the app
    """
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException

    # Validation errors
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValueError, value_error_handler)

    # HTTP errors
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions with appropriate handler"""
        correlation_id = get_correlation_id(request)

        # Route to specific handler based on status code
        if exc.status_code == 404:
            return await not_found_handler(request, exc)
        elif exc.status_code == 401:
            return await unauthorized_handler(request, exc)
        elif exc.status_code == 403:
            return await forbidden_handler(request, exc)
        elif exc.status_code == 429:
            return await rate_limit_handler(request, exc)
        else:
            # Generic HTTP error
            logger.warning(
                f"HTTP {exc.status_code}: {exc.detail}",
                correlation_id=correlation_id,
                path=request.url.path
            )

            error_response = ErrorResponse(
                error_type=f"HTTP{exc.status_code}",
                message=str(exc.detail),
                correlation_id=correlation_id,
                status_code=exc.status_code
            )

            return JSONResponse(
                status_code=exc.status_code,
                content=error_response.to_dict(),
                headers={
                    "X-Correlation-ID": correlation_id
                }
            )

    # Catch-all for unhandled exceptions
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Catch all unhandled exceptions"""
        return await internal_error_handler(request, exc)

    logger.info("✅ Error handlers registered successfully")
