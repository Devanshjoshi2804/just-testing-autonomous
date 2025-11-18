"""
API Documentation Parsers
Universal parsers supporting multiple formats
"""
from src.ingestion.parsers.base import (
    BaseParser,
    ParserError,
    ParsingError,
    FormatNotSupportedError
)
from src.ingestion.parsers.openapi_parser import OpenAPIParser
from src.ingestion.parsers.postman_parser import PostmanParser
from src.ingestion.parsers.text_parser import TextParser
from src.ingestion.parsers.universal_parser import UniversalParser, detect_format

__all__ = [
    # Base
    'BaseParser',
    'ParserError',
    'ParsingError',
    'FormatNotSupportedError',

    # Specific parsers
    'OpenAPIParser',
    'PostmanParser',
    'TextParser',

    # Universal parser
    'UniversalParser',
    'detect_format'
]
