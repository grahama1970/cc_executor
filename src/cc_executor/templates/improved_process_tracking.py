#!/usr/bin/env python3
"""Improved process tracking implementation based on Perplexity and Gemini feedback."""

import asyncio
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Set, List, Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    print("⚠️ psutil not installed, process tracking will be limited")
    psutil = None
    PSUTIL_AVAILABLE = False

class ImprovedProcessTracker:
    """Robust process tracking with parent-child relationships and cross-platform support."""
    
    def __init__(self):
        self.ws_process = None
        self.ws_port = 8004
        self.ws_url = f"ws://localhost:{self.ws_port}/ws"
        
        # Process tracking state
        self.tracked_processes: Dict[int, str] = {}  # PID -> description
        self.cleanup_performed = False
        
        # Test identifier for marking our processes
        self.test_id = f"stress_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.test_env_var = "CLAUDE_STRESS_TEST_ID"
        
    async def start_websocket_handler(self):
        """Start websocket handler with improved process tracking."""
        print(f"Starting websocket_handler.py on port {self.ws_port}...")
        
        # Clean up port first
        await self._cleanup_port()
        
        # Prepare environment with test identifier
        env = os.environ.copy()
        env['PYTHONPATH'] = os.path.join(os.getcwd(), 'src')
        env['WS_PORT'] = str(self.ws_port)
        env[self.test_env_var] = self.test_id  # Mark our test processes
        
        handler_path = Path("src/cc_executor/core/websocket_handler.py")
        
        # Platform-specific process group creation
        creation_kwargs = {}
        if sys.platform == "win32":
            # Windows: Create new process group
            creation_kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            # Unix: Create new session
            creation_kwargs['preexec_fn'] = os.setsid
        
        # Start the process
        self.ws_process = subprocess.Popen(
            [sys.executable, str(handler_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,  # Separate stderr to avoid deadlocks
            text=True,
            env=env,
            **creation_kwargs
        )
        
        # Track the websocket handler
        self.tracked_processes[self.ws_process.pid] = "websocket_handler.py"
        print(f"  ✓ Started WebSocket handler PID: {self.ws_process.pid}")
        
        # Start async tasks to drain output streams (prevents deadlock)
        asyncio.create_task(self._drain_stream(self.ws_process.stdout, "STDOUT"))
        asyncio.create_task(self._drain_stream(self.ws_process.stderr, "STDERR"))
        
        # Wait for startup
        if not await self._wait_for_startup():
            await self.cleanup_processes()
            return False
            
        return True
    
    async def _drain_stream(self, stream, prefix):
        """Drain output stream to prevent deadlock."""
        try:
            while True:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, stream.readline
                )
                if not line:
                    break
                # Optionally log the output
                # print(f"[{prefix}] {line.strip()}")
        except Exception as e:
            print(f"Error draining {prefix}: {e}")
    
    async def _cleanup_port(self):
        """Clean up processes using the port."""
        if sys.platform == "win32":
            # Windows command to find process using port
            cmd = f"netstat -ano | findstr :{self.ws_port}"
        else:
            # Unix command
            cmd = f"lsof -ti:{self.ws_port}"
        
        try:
            result = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )
            stdout, _ = await result.communicate()
            
            if stdout:
                pids = stdout.decode().strip().split()
                for pid_str in pids:
                    try:
                        pid = int(pid_str.split()[-1] if sys.platform == "win32" else pid_str)
                        os.kill(pid, signal.SIGTERM)
                        print(f"  Killed process {pid} using port {self.ws_port}")
                    except:
                        pass
                        
                await asyncio.sleep(1)  # Wait for cleanup
        except:
            pass  # Port cleanup is best-effort
    
    async def _wait_for_startup(self, timeout=10):
        """Wait for WebSocket handler to be ready."""
        import websockets
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check if process is still alive
            if self.ws_process.poll() is not None:
                print(f"  ✗ Process died with exit code: {self.ws_process.returncode}")
                return False
            
            # Try to connect
            try:
                async with websockets.connect(self.ws_url, ping_timeout=None) as ws:
                    await ws.close()
                print(f"  ✓ WebSocket handler ready")
                return True
            except:
                await asyncio.sleep(0.5)
        
        print(f"  ✗ Timeout waiting for WebSocket handler")
        return False
    
    async def track_child_processes(self):
        """Track child processes using parent-child relationships."""
        if not PSUTIL_AVAILABLE or not self.ws_process:
            return []
        
        # Run psutil operations in thread to avoid blocking
        def get_children():
            children = []
            try:
                parent = psutil.Process(self.ws_process.pid)
                # Get all descendants recursively
                for child in parent.children(recursive=True):
                    # Double-check with our test ID if possible
                    try:
                        child_env = child.environ()
                        if child_env.get(self.test_env_var) == self.test_id:
                            children.append((child.pid, child.name(), child.cmdline()))
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        # If we can't check env, include if it's a child
                        children.append((child.pid, child.name(), child.cmdline()))
            except psutil.NoSuchProcess:
                pass  # Parent process already gone
            
            return children
        
        children = await asyncio.get_event_loop().run_in_executor(None, get_children)
        
        # Track new children
        new_count = 0
        for pid, name, cmdline in children:
            if pid not in self.tracked_processes:
                desc = f"{name}_{pid}"
                if cmdline and 'claude' in ' '.join(cmdline):
                    desc = f"claude_cli_{pid}"
                self.tracked_processes[pid] = desc
                new_count += 1
        
        if new_count > 0:
            print(f"  Tracked {new_count} new child process(es)")
        
        return children
    
    async def cleanup_processes(self):
        """Clean up all tracked processes."""
        if self.cleanup_performed:
            return
        
        print("\n🧹 Cleaning up test processes...")
        
        # Track any final child processes
        await self.track_child_processes()
        
        print(f"  Total tracked: {len(self.tracked_processes)} processes")
        
        # Phase 1: Graceful termination
        terminated = []
        for pid, desc in list(self.tracked_processes.items()):
            try:
                if PSUTIL_AVAILABLE:
                    proc = psutil.Process(pid)
                    if proc.is_running():
                        print(f"  Terminating {desc} (PID {pid})")
                        proc.terminate()
                        terminated.append(pid)
                else:
                    os.kill(pid, signal.SIGTERM)
                    terminated.append(pid)
            except (ProcessLookupError, psutil.NoSuchProcess):
                # Process already gone
                del self.tracked_processes[pid]
            except PermissionError:
                print(f"  ⚠️  No permission to terminate {desc} (PID {pid})")
            except Exception as e:
                print(f"  ⚠️  Error terminating {desc}: {e}")
        
        # Wait for graceful shutdown
        if terminated:
            print(f"  Waiting 3s for {len(terminated)} process(es) to terminate...")
            await asyncio.sleep(3)
            
            # Phase 2: Force kill remaining
            for pid in terminated:
                try:
                    if PSUTIL_AVAILABLE:
                        proc = psutil.Process(pid)
                        if proc.is_running():
                            print(f"  Force killing PID {pid}")
                            proc.kill()
                            # Wait for process to be reaped
                            proc.wait(timeout=1)
                    else:
                        os.kill(pid, signal.SIGKILL)
                except:
                    pass  # Process already gone or other error
        
        # Phase 3: Kill process group (Unix only)
        if sys.platform != "win32" and self.ws_process:
            try:
                if self.ws_process.poll() is None:
                    pgid = os.getpgid(self.ws_process.pid)
                    print(f"  Killing process group {pgid}")
                    os.killpg(pgid, signal.SIGKILL)
            except:
                pass
        
        # Wait for any processes to be reaped
        if self.ws_process:
            try:
                self.ws_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                print("  ⚠️  WebSocket handler didn't exit cleanly")
        
        self.cleanup_performed = True
        print("  ✅ Cleanup complete")
    
    def __del__(self):
        """Ensure cleanup on object destruction."""
        if not self.cleanup_performed:
            # Can't use async in __del__, so use sync cleanup
            try:
                asyncio.run(self.cleanup_processes())
            except:
                # Best effort cleanup
                for pid in list(self.tracked_processes.keys()):
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except:
                        pass