"""
Integration Tests for Parallel Execution System
Tests worker pool, task queue, result aggregation, and parallel executor
"""
import pytest
import asyncio
from typing import Dict, Any

from src.execution import (
    WorkerPool,
    TaskQueue,
    TaskPriority,
    ResultAggregator,
    TestResult,
    ParallelTestExecutor
)


# ============================================================================
# Worker Pool Tests
# ============================================================================

@pytest.mark.asyncio
class TestWorkerPool:
    """Test worker pool functionality"""

    async def test_worker_pool_initialization(self):
        """Test worker pool can be initialized with various configs"""
        pool = WorkerPool(num_workers=5, max_queue_size=100)
        assert pool.num_workers == 5
        assert pool.max_queue_size == 100
        assert not pool.running

    async def test_worker_pool_start_stop(self):
        """Test worker pool can start and stop gracefully"""
        pool = WorkerPool(num_workers=3)

        await pool.start()
        assert pool.running
        assert len(pool.workers) == 3

        await pool.stop()
        assert not pool.running
        assert len(pool.workers) == 0

    async def test_worker_pool_submit_task(self):
        """Test submitting and executing a single task"""
        pool = WorkerPool(num_workers=2)
        await pool.start()

        async def test_func(x: int) -> int:
            return x * 2

        try:
            result = await pool.submit(test_func, 5)
            assert result == 10
        finally:
            await pool.stop()

    async def test_worker_pool_batch_submit(self):
        """Test submitting multiple tasks in batch"""
        pool = WorkerPool(num_workers=4)
        await pool.start()

        async def square(x: int) -> int:
            return x ** 2

        try:
            tasks = [(square, (i,)) for i in range(10)]
            results = await pool.submit_batch(tasks)

            assert len(results) == 10
            assert results[0] == 0
            assert results[5] == 25
            assert results[9] == 81
        finally:
            await pool.stop()

    async def test_worker_pool_task_timeout(self):
        """Test task timeout handling"""
        pool = WorkerPool(num_workers=2, task_timeout=0.5)
        await pool.start()

        async def slow_task():
            await asyncio.sleep(2)
            return "should timeout"

        try:
            with pytest.raises(asyncio.TimeoutError):
                await pool.submit(slow_task)
        finally:
            await pool.stop()

    async def test_worker_pool_statistics(self):
        """Test worker pool tracks statistics correctly"""
        pool = WorkerPool(num_workers=3)
        await pool.start()

        async def simple_task(x: int) -> int:
            return x + 1

        try:
            # Submit some tasks
            for i in range(10):
                await pool.submit(simple_task, i)

            stats = pool.get_stats()
            assert stats['total_submitted'] == 10
            assert stats['total_completed'] == 10
            assert stats['total_failed'] == 0
            assert stats['queue_size'] == 0
        finally:
            await pool.stop()

    async def test_worker_pool_context_manager(self):
        """Test worker pool works as async context manager"""
        async with WorkerPool(num_workers=2) as pool:
            async def test_func() -> str:
                return "context manager works"

            result = await pool.submit(test_func)
            assert result == "context manager works"


# ============================================================================
# Task Queue Tests
# ============================================================================

@pytest.mark.asyncio
class TestTaskQueue:
    """Test task queue functionality"""

    async def test_task_queue_initialization(self):
        """Test task queue initialization"""
        queue = TaskQueue(max_size=100, enable_retries=True, default_max_retries=3)
        assert queue.max_size == 100
        assert queue.enable_retries
        assert queue.default_max_retries == 3

    async def test_add_and_get_task(self):
        """Test adding and retrieving tasks"""
        queue = TaskQueue()

        async def test_func(x: int) -> int:
            return x * 2

        task_id = await queue.add_task(test_func, 5)
        assert task_id is not None

        task = await queue.get_task()
        assert task is not None
        assert task.id == task_id
        assert task.func == test_func
        assert task.args == (5,)

    async def test_task_priority_ordering(self):
        """Test tasks are retrieved by priority"""
        queue = TaskQueue()

        async def task_func(name: str) -> str:
            return name

        # Add tasks in random priority order
        low_id = await queue.add_task(task_func, "low", priority=TaskPriority.LOW)
        high_id = await queue.add_task(task_func, "high", priority=TaskPriority.HIGH)
        normal_id = await queue.add_task(task_func, "normal", priority=TaskPriority.NORMAL)
        critical_id = await queue.add_task(task_func, "critical", priority=TaskPriority.CRITICAL)

        # Should get tasks in priority order: CRITICAL > HIGH > NORMAL > LOW
        task1 = await queue.get_task()
        assert task1.id == critical_id

        task2 = await queue.get_task()
        assert task2.id == high_id

        task3 = await queue.get_task()
        assert task3.id == normal_id

        task4 = await queue.get_task()
        assert task4.id == low_id

    async def test_task_metadata(self):
        """Test task metadata is preserved"""
        queue = TaskQueue()

        async def test_func() -> str:
            return "test"

        metadata = {
            "test_name": "test_login",
            "endpoint_path": "/api/login",
            "test_type": "positive"
        }

        task_id = await queue.add_task(test_func, metadata=metadata)
        task = await queue.get_task()

        assert task.metadata == metadata
        assert task.metadata["test_name"] == "test_login"

    async def test_batch_add_tasks(self):
        """Test adding multiple tasks at once"""
        queue = TaskQueue()

        async def test_func(x: int) -> int:
            return x

        tasks = [
            {
                'func': test_func,
                'args': (i,),
                'kwargs': {},
                'priority': TaskPriority.NORMAL
            }
            for i in range(5)
        ]

        task_ids = await queue.add_tasks_batch(tasks)
        assert len(task_ids) == 5

        # All tasks should be retrievable
        for _ in range(5):
            task = await queue.get_task()
            assert task is not None


# ============================================================================
# Result Aggregator Tests
# ============================================================================

@pytest.mark.asyncio
class TestResultAggregator:
    """Test result aggregator functionality"""

    def test_aggregator_initialization(self):
        """Test result aggregator initialization"""
        aggregator = ResultAggregator()
        assert len(aggregator.results) == 0

    def test_add_single_result(self):
        """Test adding a single result"""
        aggregator = ResultAggregator()
        aggregator.start()

        result = TestResult(
            test_id="test1",
            test_name="test_login",
            endpoint_path="/api/login",
            endpoint_method="POST",
            test_type="positive",
            success=True,
            status_code=200,
            response_time_ms=150.5
        )

        aggregator.add_result(result)
        assert len(aggregator.results) == 1

    def test_get_aggregated_results(self):
        """Test aggregated results calculation"""
        aggregator = ResultAggregator()
        aggregator.start()

        # Add multiple results
        for i in range(10):
            result = TestResult(
                test_id=f"test{i}",
                test_name=f"test_{i}",
                endpoint_path="/api/test",
                endpoint_method="GET",
                test_type="positive",
                success=i < 7,  # 7 passed, 3 failed
                status_code=200 if i < 7 else 500,
                response_time_ms=100.0 + i * 10
            )
            aggregator.add_result(result)

        aggregator.complete()
        aggregated = aggregator.get_aggregated_results()

        assert aggregated.total_tests == 10
        assert aggregated.passed_tests == 7
        assert aggregated.failed_tests == 3
        assert aggregated.success_rate == 70.0

    def test_response_time_statistics(self):
        """Test response time statistical calculations"""
        aggregator = ResultAggregator()
        aggregator.start()

        response_times = [100, 150, 200, 250, 300]
        for i, rt in enumerate(response_times):
            result = TestResult(
                test_id=f"test{i}",
                test_name=f"test_{i}",
                endpoint_path="/api/test",
                endpoint_method="GET",
                test_type="positive",
                success=True,
                status_code=200,
                response_time_ms=rt
            )
            aggregator.add_result(result)

        aggregator.complete()
        aggregated = aggregator.get_aggregated_results()

        assert aggregated.average_response_time_ms == 200.0
        assert aggregated.median_response_time_ms == 200.0
        assert aggregated.min_response_time_ms == 100.0
        assert aggregated.max_response_time_ms == 300.0

    def test_test_type_distribution(self):
        """Test test type distribution tracking"""
        aggregator = ResultAggregator()
        aggregator.start()

        # Add different test types
        for test_type, count in [("positive", 5), ("negative", 3), ("boundary", 2)]:
            for i in range(count):
                result = TestResult(
                    test_id=f"{test_type}{i}",
                    test_name=f"test_{test_type}_{i}",
                    endpoint_path="/api/test",
                    endpoint_method="GET",
                    test_type=test_type,
                    success=True,
                    status_code=200
                )
                aggregator.add_result(result)

        aggregator.complete()
        aggregated = aggregator.get_aggregated_results()

        assert aggregated.test_type_distribution["positive"] == 5
        assert aggregated.test_type_distribution["negative"] == 3
        assert aggregated.test_type_distribution["boundary"] == 2

    def test_status_code_distribution(self):
        """Test status code distribution tracking"""
        aggregator = ResultAggregator()
        aggregator.start()

        status_codes = [200, 200, 200, 201, 400, 404, 500]
        for i, code in enumerate(status_codes):
            result = TestResult(
                test_id=f"test{i}",
                test_name=f"test_{i}",
                endpoint_path="/api/test",
                endpoint_method="GET",
                test_type="positive",
                success=code < 400,
                status_code=code
            )
            aggregator.add_result(result)

        aggregator.complete()
        aggregated = aggregator.get_aggregated_results()

        assert aggregated.status_code_distribution[200] == 3
        assert aggregated.status_code_distribution[201] == 1
        assert aggregated.status_code_distribution[400] == 1
        assert aggregated.status_code_distribution[404] == 1
        assert aggregated.status_code_distribution[500] == 1

    def test_get_failed_tests(self):
        """Test retrieving failed tests"""
        aggregator = ResultAggregator()
        aggregator.start()

        # Add mix of passed and failed tests
        for i in range(10):
            result = TestResult(
                test_id=f"test{i}",
                test_name=f"test_{i}",
                endpoint_path="/api/test",
                endpoint_method="GET",
                test_type="positive",
                success=i % 2 == 0,  # Every other test fails
                status_code=200 if i % 2 == 0 else 500,
                error_message="Test failed" if i % 2 != 0 else None
            )
            aggregator.add_result(result)

        failed = aggregator.get_failed_tests()
        assert len(failed) == 5
        assert all(not result.success for result in failed)

    def test_get_slowest_tests(self):
        """Test retrieving slowest tests"""
        aggregator = ResultAggregator()
        aggregator.start()

        response_times = [100, 500, 200, 800, 150, 600, 300]
        for i, rt in enumerate(response_times):
            result = TestResult(
                test_id=f"test{i}",
                test_name=f"test_{i}",
                endpoint_path="/api/test",
                endpoint_method="GET",
                test_type="positive",
                success=True,
                status_code=200,
                response_time_ms=rt
            )
            aggregator.add_result(result)

        slowest = aggregator.get_slowest_tests(limit=3)
        assert len(slowest) == 3
        assert slowest[0].response_time_ms == 800
        assert slowest[1].response_time_ms == 600
        assert slowest[2].response_time_ms == 500


# ============================================================================
# Parallel Executor Integration Tests
# ============================================================================

@pytest.mark.asyncio
class TestParallelExecutor:
    """Test parallel executor integration"""

    async def test_executor_initialization(self):
        """Test executor initialization"""
        executor = ParallelTestExecutor(
            num_workers=5,
            max_queue_size=100,
            enable_retries=True
        )
        assert executor.num_workers == 5
        assert not executor.is_running()

    async def test_execute_simple_tests(self):
        """Test executing simple test functions"""
        executor = ParallelTestExecutor(num_workers=3)

        async def simple_test(test_id: int) -> Dict[str, Any]:
            await asyncio.sleep(0.01)
            return {
                'success': True,
                'status_code': 200,
                'expected_status': 200,
                'response_time_ms': 10.0,
                'metadata': {}
            }

        test_functions = [
            {
                'func': simple_test,
                'test_name': f'test_{i}',
                'endpoint_path': '/api/test',
                'endpoint_method': 'GET',
                'test_type': 'positive',
                'args': (i,)
            }
            for i in range(10)
        ]

        result = await executor.execute_tests(test_functions)

        assert result['success']
        assert result['aggregated_results'].total_tests == 10
        assert result['aggregated_results'].passed_tests == 10
        assert result['aggregated_results'].success_rate == 100.0

    async def test_execute_with_failures(self):
        """Test executing tests with some failures"""
        executor = ParallelTestExecutor(num_workers=3, enable_retries=False)

        async def test_function(test_id: int) -> Dict[str, Any]:
            # Fail every third test
            success = test_id % 3 != 0
            return {
                'success': success,
                'status_code': 200 if success else 500,
                'expected_status': 200,
                'response_time_ms': 10.0
            }

        test_functions = [
            {
                'func': test_function,
                'test_name': f'test_{i}',
                'endpoint_path': '/api/test',
                'endpoint_method': 'GET',
                'test_type': 'positive',
                'args': (i,)
            }
            for i in range(12)
        ]

        result = await executor.execute_tests(test_functions)

        assert result['success']
        assert result['aggregated_results'].total_tests == 12
        assert result['aggregated_results'].passed_tests == 8
        assert result['aggregated_results'].failed_tests == 4

    async def test_executor_context_manager(self):
        """Test executor as async context manager"""
        async with ParallelTestExecutor(num_workers=2) as executor:
            async def simple_test() -> Dict[str, Any]:
                return {
                    'success': True,
                    'status_code': 200,
                    'expected_status': 200,
                    'response_time_ms': 5.0
                }

            test_functions = [
                {
                    'func': simple_test,
                    'test_name': 'test_1',
                    'endpoint_path': '/api/test',
                    'endpoint_method': 'GET',
                    'test_type': 'positive'
                }
            ]

            result = await executor.execute_tests(test_functions)
            assert result['success']

    async def test_executor_statistics(self):
        """Test executor provides comprehensive statistics"""
        executor = ParallelTestExecutor(num_workers=3)

        async def test_function(test_id: int) -> Dict[str, Any]:
            await asyncio.sleep(0.01)
            return {
                'success': True,
                'status_code': 200,
                'expected_status': 200,
                'response_time_ms': 10.0 + test_id
            }

        test_functions = [
            {
                'func': test_function,
                'test_name': f'test_{i}',
                'endpoint_path': '/api/test',
                'endpoint_method': 'GET',
                'test_type': 'positive',
                'args': (i,)
            }
            for i in range(20)
        ]

        result = await executor.execute_tests(test_functions)

        assert result['success']
        assert 'summary' in result
        assert 'aggregated_results' in result
        assert 'worker_stats' in result
        assert 'queue_stats' in result

        summary = result['summary']
        assert summary['total_tests'] == 20
        assert summary['passed_tests'] == 20
        assert 'average_response_time_ms' in summary

    async def test_executor_error_handling(self):
        """Test executor handles errors gracefully"""
        executor = ParallelTestExecutor(num_workers=2, enable_retries=False)

        async def failing_test() -> Dict[str, Any]:
            raise Exception("Test execution error")

        test_functions = [
            {
                'func': failing_test,
                'test_name': 'failing_test',
                'endpoint_path': '/api/test',
                'endpoint_method': 'GET',
                'test_type': 'negative'
            }
        ]

        result = await executor.execute_tests(test_functions)

        # Should complete but show failures
        assert result['success']
        assert result['aggregated_results'].failed_tests == 1

        failed_tests = executor.get_failed_tests()
        assert len(failed_tests) == 1
        assert failed_tests[0].error_message is not None
