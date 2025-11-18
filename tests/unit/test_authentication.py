"""
Unit Tests for Authentication Middleware
Phase 9: Critical Infrastructure & Production Readiness
"""

import pytest
from unittest.mock import Mock, patch
from fastapi import Request, HTTPException
from starlette.datastructures import Headers

from src.api.middleware.authentication import (
    APIKeyManager,
    AuthenticationMiddleware,
    api_key_manager,
    check_permission,
    get_current_api_key,
    require_api_key,
)


class TestAPIKeyManager:
    """Test API key management functionality"""

    def test_generate_api_key(self, api_key_manager_instance):
        """Test generating a new API key"""
        api_key = api_key_manager_instance.generate_api_key("test_app")

        assert api_key.startswith("at_")
        assert len(api_key) > 10
        assert "test_app" in str(api_key_manager_instance.list_api_keys())

    def test_validate_valid_api_key(self, api_key_manager_instance):
        """Test validating a valid API key"""
        api_key = api_key_manager_instance.generate_api_key("test_app")

        assert api_key_manager_instance.validate_api_key(api_key) is True

    def test_validate_invalid_api_key(self, api_key_manager_instance):
        """Test validating an invalid API key"""
        assert api_key_manager_instance.validate_api_key("invalid_key") is False

    def test_validate_empty_api_key(self, api_key_manager_instance):
        """Test validating an empty API key"""
        assert api_key_manager_instance.validate_api_key("") is False
        assert api_key_manager_instance.validate_api_key(None) is False

    def test_get_key_info(self, api_key_manager_instance):
        """Test retrieving API key information"""
        api_key = api_key_manager_instance.generate_api_key(
            "test_app",
            rate_limit=100,
            permissions=["documents:read"]
        )

        info = api_key_manager_instance.get_key_info(api_key)

        assert info is not None
        assert info["name"] == "test_app"
        assert info["rate_limit"] == 100
        assert "documents:read" in info["permissions"]

    def test_revoke_api_key(self, api_key_manager_instance):
        """Test revoking an API key"""
        api_key = api_key_manager_instance.generate_api_key("test_app")

        # Key should be valid before revocation
        assert api_key_manager_instance.validate_api_key(api_key) is True

        # Revoke the key
        assert api_key_manager_instance.revoke_api_key(api_key) is True

        # Key should be invalid after revocation
        assert api_key_manager_instance.validate_api_key(api_key) is False

    def test_revoke_nonexistent_key(self, api_key_manager_instance):
        """Test revoking a key that doesn't exist"""
        assert api_key_manager_instance.revoke_api_key("nonexistent") is False

    def test_list_api_keys(self, api_key_manager_instance):
        """Test listing all API keys"""
        # Generate multiple keys
        api_key_manager_instance.generate_api_key("app1")
        api_key_manager_instance.generate_api_key("app2")

        keys = api_key_manager_instance.list_api_keys()

        assert len(keys) >= 2
        assert any(k["name"] == "app1" for k in keys)
        assert any(k["name"] == "app2" for k in keys)

        # Ensure actual keys are not exposed
        for key_info in keys:
            assert "name" in key_info
            assert "created_at" in key_info
            # Should not contain the actual API key
            assert not any(v.startswith("at_") for v in key_info.values() if isinstance(v, str))

    def test_api_key_last_used_updated(self, api_key_manager_instance):
        """Test that last_used timestamp is updated on validation"""
        api_key = api_key_manager_instance.generate_api_key("test_app")

        info_before = api_key_manager_instance.get_key_info(api_key)
        assert info_before["last_used"] is None

        # Validate to update last_used
        api_key_manager_instance.validate_api_key(api_key)

        info_after = api_key_manager_instance.get_key_info(api_key)
        assert info_after["last_used"] is not None

    def test_master_api_key_initialization(self):
        """Test that master API key is initialized if provided"""
        with patch('src.config.settings.MASTER_API_KEY', "test_master_key"):
            manager = APIKeyManager()

            # Master key should be valid
            assert manager.validate_api_key("test_master_key") is True

            # Master key should have all permissions
            info = manager.get_key_info("test_master_key")
            assert "*" in info["permissions"]

    def test_custom_permissions(self, api_key_manager_instance):
        """Test generating keys with custom permissions"""
        api_key = api_key_manager_instance.generate_api_key(
            "limited_app",
            permissions=["documents:read", "tests:read"]
        )

        info = api_key_manager_instance.get_key_info(api_key)
        assert set(info["permissions"]) == {"documents:read", "tests:read"}


class TestPermissionChecking:
    """Test permission checking functionality"""

    def test_check_permission_with_wildcard(self):
        """Test checking permission with wildcard"""
        request = Mock(spec=Request)
        request.state.api_key_permissions = ["*"]

        assert check_permission(request, "any:permission") is True
        assert check_permission(request, "documents:write") is True

    def test_check_permission_exact_match(self):
        """Test checking permission with exact match"""
        request = Mock(spec=Request)
        request.state.api_key_permissions = ["documents:read", "tests:execute"]

        assert check_permission(request, "documents:read") is True
        assert check_permission(request, "tests:execute") is True
        assert check_permission(request, "documents:write") is False

    def test_check_permission_with_resource_wildcard(self):
        """Test checking permission with resource-level wildcard"""
        request = Mock(spec=Request)
        request.state.api_key_permissions = ["documents:*"]

        assert check_permission(request, "documents:read") is True
        assert check_permission(request, "documents:write") is True
        assert check_permission(request, "documents:delete") is True
        assert check_permission(request, "tests:read") is False

    def test_check_permission_no_permissions(self):
        """Test checking permission with no permissions set"""
        request = Mock(spec=Request)
        request.state.api_key_permissions = []

        assert check_permission(request, "documents:read") is False


class TestAuthenticationMiddleware:
    """Test authentication middleware"""

    @pytest.mark.asyncio
    async def test_exempt_paths_bypass_auth(self):
        """Test that exempt paths bypass authentication"""
        # Create middleware
        app_mock = Mock()
        middleware = AuthenticationMiddleware(
            app=app_mock,
            require_auth=True
        )

        # Mock request and call_next
        request = Mock(spec=Request)
        request.url.path = "/health"

        call_next = Mock()
        call_next.return_value = Mock()  # Simulated response

        # Should bypass auth for exempt paths
        await middleware.dispatch(request, call_next)

        # call_next should have been called
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_missing_api_key_returns_401(self):
        """Test that missing API key returns 401"""
        app_mock = Mock()
        middleware = AuthenticationMiddleware(
            app=app_mock,
            require_auth=True
        )

        request = Mock(spec=Request)
        request.url.path = "/api/v1/documents"
        request.headers = Headers({})
        request.client.host = "127.0.0.1"

        call_next = Mock()

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 401
        assert b"Missing API key" in response.body

    @pytest.mark.asyncio
    async def test_invalid_api_key_returns_401(self, api_key_manager_instance):
        """Test that invalid API key returns 401"""
        app_mock = Mock()
        middleware = AuthenticationMiddleware(
            app=app_mock,
            require_auth=True
        )

        # Patch the global api_key_manager
        with patch('src.api.middleware.authentication.api_key_manager', api_key_manager_instance):
            request = Mock(spec=Request)
            request.url.path = "/api/v1/documents"
            request.headers = Headers({"X-API-Key": "invalid_key"})
            request.client.host = "127.0.0.1"

            call_next = Mock()

            response = await middleware.dispatch(request, call_next)

            assert response.status_code == 401
            assert b"Invalid API key" in response.body

    @pytest.mark.asyncio
    async def test_valid_api_key_allows_access(self, api_key_manager_instance):
        """Test that valid API key allows access"""
        app_mock = Mock()
        middleware = AuthenticationMiddleware(
            app=app_mock,
            require_auth=True
        )

        # Generate valid key
        valid_key = api_key_manager_instance.generate_api_key("test_app")

        # Patch the global api_key_manager
        with patch('src.api.middleware.authentication.api_key_manager', api_key_manager_instance):
            request = Mock(spec=Request)
            request.url.path = "/api/v1/documents"
            request.headers = Headers({"X-API-Key": valid_key})
            request.client.host = "127.0.0.1"
            request.state = Mock()

            call_next = Mock()
            call_next.return_value = Mock(status_code=200)

            response = await middleware.dispatch(request, call_next)

            # Should pass through
            call_next.assert_called_once()
            assert hasattr(request.state, 'api_key')

    @pytest.mark.asyncio
    async def test_auth_disabled_allows_all(self):
        """Test that disabling auth allows all requests"""
        app_mock = Mock()
        middleware = AuthenticationMiddleware(
            app=app_mock,
            require_auth=False  # Auth disabled
        )

        request = Mock(spec=Request)
        request.url.path = "/api/v1/documents"
        request.headers = Headers({})  # No API key

        call_next = Mock()
        call_next.return_value = Mock()

        await middleware.dispatch(request, call_next)

        # Should pass through even without API key
        call_next.assert_called_once()


@pytest.mark.asyncio
async def test_require_api_key_dependency():
    """Test the require_api_key dependency"""
    # Request with API key
    request = Mock(spec=Request)
    request.state.api_key = "test_key"

    result = await require_api_key(request)
    assert result == "test_key"

    # Request without API key
    request_no_key = Mock(spec=Request)

    with pytest.raises(HTTPException) as exc_info:
        await require_api_key(request_no_key)

    assert exc_info.value.status_code == 401
