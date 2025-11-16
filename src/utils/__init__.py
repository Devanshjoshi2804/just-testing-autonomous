"""
Utility Functions and Helpers
Every small detail and helper function the system needs
"""

from src.utils.text_utils import (
    clean_text,
    truncate_text,
    extract_urls,
    extract_json,
    sanitize_filename,
    count_tokens_approximate,
)

from src.utils.validation import (
    validate_url,
    validate_email,
    validate_json,
    validate_api_key,
    is_valid_http_method,
    is_valid_status_code,
)

from src.utils.formatting import (
    format_bytes,
    format_duration,
    format_timestamp,
    format_percentage,
    format_number,
)

from src.utils.retry import (
    retry_with_backoff,
    exponential_backoff,
    RetryConfig,
)

from src.utils.async_helpers import (
    run_async_with_timeout,
    gather_with_concurrency,
    async_retry,
)

__all__ = [
    # Text utilities
    "clean_text",
    "truncate_text",
    "extract_urls",
    "extract_json",
    "sanitize_filename",
    "count_tokens_approximate",

    # Validation
    "validate_url",
    "validate_email",
    "validate_json",
    "validate_api_key",
    "is_valid_http_method",
    "is_valid_status_code",

    # Formatting
    "format_bytes",
    "format_duration",
    "format_timestamp",
    "format_percentage",
    "format_number",

    # Retry
    "retry_with_backoff",
    "exponential_backoff",
    "RetryConfig",

    # Async helpers
    "run_async_with_timeout",
    "gather_with_concurrency",
    "async_retry",
]
