"""
OpenAPI Schema Parser
Extracts and processes schemas from OpenAPI specifications
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

try:
    from loguru import logger
except ImportError:
    class MockLogger:
        def info(self, msg, **kwargs): pass
        def warning(self, msg, **kwargs): pass
        def error(self, msg, **kwargs): pass
        def debug(self, msg, **kwargs): pass
    logger = MockLogger()


@dataclass
class EndpointSchema:
    """Schema for a specific endpoint and method"""
    path: str
    method: str
    request_schema: Optional[Dict[str, Any]] = None
    response_schemas: Dict[int, Dict[str, Any]] = None  # status_code -> schema

    def __post_init__(self):
        if self.response_schemas is None:
            self.response_schemas = {}


class OpenAPISchemaParser:
    """
    Parse OpenAPI specifications and extract schemas

    Supports:
    - OpenAPI 3.0.x
    - Swagger 2.0
    - Response schema extraction by status code
    - Request body schema extraction
    - Schema references ($ref)
    """

    def __init__(self, openapi_spec: Dict[str, Any]):
        """
        Initialize parser with OpenAPI specification

        Args:
            openapi_spec: OpenAPI specification as dict
        """
        self.spec = openapi_spec
        self.version = self._detect_version()
        self.components = self.spec.get('components', {}) or self.spec.get('definitions', {})

        logger.info(f"Initialized OpenAPI parser for version: {self.version}")

    def _detect_version(self) -> str:
        """Detect OpenAPI version"""
        if 'openapi' in self.spec:
            return self.spec['openapi']
        elif 'swagger' in self.spec:
            return self.spec['swagger']
        else:
            return 'unknown'

    def extract_endpoint_schemas(self) -> Dict[str, EndpointSchema]:
        """
        Extract all endpoint schemas from spec

        Returns:
            Dict mapping endpoint_key (METHOD path) to EndpointSchema
        """
        schemas = {}
        paths = self.spec.get('paths', {})

        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.upper() not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                    continue

                endpoint_key = f"{method.upper()} {path}"

                # Extract request schema
                request_schema = self._extract_request_schema(operation)

                # Extract response schemas
                response_schemas = self._extract_response_schemas(operation)

                schemas[endpoint_key] = EndpointSchema(
                    path=path,
                    method=method.upper(),
                    request_schema=request_schema,
                    response_schemas=response_schemas
                )

        logger.info(f"Extracted schemas for {len(schemas)} endpoints")
        return schemas

    def _extract_request_schema(self, operation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract request body schema from operation"""
        # OpenAPI 3.0
        if 'requestBody' in operation:
            request_body = operation['requestBody']
            content = request_body.get('content', {})

            # Try application/json first
            if 'application/json' in content:
                schema = content['application/json'].get('schema', {})
                return self._resolve_schema(schema)

            # Fall back to first content type
            for content_type, content_schema in content.items():
                schema = content_schema.get('schema', {})
                return self._resolve_schema(schema)

        # Swagger 2.0
        if 'parameters' in operation:
            for param in operation['parameters']:
                if param.get('in') == 'body':
                    schema = param.get('schema', {})
                    return self._resolve_schema(schema)

        return None

    def _extract_response_schemas(self, operation: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
        """Extract response schemas by status code"""
        response_schemas = {}
        responses = operation.get('responses', {})

        for status_code, response in responses.items():
            # Convert status code to int
            try:
                status_int = int(status_code)
            except ValueError:
                # Handle 'default', '2XX', etc.
                if status_code == 'default':
                    status_int = 200
                else:
                    continue

            # OpenAPI 3.0
            if 'content' in response:
                content = response['content']

                # Try application/json first
                if 'application/json' in content:
                    schema = content['application/json'].get('schema', {})
                    response_schemas[status_int] = self._resolve_schema(schema)
                else:
                    # Use first content type
                    for content_type, content_schema in content.items():
                        schema = content_schema.get('schema', {})
                        response_schemas[status_int] = self._resolve_schema(schema)
                        break

            # Swagger 2.0
            elif 'schema' in response:
                schema = response['schema']
                response_schemas[status_int] = self._resolve_schema(schema)

        return response_schemas

    def _resolve_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve schema references ($ref)

        Args:
            schema: Schema dict that may contain $ref

        Returns:
            Resolved schema dict
        """
        if not isinstance(schema, dict):
            return schema

        # Handle $ref
        if '$ref' in schema:
            ref_path = schema['$ref']
            resolved = self._resolve_ref(ref_path)

            # Merge other properties with resolved schema
            merged = {**resolved}
            for key, value in schema.items():
                if key != '$ref':
                    merged[key] = value

            return merged

        # Recursively resolve nested schemas
        resolved = {}
        for key, value in schema.items():
            if isinstance(value, dict):
                resolved[key] = self._resolve_schema(value)
            elif isinstance(value, list):
                resolved[key] = [self._resolve_schema(item) if isinstance(item, dict) else item
                                for item in value]
            else:
                resolved[key] = value

        return resolved

    def _resolve_ref(self, ref_path: str) -> Dict[str, Any]:
        """
        Resolve a $ref path

        Args:
            ref_path: Reference path like '#/components/schemas/User'

        Returns:
            Resolved schema dict
        """
        # Remove leading '#/'
        if ref_path.startswith('#/'):
            ref_path = ref_path[2:]

        # Split path
        parts = ref_path.split('/')

        # Navigate spec
        current = self.spec
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                logger.warning(f"Could not resolve reference: {ref_path}")
                return {}

        # Recursively resolve in case resolved schema has more refs
        return self._resolve_schema(current)

    def get_endpoint_schema(self, method: str, path: str) -> Optional[EndpointSchema]:
        """
        Get schema for specific endpoint

        Args:
            method: HTTP method (GET, POST, etc.)
            path: Endpoint path

        Returns:
            EndpointSchema or None if not found
        """
        endpoint_key = f"{method.upper()} {path}"
        schemas = self.extract_endpoint_schemas()
        return schemas.get(endpoint_key)

    def get_response_schema(self, method: str, path: str, status_code: int) -> Optional[Dict[str, Any]]:
        """
        Get response schema for specific endpoint and status code

        Args:
            method: HTTP method
            path: Endpoint path
            status_code: HTTP status code

        Returns:
            Schema dict or None
        """
        endpoint_schema = self.get_endpoint_schema(method, path)
        if not endpoint_schema:
            return None

        return endpoint_schema.response_schemas.get(status_code)

    def list_endpoints(self) -> List[str]:
        """List all endpoint keys in spec"""
        schemas = self.extract_endpoint_schemas()
        return list(schemas.keys())
