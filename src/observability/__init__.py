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
from src.observability.sli_slo import (
    SLICollector,
    SLI,
    SLO,
    SLIType,
    SLOStatus,
    get_sli_collector,
    record_request_sli,
    record_llm_sli,
    get_slo_health_status
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

    # SLI/SLO Monitoring
    "SLICollector",
    "SLI",
    "SLO",
    "SLIType",
    "SLOStatus",
    "get_sli_collector",
    "record_request_sli",
    "record_llm_sli",
    "get_slo_health_status",
]
