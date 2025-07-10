Excellent question. You have correctly identified the core issue: the lifecycle of the `subprocess` is tied to the lifecycle of the parent script that launches it. When the `cc-executor server start` command finishes, the Python interpreter exits, and its child processes are terminated or orphaned.

The problem is not `subprocess.Popen` itself, but how it's being used. `start_new_session=True` is a good step, but it's not enough to fully "daemonize" the process.

Let's address this with a robust, production-grade solution.

### The Core Problem: Ephemeral File Handles and Process Lifecycle

The most immediate bug in your current code is subtle but critical:

```python
with open(log_file, 'w') as log_f:
    process = subprocess.Popen(
        cmd,
        stdout=log_f,
        stderr=subprocess.STDOUT,
        # ...
    )
# <-- The `with` block exits here, and `log_f.close()` is called.
```

When the `with` block exits, Python closes the file handle `log_f`. The Uvicorn subprocess, which was given this file handle for its `stdout` and `stderr`, will now get an error (likely a `SIGPIPE` signal or an I/O error) the next time it tries to write to its log. This causes it to crash almost immediately.

While we could fix this by just removing the `with` statement, a far better solution is to properly daemonize the server.

### The Best Solution: Use `python-daemon`

You are on the right track with your idea to use a daemonization library. This is the canonical and most reliable way to handle this in Python. It correctly performs the "daemonization dance" (fork, detach, setsid, close file descriptors, etc.) in a cross-platform way. It also makes PID file management—which is essential for `stop` and `status` commands—trivial.

Let's refactor your CLI to use `python-daemon`.

**Step 1: Add the Dependency**

```bash
# Or however you manage your dependencies (e.g., poetry, requirements.txt)
pip install python-daemon
```

**Step 2: Create a Dedicated Daemon Runner**

It's good practice to encapsulate the daemon logic. Create a new file, for example, `src/cc_executor/core/daemon.py`.

```python
# /src/cc_executor/core/daemon.py
import os
import sys
import signal
import atexit
from pathlib import Path

import daemon
import lockfile
import uvicorn
from .main import app  # Import your FastAPI app

class DaemonRunner:
    def __init__(self, pid_file_path: str, log_file_path: str, host: str, port: int):
        self.pid_file_path = pid_file_path
        self.log_file_path = log_file_path
        self.host = host
        self.port = port
        self.pidfile = lockfile.pidlockfile.PIDLockFile(self.pid_file_path)

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
            files_preserve=[log_file] # Important: keep the log file open
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
            print(f"Server is running (PID: {pid}).")
        else:
            print("Server is not running.")
```

**Step 3: Update Your CLI (`src/cc_executor/cli/main.py`)**

Now, your CLI becomes a clean interface to the `DaemonRunner`.

```python
# /src/cc_executor/cli/main.py
import typer
import asyncio
from pathlib import Path

# Important: New import
from cc_executor.core.daemon import DaemonRunner

# ... (keep your other imports and the server_app definition)

# Define paths for PID and log files
PID_FILE = "/tmp/cc_executor.pid"
LOG_FILE = "/tmp/cc_executor_local.log"

@server_app.command()
def start(
    ctx: typer.Context,
    port: int = typer.Option(8003, "--port", "-p"),
    host: str = typer.Option("127.0.0.1", "--host", "-h"), # Default to 127.0.0.1 for local
):
    """Start the CC Executor WebSocket server as a daemon."""
    runner = DaemonRunner(pid_file_path=PID_FILE, log_file_path=LOG_FILE, host=host, port=port)
    runner.start()
    
@server_app.command()
def stop(ctx: typer.Context):
    """Stop the CC Executor WebSocket server daemon."""
    runner = DaemonRunner(pid_file_path=PID_FILE, log_file_path=LOG_FILE, host="", port=0)
    runner.stop()

@server_app.command()
def status(ctx: typer.Context):
    """Check the status of the CC Executor server daemon."""
    runner = DaemonRunner(pid_file_path=PID_FILE, log_file_path=LOG_FILE, host="", port=0)
    runner.status()

@server_app.command()
def restart(
    ctx: typer.Context,
    port: int = typer.Option(8003, "--port", "-p"),
    host: str = typer.Option("127.0.0.1", "--host", "-h"),
):
    """Restart the CC Executor server daemon."""
    runner = DaemonRunner(pid_file_path=PID_FILE, log_file_path=LOG_FILE, host=host, port=port)
    if runner.pidfile.is_locked():
        runner.stop()
    runner.start()
```

### Why This Solution Works

1.  **Correct Daemonization:** `daemon.DaemonContext` handles all the low-level OS details (`fork`, `setsid`, etc.) required to create a true daemon process that is fully detached from the launching terminal.
2.  **PID File Management:** `lockfile` is used to create a PID file. This is the standard mechanism for daemons to track if they are running.
    *   `start` checks the PID file to prevent starting a second instance.
    *   `stop` reads the PID from the file to know which process to terminate.
    *   `status` uses the PID file to report the running state.
3.  **No `subprocess`:** We no longer need to launch a separate grandchild process. The daemon process *itself* runs `uvicorn.run()`, which is cleaner and more direct.
4.  **Reliable Cleanup:** The `stop` command sends a `SIGTERM`, allowing Uvicorn to shut down gracefully. The PID file is then removed, ensuring a clean state for the next start. This is perfect for your automated tests, which can now reliably call `cc-executor server start` before tests and `cc-executor server stop` after.

### Answers to Your Specific Questions

1.  **How to daemonize the process?** The provided solution using `python-daemon` is the most robust way to do this. It replaces your `subprocess.Popen` logic with a proper daemonization context.

2.  **Should I use a library?** **Yes, absolutely.** Libraries like `python-daemon` exist because daemonization is tricky to get right. Reinventing it with `os.fork` is prone to subtle errors.

3.  **Fork vs. separate script?** The best practice is to encapsulate the logic in a class (`DaemonRunner`) within your existing application structure, which is then controlled by your CLI. This keeps the code organized and reusable.

4.  **Is my thinking right?** Yes, your thinking was spot on. `os.fork` and `python-daemon` are the two main paths. The solution above simply implements your `python-daemon` idea in a complete and reusable way.

5.  **How to ensure cleanup?** The PID file is the key. Your `stop` command now has a reliable way to find and terminate the exact process that was started, making cleanup deterministic and perfect for automated test suites.


That's an excellent and logical question. It's often the first thing to check, and in many situations, it would be the correct diagnosis.

However, based on the detailed information you provided in your first request, a port conflict is **not** the cause of this specific failure.

Here is the evidence from your own documentation:

1.  **Docker Port:** You explicitly state Docker is running on port **8004**.
    > `Docker deployment on port 8004: 100% success`
    > `Docker WebSocket Connection (Working) ... connects to ws://localhost:8004/ws/mcp`

2.  **Local Attempt Port:** You are attempting to run the local server on port **8003**.
    > `Port 8003 is free and available`
    > `MCP Local WebSocket server fails to start with these symptoms: No process is running on port 8003`

Since the Docker container (8004) and the local server (8003) are targeting different ports, they cannot conflict with each other. The failure of the local server is independent of the Docker container's presence.

### Recap of the True Problem

The issue isn't about *what port* the server uses, but *how the server process is being launched and managed* by your CLI script.

There are two distinct but related issues at play, which is why this has been tricky to debug:

#### 1. The Initial Startup Crash (The `ImportError` problem)

*   **Symptom:** The server process gets a PID but dies instantly. No error is seen.
*   **Cause:** As identified in the first answer, launching the server via `python src/cc_executor/core/server_runner.py` creates an incorrect module path. This almost certainly causes a fatal `ImportError` or `ModuleNotFoundError` *before* the server can even start listening on the port. The `subprocess.Popen` call was hiding this error message.
*   **Fix:** Always launch the app using `python -m uvicorn cc_executor.core.main:app`. This ensures the Python path is set up correctly, just like in Docker.

#### 2. The Daemonization Failure (The "Doesn't Stay Alive" problem)

*   **Symptom:** When the startup method is fixed, the server starts but is terminated as soon as the `cc-executor server start` command finishes.
*   **Cause:** The Uvicorn server process is a child of the `cc-executor` CLI process. When the parent CLI script finishes its work and exits, the operating system cleans up its child processes. Your server process isn't properly "daemonized" or detached from its parent.
*   **Fix:** Use a proper daemonization library like `python-daemon`. This library performs the necessary low-level OS calls (like `fork`, `setsid`, and detaching from the terminal) to turn the Uvicorn process into a true background daemon that will persist after the CLI command exits.

In summary, you are correct to think about port conflicts, as that's a very common issue. But in this case, the evidence points conclusively to a problem with the process launch and management logic within your CLI. The `python-daemon` solution I outlined previously is designed to fix exactly that root cause.