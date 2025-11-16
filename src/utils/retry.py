"""
Retry Utilities with Exponential Backoff
Comprehensive retry logic for resilient operations
"""
import time
import random
import functools
from typing import Callable, TypeVar, Optional, Tuple, Type, List, Any
from dataclasses import dataclass
from loguru import logger

T = TypeVar('T')


@dataclass
class RetryConfig:
    """
    Retry configuration with all options

    Attributes:
        max_attempts: Maximum retry attempts (including first try)
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff (2 = double each time)
        jitter: Add randomness to prevent thundering herd (0.0-1.0)
        retryable_exceptions: Tuple of exceptions to retry on
        on_retry: Callback function called before each retry
        on_failure: Callback function called when all retries exhausted
    """
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: float = 0.1
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    on_retry: Optional[Callable[[Exception, int], None]] = None
    on_failure: Optional[Callable[[Exception, int], None]] = None


def exponential_backoff(
    attempt: int,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: float = 0.1,
) -> float:
    """
    Calculate exponential backoff delay

    Args:
        attempt: Current attempt number (0-based)
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential growth
        jitter: Random jitter factor (0.0-1.0)

    Returns:
        Delay in seconds

    Examples:
        >>> exponential_backoff(0)  # First retry
        ~1.0 seconds (+ jitter)
        >>> exponential_backoff(1)  # Second retry
        ~2.0 seconds (+ jitter)
        >>> exponential_backoff(2)  # Third retry
        ~4.0 seconds (+ jitter)

    Formula:
        delay = min(initial_delay * (exponential_base ^ attempt), max_delay)
        delay += random(-jitter * delay, +jitter * delay)
    """
    # Calculate base delay
    delay = min(initial_delay * (exponential_base ** attempt), max_delay)

    # Add jitter to prevent thundering herd
    if jitter > 0:
        jitter_amount = delay * jitter
        delay += random.uniform(-jitter_amount, jitter_amount)

    # Ensure positive
    delay = max(0, delay)

    return delay


def retry_with_backoff(
    config: Optional[RetryConfig] = None,
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: float = 0.1,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
    on_failure: Optional[Callable[[Exception, int], None]] = None,
):
    """
    Decorator for retry with exponential backoff

    Args:
        config: RetryConfig object (overrides other args)
        max_attempts: Maximum retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Exponential base
        jitter: Jitter factor
        retryable_exceptions: Exceptions to retry on
        on_retry: Callback before retry
        on_failure: Callback after all retries fail

    Returns:
        Decorated function

    Examples:
        @retry_with_backoff(max_attempts=3, initial_delay=1.0)
        def unstable_function():
            # Might fail occasionally
            ...

        @retry_with_backoff(
            retryable_exceptions=(ConnectionError, TimeoutError),
            on_retry=lambda e, attempt: print(f"Retry {attempt}: {e}")
        )
        def network_request():
            ...
    """
    # Use config if provided, otherwise use individual params
    if config:
        max_attempts = config.max_attempts
        initial_delay = config.initial_delay
        max_delay = config.max_delay
        exponential_base = config.exponential_base
        jitter = config.jitter
        retryable_exceptions = config.retryable_exceptions
        on_retry = config.on_retry
        on_failure = config.on_failure

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    # Attempt the function
                    result = func(*args, **kwargs)

                    # Success! Log if this was a retry
                    if attempt > 0:
                        logger.info(
                            f"✅ {func.__name__} succeeded on attempt {attempt + 1}/{max_attempts}"
                        )

                    return result

                except retryable_exceptions as e:
                    last_exception = e

                    # Check if we have more attempts
                    if attempt < max_attempts - 1:
                        # Calculate delay
                        delay = exponential_backoff(
                            attempt,
                            initial_delay,
                            max_delay,
                            exponential_base,
                            jitter,
                        )

                        # Log retry
                        logger.warning(
                            f"🔄 {func.__name__} failed (attempt {attempt + 1}/{max_attempts}): {e}\n"
                            f"   Retrying in {delay:.2f}s..."
                        )

                        # Call on_retry callback if provided
                        if on_retry:
                            try:
                                on_retry(e, attempt + 1)
                            except Exception as callback_error:
                                logger.error(f"on_retry callback failed: {callback_error}")

                        # Wait before retry
                        time.sleep(delay)

                    else:
                        # All retries exhausted
                        logger.error(
                            f"❌ {func.__name__} failed after {max_attempts} attempts: {e}"
                        )

                        # Call on_failure callback if provided
                        if on_failure:
                            try:
                                on_failure(e, max_attempts)
                            except Exception as callback_error:
                                logger.error(f"on_failure callback failed: {callback_error}")

            # Raise the last exception
            raise last_exception

        return wrapper

    return decorator


class RetryStrategy:
    """
    Retry strategy with detailed configuration and state tracking
    """

    def __init__(self, config: RetryConfig):
        """
        Initialize retry strategy

        Args:
            config: Retry configuration
        """
        self.config = config
        self.reset()

    def reset(self):
        """Reset retry state"""
        self.attempt = 0
        self.total_delay = 0.0
        self.exceptions: List[Exception] = []

    def should_retry(self, exception: Exception) -> bool:
        """
        Check if should retry

        Args:
            exception: Exception that occurred

        Returns:
            True if should retry
        """
        # Check if exception is retryable
        if not isinstance(exception, self.config.retryable_exceptions):
            return False

        # Check if have attempts left
        if self.attempt >= self.config.max_attempts:
            return False

        return True

    def get_next_delay(self) -> float:
        """
        Get delay for next retry

        Returns:
            Delay in seconds
        """
        delay = exponential_backoff(
            self.attempt,
            self.config.initial_delay,
            self.config.max_delay,
            self.config.exponential_base,
            self.config.jitter,
        )

        return delay

    def record_attempt(self, exception: Exception) -> Tuple[bool, Optional[float]]:
        """
        Record attempt and determine if should retry

        Args:
            exception: Exception that occurred

        Returns:
            Tuple of (should_retry, delay_seconds)
        """
        self.attempt += 1
        self.exceptions.append(exception)

        if self.should_retry(exception):
            delay = self.get_next_delay()
            self.total_delay += delay
            return True, delay
        else:
            return False, None

    def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function with retry logic

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Last exception if all retries exhausted
        """
        self.reset()

        while True:
            try:
                result = func(*args, **kwargs)
                return result

            except Exception as e:
                should_retry, delay = self.record_attempt(e)

                if should_retry:
                    logger.warning(
                        f"Retry {self.attempt}/{self.config.max_attempts}: {e}\n"
                        f"Waiting {delay:.2f}s..."
                    )

                    # Callback
                    if self.config.on_retry:
                        self.config.on_retry(e, self.attempt)

                    # Wait
                    time.sleep(delay)

                else:
                    # All retries exhausted or non-retryable exception
                    if self.config.on_failure:
                        self.config.on_failure(e, self.attempt)

                    raise


def retry_on_exception(
    exception_types: Tuple[Type[Exception], ...] = (Exception,),
    max_attempts: int = 3,
    delay: float = 1.0,
):
    """
    Simple retry decorator for specific exceptions

    Args:
        exception_types: Exceptions to retry on
        max_attempts: Maximum attempts
        delay: Fixed delay between retries

    Returns:
        Decorated function

    Examples:
        @retry_on_exception((ConnectionError,), max_attempts=5, delay=2.0)
        def connect_to_server():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exception_types as e:
                    if attempt < max_attempts - 1:
                        logger.warning(f"Retry {attempt + 1}/{max_attempts}: {e}")
                        time.sleep(delay)
                    else:
                        raise
            # This should never be reached
            raise RuntimeError("Unexpected retry exhaustion")

        return wrapper

    return decorator


def retry_async_with_backoff(
    config: Optional[RetryConfig] = None,
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: float = 0.1,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """
    Async version of retry_with_backoff

    Args:
        config: RetryConfig object
        max_attempts: Maximum retry attempts
        initial_delay: Initial delay
        max_delay: Maximum delay
        exponential_base: Exponential base
        jitter: Jitter factor
        retryable_exceptions: Exceptions to retry

    Returns:
        Decorated async function

    Examples:
        @retry_async_with_backoff(max_attempts=3)
        async def async_operation():
            ...
    """
    import asyncio

    # Use config if provided
    if config:
        max_attempts = config.max_attempts
        initial_delay = config.initial_delay
        max_delay = config.max_delay
        exponential_base = config.exponential_base
        jitter = config.jitter
        retryable_exceptions = config.retryable_exceptions

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    result = await func(*args, **kwargs)

                    if attempt > 0:
                        logger.info(
                            f"✅ {func.__name__} succeeded on attempt {attempt + 1}/{max_attempts}"
                        )

                    return result

                except retryable_exceptions as e:
                    last_exception = e

                    if attempt < max_attempts - 1:
                        delay = exponential_backoff(
                            attempt,
                            initial_delay,
                            max_delay,
                            exponential_base,
                            jitter,
                        )

                        logger.warning(
                            f"🔄 {func.__name__} failed (attempt {attempt + 1}/{max_attempts}): {e}\n"
                            f"   Retrying in {delay:.2f}s..."
                        )

                        await asyncio.sleep(delay)

                    else:
                        logger.error(
                            f"❌ {func.__name__} failed after {max_attempts} attempts: {e}"
                        )

            raise last_exception

        return wrapper

    return decorator
