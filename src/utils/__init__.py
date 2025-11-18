"""
Utility Functions and Helpers
Every small detail and helper function the system needs
"""

# Text utilities
from src.utils.text_utils import (
    clean_text,
    truncate_text,
    extract_urls,
    extract_json,
    extract_code_blocks,
    extract_emails,
    sanitize_filename,
    count_tokens_approximate,
    normalize_whitespace,
    word_count,
    line_count,
    char_count,
)

# Validation utilities
from src.utils.validation import (
    validate_url,
    validate_email,
    validate_json,
    validate_api_key,
    validate_ip_address,
    validate_port,
    validate_file_extension,
    validate_json_path,
    is_valid_http_method,
    is_valid_status_code,
    sanitize_input,
)

# Formatting utilities
from src.utils.formatting import (
    format_bytes,
    format_duration,
    format_timestamp,
    format_percentage,
    format_number,
)

# Retry utilities
from src.utils.retry import (
    retry_with_backoff,
    retry_async_with_backoff,
    retry_on_exception,
    exponential_backoff,
    RetryConfig,
    RetryStrategy,
)

# Async utilities
from src.utils.async_helpers import (
    run_async_with_timeout,
    gather_with_concurrency,
    async_retry,
    run_in_batches,
    race_tasks,
    run_with_progress,
    async_map,
    async_filter,
    AsyncContextManager,
    async_lru_cache,
    async_debounce,
    async_throttle,
)

__all__ = [
    # Text utilities (12 functions)
    "clean_text",
    "truncate_text",
    "extract_urls",
    "extract_json",
    "extract_code_blocks",
    "extract_emails",
    "sanitize_filename",
    "count_tokens_approximate",
    "normalize_whitespace",
    "word_count",
    "line_count",
    "char_count",

    # Validation utilities (11 functions)
    "validate_url",
    "validate_email",
    "validate_json",
    "validate_api_key",
    "validate_ip_address",
    "validate_port",
    "validate_file_extension",
    "validate_json_path",
    "is_valid_http_method",
    "is_valid_status_code",
    "sanitize_input",

    # Formatting utilities (5 functions)
    "format_bytes",
    "format_duration",
    "format_timestamp",
    "format_percentage",
    "format_number",

    # Retry utilities (6 functions/classes)
    "retry_with_backoff",
    "retry_async_with_backoff",
    "retry_on_exception",
    "exponential_backoff",
    "RetryConfig",
    "RetryStrategy",

    # Async utilities (12 functions/classes)
    "run_async_with_timeout",
    "gather_with_concurrency",
    "async_retry",
    "run_in_batches",
    "race_tasks",
    "run_with_progress",
    "async_map",
    "async_filter",
    "AsyncContextManager",
    "async_lru_cache",
    "async_debounce",
    "async_throttle",
]
