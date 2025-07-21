#!/usr/bin/env python3
"""
Post-task-list code review hook.

This hook triggers a 2-level code review after all tasks in a task list are completed:
1. First level: o3 model performs initial code review
2. Second level: Gemini reviews o3's output and provides final assessment

The review covers all files modified during the task list execution.
"""

import sys
import os
import json
import redis
import time
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from loguru import logger
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cc_executor.hooks.two_level_code_review import TwoLevelCodeReview


class PostTaskListReview:
    """Handles post-task-list code review triggering."""
    
    def __init__(self):
        self.redis_client = self._get_redis_client()
        self.review_system = TwoLevelCodeReview()
        
    def _get_redis_client(self) -> Optional[redis.Redis]:
        """Get Redis client if available."""
        try:
            r = redis.Redis(decode_responses=True)
            r.ping()
            return r
        except Exception as e:
            logger.warning(f"Redis not available: {e}")
            return None
            
    def get_modified_files(self, session_id: str) -> List[str]:
        """Get list of files modified during this session."""
        modified_files = set()
        
        if not self.redis_client:
            # Fallback: use git to find modified files
            try:
                import subprocess
                result = subprocess.run(
                    ["git", "diff", "--name-only", "HEAD"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    modified_files.update(result.stdout.strip().split('\n'))
            except Exception as e:
                logger.error(f"Could not get modified files from git: {e}")
                
        else:
            # Get from Redis tracking
            try:
                # Look for file edits in session
                pattern = f"hook:file_edit:{session_id}:*"
                for key in self.redis_client.scan_iter(match=pattern):
                    data = self.redis_client.get(key)
                    if data:
                        edit_info = json.loads(data)
                        modified_files.add(edit_info.get('file_path', ''))
                        
                # Also check execution history for created files
                history_key = f"task:execution_history"
                history = self.redis_client.lrange(history_key, 0, -1)
                
                for entry in history:
                    try:
                        record = json.loads(entry)
                        # Look for file creation commands
                        desc = record.get('description', '')
                        if 'create' in desc.lower() or 'write' in desc.lower():
                            # Extract file paths from description
                            import re
                            paths = re.findall(r'[\/\w\-\.]+\.(?:py|js|ts|md)', desc)
                            modified_files.update(paths)
                    except:
                        pass
                        
            except Exception as e:
                logger.error(f"Error getting modified files from Redis: {e}")
                
        # Filter to only existing files
        return [f for f in modified_files if f and os.path.exists(f)]
        
    def check_all_tasks_complete(self, session_id: str) -> Tuple[bool, Dict]:
        """Check if all tasks in the current list are complete."""
        if not self.redis_client:
            return False, {}
            
        try:
            # Get task statuses
            statuses = self.redis_client.hgetall("task:status")
            
            # Filter to current session tasks
            session_tasks = {}
            incomplete_tasks = []
            
            for task_key, status in statuses.items():
                # Check if this task belongs to current session
                task_data = self.redis_client.hget("task:session_map", task_key)
                if task_data == session_id:
                    session_tasks[task_key] = status
                    if status != "completed":
                        incomplete_tasks.append(task_key)
                        
            # Calculate completion
            total_tasks = len(session_tasks)
            completed_tasks = total_tasks - len(incomplete_tasks)
            
            all_complete = len(incomplete_tasks) == 0 and total_tasks > 0
            
            summary = {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "incomplete_tasks": incomplete_tasks,
                "completion_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            }
            
            return all_complete, summary
            
        except Exception as e:
            logger.error(f"Error checking task completion: {e}")
            return False, {}
            
    async def trigger_review(self, files: List[str], context: Dict) -> Dict:
        """Trigger the 2-level code review."""
        logger.info(f"Triggering 2-level code review for {len(files)} files")
        
        try:
            # Run the review
            result = await self.review_system.run_two_level_review(
                files=files,
                context=context
            )
            
            # Store result in Redis
            if self.redis_client and result['success']:
                review_key = f"review:result:{context.get('session_id', 'unknown')}:{int(time.time())}"
                self.redis_client.setex(
                    review_key,
                    86400,  # Keep for 24 hours
                    json.dumps(result)
                )
                
                # Also store summary for quick access
                summary_key = f"review:summary:{context.get('session_id', 'unknown')}"
                summary = {
                    "timestamp": time.time(),
                    "files_reviewed": len(files),
                    "critical_issues": result.get('summary', {}).get('critical_issues', 0),
                    "suggestions": result.get('summary', {}).get('total_suggestions', 0),
                    "review_id": review_key
                }
                self.redis_client.setex(summary_key, 86400, json.dumps(summary))
                
            return result
            
        except Exception as e:
            logger.error(f"Error triggering review: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def should_trigger_review(self) -> bool:
        """Determine if review should be triggered."""
        # Check environment variables
        if os.environ.get('DISABLE_CODE_REVIEW') == '1':
            return False
            
        # Check if this is a task list context
        context = os.environ.get('CLAUDE_CONTEXT', '')
        if 'task_list' not in context.lower():
            return False
            
        return True


async def main():
    """Main hook entry point."""
    # Get session ID
    session_id = os.environ.get('CLAUDE_SESSION_ID', 'unknown')
    
    # Initialize review system
    reviewer = PostTaskListReview()
    
    # Check if we should run
    if not reviewer.should_trigger_review():
        logger.info("Code review not applicable for this context")
        return 0
        
    # Check if all tasks are complete
    all_complete, summary = reviewer.check_all_tasks_complete(session_id)
    
    if not all_complete:
        logger.info(f"Not all tasks complete: {summary}")
        return 0
        
    logger.info(f"All tasks complete! Summary: {summary}")
    
    # Get modified files
    modified_files = reviewer.get_modified_files(session_id)
    
    if not modified_files:
        logger.info("No modified files found to review")
        return 0
        
    logger.info(f"Found {len(modified_files)} modified files to review")
    
    # Prepare context
    context = {
        "session_id": session_id,
        "task_summary": summary,
        "timestamp": datetime.now().isoformat(),
        "trigger": "post_task_list"
    }
    
    # Trigger review
    result = await reviewer.trigger_review(modified_files, context)
    
    if result['success']:
        logger.success(f"Code review completed successfully")
        
        # Output summary for user
        if 'summary' in result:
            print("\n" + "="*60)
            print("CODE REVIEW SUMMARY")
            print("="*60)
            print(f"Files reviewed: {len(modified_files)}")
            print(f"Critical issues: {result['summary'].get('critical_issues', 0)}")
            print(f"Suggestions: {result['summary'].get('total_suggestions', 0)}")
            print(f"Review saved to: {result.get('output_file', 'N/A')}")
            print("="*60 + "\n")
    else:
        logger.error(f"Code review failed: {result.get('error', 'Unknown error')}")
        
    return 0


if __name__ == "__main__":
    # Test mode
    if "--test" in sys.argv:
        print("\n=== Post-Task-List Review Hook Test ===\n")
        
        reviewer = PostTaskListReview()
        
        print("1. Testing modified files detection:")
        files = reviewer.get_modified_files("test_session")
        print(f"   Found {len(files)} modified files")
        if files:
            print(f"   Sample: {files[:3]}")
            
        print("\n2. Testing task completion check:")
        complete, summary = reviewer.check_all_tasks_complete("test_session")
        print(f"   All complete: {complete}")
        print(f"   Summary: {summary}")
        
        print("\n3. Testing review trigger conditions:")
        should_run = reviewer.should_trigger_review()
        print(f"   Should trigger: {should_run}")
        
        print("\n4. Testing review context preparation:")
        context = {
            "session_id": "test_session",
            "task_summary": {"total_tasks": 5, "completed_tasks": 5},
            "timestamp": datetime.now().isoformat(),
            "trigger": "test"
        }
        print(f"   Context: {json.dumps(context, indent=2)}")
        
        print("\n=== Test Complete ===")
    else:
        # Run the async main function
        asyncio.run(main())