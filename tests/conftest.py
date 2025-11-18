"""
Pytest Configuration and Shared Fixtures
"""
import pytest
import asyncio
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock

# Import settings for tests
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Settings


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom settings"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")


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
    settings = Mock(spec=Settings)
    settings.ENVIRONMENT = "test"
    settings.DEBUG = True
    settings.LLM_PROVIDER = "ollama"
    settings.LLM_MODEL = "llama3.2:3b"
    settings.FAST_LLM_PROVIDER = "ollama"
    settings.FAST_LLM_MODEL = "llama3.2:3b"
    settings.OLLAMA_BASE_URL = "http://localhost:11434"
    settings.CHROMA_HOST = "localhost"
    settings.CHROMA_PORT = 8001
    settings.REDIS_HOST = "localhost"
    settings.REDIS_PORT = 6379
    return settings


# ============================================================================
# Sample Data Fixtures
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
def sample_test_result():
    """Sample test execution result"""
    return {
        "endpoint": "/api/users",
        "method": "GET",
        "status_code": 200,
        "response_time": 0.123,
        "success": True,
        "request": {
            "params": {"page": 1, "limit": 10}
        },
        "response": {
            "status": 200,
            "body": {"users": [], "total": 0}
        }
    }


# ============================================================================
# Mock Service Fixtures
# ============================================================================

@pytest.fixture
def mock_llm_client():
    """Mock LLM client"""
    client = AsyncMock()
    client.generate.return_value = {
        "response": "Mock LLM response",
        "model": "llama3.2:3b"
    }
    return client


@pytest.fixture
def mock_chromadb():
    """Mock ChromaDB client"""
    client = Mock()
    collection = Mock()
    collection.add = Mock()
    collection.query = Mock(return_value={
        "documents": [["Sample document"]],
        "metadatas": [[{"source": "test"}]],
        "distances": [[0.5]]
    })
    client.get_or_create_collection.return_value = collection
    return client


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    client = Mock()
    client.get = Mock(return_value=None)
    client.set = Mock(return_value=True)
    client.ping = Mock(return_value=True)
    return client


# ============================================================================
# Temporary File Fixtures
# ============================================================================

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
    import json
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
# Async Fixtures
# ============================================================================

@pytest.fixture
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_temp_files(tmp_path):
    """Cleanup temporary files after each test"""
    yield
    # Cleanup happens automatically with tmp_path
