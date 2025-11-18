"""
Circuit Breaker Pattern
Prevents cascading failures by failing fast when services are unavailable
"""
import time
from typing import Callable, Optional, Any
from functools import wraps
from enum import Enum
from dataclasses import dataclass
from threading import Lock

from loguru import logger


class CircuitState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing fast
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5  # Failures before opening
    recovery_timeout: int = 60  # Seconds before attempting recovery
    expected_exception: type = Exception  # Exception type to catch
    success_threshold: int = 2  # Successes in half-open before closing


class CircuitBreaker:
    """
    Circuit breaker implementation

    Prevents cascading failures by:
    1. Tracking failure rate
    2. Opening circuit after threshold
    3. Failing fast while open
    4. Testing recovery in half-open state
    5. Closing circuit when service recovers

    Usage:
        breaker = CircuitBreaker("external_api", failure_threshold=3)

        @breaker.protected
        def call_external_api():
            # ... API call ...
            return response
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
        expected_exception: type = Exception
    ):
        """
        Initialize circuit breaker

        Args:
            name: Circuit breaker name (for logging)
            failure_threshold: Number of failures before opening
            recovery_timeout: Seconds to wait before attempting recovery
            success_threshold: Successes needed in half-open to close
            expected_exception: Exception type to catch
        """
        self.name = name
        self.config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
            success_threshold=success_threshold
        )

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self._lock = Lock()

        logger.info(
            f"Circuit breaker initialized: {name}",
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call function with circuit breaker protection

        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitOpenError: If circuit is open
            Exception: If function raises exception
        """
        with self._lock:
            # Check circuit state
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    logger.info(f"Circuit {self.name}: Entering half-open state")
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                else:
                    raise CircuitOpenError(
                        f"Circuit breaker {self.name} is OPEN",
                        circuit_name=self.name,
                        last_failure_time=self.last_failure_time,
                        failure_count=self.failure_count
                    )

        # Attempt to call function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except self.config.expected_exception as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True

        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.config.recovery_timeout

    def _on_success(self):
        """Handle successful call"""
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1

                if self.success_count >= self.config.success_threshold:
                    logger.info(
                        f"Circuit {self.name}: Closing (recovered)",
                        success_count=self.success_count
                    )
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0

            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                if self.failure_count > 0:
                    self.failure_count = 0

    def _on_failure(self):
        """Handle failed call"""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                logger.warning(
                    f"Circuit {self.name}: Opening (recovery failed)",
                    failure_count=self.failure_count
                )
                self.state = CircuitState.OPEN
                self.success_count = 0

            elif self.state == CircuitState.CLOSED:
                if self.failure_count >= self.config.failure_threshold:
                    logger.error(
                        f"Circuit {self.name}: Opening (threshold reached)",
                        failure_count=self.failure_count,
                        threshold=self.config.failure_threshold
                    )
                    self.state = CircuitState.OPEN

    def protected(self, func: Callable) -> Callable:
        """
        Decorator for circuit breaker protection

        Usage:
            @breaker.protected
            def call_api():
                return response
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper

    def get_status(self) -> dict:
        """Get current circuit breaker status"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold
            }
        }

    def reset(self):
        """Manually reset circuit breaker to closed state"""
        with self._lock:
            logger.info(f"Circuit {self.name}: Manual reset")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = None


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open"""

    def __init__(
        self,
        message: str,
        circuit_name: str,
        last_failure_time: Optional[float],
        failure_count: int
    ):
        super().__init__(message)
        self.circuit_name = circuit_name
        self.last_failure_time = last_failure_time
        self.failure_count = failure_count


# Global circuit breaker registry
_circuit_breakers: dict[str, CircuitBreaker] = {}
_registry_lock = Lock()


def get_circuit_breaker(
    name: str,
    **kwargs
) -> CircuitBreaker:
    """
    Get or create circuit breaker

    Args:
        name: Circuit breaker name
        **kwargs: CircuitBreaker constructor arguments

    Returns:
        CircuitBreaker instance
    """
    with _registry_lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = CircuitBreaker(name, **kwargs)
        return _circuit_breakers[name]


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type = Exception
):
    """
    Decorator for circuit breaker protection

    Usage:
        @circuit_breaker("external_api", failure_threshold=3, recovery_timeout=30)
        def call_api():
            # ... API call ...
            return response

    Args:
        name: Circuit breaker name
        failure_threshold: Failures before opening
        recovery_timeout: Seconds before recovery attempt
        expected_exception: Exception type to catch
    """
    def decorator(func: Callable):
        breaker = get_circuit_breaker(
            name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception
        )

        @wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)

        return wrapper
    return decorator


# Async circuit breaker support
class AsyncCircuitBreaker(CircuitBreaker):
    """Async version of circuit breaker"""

    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call async function with circuit breaker protection

        Args:
            func: Async function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitOpenError: If circuit is open
        """
        # Check state (synchronous)
        with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    logger.info(f"Circuit {self.name}: Entering half-open state")
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                else:
                    raise CircuitOpenError(
                        f"Circuit breaker {self.name} is OPEN",
                        circuit_name=self.name,
                        last_failure_time=self.last_failure_time,
                        failure_count=self.failure_count
                    )

        # Attempt async call
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result

        except self.config.expected_exception as e:
            self._on_failure()
            raise

    def protected_async(self, func: Callable) -> Callable:
        """
        Decorator for async circuit breaker protection

        Usage:
            @breaker.protected_async
            async def call_api():
                return response
        """
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await self.call_async(func, *args, **kwargs)
        return wrapper


def async_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type = Exception
):
    """
    Decorator for async circuit breaker protection

    Usage:
        @async_circuit_breaker("llm_api", failure_threshold=3)
        async def call_llm(prompt: str):
            # ... LLM API call ...
            return response
    """
    def decorator(func: Callable):
        with _registry_lock:
            if name not in _circuit_breakers:
                _circuit_breakers[name] = AsyncCircuitBreaker(
                    name,
                    failure_threshold=failure_threshold,
                    recovery_timeout=recovery_timeout,
                    expected_exception=expected_exception
                )
            breaker = _circuit_breakers[name]

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await breaker.call_async(func, *args, **kwargs)

        return wrapper
    return decorator


def get_all_circuit_breakers() -> dict[str, dict]:
    """Get status of all circuit breakers"""
    with _registry_lock:
        return {
            name: breaker.get_status()
            for name, breaker in _circuit_breakers.items()
        }


def reset_all_circuit_breakers():
    """Reset all circuit breakers (for testing/recovery)"""
    with _registry_lock:
        for breaker in _circuit_breakers.values():
            breaker.reset()
        logger.info(f"Reset {len(_circuit_breakers)} circuit breakers")
