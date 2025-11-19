"""
Observability Module
Comprehensive observability, tracing, and audit logging
"""
from src.observability.audit import (
    AuditLogger,
    AuditEvent,
    AuditEventType,
    AuditSeverity,
    get_audit_logger,
    audit_log,
    audit_middleware,
    audit_logger
)
from src.observability.tracing import (
    DistributedTracer,
    init_tracing,
    get_tracer,
    start_span,
    trace
)

__all__ = [
    # Audit Logging
    "AuditLogger",
    "AuditEvent",
    "AuditEventType",
    "AuditSeverity",
    "get_audit_logger",
    "audit_log",
    "audit_middleware",
    "audit_logger",

    # Distributed Tracing
    "DistributedTracer",
    "init_tracing",
    "get_tracer",
    "start_span",
    "trace",
]
