"""
Prometheus Metrics for AutoTest-RL
Production-grade metrics collection and exposition
Phase 10: Observability & Monitoring
"""

import time
from typing import Optional, Dict, Any
from functools import wraps
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Histogram,
    Gauge,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from loguru import logger


# ============================================================================
# Metrics Registry
# ============================================================================

# Create a custom registry for our metrics
metrics_registry = CollectorRegistry()


# ============================================================================
# HTTP Metrics
# ============================================================================

http_requests_total = Counter(
    name='autotest_http_requests_total',
    documentation='Total number of HTTP requests',
    labelnames=['method', 'endpoint', 'status_code'],
    registry=metrics_registry
)

http_request_duration_seconds = Histogram(
    name='autotest_http_request_duration_seconds',
    documentation='HTTP request latency in seconds',
    labelnames=['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=metrics_registry
)

http_requests_in_progress = Gauge(
    name='autotest_http_requests_in_progress',
    documentation='Number of HTTP requests currently being processed',
    labelnames=['method', 'endpoint'],
    registry=metrics_registry
)


# ============================================================================
# Business Metrics - Test Execution
# ============================================================================

test_executions_total = Counter(
    name='autotest_test_executions_total',
    documentation='Total number of test executions',
    labelnames=['status', 'endpoint_method', 'test_type'],
    registry=metrics_registry
)

test_execution_duration_seconds = Histogram(
    name='autotest_test_execution_duration_seconds',
    documentation='Test execution duration in seconds',
    labelnames=['endpoint_method', 'test_type'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0),
    registry=metrics_registry
)

test_retry_attempts_total = Counter(
    name='autotest_test_retry_attempts_total',
    documentation='Total number of test retry attempts',
    labelnames=['endpoint_method', 'reason'],
    registry=metrics_registry
)

test_success_rate = Gauge(
    name='autotest_test_success_rate',
    documentation='Test success rate (percentage)',
    labelnames=['session_id'],
    registry=metrics_registry
)


# ============================================================================
# Business Metrics - Document Processing
# ============================================================================

document_uploads_total = Counter(
    name='autotest_document_uploads_total',
    documentation='Total number of document uploads',
    labelnames=['doc_type', 'status'],
    registry=metrics_registry
)

document_processing_duration_seconds = Histogram(
    name='autotest_document_processing_duration_seconds',
    documentation='Document processing duration in seconds',
    labelnames=['doc_type', 'phase'],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
    registry=metrics_registry
)

endpoints_discovered = Histogram(
    name='autotest_endpoints_discovered',
    documentation='Number of endpoints discovered per document',
    buckets=(1, 5, 10, 20, 50, 100, 200),
    registry=metrics_registry
)


# ============================================================================
# Business Metrics - LLM Operations
# ============================================================================

llm_requests_total = Counter(
    name='autotest_llm_requests_total',
    documentation='Total number of LLM requests',
    labelnames=['provider', 'model', 'operation'],
    registry=metrics_registry
)

llm_request_duration_seconds = Histogram(
    name='autotest_llm_request_duration_seconds',
    documentation='LLM request duration in seconds',
    labelnames=['provider', 'model', 'operation'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
    registry=metrics_registry
)

llm_tokens_used_total = Counter(
    name='autotest_llm_tokens_used_total',
    documentation='Total number of LLM tokens used',
    labelnames=['provider', 'model', 'token_type'],
    registry=metrics_registry
)

llm_errors_total = Counter(
    name='autotest_llm_errors_total',
    documentation='Total number of LLM errors',
    labelnames=['provider', 'model', 'error_type'],
    registry=metrics_registry
)


# ============================================================================
# Business Metrics - RAG Operations
# ============================================================================

rag_queries_total = Counter(
    name='autotest_rag_queries_total',
    documentation='Total number of RAG queries',
    labelnames=['store_type', 'operation'],
    registry=metrics_registry
)

rag_query_duration_seconds = Histogram(
    name='autotest_rag_query_duration_seconds',
    documentation='RAG query duration in seconds',
    labelnames=['store_type', 'operation'],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0),
    registry=metrics_registry
)

rag_documents_stored_total = Counter(
    name='autotest_rag_documents_stored_total',
    documentation='Total number of documents stored in RAG',
    labelnames=['store_type'],
    registry=metrics_registry
)

rag_similarity_scores = Histogram(
    name='autotest_rag_similarity_scores',
    documentation='Distribution of RAG similarity scores',
    labelnames=['store_type'],
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
    registry=metrics_registry
)


# ============================================================================
# Business Metrics - Workflow Orchestration
# ============================================================================

workflow_executions_total = Counter(
    name='autotest_workflow_executions_total',
    documentation='Total number of workflow executions',
    labelnames=['status', 'phase'],
    registry=metrics_registry
)

workflow_execution_duration_seconds = Histogram(
    name='autotest_workflow_execution_duration_seconds',
    documentation='Workflow execution duration in seconds',
    labelnames=['phase'],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0),
    registry=metrics_registry
)

workflow_phase_duration_seconds = Histogram(
    name='autotest_workflow_phase_duration_seconds',
    documentation='Individual workflow phase duration in seconds',
    labelnames=['workflow_id', 'phase'],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
    registry=metrics_registry
)


# ============================================================================
# Business Metrics - Self-Healing
# ============================================================================

self_healing_actions_total = Counter(
    name='autotest_self_healing_actions_total',
    documentation='Total number of self-healing actions',
    labelnames=['action_type', 'success'],
    registry=metrics_registry
)

api_changes_detected_total = Counter(
    name='autotest_api_changes_detected_total',
    documentation='Total number of API changes detected',
    labelnames=['change_type', 'severity'],
    registry=metrics_registry
)


# ============================================================================
# System Metrics
# ============================================================================

api_errors_total = Counter(
    name='autotest_api_errors_total',
    documentation='Total number of API errors',
    labelnames=['error_type', 'endpoint'],
    registry=metrics_registry
)

active_sessions = Gauge(
    name='autotest_active_sessions',
    documentation='Number of currently active test sessions',
    registry=metrics_registry
)

system_info = Info(
    name='autotest_system',
    documentation='System information',
    registry=metrics_registry
)


# ============================================================================
# Helper Functions
# ============================================================================

def record_http_request(
    method: str,
    endpoint: str,
    status_code: int,
    duration: float
):
    """
    Record HTTP request metrics

    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: Endpoint path
        status_code: Response status code
        duration: Request duration in seconds
    """
    http_requests_total.labels(
        method=method,
        endpoint=endpoint,
        status_code=status_code
    ).inc()

    http_request_duration_seconds.labels(
        method=method,
        endpoint=endpoint
    ).observe(duration)


def record_test_execution(
    status: str,
    endpoint_method: str,
    test_type: str,
    duration: Optional[float] = None,
    attempts: Optional[int] = None
):
    """
    Record test execution metrics

    Args:
        status: Test status (passed, failed, error)
        endpoint_method: HTTP method of tested endpoint
        test_type: Type of test (semantic, mutation, llm)
        duration: Test duration in seconds
        attempts: Number of retry attempts
    """
    test_executions_total.labels(
        status=status,
        endpoint_method=endpoint_method,
        test_type=test_type
    ).inc()

    if duration is not None:
        test_execution_duration_seconds.labels(
            endpoint_method=endpoint_method,
            test_type=test_type
        ).observe(duration)

    if attempts and attempts > 1:
        test_retry_attempts_total.labels(
            endpoint_method=endpoint_method,
            reason='retry_after_failure'
        ).inc(attempts - 1)


def record_document_upload(
    doc_type: str,
    status: str,
    processing_duration: Optional[float] = None,
    endpoints_count: Optional[int] = None
):
    """
    Record document upload metrics

    Args:
        doc_type: Document type (pdf, json, yaml)
        status: Upload status (success, failed)
        processing_duration: Processing duration in seconds
        endpoints_count: Number of endpoints discovered
    """
    document_uploads_total.labels(
        doc_type=doc_type,
        status=status
    ).inc()

    if processing_duration is not None:
        document_processing_duration_seconds.labels(
            doc_type=doc_type,
            phase='complete'
        ).observe(processing_duration)

    if endpoints_count is not None:
        endpoints_discovered.observe(endpoints_count)


def record_llm_request(
    provider: str,
    model: str,
    operation: str,
    duration: float,
    tokens_used: Optional[int] = None,
    error: Optional[str] = None
):
    """
    Record LLM request metrics

    Args:
        provider: LLM provider (ollama, openai, anthropic)
        model: Model name
        operation: Operation type (analyze, generate, fix)
        duration: Request duration in seconds
        tokens_used: Number of tokens used
        error: Error type if request failed
    """
    llm_requests_total.labels(
        provider=provider,
        model=model,
        operation=operation
    ).inc()

    llm_request_duration_seconds.labels(
        provider=provider,
        model=model,
        operation=operation
    ).observe(duration)

    if tokens_used is not None:
        llm_tokens_used_total.labels(
            provider=provider,
            model=model,
            token_type='total'
        ).inc(tokens_used)

    if error:
        llm_errors_total.labels(
            provider=provider,
            model=model,
            error_type=error
        ).inc()


def record_rag_query(
    store_type: str,
    operation: str,
    duration: float,
    similarity_score: Optional[float] = None
):
    """
    Record RAG query metrics

    Args:
        store_type: Store type (doc_store, flow_store)
        operation: Operation (query, add, delete)
        duration: Query duration in seconds
        similarity_score: Similarity score of best match
    """
    rag_queries_total.labels(
        store_type=store_type,
        operation=operation
    ).inc()

    rag_query_duration_seconds.labels(
        store_type=store_type,
        operation=operation
    ).observe(duration)

    if similarity_score is not None:
        rag_similarity_scores.labels(
            store_type=store_type
        ).observe(similarity_score)


def record_workflow_execution(
    status: str,
    phase: str,
    duration: Optional[float] = None,
    workflow_id: Optional[str] = None
):
    """
    Record workflow execution metrics

    Args:
        status: Workflow status (completed, failed)
        phase: Workflow phase
        duration: Execution duration in seconds
        workflow_id: Workflow ID for phase-specific tracking
    """
    workflow_executions_total.labels(
        status=status,
        phase=phase
    ).inc()

    if duration is not None:
        workflow_execution_duration_seconds.labels(
            phase=phase
        ).observe(duration)

        if workflow_id:
            workflow_phase_duration_seconds.labels(
                workflow_id=workflow_id,
                phase=phase
            ).observe(duration)


def record_api_error(error_type: str, endpoint: str):
    """
    Record API error metrics

    Args:
        error_type: Type of error
        endpoint: Endpoint where error occurred
    """
    api_errors_total.labels(
        error_type=error_type,
        endpoint=endpoint
    ).inc()


def update_active_sessions(count: int):
    """
    Update active sessions gauge

    Args:
        count: Current number of active sessions
    """
    active_sessions.set(count)


def set_system_info(version: str, environment: str, llm_provider: str):
    """
    Set system information

    Args:
        version: Application version
        environment: Environment (development, production)
        llm_provider: LLM provider being used
    """
    system_info.info({
        'version': version,
        'environment': environment,
        'llm_provider': llm_provider
    })


# ============================================================================
# Decorators for Automatic Metrics Collection
# ============================================================================

def track_duration(metric: Histogram, **labels):
    """
    Decorator to track function execution duration

    Usage:
        @track_duration(llm_request_duration_seconds, provider="ollama", model="phi3", operation="analyze")
        def analyze_endpoint(text):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                metric.labels(**labels).observe(duration)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                metric.labels(**labels).observe(duration)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def count_calls(metric: Counter, **labels):
    """
    Decorator to count function calls

    Usage:
        @count_calls(llm_requests_total, provider="ollama", model="phi3", operation="analyze")
        def analyze_endpoint(text):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            metric.labels(**labels).inc()
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            metric.labels(**labels).inc()
            return func(*args, **kwargs)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ============================================================================
# Metrics Endpoint
# ============================================================================

def get_metrics() -> tuple[bytes, str]:
    """
    Get Prometheus metrics in exposition format

    Returns:
        Tuple of (metrics_content, content_type)
    """
    return generate_latest(metrics_registry), CONTENT_TYPE_LATEST
