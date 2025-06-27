#!/usr/bin/env python3
"""
Execution Time Tracker using Redis
Tracks expected vs actual execution times for stress test tasks
"""

import redis
import json
import time
from datetime import datetime
from typing import Dict, Optional, List, Tuple
import statistics

class ExecutionTimeTracker:
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379, redis_db: int = 0):
        """Initialize Redis connection for tracking execution times"""
        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True
            )
            # Test connection
            self.redis_client.ping()
            self.connected = True
        except (redis.ConnectionError, redis.TimeoutError):
            print("Warning: Redis not available, falling back to in-memory tracking")
            self.connected = False
            self.memory_store = {}
    
    def _get_key(self, task_id: str, category: str) -> str:
        """Generate Redis key for a task"""
        return f"cc_executor:stress_test:{category}:{task_id}"
    
    def record_execution(
        self, 
        task_id: str, 
        category: str,
        expected_time: float,
        actual_time: float,
        success: bool,
        complexity_score: int,
        response_length: int,
        error: str = None
    ) -> None:
        """Record a task execution with timing data"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "expected_time": expected_time,
            "actual_time": actual_time,
            "success": success,
            "complexity_score": complexity_score,
            "response_length": response_length,
            "time_ratio": actual_time / expected_time if expected_time > 0 else 1.0
        }
        
        key = self._get_key(task_id, category)
        
        if self.connected:
            # Store in Redis list (keep last 100 executions)
            self.redis_client.lpush(key, json.dumps(data))
            self.redis_client.ltrim(key, 0, 99)
            # Set expiry to 30 days
            self.redis_client.expire(key, 30 * 24 * 60 * 60)
        else:
            # Fallback to memory
            if key not in self.memory_store:
                self.memory_store[key] = []
            self.memory_store[key].insert(0, data)
            # Keep only last 100
            self.memory_store[key] = self.memory_store[key][:100]
    
    def get_predicted_timeout(
        self, 
        task_id: str, 
        category: str,
        base_timeout: float,
        complexity_score: int
    ) -> Tuple[float, Dict[str, float]]:
        """
        Get predicted timeout based on historical data
        Returns (recommended_timeout, statistics)
        """
        key = self._get_key(task_id, category)
        
        # Get historical data
        if self.connected:
            history = self.redis_client.lrange(key, 0, -1)
            executions = [json.loads(item) for item in history]
        else:
            executions = self.memory_store.get(key, [])
        
        if not executions:
            # No history, use base timeout with complexity adjustment
            return base_timeout + (complexity_score * 5), {
                "sample_size": 0,
                "confidence": 0.0
            }
        
        # Analyze successful executions
        successful_times = [
            e["actual_time"] for e in executions 
            if e.get("success", False)
        ]
        
        if not successful_times:
            # No successful executions, use max actual time + 50%
            max_time = max(e["actual_time"] for e in executions)
            return max_time * 1.5, {
                "sample_size": len(executions),
                "confidence": 0.3,
                "all_failed": True
            }
        
        # Calculate statistics
        avg_time = statistics.mean(successful_times)
        median_time = statistics.median(successful_times)
        
        if len(successful_times) > 1:
            std_dev = statistics.stdev(successful_times)
            percentile_95 = sorted(successful_times)[int(len(successful_times) * 0.95)]
        else:
            std_dev = avg_time * 0.2  # Assume 20% variance
            percentile_95 = avg_time * 1.2
        
        # Calculate confidence based on sample size and consistency
        sample_confidence = min(len(successful_times) / 10, 1.0)  # Max confidence at 10 samples
        consistency_confidence = 1.0 - (std_dev / avg_time) if avg_time > 0 else 0.5
        confidence = (sample_confidence + consistency_confidence) / 2
        
        # Recommend timeout: 95th percentile + buffer based on confidence
        buffer_multiplier = 1.5 - (confidence * 0.3)  # 1.5x when low confidence, 1.2x when high
        recommended_timeout = percentile_95 * buffer_multiplier
        
        # Never go below base timeout
        recommended_timeout = max(recommended_timeout, base_timeout)
        
        return recommended_timeout, {
            "sample_size": len(successful_times),
            "avg_time": avg_time,
            "median_time": median_time,
            "std_dev": std_dev,
            "percentile_95": percentile_95,
            "confidence": confidence,
            "success_rate": len(successful_times) / len(executions)
        }
    
    def get_task_statistics(self, task_id: str, category: str) -> Optional[Dict]:
        """Get detailed statistics for a task"""
        key = self._get_key(task_id, category)
        
        if self.connected:
            history = self.redis_client.lrange(key, 0, -1)
            executions = [json.loads(item) for item in history]
        else:
            executions = self.memory_store.get(key, [])
        
        if not executions:
            return None
        
        successful = [e for e in executions if e.get("success", False)]
        failed = [e for e in executions if not e.get("success", False)]
        
        return {
            "total_executions": len(executions),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(executions) if executions else 0,
            "avg_actual_time": statistics.mean([e["actual_time"] for e in executions]),
            "avg_expected_time": statistics.mean([e["expected_time"] for e in executions]),
            "avg_time_ratio": statistics.mean([e["time_ratio"] for e in executions]),
            "last_execution": executions[0] if executions else None
        }
    
    def get_all_tasks_summary(self) -> Dict[str, Dict]:
        """Get summary of all tracked tasks"""
        summary = {}
        
        if self.connected:
            # Scan all keys matching our pattern
            cursor = 0
            pattern = "cc_executor:stress_test:*"
            while True:
                cursor, keys = self.redis_client.scan(cursor, match=pattern, count=100)
                for key in keys:
                    parts = key.split(":")
                    if len(parts) >= 4:
                        category = parts[2]
                        task_id = parts[3]
                        stats = self.get_task_statistics(task_id, category)
                        if stats:
                            summary[f"{category}:{task_id}"] = stats
                if cursor == 0:
                    break
        else:
            # From memory store
            for key in self.memory_store:
                parts = key.split(":")
                if len(parts) >= 4:
                    category = parts[2]
                    task_id = parts[3]
                    stats = self.get_task_statistics(task_id, category)
                    if stats:
                        summary[f"{category}:{task_id}"] = stats
        
        return summary


# Example usage and testing
if __name__ == "__main__":
    tracker = ExecutionTimeTracker()
    
    # Test recording
    tracker.record_execution(
        task_id="test_1",
        category="simple",
        expected_time=30.0,
        actual_time=35.5,
        success=True,
        complexity_score=5,
        response_length=1500
    )
    
    # Test prediction
    timeout, stats = tracker.get_predicted_timeout(
        task_id="test_1",
        category="simple", 
        base_timeout=30.0,
        complexity_score=5
    )
    
    print(f"Recommended timeout: {timeout:.1f}s")
    print(f"Statistics: {json.dumps(stats, indent=2)}")
    
    # Test summary
    summary = tracker.get_all_tasks_summary()
    print(f"\nAll tasks summary:")
    for task, stats in summary.items():
        print(f"  {task}: {stats['success_rate']:.0%} success rate, "
              f"avg time: {stats['avg_actual_time']:.1f}s")