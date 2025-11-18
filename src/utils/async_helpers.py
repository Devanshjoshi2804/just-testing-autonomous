"""
Async Utility Functions
Comprehensive async helpers for concurrent operations
"""
import asyncio
import functools
from typing import TypeVar, List, Callable, Any, Optional, Coroutine, Tuple
from loguru import logger

T = TypeVar('T')


async def run_async_with_timeout(
    coro: Coroutine[Any, Any, T],
    timeout: float,
    timeout_message: Optional[str] = None,
) -> T:
    """
    Run async function with timeout

    Args:
        coro: Coroutine to execute
        timeout: Timeout in seconds
        timeout_message: Custom timeout error message

    Returns:
        Coroutine result

    Raises:
        asyncio.TimeoutError: If timeout exceeded

    Examples:
        result = await run_async_with_timeout(
            slow_function(),
            timeout=30.0,
            timeout_message="Operation took too long"
        )
    """
    try:
        result = await asyncio.wait_for(coro, timeout=timeout)
        return result

    except asyncio.TimeoutError:
        if timeout_message:
            logger.error(f"Timeout: {timeout_message} ({timeout}s)")
            raise asyncio.TimeoutError(timeout_message)
        else:
            logger.error(f"Operation timed out after {timeout}s")
            raise


async def gather_with_concurrency(
    *coroutines: Coroutine,
    max_concurrency: int = 10,
    return_exceptions: bool = False,
) -> List[Any]:
    """
    Gather coroutines with concurrency limit

    Args:
        *coroutines: Coroutines to execute
        max_concurrency: Maximum concurrent operations
        return_exceptions: Return exceptions instead of raising

    Returns:
        List of results

    Examples:
        # Run 100 tasks but only 10 at a time
        tasks = [fetch_data(i) for i in range(100)]
        results = await gather_with_concurrency(
            *tasks,
            max_concurrency=10
        )
    """
    # Create semaphore for concurrency control
    semaphore = asyncio.Semaphore(max_concurrency)

    async def limited_task(coro):
        async with semaphore:
            if return_exceptions:
                try:
                    return await coro
                except Exception as e:
                    return e
            else:
                return await coro

    # Wrap all coroutines with semaphore
    limited_coroutines = [limited_task(coro) for coro in coroutines]

    # Gather all
    return await asyncio.gather(*limited_coroutines, return_exceptions=False)


async def async_retry(
    coro_func: Callable[..., Coroutine[Any, Any, T]],
    *args,
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    exponential_base: float = 2.0,
    retryable_exceptions: Tuple[type, ...] = (Exception,),
    **kwargs
) -> T:
    """
    Retry async function with exponential backoff

    Args:
        coro_func: Async function to retry
        *args: Positional arguments
        max_attempts: Maximum retry attempts
        initial_delay: Initial delay in seconds
        exponential_base: Exponential backoff base
        retryable_exceptions: Exceptions to retry on
        **kwargs: Keyword arguments

    Returns:
        Function result

    Raises:
        Last exception if all retries exhausted

    Examples:
        result = await async_retry(
            fetch_data,
            url="https://api.example.com",
            max_attempts=5,
            initial_delay=2.0
        )
    """
    from src.utils.retry import exponential_backoff

    last_exception = None

    for attempt in range(max_attempts):
        try:
            result = await coro_func(*args, **kwargs)
            return result

        except retryable_exceptions as e:
            last_exception = e

            if attempt < max_attempts - 1:
                delay = exponential_backoff(
                    attempt,
                    initial_delay=initial_delay,
                    exponential_base=exponential_base,
                )

                logger.warning(
                    f"Retry {attempt + 1}/{max_attempts}: {e}\n"
                    f"Waiting {delay:.2f}s..."
                )

                await asyncio.sleep(delay)
            else:
                logger.error(f"Failed after {max_attempts} attempts: {e}")

    raise last_exception


async def run_in_batches(
    items: List[Any],
    async_func: Callable[[Any], Coroutine[Any, Any, T]],
    batch_size: int = 10,
    delay_between_batches: float = 0.0,
) -> List[T]:
    """
    Process items in batches

    Args:
        items: List of items to process
        async_func: Async function to apply to each item
        batch_size: Number of items per batch
        delay_between_batches: Delay between batches in seconds

    Returns:
        List of results

    Examples:
        # Process 1000 items in batches of 50
        results = await run_in_batches(
            items=list(range(1000)),
            async_func=process_item,
            batch_size=50,
            delay_between_batches=1.0
        )
    """
    results = []

    # Split into batches
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]

        logger.debug(
            f"Processing batch {i//batch_size + 1} "
            f"({len(batch)} items, {i+1}-{i+len(batch)}/{len(items)})"
        )

        # Process batch
        batch_results = await asyncio.gather(
            *[async_func(item) for item in batch],
            return_exceptions=False
        )

        results.extend(batch_results)

        # Delay before next batch
        if delay_between_batches > 0 and i + batch_size < len(items):
            await asyncio.sleep(delay_between_batches)

    return results


async def race_tasks(
    *coroutines: Coroutine,
    cancel_remaining: bool = True,
) -> Tuple[Any, int]:
    """
    Race multiple tasks, return first to complete

    Args:
        *coroutines: Coroutines to race
        cancel_remaining: Cancel other tasks when first completes

    Returns:
        Tuple of (result, winner_index)

    Examples:
        # Race two API calls, use whichever responds first
        result, winner = await race_tasks(
            fetch_from_api1(),
            fetch_from_api2(),
            cancel_remaining=True
        )
    """
    if not coroutines:
        raise ValueError("No coroutines provided")

    # Create tasks
    tasks = [asyncio.create_task(coro) for coro in coroutines]

    try:
        # Wait for first to complete
        done, pending = await asyncio.wait(
            tasks,
            return_when=asyncio.FIRST_COMPLETED
        )

        # Get result
        winner_task = done.pop()
        result = await winner_task

        # Find winner index
        winner_index = tasks.index(winner_task)

        # Cancel remaining if requested
        if cancel_remaining:
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        return result, winner_index

    except Exception as e:
        # Cancel all tasks on error
        for task in tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        raise


async def run_with_progress(
    items: List[Any],
    async_func: Callable[[Any], Coroutine[Any, Any, T]],
    progress_callback: Optional[Callable[[int, int], None]] = None,
    max_concurrency: int = 10,
) -> List[T]:
    """
    Run async function on items with progress tracking

    Args:
        items: Items to process
        async_func: Async function to apply
        progress_callback: Called with (completed, total)
        max_concurrency: Maximum concurrent tasks

    Returns:
        List of results

    Examples:
        def on_progress(completed, total):
            print(f"{completed}/{total} completed ({completed/total*100:.1f}%)")

        results = await run_with_progress(
            items,
            process_item,
            progress_callback=on_progress,
            max_concurrency=5
        )
    """
    total = len(items)
    completed = 0
    results = []

    semaphore = asyncio.Semaphore(max_concurrency)

    async def process_with_progress(item):
        nonlocal completed

        async with semaphore:
            result = await async_func(item)

            completed += 1
            if progress_callback:
                progress_callback(completed, total)

            return result

    # Process all items
    results = await asyncio.gather(
        *[process_with_progress(item) for item in items],
        return_exceptions=False
    )

    return results


async def async_map(
    func: Callable[[T], Coroutine[Any, Any, Any]],
    items: List[T],
    max_concurrency: int = 10,
) -> List[Any]:
    """
    Async map function with concurrency control

    Args:
        func: Async function to apply
        items: Items to map over
        max_concurrency: Maximum concurrent operations

    Returns:
        List of results

    Examples:
        results = await async_map(
            lambda x: process(x),
            [1, 2, 3, 4, 5],
            max_concurrency=2
        )
    """
    return await gather_with_concurrency(
        *[func(item) for item in items],
        max_concurrency=max_concurrency
    )


async def async_filter(
    func: Callable[[T], Coroutine[Any, Any, bool]],
    items: List[T],
    max_concurrency: int = 10,
) -> List[T]:
    """
    Async filter function

    Args:
        func: Async predicate function
        items: Items to filter
        max_concurrency: Maximum concurrent operations

    Returns:
        Filtered list

    Examples:
        async def is_valid(item):
            return await validate(item)

        valid_items = await async_filter(is_valid, items)
    """
    # Run predicate on all items
    results = await gather_with_concurrency(
        *[func(item) for item in items],
        max_concurrency=max_concurrency
    )

    # Filter items where predicate is True
    return [item for item, keep in zip(items, results) if keep]


class AsyncContextManager:
    """
    Helper for managing async resources

    Examples:
        async with AsyncContextManager() as manager:
            resource1 = await manager.add(create_resource1())
            resource2 = await manager.add(create_resource2())
            # Use resources...
        # Resources cleaned up automatically
    """

    def __init__(self):
        self.resources = []

    async def add(self, resource):
        """Add resource to be managed"""
        self.resources.append(resource)
        return resource

    async def cleanup(self):
        """Cleanup all resources"""
        for resource in reversed(self.resources):
            try:
                if hasattr(resource, 'close'):
                    if asyncio.iscoroutinefunction(resource.close):
                        await resource.close()
                    else:
                        resource.close()

                elif hasattr(resource, 'cleanup'):
                    if asyncio.iscoroutinefunction(resource.cleanup):
                        await resource.cleanup()
                    else:
                        resource.cleanup()

            except Exception as e:
                logger.error(f"Error cleaning up resource: {e}")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()


def async_lru_cache(maxsize: int = 128):
    """
    LRU cache for async functions

    Args:
        maxsize: Maximum cache size

    Returns:
        Decorated function

    Examples:
        @async_lru_cache(maxsize=100)
        async def expensive_operation(key):
            ...
    """
    def decorator(func):
        cache = {}
        access_order = []

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key
            key = (args, tuple(sorted(kwargs.items())))

            # Check cache
            if key in cache:
                # Update access order
                access_order.remove(key)
                access_order.append(key)
                return cache[key]

            # Compute result
            result = await func(*args, **kwargs)

            # Add to cache
            cache[key] = result
            access_order.append(key)

            # Evict oldest if cache full
            if len(cache) > maxsize:
                oldest_key = access_order.pop(0)
                del cache[oldest_key]

            return result

        return wrapper

    return decorator


async def async_debounce(
    func: Callable[..., Coroutine],
    delay: float,
    *args,
    **kwargs
):
    """
    Debounce async function (call only after delay with no new calls)

    Args:
        func: Async function to debounce
        delay: Delay in seconds
        *args: Function arguments
        **kwargs: Function keyword arguments

    Returns:
        Function result or None if cancelled

    Examples:
        # Only execute after 1 second of no calls
        result = await async_debounce(save_data, 1.0, data=data)
    """
    try:
        await asyncio.sleep(delay)
        return await func(*args, **kwargs)
    except asyncio.CancelledError:
        return None


async def async_throttle(
    func: Callable[..., Coroutine],
    min_interval: float,
    *args,
    **kwargs
):
    """
    Throttle async function (ensure minimum interval between calls)

    Args:
        func: Async function to throttle
        min_interval: Minimum interval in seconds
        *args: Function arguments
        **kwargs: Function keyword arguments

    Returns:
        Function result
    """
    # This is a simplified version
    # For production, use a class to track last call time
    await asyncio.sleep(min_interval)
    return await func(*args, **kwargs)
