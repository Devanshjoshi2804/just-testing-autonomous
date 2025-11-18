"""
OpenAPI/Swagger Parser
Supports OpenAPI 3.x and Swagger 2.0
"""
import json
from typing import Dict, Any, List, Optional, Union

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from loguru import logger

from src.ingestion.parsers.base import BaseParser, ParsingError
from src.ingestion.models import (
    UnifiedAPISpec,
    EndpointSpec,
    ParameterSpec,
    ResponseSpec,
    SchemaSpec,
    SchemaProperty,
    SecuritySchemeSpec,
    ServerSpec,
    RequestBodySpec,
    HTTPMethod,
    ParameterLocation,
    DataType,
    AuthType
)


class OpenAPIParser(BaseParser):
    """
    OpenAPI/Swagger parser
    Supports OpenAPI 3.0, 3.1, and Swagger 2.0
    """

    def __init__(self):
        """Initialize OpenAPI parser"""
        super().__init__()
        self.supported_formats = ['openapi', 'swagger']

    def can_parse(self, content: Union[str, Dict[str, Any]]) -> bool:
        """Check if content is OpenAPI/Swagger format"""
        try:
            # Parse if string
            if isinstance(content, str):
                content = self._parse_content(content)

            # Check for OpenAPI/Swagger indicators
            if isinstance(content, dict):
                return (
                    'openapi' in content or
                    'swagger' in content or
                    ('info' in content and 'paths' in content)
                )

            return False

        except Exception:
            return False

    def parse(
        self,
        content: Union[str, Dict[str, Any]],
        source_file: Optional[str] = None,
        **kwargs
    ) -> UnifiedAPISpec:
        """
        Parse OpenAPI/Swagger documentation

        Args:
            content: OpenAPI spec (JSON string, YAML string, or dict)
            source_file: Optional source file path
            **kwargs: Additional arguments

        Returns:
            UnifiedAPISpec instance

        Raises:
            ParsingError: If parsing fails
        """
        try:
            # Parse content if string
            if isinstance(content, str):
                spec = self._parse_content(content)
            else:
                spec = content

            # Validate it's OpenAPI/Swagger
            if not self.can_parse(spec):
                raise ParsingError("Content is not valid OpenAPI/Swagger format")

            # Determine version
            version = self._get_version(spec)
            logger.info(f"Parsing {version} specification")

            # Extract components
            info = spec.get('info', {})
            paths = spec.get('paths', {})
            components = spec.get('components', {}) or spec.get('definitions', {})

            # Parse basic info
            title = info.get('title', 'Untitled API')
            api_version = info.get('version', '1.0.0')
            description = info.get('description')
            contact = info.get('contact')
            license_info = info.get('license')
            terms = info.get('termsOfService')

            # Parse servers
            servers = self._parse_servers(spec)

            # Parse security schemes
            security_schemes = self._parse_security_schemes(spec)

            # Parse schemas/definitions
            schemas = self._parse_schemas(components)

            # Parse endpoints
            endpoints = self._parse_paths(paths, spec)

            # Parse global security
            global_security = spec.get('security', [])

            # Parse tags
            tags = spec.get('tags', [])

            # Build unified spec
            unified_spec = UnifiedAPISpec(
                title=title,
                version=api_version,
                description=description,
                terms_of_service=terms,
                contact=contact,
                license=license_info,
                servers=servers,
                endpoints=endpoints,
                schemas=schemas,
                security_schemes=security_schemes,
                security=global_security,
                tags=tags,
                source_format=version,
                source_file=source_file
            )

            logger.info(
                f"Parsed {len(endpoints)} endpoints, "
                f"{len(schemas)} schemas, "
                f"{len(security_schemes)} security schemes"
            )

            return unified_spec

        except Exception as e:
            logger.error(f"OpenAPI parsing failed: {e}")
            raise ParsingError(f"Failed to parse OpenAPI spec: {e}")

    def _parse_content(self, content: str) -> Dict[str, Any]:
        """Parse JSON or YAML content"""
        content = content.strip()

        # Try JSON first
        if content.startswith('{'):
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                raise ParsingError(f"Invalid JSON: {e}")

        # Try YAML
        if YAML_AVAILABLE:
            try:
                return yaml.safe_load(content)
            except yaml.YAMLError as e:
                raise ParsingError(f"Invalid YAML: {e}")
        else:
            raise ParsingError("YAML support not available. Install PyYAML.")

    def _get_version(self, spec: Dict[str, Any]) -> str:
        """Get OpenAPI/Swagger version"""
        if 'openapi' in spec:
            return f"OpenAPI {spec['openapi']}"
        elif 'swagger' in spec:
            return f"Swagger {spec['swagger']}"
        else:
            return "Unknown"

    def _parse_servers(self, spec: Dict[str, Any]) -> List[ServerSpec]:
        """Parse server specifications"""
        servers = []

        # OpenAPI 3.x servers
        if 'servers' in spec:
            for server in spec['servers']:
                servers.append(ServerSpec(
                    url=server.get('url', ''),
                    description=server.get('description'),
                    variables=server.get('variables', {})
                ))

        # Swagger 2.0 host/basePath
        elif 'host' in spec:
            scheme = spec.get('schemes', ['https'])[0]
            host = spec['host']
            base_path = spec.get('basePath', '')
            url = f"{scheme}://{host}{base_path}"
            servers.append(ServerSpec(url=url))

        return servers

    def _parse_security_schemes(
        self,
        spec: Dict[str, Any]
    ) -> Dict[str, SecuritySchemeSpec]:
        """Parse security scheme definitions"""
        schemes = {}

        # OpenAPI 3.x
        components = spec.get('components', {})
        if 'securitySchemes' in components:
            for name, scheme in components['securitySchemes'].items():
                schemes[name] = self._parse_security_scheme(scheme)

        # Swagger 2.0
        elif 'securityDefinitions' in spec:
            for name, scheme in spec['securityDefinitions'].items():
                schemes[name] = self._parse_security_scheme(scheme)

        return schemes

    def _parse_security_scheme(self, scheme: Dict[str, Any]) -> SecuritySchemeSpec:
        """Parse single security scheme"""
        scheme_type = scheme.get('type', 'apiKey')

        # Map OpenAPI types to our AuthType
        type_mapping = {
            'apiKey': AuthType.API_KEY,
            'http': AuthType.HTTP_BEARER if scheme.get('scheme') == 'bearer' else AuthType.HTTP_BASIC,
            'oauth2': AuthType.OAUTH2,
            'openIdConnect': AuthType.OPENID_CONNECT
        }

        auth_type = type_mapping.get(scheme_type, AuthType.API_KEY)

        # Parse location for API key
        location = None
        if scheme.get('in'):
            location_mapping = {
                'query': ParameterLocation.QUERY,
                'header': ParameterLocation.HEADER,
                'cookie': ParameterLocation.COOKIE
            }
            location = location_mapping.get(scheme['in'])

        return SecuritySchemeSpec(
            type=auth_type,
            name=scheme.get('name'),
            location=location,
            scheme=scheme.get('scheme'),
            bearer_format=scheme.get('bearerFormat'),
            flows=scheme.get('flows'),
            openid_connect_url=scheme.get('openIdConnectUrl'),
            description=scheme.get('description')
        )

    def _parse_schemas(self, components: Dict[str, Any]) -> Dict[str, SchemaSpec]:
        """Parse schema/component definitions"""
        schemas = {}

        # OpenAPI 3.x components/schemas
        if isinstance(components, dict) and 'schemas' in components:
            for name, schema in components['schemas'].items():
                schemas[name] = self._parse_schema(schema)

        # Swagger 2.0 definitions (components is actually definitions)
        elif isinstance(components, dict):
            for name, schema in components.items():
                if isinstance(schema, dict):
                    schemas[name] = self._parse_schema(schema)

        return schemas

    def _parse_schema(self, schema: Dict[str, Any]) -> SchemaSpec:
        """Parse single schema definition"""
        schema_type = schema.get('type', 'object')

        # Map OpenAPI types to our DataType
        type_mapping = {
            'string': DataType.STRING,
            'number': DataType.NUMBER,
            'integer': DataType.INTEGER,
            'boolean': DataType.BOOLEAN,
            'array': DataType.ARRAY,
            'object': DataType.OBJECT
        }

        data_type = type_mapping.get(schema_type, DataType.OBJECT)

        # Parse properties
        properties = {}
        if 'properties' in schema:
            for prop_name, prop_schema in schema['properties'].items():
                properties[prop_name] = self._parse_property(prop_name, prop_schema)

        # Parse items for arrays
        items = None
        if data_type == DataType.ARRAY and 'items' in schema:
            items = self._parse_schema(schema['items'])

        return SchemaSpec(
            type=data_type,
            description=schema.get('description'),
            properties=properties,
            required=schema.get('required', []),
            items=items,
            title=schema.get('title'),
            example=schema.get('example'),
            examples=schema.get('examples')
        )

    def _parse_property(self, name: str, prop: Dict[str, Any]) -> SchemaProperty:
        """Parse schema property"""
        prop_type = prop.get('type', 'string')

        type_mapping = {
            'string': DataType.STRING,
            'number': DataType.NUMBER,
            'integer': DataType.INTEGER,
            'boolean': DataType.BOOLEAN,
            'array': DataType.ARRAY,
            'object': DataType.OBJECT
        }

        data_type = type_mapping.get(prop_type, DataType.STRING)

        return SchemaProperty(
            name=name,
            type=data_type,
            description=prop.get('description'),
            default=prop.get('default'),
            min_length=prop.get('minLength'),
            max_length=prop.get('maxLength'),
            pattern=prop.get('pattern'),
            minimum=prop.get('minimum'),
            maximum=prop.get('maximum'),
            enum=prop.get('enum'),
            format=prop.get('format'),
            example=prop.get('example'),
            examples=prop.get('examples')
        )

    def _parse_paths(
        self,
        paths: Dict[str, Any],
        spec: Dict[str, Any]
    ) -> List[EndpointSpec]:
        """Parse all paths/endpoints"""
        endpoints = []

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            # Parse each HTTP method
            for method in ['get', 'post', 'put', 'delete', 'patch', 'head', 'options', 'trace']:
                if method in path_item:
                    operation = path_item[method]
                    endpoint = self._parse_operation(
                        method=method,
                        path=path,
                        operation=operation,
                        spec=spec
                    )
                    endpoints.append(endpoint)

        return endpoints

    def _parse_operation(
        self,
        method: str,
        path: str,
        operation: Dict[str, Any],
        spec: Dict[str, Any]
    ) -> EndpointSpec:
        """Parse single operation/endpoint"""
        # Parse parameters
        parameters = []
        if 'parameters' in operation:
            for param in operation['parameters']:
                parameters.append(self._parse_parameter(param))

        # Parse request body (OpenAPI 3.x)
        request_body = None
        if 'requestBody' in operation:
            request_body = self._parse_request_body(operation['requestBody'])

        # Parse responses
        responses = {}
        if 'responses' in operation:
            for code, response in operation['responses'].items():
                try:
                    status_code = int(code) if code != 'default' else 200
                    responses[status_code] = self._parse_response(response)
                except ValueError:
                    continue

        # Parse security
        security = operation.get('security', [])

        return EndpointSpec(
            method=HTTPMethod[method.upper()],
            path=path,
            operation_id=operation.get('operationId'),
            summary=operation.get('summary'),
            description=operation.get('description'),
            tags=operation.get('tags', []),
            parameters=parameters,
            request_body=request_body,
            responses=responses,
            security=security,
            deprecated=operation.get('deprecated', False)
        )

    def _parse_parameter(self, param: Dict[str, Any]) -> ParameterSpec:
        """Parse parameter specification"""
        # Location mapping
        location_mapping = {
            'path': ParameterLocation.PATH,
            'query': ParameterLocation.QUERY,
            'header': ParameterLocation.HEADER,
            'cookie': ParameterLocation.COOKIE,
            'body': ParameterLocation.BODY
        }

        location = location_mapping.get(param.get('in', 'query'), ParameterLocation.QUERY)

        # Parse schema
        schema = None
        if 'schema' in param:
            schema = self._parse_schema(param['schema'])

        # Get type from schema or directly
        param_type = None
        if schema:
            param_type = DataType(schema.type)
        elif 'type' in param:
            type_mapping = {
                'string': DataType.STRING,
                'number': DataType.NUMBER,
                'integer': DataType.INTEGER,
                'boolean': DataType.BOOLEAN,
                'array': DataType.ARRAY
            }
            param_type = type_mapping.get(param['type'], DataType.STRING)

        return ParameterSpec(
            name=param['name'],
            location=location,
            description=param.get('description'),
            required=param.get('required', False),
            deprecated=param.get('deprecated', False),
            schema=schema,
            type=param_type,
            default=param.get('default'),
            enum=param.get('enum'),
            pattern=param.get('pattern'),
            example=param.get('example'),
            examples=param.get('examples')
        )

    def _parse_request_body(self, body: Dict[str, Any]) -> RequestBodySpec:
        """Parse request body specification"""
        # Get first content type (usually application/json)
        content = body.get('content', {})
        content_type = list(content.keys())[0] if content else 'application/json'

        schema = None
        examples = None

        if content_type in content:
            media_type = content[content_type]
            if 'schema' in media_type:
                schema = self._parse_schema(media_type['schema'])
            examples = media_type.get('examples')

        return RequestBodySpec(
            description=body.get('description'),
            required=body.get('required', False),
            content_type=content_type,
            schema=schema,
            examples=examples
        )

    def _parse_response(self, response: Dict[str, Any]) -> ResponseSpec:
        """Parse response specification"""
        # Get schema from content (OpenAPI 3.x) or directly (Swagger 2.0)
        schema = None
        content_type = 'application/json'

        if 'content' in response:
            content = response['content']
            content_type = list(content.keys())[0] if content else 'application/json'
            if content_type in content and 'schema' in content[content_type]:
                schema = self._parse_schema(content[content_type]['schema'])
        elif 'schema' in response:
            schema = self._parse_schema(response['schema'])

        # Parse headers
        headers = {}
        if 'headers' in response:
            for name, header in response['headers'].items():
                headers[name] = ParameterSpec(
                    name=name,
                    location=ParameterLocation.HEADER,
                    description=header.get('description'),
                    schema=self._parse_schema(header.get('schema', {})) if 'schema' in header else None
                )

        return ResponseSpec(
            status_code=200,  # Will be set by caller
            description=response.get('description', 'Response'),
            schema=schema,
            headers=headers,
            content_type=content_type,
            examples=response.get('examples')
        )
