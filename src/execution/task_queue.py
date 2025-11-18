"""
Task Queue System for Test Distribution
Manages test task distribution and prioritization
"""
import asyncio
from typing import List, Dict, Any, Optional, Callable, Coroutine
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from loguru import logger
import uuid


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Task:
    """Represents a test task"""
    id: str
    func: Callable[..., Coroutine]
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[Exception] = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other):
        """Compare tasks by priority (for priority queue)"""
        return self.priority.value > other.priority.value


class TaskQueue:
    """
    Priority-based task queue with retry logic

    Features:
    - Priority-based execution
    - Automatic retries on failure
    - Task metadata tracking
    - Task cancellation
    - Queue statistics
    """

    def __init__(
        self,
        max_size: Optional[int] = None,
        enable_retries: bool = True,
        default_max_retries: int = 3
    ):
        """
        Initialize task queue

        Args:
            max_size: Maximum queue size (None = unlimited)
            enable_retries: Whether to retry failed tasks
            default_max_retries: Default number of retries
        """
        self.max_size = max_size
        self.enable_retries = enable_retries
        self.default_max_retries = default_max_retries

        # Priority queue
        self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue(
            maxsize=max_size or 0
        )

        # Task tracking
        self.tasks: Dict[str, Task] = {}
        self.pending_tasks: int = 0
        self.completed_tasks: int = 0
        self.failed_tasks: int = 0

        logger.info(
            f"Initialized TaskQueue: max_size={max_size}, "
            f"enable_retries={enable_retries}"
        )

    async def add_task(
        self,
        func: Callable[..., Coroutine],
        *args,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Add a task to the queue

        Args:
            func: Async function to execute
            *args: Positional arguments
            priority: Task priority
            max_retries: Maximum retries (overrides default)
            metadata: Additional task metadata
            **kwargs: Keyword arguments

        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())

        task = Task(
            id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            max_retries=max_retries or self.default_max_retries,
            metadata=metadata or {}
        )

        # Store task
        self.tasks[task_id] = task

        # Add to queue (with priority)
        await self.queue.put(task)
        self.pending_tasks += 1

        logger.debug(f"Added task {task_id} with priority {priority.name}")

        return task_id

    async def add_tasks_batch(
        self,
        tasks: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Add multiple tasks at once

        Args:
            tasks: List of task dictionaries with keys:
                   - func: Callable
                   - args: tuple (optional)
                   - kwargs: dict (optional)
                   - priority: TaskPriority (optional)
                   - metadata: dict (optional)

        Returns:
            List of task IDs
        """
        task_ids = []

        for task_data in tasks:
            func = task_data['func']
            args = task_data.get('args', ())
            kwargs = task_data.get('kwargs', {})
            priority = task_data.get('priority', TaskPriority.NORMAL)
            metadata = task_data.get('metadata')

            task_id = await self.add_task(
                func,
                *args,
                priority=priority,
                metadata=metadata,
                **kwargs
            )
            task_ids.append(task_id)

        logger.info(f"Added {len(task_ids)} tasks to queue")

        return task_ids

    async def get_task(self, timeout: Optional[float] = None) -> Optional[Task]:
        """
        Get next task from queue

        Args:
            timeout: Timeout in seconds (None = wait forever)

        Returns:
            Task or None if timeout
        """
        try:
            if timeout:
                task = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=timeout
                )
            else:
                task = await self.queue.get()

            task.started_at = datetime.now()
            self.pending_tasks -= 1

            return task

        except asyncio.TimeoutError:
            return None

    async def mark_complete(
        self,
        task_id: str,
        result: Optional[Any] = None
    ):
        """
        Mark task as completed

        Args:
            task_id: Task ID
            result: Task result
        """
        if task_id not in self.tasks:
            logger.warning(f"Task {task_id} not found")
            return

        task = self.tasks[task_id]
        task.completed_at = datetime.now()
        task.result = result

        self.completed_tasks += 1
        self.queue.task_done()

        logger.debug(f"Task {task_id} completed")

    async def mark_failed(
        self,
        task_id: str,
        error: Exception
    ):
        """
        Mark task as failed and retry if needed

        Args:
            task_id: Task ID
            error: Error that occurred
        """
        if task_id not in self.tasks:
            logger.warning(f"Task {task_id} not found")
            return

        task = self.tasks[task_id]
        task.error = error
        task.retry_count += 1

        # Retry if under limit
        if self.enable_retries and task.retry_count < task.max_retries:
            logger.info(
                f"Retrying task {task_id} "
                f"(attempt {task.retry_count + 1}/{task.max_retries})"
            )

            # Reset timestamps
            task.started_at = None
            task.completed_at = None
            task.error = None

            # Re-queue with same priority
            await self.queue.put(task)
            self.pending_tasks += 1

        else:
            # Max retries exceeded or retries disabled
            task.completed_at = datetime.now()
            self.failed_tasks += 1
            self.queue.task_done()

            logger.error(
                f"Task {task_id} failed after {task.retry_count} attempts: {error}"
            )

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a task

        Args:
            task_id: Task ID

        Returns:
            Task status dictionary or None
        """
        if task_id not in self.tasks:
            return None

        task = self.tasks[task_id]

        status = "pending"
        if task.completed_at:
            status = "completed" if task.error is None else "failed"
        elif task.started_at:
            status = "running"

        return {
            'id': task.id,
            'status': status,
            'priority': task.priority.name,
            'created_at': task.created_at,
            'started_at': task.started_at,
            'completed_at': task.completed_at,
            'retry_count': task.retry_count,
            'has_result': task.result is not None,
            'has_error': task.error is not None,
            'metadata': task.metadata
        }

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get queue statistics

        Returns:
            Statistics dictionary
        """
        return {
            'total_tasks': len(self.tasks),
            'pending_tasks': self.pending_tasks,
            'completed_tasks': self.completed_tasks,
            'failed_tasks': self.failed_tasks,
            'queue_size': self.queue.qsize(),
            'completion_rate': (
                self.completed_tasks / len(self.tasks) * 100
                if len(self.tasks) > 0 else 0.0
            )
        }

    def get_task_result(self, task_id: str) -> Optional[Any]:
        """
        Get result of completed task

        Args:
            task_id: Task ID

        Returns:
            Task result or None
        """
        if task_id not in self.tasks:
            return None

        return self.tasks[task_id].result

    def get_task_error(self, task_id: str) -> Optional[Exception]:
        """
        Get error of failed task

        Args:
            task_id: Task ID

        Returns:
            Task error or None
        """
        if task_id not in self.tasks:
            return None

        return self.tasks[task_id].error

    async def wait_completion(self, timeout: Optional[float] = None):
        """
        Wait for all tasks to complete

        Args:
            timeout: Timeout in seconds

        Raises:
            asyncio.TimeoutError: If timeout exceeded
        """
        if timeout:
            await asyncio.wait_for(self.queue.join(), timeout=timeout)
        else:
            await self.queue.join()

    def is_empty(self) -> bool:
        """Check if queue is empty"""
        return self.queue.empty()

    def size(self) -> int:
        """Get current queue size"""
        return self.queue.qsize()

    def clear(self):
        """Clear all tasks"""
        self.tasks.clear()
        self.pending_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0

        # Clear queue
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                self.queue.task_done()
            except asyncio.QueueEmpty:
                break

        logger.info("Queue cleared")
