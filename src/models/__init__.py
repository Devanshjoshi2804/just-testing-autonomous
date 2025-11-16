"""
Pydantic Models and Schemas for API validation
"""
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum


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
# Request Models
# ============================================================================

class DocumentUploadRequest(BaseModel):
    """Document upload metadata"""
    name: Optional[str] = Field(None, description="Document name")
    description: Optional[str] = Field(None, description="Document description")
    base_url: Optional[str] = Field(None, description="API base URL (optional)")

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
    document_id: str = Field(..., description="Document ID to test")
    max_retries: Optional[int] = Field(3, ge=1, le=5, description="Max retry attempts per endpoint")
    use_optimal_order: Optional[bool] = Field(True, description="Use optimal testing order")
    comprehensive_mode: Optional[bool] = Field(
        True,
        description="Enable comprehensive testing (semantic + LLM + security mutation tests). "
                   "When enabled, generates 40+ tests per endpoint instead of 1-3 basic tests."
    )
    test_types: Optional[List[TestType]] = Field(
        [TestType.POSITIVE],
        description="Types of tests to run"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "doc_abc123",
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
                "uploaded_at": "2025-01-15T10:30:00Z"
            }
        }


class EndpointInfo(BaseModel):
    """Information about a single endpoint"""
    path: str = Field(..., description="Endpoint path")
    method: str = Field(..., description="HTTP method")
    summary: Optional[str] = Field(None, description="Endpoint summary")
    auth_required: bool = Field(False, description="Requires authentication")
    parameters: List[Dict[str, Any]] = Field(default_factory=list, description="Parameters")


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
