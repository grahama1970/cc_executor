Of course. This is an excellent and well-documented problem. The way you've structured the question makes it much easier to diagnose. Let's break it down.

### Executive Summary: The Most Likely Cause

The most likely cause of your local server failure is the **inconsistent and non-standard way you are launching the application locally**.

Your local startup method (`python src/cc_executor/core/server_runner.py`) creates a different Python module context than the standard method used in Docker (`python -m uvicorn cc_executor.core.main:app`). This inconsistency is the source of the `RuntimeWarning` and almost certainly leads to a fatal `ImportError` or a configuration error that is being silenced by your `subprocess.Popen` call.

The server isn't "crashing"; it's likely failing to start at all due to a module-level error, and the parent process isn't capturing the error output.

---

### Step-by-Step Debugging and Resolution Plan

Follow these steps to diagnose and fix the issue.

**Step 1: Run the Server Directly and Expose the Error**

Forget the CLI wrapper and `subprocess` for a moment. The goal is to see the raw error. Open your terminal, navigate to the root of your project (the directory containing `src/`), and run the *exact same command* that Docker uses.

```bash
# Ensure your virtual environment is activated
# From your project root directory

# This is the command that works in Docker. Run it locally.
python -m uvicorn cc_executor.core.main:app --host="127.0.0.1" --port=8003 --reload
```
*   I've changed `0.0.0.0` to `127.0.0.1` for local security, though either will work.
*   `--reload` is added for easier development; it will auto-restart the server on code changes.

This command will almost certainly fail, but **it will print the true error message to your console**. The most likely errors you'll see are:
*   `ImportError: attempted relative import with no known parent package`
*   `ModuleNotFoundError: No module named 'config'` (or some other module)
*   `KeyError` or `ValueError` from a configuration loader that depends on an environment variable not set in your local shell.

**Step 2: Address the Exposed Error**

*   **If it's an `ImportError`:** This confirms the module path issue. The fix is to *always* use the `python -m uvicorn` startup method, which correctly treats your `src` directory as a source root.
*   **If it's a `Configuration/KeyError`:** Your Docker container has environment variables set that your local shell does not. Use `docker exec <container_name> env` to list the environment variables inside the working container. Create a `.env` file locally and ensure all required variables are present. Uvicorn will automatically load `.env` files.

**Step 3: Refactor Your Application's Startup Logic**

The `server_runner.py` script and the complex logic in `main.py` are the root cause. Let's refactor to follow best practices.

**1. Clean up `src/cc_executor/core/main.py`**

This file should only define the FastAPI `app` object. It should not contain any startup logic or `if __name__ == "__main__"` blocks for running the server.

```python
# /src/cc_executor/core/main.py

# Keep all your FastAPI app creation logic
from fastapi import FastAPI
# ... your other imports and route setups

app = FastAPI(
    title=SERVICE_NAME,
    version=SERVICE_VERSION
)

# ... include your routers, middleware, etc.
# app.include_router(...)
# app.add_websocket_route(...)

# --- REMOVE THE ENTIRE if __name__ == "__main__": BLOCK ---
```

**2. Delete `src/cc_executor/core/server_runner.py`**

This file is a workaround and is no longer needed. The correct way to run the server is via the `uvicorn` command.

**3. Modify the CLI Start Command (`/src/cc_executor/cli/main.py`)**

Update your CLI to call Uvicorn directly. This is a much more robust and standard approach.

```python
# /src/cc_executor/cli/main.py
import subprocess
import sys
from pathlib import Path

# ... your other CLI logic for setting port, host, env ...

# Build the command to run Uvicorn as a module
cmd = [
    sys.executable,  # Ensures you use the python from the correct virtual env
    "-m", "uvicorn",
    "cc_executor.core.main:app", # The standard path to your app object
    "--host", host,
    "--port", str(actual_port),
    # Add other uvicorn flags as needed
    # e.g., "--ws-ping-interval", os.environ.get("WS_PING_INTERVAL", "20.0"),
]

# For debugging, it's better to run in the foreground.
# For production/background, Popen is fine, but you must handle stdout/stderr.
if debug:
    # In debug mode, run it in the foreground and see all output directly
    # The process will block the current shell, which is what you want for debugging.
    process = subprocess.run(cmd, env=env)
else:
    # When running in the background, ensure you have a proper logging strategy.
    # Piping to PIPE and not reading from it is how errors get lost.
    # It's better to redirect to log files.
    with open("mcp-server.log", "wb") as log_file:
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=log_file,
            stderr=log_file,
            start_new_session=True
        )

# ... rest of your code
```

---

### Detailed Answers to Your Questions

#### Question 1: Import and Module Issues

Yes, the `RuntimeWarning` is the smoke, and the immediate crash is the fire. It's telling you that Python is confused about your package structure. Running `python path/to/script.py` makes Python see `core` as a top-level directory, while your imports likely treat `cc_executor` as the top-level package. This leads to unpredictable behavior, most often `ImportError`.

**Fix:** The fix is not to change your imports, but to **change how you run the code**. Always use the `python -m <module_name>` syntax for runnable modules within a package, as this sets up the path context correctly. The refactoring in Step 3 solves this permanently.

#### Question 2: Process Management (Immediate Crash)

Common reasons for immediate crashes in this context:

1.  **Module-Level `ImportError`:** The most likely reason here. The Python interpreter fails to even compile the module and exits with an error code before Uvicorn's server loop can start.
2.  **Configuration Error:** The app tries to read a required environment variable or config file at the module level (i.e., outside any function). The file/variable is missing, an exception is raised, and the process dies.
3.  **Silenced Exceptions:** Your `subprocess.Popen` call with `stderr=subprocess.PIPE` is hiding the error. The child process writes its fatal error to stderr and exits. The parent process holds the other end of the pipe but never reads from it, so the error message is lost forever when the child process is reaped.

#### Question 3: Server Runner Architecture

Yes, the `server_runner.py` approach is problematic and an anti-pattern for exactly the reasons you've discovered. It breaks the standard execution model.

*   **a) Modify main.py to not have a usage function:** **Correct.** The file defining the `app` object should not be a runnable script.
*   **b) Use a different entry point:** **Correct.** The entry point for *running* the server should be `uvicorn`. Your CLI (`cli/main.py`) is the entry point for *initiating* the server start.
*   **c) Start uvicorn differently:** **Correct.** Start it via `python -m uvicorn ...` as shown in the refactoring plan.

#### Question 4: Environment Differences

The key differences causing Docker to work and local to fail are:

1.  **Startup Command:** (The #1 reason) `python -m uvicorn` vs. `python path/to/script.py`.
2.  **Environment Variables:** Docker has a sealed, explicit environment. Your local shell is implicit. A variable like `WS_PING_INTERVAL` or `DATABASE_URL` might be set in the Dockerfile/docker-compose but not in your local `.env` or shell profile.
3.  **Working Directory:** The `CMD` in a Dockerfile runs from the `WORKDIR`. Your local script runs from wherever you happen to call it, which can break relative paths to config files or templates.

#### Question 5: Debugging Strategy

Your instincts are good. Here is the optimal strategy:

1.  **Run in Foreground First (Highest Priority):** This is Step 1 of the plan above. **Always simplify first.** Run the process directly in your terminal to see the live, unfiltered output. This almost always reveals the root cause in seconds.
2.  **Check for Missing Dependencies/Config:** If the foreground run shows an error related to a missing module or a config value, that's your next target. Compare `pip freeze` from Docker with your local venv and check environment variables.
3.  **Add Logging (If Needed):** Once the server *can* start, adding more logging is useful for debugging application logic. But for startup failures, it's less useful because the crash often happens before your logging configuration is even loaded.
4.  **`strace`/`ltrace` (Last Resort):** These are powerful but overkill for this problem. You would only resort to these if you suspected a low-level issue with a C-extension or a system library, which is highly unlikely here. The problem is almost certainly at the Python level.