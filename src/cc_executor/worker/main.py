#!/usr/bin/env python3
"""
Secure worker process for CC Executor.

This worker runs in an isolated container and executes tasks from a Redis queue.
It provides additional security layers beyond the main API container.
"""

import os
import sys
import asyncio
import json
import time
import signal
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

import redis.asyncio as redis
from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stderr, level=os.environ.get("LOG_LEVEL", "INFO"))


class SecureWorker:
    """Secure worker for executing tasks in isolation."""
    
    def __init__(self):
        self.redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        self.worker_id = f"worker_{os.getpid()}"
        self.execution_timeout = int(os.environ.get("EXECUTION_TIMEOUT", "300"))
        self.workspace = Path("/workspace")
        self.output_dir = Path("/output")
        self.running = True
        self.current_task = None
        
    async def connect(self):
        """Connect to Redis."""
        self.redis = await redis.from_url(self.redis_url, decode_responses=True)
        logger.info(f"Worker {self.worker_id} connected to Redis")
        
    async def cleanup_workspace(self):
        """Clean the workspace directory."""
        try:
            # Remove all files in workspace
            for item in self.workspace.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
            logger.debug("Workspace cleaned")
        except Exception as e:
            logger.error(f"Failed to clean workspace: {e}")
            
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task in the isolated environment.
        
        Args:
            task: Task dictionary with command, timeout, etc.
            
        Returns:
            Result dictionary with output, exit_code, etc.
        """
        task_id = task.get("id", "unknown")
        command = task.get("command", "")
        timeout = min(task.get("timeout", self.execution_timeout), self.execution_timeout)
        
        logger.info(f"Executing task {task_id}: {command[:100]}...")
        
        # Clean workspace before execution
        await self.cleanup_workspace()
        
        # Create a unique subdirectory for this task
        task_dir = self.workspace / f"task_{task_id}"
        task_dir.mkdir(exist_ok=True)
        
        start_time = time.time()
        
        try:
            # Execute command in the task directory
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=str(task_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                # Security: limit resources
                preexec_fn=os.setsid,  # Create new process group
                env={
                    **os.environ,
                    "HOME": str(task_dir),
                    "TMPDIR": str(task_dir),
                    "PYTHONPATH": "",  # Clear Python path
                    "PATH": "/usr/local/bin:/usr/bin:/bin",  # Minimal PATH
                }
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout
                )
                exit_code = proc.returncode
            except asyncio.TimeoutError:
                # Kill process group on timeout
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except:
                    pass
                exit_code = -1
                stdout = b""
                stderr = b"Execution timed out"
                
            execution_time = time.time() - start_time
            
            # Collect any output files (with size limits)
            output_files = {}
            max_file_size = 1024 * 1024  # 1MB per file
            max_total_size = 10 * 1024 * 1024  # 10MB total
            total_size = 0
            
            for file_path in task_dir.rglob("*"):
                if file_path.is_file():
                    rel_path = file_path.relative_to(task_dir)
                    file_size = file_path.stat().st_size
                    
                    if total_size + file_size > max_total_size:
                        logger.warning(f"Output size limit reached, skipping {rel_path}")
                        break
                        
                    if file_size <= max_file_size:
                        try:
                            output_files[str(rel_path)] = file_path.read_text()
                            total_size += file_size
                        except:
                            # Binary file or read error
                            output_files[str(rel_path)] = f"<binary file, {file_size} bytes>"
                    else:
                        output_files[str(rel_path)] = f"<file too large, {file_size} bytes>"
                        
            return {
                "task_id": task_id,
                "exit_code": exit_code,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "execution_time": execution_time,
                "output_files": output_files,
                "completed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            return {
                "task_id": task_id,
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "execution_time": time.time() - start_time,
                "error": str(e),
                "completed_at": datetime.utcnow().isoformat()
            }
        finally:
            # Always clean up
            await self.cleanup_workspace()
            
    async def process_tasks(self):
        """Main task processing loop."""
        logger.info(f"Worker {self.worker_id} starting task processing")
        
        while self.running:
            try:
                # Block waiting for task (with timeout for graceful shutdown)
                task_data = await self.redis.blpop("cc_executor:task_queue", timeout=5)
                
                if not task_data:
                    continue
                    
                _, task_json = task_data
                task = json.loads(task_json)
                self.current_task = task
                
                # Update task status
                await self.redis.hset(
                    f"cc_executor:task:{task['id']}",
                    mapping={
                        "status": "processing",
                        "worker": self.worker_id,
                        "started_at": datetime.utcnow().isoformat()
                    }
                )
                
                # Execute task
                result = await self.execute_task(task)
                
                # Save result
                await self.redis.hset(
                    f"cc_executor:task:{task['id']}",
                    mapping={
                        "status": "completed",
                        "result": json.dumps(result),
                        "completed_at": datetime.utcnow().isoformat()
                    }
                )
                
                # Publish completion event
                await self.redis.publish(
                    f"cc_executor:task:{task['id']}:complete",
                    json.dumps(result)
                )
                
                logger.info(f"Task {task['id']} completed with exit code {result['exit_code']}")
                
            except Exception as e:
                logger.error(f"Error processing task: {e}")
                if self.current_task:
                    try:
                        await self.redis.hset(
                            f"cc_executor:task:{self.current_task['id']}",
                            mapping={
                                "status": "failed",
                                "error": str(e),
                                "completed_at": datetime.utcnow().isoformat()
                            }
                        )
                    except:
                        pass
                        
            finally:
                self.current_task = None
                
    async def shutdown(self):
        """Graceful shutdown."""
        logger.info(f"Worker {self.worker_id} shutting down")
        self.running = False
        
        if self.current_task:
            # Mark current task as interrupted
            try:
                await self.redis.hset(
                    f"cc_executor:task:{self.current_task['id']}",
                    mapping={
                        "status": "interrupted",
                        "error": "Worker shutdown",
                        "completed_at": datetime.utcnow().isoformat()
                    }
                )
            except:
                pass
                
        await self.redis.close()
        
    async def run(self):
        """Run the worker."""
        await self.connect()
        
        # Register signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))
            
        try:
            await self.process_tasks()
        except Exception as e:
            logger.error(f"Worker failed: {e}")
        finally:
            await self.shutdown()


async def main():
    """Main entry point."""
    worker = SecureWorker()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())