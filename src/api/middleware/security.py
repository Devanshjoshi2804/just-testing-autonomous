"""
Security Middleware
Headers, input validation, and protection against common attacks
"""
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses

    Headers added:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security: max-age=31536000; includeSubDomains
    - Content-Security-Policy: default-src 'self'
    - Referrer-Policy: strict-origin-when-cross-origin
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy (adjust as needed)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        )

        return response


async def security_headers_middleware(request: Request, call_next: Callable) -> Response:
    """
    Functional security headers middleware
    """
    response = await call_next(request)

    # Add security headers
    security_headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "X-Powered-By": "AutoTest-RL",  # Custom header
    }

    for header, value in security_headers.items():
        response.headers[header] = value

    return response


class InputValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for input validation and sanitization

    Protections:
    - Null byte injection
    - Path traversal
    - Suspicious patterns
    - Excessive input size
    """

    MAX_QUERY_LENGTH = 2000
    MAX_HEADER_LENGTH = 8000

    SUSPICIOUS_PATTERNS = [
        "../",  # Path traversal
        "..\\",  # Path traversal (Windows)
        "\0",  # Null byte
        "<script",  # XSS attempt
        "javascript:",  # XSS attempt
        "onerror=",  # XSS attempt
        "${",  # Template injection
        "{{",  # Template injection
    ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Validate query string length
        query_string = str(request.url.query)
        if len(query_string) > self.MAX_QUERY_LENGTH:
            logger.warning(
                "Rejected request with excessive query length",
                length=len(query_string),
                path=request.url.path,
            )
            return Response(
                content="Query string too long",
                status_code=400,
            )

        # Check for suspicious patterns in query parameters
        for param, value in request.query_params.items():
            for pattern in self.SUSPICIOUS_PATTERNS:
                if pattern.lower() in value.lower():
                    logger.warning(
                        "Rejected request with suspicious pattern",
                        pattern=pattern,
                        param=param,
                        path=request.url.path,
                    )
                    return Response(
                        content="Invalid input detected",
                        status_code=400,
                    )

        # Check for suspicious patterns in headers
        for header, value in request.headers.items():
            if len(value) > self.MAX_HEADER_LENGTH:
                logger.warning(
                    "Rejected request with excessive header length",
                    header=header,
                    length=len(value),
                )
                return Response(
                    content="Header too long",
                    status_code=400,
                )

            for pattern in self.SUSPICIOUS_PATTERNS:
                if pattern.lower() in value.lower():
                    logger.warning(
                        "Rejected request with suspicious header",
                        pattern=pattern,
                        header=header,
                        path=request.url.path,
                    )
                    return Response(
                        content="Invalid header detected",
                        status_code=400,
                    )

        # Check path for traversal attempts
        path = str(request.url.path)
        if "../" in path or "..\\" in path or "\0" in path:
            logger.warning(
                "Rejected request with path traversal attempt",
                path=path,
            )
            return Response(
                content="Invalid path",
                status_code=400,
            )

        # Request is safe, continue processing
        return await call_next(request)
