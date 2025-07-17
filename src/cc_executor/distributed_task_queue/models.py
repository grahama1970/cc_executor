"""
Task queue data models and serialization.

Defines the core data structures for the distributed task queue system.
"""
import json
import uuid
import time
from enum import Enum
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD = "dead"
    CANCELLED = "cancelled"


class TaskPriority(int, Enum):
    """Task priority levels (higher value = higher priority)."""
    LOW = 0
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


@dataclass
class Task:
    """Represents a task in the queue."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    queue: str = "default"
    priority: int = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    
    # Timing
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    # Execution
    worker_id: Optional[str] = None
    attempt: int = 0
    max_retries: int = 3
    retry_delay: int = 60  # seconds
    timeout: int = 300  # seconds
    
    # Results
    result: Optional[Any] = None
    error: Optional[str] = None
    traceback: Optional[str] = None
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_json(self) -> str:
        """Serialize task to JSON."""
        data = asdict(self)
        # Convert enums to strings
        data["status"] = self.status.value
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, json_str: str) -> "Task":
        """Deserialize task from JSON."""
        data = json.loads(json_str)
        # Convert status string back to enum
        if "status" in data:
            data["status"] = TaskStatus(data["status"])
        return cls(**data)
    
    def to_redis_key(self) -> str:
        """Generate Redis key for this task."""
        return f"task:{self.queue}:{self.id}"
    
    def is_expired(self) -> bool:
        """Check if task has exceeded its timeout."""
        if self.status != TaskStatus.RUNNING or not self.started_at:
            return False
        return (time.time() - self.started_at) > self.timeout
    
    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return self.attempt < self.max_retries
    
    def calculate_retry_delay(self) -> int:
        """Calculate exponential backoff delay for retries."""
        return self.retry_delay * (2 ** (self.attempt - 1))


@dataclass
class WorkerInfo:
    """Information about a task queue worker."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    hostname: str = ""
    pid: int = 0
    queues: List[str] = field(default_factory=list)
    status: str = "idle"
    started_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    current_task_id: Optional[str] = None
    tasks_processed: int = 0
    tasks_failed: int = 0
    
    def to_json(self) -> str:
        """Serialize worker info to JSON."""
        return json.dumps(asdict(self))
    
    @classmethod
    def from_json(cls, json_str: str) -> "WorkerInfo":
        """Deserialize worker info from JSON."""
        return cls(**json.loads(json_str))
    
    def to_redis_key(self) -> str:
        """Generate Redis key for this worker."""
        return f"worker:{self.id}"
    
    def is_alive(self, timeout: int = 60) -> bool:
        """Check if worker is still alive based on heartbeat."""
        return (time.time() - self.last_heartbeat) < timeout


@dataclass
class QueueMetrics:
    """Metrics for a task queue."""
    queue_name: str
    pending_tasks: int = 0
    running_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    dead_tasks: int = 0
    total_workers: int = 0
    active_workers: int = 0
    avg_processing_time: float = 0.0
    avg_wait_time: float = 0.0
    timestamp: float = field(default_factory=time.time)
    
    def to_json(self) -> str:
        """Serialize metrics to JSON."""
        return json.dumps(asdict(self))
    
    @classmethod
    def from_json(cls, json_str: str) -> "QueueMetrics":
        """Deserialize metrics from JSON."""
        return cls(**json.loads(json_str))


class RedisKeys:
    """Redis key patterns for the task queue system."""
    
    # Queue keys
    QUEUE_PENDING = "queue:pending:{queue}"  # Sorted set by priority
    QUEUE_RUNNING = "queue:running:{queue}"  # Set of running task IDs
    QUEUE_DELAYED = "queue:delayed:{queue}"  # Sorted set by retry time
    QUEUE_DEAD = "queue:dead:{queue}"       # List of dead tasks
    
    # Task keys
    TASK_DATA = "task:{queue}:{task_id}"    # Hash of task data
    TASK_LOCK = "lock:task:{task_id}"       # Task processing lock
    
    # Worker keys
    WORKER_INFO = "worker:{worker_id}"      # Hash of worker info
    WORKER_HEARTBEAT = "worker:heartbeat"   # Sorted set by last heartbeat
    WORKERS_BY_QUEUE = "workers:queue:{queue}"  # Set of worker IDs
    
    # Metrics keys
    METRICS_QUEUE = "metrics:queue:{queue}"  # Current queue metrics
    METRICS_HISTORY = "metrics:history:{queue}:{date}"  # Historical metrics
    
    # Control keys
    PAUSE_QUEUE = "control:pause:{queue}"   # Queue pause flag
    SHUTDOWN_SIGNAL = "control:shutdown"    # Global shutdown signal
    
    @staticmethod
    def format(pattern: str, **kwargs) -> str:
        """Format a key pattern with values."""
        return pattern.format(**kwargs)


async def working_usage():
    """Demonstrate task model usage.
    
    AGENT: Run this for stable, production-ready example.
    This function is known to work and should not be modified.
    """
    # Create a task
    task = Task(
        name="process_order",
        payload={"order_id": 12345, "amount": 99.99},
        queue="orders",
        priority=TaskPriority.HIGH,
        tags=["customer", "priority"],
        metadata={"customer_id": "cust_123"}
    )
    
    print(f"Task created: {task.id}")
    print(f"Task queue: {task.queue}")
    print(f"Task priority: {task.priority}")
    
    # Serialize to JSON
    json_str = task.to_json()
    print(f"Serialized: {json_str[:100]}...")
    
    # Deserialize from JSON
    task2 = Task.from_json(json_str)
    print(f"Deserialized task ID: {task2.id}")
    assert task.id == task2.id
    
    # Create worker info
    worker = WorkerInfo(
        hostname="worker-01",
        pid=1234,
        queues=["orders", "notifications"],
        status="running"
    )
    
    print(f"\nWorker created: {worker.id}")
    print(f"Worker queues: {worker.queues}")
    
    # Test Redis key generation
    print(f"\nRedis keys:")
    print(f"Task key: {task.to_redis_key()}")
    print(f"Worker key: {worker.to_redis_key()}")
    print(f"Queue key: {RedisKeys.format(RedisKeys.QUEUE_PENDING, queue='orders')}")
    
    print("\n✓ Task models test complete")
    return True


async def debug_function():
    """Debug function for testing edge cases.
    
    AGENT: Use this function for experimenting! Rewrite freely.
    This is constantly rewritten to test different things.
    """
    # Test task state transitions
    task = Task(name="test_task")
    
    print("Testing task state transitions:")
    print(f"Initial status: {task.status}")
    
    # Simulate task execution
    task.status = TaskStatus.RUNNING
    task.started_at = time.time()
    task.worker_id = "worker-123"
    print(f"Running status: {task.status}")
    
    # Simulate failure
    task.status = TaskStatus.FAILED
    task.error = "Connection timeout"
    task.attempt = 1
    print(f"Failed status: {task.status}, can retry: {task.can_retry()}")
    
    # Test retry delay calculation
    for attempt in range(1, 5):
        task.attempt = attempt
        delay = task.calculate_retry_delay()
        print(f"Attempt {attempt}: retry delay = {delay}s")
    
    # Test timeout detection
    expired_task = Task(name="expired", timeout=1)
    expired_task.status = TaskStatus.RUNNING
    expired_task.started_at = time.time() - 10  # Started 10 seconds ago
    print(f"\nExpired task: {expired_task.is_expired()}")
    
    # Test queue metrics
    metrics = QueueMetrics(
        queue_name="orders",
        pending_tasks=42,
        running_tasks=5,
        completed_tasks=1000,
        failed_tasks=3,
        active_workers=2
    )
    print(f"\nQueue metrics: {metrics.queue_name}")
    print(f"  Pending: {metrics.pending_tasks}")
    print(f"  Running: {metrics.running_tasks}")
    print(f"  Completed: {metrics.completed_tasks}")
    
    print("\n✓ Debug tests complete")


if __name__ == "__main__":
    """
    AGENT INSTRUCTIONS:
    - DEFAULT: Runs working_usage() - stable example that works
    - DEBUG: Run with 'debug' argument to test new ideas
    - DO NOT create external test files - use debug_function() instead!
    """
    import sys
    import asyncio
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    if mode == "debug":
        print("Running debug mode...")
        asyncio.run(debug_function())
    else:
        print("Running working usage mode...")
        asyncio.run(working_usage())