"""
Postman Collection Parser
Supports Postman Collection Format v2.0 and v2.1
"""
import json
from typing import Dict, Any, List, Optional, Union
from urllib.parse import urlparse, parse_qs

from loguru import logger

from src.ingestion.parsers.base import BaseParser, ParsingError
from src.ingestion.models import (
    UnifiedAPISpec,
    EndpointSpec,
    ParameterSpec,
    ResponseSpec,
    SchemaSpec,
    SchemaProperty,
    ServerSpec,
    RequestBodySpec,
    SecuritySchemeSpec,
    HTTPMethod,
    ParameterLocation,
    DataType,
    AuthType
)


class PostmanParser(BaseParser):
    """
    Postman Collection parser
    Supports Collection Format v2.0 and v2.1
    """

    def __init__(self):
        """Initialize Postman parser"""
        super().__init__()
        self.supported_formats = ['postman', 'postman_collection']

    def can_parse(self, content: Union[str, Dict[str, Any]]) -> bool:
        """Check if content is Postman collection format"""
        try:
            # Parse if string
            if isinstance(content, str):
                try:
                    content = json.loads(content)
                except json.JSONDecodeError:
                    return False

            # Check for Postman indicators
            if isinstance(content, dict):
                return (
                    'info' in content and
                    '_postman_id' in content.get('info', {})
                ) or (
                    'item' in content and
                    isinstance(content['item'], list)
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
        Parse Postman collection

        Args:
            content: Postman collection (JSON string or dict)
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
                collection = json.loads(content)
            else:
                collection = content

            # Validate it's Postman format
            if not self.can_parse(collection):
                raise ParsingError("Content is not valid Postman collection format")

            # Extract info
            info = collection.get('info', {})
            title = info.get('name', 'Untitled Collection')
            version = info.get('version', '1.0.0')
            description = info.get('description')

            logger.info(f"Parsing Postman collection: {title}")

            # Parse variables (for base URL)
            variables = collection.get('variable', [])
            base_url = self._extract_base_url(variables)

            # Parse auth
            auth = collection.get('auth')
            security_schemes = {}
            global_security = []

            if auth:
                security_schemes['default'] = self._parse_auth(auth)
                global_security = [{'default': []}]

            # Parse items (requests/folders)
            endpoints = []
            items = collection.get('item', [])
            self._parse_items(items, endpoints, base_url)

            # Build server spec
            servers = []
            if base_url:
                servers.append(ServerSpec(url=base_url))

            # Build unified spec
            unified_spec = UnifiedAPISpec(
                title=title,
                version=version,
                description=description,
                base_url=base_url,
                servers=servers,
                endpoints=endpoints,
                security_schemes=security_schemes,
                security=global_security,
                source_format='postman',
                source_file=source_file
            )

            logger.info(f"Parsed {len(endpoints)} endpoints from Postman collection")

            return unified_spec

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in Postman collection: {e}")
            raise ParsingError(f"Invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Postman parsing failed: {e}")
            raise ParsingError(f"Failed to parse Postman collection: {e}")

    def _extract_base_url(self, variables: List[Dict[str, Any]]) -> Optional[str]:
        """Extract base URL from variables"""
        for var in variables:
            if var.get('key') in ['baseUrl', 'base_url', 'host', 'url']:
                return var.get('value')
        return None

    def _parse_items(
        self,
        items: List[Dict[str, Any]],
        endpoints: List[EndpointSpec],
        base_url: Optional[str] = None,
        parent_path: str = ""
    ):
        """Recursively parse items (requests and folders)"""
        for item in items:
            # If it's a folder, recurse
            if 'item' in item:
                folder_name = item.get('name', '')
                # Use folder name as tag
                self._parse_items(
                    item['item'],
                    endpoints,
                    base_url,
                    parent_path
                )
            # If it's a request
            elif 'request' in item:
                endpoint = self._parse_request(item, base_url)
                if endpoint:
                    # Add folder name as tag if exists
                    if parent_path:
                        endpoint.tags.append(parent_path)
                    endpoints.append(endpoint)

    def _parse_request(
        self,
        item: Dict[str, Any],
        base_url: Optional[str] = None
    ) -> Optional[EndpointSpec]:
        """Parse single request item"""
        try:
            request = item.get('request', {})

            # Handle string format (simple) or dict format (detailed)
            if isinstance(request, str):
                # Simple format: just a URL
                method = HTTPMethod.GET
                url = request
            else:
                # Detailed format
                method_str = request.get('method', 'GET').upper()
                try:
                    method = HTTPMethod[method_str]
                except KeyError:
                    logger.warning(f"Unknown HTTP method: {method_str}, using GET")
                    method = HTTPMethod.GET

                url_obj = request.get('url', {})
                if isinstance(url_obj, str):
                    url = url_obj
                else:
                    # URL object with protocol, host, path, query
                    protocol = url_obj.get('protocol', 'https')
                    host = url_obj.get('host', [])
                    if isinstance(host, list):
                        host = '.'.join(host)
                    path = url_obj.get('path', [])
                    if isinstance(path, list):
                        path = '/' + '/'.join(path)
                    elif isinstance(path, str):
                        path = path if path.startswith('/') else f'/{path}'
                    else:
                        path = '/'

                    url = f"{protocol}://{host}{path}"

            # Extract path from URL
            parsed_url = urlparse(url)
            path = parsed_url.path or '/'

            # Parse parameters
            parameters = []

            # Query parameters from URL
            if parsed_url.query:
                query_params = parse_qs(parsed_url.query)
                for key, values in query_params.items():
                    parameters.append(ParameterSpec(
                        name=key,
                        location=ParameterLocation.QUERY,
                        type=DataType.STRING,
                        example=values[0] if values else None
                    ))

            # Parameters from Postman format
            if isinstance(request, dict):
                url_obj = request.get('url', {})
                if isinstance(url_obj, dict) and 'query' in url_obj:
                    for param in url_obj['query']:
                        if param.get('disabled', False):
                            continue
                        parameters.append(ParameterSpec(
                            name=param['key'],
                            location=ParameterLocation.QUERY,
                            description=param.get('description'),
                            type=DataType.STRING,
                            default=param.get('value')
                        ))

                # Header parameters
                if 'header' in request:
                    for header in request['header']:
                        if header.get('disabled', False):
                            continue
                        # Skip standard headers
                        if header['key'].lower() in ['content-type', 'accept', 'authorization']:
                            continue
                        parameters.append(ParameterSpec(
                            name=header['key'],
                            location=ParameterLocation.HEADER,
                            description=header.get('description'),
                            type=DataType.STRING,
                            default=header.get('value')
                        ))

            # Parse request body
            request_body = None
            if isinstance(request, dict) and 'body' in request:
                request_body = self._parse_request_body(request['body'])

            # Parse responses (examples)
            responses = {}
            if 'response' in item:
                for idx, response in enumerate(item['response']):
                    response_spec = self._parse_response(response)
                    if response_spec:
                        responses[response_spec.status_code] = response_spec

            # Default response if none
            if not responses:
                responses[200] = ResponseSpec(
                    status_code=200,
                    description='Success'
                )

            # Create endpoint
            endpoint = EndpointSpec(
                method=method,
                path=path,
                operation_id=item.get('name'),
                summary=item.get('name'),
                description=request.get('description') if isinstance(request, dict) else None,
                parameters=parameters,
                request_body=request_body,
                responses=responses,
                tags=[]
            )

            return endpoint

        except Exception as e:
            logger.warning(f"Failed to parse request '{item.get('name')}': {e}")
            return None

    def _parse_request_body(self, body: Dict[str, Any]) -> Optional[RequestBodySpec]:
        """Parse request body"""
        mode = body.get('mode', 'raw')

        content_type = 'application/json'
        schema = None

        if mode == 'raw':
            raw_data = body.get('raw', '')
            # Try to infer content type
            options = body.get('options', {})
            if 'raw' in options and 'language' in options['raw']:
                lang = options['raw']['language']
                if lang == 'json':
                    content_type = 'application/json'
                elif lang == 'xml':
                    content_type = 'application/xml'
                elif lang == 'html':
                    content_type = 'text/html'

            # Try to parse JSON schema
            if content_type == 'application/json' and raw_data:
                try:
                    data = json.loads(raw_data)
                    schema = self._infer_schema_from_example(data)
                except json.JSONDecodeError:
                    pass

        elif mode == 'formdata':
            content_type = 'multipart/form-data'
            # Parse form fields into schema
            properties = {}
            for field in body.get('formdata', []):
                if field.get('disabled', False):
                    continue
                properties[field['key']] = SchemaProperty(
                    name=field['key'],
                    type=DataType.STRING,
                    description=field.get('description')
                )
            if properties:
                schema = SchemaSpec(
                    type=DataType.OBJECT,
                    properties=properties
                )

        elif mode == 'urlencoded':
            content_type = 'application/x-www-form-urlencoded'
            properties = {}
            for field in body.get('urlencoded', []):
                if field.get('disabled', False):
                    continue
                properties[field['key']] = SchemaProperty(
                    name=field['key'],
                    type=DataType.STRING,
                    description=field.get('description')
                )
            if properties:
                schema = SchemaSpec(
                    type=DataType.OBJECT,
                    properties=properties
                )

        return RequestBodySpec(
            content_type=content_type,
            schema=schema,
            required=True
        )

    def _parse_response(self, response: Dict[str, Any]) -> Optional[ResponseSpec]:
        """Parse response example"""
        try:
            # Get status code
            code = response.get('code', 200)

            # Get body
            body = response.get('body', '')
            schema = None

            # Try to infer schema from response body
            if body:
                try:
                    data = json.loads(body)
                    schema = self._infer_schema_from_example(data)
                except json.JSONDecodeError:
                    pass

            return ResponseSpec(
                status_code=code,
                description=response.get('name', f'Response {code}'),
                schema=schema,
                content_type='application/json'
            )

        except Exception as e:
            logger.warning(f"Failed to parse response: {e}")
            return None

    def _infer_schema_from_example(self, data: Any) -> SchemaSpec:
        """Infer schema from example data"""
        if isinstance(data, dict):
            properties = {}
            for key, value in data.items():
                prop_type = self._infer_type(value)
                properties[key] = SchemaProperty(
                    name=key,
                    type=prop_type,
                    example=value
                )

            return SchemaSpec(
                type=DataType.OBJECT,
                properties=properties
            )

        elif isinstance(data, list):
            # Infer items schema from first element
            items = None
            if data:
                items = self._infer_schema_from_example(data[0])

            return SchemaSpec(
                type=DataType.ARRAY,
                items=items
            )

        else:
            return SchemaSpec(
                type=self._infer_type(data)
            )

    def _infer_type(self, value: Any) -> DataType:
        """Infer data type from value"""
        if isinstance(value, bool):
            return DataType.BOOLEAN
        elif isinstance(value, int):
            return DataType.INTEGER
        elif isinstance(value, float):
            return DataType.NUMBER
        elif isinstance(value, str):
            return DataType.STRING
        elif isinstance(value, list):
            return DataType.ARRAY
        elif isinstance(value, dict):
            return DataType.OBJECT
        else:
            return DataType.STRING

    def _parse_auth(self, auth: Dict[str, Any]) -> SecuritySchemeSpec:
        """Parse authentication scheme"""
        auth_type = auth.get('type', 'noauth')

        if auth_type == 'apikey':
            return SecuritySchemeSpec(
                type=AuthType.API_KEY,
                name=auth.get('apikey', [{}])[0].get('key'),
                location=ParameterLocation.HEADER
            )

        elif auth_type == 'bearer':
            return SecuritySchemeSpec(
                type=AuthType.HTTP_BEARER,
                scheme='bearer'
            )

        elif auth_type == 'basic':
            return SecuritySchemeSpec(
                type=AuthType.HTTP_BASIC,
                scheme='basic'
            )

        elif auth_type == 'oauth2':
            return SecuritySchemeSpec(
                type=AuthType.OAUTH2
            )

        else:
            return SecuritySchemeSpec(
                type=AuthType.NONE
            )
