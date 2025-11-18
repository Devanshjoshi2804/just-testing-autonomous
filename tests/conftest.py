"""
Pytest Configuration and Shared Fixtures
Phase 9: Critical Infrastructure & Production Readiness
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Generator, AsyncGenerator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Import application components
from src.config import settings
from src.api.main import app as main_app
from src.api.middleware.authentication import APIKeyManager, api_key_manager


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom settings"""
    # Set test environment
    settings.ENVIRONMENT = "testing"
    settings.DEBUG = True
    settings.REQUIRE_AUTH = False  # Disable auth for most tests


# ============================================================================
# Event Loop Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create event loop for async tests

    Scope: session - one loop for all tests
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Application Fixtures
# ============================================================================

@pytest.fixture
def app() -> FastAPI:
    """
    FastAPI application instance

    Returns a fresh app instance for each test
    """
    return main_app


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient, None, None]:
    """
    Test client for making requests to the API

    Usage:
        def test_endpoint(client):
            response = client.get("/health")
            assert response.status_code == 200
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """
    Async test client for testing async endpoints

    Usage:
        async def test_async_endpoint(async_client):
            response = await async_client.get("/health")
            assert response.status_code == 200
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


# ============================================================================
# Authentication Fixtures
# ============================================================================

@pytest.fixture
def api_key_manager_instance() -> APIKeyManager:
    """Fresh API key manager for testing"""
    return APIKeyManager()


@pytest.fixture
def test_api_key(api_key_manager_instance: APIKeyManager) -> str:
    """Generate a test API key"""
    return api_key_manager_instance.generate_api_key(
        name="test_key",
        permissions=["*"]
    )


@pytest.fixture
def limited_api_key(api_key_manager_instance: APIKeyManager) -> str:
    """Generate an API key with limited permissions"""
    return api_key_manager_instance.generate_api_key(
        name="limited_key",
        permissions=["documents:read", "tests:read"]
    )


@pytest.fixture
def authenticated_client(client: TestClient, test_api_key: str) -> TestClient:
    """
    Test client with authentication headers

    Usage:
        def test_protected_endpoint(authenticated_client):
            response = authenticated_client.get("/api/v1/documents")
            assert response.status_code == 200
    """
    client.headers["X-API-Key"] = test_api_key
    return client


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing without actual API calls"""
    mock = Mock()
    mock.generate = Mock(return_value="Mocked LLM response")
    mock.embed = Mock(return_value=[0.1] * 768)
    return mock


@pytest.fixture
def mock_chromadb():
    """Mock ChromaDB client"""
    mock = MagicMock()
    mock.add.return_value = None
    mock.query.return_value = {
        "documents": [["test document"]],
        "metadatas": [[{"source": "test"}]],
        "distances": [[0.5]]
    }
    return mock


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    mock = Mock()
    mock.get = Mock(return_value=None)
    mock.set = Mock(return_value=True)
    mock.delete = Mock(return_value=True)
    mock.exists = Mock(return_value=False)
    return mock


# ============================================================================
# File Fixtures
# ============================================================================

@pytest.fixture
def sample_openapi_json(tmp_path: Path) -> Path:
    """Create a sample OpenAPI JSON file"""
    content = """
    {
        "openapi": "3.0.0",
        "info": {
            "title": "Test API",
            "version": "1.0.0"
        },
        "paths": {
            "/users": {
                "get": {
                    "summary": "List users",
                    "responses": {
                        "200": {"description": "Success"}
                    }
                }
            }
        }
    }
    """
    file_path = tmp_path / "test_api.json"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def sample_pdf_path(tmp_path: Path) -> Path:
    """Create a sample PDF file path (not a real PDF)"""
    file_path = tmp_path / "test_doc.pdf"
    file_path.write_text("This is a test PDF content")
    return file_path


# ============================================================================
# Data Fixtures
# ============================================================================

@pytest.fixture
def sample_endpoint_data() -> dict:
    """Sample endpoint data for testing"""
    return {
        "path": "/api/v1/users",
        "method": "GET",
        "summary": "List all users",
        "auth_required": False,
        "parameters": [
            {
                "name": "limit",
                "in": "query",
                "type": "integer",
                "required": False
            }
        ]
    }


@pytest.fixture
def sample_test_result() -> dict:
    """Sample test result data"""
    return {
        "endpoint": "/api/v1/users",
        "method": "GET",
        "status_code": 200,
        "success": True,
        "attempts": 1,
        "elapsed_time": 0.123,
        "response": {"users": []}
    }


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_test_data(tmp_path: Path):
    """Automatically cleanup test data after each test"""
    yield
    # Cleanup logic here if needed


# ============================================================================
# Parametrize Helpers
# ============================================================================

@pytest.fixture(params=["pdf", "json", "yaml"])
def file_extension(request):
    """Parametrize tests with different file extensions"""
    return request.param


@pytest.fixture(params=[True, False])
def bool_param(request):
    """Parametrize tests with boolean values"""
    return request.param


# ============================================================================
# Markers for Test Selection
# ============================================================================

def pytest_collection_modifyitems(config, items):
    """
    Automatically mark tests based on their path/name

    This adds markers based on file location and test names
    """
    for item in items:
        # Mark tests based on directory
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)

        # Mark tests based on name patterns
        if "auth" in item.nodeid.lower():
            item.add_marker(pytest.mark.auth)
        if "security" in item.nodeid.lower():
            item.add_marker(pytest.mark.security)
        if "api" in item.nodeid.lower():
            item.add_marker(pytest.mark.api)
        if "workflow" in item.nodeid.lower():
            item.add_marker(pytest.mark.workflow)
