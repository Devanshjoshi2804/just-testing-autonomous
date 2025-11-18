"""
Unified API Specification Models
Standardized representation of API documentation from any source
"""
from typing import Dict, List, Optional, Any, Literal, Union
from enum import Enum
from pydantic import BaseModel, Field, validator, field_validator, model_validator, HttpUrl
from datetime import datetime


# ============================================================================
# Enums
# ============================================================================

class HTTPMethod(str, Enum):
    """HTTP methods"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    TRACE = "TRACE"


class ParameterLocation(str, Enum):
    """Parameter location"""
    PATH = "path"
    QUERY = "query"
    HEADER = "header"
    COOKIE = "cookie"
    BODY = "body"


class DataType(str, Enum):
    """Data types"""
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    NULL = "null"


class AuthType(str, Enum):
    """Authentication types"""
    NONE = "none"
    API_KEY = "apiKey"
    HTTP_BASIC = "http_basic"
    HTTP_BEARER = "http_bearer"
    OAUTH2 = "oauth2"
    OPENID_CONNECT = "openIdConnect"
    JWT = "jwt"
    CUSTOM = "custom"


# ============================================================================
# Base Models
# ============================================================================

class SchemaProperty(BaseModel):
    """Schema property definition"""
    name: str
    type: DataType
    description: Optional[str] = None
    required: bool = False
    default: Optional[Any] = None

    # Validation constraints
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    enum: Optional[List[Any]] = None
    format: Optional[str] = None  # email, date-time, uri, uuid, etc.

    # Array-specific
    items: Optional['SchemaSpec'] = None
    min_items: Optional[int] = None
    max_items: Optional[int] = None
    unique_items: Optional[bool] = None

    # Object-specific
    properties: Optional[Dict[str, 'SchemaProperty']] = None
    additional_properties: Optional[bool] = True

    # Metadata
    example: Optional[Any] = None
    examples: Optional[List[Any]] = None
    deprecated: bool = False

    class Config:
        use_enum_values = True


class SchemaSpec(BaseModel):
    """Request/Response schema specification"""
    type: DataType
    description: Optional[str] = None
    properties: Dict[str, SchemaProperty] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)
    additional_properties: bool = True

    # For array types
    items: Optional['SchemaSpec'] = None

    # For nested/referenced schemas
    ref: Optional[str] = None  # Reference to another schema
    all_of: Optional[List['SchemaSpec']] = None
    any_of: Optional[List['SchemaSpec']] = None
    one_of: Optional[List['SchemaSpec']] = None

    # Metadata
    title: Optional[str] = None
    example: Optional[Dict[str, Any]] = None
    examples: Optional[List[Dict[str, Any]]] = None

    class Config:
        use_enum_values = True

    def get_required_properties(self) -> List[SchemaProperty]:
        """Get list of required properties"""
        return [
            prop for name, prop in self.properties.items()
            if name in self.required
        ]

    def get_optional_properties(self) -> List[SchemaProperty]:
        """Get list of optional properties"""
        return [
            prop for name, prop in self.properties.items()
            if name not in self.required
        ]


# Update forward references
SchemaProperty.model_rebuild()
SchemaSpec.model_rebuild()


class ParameterSpec(BaseModel):
    """API parameter specification"""
    name: str
    location: ParameterLocation
    description: Optional[str] = None
    required: bool = False
    deprecated: bool = False

    # Schema
    schema: Optional[SchemaSpec] = None
    type: Optional[DataType] = None  # Simplified type if schema not provided

    # Validation
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None
    pattern: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None

    # Examples
    example: Optional[Any] = None
    examples: Optional[Dict[str, Any]] = None

    class Config:
        use_enum_values = True

    @validator('type', always=True)
    def set_type_from_schema(cls, v, values):
        """Set type from schema if not provided"""
        if v is None and 'schema' in values and values['schema']:
            return values['schema'].type
        return v


class ResponseSpec(BaseModel):
    """API response specification"""
    status_code: int
    description: Optional[str] = None
    schema: Optional[SchemaSpec] = None
    headers: Dict[str, ParameterSpec] = Field(default_factory=dict)
    examples: Optional[Dict[str, Any]] = None
    content_type: str = "application/json"

    @validator('status_code')
    def validate_status_code(cls, v):
        """Validate HTTP status code"""
        if not (100 <= v < 600):
            raise ValueError(f"Invalid HTTP status code: {v}")
        return v


class RequestBodySpec(BaseModel):
    """Request body specification"""
    description: Optional[str] = None
    required: bool = False
    content_type: str = "application/json"
    schema: Optional[SchemaSpec] = None
    examples: Optional[Dict[str, Any]] = None


class SecuritySchemeSpec(BaseModel):
    """Security scheme specification"""
    type: AuthType
    name: Optional[str] = None  # For apiKey
    location: Optional[ParameterLocation] = None  # For apiKey
    scheme: Optional[str] = None  # For http (basic, bearer, etc.)
    bearer_format: Optional[str] = None  # For http bearer
    flows: Optional[Dict[str, Any]] = None  # For oauth2
    openid_connect_url: Optional[str] = None  # For openIdConnect
    description: Optional[str] = None

    class Config:
        use_enum_values = True


class ServerSpec(BaseModel):
    """Server specification"""
    url: str
    description: Optional[str] = None
    variables: Dict[str, Any] = Field(default_factory=dict)

    @validator('url')
    def validate_url(cls, v):
        """Validate URL format"""
        if not v:
            raise ValueError("Server URL cannot be empty")
        # Basic validation - can be enhanced
        if not (v.startswith('http://') or v.startswith('https://') or v.startswith('{')):
            # Allow {variables} in URL
            if '{' not in v:
                raise ValueError(f"Invalid server URL: {v}")
        return v


class EndpointSpec(BaseModel):
    """API endpoint specification"""
    method: HTTPMethod
    path: str
    operation_id: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    # Parameters
    parameters: List[ParameterSpec] = Field(default_factory=list)
    request_body: Optional[RequestBodySpec] = None

    # Responses
    responses: Dict[int, ResponseSpec] = Field(default_factory=dict)
    default_response: Optional[ResponseSpec] = None

    # Security
    security: List[Dict[str, List[str]]] = Field(default_factory=list)

    # Metadata
    deprecated: bool = False
    external_docs: Optional[Dict[str, str]] = None
    servers: List[ServerSpec] = Field(default_factory=list)

    class Config:
        use_enum_values = True

    @validator('path')
    def validate_path(cls, v):
        """Validate path format"""
        if not v.startswith('/'):
            v = f'/{v}'
        return v

    def get_path_parameters(self) -> List[ParameterSpec]:
        """Get all path parameters"""
        return [p for p in self.parameters if p.location == ParameterLocation.PATH]

    def get_query_parameters(self) -> List[ParameterSpec]:
        """Get all query parameters"""
        return [p for p in self.parameters if p.location == ParameterLocation.QUERY]

    def get_header_parameters(self) -> List[ParameterSpec]:
        """Get all header parameters"""
        return [p for p in self.parameters if p.location == ParameterLocation.HEADER]

    def get_required_parameters(self) -> List[ParameterSpec]:
        """Get all required parameters"""
        return [p for p in self.parameters if p.required]

    def get_optional_parameters(self) -> List[ParameterSpec]:
        """Get all optional parameters"""
        return [p for p in self.parameters if not p.required]

    def get_success_responses(self) -> Dict[int, ResponseSpec]:
        """Get successful responses (2xx)"""
        return {
            code: response
            for code, response in self.responses.items()
            if 200 <= code < 300
        }

    def get_error_responses(self) -> Dict[int, ResponseSpec]:
        """Get error responses (4xx, 5xx)"""
        return {
            code: response
            for code, response in self.responses.items()
            if code >= 400
        }


class UnifiedAPISpec(BaseModel):
    """
    Unified API Specification
    Standardized representation of any API documentation
    """
    # Basic info
    title: str
    version: str = "1.0.0"
    description: Optional[str] = None
    terms_of_service: Optional[str] = None
    contact: Optional[Dict[str, str]] = None
    license: Optional[Dict[str, str]] = None

    # Servers
    base_url: Optional[str] = None  # Primary base URL
    servers: List[ServerSpec] = Field(default_factory=list)

    # Endpoints
    endpoints: List[EndpointSpec] = Field(default_factory=list)

    # Schemas (components/definitions)
    schemas: Dict[str, SchemaSpec] = Field(default_factory=dict)

    # Security
    security_schemes: Dict[str, SecuritySchemeSpec] = Field(default_factory=dict)
    security: List[Dict[str, List[str]]] = Field(default_factory=list)  # Global security

    # Metadata
    tags: List[Dict[str, str]] = Field(default_factory=list)
    external_docs: Optional[Dict[str, str]] = None

    # Source information
    source_format: Optional[str] = None  # openapi, postman, raml, text, etc.
    source_file: Optional[str] = None
    parsed_at: datetime = Field(default_factory=datetime.now)

    # Additional custom data
    extensions: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode='after')
    def set_base_url_from_servers(self):
        """Set base URL from servers if not provided"""
        if self.base_url is None and self.servers:
            self.base_url = self.servers[0].url
        return self

    @validator('endpoints')
    def validate_unique_endpoints(cls, v):
        """Ensure endpoints are unique by method+path"""
        seen = set()
        for endpoint in v:
            key = (endpoint.method, endpoint.path)
            if key in seen:
                raise ValueError(
                    f"Duplicate endpoint: {endpoint.method} {endpoint.path}"
                )
            seen.add(key)
        return v

    # Query methods
    def get_endpoint(self, method: str, path: str) -> Optional[EndpointSpec]:
        """Get endpoint by method and path"""
        method = method.upper()
        for endpoint in self.endpoints:
            # endpoint.method is already a string due to use_enum_values
            if endpoint.method == method and endpoint.path == path:
                return endpoint
        return None

    def get_endpoints_by_tag(self, tag: str) -> List[EndpointSpec]:
        """Get all endpoints with specific tag"""
        return [e for e in self.endpoints if tag in e.tags]

    def get_endpoints_by_method(self, method: str) -> List[EndpointSpec]:
        """Get all endpoints with specific HTTP method"""
        method = method.upper()
        # e.method is already a string due to use_enum_values
        return [e for e in self.endpoints if e.method == method]

    def get_all_paths(self) -> List[str]:
        """Get all unique paths"""
        return sorted(list(set(e.path for e in self.endpoints)))

    def get_all_tags(self) -> List[str]:
        """Get all unique tags"""
        tags = set()
        for endpoint in self.endpoints:
            tags.update(endpoint.tags)
        return sorted(list(tags))

    def get_all_methods(self) -> List[str]:
        """Get all unique HTTP methods"""
        # e.method is already a string due to use_enum_values
        return sorted(list(set(e.method for e in self.endpoints)))

    def get_schema(self, name: str) -> Optional[SchemaSpec]:
        """Get schema by name"""
        return self.schemas.get(name)

    def get_security_scheme(self, name: str) -> Optional[SecuritySchemeSpec]:
        """Get security scheme by name"""
        return self.security_schemes.get(name)

    # Statistics
    def get_statistics(self) -> Dict[str, Any]:
        """Get API statistics"""
        return {
            'title': self.title,
            'version': self.version,
            'total_endpoints': len(self.endpoints),
            'endpoints_by_method': {
                method: len(self.get_endpoints_by_method(method))
                for method in self.get_all_methods()
            },
            'total_paths': len(self.get_all_paths()),
            'total_schemas': len(self.schemas),
            'total_tags': len(self.get_all_tags()),
            'security_schemes': list(self.security_schemes.keys()),
            'servers': [s.url for s in self.servers],
            'source_format': self.source_format,
            'parsed_at': self.parsed_at.isoformat()
        }

    # Export methods
    def to_openapi(self, version: str = "3.0.0") -> Dict[str, Any]:
        """
        Export to OpenAPI format

        Args:
            version: OpenAPI version (3.0.0 or 3.1.0)

        Returns:
            OpenAPI specification dict
        """
        openapi_spec = {
            'openapi': version,
            'info': {
                'title': self.title,
                'version': self.version
            }
        }

        if self.description:
            openapi_spec['info']['description'] = self.description

        if self.contact:
            openapi_spec['info']['contact'] = self.contact

        if self.license:
            openapi_spec['info']['license'] = self.license

        # Servers
        if self.servers:
            openapi_spec['servers'] = [
                {'url': s.url, 'description': s.description}
                for s in self.servers
            ]

        # Paths (endpoints)
        paths = {}
        for endpoint in self.endpoints:
            path = endpoint.path
            if path not in paths:
                paths[path] = {}

            # endpoint.method is already a string due to use_enum_values
            method = endpoint.method.lower()
            operation = {
                'summary': endpoint.summary,
                'description': endpoint.description,
                'operationId': endpoint.operation_id,
                'tags': endpoint.tags,
                'parameters': [],
                'responses': {}
            }

            # Parameters
            for param in endpoint.parameters:
                # param.location and param.type are already strings due to use_enum_values
                operation['parameters'].append({
                    'name': param.name,
                    'in': param.location,
                    'required': param.required,
                    'description': param.description,
                    'schema': {'type': param.type if param.type else 'string'}
                })

            # Responses
            for code, response in endpoint.responses.items():
                operation['responses'][str(code)] = {
                    'description': response.description or f'Response {code}'
                }

            paths[path][method] = operation

        openapi_spec['paths'] = paths

        # Components
        if self.schemas or self.security_schemes:
            openapi_spec['components'] = {}

            if self.schemas:
                # schema.type is already a string due to use_enum_values
                openapi_spec['components']['schemas'] = {
                    name: {'type': schema.type, 'properties': {}}
                    for name, schema in self.schemas.items()
                }

            if self.security_schemes:
                # scheme.type is already a string due to use_enum_values
                openapi_spec['components']['securitySchemes'] = {
                    name: {'type': scheme.type}
                    for name, scheme in self.security_schemes.items()
                }

        return openapi_spec

    def to_dict(self) -> Dict[str, Any]:
        """Export to dictionary"""
        return self.model_dump(exclude_none=True)

    def to_json(self, **kwargs) -> str:
        """Export to JSON string"""
        return self.model_dump_json(exclude_none=True, **kwargs)

    # Summary methods
    def get_summary(self) -> str:
        """Get human-readable summary"""
        stats = self.get_statistics()

        summary = f"""
API Specification: {self.title} v{self.version}
{'=' * 60}

Endpoints: {stats['total_endpoints']}
  - GET: {stats['endpoints_by_method'].get('GET', 0)}
  - POST: {stats['endpoints_by_method'].get('POST', 0)}
  - PUT: {stats['endpoints_by_method'].get('PUT', 0)}
  - DELETE: {stats['endpoints_by_method'].get('DELETE', 0)}
  - PATCH: {stats['endpoints_by_method'].get('PATCH', 0)}

Paths: {stats['total_paths']}
Schemas: {stats['total_schemas']}
Tags: {stats['total_tags']}

Security: {', '.join(stats['security_schemes']) if stats['security_schemes'] else 'None'}
Servers: {len(stats['servers'])}

Source: {stats['source_format'] or 'Unknown'}
Parsed: {stats['parsed_at']}
"""
        return summary.strip()

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
