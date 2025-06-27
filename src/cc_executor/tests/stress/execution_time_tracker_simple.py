#!/usr/bin/env python3
"""
Simple Execution Time Tracker using JSONL file
Tracks expected vs actual execution times for stress test tasks
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional, List, Tuple
import statistics
from pathlib import Path

class SimpleExecutionTimeTracker:
    def __init__(self, history_file: str = None):
        """Initialize tracker with JSONL file for persistence"""
        if history_file is None:
            # Store in home directory
            history_dir = Path.home() / ".claude" / "stress_test_history"
            history_dir.mkdir(parents=True, exist_ok=True)
            self.history_file = history_dir / "execution_times.jsonl"
        else:
            self.history_file = Path(history_file)
        
        # Ensure file exists
        self.history_file.touch(exist_ok=True)
        
        # Load recent history into memory for fast access
        self.recent_history = self._load_recent_history(1000)  # Last 1000 entries
    
    def _load_recent_history(self, max_entries: int) -> Dict[str, List[Dict]]:
        """Load recent history from file into memory"""
        history = {}
        entries = []
        
        # Read all entries first
        with open(self.history_file, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        
        # Take only the most recent entries
        recent_entries = entries[-max_entries:] if len(entries) > max_entries else entries
        
        # Group by task
        for entry in recent_entries:
            key = f"{entry['category']}:{entry['task_id']}"
            if key not in history:
                history[key] = []
            history[key].append(entry)
        
        return history
    
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
            "task_id": task_id,
            "category": category,
            "expected_time": expected_time,
            "actual_time": actual_time,
            "success": success,
            "complexity_score": complexity_score,
            "response_length": response_length,
            "time_ratio": actual_time / expected_time if expected_time > 0 else 1.0,
            "error": error
        }
        
        # Append to file
        with open(self.history_file, 'a') as f:
            json.dump(data, f)
            f.write('\n')
        
        # Update memory cache
        key = f"{category}:{task_id}"
        if key not in self.recent_history:
            self.recent_history[key] = []
        self.recent_history[key].append(data)
        
        # Keep only last 100 per task in memory
        if len(self.recent_history[key]) > 100:
            self.recent_history[key] = self.recent_history[key][-100:]
    
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
        key = f"{category}:{task_id}"
        executions = self.recent_history.get(key, [])
        
        if not executions:
            # No history, use base timeout
            print(f"No history for {key}, using base timeout")
            return base_timeout, {
                "sample_size": 0,
                "confidence": 0.0,
                "source": "no_history"
            }
        
        # Get recent successful executions
        recent_successes = [
            e for e in executions[-20:]  # Last 20 executions
            if e.get("success", False)
        ]
        
        if not recent_successes:
            # No recent successes, look at all executions
            all_times = [e["actual_time"] for e in executions[-10:]]
            if all_times:
                # Use max time + 50%
                max_time = max(all_times)
                print(f"No recent successes for {key}, using max time * 1.5")
                return max_time * 1.5, {
                    "sample_size": len(executions),
                    "confidence": 0.3,
                    "all_failed": True,
                    "max_observed": max_time,
                    "source": "failed_history"
                }
            else:
                return base_timeout, {"sample_size": 0, "confidence": 0.0}
        
        # Calculate statistics from successful runs
        success_times = [e["actual_time"] for e in recent_successes]
        avg_time = statistics.mean(success_times)
        
        if len(success_times) >= 3:
            # Enough data for good statistics
            median_time = statistics.median(success_times)
            percentile_90 = sorted(success_times)[int(len(success_times) * 0.9)]
            max_time = max(success_times)
            
            # Use 90th percentile + 20% buffer
            recommended = percentile_90 * 1.2
            confidence = min(len(success_times) / 10, 0.9)  # Max 0.9 confidence
            
            stats = {
                "sample_size": len(success_times),
                "avg_time": avg_time,
                "median_time": median_time,
                "percentile_90": percentile_90,
                "max_time": max_time,
                "confidence": confidence,
                "source": "good_history"
            }
        else:
            # Limited data, be conservative
            max_time = max(success_times)
            recommended = max_time * 1.5  # 50% buffer
            confidence = 0.5
            
            stats = {
                "sample_size": len(success_times),
                "avg_time": avg_time,
                "max_time": max_time,
                "confidence": confidence,
                "source": "limited_history"
            }
        
        # Never go below base timeout
        recommended = max(recommended, base_timeout)
        
        print(f"History for {key}: {len(success_times)} successes, "
              f"recommending {recommended:.0f}s timeout (was {base_timeout:.0f}s)")
        
        return recommended, stats
    
    def get_task_summary(self, task_id: str = None, category: str = None) -> Dict[str, Dict]:
        """Get summary of task execution times"""
        summary = {}
        
        for key, executions in self.recent_history.items():
            cat, tid = key.split(":", 1)
            
            # Filter if specific task/category requested
            if task_id and tid != task_id:
                continue
            if category and cat != category:
                continue
            
            if executions:
                successful = [e for e in executions if e.get("success", False)]
                failed = [e for e in executions if not e.get("success", False)]
                
                summary[key] = {
                    "total_runs": len(executions),
                    "successful": len(successful),
                    "failed": len(failed),
                    "success_rate": len(successful) / len(executions) if executions else 0,
                    "avg_actual_time": statistics.mean([e["actual_time"] for e in executions]),
                    "avg_expected_time": statistics.mean([e["expected_time"] for e in executions]),
                    "last_run": executions[-1]["timestamp"],
                    "last_success": successful[-1]["timestamp"] if successful else None,
                    "recent_trend": "improving" if len(successful) > len(failed) else "degrading"
                }
        
        return summary
    
    def print_summary(self):
        """Print a nice summary of execution times"""
        summary = self.get_task_summary()
        
        if not summary:
            print("No execution history available")
            return
        
        print("\n" + "="*80)
        print("EXECUTION TIME HISTORY SUMMARY")
        print("="*80)
        
        for task_key, stats in sorted(summary.items()):
            print(f"\n{task_key}:")
            print(f"  Total runs: {stats['total_runs']} "
                  f"(Success: {stats['successful']}, Failed: {stats['failed']})")
            print(f"  Success rate: {stats['success_rate']:.1%}")
            print(f"  Avg execution time: {stats['avg_actual_time']:.1f}s")
            print(f"  Avg expected time: {stats['avg_expected_time']:.1f}s")
            print(f"  Recent trend: {stats['recent_trend']}")
            if stats['last_success']:
                print(f"  Last success: {stats['last_success']}")


# Example usage
if __name__ == "__main__":
    tracker = SimpleExecutionTimeTracker()
    
    # Test recording
    tracker.record_execution(
        task_id="daily_standup",
        category="simple",
        expected_time=30.0,
        actual_time=13.5,
        success=True,
        complexity_score=0,
        response_length=500
    )
    
    # Test prediction
    timeout, stats = tracker.get_predicted_timeout(
        task_id="daily_standup",
        category="simple",
        base_timeout=30.0,
        complexity_score=0
    )
    
    print(f"\nRecommended timeout: {timeout:.1f}s")
    print(f"Stats: {json.dumps(stats, indent=2)}")
    
    # Show summary
    tracker.print_summary()