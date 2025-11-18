"""
API Authentication Middleware
API key-based authentication for securing endpoints
Phase 9: Critical Infrastructure & Production Readiness
"""

import hmac
import hashlib
import secrets
from typing import Callable, Optional, Set, List
from datetime import datetime, timedelta

from fastapi import Request, Response, HTTPException, status
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger

from src.config import settings
from src.exceptions import UnauthorizedError


# API Key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class APIKeyManager:
    """
    Manage API keys with in-memory storage

    In production, this should use a database or secret manager
    """

    def __init__(self):
        # In-memory API key store
        # Format: {api_key: {name, created_at, last_used, rate_limit}}
        self.api_keys: dict[str, dict] = {}

        # Master API key from environment
        if settings.MASTER_API_KEY:
            self.api_keys[settings.MASTER_API_KEY] = {
                "name": "master",
                "created_at": datetime.now(),
                "last_used": None,
                "rate_limit": None,  # No rate limit for master key
                "permissions": ["*"]  # All permissions
            }

    def generate_api_key(
        self,
        name: str,
        rate_limit: Optional[int] = None,
        permissions: Optional[List[str]] = None
    ) -> str:
        """
        Generate a new API key

        Args:
            name: Name/description for the API key
            rate_limit: Optional custom rate limit
            permissions: List of allowed permissions (default: all)

        Returns:
            Generated API key
        """
        # Generate secure random API key
        api_key = f"at_{secrets.token_urlsafe(32)}"

        # Store metadata
        self.api_keys[api_key] = {
            "name": name,
            "created_at": datetime.now(),
            "last_used": None,
            "rate_limit": rate_limit,
            "permissions": permissions or ["*"]
        }

        logger.info(f"Generated new API key: {name}")

        return api_key

    def validate_api_key(self, api_key: str) -> bool:
        """
        Validate an API key

        Args:
            api_key: API key to validate

        Returns:
            True if valid, False otherwise
        """
        if not api_key:
            return False

        # Check if key exists
        if api_key not in self.api_keys:
            return False

        # Update last used timestamp
        self.api_keys[api_key]["last_used"] = datetime.now()

        return True

    def get_key_info(self, api_key: str) -> Optional[dict]:
        """Get information about an API key"""
        return self.api_keys.get(api_key)

    def revoke_api_key(self, api_key: str) -> bool:
        """
        Revoke an API key

        Args:
            api_key: API key to revoke

        Returns:
            True if revoked, False if not found
        """
        if api_key in self.api_keys:
            key_info = self.api_keys.pop(api_key)
            logger.warning(f"Revoked API key: {key_info['name']}")
            return True
        return False

    def list_api_keys(self) -> List[dict]:
        """List all API keys (without exposing the actual keys)"""
        return [
            {
                "name": info["name"],
                "created_at": info["created_at"].isoformat(),
                "last_used": info["last_used"].isoformat() if info["last_used"] else None,
                "rate_limit": info["rate_limit"],
                "permissions": info["permissions"]
            }
            for info in self.api_keys.values()
        ]


# Global API key manager
api_key_manager = APIKeyManager()


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API key authentication

    Protects endpoints by requiring valid API key in X-API-Key header
    """

    def __init__(
        self,
        app,
        exempt_paths: Optional[Set[str]] = None,
        require_auth: bool = True
    ):
        """
        Initialize authentication middleware

        Args:
            app: FastAPI app
            exempt_paths: Paths that don't require authentication
            require_auth: Whether to require authentication (can be disabled for development)
        """
        super().__init__(app)
        self.require_auth = require_auth

        # Paths that don't require authentication
        self.exempt_paths = exempt_paths or {
            "/",
            "/health",
            "/health/detailed",
            "/health/ready",
            "/health/live",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/info",  # Development info endpoint
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip authentication for exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        # Skip authentication if disabled (development mode)
        if not self.require_auth:
            return await call_next(request)

        # Extract API key from header
        api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization", "").replace("Bearer ", "")

        # Validate API key
        if not api_key:
            logger.warning(
                "Request rejected: Missing API key",
                path=request.url.path,
                client=request.client.host if request.client else "unknown"
            )
            return Response(
                content='{"error": "Missing API key", "message": "Please provide X-API-Key header"}',
                status_code=401,
                media_type="application/json",
                headers={"WWW-Authenticate": 'APIKey realm="AutoTest-RL API"'}
            )

        # Check if API key is valid
        if not api_key_manager.validate_api_key(api_key):
            # SECURITY: Never log API keys (even partial). Use hash for correlation.
            import hashlib
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:12]

            logger.warning(
                "Request rejected: Invalid API key",
                path=request.url.path,
                key_hash=key_hash,  # Safe: Only log hash for correlation
                client=request.client.host if request.client else "unknown",
                method=request.method
            )
            return Response(
                content='{"error": "Invalid API key", "message": "The provided API key is invalid or revoked"}',
                status_code=401,
                media_type="application/json",
                headers={"WWW-Authenticate": 'APIKey realm="AutoTest-RL API"'}
            )

        # Get key info for logging
        key_info = api_key_manager.get_key_info(api_key)

        # Add API key info to request state for use in endpoints
        request.state.api_key = api_key
        request.state.api_key_name = key_info["name"] if key_info else "unknown"
        request.state.api_key_permissions = key_info["permissions"] if key_info else []

        # Log successful authentication
        logger.debug(
            "Request authenticated",
            path=request.url.path,
            api_key_name=request.state.api_key_name
        )

        # Continue processing request
        return await call_next(request)


async def get_current_api_key(request: Request) -> str:
    """
    Dependency to get current API key from request

    Usage:
        @app.get("/protected")
        async def protected_endpoint(api_key: str = Depends(get_current_api_key)):
            ...
    """
    return getattr(request.state, "api_key", None)


async def require_api_key(request: Request) -> str:
    """
    Dependency that requires valid API key

    Raises HTTPException if API key is invalid
    """
    api_key = await get_current_api_key(request)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
            headers={"WWW-Authenticate": 'APIKey realm="AutoTest-RL API"'}
        )

    return api_key


def check_permission(request: Request, permission: str) -> bool:
    """
    Check if current API key has a specific permission

    Args:
        request: FastAPI request
        permission: Permission to check (e.g., "documents:write", "tests:execute")

    Returns:
        True if permission granted, False otherwise
    """
    permissions = getattr(request.state, "api_key_permissions", [])

    # "*" grants all permissions
    if "*" in permissions:
        return True

    # Check exact permission match
    if permission in permissions:
        return True

    # Check wildcard permissions (e.g., "documents:*" grants "documents:write")
    permission_parts = permission.split(":")
    if len(permission_parts) == 2:
        wildcard = f"{permission_parts[0]}:*"
        if wildcard in permissions:
            return True

    return False


async def require_permission(permission: str):
    """
    Dependency that requires a specific permission

    Usage:
        @app.post("/api/v1/documents/upload")
        async def upload(api_key: str = Depends(require_permission("documents:write"))):
            ...
    """
    async def _check_permission(request: Request):
        # First ensure API key is present
        api_key = await require_api_key(request)

        # Check permission
        if not check_permission(request, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission} required"
            )

        return api_key

    return _check_permission
