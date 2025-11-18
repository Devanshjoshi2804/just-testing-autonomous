"""
Observability Module
Metrics, tracing, and monitoring for production systems
Phase 10: Observability & Monitoring
"""

from src.observability.metrics import (
    metrics_registry,
    http_requests_total,
    http_request_duration_seconds,
    test_executions_total,
    document_uploads_total,
    llm_requests_total,
    llm_request_duration_seconds,
    rag_queries_total,
    workflow_executions_total,
    api_errors_total,
    record_http_request,
    record_test_execution,
    record_document_upload,
    record_llm_request,
    record_rag_query,
    record_workflow_execution,
    record_api_error,
)

from src.observability.tracing import (
    TracingContext,
    create_span,
    get_current_span,
    trace_function,
    trace_async_function,
)

__all__ = [
    # Metrics registry
    "metrics_registry",

    # Metric instances
    "http_requests_total",
    "http_request_duration_seconds",
    "test_executions_total",
    "document_uploads_total",
    "llm_requests_total",
    "llm_request_duration_seconds",
    "rag_queries_total",
    "workflow_executions_total",
    "api_errors_total",

    # Helper functions
    "record_http_request",
    "record_test_execution",
    "record_document_upload",
    "record_llm_request",
    "record_rag_query",
    "record_workflow_execution",
    "record_api_error",

    # Tracing
    "TracingContext",
    "create_span",
    "get_current_span",
    "trace_function",
    "trace_async_function",
]
