"""
Parallel Execution Package
Orchestrates concurrent test execution with worker pooling, task queuing, and result aggregation
"""
from src.execution.worker_pool import (
    WorkerPool,
    WorkerStats,
    PoolStats
)

from src.execution.task_queue import (
    TaskQueue,
    Task,
    TaskPriority
)

from src.execution.result_aggregator import (
    ResultAggregator,
    TestResult,
    AggregatedResults
)

from src.execution.parallel_executor import (
    ParallelTestExecutor
)

__all__ = [
    # Worker Pool
    'WorkerPool',
    'WorkerStats',
    'PoolStats',

    # Task Queue
    'TaskQueue',
    'Task',
    'TaskPriority',

    # Result Aggregation
    'ResultAggregator',
    'TestResult',
    'AggregatedResults',

    # Parallel Executor
    'ParallelTestExecutor',
]
