"""
Enhanced Document Parser with Comprehensive Error Handling and Validation
Every edge case, validation, and detail is handled
"""
import os
import sys
import json
import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
from enum import Enum
from datetime import datetime
import re

from loguru import logger

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.exceptions import (
    DocumentProcessingError,
    DocumentParseError,
    InvalidDocumentFormat,
    DocumentValidationError,
)


class DocumentType(str, Enum):
    """Supported document types with validation"""
    PDF = "pdf"
    JSON = "json"
    YAML = "yaml"
    YML = "yml"
    TEXT = "txt"
    MARKDOWN = "md"


class FileValidation:
    """File validation utilities with detailed checks"""

    # File size limits (in bytes)
    MIN_FILE_SIZE = 100  # 100 bytes minimum
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB maximum

    # Magic bytes for file type validation
    MAGIC_BYTES = {
        "pdf": b"%PDF",
        "json": [b"{", b"["],  # JSON starts with { or [
        "yaml": [b"---", b"#"],  # YAML often starts with --- or #
    }

    @staticmethod
    def validate_file_exists(file_path: Path) -> None:
        """
        Validate file exists with detailed error

        Args:
            file_path: Path to validate

        Raises:
            FileNotFoundError: With detailed message
        """
        if not file_path.exists():
            raise FileNotFoundError(
                f"File not found: {file_path}\n"
                f"Current directory: {Path.cwd()}\n"
                f"Absolute path checked: {file_path.absolute()}"
            )

    @staticmethod
    def validate_file_readable(file_path: Path) -> None:
        """
        Validate file is readable

        Args:
            file_path: Path to validate

        Raises:
            PermissionError: If file not readable
        """
        if not os.access(file_path, os.R_OK):
            raise PermissionError(
                f"File is not readable: {file_path}\n"
                f"Check file permissions: {oct(file_path.stat().st_mode)}"
            )

    @staticmethod
    def validate_file_size(file_path: Path) -> Tuple[int, str]:
        """
        Validate file size is within limits

        Args:
            file_path: Path to validate

        Returns:
            Tuple of (size_bytes, size_human_readable)

        Raises:
            ValueError: If file size invalid
        """
        size = file_path.stat().st_size

        # Check minimum size
        if size < FileValidation.MIN_FILE_SIZE:
            raise ValueError(
                f"File too small: {size} bytes\n"
                f"Minimum size: {FileValidation.MIN_FILE_SIZE} bytes\n"
                f"File may be empty or corrupted"
            )

        # Check maximum size
        if size > FileValidation.MAX_FILE_SIZE:
            max_mb = FileValidation.MAX_FILE_SIZE / (1024 * 1024)
            actual_mb = size / (1024 * 1024)
            raise ValueError(
                f"File too large: {actual_mb:.2f} MB\n"
                f"Maximum size: {max_mb:.2f} MB\n"
                f"Consider splitting into smaller files"
            )

        # Human-readable size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                size_human = f"{size:.2f} {unit}"
                break
            size = size / 1024.0
        else:
            size_human = f"{size:.2f} TB"

        return file_path.stat().st_size, size_human

    @staticmethod
    def validate_file_type(file_path: Path, expected_type: str) -> bool:
        """
        Validate file type using magic bytes (more reliable than extension)

        Args:
            file_path: Path to validate
            expected_type: Expected file type (pdf, json, yaml)

        Returns:
            True if file type matches
        """
        try:
            with open(file_path, 'rb') as f:
                header = f.read(512)  # Read first 512 bytes

            # Check magic bytes
            magic = FileValidation.MAGIC_BYTES.get(expected_type)
            if magic:
                if isinstance(magic, list):
                    return any(header.startswith(m) for m in magic)
                else:
                    return header.startswith(magic)

            # No magic bytes defined, rely on extension
            return True

        except Exception as e:
            logger.warning(f"Could not validate file type via magic bytes: {e}")
            return True  # Fallback to extension-based check

    @staticmethod
    def calculate_file_hash(file_path: Path) -> str:
        """
        Calculate SHA256 hash of file for caching/deduplication

        Args:
            file_path: Path to file

        Returns:
            Hex string of SHA256 hash
        """
        sha256 = hashlib.sha256()

        with open(file_path, 'rb') as f:
            # Read in chunks for memory efficiency
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)

        return sha256.hexdigest()

    @staticmethod
    def detect_encoding(file_path: Path) -> str:
        """
        Detect file encoding

        Args:
            file_path: Path to file

        Returns:
            Detected encoding (utf-8, latin-1, etc.)
        """
        try:
            import chardet

            with open(file_path, 'rb') as f:
                raw_data = f.read(10000)  # Read first 10KB

            result = chardet.detect(raw_data)
            encoding = result['encoding']
            confidence = result['confidence']

            logger.debug(
                f"Detected encoding: {encoding} "
                f"(confidence: {confidence:.2%})"
            )

            return encoding or 'utf-8'

        except ImportError:
            logger.warning("chardet not available, defaulting to utf-8")
            return 'utf-8'
        except Exception as e:
            logger.warning(f"Encoding detection failed: {e}, defaulting to utf-8")
            return 'utf-8'


class EnhancedDocumentParser:
    """
    Enhanced document parser with comprehensive validation and error handling

    Features:
    - File validation (existence, size, permissions, type)
    - Multiple parser fallbacks
    - Detailed error messages
    - Progress tracking for large files
    - Caching support
    - Metadata extraction
    - Encoding detection
    - Hash calculation for deduplication
    """

    def __init__(self, enable_cache: bool = False, cache_dir: Optional[Path] = None):
        """
        Initialize enhanced document parser

        Args:
            enable_cache: Enable caching of parsed results
            cache_dir: Directory for cache (default: ./cache/documents)
        """
        self.supported_types = [e.value for e in DocumentType]
        self.enable_cache = enable_cache
        self.cache_dir = cache_dir or Path("./cache/documents")

        if self.enable_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Document caching enabled: {self.cache_dir}")

    def parse(
        self,
        file_path: Union[str, Path],
        validate_api_doc: bool = True,
        extract_metadata: bool = True,
    ) -> Dict[str, Any]:
        """
        Parse document with comprehensive validation

        Args:
            file_path: Path to document file
            validate_api_doc: Validate if document contains API documentation
            extract_metadata: Extract detailed metadata

        Returns:
            Dict with:
                - raw_text: Full extracted text
                - plain_text: Plain text version
                - metadata: Detailed document metadata
                - doc_type: Document type
                - structured_data: Parsed structure (for JSON/YAML)
                - file_hash: SHA256 hash
                - validation: Validation results

        Raises:
            DocumentProcessingError: Base error for all parsing issues
            FileNotFoundError: File doesn't exist
            PermissionError: File not readable
            ValueError: Invalid file (size, type, etc.)
            DocumentParseError: Parsing failed
        """
        # Convert to Path
        file_path = Path(file_path)

        logger.info(f"=" * 80)
        logger.info(f"Starting document parsing: {file_path.name}")
        logger.info(f"=" * 80)

        try:
            # Step 1: Comprehensive file validation
            logger.info("Step 1/6: Validating file...")
            self._validate_file(file_path)

            # Step 2: Extract file information
            logger.info("Step 2/6: Extracting file information...")
            file_info = self._extract_file_info(file_path)
            logger.info(
                f"File: {file_info['name']}, "
                f"Size: {file_info['size_human']}, "
                f"Type: {file_info['extension'].upper()}"
            )

            # Step 3: Check cache
            if self.enable_cache:
                logger.info("Step 3/6: Checking cache...")
                cached_result = self._check_cache(file_info['hash'])
                if cached_result:
                    logger.info("✅ Found in cache, returning cached result")
                    return cached_result
            else:
                logger.info("Step 3/6: Cache disabled, skipping...")

            # Step 4: Parse document
            logger.info(f"Step 4/6: Parsing {file_info['extension'].upper()} document...")
            parsed_data = self._parse_by_type(file_path, file_info)

            # Step 5: Validate API documentation
            if validate_api_doc:
                logger.info("Step 5/6: Validating API documentation...")
                validation_result = self._validate_api_documentation(parsed_data)
                parsed_data['validation'] = validation_result

                if not validation_result['is_api_doc']:
                    logger.warning(
                        f"⚠️  Document may not be API documentation "
                        f"(confidence: {validation_result['confidence']:.1%})"
                    )
            else:
                logger.info("Step 5/6: API validation skipped")
                parsed_data['validation'] = {'skipped': True}

            # Step 6: Extract metadata
            if extract_metadata:
                logger.info("Step 6/6: Extracting metadata...")
                parsed_data['metadata'].update(self._extract_detailed_metadata(parsed_data))
            else:
                logger.info("Step 6/6: Metadata extraction skipped")

            # Add file hash for deduplication
            parsed_data['file_hash'] = file_info['hash']

            # Cache result
            if self.enable_cache:
                self._cache_result(file_info['hash'], parsed_data)

            logger.info(f"✅ Document parsing complete!")
            logger.info(
                f"Extracted {len(parsed_data['raw_text'])} characters, "
                f"{len(parsed_data['raw_text'].split())} words"
            )
            logger.info(f"=" * 80)

            return parsed_data

        except (FileNotFoundError, PermissionError, ValueError) as e:
            # Re-raise validation errors as-is
            logger.error(f"Validation error: {e}")
            raise

        except Exception as e:
            # Wrap other errors in DocumentProcessingError
            logger.exception(f"Unexpected error parsing document: {e}")
            raise DocumentProcessingError(
                message=f"Failed to parse document: {file_path.name}",
                details={
                    "file_path": str(file_path),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                original_error=e
            ) from e

    def _validate_file(self, file_path: Path) -> None:
        """
        Comprehensive file validation

        Args:
            file_path: Path to validate

        Raises:
            Various validation errors
        """
        # Check existence
        FileValidation.validate_file_exists(file_path)

        # Check readability
        FileValidation.validate_file_readable(file_path)

        # Check size
        size_bytes, size_human = FileValidation.validate_file_size(file_path)
        logger.debug(f"File size: {size_human} ({size_bytes:,} bytes)")

        # Check extension
        ext = file_path.suffix.lower().lstrip('.')
        if ext not in self.supported_types:
            raise InvalidDocumentFormat(
                message=f"Unsupported file type: .{ext}",
                details={
                    "file_name": file_path.name,
                    "extension": ext,
                    "supported_types": self.supported_types,
                }
            )

        # Validate file type via magic bytes
        if not FileValidation.validate_file_type(file_path, ext):
            logger.warning(
                f"File extension .{ext} doesn't match file content "
                f"(magic bytes check failed)"
            )

    def _extract_file_info(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract comprehensive file information

        Args:
            file_path: Path to file

        Returns:
            Dict with file information
        """
        stat = file_path.stat()

        # File size
        size_bytes = stat.st_size
        size_human = self._format_size(size_bytes)

        # File hash
        file_hash = FileValidation.calculate_file_hash(file_path)

        # MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))

        # Extension
        extension = file_path.suffix.lower().lstrip('.')

        # Timestamps
        created_at = datetime.fromtimestamp(stat.st_ctime)
        modified_at = datetime.fromtimestamp(stat.st_mtime)

        return {
            "name": file_path.name,
            "path": str(file_path.absolute()),
            "extension": extension,
            "size_bytes": size_bytes,
            "size_human": size_human,
            "hash": file_hash,
            "mime_type": mime_type,
            "created_at": created_at.isoformat(),
            "modified_at": modified_at.isoformat(),
        }

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format bytes to human-readable size"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    def _check_cache(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Check if parsed result exists in cache"""
        cache_file = self.cache_dir / f"{file_hash}.json"

        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)

                logger.debug(f"Cache hit: {file_hash[:16]}...")
                return cached_data

            except Exception as e:
                logger.warning(f"Cache read failed: {e}")
                return None

        logger.debug(f"Cache miss: {file_hash[:16]}...")
        return None

    def _cache_result(self, file_hash: str, data: Dict[str, Any]) -> None:
        """Cache parsed result"""
        cache_file = self.cache_dir / f"{file_hash}.json"

        try:
            # Add cache metadata
            data['cache_metadata'] = {
                "cached_at": datetime.now().isoformat(),
                "cache_version": "1.0",
            }

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)

            logger.debug(f"Cached result: {file_hash[:16]}...")

        except Exception as e:
            logger.warning(f"Cache write failed: {e}")

    def _parse_by_type(self, file_path: Path, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route to appropriate parser based on file type

        Args:
            file_path: Path to file
            file_info: File information dict

        Returns:
            Parsed document data
        """
        ext = file_info['extension']

        parsers = {
            DocumentType.PDF: self._parse_pdf,
            DocumentType.JSON: self._parse_json,
            DocumentType.YAML: self._parse_yaml,
            DocumentType.YML: self._parse_yaml,
            DocumentType.TEXT: self._parse_text,
            DocumentType.MARKDOWN: self._parse_text,
        }

        parser = parsers.get(ext)
        if not parser:
            raise ValueError(f"No parser available for: {ext}")

        try:
            return parser(file_path, file_info)
        except Exception as e:
            raise DocumentParseError(
                message=f"Failed to parse {ext.upper()} document",
                details={
                    "file_name": file_path.name,
                    "parser": parser.__name__,
                    "error": str(e),
                },
                original_error=e
            ) from e

    def _parse_pdf(self, file_path: Path, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse PDF with multiple fallback options

        Priority:
        1. PyMuPDF4LLM (best structure preservation)
        2. PyMuPDF (fallback)
        3. PyPDF2 (last resort)
        """
        # Try PyMuPDF4LLM first
        try:
            from pymupdf4llm import to_markdown
            import pymupdf

            logger.debug("Using PyMuPDF4LLM for structure-preserving parsing")

            # Convert to markdown
            md_text = to_markdown(str(file_path))

            # Also get plain text
            doc = pymupdf.open(str(file_path))
            plain_text = "\n\n".join([page.get_text() for page in doc])
            page_count = len(doc)
            doc.close()

            return {
                "raw_text": md_text,
                "plain_text": plain_text,
                "metadata": {
                    **file_info,
                    "parser": "pymupdf4llm",
                    "num_pages": page_count,
                    "has_structure": True,
                },
                "doc_type": DocumentType.PDF,
                "structured_data": None,
            }

        except ImportError:
            logger.debug("PyMuPDF4LLM not available, trying PyMuPDF")

        except Exception as e:
            logger.warning(f"PyMuPDF4LLM failed: {e}, trying fallback")

        # Fallback to PyPDF
        try:
            from pypdf import PdfReader

            logger.debug("Using PyPDF fallback")

            reader = PdfReader(str(file_path))
            page_count = len(reader.pages)

            # Extract text from all pages with progress
            text_parts = []
            for page_num, page in enumerate(reader.pages, 1):
                if page_num % 10 == 0:
                    logger.debug(f"Processing page {page_num}/{page_count}...")

                text = page.extract_text()
                text_parts.append(f"--- Page {page_num} ---\n{text}")

            full_text = "\n\n".join(text_parts)

            return {
                "raw_text": full_text,
                "plain_text": full_text,
                "metadata": {
                    **file_info,
                    "parser": "pypdf",
                    "num_pages": page_count,
                    "has_structure": False,
                },
                "doc_type": DocumentType.PDF,
                "structured_data": None,
            }

        except ImportError:
            raise ImportError(
                "No PDF parser available. Install with:\n"
                "  pip install pymupdf4llm pymupdf\n"
                "  or\n"
                "  pip install pypdf"
            )

    def _parse_json(self, file_path: Path, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """Parse JSON with validation"""
        try:
            # Detect encoding
            encoding = FileValidation.detect_encoding(file_path)

            with open(file_path, 'r', encoding=encoding) as f:
                data = json.load(f)

            # Validate JSON structure
            if not isinstance(data, (dict, list)):
                raise ValueError("JSON must be object or array")

            # Format text
            formatted_text = json.dumps(data, indent=2, ensure_ascii=False)

            return {
                "raw_text": formatted_text,
                "plain_text": formatted_text,
                "metadata": {
                    **file_info,
                    "parser": "json",
                    "encoding": encoding,
                    "json_type": "object" if isinstance(data, dict) else "array",
                    "json_size": len(data),
                },
                "doc_type": DocumentType.JSON,
                "structured_data": data,
            }

        except json.JSONDecodeError as e:
            raise DocumentParseError(
                message="Invalid JSON format",
                details={
                    "file_name": file_path.name,
                    "line": e.lineno,
                    "column": e.colno,
                    "error": e.msg,
                }
            ) from e

    def _parse_yaml(self, file_path: Path, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """Parse YAML with validation"""
        try:
            import yaml

            # Detect encoding
            encoding = FileValidation.detect_encoding(file_path)

            with open(file_path, 'r', encoding=encoding) as f:
                data = yaml.safe_load(f)

            # Format as YAML and JSON
            yaml_text = yaml.dump(data, default_flow_style=False, sort_keys=False)
            json_text = json.dumps(data, indent=2, ensure_ascii=False)

            return {
                "raw_text": yaml_text,
                "plain_text": json_text,
                "metadata": {
                    **file_info,
                    "parser": "yaml",
                    "encoding": encoding,
                    "yaml_type": type(data).__name__,
                },
                "doc_type": DocumentType.YAML,
                "structured_data": data,
            }

        except yaml.YAMLError as e:
            raise DocumentParseError(
                message="Invalid YAML format",
                details={
                    "file_name": file_path.name,
                    "error": str(e),
                }
            ) from e

    def _parse_text(self, file_path: Path, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """Parse text file with encoding detection"""
        # Detect encoding
        encoding = FileValidation.detect_encoding(file_path)
        logger.debug(f"Reading text file with encoding: {encoding}")

        try:
            with open(file_path, 'r', encoding=encoding) as f:
                text = f.read()

            # Count lines and words
            lines = text.split('\n')
            words = text.split()

            return {
                "raw_text": text,
                "plain_text": text,
                "metadata": {
                    **file_info,
                    "parser": "text",
                    "encoding": encoding,
                    "line_count": len(lines),
                    "word_count": len(words),
                    "char_count": len(text),
                },
                "doc_type": DocumentType.TEXT,
                "structured_data": None,
            }

        except UnicodeDecodeError as e:
            raise DocumentParseError(
                message=f"Failed to decode text file with {encoding} encoding",
                details={
                    "file_name": file_path.name,
                    "encoding": encoding,
                    "error": str(e),
                }
            ) from e

    def _validate_api_documentation(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive API documentation validation

        Returns:
            Dict with validation results and confidence score
        """
        text = parsed_data.get("raw_text", "").lower()
        structured_data = parsed_data.get("structured_data")

        # API keywords with weights
        keyword_weights = {
            # High confidence keywords
            "openapi": 3,
            "swagger": 3,
            "api": 2,
            "endpoint": 2,
            "rest": 2,

            # Medium confidence keywords
            "request": 1,
            "response": 1,
            "authentication": 1,
            "authorization": 1,

            # HTTP methods (high confidence)
            "post": 1.5,
            "get": 1,
            "put": 1.5,
            "delete": 1.5,
            "patch": 1.5,

            # Protocols
            "http": 1,
            "https": 1,
            "json": 1,
            "xml": 0.5,

            # Auth
            "bearer": 1,
            "token": 1,
            "oauth": 2,
            "jwt": 2,
        }

        # Calculate weighted score
        score = 0
        found_keywords = {}

        for keyword, weight in keyword_weights.items():
            count = text.count(keyword)
            if count > 0:
                found_keywords[keyword] = count
                score += count * weight

        # Check structured data for OpenAPI/Swagger
        is_openapi = False
        if structured_data:
            is_openapi = (
                "openapi" in structured_data or
                "swagger" in structured_data or
                ("paths" in structured_data and "info" in structured_data)
            )

        if is_openapi:
            score += 10  # Big bonus for actual OpenAPI spec

        # Confidence calculation
        max_score = 30  # Approximate maximum
        confidence = min(score / max_score, 1.0)

        is_api_doc = confidence >= 0.3  # 30% threshold

        return {
            "is_api_doc": is_api_doc,
            "confidence": confidence,
            "score": score,
            "found_keywords": found_keywords,
            "is_openapi": is_openapi,
            "keyword_count": len(found_keywords),
        }

    def _extract_detailed_metadata(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract detailed metadata from parsed document

        Returns:
            Dict with extracted metadata
        """
        text = parsed_data.get("raw_text", "")
        structured = parsed_data.get("structured_data")

        metadata = {}

        # Extract title
        metadata['title'] = self._extract_title(text, structured)

        # Extract version
        metadata['version'] = self._extract_version(text, structured)

        # Extract base URL
        metadata['base_url'] = self._extract_base_url(text, structured)

        # Extract description
        metadata['description'] = self._extract_description(text, structured)

        # Count endpoints
        metadata['endpoint_count'] = self._count_endpoints(text, structured)

        return metadata

    def _extract_title(self, text: str, structured: Optional[Dict]) -> Optional[str]:
        """Extract document title"""
        # Check structured data first
        if structured:
            if "info" in structured and "title" in structured["info"]:
                return structured["info"]["title"]

        # Look for title in text
        title_patterns = [
            r'^#\s+(.+)$',  # Markdown h1
            r'^Title:\s*(.+)$',  # "Title: ..."
            r'^API:\s*(.+)$',  # "API: ..."
        ]

        for pattern in title_patterns:
            match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_version(self, text: str, structured: Optional[Dict]) -> Optional[str]:
        """Extract API version"""
        # Check structured data
        if structured:
            if "info" in structured and "version" in structured["info"]:
                return structured["info"]["version"]
            if "swagger" in structured:
                return structured["swagger"]
            if "openapi" in structured:
                return structured["openapi"]

        # Look for version in text
        version_patterns = [
            r'version[:\s]+([0-9]+\.[0-9]+(?:\.[0-9]+)?)',
            r'v([0-9]+\.[0-9]+(?:\.[0-9]+)?)',
        ]

        for pattern in version_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _extract_base_url(self, text: str, structured: Optional[Dict]) -> Optional[str]:
        """Extract base URL"""
        # Check structured data
        if structured:
            # OpenAPI 3.x
            if "servers" in structured and isinstance(structured["servers"], list):
                if structured["servers"] and "url" in structured["servers"][0]:
                    return structured["servers"][0]["url"]

            # Swagger 2.x
            if "host" in structured:
                scheme = structured.get("schemes", ["https"])[0]
                base_path = structured.get("basePath", "")
                return f"{scheme}://{structured['host']}{base_path}"

        # Look for URL in text
        url_patterns = [
            r'https?://[a-zA-Z0-9.-]+(?:/[a-zA-Z0-9._-]*)?',
            r'Base\s+URL[:\s]+([^\s\n]+)',
            r'API\s+URL[:\s]+([^\s\n]+)',
        ]

        for pattern in url_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0]

        return None

    def _extract_description(self, text: str, structured: Optional[Dict]) -> Optional[str]:
        """Extract API description"""
        # Check structured data
        if structured:
            if "info" in structured and "description" in structured["info"]:
                desc = structured["info"]["description"]
                return desc[:500] if len(desc) > 500 else desc

        # Extract from text (first paragraph)
        paragraphs = text.split('\n\n')
        for para in paragraphs:
            para = para.strip()
            if len(para) > 50 and not para.startswith('#'):
                return para[:500]

        return None

    def _count_endpoints(self, text: str, structured: Optional[Dict]) -> int:
        """Estimate number of endpoints"""
        # Check structured data
        if structured and "paths" in structured:
            return len(structured["paths"])

        # Count HTTP method occurrences (rough estimate)
        methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
        count = sum(text.upper().count(method) for method in methods)

        # Divide by 2 as methods might be mentioned multiple times
        return max(1, count // 2)


# Convenience function
def parse_document(
    file_path: Union[str, Path],
    enable_cache: bool = False,
    validate_api: bool = True,
) -> Dict[str, Any]:
    """
    Parse document with all features enabled

    Args:
        file_path: Path to document
        enable_cache: Enable caching
        validate_api: Validate if API documentation

    Returns:
        Parsed document data
    """
    parser = EnhancedDocumentParser(enable_cache=enable_cache)
    return parser.parse(file_path, validate_api_doc=validate_api)
