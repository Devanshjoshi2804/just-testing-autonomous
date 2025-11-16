"""
Custom Exception Hierarchy for AutoTest-RL
Provides specific exceptions for better error handling and debugging
"""
from typing import Optional, Dict, Any


class AutoTestException(Exception):
    """
    Base exception for all AutoTest-RL errors

    All custom exceptions should inherit from this class.
    This allows catching all AutoTest-specific exceptions with a single except clause.
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        self.message = message
        self.details = details or {}
        self.original_error = original_error
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses"""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details
        }


# ============================================================================
# Document Processing Exceptions
# ============================================================================

class DocumentProcessingError(AutoTestException):
    """Base exception for document processing errors"""
    pass


class DocumentParseError(DocumentProcessingError):
    """Document parsing failed"""
    pass


class InvalidDocumentFormat(DocumentProcessingError):
    """Document format is not supported or invalid"""
    pass


class DocumentNotFound(DocumentProcessingError):
    """Document was not found"""
    pass


class DocumentValidationError(DocumentProcessingError):
    """Document validation failed (not API documentation)"""
    pass


# ============================================================================
# RAG System Exceptions
# ============================================================================

class RAGError(AutoTestException):
    """Base exception for RAG system errors"""
    pass


class EmbeddingGenerationError(RAGError):
    """Failed to generate embeddings"""
    pass


class ChromaDBError(RAGError):
    """ChromaDB operation failed"""
    pass


class QueryError(RAGError):
    """Semantic query failed"""
    pass


# ============================================================================
# Agent Exceptions
# ============================================================================

class AgentError(AutoTestException):
    """Base exception for AI agent errors"""
    pass


class LLMError(AgentError):
    """LLM invocation failed"""
    pass


class EndpointAnalysisError(AgentError):
    """Endpoint analysis failed"""
    pass


class TestGenerationError(AgentError):
    """Test case generation failed"""
    pass


class ErrorFixingError(AgentError):
    """Error fixing attempt failed"""
    pass


# ============================================================================
# Test Execution Exceptions
# ============================================================================

class TestExecutionError(AutoTestException):
    """Base exception for test execution errors"""
    pass


class HTTPRequestError(TestExecutionError):
    """HTTP request failed"""
    pass


class TestTimeoutError(TestExecutionError):
    """Test execution timed out"""
    pass


class MaxRetriesExceeded(TestExecutionError):
    """Maximum retry attempts exceeded"""
    pass


class AuthenticationError(TestExecutionError):
    """Authentication failed during testing"""
    pass


# ============================================================================
# Storage Exceptions
# ============================================================================

class StorageError(AutoTestException):
    """Base exception for storage errors"""
    pass


class RedisError(StorageError):
    """Redis operation failed"""
    pass


class SessionNotFound(StorageError):
    """Test session not found"""
    pass


class SessionExpired(StorageError):
    """Test session has expired"""
    pass


# ============================================================================
# API Exceptions
# ============================================================================

class APIError(AutoTestException):
    """Base exception for API errors"""
    pass


class ValidationError(APIError):
    """Request validation failed"""
    pass


class RateLimitExceeded(APIError):
    """Rate limit exceeded"""
    pass


class UnauthorizedError(APIError):
    """User is not authorized"""
    pass


class ResourceNotFound(APIError):
    """Requested resource not found"""
    pass


# ============================================================================
# Task Exceptions
# ============================================================================

class TaskError(AutoTestException):
    """Base exception for Celery task errors"""
    pass


class TaskExecutionError(TaskError):
    """Task execution failed"""
    pass


class TaskTimeoutError(TaskError):
    """Task execution timed out"""
    pass


class TaskRevoked(TaskError):
    """Task was revoked/cancelled"""
    pass


# ============================================================================
# Configuration Exceptions
# ============================================================================

class ConfigurationError(AutoTestException):
    """Base exception for configuration errors"""
    pass


class InvalidConfiguration(ConfigurationError):
    """Configuration is invalid"""
    pass


class MissingConfiguration(ConfigurationError):
    """Required configuration is missing"""
    pass


# ============================================================================
# Helper Functions
# ============================================================================

def create_error_response(
    exception: AutoTestException,
    status_code: int = 500
) -> Dict[str, Any]:
    """
    Create standardized error response from exception

    Args:
        exception: AutoTest exception
        status_code: HTTP status code

    Returns:
        Error response dictionary
    """
    return {
        "status_code": status_code,
        "error": exception.__class__.__name__,
        "message": exception.message,
        "details": exception.details
    }
