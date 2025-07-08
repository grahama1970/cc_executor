"""
Anthropic Claude Code Hooks for cc_executor.

This module provides hook handlers that integrate with Claude Code's
lifecycle events to enhance timeout prediction, task sequencing,
code review, and self-reflection capabilities.

Hook Types:
- pre-edit: Analyze task complexity before execution
- post-edit: Review code changes for quality and security
- pre-tool: Validate task dependencies and system state
- post-tool: Update task completion status
- post-output: Record execution metrics and trigger reflection

Configuration:
Hooks are configured in .claude-hooks.json at the project root.
Each hook has a 60-second timeout and runs as a shell command.

Usage:
The hooks are automatically invoked by Claude Code when the
.claude-hooks.json file is present in the project.
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Hook handler modules - only import what exists
from . import (
    analyze_task_complexity,
    check_task_dependencies,
    update_task_status,
    record_execution_metrics
)

__all__ = [
    'analyze_task_complexity',
    'check_task_dependencies', 
    'update_task_status',
    'record_execution_metrics'
]

# Hook configuration defaults
HOOK_TIMEOUT = 60  # seconds
HOOK_PARALLEL = False  # Run hooks sequentially by default

# Redis configuration for hooks
REDIS_CONFIG = {
    'host': os.environ.get('REDIS_HOST', 'localhost'),
    'port': int(os.environ.get('REDIS_PORT', 6379)),
    'decode_responses': True
}