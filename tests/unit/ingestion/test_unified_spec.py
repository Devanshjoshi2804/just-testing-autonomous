"""
Unit Tests for Unified API Specification Models
Tests all models, validation, and query methods
"""
import pytest
from datetime import datetime

from src.ingestion.models import (
    HTTPMethod,
    ParameterLocation,
    DataType,
    AuthType,
    SchemaProperty,
    SchemaSpec,
    ParameterSpec,
    ResponseSpec,
    RequestBodySpec,
    SecuritySchemeSpec,
    ServerSpec,
    EndpointSpec,
    UnifiedAPISpec
)


class TestEnums:
    """Test enum definitions"""

    def test_http_methods(self):
        """Test HTTP method enum"""
        assert HTTPMethod.GET.value == "GET"
        assert HTTPMethod.POST.value == "POST"
        assert HTTPMethod.PUT.value == "PUT"
        assert HTTPMethod.DELETE.value == "DELETE"

    def test_parameter_locations(self):
        """Test parameter location enum"""
        assert ParameterLocation.PATH.value == "path"
        assert ParameterLocation.QUERY.value == "query"
        assert ParameterLocation.HEADER.value == "header"
        assert ParameterLocation.BODY.value == "body"

    def test_data_types(self):
        """Test data type enum"""
        assert DataType.STRING.value == "string"
        assert DataType.INTEGER.value == "integer"
        assert DataType.OBJECT.value == "object"
        assert DataType.ARRAY.value == "array"

    def test_auth_types(self):
        """Test authentication type enum"""
        assert AuthType.API_KEY.value == "apiKey"
        assert AuthType.HTTP_BEARER.value == "http_bearer"
        assert AuthType.OAUTH2.value == "oauth2"


class TestSchemaProperty:
    """Test schema property model"""

    def test_basic_property(self):
        """Test basic property creation"""
        prop = SchemaProperty(
            name="username",
            type=DataType.STRING,
            description="User's username",
            required=True
        )

        assert prop.name == "username"
        assert prop.type == DataType.STRING
        assert prop.required is True

    def test_property_with_constraints(self):
        """Test property with validation constraints"""
        prop = SchemaProperty(
            name="age",
            type=DataType.INTEGER,
            minimum=0,
            maximum=150,
            required=True
        )

        assert prop.minimum == 0
        assert prop.maximum == 150

    def test_string_property_with_pattern(self):
        """Test string property with pattern"""
        prop = SchemaProperty(
            name="email",
            type=DataType.STRING,
            format="email",
            pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        )

        assert prop.format == "email"
        assert prop.pattern is not None

    def test_array_property(self):
        """Test array property"""
        item_schema = SchemaSpec(
            type=DataType.STRING
        )

        prop = SchemaProperty(
            name="tags",
            type=DataType.ARRAY,
            items=item_schema,
            min_items=1,
            max_items=10
        )

        assert prop.type == DataType.ARRAY
        assert prop.items is not None
        assert prop.min_items == 1


class TestSchemaSpec:
    """Test schema specification model"""

    def test_simple_schema(self):
        """Test simple object schema"""
        schema = SchemaSpec(
            type=DataType.OBJECT,
            properties={
                'id': SchemaProperty(name='id', type=DataType.INTEGER),
                'name': SchemaProperty(name='name', type=DataType.STRING)
            },
            required=['id', 'name']
        )

        assert schema.type == DataType.OBJECT
        assert len(schema.properties) == 2
        assert 'id' in schema.required

    def test_get_required_properties(self):
        """Test getting required properties"""
        schema = SchemaSpec(
            type=DataType.OBJECT,
            properties={
                'id': SchemaProperty(name='id', type=DataType.INTEGER),
                'name': SchemaProperty(name='name', type=DataType.STRING),
                'email': SchemaProperty(name='email', type=DataType.STRING)
            },
            required=['id', 'name']
        )

        required = schema.get_required_properties()
        assert len(required) == 2
        assert all(p.name in ['id', 'name'] for p in required)

    def test_get_optional_properties(self):
        """Test getting optional properties"""
        schema = SchemaSpec(
            type=DataType.OBJECT,
            properties={
                'id': SchemaProperty(name='id', type=DataType.INTEGER),
                'email': SchemaProperty(name='email', type=DataType.STRING)
            },
            required=['id']
        )

        optional = schema.get_optional_properties()
        assert len(optional) == 1
        assert optional[0].name == 'email'

    def test_nested_schema(self):
        """Test nested object schema"""
        address_schema = SchemaSpec(
            type=DataType.OBJECT,
            properties={
                'street': SchemaProperty(name='street', type=DataType.STRING),
                'city': SchemaProperty(name='city', type=DataType.STRING)
            }
        )

        user_schema = SchemaSpec(
            type=DataType.OBJECT,
            properties={
                'name': SchemaProperty(name='name', type=DataType.STRING),
                'address': SchemaProperty(
                    name='address',
                    type=DataType.OBJECT,
                    properties={
                        'street': SchemaProperty(name='street', type=DataType.STRING),
                        'city': SchemaProperty(name='city', type=DataType.STRING)
                    }
                )
            }
        )

        assert user_schema.properties['address'].type == DataType.OBJECT


class TestParameterSpec:
    """Test parameter specification model"""

    def test_query_parameter(self):
        """Test query parameter"""
        param = ParameterSpec(
            name="page",
            location=ParameterLocation.QUERY,
            type=DataType.INTEGER,
            description="Page number",
            required=False,
            default=1
        )

        assert param.location == ParameterLocation.QUERY
        assert param.required is False
        assert param.default == 1

    def test_path_parameter(self):
        """Test path parameter"""
        param = ParameterSpec(
            name="id",
            location=ParameterLocation.PATH,
            type=DataType.STRING,
            required=True
        )

        assert param.location == ParameterLocation.PATH
        assert param.required is True

    def test_header_parameter(self):
        """Test header parameter"""
        param = ParameterSpec(
            name="Authorization",
            location=ParameterLocation.HEADER,
            type=DataType.STRING,
            required=True
        )

        assert param.location == ParameterLocation.HEADER

    def test_parameter_with_enum(self):
        """Test parameter with enum values"""
        param = ParameterSpec(
            name="status",
            location=ParameterLocation.QUERY,
            type=DataType.STRING,
            enum=["active", "inactive", "pending"]
        )

        assert param.enum is not None
        assert len(param.enum) == 3


class TestResponseSpec:
    """Test response specification model"""

    def test_success_response(self):
        """Test successful response"""
        response = ResponseSpec(
            status_code=200,
            description="Successful response",
            schema=SchemaSpec(
                type=DataType.OBJECT,
                properties={
                    'message': SchemaProperty(name='message', type=DataType.STRING)
                }
            )
        )

        assert response.status_code == 200
        assert response.schema is not None

    def test_error_response(self):
        """Test error response"""
        response = ResponseSpec(
            status_code=404,
            description="Resource not found"
        )

        assert response.status_code == 404

    def test_invalid_status_code(self):
        """Test invalid status code raises error"""
        with pytest.raises(ValueError, match="Invalid HTTP status code"):
            ResponseSpec(status_code=999)

    def test_response_with_headers(self):
        """Test response with headers"""
        response = ResponseSpec(
            status_code=200,
            description="Success",
            headers={
                'X-Rate-Limit': ParameterSpec(
                    name='X-Rate-Limit',
                    location=ParameterLocation.HEADER,
                    type=DataType.INTEGER
                )
            }
        )

        assert 'X-Rate-Limit' in response.headers


class TestEndpointSpec:
    """Test endpoint specification model"""

    def test_basic_endpoint(self):
        """Test basic endpoint creation"""
        endpoint = EndpointSpec(
            method=HTTPMethod.GET,
            path="/users",
            summary="Get all users",
            description="Retrieve a list of all users"
        )

        assert endpoint.method == HTTPMethod.GET
        assert endpoint.path == "/users"

    def test_path_normalization(self):
        """Test path is normalized with leading slash"""
        endpoint = EndpointSpec(
            method=HTTPMethod.GET,
            path="users"  # No leading slash
        )

        assert endpoint.path == "/users"

    def test_endpoint_with_parameters(self):
        """Test endpoint with parameters"""
        endpoint = EndpointSpec(
            method=HTTPMethod.GET,
            path="/users/{id}",
            parameters=[
                ParameterSpec(
                    name="id",
                    location=ParameterLocation.PATH,
                    type=DataType.STRING,
                    required=True
                ),
                ParameterSpec(
                    name="include",
                    location=ParameterLocation.QUERY,
                    type=DataType.STRING,
                    required=False
                )
            ]
        )

        assert len(endpoint.parameters) == 2

    def test_get_path_parameters(self):
        """Test getting path parameters"""
        endpoint = EndpointSpec(
            method=HTTPMethod.GET,
            path="/users/{id}",
            parameters=[
                ParameterSpec(name="id", location=ParameterLocation.PATH, type=DataType.STRING),
                ParameterSpec(name="page", location=ParameterLocation.QUERY, type=DataType.INTEGER)
            ]
        )

        path_params = endpoint.get_path_parameters()
        assert len(path_params) == 1
        assert path_params[0].name == "id"

    def test_get_query_parameters(self):
        """Test getting query parameters"""
        endpoint = EndpointSpec(
            method=HTTPMethod.GET,
            path="/users",
            parameters=[
                ParameterSpec(name="page", location=ParameterLocation.QUERY, type=DataType.INTEGER),
                ParameterSpec(name="limit", location=ParameterLocation.QUERY, type=DataType.INTEGER)
            ]
        )

        query_params = endpoint.get_query_parameters()
        assert len(query_params) == 2

    def test_get_required_parameters(self):
        """Test getting required parameters"""
        endpoint = EndpointSpec(
            method=HTTPMethod.POST,
            path="/users",
            parameters=[
                ParameterSpec(name="name", location=ParameterLocation.BODY, type=DataType.STRING, required=True),
                ParameterSpec(name="email", location=ParameterLocation.BODY, type=DataType.STRING, required=False)
            ]
        )

        required = endpoint.get_required_parameters()
        assert len(required) == 1
        assert required[0].name == "name"

    def test_get_success_responses(self):
        """Test getting successful responses"""
        endpoint = EndpointSpec(
            method=HTTPMethod.GET,
            path="/users",
            responses={
                200: ResponseSpec(status_code=200, description="Success"),
                201: ResponseSpec(status_code=201, description="Created"),
                400: ResponseSpec(status_code=400, description="Bad Request")
            }
        )

        success = endpoint.get_success_responses()
        assert len(success) == 2
        assert 200 in success
        assert 201 in success

    def test_get_error_responses(self):
        """Test getting error responses"""
        endpoint = EndpointSpec(
            method=HTTPMethod.GET,
            path="/users",
            responses={
                200: ResponseSpec(status_code=200, description="Success"),
                404: ResponseSpec(status_code=404, description="Not Found"),
                500: ResponseSpec(status_code=500, description="Server Error")
            }
        )

        errors = endpoint.get_error_responses()
        assert len(errors) == 2
        assert 404 in errors
        assert 500 in errors


class TestServerSpec:
    """Test server specification model"""

    def test_basic_server(self):
        """Test basic server spec"""
        server = ServerSpec(
            url="https://api.example.com",
            description="Production server"
        )

        assert server.url == "https://api.example.com"

    def test_server_with_variables(self):
        """Test server with variables"""
        server = ServerSpec(
            url="https://{environment}.example.com",
            variables={
                'environment': {
                    'default': 'api',
                    'enum': ['api', 'api-dev', 'api-staging']
                }
            }
        )

        assert '{environment}' in server.url
        assert 'environment' in server.variables

    def test_invalid_server_url(self):
        """Test invalid server URL"""
        with pytest.raises(ValueError, match="Invalid server URL"):
            ServerSpec(url="not-a-valid-url")


class TestSecuritySchemeSpec:
    """Test security scheme specification"""

    def test_api_key_scheme(self):
        """Test API key security scheme"""
        scheme = SecuritySchemeSpec(
            type=AuthType.API_KEY,
            name="X-API-Key",
            location=ParameterLocation.HEADER
        )

        assert scheme.type == AuthType.API_KEY
        assert scheme.name == "X-API-Key"

    def test_bearer_scheme(self):
        """Test HTTP bearer scheme"""
        scheme = SecuritySchemeSpec(
            type=AuthType.HTTP_BEARER,
            scheme="bearer",
            bearer_format="JWT"
        )

        assert scheme.type == AuthType.HTTP_BEARER
        assert scheme.bearer_format == "JWT"

    def test_oauth2_scheme(self):
        """Test OAuth2 scheme"""
        scheme = SecuritySchemeSpec(
            type=AuthType.OAUTH2,
            flows={
                'authorizationCode': {
                    'authorizationUrl': 'https://example.com/oauth/authorize',
                    'tokenUrl': 'https://example.com/oauth/token'
                }
            }
        )

        assert scheme.type == AuthType.OAUTH2
        assert 'authorizationCode' in scheme.flows


class TestUnifiedAPISpec:
    """Test unified API specification model"""

    def test_minimal_spec(self):
        """Test minimal API specification"""
        spec = UnifiedAPISpec(
            title="Test API",
            version="1.0.0"
        )

        assert spec.title == "Test API"
        assert spec.version == "1.0.0"
        assert len(spec.endpoints) == 0

    def test_spec_with_endpoints(self):
        """Test spec with endpoints"""
        spec = UnifiedAPISpec(
            title="Test API",
            version="1.0.0",
            endpoints=[
                EndpointSpec(method=HTTPMethod.GET, path="/users"),
                EndpointSpec(method=HTTPMethod.POST, path="/users"),
                EndpointSpec(method=HTTPMethod.GET, path="/users/{id}")
            ]
        )

        assert len(spec.endpoints) == 3

    def test_duplicate_endpoints_rejected(self):
        """Test duplicate endpoints are rejected"""
        with pytest.raises(ValueError, match="Duplicate endpoint"):
            UnifiedAPISpec(
                title="Test API",
                version="1.0.0",
                endpoints=[
                    EndpointSpec(method=HTTPMethod.GET, path="/users"),
                    EndpointSpec(method=HTTPMethod.GET, path="/users")  # Duplicate
                ]
            )

    def test_base_url_from_servers(self):
        """Test base URL set from servers"""
        spec = UnifiedAPISpec(
            title="Test API",
            version="1.0.0",
            servers=[
                ServerSpec(url="https://api.example.com")
            ]
        )

        assert spec.base_url == "https://api.example.com"

    def test_get_endpoint(self):
        """Test getting endpoint by method and path"""
        spec = UnifiedAPISpec(
            title="Test API",
            version="1.0.0",
            endpoints=[
                EndpointSpec(method=HTTPMethod.GET, path="/users"),
                EndpointSpec(method=HTTPMethod.POST, path="/users")
            ]
        )

        endpoint = spec.get_endpoint("GET", "/users")
        assert endpoint is not None
        assert endpoint.method == HTTPMethod.GET

    def test_get_endpoints_by_tag(self):
        """Test getting endpoints by tag"""
        spec = UnifiedAPISpec(
            title="Test API",
            version="1.0.0",
            endpoints=[
                EndpointSpec(method=HTTPMethod.GET, path="/users", tags=["users"]),
                EndpointSpec(method=HTTPMethod.POST, path="/posts", tags=["posts"]),
                EndpointSpec(method=HTTPMethod.GET, path="/users/{id}", tags=["users"])
            ]
        )

        user_endpoints = spec.get_endpoints_by_tag("users")
        assert len(user_endpoints) == 2

    def test_get_endpoints_by_method(self):
        """Test getting endpoints by HTTP method"""
        spec = UnifiedAPISpec(
            title="Test API",
            version="1.0.0",
            endpoints=[
                EndpointSpec(method=HTTPMethod.GET, path="/users"),
                EndpointSpec(method=HTTPMethod.POST, path="/users"),
                EndpointSpec(method=HTTPMethod.GET, path="/posts")
            ]
        )

        get_endpoints = spec.get_endpoints_by_method("GET")
        assert len(get_endpoints) == 2

    def test_get_all_paths(self):
        """Test getting all unique paths"""
        spec = UnifiedAPISpec(
            title="Test API",
            version="1.0.0",
            endpoints=[
                EndpointSpec(method=HTTPMethod.GET, path="/users"),
                EndpointSpec(method=HTTPMethod.POST, path="/users"),
                EndpointSpec(method=HTTPMethod.GET, path="/posts")
            ]
        )

        paths = spec.get_all_paths()
        assert len(paths) == 2
        assert "/users" in paths
        assert "/posts" in paths

    def test_get_all_tags(self):
        """Test getting all unique tags"""
        spec = UnifiedAPISpec(
            title="Test API",
            version="1.0.0",
            endpoints=[
                EndpointSpec(method=HTTPMethod.GET, path="/users", tags=["users", "public"]),
                EndpointSpec(method=HTTPMethod.GET, path="/posts", tags=["posts", "public"])
            ]
        )

        tags = spec.get_all_tags()
        assert len(tags) == 3
        assert "users" in tags
        assert "posts" in tags
        assert "public" in tags

    def test_get_statistics(self):
        """Test getting API statistics"""
        spec = UnifiedAPISpec(
            title="Test API",
            version="1.0.0",
            base_url="https://api.example.com",
            endpoints=[
                EndpointSpec(method=HTTPMethod.GET, path="/users"),
                EndpointSpec(method=HTTPMethod.POST, path="/users"),
                EndpointSpec(method=HTTPMethod.DELETE, path="/users/{id}")
            ]
        )

        stats = spec.get_statistics()
        assert stats['total_endpoints'] == 3
        assert stats['endpoints_by_method']['GET'] == 1
        assert stats['endpoints_by_method']['POST'] == 1

    def test_to_openapi(self):
        """Test export to OpenAPI format"""
        spec = UnifiedAPISpec(
            title="Test API",
            version="1.0.0",
            description="A test API",
            servers=[ServerSpec(url="https://api.example.com")],
            endpoints=[
                EndpointSpec(
                    method=HTTPMethod.GET,
                    path="/users",
                    summary="Get users",
                    operation_id="getUsers",
                    tags=["users"]
                )
            ]
        )

        openapi = spec.to_openapi()

        assert openapi['openapi'] == "3.0.0"
        assert openapi['info']['title'] == "Test API"
        assert '/users' in openapi['paths']
        assert 'get' in openapi['paths']['/users']

    def test_get_summary(self):
        """Test getting human-readable summary"""
        spec = UnifiedAPISpec(
            title="Test API",
            version="1.0.0",
            endpoints=[
                EndpointSpec(method=HTTPMethod.GET, path="/users"),
                EndpointSpec(method=HTTPMethod.POST, path="/users")
            ]
        )

        summary = spec.get_summary()
        assert "Test API" in summary
        assert "v1.0.0" in summary
        assert "Endpoints: 2" in summary
