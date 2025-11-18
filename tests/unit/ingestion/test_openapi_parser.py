"""
Unit Tests for OpenAPI Parser
Tests OpenAPI 3.x and Swagger 2.0 parsing
"""
import pytest
import json

from src.ingestion.parsers import OpenAPIParser, ParsingError
from src.ingestion.models import (
    UnifiedAPISpec,
    HTTPMethod,
    ParameterLocation,
    DataType,
    AuthType
)


@pytest.fixture
def parser():
    """Create OpenAPI parser instance"""
    return OpenAPIParser()


@pytest.fixture
def simple_openapi_3():
    """Simple OpenAPI 3.0 spec"""
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Simple API",
            "version": "1.0.0",
            "description": "A simple test API"
        },
        "servers": [
            {"url": "https://api.example.com"}
        ],
        "paths": {
            "/users": {
                "get": {
                    "summary": "List users",
                    "responses": {
                        "200": {
                            "description": "Success"
                        }
                    }
                }
            }
        }
    }


@pytest.fixture
def complex_openapi_3():
    """Complex OpenAPI 3.0 spec with parameters and schemas"""
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Pet Store API",
            "version": "2.0.0",
            "description": "A sample Pet Store API"
        },
        "servers": [
            {
                "url": "https://petstore.example.com/v2",
                "description": "Production server"
            }
        ],
        "components": {
            "schemas": {
                "Pet": {
                    "type": "object",
                    "required": ["name"],
                    "properties": {
                        "id": {
                            "type": "integer",
                            "format": "int64"
                        },
                        "name": {
                            "type": "string"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["available", "pending", "sold"]
                        }
                    }
                }
            },
            "securitySchemes": {
                "api_key": {
                    "type": "apiKey",
                    "name": "X-API-Key",
                    "in": "header"
                }
            }
        },
        "paths": {
            "/pets/{petId}": {
                "get": {
                    "summary": "Get pet by ID",
                    "operationId": "getPetById",
                    "tags": ["pets"],
                    "parameters": [
                        {
                            "name": "petId",
                            "in": "path",
                            "required": True,
                            "description": "ID of pet to return",
                            "schema": {
                                "type": "integer",
                                "format": "int64"
                            }
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful operation",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Pet"
                                    }
                                }
                            }
                        },
                        "404": {
                            "description": "Pet not found"
                        }
                    }
                },
                "post": {
                    "summary": "Update pet",
                    "tags": ["pets"],
                    "parameters": [
                        {
                            "name": "petId",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"}
                        }
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/Pet"
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Pet updated"
                        }
                    }
                }
            }
        },
        "security": [
            {"api_key": []}
        ]
    }


@pytest.fixture
def swagger_2_spec():
    """Swagger 2.0 spec"""
    return {
        "swagger": "2.0",
        "info": {
            "title": "Swagger API",
            "version": "1.0.0"
        },
        "host": "api.example.com",
        "basePath": "/v1",
        "schemes": ["https"],
        "paths": {
            "/products": {
                "get": {
                    "summary": "List products",
                    "produces": ["application/json"],
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "type": "integer",
                            "description": "Max items to return"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Success",
                            "schema": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "integer"},
                                        "name": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "securityDefinitions": {
            "basicAuth": {
                "type": "basic"
            }
        }
    }


class TestOpenAPIParser:
    """Test OpenAPI parser"""

    def test_parser_initialization(self, parser):
        """Test parser initializes correctly"""
        assert parser.name == 'OpenAPIParser'
        assert 'openapi' in parser.supported_formats
        assert 'swagger' in parser.supported_formats

    def test_can_parse_openapi_3_dict(self, parser, simple_openapi_3):
        """Test can detect OpenAPI 3.x dict"""
        assert parser.can_parse(simple_openapi_3) is True

    def test_can_parse_openapi_3_json_string(self, parser, simple_openapi_3):
        """Test can detect OpenAPI 3.x JSON string"""
        json_str = json.dumps(simple_openapi_3)
        assert parser.can_parse(json_str) is True

    def test_can_parse_swagger_2(self, parser, swagger_2_spec):
        """Test can detect Swagger 2.0"""
        assert parser.can_parse(swagger_2_spec) is True

    def test_can_parse_invalid_content(self, parser):
        """Test rejects invalid content"""
        assert parser.can_parse({}) is False
        assert parser.can_parse("random text") is False
        assert parser.can_parse({"random": "object"}) is False

    def test_parse_simple_openapi_3(self, parser, simple_openapi_3):
        """Test parsing simple OpenAPI 3.0 spec"""
        spec = parser.parse(simple_openapi_3)

        assert isinstance(spec, UnifiedAPISpec)
        assert spec.title == "Simple API"
        assert spec.version == "1.0.0"
        assert spec.description == "A simple test API"
        assert len(spec.servers) == 1
        assert spec.servers[0].url == "https://api.example.com"
        assert len(spec.endpoints) == 1

        # Check endpoint
        endpoint = spec.endpoints[0]
        assert endpoint.method == "GET"
        assert endpoint.path == "/users"
        assert endpoint.summary == "List users"
        assert 200 in endpoint.responses

    def test_parse_complex_openapi_3(self, parser, complex_openapi_3):
        """Test parsing complex OpenAPI 3.0 spec"""
        spec = parser.parse(complex_openapi_3)

        assert spec.title == "Pet Store API"
        assert spec.version == "2.0.0"
        assert len(spec.endpoints) == 2  # GET and POST /pets/{petId}
        assert len(spec.schemas) == 1  # Pet schema
        assert "Pet" in spec.schemas
        assert len(spec.security_schemes) == 1
        assert "api_key" in spec.security_schemes

        # Check GET endpoint
        get_endpoint = spec.get_endpoint("GET", "/pets/{petId}")
        assert get_endpoint is not None
        assert get_endpoint.operation_id == "getPetById"
        assert "pets" in get_endpoint.tags
        assert len(get_endpoint.parameters) == 1

        # Check parameter
        param = get_endpoint.parameters[0]
        assert param.name == "petId"
        assert param.location == "path"
        assert param.required is True
        assert param.type == "integer"

        # Check responses
        assert 200 in get_endpoint.responses
        assert 404 in get_endpoint.responses

        # Check POST endpoint
        post_endpoint = spec.get_endpoint("POST", "/pets/{petId}")
        assert post_endpoint is not None
        assert post_endpoint.request_body is not None
        assert post_endpoint.request_body.required is True

    def test_parse_swagger_2(self, parser, swagger_2_spec):
        """Test parsing Swagger 2.0 spec"""
        spec = parser.parse(swagger_2_spec)

        assert spec.title == "Swagger API"
        assert len(spec.servers) == 1
        assert spec.servers[0].url == "https://api.example.com/v1"

        # Check endpoint
        endpoint = spec.get_endpoint("GET", "/products")
        assert endpoint is not None
        assert len(endpoint.parameters) == 1

        # Check query parameter
        param = endpoint.parameters[0]
        assert param.name == "limit"
        assert param.location == "query"
        assert param.type == "integer"

        # Check security
        assert "basicAuth" in spec.security_schemes

    def test_parse_json_string(self, parser, simple_openapi_3):
        """Test parsing JSON string"""
        json_str = json.dumps(simple_openapi_3)
        spec = parser.parse(json_str)

        assert spec.title == "Simple API"
        assert len(spec.endpoints) == 1

    def test_parse_with_source_file(self, parser, simple_openapi_3):
        """Test parsing with source file tracking"""
        spec = parser.parse(simple_openapi_3, source_file="test.yaml")

        assert spec.source_file == "test.yaml"
        assert spec.source_format == "OpenAPI 3.0.0"

    def test_parse_invalid_json(self, parser):
        """Test parsing invalid JSON raises error"""
        with pytest.raises(ParsingError, match="Invalid JSON"):
            parser.parse("{invalid json")

    def test_parse_non_openapi_content(self, parser):
        """Test parsing non-OpenAPI content raises error"""
        with pytest.raises(ParsingError, match="not valid OpenAPI"):
            parser.parse({"random": "object"})

    def test_get_all_methods(self, parser, complex_openapi_3):
        """Test extracting all HTTP methods"""
        spec = parser.parse(complex_openapi_3)

        methods = spec.get_all_methods()
        assert "GET" in methods
        assert "POST" in methods

    def test_get_endpoints_by_tag(self, parser, complex_openapi_3):
        """Test filtering endpoints by tag"""
        spec = parser.parse(complex_openapi_3)

        pet_endpoints = spec.get_endpoints_by_tag("pets")
        assert len(pet_endpoints) == 2
        assert all("pets" in e.tags for e in pet_endpoints)

    def test_statistics(self, parser, complex_openapi_3):
        """Test API statistics generation"""
        spec = parser.parse(complex_openapi_3)

        stats = spec.get_statistics()
        assert stats['total_endpoints'] == 2
        assert stats['total_schemas'] == 1
        assert 'GET' in stats['endpoints_by_method']
        assert 'POST' in stats['endpoints_by_method']

    def test_security_scheme_parsing(self, parser, complex_openapi_3):
        """Test security scheme parsing"""
        spec = parser.parse(complex_openapi_3)

        api_key = spec.get_security_scheme("api_key")
        assert api_key is not None
        assert api_key.type == "apiKey"
        assert api_key.name == "X-API-Key"
        assert api_key.location == "header"

    def test_schema_parsing(self, parser, complex_openapi_3):
        """Test schema parsing"""
        spec = parser.parse(complex_openapi_3)

        pet_schema = spec.get_schema("Pet")
        assert pet_schema is not None
        assert pet_schema.type == "object"
        assert "name" in pet_schema.required
        assert "name" in pet_schema.properties
        assert "status" in pet_schema.properties

        # Check property details
        status_prop = pet_schema.properties["status"]
        assert status_prop.type == "string"
        assert status_prop.enum == ["available", "pending", "sold"]

    def test_response_success_filtering(self, parser, complex_openapi_3):
        """Test filtering success responses"""
        spec = parser.parse(complex_openapi_3)

        endpoint = spec.get_endpoint("GET", "/pets/{petId}")
        success_responses = endpoint.get_success_responses()

        assert 200 in success_responses
        assert 404 not in success_responses  # 4xx is error

    def test_response_error_filtering(self, parser, complex_openapi_3):
        """Test filtering error responses"""
        spec = parser.parse(complex_openapi_3)

        endpoint = spec.get_endpoint("GET", "/pets/{petId}")
        error_responses = endpoint.get_error_responses()

        assert 404 in error_responses
        assert 200 not in error_responses  # 2xx is success

    def test_parameter_filtering(self, parser, complex_openapi_3):
        """Test parameter filtering methods"""
        spec = parser.parse(complex_openapi_3)

        endpoint = spec.get_endpoint("GET", "/pets/{petId}")

        # Path parameters
        path_params = endpoint.get_path_parameters()
        assert len(path_params) == 1
        assert path_params[0].name == "petId"

        # Required parameters
        required_params = endpoint.get_required_parameters()
        assert len(required_params) == 1
        assert required_params[0].required is True

    def test_export_to_openapi(self, parser, simple_openapi_3):
        """Test exporting back to OpenAPI format"""
        spec = parser.parse(simple_openapi_3)

        openapi_output = spec.to_openapi()

        assert 'openapi' in openapi_output
        assert openapi_output['info']['title'] == "Simple API"
        assert 'paths' in openapi_output
        assert '/users' in openapi_output['paths']
        assert 'get' in openapi_output['paths']['/users']
