"""
Parallel Test Executor
Orchestrates parallel test execution using worker pool, task queue, and result aggregation
"""
import asyncio
from typing import List, Dict, Any, Optional, Callable
from loguru import logger

from src.execution.worker_pool import WorkerPool
from src.execution.task_queue import TaskQueue, TaskPriority
from src.execution.result_aggregator import ResultAggregator, TestResult


class ParallelTestExecutor:
    """
    Orchestrates parallel test execution

    Features:
    - Concurrent test execution with worker pool
    - Priority-based task scheduling
    - Automatic retries on failure
    - Real-time result aggregation
    - Rate limiting and backpressure handling
    - Comprehensive statistics and reporting
    """

    def __init__(
        self,
        num_workers: int = 10,
        max_queue_size: int = 1000,
        rate_limit: Optional[float] = None,
        task_timeout: float = 300.0,
        enable_retries: bool = True,
        max_retries: int = 3
    ):
        """
        Initialize parallel test executor

        Args:
            num_workers: Number of concurrent workers
            max_queue_size: Maximum task queue size
            rate_limit: Maximum tasks per second (None = unlimited)
            task_timeout: Timeout per task in seconds
            enable_retries: Whether to retry failed tests
            max_retries: Maximum number of retries per test
        """
        self.num_workers = num_workers
        self.rate_limit = rate_limit
        self.task_timeout = task_timeout

        # Initialize components
        self.worker_pool = WorkerPool(
            num_workers=num_workers,
            max_queue_size=max_queue_size,
            rate_limit=rate_limit,
            task_timeout=task_timeout
        )

        self.task_queue = TaskQueue(
            max_size=max_queue_size,
            enable_retries=enable_retries,
            default_max_retries=max_retries
        )

        self.result_aggregator = ResultAggregator()

        # State
        self.running = False

        logger.info(
            f"Initialized ParallelTestExecutor: "
            f"{num_workers} workers, rate_limit={rate_limit}"
        )

    async def execute_tests(
        self,
        test_functions: List[Dict[str, Any]],
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> Dict[str, Any]:
        """
        Execute tests in parallel

        Args:
            test_functions: List of test function dictionaries with keys:
                           - func: Callable (async test function)
                           - test_name: str
                           - endpoint_path: str
                           - endpoint_method: str
                           - test_type: str
                           - args: tuple (optional)
                           - kwargs: dict (optional)
                           - metadata: dict (optional)
            priority: Default priority for all tests

        Returns:
            Dictionary with execution results and statistics
        """
        if self.running:
            raise RuntimeError("Executor already running")

        self.running = True
        self.result_aggregator.start()

        logger.info(f"Starting parallel execution of {len(test_functions)} tests")

        try:
            # Start worker pool
            await self.worker_pool.start()

            # Submit all tests to task queue
            task_ids = []
            for test_func_data in test_functions:
                # Wrap test function to capture result
                test_id = await self._submit_test(test_func_data, priority)
                task_ids.append(test_id)

            logger.info(f"Submitted {len(task_ids)} tests to queue")

            # Start worker tasks
            worker_tasks = []
            for i in range(self.num_workers):
                task = asyncio.create_task(self._worker_loop(i))
                worker_tasks.append(task)

            # Wait for all tasks to complete
            await self.task_queue.wait_completion()

            # Cancel workers
            for task in worker_tasks:
                task.cancel()

            await asyncio.gather(*worker_tasks, return_exceptions=True)

            # Stop worker pool
            await self.worker_pool.stop(wait_for_completion=False)

            # Complete aggregation
            self.result_aggregator.complete()

            # Get results
            aggregated = self.result_aggregator.get_aggregated_results()
            summary = self.result_aggregator.get_summary()

            logger.info(
                f"Execution complete: {aggregated.passed_tests}/{aggregated.total_tests} "
                f"passed ({aggregated.success_rate:.2f}%)"
            )

            return {
                'success': True,
                'summary': summary,
                'aggregated_results': aggregated,
                'task_ids': task_ids,
                'worker_stats': self.worker_pool.get_stats(),
                'queue_stats': self.task_queue.get_statistics()
            }

        except Exception as e:
            logger.error(f"Execution failed: {e}")
            raise

        finally:
            self.running = False

    async def _submit_test(
        self,
        test_func_data: Dict[str, Any],
        priority: TaskPriority
    ) -> str:
        """
        Submit a test to the task queue

        Args:
            test_func_data: Test function data
            priority: Task priority

        Returns:
            Task ID
        """
        func = test_func_data['func']
        test_name = test_func_data['test_name']
        endpoint_path = test_func_data['endpoint_path']
        endpoint_method = test_func_data['endpoint_method']
        test_type = test_func_data['test_type']
        args = test_func_data.get('args', ())
        kwargs = test_func_data.get('kwargs', {})
        metadata = test_func_data.get('metadata', {})

        # Add test metadata
        metadata.update({
            'test_name': test_name,
            'endpoint_path': endpoint_path,
            'endpoint_method': endpoint_method,
            'test_type': test_type
        })

        # Submit to task queue
        task_id = await self.task_queue.add_task(
            func,
            *args,
            priority=priority,
            metadata=metadata,
            **kwargs
        )

        return task_id

    async def _worker_loop(self, worker_id: int):
        """
        Worker loop for processing tasks

        Args:
            worker_id: Worker identifier
        """
        logger.debug(f"Worker {worker_id} loop started")

        while True:
            try:
                # Get next task from queue
                task = await self.task_queue.get_task(timeout=1.0)

                if task is None:
                    # Check if queue is empty and we're done
                    if self.task_queue.is_empty():
                        break
                    continue

                # Execute task
                try:
                    # Execute test function
                    result = await task.func(*task.args, **task.kwargs)

                    # Extract result data
                    test_result = TestResult(
                        test_id=task.id,
                        test_name=task.metadata.get('test_name', 'Unknown'),
                        endpoint_path=task.metadata.get('endpoint_path', ''),
                        endpoint_method=task.metadata.get('endpoint_method', ''),
                        test_type=task.metadata.get('test_type', 'unknown'),
                        success=result.get('success', False),
                        status_code=result.get('status_code'),
                        expected_status=result.get('expected_status'),
                        response_time_ms=result.get('response_time_ms'),
                        error_message=result.get('error_message'),
                        metadata=result.get('metadata', {})
                    )

                    # Add to aggregator
                    self.result_aggregator.add_result(test_result)

                    # Mark task complete
                    await self.task_queue.mark_complete(task.id, result)

                except Exception as e:
                    logger.error(f"Worker {worker_id} task {task.id} failed: {e}")

                    # Create failed result
                    test_result = TestResult(
                        test_id=task.id,
                        test_name=task.metadata.get('test_name', 'Unknown'),
                        endpoint_path=task.metadata.get('endpoint_path', ''),
                        endpoint_method=task.metadata.get('endpoint_method', ''),
                        test_type=task.metadata.get('test_type', 'unknown'),
                        success=False,
                        error_message=str(e)
                    )

                    self.result_aggregator.add_result(test_result)

                    # Mark task failed (will retry if enabled)
                    await self.task_queue.mark_failed(task.id, e)

            except asyncio.CancelledError:
                logger.debug(f"Worker {worker_id} cancelled")
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} unexpected error: {e}")

        logger.debug(f"Worker {worker_id} loop ended")

    def get_results(self) -> Dict[str, Any]:
        """
        Get current execution results

        Returns:
            Results dictionary
        """
        return {
            'summary': self.result_aggregator.get_summary(),
            'aggregated_results': self.result_aggregator.get_aggregated_results(),
            'worker_stats': self.worker_pool.get_stats(),
            'queue_stats': self.task_queue.get_statistics()
        }

    def get_failed_tests(self) -> List[TestResult]:
        """Get all failed tests"""
        return self.result_aggregator.get_failed_tests()

    def get_passed_tests(self) -> List[TestResult]:
        """Get all passed tests"""
        return self.result_aggregator.get_passed_tests()

    def is_running(self) -> bool:
        """Check if executor is running"""
        return self.running

    async def shutdown(self):
        """Shutdown executor gracefully"""
        if self.running:
            logger.info("Shutting down executor...")
            await self.worker_pool.stop(wait_for_completion=True)
            self.running = False
            logger.info("Executor shutdown complete")

    async def __aenter__(self):
        """Context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.shutdown()
