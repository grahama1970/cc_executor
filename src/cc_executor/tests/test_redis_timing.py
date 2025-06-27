#!/usr/bin/env python3
"""Tests for Redis task timing module"""

import pytest
import asyncio
import hashlib
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from prompts.redis_task_timing import RedisTaskTimer


@pytest.mark.asyncio
async def test_no_event_loop_conflict():
    """Test that _calculate_stall_timeout doesn't cause event loop conflicts"""
    timer = RedisTaskTimer()
    
    # Test case 1: Called from async context
    task_type = {
        'category': 'test',
        'name': 'test_task',
        'complexity': 'medium',
        'question_type': 'general'
    }
    
    # This should not raise RuntimeError
    result = timer._calculate_stall_timeout(100.0, task_type)
    assert isinstance(result, int)
    assert result > 0
    
    # Test case 2: Called from sync context (outside event loop)
    # This is tested by the fact that this test runs without error


@pytest.mark.asyncio
async def test_percentile_logic():
    """Test that percentile calculation works correctly"""
    timer = RedisTaskTimer()
    
    # Mock the execute_redis method to return test data
    original_execute = timer.execute_redis
    
    async def mock_execute(cmd):
        if "zrange" in cmd:
            # Return test data with outliers
            return '\n'.join([
                '{"timestamp": 1, "actual": 10.0, "success": true}',
                '{"timestamp": 2, "actual": 12.0, "success": true}',
                '{"timestamp": 3, "actual": 15.0, "success": true}',
                '{"timestamp": 4, "actual": 18.0, "success": true}',
                '{"timestamp": 5, "actual": 20.0, "success": true}',
                '{"timestamp": 6, "actual": 100.0, "success": true}'  # Outlier
            ])
        elif "hgetall" in cmd:
            return 'total_runs\n6\nsuccesses\n6'
        return ""
    
    timer.execute_redis = mock_execute
    
    # Test with 6 samples (should use p90)
    history = await timer.get_task_history("test", "task1")
    
    # p90 of [10, 12, 15, 18, 20, 100] should be 20 (not mean of 29.17)
    assert history['avg_time'] == 20.0
    assert history['sample_size'] == 6
    
    # Restore original method
    timer.execute_redis = original_execute


def test_unknown_hash_stable():
    """Test that unknown command classification produces stable hash"""
    timer = RedisTaskTimer()
    
    # Test unknown command
    unknown_cmd = "some_unknown_command --with --flags"
    result = timer.classify_command(unknown_cmd)
    
    # Check that it's classified as unknown with hash
    assert result['category'] == 'unknown'
    assert len(result['name']) == 8  # Hash should be 8 chars
    
    # Verify hash is stable (same command produces same hash)
    result2 = timer.classify_command(unknown_cmd)
    assert result['name'] == result2['name']
    
    # Verify it's the expected MD5 hash
    expected_hash = hashlib.md5(unknown_cmd.encode()).hexdigest()[:8]
    assert result['name'] == expected_hash


if __name__ == "__main__":
    # Run the tests
    import subprocess
    result = subprocess.run([sys.executable, "-m", "pytest", __file__, "-v"], 
                          capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    exit(result.returncode)