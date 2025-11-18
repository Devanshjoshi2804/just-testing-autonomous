"""
Base Parser Interface
All parsers must implement this interface
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Union
from pathlib import Path

from src.ingestion.models import UnifiedAPISpec


class ParserError(Exception):
    """Base exception for parser errors"""
    pass


class FormatNotSupportedError(ParserError):
    """Raised when format is not supported"""
    pass


class ParsingError(ParserError):
    """Raised when parsing fails"""
    pass


class BaseParser(ABC):
    """
    Base parser interface
    All document parsers must implement this interface
    """

    def __init__(self):
        """Initialize parser"""
        self.supported_formats = []

    @abstractmethod
    def parse(
        self,
        content: Union[str, Dict[str, Any]],
        source_file: Optional[str] = None,
        **kwargs
    ) -> UnifiedAPISpec:
        """
        Parse API documentation into UnifiedAPISpec

        Args:
            content: Raw content (string for YAML/JSON/text, dict for parsed JSON)
            source_file: Optional source file path
            **kwargs: Additional parser-specific arguments

        Returns:
            UnifiedAPISpec instance

        Raises:
            ParsingError: If parsing fails
        """
        pass

    @abstractmethod
    def can_parse(self, content: Union[str, Dict[str, Any]]) -> bool:
        """
        Check if this parser can handle the given content

        Args:
            content: Raw content to check

        Returns:
            True if this parser can handle the content
        """
        pass

    def parse_file(self, file_path: Union[str, Path], **kwargs) -> UnifiedAPISpec:
        """
        Parse API documentation from file

        Args:
            file_path: Path to file
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

        # Read file content
        content = file_path.read_text(encoding='utf-8')

        # Parse content
        return self.parse(
            content=content,
            source_file=str(file_path),
            **kwargs
        )

    @property
    def name(self) -> str:
        """Get parser name"""
        return self.__class__.__name__

    def __repr__(self) -> str:
        return f"{self.name}(formats={self.supported_formats})"
