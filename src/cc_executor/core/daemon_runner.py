"""
Daemon runner for CC Executor server.

This module handles proper daemonization of the uvicorn server,
ensuring it continues running after the CLI command exits.
"""

import os
import sys
import signal
import atexit
from pathlib import Path

import daemon
from daemon import pidfile
import uvicorn
from .main import app  # Import the FastAPI app


class DaemonRunner:
    def __init__(self, pid_file_path: str, log_file_path: str, host: str, port: int):
        self.pid_file_path = pid_file_path
        self.log_file_path = log_file_path
        self.host = host
        self.port = port
        self.pidfile = pidfile.TimeoutPIDLockFile(self.pid_file_path)

    def _run_server(self):
        """This is the function that will run inside the daemon context."""
        # This code runs in the detached daemon process
        uvicorn.run(
            app,
            host=self.host,
            port=self.port,
            log_config=None,  # Uvicorn logging can be tricky in daemons, let daemon handle it
        )

    def start(self):
        """Start the daemon."""
        if self.pidfile.is_locked():
            print(f"Server is already running (PID: {self.pidfile.read_pid()}).")
            sys.exit(1)

        print(f"Starting server in background. Logs at: {self.log_file_path}")
        
        # Ensure the log directory exists
        Path(self.log_file_path).parent.mkdir(parents=True, exist_ok=True)
        log_file = open(self.log_file_path, 'a+')

        context = daemon.DaemonContext(
            pidfile=self.pidfile,
            stdout=log_file,
            stderr=log_file,
            working_directory=os.getcwd(),
            files_preserve=[log_file]  # Important: keep the log file open
        )

        with context:
            self._run_server()

    def stop(self):
        """Stop the daemon."""
        if not self.pidfile.is_locked():
            print("Server is not running.")
            return

        pid = self.pidfile.read_pid()
        print(f"Stopping server (PID: {pid})...")
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            print(f"Process with PID {pid} not found. Cleaning up stale PID file.")
        except Exception as e:
            print(f"Error stopping process: {e}")
        
        # Make sure the PID file is removed
        self.pidfile.break_lock()
        print("Server stopped.")

    def status(self):
        """Check the status of the daemon."""
        if self.pidfile.is_locked():
            pid = self.pidfile.read_pid()
            # Verify process is actually running
            try:
                os.kill(pid, 0)  # Signal 0 doesn't kill, just checks
                print(f"Server is running (PID: {pid}).")
                return True
            except ProcessLookupError:
                print(f"Server PID file exists but process {pid} is not running. Cleaning up.")
                self.pidfile.break_lock()
                return False
        else:
            print("Server is not running.")
            return False