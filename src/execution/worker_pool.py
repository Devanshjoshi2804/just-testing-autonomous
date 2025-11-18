"""
Worker Pool for Parallel Test Execution
Manages concurrent workers with rate limiting and backpressure
"""
import asyncio
from typing import List, Callable, Any, Optional, Dict, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger
import time


@dataclass
class WorkerStats:
    """Statistics for a worker"""
    worker_id: int
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_duration: float = 0.0
    average_duration: float = 0.0
    last_task_at: Optional[datetime] = None


@dataclass
class PoolStats:
    """Statistics for the entire worker pool"""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    active_workers: int = 0
    idle_workers: int = 0
    queue_size: int = 0
    total_duration: float = 0.0
    average_task_duration: float = 0.0
    throughput: float = 0.0  # tasks per second
    worker_stats: Dict[int, WorkerStats] = field(default_factory=dict)


class WorkerPool:
    """
    Async worker pool for parallel task execution

    Features:
    - Configurable number of workers
    - Rate limiting (max tasks per second)
    - Backpressure handling
    - Task timeout support
    - Comprehensive statistics
    - Graceful shutdown
    """

    def __init__(
        self,
        num_workers: int = 10,
        max_queue_size: int = 1000,
        rate_limit: Optional[float] = None,  # tasks per second
        task_timeout: Optional[float] = 300.0,  # 5 minutes default
        enable_stats: bool = True
    ):
        """
        Initialize worker pool

        Args:
            num_workers: Number of concurrent workers
            max_queue_size: Maximum queue size (for backpressure)
            rate_limit: Maximum tasks per second (None = unlimited)
            task_timeout: Timeout per task in seconds
            enable_stats: Whether to track statistics
        """
        self.num_workers = num_workers
        self.max_queue_size = max_queue_size
        self.rate_limit = rate_limit
        self.task_timeout = task_timeout
        self.enable_stats = enable_stats

        # Task queue
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)

        # Worker management
        self.workers: List[asyncio.Task] = []
        self.running = False

        # Rate limiting
        self.rate_limiter: Optional[asyncio.Semaphore] = None
        self.last_execution_time = 0.0

        # Statistics
        self.stats = PoolStats()
        self.start_time: Optional[float] = None

        logger.info(
            f"Initialized WorkerPool: {num_workers} workers, "
            f"queue_size={max_queue_size}, rate_limit={rate_limit}"
        )

    async def start(self):
        """Start the worker pool"""
        if self.running:
            logger.warning("Worker pool already running")
            return

        self.running = True
        self.start_time = time.time()

        # Create rate limiter if needed
        if self.rate_limit:
            # Convert rate limit to tokens per batch
            self.rate_limiter = asyncio.Semaphore(int(self.rate_limit))

        # Start workers
        for i in range(self.num_workers):
            worker = asyncio.create_task(self._worker(i))
            self.workers.append(worker)

            if self.enable_stats:
                self.stats.worker_stats[i] = WorkerStats(worker_id=i)

        self.stats.active_workers = self.num_workers

        logger.info(f"Started {self.num_workers} workers")

    async def stop(self, wait_for_completion: bool = True):
        """
        Stop the worker pool

        Args:
            wait_for_completion: Whether to wait for pending tasks
        """
        if not self.running:
            return

        logger.info("Stopping worker pool...")

        self.running = False

        if wait_for_completion:
            # Wait for queue to empty
            await self.queue.join()

        # Cancel all workers
        for worker in self.workers:
            worker.cancel()

        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)

        self.workers.clear()
        self.stats.active_workers = 0

        logger.info("Worker pool stopped")

    async def submit(
        self,
        func: Callable[..., Coroutine],
        *args,
        **kwargs
    ) -> Any:
        """
        Submit a task to the worker pool and wait for result

        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result from the function execution

        Raises:
            asyncio.QueueFull: If queue is full (backpressure)
        """
        if not self.running:
            raise RuntimeError("Worker pool not running. Call start() first.")

        # Create a future to capture the result
        future = asyncio.Future()

        task = {
            'func': func,
            'args': args,
            'kwargs': kwargs,
            'submitted_at': time.time(),
            'future': future
        }

        # Apply rate limiting
        if self.rate_limit:
            await self._apply_rate_limit()

        # Add to queue (blocks if full - backpressure)
        await self.queue.put(task)

        if self.enable_stats:
            self.stats.total_tasks += 1
            self.stats.queue_size = self.queue.qsize()

        # Wait for and return the result
        return await future

    async def submit_batch(
        self,
        tasks: List[tuple]
    ) -> List[Any]:
        """
        Submit multiple tasks at once and wait for all results

        Args:
            tasks: List of (func, args, kwargs) tuples

        Returns:
            List of results from all tasks
        """
        futures = []
        for task_data in tasks:
            func = task_data[0]
            args = task_data[1] if len(task_data) > 1 else ()
            kwargs = task_data[2] if len(task_data) > 2 else {}

            future = asyncio.create_task(self.submit(func, *args, **kwargs))
            futures.append(future)

        # Wait for all tasks to complete
        results = await asyncio.gather(*futures)
        return results

    async def _worker(self, worker_id: int):
        """
        Worker coroutine

        Args:
            worker_id: Unique worker identifier
        """
        logger.debug(f"Worker {worker_id} started")

        while self.running:
            try:
                # Get task from queue (with timeout to check running flag)
                try:
                    task = await asyncio.wait_for(
                        self.queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Update stats
                if self.enable_stats:
                    self.stats.idle_workers -= 1
                    self.stats.queue_size = self.queue.qsize()

                # Execute task
                start_time = time.time()
                success = False
                result = None
                error = None

                try:
                    func = task['func']
                    args = task['args']
                    kwargs = task['kwargs']
                    future = task.get('future')

                    # Execute with timeout
                    if self.task_timeout:
                        result = await asyncio.wait_for(
                            func(*args, **kwargs),
                            timeout=self.task_timeout
                        )
                    else:
                        result = await func(*args, **kwargs)

                    success = True

                    # Set result on future if present
                    if future and not future.done():
                        future.set_result(result)

                except asyncio.TimeoutError as e:
                    error = e
                    logger.error(
                        f"Worker {worker_id} task timeout after {self.task_timeout}s"
                    )
                    # Set exception on future if present
                    if future and not future.done():
                        future.set_exception(e)

                except Exception as e:
                    error = e
                    logger.error(f"Worker {worker_id} task failed: {e}")
                    # Set exception on future if present
                    if future and not future.done():
                        future.set_exception(e)

                finally:
                    # Update statistics
                    duration = time.time() - start_time

                    if self.enable_stats:
                        worker_stats = self.stats.worker_stats[worker_id]
                        worker_stats.last_task_at = datetime.now()
                        worker_stats.total_duration += duration

                        if success:
                            worker_stats.tasks_completed += 1
                            self.stats.completed_tasks += 1
                        else:
                            worker_stats.tasks_failed += 1
                            self.stats.failed_tasks += 1

                        # Update average
                        total_tasks = worker_stats.tasks_completed + worker_stats.tasks_failed
                        if total_tasks > 0:
                            worker_stats.average_duration = (
                                worker_stats.total_duration / total_tasks
                            )

                        # Update pool stats
                        self.stats.total_duration += duration
                        completed = self.stats.completed_tasks + self.stats.failed_tasks
                        if completed > 0:
                            self.stats.average_task_duration = (
                                self.stats.total_duration / completed
                            )

                        # Calculate throughput
                        if self.start_time:
                            elapsed = time.time() - self.start_time
                            if elapsed > 0:
                                self.stats.throughput = completed / elapsed

                        self.stats.idle_workers += 1

                    # Mark task as done
                    self.queue.task_done()

            except asyncio.CancelledError:
                logger.debug(f"Worker {worker_id} cancelled")
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} unexpected error: {e}")

        logger.debug(f"Worker {worker_id} stopped")

    async def _apply_rate_limit(self):
        """Apply rate limiting using token bucket algorithm"""
        if not self.rate_limit:
            return

        current_time = time.time()
        time_since_last = current_time - self.last_execution_time

        # Calculate minimum time between tasks
        min_interval = 1.0 / self.rate_limit

        if time_since_last < min_interval:
            # Need to wait
            wait_time = min_interval - time_since_last
            await asyncio.sleep(wait_time)

        self.last_execution_time = time.time()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get current pool statistics

        Returns:
            Dictionary with pool statistics
        """
        return {
            'total_submitted': self.stats.total_tasks,
            'total_completed': self.stats.completed_tasks,
            'total_failed': self.stats.failed_tasks,
            'active_workers': self.stats.active_workers,
            'idle_workers': self.stats.idle_workers,
            'queue_size': self.stats.queue_size,
            'total_duration': self.stats.total_duration,
            'average_task_duration': self.stats.average_task_duration,
            'throughput': self.stats.throughput
        }

    def is_running(self) -> bool:
        """Check if pool is running"""
        return self.running

    def is_idle(self) -> bool:
        """Check if pool is idle (no pending tasks)"""
        return self.queue.qsize() == 0 and self.stats.idle_workers == self.num_workers

    async def wait_idle(self, timeout: Optional[float] = None):
        """
        Wait for pool to become idle

        Args:
            timeout: Maximum time to wait (None = wait forever)

        Raises:
            asyncio.TimeoutError: If timeout exceeded
        """
        start_time = time.time()

        while not self.is_idle():
            await asyncio.sleep(0.1)

            if timeout and (time.time() - start_time) > timeout:
                raise asyncio.TimeoutError("Timeout waiting for pool to become idle")

    async def __aenter__(self):
        """Context manager entry"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.stop(wait_for_completion=True)
