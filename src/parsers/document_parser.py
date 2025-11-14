"""
Document Parser Module
Handles PDF, JSON, YAML API documentation parsing with structure preservation
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from enum import Enum

from loguru import logger


class DocumentType(str, Enum):
    """Supported document types"""
    PDF = "pdf"
    JSON = "json"
    YAML = "yaml"
    YML = "yml"
    TEXT = "txt"


class DocumentParser:
    """
    Universal document parser for API documentation
    Supports PDF, JSON, YAML with structure preservation
    """

    def __init__(self):
        """Initialize document parser"""
        self.supported_types = [e.value for e in DocumentType]

    def parse(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Parse document and extract structured content

        Args:
            file_path: Path to document file

        Returns:
            Dict with:
                - raw_text: Full extracted text
                - metadata: Document metadata
                - doc_type: Document type
                - structured_data: Parsed structure (for JSON/YAML)

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file type not supported
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Get file extension
        ext = file_path.suffix.lower().lstrip('.')

        if ext not in self.supported_types:
            raise ValueError(
                f"Unsupported file type: {ext}. "
                f"Supported types: {', '.join(self.supported_types)}"
            )

        logger.info(f"Parsing {ext.upper()} document: {file_path.name}")

        # Route to appropriate parser
        if ext == DocumentType.PDF:
            return self._parse_pdf(file_path)
        elif ext == DocumentType.JSON:
            return self._parse_json(file_path)
        elif ext in [DocumentType.YAML, DocumentType.YML]:
            return self._parse_yaml(file_path)
        elif ext == DocumentType.TEXT:
            return self._parse_text(file_path)
        else:
            raise ValueError(f"Unsupported document type: {ext}")

    def _parse_pdf(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse PDF with structure preservation using PyMuPDF4LLM

        Args:
            file_path: Path to PDF file

        Returns:
            Parsed document data
        """
        try:
            # Try PyMuPDF4LLM first (better structure preservation)
            from pymupdf4llm import to_markdown

            logger.info("Using PyMuPDF4LLM for PDF parsing")

            # Convert PDF to markdown (preserves structure)
            md_text = to_markdown(str(file_path))

            # Also extract plain text for fallback
            import pymupdf
            doc = pymupdf.open(str(file_path))
            plain_text = "\n\n".join([page.get_text() for page in doc])
            doc.close()

            return {
                "raw_text": md_text,  # Markdown with structure
                "plain_text": plain_text,  # Plain text fallback
                "metadata": {
                    "file_name": file_path.name,
                    "file_size": file_path.stat().st_size,
                    "parser": "pymupdf4llm",
                },
                "doc_type": DocumentType.PDF,
                "structured_data": None,
            }

        except ImportError:
            logger.warning("PyMuPDF4LLM not available, falling back to PyPDF")

            # Fallback to PyPDF
            try:
                from pypdf import PdfReader

                reader = PdfReader(str(file_path))

                # Extract text from all pages
                text_parts = []
                for page_num, page in enumerate(reader.pages, 1):
                    text = page.extract_text()
                    text_parts.append(f"--- Page {page_num} ---\n{text}")

                full_text = "\n\n".join(text_parts)

                return {
                    "raw_text": full_text,
                    "plain_text": full_text,
                    "metadata": {
                        "file_name": file_path.name,
                        "file_size": file_path.stat().st_size,
                        "num_pages": len(reader.pages),
                        "parser": "pypdf",
                    },
                    "doc_type": DocumentType.PDF,
                    "structured_data": None,
                }

            except ImportError as e:
                raise ImportError(
                    "No PDF parser available. "
                    "Install with: pip install pymupdf4llm or pip install pypdf"
                ) from e

    def _parse_json(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse JSON API documentation

        Args:
            file_path: Path to JSON file

        Returns:
            Parsed document data
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Convert to formatted text
        formatted_text = json.dumps(data, indent=2, ensure_ascii=False)

        return {
            "raw_text": formatted_text,
            "plain_text": formatted_text,
            "metadata": {
                "file_name": file_path.name,
                "file_size": file_path.stat().st_size,
                "parser": "json",
            },
            "doc_type": DocumentType.JSON,
            "structured_data": data,  # Keep original structure
        }

    def _parse_yaml(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse YAML API documentation (OpenAPI, Swagger, etc.)

        Args:
            file_path: Path to YAML file

        Returns:
            Parsed document data
        """
        import yaml

        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # Convert to formatted text
        formatted_text = yaml.dump(data, default_flow_style=False, sort_keys=False)

        # Also create JSON representation
        json_text = json.dumps(data, indent=2, ensure_ascii=False)

        return {
            "raw_text": formatted_text,
            "plain_text": json_text,  # JSON is often easier for LLMs
            "metadata": {
                "file_name": file_path.name,
                "file_size": file_path.stat().st_size,
                "parser": "yaml",
            },
            "doc_type": DocumentType.YAML,
            "structured_data": data,  # Keep original structure
        }

    def _parse_text(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse plain text documentation

        Args:
            file_path: Path to text file

        Returns:
            Parsed document data
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()

        return {
            "raw_text": text,
            "plain_text": text,
            "metadata": {
                "file_name": file_path.name,
                "file_size": file_path.stat().st_size,
                "parser": "text",
            },
            "doc_type": DocumentType.TEXT,
            "structured_data": None,
        }

    def validate_api_doc(self, parsed_data: Dict[str, Any]) -> bool:
        """
        Validate if document contains API documentation

        Args:
            parsed_data: Parsed document data

        Returns:
            True if looks like API documentation
        """
        text = parsed_data.get("raw_text", "").lower()

        # Common API documentation indicators
        api_keywords = [
            "api", "endpoint", "request", "response",
            "post", "get", "put", "delete", "patch",
            "http", "https", "rest", "json",
            "authentication", "authorization", "bearer",
            "swagger", "openapi", "postman"
        ]

        # Count keyword occurrences
        keyword_count = sum(1 for keyword in api_keywords if keyword in text)

        # Consider it API doc if has 3+ keywords
        is_api_doc = keyword_count >= 3

        if is_api_doc:
            logger.info(f"✅ Detected API documentation ({keyword_count} keywords found)")
        else:
            logger.warning(f"⚠️ May not be API documentation ({keyword_count} keywords found)")

        return is_api_doc

    def extract_base_url(self, parsed_data: Dict[str, Any]) -> Optional[str]:
        """
        Try to extract base URL from document

        Args:
            parsed_data: Parsed document data

        Returns:
            Base URL if found, None otherwise
        """
        # Check structured data first (OpenAPI, Swagger)
        if parsed_data.get("structured_data"):
            data = parsed_data["structured_data"]

            # OpenAPI 3.x
            if "servers" in data and isinstance(data["servers"], list):
                if data["servers"] and "url" in data["servers"][0]:
                    url = data["servers"][0]["url"]
                    logger.info(f"Found base URL in OpenAPI servers: {url}")
                    return url

            # Swagger 2.x
            if "host" in data:
                scheme = data.get("schemes", ["https"])[0]
                base_path = data.get("basePath", "")
                url = f"{scheme}://{data['host']}{base_path}"
                logger.info(f"Found base URL in Swagger: {url}")
                return url

        # Try to find URL in text
        import re
        text = parsed_data.get("raw_text", "")

        # Look for common URL patterns
        url_patterns = [
            r'https?://[a-zA-Z0-9.-]+(?:/[a-zA-Z0-9._-]*)?',  # Full URLs
            r'Base URL[:\s]+([^\s\n]+)',  # "Base URL: ..."
            r'API URL[:\s]+([^\s\n]+)',  # "API URL: ..."
        ]

        for pattern in url_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                url = matches[0]
                logger.info(f"Found base URL in text: {url}")
                return url

        logger.warning("Could not extract base URL from document")
        return None
