#!/usr/bin/env python3
"""
Server Process Management Utility for CC Executor.

This module provides utilities to manage MCP server processes, preventing
port conflicts and orphaned processes. It includes functionality to:
- Find and kill existing server processes
- Start servers with proper cleanup
- Manage port allocation
- Handle process lifecycle

This solves the common problem of orphaned MCP server instances causing
connection failures and port conflicts.
"""

import os
import sys
import asyncio
import signal
import subprocess
import time
import psutil
import socket
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO")


class ServerManager:
    """Manages MCP server processes with proper lifecycle control."""
    
    def __init__(self, server_name: str = "mcp_cc_execute", default_port: int = 8002):
        """
        Initialize the server manager.
        
        Args:
            server_name: Name pattern to identify server processes
            default_port: Default port for the server
        """
        self.server_name = server_name
        self.default_port = default_port
        self.server_process: Optional[subprocess.Popen] = None
        
    def find_server_processes(self) -> List[Dict[str, Any]]:
        """
        Find all running server processes matching the server name.
        
        Returns:
            List of process info dicts with pid, name, cmdline, etc.
        """
        processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                try:
                    # Check if process matches our server
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and any(self.server_name in arg for arg in cmdline):
                        processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cmdline': ' '.join(cmdline),
                            'create_time': proc.info['create_time'],
                            'age': time.time() - proc.info['create_time']
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            logger.error(f"Error finding processes: {e}")
            
        return processes
    
    def is_port_in_use(self, port: int) -> bool:
        """Check if a port is currently in use."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('', port))
                return False
            except OSError:
                return True
    
    def find_available_port(self, start_port: int = 8002, max_attempts: int = 10) -> Optional[int]:
        """
        Find an available port starting from start_port.
        
        Args:
            start_port: Port to start searching from
            max_attempts: Maximum number of ports to try
            
        Returns:
            Available port number or None if none found
        """
        for offset in range(max_attempts):
            port = start_port + offset
            if not self.is_port_in_use(port):
                return port
        return None
    
    async def kill_server_processes(self, force: bool = False) -> int:
        """
        Kill all running server processes.
        
        Args:
            force: Use SIGKILL instead of SIGTERM
            
        Returns:
            Number of processes killed
        """
        processes = self.find_server_processes()
        killed_count = 0
        
        for proc_info in processes:
            pid = proc_info['pid']
            age_minutes = proc_info['age'] / 60
            
            logger.info(f"Found server process: PID={pid}, Age={age_minutes:.1f}min")
            logger.debug(f"  Command: {proc_info['cmdline']}")
            
            try:
                proc = psutil.Process(pid)
                
                if force:
                    proc.kill()  # SIGKILL
                    logger.info(f"Force killed process {pid}")
                else:
                    proc.terminate()  # SIGTERM
                    logger.info(f"Terminated process {pid}")
                    
                    # Wait up to 5 seconds for graceful shutdown
                    try:
                        proc.wait(timeout=5)
                    except psutil.TimeoutExpired:
                        logger.warning(f"Process {pid} didn't terminate gracefully, force killing")
                        proc.kill()
                        
                killed_count += 1
                
            except psutil.NoSuchProcess:
                logger.info(f"Process {pid} already terminated")
            except Exception as e:
                logger.error(f"Error killing process {pid}: {e}")
                
        if killed_count > 0:
            # Wait a moment for ports to be released
            await asyncio.sleep(0.5)
            
        return killed_count
    
    async def ensure_clean_start(self, port: Optional[int] = None) -> int:
        """
        Ensure a clean start by killing existing processes and finding available port.
        
        Args:
            port: Preferred port (will find available if not specified or in use)
            
        Returns:
            Port number that will be used
        """
        # Kill existing processes
        killed = await self.kill_server_processes()
        if killed > 0:
            logger.info(f"Killed {killed} existing server process(es)")
            
        # Determine port to use
        if port is None:
            port = self.default_port
            
        if self.is_port_in_use(port):
            logger.warning(f"Port {port} is in use, finding alternative")
            available_port = self.find_available_port(port)
            if available_port:
                logger.info(f"Using port {available_port}")
                return available_port
            else:
                raise RuntimeError(f"No available ports found starting from {port}")
                
        return port
    
    async def start_server(
        self,
        server_script: str,
        port: Optional[int] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None
    ) -> Tuple[subprocess.Popen, int]:
        """
        Start the MCP server with proper cleanup.
        
        Args:
            server_script: Path to server script
            port: Port to use (will ensure availability)
            env: Environment variables
            cwd: Working directory
            
        Returns:
            Tuple of (process, port)
        """
        # Ensure clean start
        port = await self.ensure_clean_start(port)
        
        # Prepare environment
        server_env = os.environ.copy()
        if env:
            server_env.update(env)
        server_env['DEFAULT_PORT'] = str(port)
        
        # Start server
        logger.info(f"Starting {self.server_name} on port {port}")
        
        cmd = [sys.executable, server_script]
        self.server_process = subprocess.Popen(
            cmd,
            env=server_env,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid  # Create new process group
        )
        
        # Wait a moment for server to start
        await asyncio.sleep(1)
        
        # Check if server started successfully
        if self.server_process.poll() is not None:
            stdout, stderr = self.server_process.communicate()
            raise RuntimeError(
                f"Server failed to start:\n"
                f"stdout: {stdout.decode()}\n"
                f"stderr: {stderr.decode()}"
            )
            
        logger.info(f"Server started successfully: PID={self.server_process.pid}")
        return self.server_process, port
    
    async def stop_server(self, timeout: float = 10) -> None:
        """
        Stop the managed server process gracefully.
        
        Args:
            timeout: Maximum time to wait for shutdown
        """
        if not self.server_process:
            return
            
        if self.server_process.poll() is not None:
            logger.info("Server already stopped")
            return
            
        logger.info(f"Stopping server PID={self.server_process.pid}")
        
        # Try graceful shutdown first
        self.server_process.terminate()
        
        try:
            await asyncio.wait_for(
                asyncio.create_task(self._wait_for_process()),
                timeout=timeout
            )
            logger.info("Server stopped gracefully")
        except asyncio.TimeoutError:
            logger.warning("Server didn't stop gracefully, force killing")
            self.server_process.kill()
            await self._wait_for_process()
            
        self.server_process = None
    
    async def _wait_for_process(self) -> None:
        """Wait for the server process to exit."""
        if self.server_process:
            while self.server_process.poll() is None:
                await asyncio.sleep(0.1)
    
    def __del__(self):
        """Cleanup on deletion."""
        if self.server_process and self.server_process.poll() is None:
            try:
                self.server_process.terminate()
            except:
                pass


async def main():
    """Command-line interface for server management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP Server Process Manager")
    parser.add_argument("action", choices=["list", "kill", "clean"], 
                       help="Action to perform")
    parser.add_argument("--server", default="mcp_cc_execute",
                       help="Server name pattern (default: mcp_cc_execute)")
    parser.add_argument("--force", action="store_true",
                       help="Force kill processes")
    
    args = parser.parse_args()
    
    manager = ServerManager(args.server)
    
    if args.action == "list":
        processes = manager.find_server_processes()
        if processes:
            print(f"Found {len(processes)} {args.server} process(es):")
            for proc in processes:
                age_min = proc['age'] / 60
                print(f"  PID: {proc['pid']}, Age: {age_min:.1f}min")
                print(f"    Command: {proc['cmdline']}")
        else:
            print(f"No {args.server} processes found")
            
    elif args.action == "kill":
        killed = await manager.kill_server_processes(force=args.force)
        print(f"Killed {killed} process(es)")
        
    elif args.action == "clean":
        # Kill processes and check ports
        killed = await manager.kill_server_processes()
        print(f"Killed {killed} process(es)")
        
        # Check default ports
        for port in range(8002, 8005):
            if manager.is_port_in_use(port):
                print(f"Port {port}: IN USE")
            else:
                print(f"Port {port}: available")


if __name__ == "__main__":
    asyncio.run(main())