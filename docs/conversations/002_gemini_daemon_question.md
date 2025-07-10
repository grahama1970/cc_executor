# Gemini Question: Fix MCP Local Server Daemon Issue

## Context
I have a FastAPI/Uvicorn WebSocket server that works perfectly when run manually but fails in automated tests because the server process doesn't stay alive. The issue is with the CLI command implementation that starts the server.

## Current Implementation

### CLI Command (src/cc_executor/cli/main.py)
```python
@server_app.command()
def start(
    ctx: typer.Context,
    port: int = typer.Option(8003, "--port", "-p", help="Port to run server on"),
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind to"),
):
    """Start the CC Executor WebSocket server with automatic cleanup."""
    console = ctx.obj["console"]
    
    console.print(f"\n[cyan]Preparing to start CC Executor on {host}:{port}[/cyan]")
    
    # Use asyncio.run to execute the async function
    try:
        asyncio.run(start_server_async(host, port, console))
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Server error: {e}[/red]")
        raise typer.Exit(code=1)

async def start_server_async(host: str, port: int, console):
    """Async function to start the server with cleanup."""
    # Initialize ServerManager for cleanup
    server_manager = ServerManager("cc_executor")
    
    # Clean up any existing processes on the port
    await server_manager.cleanup()
    
    # Find available port
    actual_port = find_available_port(port)
    if actual_port != port:
        console.print(f"[yellow]Port {port} in use, using {actual_port}[/yellow]")
    
    # Build command - use uvicorn directly as recommended by Gemini
    cmd = [
        sys.executable,
        "-m", "uvicorn", 
        "cc_executor.core.main:app",
        "--host", host,
        "--port", str(actual_port)
    ]
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parent.parent.parent)
    
    # Start server process with output to log file
    log_file = f"/tmp/cc_executor_local.log"
    console.print(f"[green]Starting server on {host}:{actual_port}[/green]")
    
    with open(log_file, 'w') as log_f:
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            start_new_session=True  # Create new process group
        )
    
    # The process dies immediately after this function returns!
```

## The Problem

1. When run via `cc-executor server start`, the server process starts but terminates as soon as the CLI command finishes
2. Using `nohup cc-executor server start &` doesn't help - the command blocks waiting for the server
3. The server works perfectly when run directly: `python -m uvicorn cc_executor.core.main:app --host 0.0.0.0 --port 8003`

## Current Test Results

```python
# Stress test shows 0% success for MCP local
"mcp_local": {
  "total_tests": 3,
  "passed": 0,
  "failed": 3,
  "success_rate": "0.0%",
  "avg_duration": "0.01s"  # Fails immediately - connection refused
}
```

## What I've Tried

1. Using `subprocess.Popen` with `start_new_session=True`
2. Redirecting stdout/stderr to a log file to prevent blocking
3. Using `nohup` when calling the CLI command
4. Running the start command in background with `&`

## Questions

1. **How can I modify the CLI command to properly daemonize the uvicorn server process so it continues running after the CLI command exits?**

2. **Should I use a library like `python-daemon` or `daemonize`, or is there a simpler approach with subprocess?**

3. **Would it be better to have the CLI command fork and detach, or should I create a separate daemon script?**

4. **Here's what I'm thinking - is this the right approach?**
   ```python
   # Option 1: Fork and detach
   pid = os.fork()
   if pid == 0:  # Child process
       os.setsid()  # Create new session
       # Start uvicorn here
       
   # Option 2: Use python-daemon
   import daemon
   with daemon.DaemonContext():
       uvicorn.run(app, host=host, port=port)
   ```

5. **How can I ensure the daemon process is properly cleaned up when running `cc-executor server stop`?**

Please provide a complete, working solution that will make `cc-executor server start` work correctly in automated tests.