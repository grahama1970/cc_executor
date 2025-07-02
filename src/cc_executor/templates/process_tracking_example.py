#!/usr/bin/env python3
"""Example of proper process tracking for stress tests."""

import asyncio
import os
import signal
import subprocess
import psutil
from datetime import datetime
from typing import Dict, List, Set

class ProcessTrackingStressTest:
    """Stress test with proper process lifecycle management."""
    
    def __init__(self):
        # Core test state
        self.ws_process = None
        self.ws_port = 8004
        
        # CRITICAL: Process tracking state
        self.spawned_processes: Dict[int, str] = {}  # PID -> description
        self.claude_processes: Set[int] = set()      # PIDs of Claude CLI processes
        self.cleanup_performed = False
        
        # Track start time for finding our processes
        self.test_start_time = datetime.now()
        
    async def start_websocket_handler(self):
        """Start websocket handler with process tracking."""
        print(f"Starting websocket_handler.py on port {self.ws_port}...")
        
        # Start the process
        self.ws_process = subprocess.Popen(
            [sys.executable, "src/cc_executor/core/websocket_handler.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=os.setsid  # Create new process group
        )
        
        # Track the websocket handler
        self.spawned_processes[self.ws_process.pid] = "websocket_handler.py"
        print(f"  Tracked WebSocket handler PID: {self.ws_process.pid}")
        
        # Monitor for Claude processes spawned by our handler
        self._start_process_monitor()
        
        return True
        
    def _start_process_monitor(self):
        """Monitor for new Claude processes spawned during our test."""
        # Get baseline Claude processes before our test
        baseline_pids = set()
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'claude' in cmdline and proc.info['create_time'] < self.test_start_time.timestamp():
                    baseline_pids.add(proc.info['pid'])
            except:
                pass
        
        self.baseline_claude_pids = baseline_pids
        print(f"  Baseline: {len(baseline_pids)} existing Claude processes")
        
    def track_new_claude_process(self):
        """Check for new Claude processes and track them."""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 'ppid']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'claude -p' in cmdline:
                    pid = proc.info['pid']
                    
                    # Is this a new process spawned after our test started?
                    if (pid not in self.baseline_claude_pids and 
                        pid not in self.claude_processes and
                        proc.info['create_time'] >= self.test_start_time.timestamp()):
                        
                        # Track it
                        self.claude_processes.add(pid)
                        self.spawned_processes[pid] = f"claude_cli_{pid}"
                        print(f"  Tracked new Claude process PID: {pid}")
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
    async def execute_test(self, test):
        """Execute test with process tracking."""
        # Check for new processes before executing
        self.track_new_claude_process()
        
        # ... execute test via websocket ...
        
        # Check again after test
        self.track_new_claude_process()
        
    def cleanup_processes(self):
        """Clean up ONLY the processes we spawned."""
        if self.cleanup_performed:
            return
            
        print("\n🧹 Cleaning up test processes...")
        print(f"  Tracked processes: {len(self.spawned_processes)}")
        
        # First, terminate gracefully
        for pid, desc in list(self.spawned_processes.items()):
            try:
                proc = psutil.Process(pid)
                if proc.is_running():
                    print(f"  Terminating {desc} (PID {pid})")
                    proc.terminate()
            except psutil.NoSuchProcess:
                print(f"  {desc} (PID {pid}) already gone")
                del self.spawned_processes[pid]
            except Exception as e:
                print(f"  Error terminating {desc}: {e}")
        
        # Wait for graceful shutdown
        if self.spawned_processes:
            print("  Waiting 5s for graceful shutdown...")
            await asyncio.sleep(5)
            
            # Force kill any remaining
            for pid, desc in list(self.spawned_processes.items()):
                try:
                    proc = psutil.Process(pid)
                    if proc.is_running():
                        print(f"  Force killing {desc} (PID {pid})")
                        proc.kill()
                except:
                    pass
                    
        # Kill process group if websocket handler still exists
        if self.ws_process and self.ws_process.poll() is None:
            try:
                pgid = os.getpgid(self.ws_process.pid)
                print(f"  Killing process group {pgid}")
                os.killpg(pgid, signal.SIGKILL)
            except:
                pass
                
        self.cleanup_performed = True
        print("  ✅ Cleanup complete")
        
    def __del__(self):
        """Ensure cleanup on object destruction."""
        if not self.cleanup_performed:
            self.cleanup_processes()

# Usage in stress test:
class ImprovedPreflightStressTest(ProcessTrackingStressTest):
    """Preflight test with proper process management."""
    
    async def run_all_tests(self):
        """Run tests with guaranteed cleanup."""
        try:
            # Start handler
            await self.start_websocket_handler()
            
            # Run tests
            for test in self.tests:
                await self.execute_test(test)
                
        finally:
            # ALWAYS clean up our processes
            self.cleanup_processes()