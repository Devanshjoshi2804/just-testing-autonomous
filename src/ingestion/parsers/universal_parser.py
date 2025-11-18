"""
Universal Parser
Automatically detects format and routes to appropriate parser
"""
import json
from typing import Dict, Any, List, Optional, Union, Literal
from pathlib import Path

from loguru import logger

from src.ingestion.parsers.base import BaseParser, ParsingError, FormatNotSupportedError
from src.ingestion.parsers.openapi_parser import OpenAPIParser
from src.ingestion.parsers.postman_parser import PostmanParser
from src.ingestion.parsers.text_parser import TextParser
from src.ingestion.models import UnifiedAPISpec


def detect_format(content: Union[str, Dict[str, Any]]) -> str:
    """
    Detect API documentation format

    Args:
        content: Content to analyze (string or dict)

    Returns:
        Format name: 'openapi', 'postman', 'text', or 'unknown'
    """
    try:
        # Parse if string
        parsed = content
        if isinstance(content, str):
            content_str = content.strip()

            # Try JSON
            if content_str.startswith('{'):
                try:
                    parsed = json.loads(content_str)
                except json.JSONDecodeError:
                    pass

            # If still string, check for YAML indicators
            if isinstance(parsed, str):
                if 'openapi:' in content_str or 'swagger:' in content_str:
                    return 'openapi'
                elif 'info:' in content_str and 'paths:' in content_str:
                    return 'openapi'
                else:
                    return 'text'

        # Check parsed dict
        if isinstance(parsed, dict):
            # Check for OpenAPI/Swagger
            if 'openapi' in parsed or 'swagger' in parsed:
                return 'openapi'
            elif 'info' in parsed and 'paths' in parsed:
                return 'openapi'

            # Check for Postman
            elif '_postman_id' in parsed.get('info', {}):
                return 'postman'
            elif 'item' in parsed and isinstance(parsed['item'], list):
                return 'postman'

        return 'unknown'

    except Exception as e:
        logger.warning(f"Format detection failed: {e}")
        return 'unknown'


class UniversalParser:
    """
    Universal API documentation parser
    Automatically detects format and uses appropriate parser
    """

    def __init__(self):
        """Initialize universal parser with all specific parsers"""
        self.parsers: List[BaseParser] = [
            OpenAPIParser(),
            PostmanParser(),
            # TextParser is async-only, handle separately
        ]
        self.text_parser = TextParser()

        logger.info(f"Initialized UniversalParser with {len(self.parsers)} parsers")

    def detect_format(
        self,
        content: Union[str, Dict[str, Any]]
    ) -> str:
        """
        Detect format using registered parsers

        Args:
            content: Content to analyze

        Returns:
            Format name
        """
        # Try each parser's can_parse method
        for parser in self.parsers:
            if parser.can_parse(content):
                return parser.supported_formats[0]

        # Check text parser
        if self.text_parser.can_parse(content):
            return 'text'

        return 'unknown'

    def parse(
        self,
        content: Union[str, Dict[str, Any]],
        source_file: Optional[str] = None,
        format_hint: Optional[str] = None,
        **kwargs
    ) -> UnifiedAPISpec:
        """
        Parse API documentation (synchronous version)

        Args:
            content: Content to parse (string or dict)
            source_file: Optional source file path
            format_hint: Optional format hint ('openapi', 'postman', 'text')
            **kwargs: Additional parser-specific arguments

        Returns:
            UnifiedAPISpec instance

        Raises:
            FormatNotSupportedError: If format cannot be determined
            ParsingError: If parsing fails
        """
        logger.info("Parsing API documentation")

        # If format hint provided, try that parser first
        if format_hint:
            logger.info(f"Using format hint: {format_hint}")
            parser = self._get_parser(format_hint)
            if parser:
                try:
                    return parser.parse(content, source_file, **kwargs)
                except Exception as e:
                    logger.warning(f"Hinted parser failed: {e}, trying auto-detection")

        # Auto-detect format
        detected_format = self.detect_format(content)
        logger.info(f"Detected format: {detected_format}")

        if detected_format == 'unknown':
            # Try each parser
            for parser in self.parsers:
                try:
                    if parser.can_parse(content):
                        logger.info(f"Trying {parser.name}")
                        return parser.parse(content, source_file, **kwargs)
                except Exception as e:
                    logger.warning(f"{parser.name} failed: {e}")
                    continue

            raise FormatNotSupportedError(
                "Could not detect format. Supported: OpenAPI, Postman, text"
            )

        # Get appropriate parser
        parser = self._get_parser(detected_format)
        if not parser:
            raise FormatNotSupportedError(f"No parser for format: {detected_format}")

        # Parse
        try:
            return parser.parse(content, source_file, **kwargs)
        except Exception as e:
            logger.error(f"Parsing failed with {parser.name}: {e}")
            raise ParsingError(f"Parsing failed: {e}")

    async def parse_async(
        self,
        content: Union[str, Dict[str, Any]],
        source_file: Optional[str] = None,
        format_hint: Optional[str] = None,
        use_ai_fallback: bool = True,
        **kwargs
    ) -> UnifiedAPISpec:
        """
        Parse API documentation (async version with AI fallback)

        Args:
            content: Content to parse
            source_file: Optional source file path
            format_hint: Optional format hint
            use_ai_fallback: Whether to use AI text parser as fallback
            **kwargs: Additional parser-specific arguments

        Returns:
            UnifiedAPISpec instance

        Raises:
            FormatNotSupportedError: If format cannot be determined
            ParsingError: If parsing fails
        """
        logger.info("Parsing API documentation (async)")

        # Try synchronous parsers first
        try:
            return self.parse(content, source_file, format_hint, **kwargs)
        except (FormatNotSupportedError, ParsingError) as e:
            if not use_ai_fallback:
                raise

            logger.info("Synchronous parsers failed, trying AI text parser")

            # Fall back to AI text parser
            if isinstance(content, str):
                try:
                    return await self.text_parser.parse(
                        content,
                        source_file,
                        **kwargs
                    )
                except Exception as ai_error:
                    logger.error(f"AI parser also failed: {ai_error}")
                    raise ParsingError(
                        f"All parsers failed. Last error: {ai_error}"
                    )
            else:
                raise ParsingError(
                    "AI parser requires string content. "
                    "Convert dict to JSON string first."
                )

    def parse_file(
        self,
        file_path: Union[str, Path],
        format_hint: Optional[str] = None,
        **kwargs
    ) -> UnifiedAPISpec:
        """
        Parse API documentation from file

        Args:
            file_path: Path to file
            format_hint: Optional format hint
            **kwargs: Additional parser-specific arguments

        Returns:
            UnifiedAPISpec instance

        Raises:
            FileNotFoundError: If file doesn't exist
            ParsingError: If parsing fails
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info(f"Parsing file: {file_path}")

        # Auto-detect format from extension if no hint
        if not format_hint:
            ext = file_path.suffix.lower()
            format_hint = self._format_from_extension(ext)
            if format_hint:
                logger.info(f"Format hint from extension: {format_hint}")

        # Read file
        content = file_path.read_text(encoding='utf-8')

        # Parse
        return self.parse(
            content=content,
            source_file=str(file_path),
            format_hint=format_hint,
            **kwargs
        )

    async def parse_file_async(
        self,
        file_path: Union[str, Path],
        format_hint: Optional[str] = None,
        use_ai_fallback: bool = True,
        **kwargs
    ) -> UnifiedAPISpec:
        """
        Parse API documentation from file (async with AI fallback)

        Args:
            file_path: Path to file
            format_hint: Optional format hint
            use_ai_fallback: Whether to use AI parser as fallback
            **kwargs: Additional parser-specific arguments

        Returns:
            UnifiedAPISpec instance
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info(f"Parsing file: {file_path} (async)")

        # Auto-detect format from extension
        if not format_hint:
            ext = file_path.suffix.lower()
            format_hint = self._format_from_extension(ext)

        # Read file
        content = file_path.read_text(encoding='utf-8')

        # Parse
        return await self.parse_async(
            content=content,
            source_file=str(file_path),
            format_hint=format_hint,
            use_ai_fallback=use_ai_fallback,
            **kwargs
        )

    def _get_parser(self, format_name: str) -> Optional[BaseParser]:
        """Get parser by format name"""
        for parser in self.parsers:
            if format_name in parser.supported_formats:
                return parser
        return None

    def _format_from_extension(self, ext: str) -> Optional[str]:
        """Determine format from file extension"""
        ext_map = {
            '.json': 'openapi',  # Could be OpenAPI or Postman
            '.yaml': 'openapi',
            '.yml': 'openapi',
            '.txt': 'text',
            '.md': 'text',
            '.pdf': 'text',
            '.doc': 'text',
            '.docx': 'text'
        }
        return ext_map.get(ext)

    def get_supported_formats(self) -> List[str]:
        """Get list of all supported formats"""
        formats = []
        for parser in self.parsers:
            formats.extend(parser.supported_formats)
        formats.extend(self.text_parser.supported_formats)
        return sorted(list(set(formats)))

    def __repr__(self) -> str:
        return f"UniversalParser(parsers={len(self.parsers)}, formats={self.get_supported_formats()})"
