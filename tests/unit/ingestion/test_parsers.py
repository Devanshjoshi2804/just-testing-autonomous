"""
Unit Tests for Postman and Universal Parsers
"""
import pytest
import json

from src.ingestion.parsers import (
    PostmanParser,
    UniversalParser,
    detect_format,
    ParsingError,
    FormatNotSupportedError
)
from src.ingestion.models import UnifiedAPISpec


@pytest.fixture
def postman_parser():
    """Create Postman parser instance"""
    return PostmanParser()


@pytest.fixture
def universal_parser():
    """Create universal parser instance"""
    return UniversalParser()


@pytest.fixture
def simple_postman_collection():
    """Simple Postman collection"""
    return {
        "info": {
            "_postman_id": "test-collection-id",
            "name": "Test API Collection",
            "description": "A test collection",
            "version": "1.0.0"
        },
        "variable": [
            {"key": "baseUrl", "value": "https://api.test.com"}
        ],
        "item": [
            {
                "name": "Get users",
                "request": {
                    "method": "GET",
                    "url": {
                        "protocol": "https",
                        "host": ["api", "test", "com"],
                        "path": ["users"],
                        "query": [
                            {
                                "key": "page",
                                "value": "1",
                                "description": "Page number"
                            }
                        ]
                    },
                    "description": "Get list of users"
                },
                "response": [
                    {
                        "name": "Success",
                        "code": 200,
                        "body": json.dumps({
                            "users": [
                                {"id": 1, "name": "John"}
                            ]
                        })
                    }
                ]
            },
            {
                "name": "Create user",
                "request": {
                    "method": "POST",
                    "url": {
                        "protocol": "https",
                        "host": ["api", "test", "com"],
                        "path": ["users"]
                    },
                    "header": [
                        {
                            "key": "Content-Type",
                            "value": "application/json"
                        }
                    ],
                    "body": {
                        "mode": "raw",
                        "raw": json.dumps({"name": "New User"}),
                        "options": {
                            "raw": {"language": "json"}
                        }
                    }
                },
                "response": []
            }
        ]
    }


class TestPostmanParser:
    """Test Postman collection parser"""

    def test_parser_initialization(self, postman_parser):
        """Test parser initializes correctly"""
        assert postman_parser.name == 'PostmanParser'
        assert 'postman' in postman_parser.supported_formats

    def test_can_parse_postman_dict(self, postman_parser, simple_postman_collection):
        """Test can detect Postman collection"""
        assert postman_parser.can_parse(simple_postman_collection) is True

    def test_can_parse_postman_json_string(self, postman_parser, simple_postman_collection):
        """Test can detect Postman collection JSON string"""
        json_str = json.dumps(simple_postman_collection)
        assert postman_parser.can_parse(json_str) is True

    def test_can_parse_invalid_content(self, postman_parser):
        """Test rejects invalid content"""
        assert postman_parser.can_parse({}) is False
        assert postman_parser.can_parse("random text") is False

    def test_parse_simple_collection(self, postman_parser, simple_postman_collection):
        """Test parsing simple Postman collection"""
        spec = postman_parser.parse(simple_postman_collection)

        assert isinstance(spec, UnifiedAPISpec)
        assert spec.title == "Test API Collection"
        assert spec.version == "1.0.0"
        assert spec.base_url == "https://api.test.com"
        assert len(spec.endpoints) == 2

        # Check GET endpoint
        get_endpoint = spec.get_endpoint("GET", "/users")
        assert get_endpoint is not None
        assert get_endpoint.summary == "Get users"
        assert len(get_endpoint.parameters) == 1

        # Check query parameter
        param = get_endpoint.parameters[0]
        assert param.name == "page"
        assert param.location == "query"
        assert param.description == "Page number"

        # Check POST endpoint
        post_endpoint = spec.get_endpoint("POST", "/users")
        assert post_endpoint is not None
        assert post_endpoint.request_body is not None
        assert post_endpoint.request_body.content_type == "application/json"

    def test_parse_with_source_file(self, postman_parser, simple_postman_collection):
        """Test parsing with source file tracking"""
        spec = postman_parser.parse(
            simple_postman_collection,
            source_file="collection.json"
        )

        assert spec.source_file == "collection.json"
        assert spec.source_format == "postman"

    def test_parse_json_string(self, postman_parser, simple_postman_collection):
        """Test parsing JSON string"""
        json_str = json.dumps(simple_postman_collection)
        spec = postman_parser.parse(json_str)

        assert spec.title == "Test API Collection"
        assert len(spec.endpoints) == 2

    def test_base_url_extraction(self, postman_parser, simple_postman_collection):
        """Test base URL extraction from variables"""
        spec = postman_parser.parse(simple_postman_collection)

        assert spec.base_url == "https://api.test.com"
        assert len(spec.servers) == 1
        assert spec.servers[0].url == "https://api.test.com"

    def test_response_inference(self, postman_parser, simple_postman_collection):
        """Test response schema inference from examples"""
        spec = postman_parser.parse(simple_postman_collection)

        get_endpoint = spec.get_endpoint("GET", "/users")
        assert 200 in get_endpoint.responses

        # Should have inferred schema from response body
        response = get_endpoint.responses[200]
        assert response.schema is not None
        assert response.schema.type == "object"

    def test_form_data_parsing(self, postman_parser):
        """Test form data request body parsing"""
        collection = {
            "info": {
                "name": "Form Test",
                "_postman_id": "test-id"
            },
            "item": [
                {
                    "name": "Upload",
                    "request": {
                        "method": "POST",
                        "url": "https://api.test.com/upload",
                        "body": {
                            "mode": "formdata",
                            "formdata": [
                                {
                                    "key": "file",
                                    "type": "file",
                                    "description": "File to upload"
                                },
                                {
                                    "key": "name",
                                    "value": "filename.txt"
                                }
                            ]
                        }
                    }
                }
            ]
        }

        spec = postman_parser.parse(collection)
        endpoint = spec.endpoints[0]

        assert endpoint.request_body is not None
        assert endpoint.request_body.content_type == "multipart/form-data"
        assert endpoint.request_body.schema is not None
        assert "file" in endpoint.request_body.schema.properties
        assert "name" in endpoint.request_body.schema.properties


class TestUniversalParser:
    """Test universal parser"""

    def test_parser_initialization(self, universal_parser):
        """Test parser initializes correctly"""
        assert len(universal_parser.parsers) >= 2  # OpenAPI and Postman
        assert universal_parser.text_parser is not None

    def test_get_supported_formats(self, universal_parser):
        """Test getting supported formats"""
        formats = universal_parser.get_supported_formats()

        assert 'openapi' in formats
        assert 'postman' in formats
        assert 'text' in formats

    def test_detect_openapi_format(self, universal_parser):
        """Test detecting OpenAPI format"""
        content = {
            "openapi": "3.0.0",
            "info": {"title": "Test"},
            "paths": {}
        }

        detected = universal_parser.detect_format(content)
        assert detected == 'openapi'

    def test_detect_postman_format(self, universal_parser, simple_postman_collection):
        """Test detecting Postman format"""
        detected = universal_parser.detect_format(simple_postman_collection)
        assert detected == 'postman'

    def test_detect_text_format(self, universal_parser):
        """Test detecting text format"""
        content = "This is plain text API documentation"
        detected = universal_parser.detect_format(content)
        assert detected == 'text'

    def test_parse_openapi_auto_detect(self, universal_parser):
        """Test parsing OpenAPI with auto-detection"""
        content = {
            "openapi": "3.0.0",
            "info": {
                "title": "Auto Detect Test",
                "version": "1.0.0"
            },
            "paths": {
                "/test": {
                    "get": {
                        "responses": {
                            "200": {"description": "Success"}
                        }
                    }
                }
            }
        }

        spec = universal_parser.parse(content)

        assert spec.title == "Auto Detect Test"
        assert len(spec.endpoints) == 1

    def test_parse_postman_auto_detect(
        self,
        universal_parser,
        simple_postman_collection
    ):
        """Test parsing Postman with auto-detection"""
        spec = universal_parser.parse(simple_postman_collection)

        assert spec.title == "Test API Collection"
        assert len(spec.endpoints) == 2

    def test_parse_with_format_hint(self, universal_parser):
        """Test parsing with format hint"""
        content = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {}
        }

        spec = universal_parser.parse(content, format_hint='openapi')

        assert spec.title == "Test"

    def test_parse_json_string(self, universal_parser):
        """Test parsing JSON string"""
        content = json.dumps({
            "openapi": "3.0.0",
            "info": {"title": "JSON Test", "version": "1.0.0"},
            "paths": {}
        })

        spec = universal_parser.parse(content)

        assert spec.title == "JSON Test"

    def test_parse_unknown_format_raises(self, universal_parser):
        """Test parsing unknown format raises error"""
        with pytest.raises(FormatNotSupportedError):
            universal_parser.parse({"unknown": "format"})

    def test_format_from_extension(self, universal_parser):
        """Test determining format from file extension"""
        assert universal_parser._format_from_extension('.json') == 'openapi'
        assert universal_parser._format_from_extension('.yaml') == 'openapi'
        assert universal_parser._format_from_extension('.yml') == 'openapi'
        assert universal_parser._format_from_extension('.txt') == 'text'
        assert universal_parser._format_from_extension('.md') == 'text'


class TestDetectFormat:
    """Test standalone detect_format function"""

    def test_detect_openapi_json(self):
        """Test detecting OpenAPI from JSON"""
        content = '{"openapi": "3.0.0", "info": {}, "paths": {}}'
        assert detect_format(content) == 'openapi'

    def test_detect_openapi_dict(self):
        """Test detecting OpenAPI from dict"""
        content = {"swagger": "2.0", "info": {}, "paths": {}}
        assert detect_format(content) == 'openapi'

    def test_detect_postman(self):
        """Test detecting Postman collection"""
        content = {
            "info": {"_postman_id": "test"},
            "item": []
        }
        assert detect_format(content) == 'postman'

    def test_detect_text(self):
        """Test detecting text format"""
        content = "Random text documentation"
        assert detect_format(content) == 'text'

    def test_detect_unknown(self):
        """Test detecting unknown format"""
        content = {"random": "data"}
        assert detect_format(content) == 'unknown'
