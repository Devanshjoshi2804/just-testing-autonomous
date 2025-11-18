"""
Pydantic Models and Schemas for API validation
"""
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, validator, field_validator, HttpUrl
from enum import Enum
import re


# ============================================================================
# Enums
# ============================================================================

class TestStatus(str, Enum):
    """Test session status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentType(str, Enum):
    """Supported document types"""
    PDF = "pdf"
    JSON = "json"
    YAML = "yaml"
    YML = "yml"


class TestType(str, Enum):
    """Test variation types"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    BOUNDARY = "boundary"


# ============================================================================
# Validation Helpers
# ============================================================================

def validate_safe_string(value: Optional[str], field_name: str, max_length: int = 500) -> Optional[str]:
    """
    Validate string is safe (no XSS, length limits)

    Args:
        value: String to validate
        field_name: Field name for error messages
        max_length: Maximum allowed length

    Returns:
        Sanitized string or None

    Raises:
        ValueError: If validation fails
    """
    if value is None:
        return None

    # Strip whitespace
    value = value.strip()

    if not value:
        return None

    # Check length
    if len(value) > max_length:
        raise ValueError(
            f"{field_name} exceeds maximum length of {max_length} characters "
            f"(got {len(value)} characters)"
        )

    # Prevent XSS attacks - check for HTML/script tags
    dangerous_patterns = [
        r'<script[^>]*>',
        r'</script>',
        r'javascript:',
        r'onerror\s*=',
        r'onclick\s*=',
        r'onload\s*=',
        r'<iframe',
        r'<object',
        r'<embed',
    ]

    value_lower = value.lower()
    for pattern in dangerous_patterns:
        if re.search(pattern, value_lower, re.IGNORECASE):
            raise ValueError(
                f"{field_name} contains potentially dangerous content. "
                f"HTML tags and JavaScript are not allowed."
            )

    # Prevent null byte injection
    if '\x00' in value:
        raise ValueError(f"{field_name} contains null bytes")

    return value


def validate_document_id(value: str) -> str:
    """
    Validate document ID format

    Document IDs should be in format: doc_<hex_string>

    Args:
        value: Document ID to validate

    Returns:
        Validated document ID

    Raises:
        ValueError: If format is invalid
    """
    if not value:
        raise ValueError("Document ID cannot be empty")

    # Check format: doc_<12-16 hex chars>
    if not re.match(r'^doc_[a-f0-9]{12,16}$', value):
        raise ValueError(
            "Document ID must be in format 'doc_<hex_string>' "
            "(e.g., 'doc_abc123def456')"
        )

    return value


def validate_session_id(value: str) -> str:
    """
    Validate session ID format

    Session IDs should be in format: session_<hex>_<timestamp>

    Args:
        value: Session ID to validate

    Returns:
        Validated session ID

    Raises:
        ValueError: If format is invalid
    """
    if not value:
        raise ValueError("Session ID cannot be empty")

    # Check format: session_<hex>_<timestamp>
    if not re.match(r'^session_[a-f0-9]+_\d+$', value):
        raise ValueError(
            "Session ID must be in format 'session_<hex>_<timestamp>' "
            "(e.g., 'session_abc123def456_1234567890')"
        )

    return value


# ============================================================================
# Request Models
# ============================================================================

class DocumentUploadRequest(BaseModel):
    """Document upload metadata"""
    name: Optional[str] = Field(
        None,
        description="Document name",
        max_length=200
    )
    description: Optional[str] = Field(
        None,
        description="Document description",
        max_length=1000
    )
    base_url: Optional[str] = Field(
        None,
        description="API base URL (optional)"
    )

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate document name is safe"""
        return validate_safe_string(v, "Document name", max_length=200)

    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate description is safe"""
        return validate_safe_string(v, "Document description", max_length=1000)

    @field_validator('base_url')
    @classmethod
    def validate_base_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate base URL format"""
        if v is None:
            return None

        v = v.strip()
        if not v:
            return None

        # Check URL format
        if not re.match(r'^https?://', v):
            raise ValueError(
                "Base URL must start with http:// or https:// "
                f"(got: {v[:50]}...)"
            )

        # Check for dangerous characters
        if any(char in v for char in ['\x00', '\n', '\r', '<', '>']):
            raise ValueError("Base URL contains invalid characters")

        # Basic length check
        if len(v) > 500:
            raise ValueError(
                f"Base URL too long (max 500 characters, got {len(v)})"
            )

        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "My API Documentation",
                "description": "REST API for user management",
                "base_url": "https://api.example.com"
            }
        }


class TestExecutionRequest(BaseModel):
    """Request to start test execution"""
    document_id: str = Field(..., description="Document ID to test", min_length=1, max_length=100)
    max_retries: Optional[int] = Field(3, ge=1, le=5, description="Max retry attempts per endpoint")
    use_optimal_order: Optional[bool] = Field(True, description="Use optimal testing order")
    comprehensive_mode: Optional[bool] = Field(
        True,
        description="Enable comprehensive testing (semantic + LLM + security mutation tests). "
                   "When enabled, generates 40+ tests per endpoint instead of 1-3 basic tests."
    )
    test_types: Optional[List[TestType]] = Field(
        [TestType.POSITIVE],
        description="Types of tests to run",
        max_length=10
    )

    @field_validator('document_id')
    @classmethod
    def validate_document_id_format(cls, v: str) -> str:
        """Validate document ID format"""
        return validate_document_id(v)

    @field_validator('test_types')
    @classmethod
    def validate_test_types_not_empty(cls, v: Optional[List[TestType]]) -> List[TestType]:
        """Ensure at least one test type is specified"""
        if not v:
            return [TestType.POSITIVE]  # Default to positive tests

        # Remove duplicates
        unique_types = list(set(v))

        if len(unique_types) > 3:
            raise ValueError(
                f"Too many test types specified (max 3, got {len(unique_types)})"
            )

        return unique_types

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "doc_abc123def456",
                "max_retries": 3,
                "use_optimal_order": True,
                "comprehensive_mode": True,
                "test_types": ["positive"]
            }
        }


# ============================================================================
# Response Models
# ============================================================================

class DocumentUploadResponse(BaseModel):
    """Response after document upload"""
    document_id: str = Field(..., description="Unique document ID")
    filename: str = Field(..., description="Original filename")
    doc_type: str = Field(..., description="Document type")
    file_size: int = Field(..., description="File size in bytes")
    base_url: Optional[str] = Field(None, description="Extracted base URL")
    endpoints_found: int = Field(..., description="Number of endpoints found")
    chunks_created: int = Field(..., description="Number of text chunks")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    parameters_with_constraints: Optional[int] = Field(
        None,
        description="Number of parameters with extracted constraints"
    )
    constraints_coverage: Optional[float] = Field(
        None,
        description="Percentage of parameters with constraints"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "doc_abc123",
                "filename": "api_doc.pdf",
                "doc_type": "pdf",
                "file_size": 245632,
                "base_url": "https://api.example.com",
                "endpoints_found": 12,
                "chunks_created": 8,
                "parameters_with_constraints": 24,
                "constraints_coverage": 85.7,
                "uploaded_at": "2025-01-15T10:30:00Z"
            }
        }


class EndpointInfo(BaseModel):
    """Information about a single endpoint"""
    path: str = Field(..., description="Endpoint path", max_length=500)
    method: str = Field(..., description="HTTP method", max_length=10)
    summary: Optional[str] = Field(None, description="Endpoint summary", max_length=500)
    auth_required: bool = Field(False, description="Requires authentication")
    parameters: List[Dict[str, Any]] = Field(default_factory=list, description="Parameters", max_length=100)

    @field_validator('path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate endpoint path format"""
        if not v:
            raise ValueError("Endpoint path cannot be empty")

        # Must start with /
        if not v.startswith('/'):
            raise ValueError(f"Endpoint path must start with '/' (got: {v[:50]})")

        # Check for dangerous characters
        if any(char in v for char in ['\x00', '\n', '\r', '<', '>']):
            raise ValueError("Endpoint path contains invalid characters")

        if len(v) > 500:
            raise ValueError(f"Endpoint path too long (max 500 characters, got {len(v)})")

        return v

    @field_validator('method')
    @classmethod
    def validate_method(cls, v: str) -> str:
        """Validate HTTP method"""
        if not v:
            raise ValueError("HTTP method cannot be empty")

        v_upper = v.upper()
        valid_methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']

        if v_upper not in valid_methods:
            raise ValueError(
                f"Invalid HTTP method: {v}. "
                f"Must be one of: {', '.join(valid_methods)}"
            )

        return v_upper

    @field_validator('summary')
    @classmethod
    def validate_summary(cls, v: Optional[str]) -> Optional[str]:
        """Validate endpoint summary is safe"""
        return validate_safe_string(v, "Endpoint summary", max_length=500)


class TestSessionResponse(BaseModel):
    """Response when starting a test session"""
    session_id: str = Field(..., description="Unique session ID")
    document_id: str = Field(..., description="Document being tested")
    status: TestStatus = Field(..., description="Current status")
    total_endpoints: int = Field(..., description="Total endpoints to test")
    started_at: datetime = Field(..., description="Start timestamp")
    estimated_duration: Optional[int] = Field(None, description="Estimated seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session_xyz789",
                "document_id": "doc_abc123",
                "status": "processing",
                "total_endpoints": 12,
                "started_at": "2025-01-15T10:35:00Z",
                "estimated_duration": 60
            }
        }


class TestResult(BaseModel):
    """Individual test result"""
    endpoint: str = Field(..., description="Endpoint key")
    method: str = Field(..., description="HTTP method")
    url: str = Field(..., description="Full URL tested")
    status_code: int = Field(..., description="HTTP status code")
    success: bool = Field(..., description="Test passed")
    attempts: int = Field(..., description="Number of attempts")
    elapsed_time: float = Field(..., description="Time in seconds")
    final_payload: Dict[str, Any] = Field(..., description="Final payload used")
    response: Dict[str, Any] = Field(..., description="API response")
    error: Optional[str] = Field(None, description="Error message if failed")


class TestStatusResponse(BaseModel):
    """Test session status response"""
    session_id: str = Field(..., description="Session ID")
    status: TestStatus = Field(..., description="Current status")
    progress: float = Field(..., ge=0, le=100, description="Progress percentage")
    total_endpoints: int = Field(..., description="Total endpoints")
    tested_endpoints: int = Field(..., description="Endpoints tested so far")
    passed: int = Field(..., description="Tests passed")
    failed: int = Field(..., description="Tests failed")
    started_at: datetime = Field(..., description="Start time")
    updated_at: datetime = Field(..., description="Last update time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session_xyz789",
                "status": "processing",
                "progress": 58.3,
                "total_endpoints": 12,
                "tested_endpoints": 7,
                "passed": 6,
                "failed": 1,
                "started_at": "2025-01-15T10:35:00Z",
                "updated_at": "2025-01-15T10:36:30Z",
                "completed_at": None
            }
        }


class TestReportResponse(BaseModel):
    """Complete test report"""
    session_id: str = Field(..., description="Session ID")
    document_id: str = Field(..., description="Document tested")
    status: TestStatus = Field(..., description="Final status")
    total_tests: int = Field(..., description="Total tests run")
    passed: int = Field(..., description="Tests passed")
    failed: int = Field(..., description="Tests failed")
    success_rate: float = Field(..., ge=0, le=100, description="Success rate percentage")
    total_time: float = Field(..., description="Total time in seconds")
    avg_time: float = Field(..., description="Average time per test")
    total_attempts: int = Field(..., description="Total retry attempts")
    started_at: datetime = Field(..., description="Start time")
    completed_at: datetime = Field(..., description="Completion time")
    results: List[TestResult] = Field(..., description="Detailed test results")
    flow_stats: Dict[str, Any] = Field(..., description="Flow DB statistics")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session_xyz789",
                "document_id": "doc_abc123",
                "status": "completed",
                "total_tests": 12,
                "passed": 10,
                "failed": 2,
                "success_rate": 83.3,
                "total_time": 45.6,
                "avg_time": 3.8,
                "total_attempts": 14,
                "started_at": "2025-01-15T10:35:00Z",
                "completed_at": "2025-01-15T10:36:15Z",
                "results": [],
                "flow_stats": {}
            }
        }


class DocumentListResponse(BaseModel):
    """List of documents"""
    documents: List[Dict[str, Any]] = Field(..., description="List of documents")
    total: int = Field(..., description="Total count")


class ErrorResponse(BaseModel):
    """Error response"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Invalid document format",
                "details": {"field": "file", "issue": "Unsupported file type"}
            }
        }


# ============================================================================
# Internal Models (Database, etc.)
# ============================================================================

class DocumentMetadata(BaseModel):
    """Internal document metadata"""
    id: str
    filename: str
    original_filename: str
    doc_type: str
    file_size: int
    file_path: str
    base_url: Optional[str]
    endpoints: List[Dict[str, Any]]
    chunks_count: int
    uploaded_at: datetime
    processed: bool


class TestSessionMetadata(BaseModel):
    """Internal test session metadata"""
    id: str
    document_id: str
    status: TestStatus
    total_endpoints: int
    tested_endpoints: int
    passed: int
    failed: int
    started_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    results: List[Dict[str, Any]]
