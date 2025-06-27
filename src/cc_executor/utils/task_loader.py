#!/usr/bin/env python3
"""Task loader with environment variable overrides for timeouts"""

import json
import os
from typing import Dict, Any

class TaskLoader:
    """Load tasks from JSON with environment-based timeout overrides"""
    
    def __init__(self):
        # Load default timeout configurations from environment
        self.default_timeout = int(os.environ.get('DEFAULT_TASK_TIMEOUT', '300'))
        self.default_stall = int(os.environ.get('DEFAULT_STALL_TIMEOUT', '120'))
        
        # Complexity-based multipliers
        self.complexity_timeouts = {
            'simple': {
                'timeout': int(os.environ.get('SIMPLE_TASK_TIMEOUT', '60')),
                'stall': int(os.environ.get('SIMPLE_STALL_TIMEOUT', '30'))
            },
            'medium': {
                'timeout': int(os.environ.get('MEDIUM_TASK_TIMEOUT', '180')),
                'stall': int(os.environ.get('MEDIUM_STALL_TIMEOUT', '60'))
            },
            'complex': {
                'timeout': int(os.environ.get('COMPLEX_TASK_TIMEOUT', '600')),
                'stall': int(os.environ.get('COMPLEX_STALL_TIMEOUT', '120'))
            }
        }
    
    def load_tasks(self, json_path: str) -> Dict[str, Any]:
        """Load tasks from JSON and apply environment overrides"""
        with open(json_path, 'r') as f:
            tasks = json.load(f)
        
        # Apply timeout overrides to all tasks
        for category_name, category_data in tasks.get('categories', {}).items():
            for task in category_data.get('tasks', []):
                self._apply_timeout_overrides(task, category_name)
        
        return tasks
    
    def _apply_timeout_overrides(self, task: Dict[str, Any], category: str) -> None:
        """Apply environment-based timeout overrides to a task"""
        task_id = task.get('id', '')
        verification = task.get('verification', {})
        
        # Check for task-specific overrides first
        timeout_override = os.environ.get(f'TIMEOUT_OVERRIDE_{task_id}')
        stall_override = os.environ.get(f'STALL_OVERRIDE_{task_id}')
        
        if timeout_override:
            verification['timeout'] = int(timeout_override)
        elif category in self.complexity_timeouts:
            # Use category-based defaults if no override
            verification['timeout'] = self.complexity_timeouts[category]['timeout']
        else:
            # Fall back to general default
            verification['timeout'] = self.default_timeout
        
        if stall_override:
            verification['stall_timeout'] = int(stall_override)
        elif category in self.complexity_timeouts:
            verification['stall_timeout'] = self.complexity_timeouts[category]['stall']
        else:
            verification['stall_timeout'] = self.default_stall
        
        # Update the task's verification settings
        task['verification'] = verification
        
        # Also extract complexity from metatags if available
        metatags = task.get('metatags', '')
        if 'complexity:' in metatags:
            complexity = metatags.split('complexity:')[1].split(']')[0]
            task['complexity'] = complexity
    
    def get_task_by_id(self, tasks: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """Get a specific task by ID"""
        for category_data in tasks.get('categories', {}).values():
            for task in category_data.get('tasks', []):
                if task.get('id') == task_id:
                    return task
        return None


# Example usage
if __name__ == "__main__":
    # Test the loader
    loader = TaskLoader()
    
    # Set some test environment variables
    os.environ['DEFAULT_TASK_TIMEOUT'] = '400'
    os.environ['TIMEOUT_OVERRIDE_extreme_1'] = '1200'
    os.environ['STALL_OVERRIDE_extreme_1'] = '300'
    
    # Load tasks
    tasks_path = "/home/graham/workspace/experiments/cc_executor/src/cc_executor/tasks/unified_stress_test_tasks.json"
    if os.path.exists(tasks_path):
        tasks = loader.load_tasks(tasks_path)
        
        # Check a specific task
        extreme_task = loader.get_task_by_id(tasks, 'extreme_1')
        if extreme_task:
            print(f"Task: {extreme_task['id']}")
            print(f"Timeout: {extreme_task['verification']['timeout']}")
            print(f"Stall timeout: {extreme_task['verification']['stall_timeout']}")
        
        # Show all timeout configurations
        print("\nAll task timeouts:")
        for cat_name, cat_data in tasks['categories'].items():
            print(f"\n{cat_name.upper()}:")
            for task in cat_data['tasks']:
                print(f"  {task['id']}: timeout={task['verification']['timeout']}s, stall={task['verification']['stall_timeout']}s")
    else:
        print(f"Tasks file not found: {tasks_path}")