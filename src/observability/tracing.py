"""
Distributed Tracing
Correlation IDs and span tracking for request tracing
Phase 10: Observability & Monitoring
"""

import time
import uuid
from typing import Optional, Dict, Any, Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps

from loguru import logger


# ============================================================================
# Context Variables for Request Tracing
# ============================================================================

# Store current trace context in async context
_trace_context: ContextVar[Optional['TracingContext']] = ContextVar('trace_context', default=None)


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class Span:
    """Represents a traced operation span"""
    span_id: str
    name: str
    operation: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    parent_span_id: Optional[str] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: list = field(default_factory=list)
    status: str = "started"  # started, completed, error

    def finish(self, status: str = "completed"):
        """Mark span as finished"""
        self.ended_at = datetime.now()
        self.duration_ms = (self.ended_at - self.started_at).total_seconds() * 1000
        self.status = status

    def add_tag(self, key: str, value: Any):
        """Add a tag to the span"""
        self.tags[key] = value

    def log(self, message: str, **kwargs):
        """Add a log entry to the span"""
        self.logs.append({
            "timestamp": datetime.now().isoformat(),
            "message": message,
            **kwargs
        })

    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary"""
        return {
            "span_id": self.span_id,
            "name": self.name,
            "operation": self.operation,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration_ms": self.duration_ms,
            "parent_span_id": self.parent_span_id,
            "tags": self.tags,
            "logs": self.logs,
            "status": self.status
        }


@dataclass
class TracingContext:
    """
    Tracing context for a request

    Maintains trace ID, spans, and correlation information
    """
    trace_id: str
    request_id: str
    root_span: Optional[Span] = None
    current_span: Optional[Span] = None
    spans: list[Span] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def create_span(
        self,
        name: str,
        operation: str,
        parent_span_id: Optional[str] = None,
        **tags
    ) -> Span:
        """
        Create a new span

        Args:
            name: Span name
            operation: Operation type (e.g., "http.request", "llm.generate")
            parent_span_id: Parent span ID (defaults to current span)
            **tags: Additional tags for the span

        Returns:
            Created span
        """
        span_id = str(uuid.uuid4())[:8]

        # If no parent specified, use current span
        if parent_span_id is None and self.current_span:
            parent_span_id = self.current_span.span_id

        span = Span(
            span_id=span_id,
            name=name,
            operation=operation,
            started_at=datetime.now(),
            parent_span_id=parent_span_id,
            tags=tags
        )

        # Set as root span if this is the first span
        if self.root_span is None:
            self.root_span = span

        self.spans.append(span)
        self.current_span = span

        logger.debug(
            f"Created span: {name}",
            span_id=span_id,
            trace_id=self.trace_id,
            operation=operation
        )

        return span

    def finish_span(self, span: Optional[Span] = None, status: str = "completed"):
        """
        Finish a span

        Args:
            span: Span to finish (defaults to current span)
            status: Span status (completed, error)
        """
        span_to_finish = span or self.current_span

        if span_to_finish:
            span_to_finish.finish(status)

            logger.debug(
                f"Finished span: {span_to_finish.name}",
                span_id=span_to_finish.span_id,
                duration_ms=span_to_finish.duration_ms,
                status=status
            )

            # Update current span to parent if finishing current span
            if span_to_finish == self.current_span and span_to_finish.parent_span_id:
                self.current_span = next(
                    (s for s in self.spans if s.span_id == span_to_finish.parent_span_id),
                    None
                )

    def get_trace_summary(self) -> Dict[str, Any]:
        """Get summary of all spans in this trace"""
        total_duration = (datetime.now() - self.started_at).total_seconds() * 1000

        return {
            "trace_id": self.trace_id,
            "request_id": self.request_id,
            "total_duration_ms": total_duration,
            "total_spans": len(self.spans),
            "completed_spans": len([s for s in self.spans if s.status == "completed"]),
            "error_spans": len([s for s in self.spans if s.status == "error"]),
            "spans": [span.to_dict() for span in self.spans],
            "metadata": self.metadata
        }


# ============================================================================
# Context Management
# ============================================================================

def create_tracing_context(request_id: Optional[str] = None) -> TracingContext:
    """
    Create a new tracing context

    Args:
        request_id: Optional request ID (generates UUID if not provided)

    Returns:
        New TracingContext
    """
    trace_id = str(uuid.uuid4())
    req_id = request_id or str(uuid.uuid4())

    context = TracingContext(
        trace_id=trace_id,
        request_id=req_id
    )

    # Set in context var
    _trace_context.set(context)

    logger.debug(f"Created tracing context", trace_id=trace_id, request_id=req_id)

    return context


def get_tracing_context() -> Optional[TracingContext]:
    """Get current tracing context from context var"""
    return _trace_context.get()


def set_tracing_context(context: TracingContext):
    """Set tracing context in context var"""
    _trace_context.set(context)


def clear_tracing_context():
    """Clear tracing context"""
    _trace_context.set(None)


# ============================================================================
# Span Management
# ============================================================================

def create_span(
    name: str,
    operation: str,
    **tags
) -> Optional[Span]:
    """
    Create a new span in current tracing context

    Args:
        name: Span name
        operation: Operation type
        **tags: Additional tags

    Returns:
        Created span or None if no context
    """
    context = get_tracing_context()

    if context:
        return context.create_span(name, operation, **tags)

    return None


def get_current_span() -> Optional[Span]:
    """Get current active span"""
    context = get_tracing_context()

    if context:
        return context.current_span

    return None


def finish_current_span(status: str = "completed"):
    """Finish current span"""
    context = get_tracing_context()

    if context and context.current_span:
        context.finish_span(status=status)


def add_span_tag(key: str, value: Any):
    """Add tag to current span"""
    span = get_current_span()

    if span:
        span.add_tag(key, value)


def log_to_span(message: str, **kwargs):
    """Add log entry to current span"""
    span = get_current_span()

    if span:
        span.log(message, **kwargs)


# ============================================================================
# Decorators for Automatic Tracing
# ============================================================================

def trace_function(operation: str, **default_tags):
    """
    Decorator to trace a synchronous function

    Usage:
        @trace_function("database.query", table="users")
        def get_users():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            context = get_tracing_context()

            if not context:
                # No tracing context, just call function
                return func(*args, **kwargs)

            # Create span for this function
            span = context.create_span(
                name=func.__name__,
                operation=operation,
                **default_tags
            )

            try:
                result = func(*args, **kwargs)
                context.finish_span(span, status="completed")
                return result

            except Exception as e:
                span.add_tag("error", True)
                span.add_tag("error.message", str(e))
                span.add_tag("error.type", type(e).__name__)
                context.finish_span(span, status="error")
                raise

        return wrapper

    return decorator


def trace_async_function(operation: str, **default_tags):
    """
    Decorator to trace an asynchronous function

    Usage:
        @trace_async_function("llm.generate", provider="ollama")
        async def generate_response(prompt):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            context = get_tracing_context()

            if not context:
                # No tracing context, just call function
                return await func(*args, **kwargs)

            # Create span for this function
            span = context.create_span(
                name=func.__name__,
                operation=operation,
                **default_tags
            )

            try:
                result = await func(*args, **kwargs)
                context.finish_span(span, status="completed")
                return result

            except Exception as e:
                span.add_tag("error", True)
                span.add_tag("error.message", str(e))
                span.add_tag("error.type", type(e).__name__)
                context.finish_span(span, status="error")
                raise

        return wrapper

    return decorator


# ============================================================================
# Context Manager for Spans
# ============================================================================

class traced_span:
    """
    Context manager for creating and finishing spans

    Usage:
        with traced_span("database_query", "db.query", table="users"):
            results = db.query("SELECT * FROM users")
    """

    def __init__(self, name: str, operation: str, **tags):
        self.name = name
        self.operation = operation
        self.tags = tags
        self.span: Optional[Span] = None

    def __enter__(self):
        self.span = create_span(self.name, self.operation, **self.tags)
        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.span:
            context = get_tracing_context()
            if context:
                status = "error" if exc_type else "completed"
                if exc_type:
                    self.span.add_tag("error", True)
                    self.span.add_tag("error.message", str(exc_val))
                    self.span.add_tag("error.type", exc_type.__name__)
                context.finish_span(self.span, status=status)


class traced_async_span:
    """
    Async context manager for creating and finishing spans

    Usage:
        async with traced_async_span("api_call", "http.request", endpoint="/users"):
            response = await client.get("/users")
    """

    def __init__(self, name: str, operation: str, **tags):
        self.name = name
        self.operation = operation
        self.tags = tags
        self.span: Optional[Span] = None

    async def __aenter__(self):
        self.span = create_span(self.name, self.operation, **self.tags)
        return self.span

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.span:
            context = get_tracing_context()
            if context:
                status = "error" if exc_type else "completed"
                if exc_type:
                    self.span.add_tag("error", True)
                    self.span.add_tag("error.message", str(exc_val))
                    self.span.add_tag("error.type", exc_type.__name__)
                context.finish_span(self.span, status=status)
