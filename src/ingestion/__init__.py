"""
API Ingestion Module
Unified parsers and models for API documentation
"""
from src.ingestion.models import (
    # Enums
    HTTPMethod,
    ParameterLocation,
    DataType,
    AuthType,

    # Models
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

from src.ingestion.parsers import (
    # Base
    BaseParser,
    ParserError,
    FormatNotSupportedError,

    # Specific parsers
    OpenAPIParser,
    PostmanParser,
    TextParser,

    # Universal parser
    UniversalParser,
    detect_format
)

__all__ = [
    # Enums
    'HTTPMethod',
    'ParameterLocation',
    'DataType',
    'AuthType',

    # Models
    'SchemaProperty',
    'SchemaSpec',
    'ParameterSpec',
    'ResponseSpec',
    'RequestBodySpec',
    'SecuritySchemeSpec',
    'ServerSpec',
    'EndpointSpec',
    'UnifiedAPISpec',

    # Parsers - Base
    'BaseParser',
    'ParserError',
    'FormatNotSupportedError',

    # Parsers - Specific
    'OpenAPIParser',
    'PostmanParser',
    'TextParser',

    # Parsers - Universal
    'UniversalParser',
    'detect_format'
]
