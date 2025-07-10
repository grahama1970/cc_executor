"""
Daemon utility for proper process daemonization.

This module implements the classic Unix double-fork pattern to properly
daemonize a process, ensuring it continues running after the parent exits.
"""

import os
import sys
import atexit
import signal
from pathlib import Path


def daemonize(pidfile: Path, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
    """
    Daemonize the current process using double-fork.
    
    Args:
        pidfile: Path to write the daemon PID
        stdin: Input stream path
        stdout: Output stream path  
        stderr: Error stream path
    """
    # First fork
    try:
        pid = os.fork()
        if pid > 0:
            # Exit first parent
            sys.exit(0)
    except OSError as e:
        sys.stderr.write(f"fork #1 failed: {e}\n")
        sys.exit(1)
    
    # Decouple from parent environment
    os.chdir("/")
    os.setsid()
    os.umask(0)
    
    # Second fork
    try:
        pid = os.fork()
        if pid > 0:
            # Exit from second parent
            sys.exit(0)
    except OSError as e:
        sys.stderr.write(f"fork #2 failed: {e}\n")
        sys.exit(1)
    
    # Redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()
    si = open(stdin, 'r')
    so = open(stdout, 'a+')
    se = open(stderr, 'a+')
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())
    
    # Write pidfile
    atexit.register(lambda: os.remove(pidfile))
    pid = str(os.getpid())
    with open(pidfile, 'w+') as f:
        f.write(f"{pid}\n")
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))


def start_daemon(target_func, pidfile: Path, logfile: Path = None):
    """
    Start a function as a daemon.
    
    Args:
        target_func: Function to run as daemon
        pidfile: Path to PID file
        logfile: Optional log file path
    """
    # Check if already running
    if pidfile.exists():
        with open(pidfile, 'r') as f:
            pid = int(f.read().strip())
        
        # Check if process is actually running
        try:
            os.kill(pid, 0)
            print(f"Daemon already running with PID {pid}")
            return
        except OSError:
            # Stale PID file
            pidfile.unlink()
    
    # Start daemon
    print(f"Starting daemon...")
    
    if not logfile:
        logfile = pidfile.parent / f"{pidfile.stem}.log"
    
    # Fork to create daemon
    daemonize(
        pidfile,
        stdout=str(logfile),
        stderr=str(logfile)
    )
    
    # This code runs in the daemon process
    target_func()


def stop_daemon(pidfile: Path):
    """Stop a daemon by PID file."""
    if not pidfile.exists():
        print("Daemon not running")
        return
    
    with open(pidfile, 'r') as f:
        pid = int(f.read().strip())
    
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"Stopped daemon with PID {pid}")
    except OSError as e:
        print(f"Failed to stop daemon: {e}")
        
    # Clean up PID file
    if pidfile.exists():
        pidfile.unlink()