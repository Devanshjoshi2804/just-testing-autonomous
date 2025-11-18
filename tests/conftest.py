"""
Pytest Configuration and Shared Fixtures
Unified configuration from Phases 6-10
"""

import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Generator, AsyncGenerator, Dict, Any

# Import settings for tests
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Import application components
from src.config import settings, Settings
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

    # Add custom markers
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")


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
# Settings Fixtures
# ============================================================================

@pytest.fixture
def test_settings():
    """Test settings with safe defaults"""
    return Settings(
        ENVIRONMENT="test",
        DEBUG=True,
        OLLAMA_BASE_URL="http://localhost:11434",
        CHROMA_HOST="localhost",
        CHROMA_PORT=8001,
        REDIS_HOST="localhost",
        REDIS_PORT=6379,
    )


@pytest.fixture
def mock_settings():
    """Mock settings for isolated tests"""
    mock_settings = Mock(spec=Settings)
    mock_settings.ENVIRONMENT = "test"
    mock_settings.DEBUG = True
    mock_settings.LLM_PROVIDER = "ollama"
    mock_settings.LLM_MODEL = "llama3.2:3b"
    mock_settings.FAST_LLM_PROVIDER = "ollama"
    mock_settings.FAST_LLM_MODEL = "llama3.2:3b"
    mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
    mock_settings.CHROMA_HOST = "localhost"
    mock_settings.CHROMA_PORT = 8001
    mock_settings.REDIS_HOST = "localhost"
    mock_settings.REDIS_PORT = 6379
    return mock_settings


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
# Mock Service Fixtures
# ============================================================================

@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing without actual API calls"""
    mock = AsyncMock()
    mock.generate = AsyncMock(return_value={
        "response": "Mocked LLM response",
        "model": "llama3.2:3b"
    })
    mock.embed = Mock(return_value=[0.1] * 768)
    return mock


@pytest.fixture
def mock_chromadb():
    """Mock ChromaDB client"""
    mock = MagicMock()
    collection = Mock()
    collection.add = Mock(return_value=None)
    collection.query = Mock(return_value={
        "documents": [["test document"]],
        "metadatas": [[{"source": "test"}]],
        "distances": [[0.5]]
    })
    mock.get_or_create_collection = Mock(return_value=collection)
    mock.add = collection.add
    mock.query = collection.query
    return mock


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    mock = Mock()
    mock.get = Mock(return_value=None)
    mock.set = Mock(return_value=True)
    mock.delete = Mock(return_value=True)
    mock.exists = Mock(return_value=False)
    mock.ping = Mock(return_value=True)
    return mock


# ============================================================================
# File Fixtures
# ============================================================================

@pytest.fixture
def sample_openapi_json(tmp_path: Path) -> Path:
    """Create a sample OpenAPI JSON file"""
    content = {
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
    file_path = tmp_path / "test_api.json"
    file_path.write_text(json.dumps(content, indent=2))
    return file_path


@pytest.fixture
def sample_pdf_path(tmp_path: Path) -> Path:
    """Create a sample PDF file path (not a real PDF)"""
    file_path = tmp_path / "test_doc.pdf"
    file_path.write_text("This is a test PDF content")
    return file_path


@pytest.fixture
def temp_pdf_file(tmp_path):
    """Create a temporary PDF file for testing"""
    pdf_path = tmp_path / "test_api.pdf"
    # Create a minimal PDF (not a real PDF, just for path testing)
    pdf_path.write_text("Mock PDF content")
    return pdf_path


@pytest.fixture
def temp_json_file(tmp_path):
    """Create a temporary JSON file for testing"""
    json_path = tmp_path / "test_api.json"
    data = {"test": "data", "endpoints": []}
    json_path.write_text(json.dumps(data, indent=2))
    return json_path


@pytest.fixture
def temp_yaml_file(tmp_path):
    """Create a temporary YAML file for testing"""
    yaml_path = tmp_path / "test_api.yaml"
    yaml_path.write_text("openapi: 3.0.0\ninfo:\n  title: Test\n  version: 1.0.0")
    return yaml_path


# ============================================================================
# Data Fixtures
# ============================================================================

@pytest.fixture
def sample_endpoint():
    """Sample endpoint data for testing"""
    return {
        "path": "/api/users",
        "method": "GET",
        "description": "Retrieve list of users",
        "parameters": {
            "page": {
                "type": "integer",
                "minimum": 1,
                "maximum": 100,
                "default": 1,
                "in": "query"
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 50,
                "default": 10,
                "in": "query"
            }
        },
        "responses": {
            "200": {"description": "Success"},
            "400": {"description": "Bad Request"},
            "401": {"description": "Unauthorized"}
        }
    }


@pytest.fixture
def sample_endpoint_data() -> dict:
    """Sample endpoint data for testing (Phase 9 format)"""
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
def sample_endpoint_with_body():
    """Sample POST endpoint with request body"""
    return {
        "path": "/api/users",
        "method": "POST",
        "description": "Create a new user",
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["email", "name"],
                        "properties": {
                            "email": {
                                "type": "string",
                                "format": "email",
                                "minLength": 5,
                                "maxLength": 100
                            },
                            "name": {
                                "type": "string",
                                "minLength": 2,
                                "maxLength": 50
                            },
                            "age": {
                                "type": "integer",
                                "minimum": 18,
                                "maximum": 120
                            }
                        }
                    }
                }
            }
        },
        "responses": {
            "201": {"description": "Created"},
            "400": {"description": "Bad Request"},
            "422": {"description": "Validation Error"}
        }
    }


@pytest.fixture
def sample_constraints():
    """Sample constraints for testing"""
    return {
        "email": {
            "type": "string",
            "format": "email",
            "minLength": 5,
            "maxLength": 100,
            "required": True
        },
        "age": {
            "type": "integer",
            "minimum": 18,
            "maximum": 120,
            "required": False
        },
        "name": {
            "type": "string",
            "minLength": 2,
            "maxLength": 50,
            "pattern": "^[a-zA-Z ]+$",
            "required": True
        }
    }


@pytest.fixture
def sample_openapi_spec():
    """Sample OpenAPI specification"""
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Test API",
            "version": "1.0.0"
        },
        "paths": {
            "/api/users": {
                "get": {
                    "summary": "List users",
                    "parameters": [
                        {
                            "name": "page",
                            "in": "query",
                            "schema": {"type": "integer", "minimum": 1}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/User"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "required": ["id", "email"],
                    "properties": {
                        "id": {"type": "string", "format": "uuid"},
                        "email": {"type": "string", "format": "email"},
                        "name": {"type": "string"}
                    }
                }
            }
        }
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
        "response_time": 0.123,
        "request": {
            "params": {"page": 1, "limit": 10}
        },
        "response": {
            "status": 200,
            "body": {"users": [], "total": 0}
        }
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
