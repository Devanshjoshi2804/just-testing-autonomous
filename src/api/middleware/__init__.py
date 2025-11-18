"""
FastAPI Middleware
Request processing, logging, security, authentication, rate limiting, and metrics
Phase 9: Critical Infrastructure & Production Readiness
Phase 10: Observability & Monitoring
"""

from src.api.middleware.request_id import request_id_middleware
from src.api.middleware.logging_middleware import logging_middleware
from src.api.middleware.security import security_headers_middleware, InputValidationMiddleware
from src.api.middleware.rate_limit import RateLimitMiddleware, RateLimiter, rate_limit
from src.api.middleware.authentication import (
    AuthenticationMiddleware,
    api_key_manager,
    get_current_api_key,
    require_api_key,
    require_permission,
    check_permission,
)
from src.api.middleware.metrics_middleware import MetricsMiddleware, metrics_middleware

__all__ = [
    "request_id_middleware",
    "logging_middleware",
    "security_headers_middleware",
    "InputValidationMiddleware",
    "RateLimitMiddleware",
    "RateLimiter",
    "rate_limit",
    "AuthenticationMiddleware",
    "api_key_manager",
    "get_current_api_key",
    "require_api_key",
    "require_permission",
    "check_permission",
    "MetricsMiddleware",
    "metrics_middleware",
]
