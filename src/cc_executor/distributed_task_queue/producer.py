"""
Task producer for enqueuing tasks with priority support.

This module provides the interface for submitting tasks to the distributed queue.
"""
import asyncio
import time
from typing import Dict, Any, List, Optional, Union
from loguru import logger

from cc_executor.distributed_task_queue.models import (
    Task, TaskStatus, TaskPriority, RedisKeys
)
from cc_executor.distributed_task_queue.redis_connection import RedisConnectionManager


class TaskProducer:
    """Produces tasks and enqueues them to Redis."""
    
    def __init__(self, redis_manager: RedisConnectionManager):
        self.redis = redis_manager
        
    async def enqueue(
        self,
        name: str,
        payload: Dict[str, Any],
        queue: str = "default",
        priority: Union[int, TaskPriority] = TaskPriority.NORMAL,
        delay: Optional[int] = None,
        **kwargs
    ) -> Task:
        """
        Enqueue a new task.
        
        Args:
            name: Task name/type
            payload: Task data to process
            queue: Queue name
            priority: Task priority (higher = more important)
            delay: Delay in seconds before task becomes available
            **kwargs: Additional task attributes
            
        Returns:
            Created Task object
        """
        # Create task
        task = Task(
            name=name,
            payload=payload,
            queue=queue,
            priority=int(priority),
            **kwargs
        )
        
        async with self.redis.get_client() as client:
            # Store task data
            task_key = task.to_redis_key()
            await client.hset(task_key, mapping={
                "data": task.to_json(),
                "status": task.status.value,
                "created_at": str(task.created_at)
            })
            
            # Add to appropriate queue
            if delay:
                # Add to delayed queue with score = current_time + delay
                queue_key = RedisKeys.format(RedisKeys.QUEUE_DELAYED, queue=queue)
                score = time.time() + delay
                await client.zadd(queue_key, {task.id: score})
                logger.info(f"Task {task.id} enqueued with {delay}s delay")
            else:
                # Add to pending queue with priority as score (negative for descending order)
                queue_key = RedisKeys.format(RedisKeys.QUEUE_PENDING, queue=queue)
                await client.zadd(queue_key, {task.id: -task.priority})
                logger.info(f"Task {task.id} enqueued with priority {task.priority}")
            
            # Update metrics
            await self._increment_metric(client, queue, "enqueued")
            
        return task
    
    async def enqueue_batch(
        self,
        tasks: List[Dict[str, Any]],
        queue: str = "default",
        priority: Union[int, TaskPriority] = TaskPriority.NORMAL
    ) -> List[Task]:
        """
        Enqueue multiple tasks in a batch.
        
        Args:
            tasks: List of task definitions (each with 'name' and 'payload')
            queue: Queue name for all tasks
            priority: Default priority for all tasks
            
        Returns:
            List of created Task objects
        """
        created_tasks = []
        
        async with self.redis.get_client() as client:
            # Use pipeline for efficiency
            pipe = client.pipeline()
            
            for task_def in tasks:
                # Create task
                task = Task(
                    name=task_def.get("name", ""),
                    payload=task_def.get("payload", {}),
                    queue=queue,
                    priority=task_def.get("priority", int(priority)),
                    **{k: v for k, v in task_def.items() if k not in ["name", "payload", "priority"]}
                )
                created_tasks.append(task)
                
                # Add commands to pipeline
                task_key = task.to_redis_key()
                pipe.hset(task_key, mapping={
                    "data": task.to_json(),
                    "status": task.status.value,
                    "created_at": str(task.created_at)
                })
                
                queue_key = RedisKeys.format(RedisKeys.QUEUE_PENDING, queue=queue)
                pipe.zadd(queue_key, {task.id: -task.priority})
            
            # Execute pipeline
            await pipe.execute()
            
            # Update metrics
            await self._increment_metric(client, queue, "enqueued", len(tasks))
            
        logger.info(f"Batch enqueued {len(created_tasks)} tasks to {queue}")
        return created_tasks
    
    async def schedule_recurring(
        self,
        name: str,
        payload: Dict[str, Any],
        interval: int,
        queue: str = "default",
        priority: Union[int, TaskPriority] = TaskPriority.NORMAL,
        **kwargs
    ) -> Task:
        """
        Schedule a recurring task.
        
        Args:
            name: Task name
            payload: Task data
            interval: Interval in seconds between executions
            queue: Queue name
            priority: Task priority
            **kwargs: Additional task attributes
            
        Returns:
            Initial Task object
        """
        # Add recurrence metadata
        kwargs["metadata"] = kwargs.get("metadata", {})
        kwargs["metadata"]["recurring"] = True
        kwargs["metadata"]["interval"] = interval
        kwargs["metadata"]["next_run"] = time.time() + interval
        
        # Enqueue the first instance
        return await self.enqueue(
            name=name,
            payload=payload,
            queue=queue,
            priority=priority,
            **kwargs
        )
    
    async def cancel_task(self, task_id: str, queue: str) -> bool:
        """
        Cancel a pending task.
        
        Args:
            task_id: Task ID to cancel
            queue: Queue name
            
        Returns:
            True if cancelled, False if not found or already running
        """
        async with self.redis.get_client() as client:
            # Check if task exists and is pending
            task_key = f"task:{queue}:{task_id}"
            task_data = await client.hget(task_key, "data")
            
            if not task_data:
                logger.warning(f"Task {task_id} not found")
                return False
            
            task = Task.from_json(task_data)
            
            if task.status != TaskStatus.PENDING:
                logger.warning(f"Task {task_id} is {task.status}, cannot cancel")
                return False
            
            # Remove from pending queue
            pending_key = RedisKeys.format(RedisKeys.QUEUE_PENDING, queue=queue)
            removed = await client.zrem(pending_key, task_id)
            
            if removed:
                # Update task status
                task.status = TaskStatus.CANCELLED
                await client.hset(task_key, mapping={
                    "data": task.to_json(),
                    "status": task.status.value
                })
                logger.info(f"Task {task_id} cancelled")
                return True
            
            # Also check delayed queue
            delayed_key = RedisKeys.format(RedisKeys.QUEUE_DELAYED, queue=queue)
            removed = await client.zrem(delayed_key, task_id)
            
            if removed:
                task.status = TaskStatus.CANCELLED
                await client.hset(task_key, mapping={
                    "data": task.to_json(),
                    "status": task.status.value
                })
                logger.info(f"Delayed task {task_id} cancelled")
                return True
            
            return False
    
    async def get_queue_length(self, queue: str = "default") -> Dict[str, int]:
        """Get the number of tasks in each queue state."""
        async with self.redis.get_client() as client:
            pending_key = RedisKeys.format(RedisKeys.QUEUE_PENDING, queue=queue)
            running_key = RedisKeys.format(RedisKeys.QUEUE_RUNNING, queue=queue)
            delayed_key = RedisKeys.format(RedisKeys.QUEUE_DELAYED, queue=queue)
            dead_key = RedisKeys.format(RedisKeys.QUEUE_DEAD, queue=queue)
            
            pending = await client.zcard(pending_key)
            running = await client.scard(running_key)
            delayed = await client.zcard(delayed_key)
            dead = await client.llen(dead_key)
            
            return {
                "pending": pending,
                "running": running,
                "delayed": delayed,
                "dead": dead,
                "total": pending + running + delayed
            }
    
    async def _increment_metric(
        self,
        client,
        queue: str,
        metric: str,
        amount: int = 1
    ) -> None:
        """Increment a queue metric."""
        metric_key = f"metrics:counter:{queue}:{metric}"
        await client.hincrby(metric_key, str(time.strftime("%Y-%m-%d")), amount)


async def working_usage():
    """Demonstrate task producer usage.
    
    AGENT: Run this for stable, production-ready example.
    This function is known to work and should not be modified.
    """
    # Initialize Redis and producer
    redis_manager = RedisConnectionManager()
    await redis_manager.connect()
    
    producer = TaskProducer(redis_manager)
    
    try:
        # Enqueue a simple task
        task1 = await producer.enqueue(
            name="send_email",
            payload={
                "to": "user@example.com",
                "subject": "Welcome!",
                "template": "welcome"
            },
            queue="emails",
            priority=TaskPriority.NORMAL
        )
        print(f"Enqueued task: {task1.id}")
        
        # Enqueue a high priority task
        task2 = await producer.enqueue(
            name="process_payment",
            payload={
                "order_id": "ORD-123",
                "amount": 99.99,
                "currency": "USD"
            },
            queue="payments",
            priority=TaskPriority.HIGH,
            tags=["urgent", "financial"]
        )
        print(f"Enqueued high priority task: {task2.id}")
        
        # Enqueue a delayed task
        task3 = await producer.enqueue(
            name="send_reminder",
            payload={"user_id": "user_456", "type": "subscription"},
            queue="notifications",
            delay=60  # Process after 60 seconds
        )
        print(f"Enqueued delayed task: {task3.id}")
        
        # Batch enqueue
        batch_tasks = [
            {
                "name": "resize_image",
                "payload": {"image_id": f"img_{i}", "size": "thumbnail"},
                "priority": TaskPriority.LOW
            }
            for i in range(5)
        ]
        
        created = await producer.enqueue_batch(batch_tasks, queue="media")
        print(f"Batch enqueued {len(created)} tasks")
        
        # Check queue lengths
        lengths = await producer.get_queue_length("emails")
        print(f"\nQueue 'emails' status: {lengths}")
        
    finally:
        await redis_manager.disconnect()
    
    print("\n✓ Task producer test complete")
    return True


async def debug_function():
    """Debug function for testing edge cases.
    
    AGENT: Use this function for experimenting! Rewrite freely.
    This is constantly rewritten to test different things.
    """
    redis_manager = RedisConnectionManager()
    await redis_manager.connect()
    
    producer = TaskProducer(redis_manager)
    
    try:
        # Test task cancellation
        print("Testing task cancellation:")
        
        # Create a task
        task = await producer.enqueue(
            name="test_cancel",
            payload={"data": "test"},
            queue="test"
        )
        print(f"Created task: {task.id}")
        
        # Cancel it
        cancelled = await producer.cancel_task(task.id, "test")
        print(f"Cancelled: {cancelled}")
        
        # Try to cancel again
        cancelled_again = await producer.cancel_task(task.id, "test")
        print(f"Cancel again: {cancelled_again}")
        
        # Test recurring task
        print("\nTesting recurring task:")
        recurring = await producer.schedule_recurring(
            name="cleanup_temp_files",
            payload={"directory": "/tmp"},
            interval=3600,  # Every hour
            queue="maintenance"
        )
        print(f"Scheduled recurring task: {recurring.id}")
        print(f"Metadata: {recurring.metadata}")
        
        # Test priority ordering
        print("\nTesting priority ordering:")
        
        # Clear the test queue first
        async with redis_manager.get_client() as client:
            await client.delete(RedisKeys.format(RedisKeys.QUEUE_PENDING, queue="priority_test"))
        
        # Add tasks with different priorities
        priorities = [
            ("low_task", TaskPriority.LOW),
            ("critical_task", TaskPriority.CRITICAL),
            ("normal_task", TaskPriority.NORMAL),
            ("high_task", TaskPriority.HIGH),
        ]
        
        for name, priority in priorities:
            await producer.enqueue(
                name=name,
                payload={"test": True},
                queue="priority_test",
                priority=priority
            )
        
        # Check order in queue
        async with redis_manager.get_client() as client:
            queue_key = RedisKeys.format(RedisKeys.QUEUE_PENDING, queue="priority_test")
            tasks = await client.zrange(queue_key, 0, -1, withscores=True)
            print("Tasks in priority order:")
            for task_id, score in tasks:
                print(f"  {task_id}: priority score = {-score}")
        
    finally:
        await redis_manager.disconnect()
    
    print("\n✓ Debug tests complete")


if __name__ == "__main__":
    """
    AGENT INSTRUCTIONS:
    - DEFAULT: Runs working_usage() - stable example that works
    - DEBUG: Run with 'debug' argument to test new ideas
    - DO NOT create external test files - use debug_function() instead!
    """
    import sys
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    if mode == "debug":
        print("Running debug mode...")
        asyncio.run(debug_function())
    else:
        print("Running working usage mode...")
        asyncio.run(working_usage())