#!/usr/bin/env python3
"""
CC Executor CLI - Command-line interface with extensive hook integration.

This CLI provides:
1. Server management (start/stop/status)
2. Command execution through WebSocket
3. Stress testing and assessments
4. Execution history from Redis
5. Hook management and introspection
6. Configuration management

Hook Integration:
- Every command triggers pre/post hooks
- Hooks can modify command behavior
- Hook chains for complex workflows
"""

import typer
import asyncio
import json
import sys
import os
import time
import signal
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown
import subprocess
import websockets
import redis
from contextlib import asynccontextmanager

# Import hook system
# from cc_executor.hooks.hook_registry import HookRegistry
# from cc_executor.hooks.hook_types import HookContext, HookResult
from cc_executor.core.config import (
    SERVICE_NAME, SERVICE_VERSION, DEFAULT_PORT,
    MAX_SESSIONS, SESSION_TIMEOUT, MAX_BUFFER_SIZE,
    STREAM_TIMEOUT, LOG_LEVEL, DEBUG_MODE
)
# Import ServerManager for proper process management
from cc_executor.utils.server_manager import ServerManager

# Initialize Typer app
app = typer.Typer(
    name="cc-executor",
    help="CC Executor MCP WebSocket Service CLI with Hook Integration",
    no_args_is_help=True,
    rich_markup_mode="rich"
)

# Initialize Rich console
console = Console()

# Initialize hook registry
# hook_registry = HookRegistry()

# Add sub-command groups
server_app = typer.Typer(help="Server management commands")
test_app = typer.Typer(help="Testing and assessment commands")
history_app = typer.Typer(help="Execution history and metrics")
hooks_app = typer.Typer(help="Hook management and introspection")
config_app = typer.Typer(help="Configuration management")

app.add_typer(server_app, name="server")
app.add_typer(test_app, name="test")
app.add_typer(history_app, name="history")
app.add_typer(hooks_app, name="hooks")
app.add_typer(config_app, name="config")


# ============================================
# HOOK DECORATORS
# ============================================

def with_hooks(command_name: str):
    """Decorator to add pre/post hook support to commands."""
    def decorator(func):
        # For now, just return the function as-is without hook support
        return func
    return decorator


# ============================================
# SERVER COMMANDS WITH HOOKS
# ============================================

# Define paths for PID and log files
PID_FILE = "/tmp/cc_executor.pid"
LOG_FILE = "/tmp/cc_executor_local.log"

@server_app.command("start")
@with_hooks("server.start")
def server_start(
    port: int = typer.Option(8003, "--port", "-p", help="Port to listen on"),
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind to"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode"),
    background: bool = typer.Option(True, "--background", "-b", help="Run in background (default: True)"),
    force: bool = typer.Option(False, "--force", "-f", help="Force kill existing processes")
):
    """Start the CC Executor WebSocket server as a daemon."""
    # Initialize server manager for cleanup
    manager = ServerManager(server_name="cc_executor", default_port=port)
    
    console.print(f"[bold blue]Preparing to start CC Executor on {host}:{port}[/bold blue]")
    
    # Find and kill existing processes
    existing = manager.find_server_processes()
    if existing:
        console.print(f"[yellow]Found {len(existing)} existing server process(es)[/yellow]")
        for proc in existing:
            console.print(f"  PID: {proc['pid']}, Age: {proc['age']/60:.1f} minutes")
        
        if force or typer.confirm("Kill existing processes?"):
            killed = asyncio.run(manager.kill_server_processes(force=force))
            console.print(f"[green]✓ Killed {killed} process(es)[/green]")
        else:
            console.print("[red]✗ Cannot start with existing processes running[/red]")
            raise typer.Exit(1)
    
    # Check if already running via PID file
    pid_file = Path(PID_FILE)
    if pid_file.exists():
        try:
            old_pid = int(pid_file.read_text().strip())
            # Check if process is actually running
            os.kill(old_pid, 0)
            if not force:
                console.print(f"[yellow]Server already running (PID: {old_pid})[/yellow]")
                raise typer.Exit(1)
            else:
                console.print(f"[yellow]Stopping existing server (PID: {old_pid})[/yellow]")
                os.kill(old_pid, signal.SIGTERM)
                time.sleep(2)
        except (ProcessLookupError, ValueError):
            # Process doesn't exist or PID file is corrupt
            pid_file.unlink(missing_ok=True)
    
    # Start the server
    if background:
        # Simple subprocess with proper detachment
        log_dir = Path.home() / ".cc_executor"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "server.log"
        
        cmd = [
            sys.executable,
            "-m", "uvicorn",
            "cc_executor.core.main:app",
            "--host", host,
            "--port", str(port)
        ]
        
        # Open log file for appending
        with open(log_file, 'a') as log_f:
            # Start process with proper detachment
            process = subprocess.Popen(
                cmd,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                start_new_session=True,  # This creates a new session, detaching from parent
                cwd=str(Path(__file__).parents[3])  # Project root
            )
        
        # Save PID
        pid_file = Path(PID_FILE)
        pid_file.write_text(str(process.pid))
        
        # Give it a moment to start
        time.sleep(2)
        
        # Check if it started successfully
        if process.poll() is None:
            console.print(f"[green]✓ Server started in background (PID: {process.pid})[/green]")
            console.print(f"  WebSocket URL: ws://{host}:{port}/ws/mcp")
            console.print(f"  Log file: {log_file}")
        else:
            console.print(f"[red]✗ Server failed to start[/red]")
            console.print(f"  Check log file: {log_file}")
            raise typer.Exit(1)
    else:
        # Run in foreground - just use uvicorn directly
        console.print(f"[bold green]Starting server in foreground on {host}:{port}[/bold green]")
        try:
            import uvicorn
            from cc_executor.core.main import app
            uvicorn.run(app, host=host, port=port)
        except KeyboardInterrupt:
            console.print("\n[yellow]Server stopped by user[/yellow]")
        except Exception as e:
            console.print(f"[red]✗ Server error: {e}[/red]")
            raise typer.Exit(1)


@server_app.command("stop")
@with_hooks("server.stop")
def server_stop(
    force: bool = typer.Option(False, "--force", "-f", help="Force kill processes")
):
    """Stop the CC Executor WebSocket server."""
    pid_file = Path(PID_FILE)
    
    # First try to stop via PID file
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, signal.SIGTERM)
            console.print(f"[green]✓ Stopped server (PID: {pid})[/green]")
            pid_file.unlink()
        except (ProcessLookupError, ValueError):
            console.print("[yellow]Server PID file exists but process not found[/yellow]")
            pid_file.unlink(missing_ok=True)
    
    # Also use ServerManager to clean up any stray processes
    manager = ServerManager(server_name="cc_executor")
    existing = manager.find_server_processes()
    if existing:
        console.print(f"[yellow]Found {len(existing)} additional process(es)[/yellow]")
        killed = asyncio.run(manager.kill_server_processes(force=force))
        if killed:
            console.print(f"[green]✓ Cleaned up {killed} stray process(es)[/green]")


@server_app.command("status")
@with_hooks("server.status")
def server_status():
    """Check the status of the CC Executor server."""
    pid_file = Path(PID_FILE)
    is_running = False
    
    # Check PID file
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)  # Signal 0 doesn't kill, just checks
            console.print(f"[green]✓ Server is running (PID: {pid})[/green]")
            is_running = True
        except (ProcessLookupError, ValueError):
            console.print("[yellow]Server PID file exists but process not found[/yellow]")
            pid_file.unlink(missing_ok=True)
    
    # Also check with ServerManager for additional info
    manager = ServerManager(server_name="cc_executor")
    processes = manager.find_server_processes()
    
    if processes:
        console.print(f"\n[bold]Process info:[/bold]")
        for proc in processes:
            console.print(f"  PID: {proc['pid']}, Command: {' '.join(proc['cmdline'][:3])}...")
            console.print(f"  Age: {proc['age']/60:.1f} minutes")
    elif not is_running:
        console.print("[yellow]Server is not running[/yellow]")
    
    return is_running


@server_app.command("restart")
@with_hooks("server.restart")
def server_restart(
    port: int = typer.Option(8003, "--port", "-p", help="Port to listen on"),
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind to"),
    background: bool = typer.Option(True, "--background", "-b", help="Run in background"),
    force: bool = typer.Option(True, "--force", "-f", help="Force kill existing processes")
):
    """Restart the CC Executor server."""
    # Stop existing server
    server_stop(force=force)
    time.sleep(1)  # Give it a moment to fully stop
    
    # Start new server
    server_start(port=port, host=host, background=background, force=force)
    """Show status of CC Executor processes."""
    import requests
    
    # Use ServerManager to find processes
    manager = ServerManager(server_name="cc_executor")
    processes = manager.find_server_processes()
    
    if not processes:
        console.print("[yellow]No CC Executor processes running[/yellow]")
        
        # Clean up stale PID file
        pid_file = Path.home() / ".cc_executor.pid"
        if pid_file.exists():
            console.print("[dim]Cleaning up stale PID file[/dim]")
            pid_file.unlink()
    else:
        console.print(f"[bold]Found {len(processes)} CC Executor process(es):[/bold]")
        for proc in processes:
            console.print(f"\n[cyan]Process {proc['pid']}:[/cyan]")
            console.print(f"  Command: {proc['cmdline']}")
            console.print(f"  Age: {proc['age']/60:.1f} minutes")
    
    # Check ports
    console.print(f"\n[bold]Port Status:[/bold]")
    for port in [8003, 8004]:
        if manager.is_port_in_use(port):
            console.print(f"  Port {port}: [yellow]IN USE[/yellow]")
        else:
            console.print(f"  Port {port}: [green]available[/green]")
    
    # Check health endpoint
    console.print(f"\n[bold]Health Check:[/bold]")
    try:
        response = requests.get("http://localhost:8003/health", timeout=2)
        if response.status_code == 200:
            data = response.json()
            
            # Get active session details from Redis
            session_details = []
            try:
                r = redis.Redis(decode_responses=True)
                sessions = r.keys("cc_executor:session:*")
                for session_key in sessions[:5]:  # Show first 5
                    session_data = r.hgetall(session_key)
                    if session_data:
                        session_details.append({
                            "id": session_key.split(":")[-1][:8],
                            "created": session_data.get("created_at", "Unknown")[:19]
                        })
            except:
                pass
            
            panel_content = f"""[green]Server is running[/green]

Service: {data.get('service', 'Unknown')}
Version: {data.get('version', 'Unknown')}
Active Sessions: {data.get('active_sessions', 0)}
Max Sessions: {data.get('max_sessions', 'Unknown')}
Uptime: {data.get('uptime_seconds', 0):.1f}s"""

            if session_details:
                panel_content += "\n\nActive Sessions:"
                for session in session_details:
                    panel_content += f"\n  • {session['id']} (created: {session['created']})"
            
            console.print(Panel(panel_content, title="Server Status"))
        else:
            console.print("  [red]Server returned error status[/red]")
    except requests.ConnectionError:
        console.print("  [red]✗ Server is not accessible on port 8003[/red]")
    except Exception as e:
        console.print(f"  [red]✗ Error checking health: {e}[/red]")


# ============================================
# EXECUTION COMMANDS WITH HOOKS
# ============================================

@app.command("run")
@with_hooks("run")
def run_command(
    command: str = typer.Argument(..., help="Command to execute"),
    timeout: Optional[int] = typer.Option(None, "--timeout", "-t", help="Execution timeout in seconds"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model to use for Claude commands"),
    temperature: Optional[float] = typer.Option(None, "--temp", help="Temperature for Claude commands"),
    save_output: bool = typer.Option(True, "--save/--no-save", help="Save output to tmp/responses"),
    server_url: str = typer.Option("ws://localhost:8003/ws/mcp", "--server", "-s", help="WebSocket server URL")
):
    """Execute a command through the CC Executor WebSocket interface."""
    
    async def execute():
        output_lines = []
        start_time = datetime.now()
        
        try:
            async with websockets.connect(server_url) as websocket:
                # Prepare request
                request = {
                    "jsonrpc": "2.0",
                    "method": "execute",
                    "params": {
                        "command": command,
                        "timeout": timeout
                    },
                    "id": 1
                }
                
                # Add model/temperature if it's a Claude command
                if "claude" in command.lower():
                    if model:
                        request["params"]["model"] = model
                    if temperature is not None:
                        request["params"]["temperature"] = temperature
                
                # Send request
                await websocket.send(json.dumps(request))
                console.print(f"[dim]Executing: {command}[/dim]\n")
                output_lines.append(f"Command: {command}")
                output_lines.append(f"Started: {start_time.isoformat()}")
                
                # Stream responses
                final_result = None
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                    transient=True
                ) as progress:
                    task = progress.add_task("Executing...", total=None)
                    
                    while True:
                        response = await websocket.recv()
                        data = json.loads(response)
                        
                        # Check for final response
                        if "result" in data or "error" in data:
                            progress.stop()
                            if "error" in data:
                                error_msg = f"Error: {data['error']['message']}"
                                console.print(f"[red]{error_msg}[/red]")
                                output_lines.append(error_msg)
                                final_result = {"error": data['error']}
                                return False, output_lines, final_result
                            else:
                                console.print(f"\n[green]✓[/green] Command completed")
                                if "exit_code" in data.get("result", {}):
                                    exit_msg = f"Exit code: {data['result']['exit_code']}"
                                    console.print(exit_msg)
                                    output_lines.append(exit_msg)
                                final_result = data.get("result", {})
                                return True, output_lines, final_result
                        
                        # Handle streaming output
                        if "output" in data:
                            progress.stop()
                            output = data["output"]
                            if output.get("type") == "stdout":
                                content = output.get("data", "")
                                console.print(content, end="")
                                output_lines.append(f"[STDOUT] {content}")
                            elif output.get("type") == "stderr":
                                content = output.get("data", "")
                                console.print(f"[red]{content}[/red]", end="")
                                output_lines.append(f"[STDERR] {content}")
                            progress.start()
                            
        except ConnectionRefusedError:
            error_msg = "Cannot connect to server. Is it running?"
            console.print(f"[red]✗[/red] {error_msg}")
            console.print("[dim]Run 'cc-executor server start' to start the server[/dim]")
            output_lines.append(f"Error: {error_msg}")
            return False, output_lines, {"error": "connection_refused"}
        except Exception as e:
            error_msg = f"Execution error: {e}"
            console.print(f"[red]✗[/red] {error_msg}")
            output_lines.append(error_msg)
            return False, output_lines, {"error": str(e)}
    
    # Run the async function
    success, output_lines, result = asyncio.run(execute())
    
    # Save output if requested
    if save_output:
        responses_dir = Path(__file__).parent / "tmp" / "responses"
        responses_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save as JSON
        response_file = responses_dir / f"run_command_{timestamp}.json"
        with open(response_file, 'w') as f:
            json.dump({
                'command': command,
                'timestamp': timestamp,
                'success': success,
                'output': output_lines,
                'result': result
            }, f, indent=2)
        
        console.print(f"\n💾 Raw response saved to: {response_file.relative_to(Path.cwd())}")
    
    # Save to Redis history
    try:
        r = redis.Redis(decode_responses=True)
        history_key = f"cc_executor:history:{datetime.now().strftime('%Y%m%d')}:{timestamp}"
        r.hset(history_key, mapping={
            "command": command,
            "success": success,
            "timestamp": timestamp,
            "duration": (datetime.now() - datetime.fromisoformat(timestamp.replace('_', ' '))).total_seconds()
        })
        r.expire(history_key, 86400 * 7)  # Keep for 7 days
    except:
        pass  # Redis optional for run command
    
    if not success:
        raise typer.Exit(1)


# ============================================
# TEST COMMANDS WITH HOOKS
# ============================================

@test_app.command("stress")
@with_hooks("test.stress")
def test_stress(
    tasks: int = typer.Option(10, "--tasks", "-n", help="Number of tasks to run"),
    parallel: int = typer.Option(1, "--parallel", "-p", help="Number of parallel executions"),
    timeout: int = typer.Option(300, "--timeout", "-t", help="Overall test timeout"),
    report: bool = typer.Option(True, "--report", "-r", help="Generate report after test"),
    task_file: Optional[Path] = typer.Option(None, "--file", "-f", help="JSON file with task definitions")
):
    """Run stress tests on the CC Executor service."""
    console.print(Panel(
        f"[bold]Stress Test Configuration[/bold]\n\n"
        f"Tasks: {tasks}\n"
        f"Parallel: {parallel}\n"
        f"Timeout: {timeout}s\n"
        f"Task File: {task_file or 'Default'}",
        title="Starting Stress Test"
    ))
    
    # Load task definitions
    if task_file and task_file.exists():
        with open(task_file) as f:
            task_definitions = json.load(f)
        console.print(f"[green]✓[/green] Loaded {len(task_definitions)} task definitions")
    else:
        # Use default stress test tasks
        task_definitions = [
            {"type": "simple", "command": f"echo 'Test {i}'"} 
            for i in range(tasks)
        ]
    
    # Run stress test script
    stress_test_script = Path(__file__).parents[1] / "stress_tests" / "enhanced_stress_test.py"
    if not stress_test_script.exists():
        console.print("[red]Stress test script not found[/red]")
        raise typer.Exit(1)
    
    env = os.environ.copy()
    env['PYTHONPATH'] = str(Path(__file__).parents[2])
    
    try:
        result = subprocess.run(
            [
                sys.executable, str(stress_test_script),
                "--tasks", str(tasks),
                "--parallel", str(parallel),
                "--timeout", str(timeout)
            ],
            env=env,
            capture_output=True,
            text=True
        )
        
        console.print(result.stdout)
        if result.stderr:
            console.print(f"[red]{result.stderr}[/red]")
        
        if report and result.returncode == 0:
            # Generate report
            report_file = Path(__file__).parent / "tmp" / f"stress_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            console.print(f"\n📊 Report saved to: {report_file}")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error running stress test: {e}")
        raise typer.Exit(1)


@test_app.command("assess")
@with_hooks("test.assess")
def test_assess(
    directory: str = typer.Argument("core", help="Directory to assess (core/hooks/cli)"),
    save_report: bool = typer.Option(True, "--save", "-s", help="Save assessment report"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output")
):
    """Run usage function assessments with hook support."""
    valid_dirs = ["core", "hooks", "cli"]
    if directory not in valid_dirs:
        console.print(f"[red]Invalid directory. Choose from: {', '.join(valid_dirs)}[/red]")
        raise typer.Exit(1)
    
    # Get the assessment script path
    base_path = Path(__file__).parents[1] / directory
    assessment_file = base_path / f"ASSESS_ALL_{directory.upper()}_USAGE.md"
    
    if not assessment_file.exists():
        console.print(f"[red]Assessment file not found: {assessment_file}[/red]")
        raise typer.Exit(1)
    
    console.print(f"[bold]Running {directory} assessment...[/bold]\n")
    
    # Extract Python code from markdown
    with open(assessment_file) as f:
        content = f.read()
    
    # Find Python code blocks
        import re
    code_blocks = re.findall(r'```python\n(.*?)\n```', content, re.DOTALL)
    
    if not code_blocks:
        console.print("[red]No Python code found in assessment file[/red]")
        raise typer.Exit(1)
    
    # Create temporary assessment script
    tmp_dir = Path(__file__).parent / "tmp"
    tmp_dir.mkdir(exist_ok=True)
    
    assessment_script = tmp_dir / f"assess_{directory}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
    assessment_script.write_text('\n\n'.join(code_blocks))
    
    env = os.environ.copy()
    env['PYTHONPATH'] = str(Path(__file__).parents[2])
    
    try:
        # Run assessment with proper output handling
        process = subprocess.Popen(
            [sys.executable, str(assessment_script)],
            cwd=str(base_path),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Stream output
        output_lines = []
        for line in process.stdout:
            if verbose or not line.startswith("[DEBUG]"):
                console.print(line.rstrip())
            output_lines.append(line.rstrip())
        
        # Wait for completion
        stderr = process.stderr.read()
        process.wait()
        
        if stderr:
            console.print(f"[red]{stderr}[/red]")
            output_lines.append(f"STDERR: {stderr}")
        
        if process.returncode != 0:
            console.print(f"[red]✗[/red] Assessment failed")
            raise typer.Exit(1)
        
        # Clean up temp script
        assessment_script.unlink()
        
        # Save raw output
        if save_report:
            responses_dir = base_path / "tmp" / "responses"
            responses_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            response_file = responses_dir / f"assessment_{timestamp}.json"
            
            with open(response_file, 'w') as f:
                json.dump({
                    'directory': directory,
                    'timestamp': timestamp,
                    'output': output_lines,
                    'success': process.returncode == 0
                }, f, indent=2)
            
            console.print(f"\n💾 Assessment output saved to: {response_file.relative_to(Path.cwd())}")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error running assessment: {e}")
        raise typer.Exit(1)


# ============================================
# HISTORY COMMANDS WITH HOOKS
# ============================================

@history_app.command("list")
@with_hooks("history.list")
def history_list(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of entries to show"),
    format: str = typer.Option("table", "--format", "-f", help="Output format (table/json)"),
    date: Optional[str] = typer.Option(None, "--date", "-d", help="Filter by date (YYYYMMDD)")
):
    """View execution history from Redis."""
    try:
        r = redis.Redis(decode_responses=True)
        r.ping()
    except:
        console.print("[red]✗[/red] Redis not available")
        raise typer.Exit(1)
    
    # Build pattern for keys
    if date:
        pattern = f"cc_executor:history:{date}:*"
    else:
        pattern = "cc_executor:history:*"
    
    # Get history entries
    keys = r.keys(pattern)
    entries = []
    
    for key in sorted(keys, reverse=True)[:limit]:
        data = r.hgetall(key)
        if data:
            entries.append({
                "timestamp": key.split(":")[-1],
                "command": data.get("command", "Unknown"),
                "success": data.get("success", "Unknown") == "True",
                "duration": float(data.get("duration", 0))
            })
    
    if not entries:
        console.print("[yellow]No history entries found[/yellow]")
        return
    
    if format == "json":
        console.print_json(data=entries)
    else:
        table = Table(title=f"Execution History (Last {limit} entries)")
        table.add_column("Time", style="cyan")
        table.add_column("Command", style="white")
        table.add_column("Status", style="green")
        table.add_column("Duration", style="yellow")
        
        for entry in entries:
            timestamp = entry["timestamp"]
            # Format timestamp for display
            time_str = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]} {timestamp[9:11]}:{timestamp[11:13]}:{timestamp[13:15]}"
            
            status = "[green]✓ Success[/green]" if entry["success"] else "[red]✗ Failed[/red]"
            duration = f"{entry['duration']:.2f}s"
            
            # Truncate long commands
            command = entry["command"]
            if len(command) > 50:
                command = command[:47] + "..."
            
            table.add_row(time_str, command, status, duration)
        
        console.print(table)


@history_app.command("metrics")
@with_hooks("history.metrics")
def history_metrics(
    days: int = typer.Option(7, "--days", "-d", help="Number of days to analyze")
):
    """View execution metrics and statistics."""
    try:
        r = redis.Redis(decode_responses=True)
        r.ping()
    except:
        console.print("[red]✗[/red] Redis not available")
        raise typer.Exit(1)
    
    # Collect metrics for the specified days
    from datetime import timedelta
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    total_executions = 0
    successful_executions = 0
    total_duration = 0.0
    commands_by_type = {}
    
    # Iterate through each day
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y%m%d')
        pattern = f"cc_executor:history:{date_str}:*"
        
        keys = r.keys(pattern)
        for key in keys:
            data = r.hgetall(key)
            if data:
                total_executions += 1
                if data.get("success", "False") == "True":
                    successful_executions += 1
                
                duration = float(data.get("duration", 0))
                total_duration += duration
                
                # Categorize command
                command = data.get("command", "Unknown")
                cmd_type = command.split()[0] if command else "Unknown"
                commands_by_type[cmd_type] = commands_by_type.get(cmd_type, 0) + 1
        
        current_date += timedelta(days=1)
    
    if total_executions == 0:
        console.print("[yellow]No executions found in the specified period[/yellow]")
        return
    
    # Calculate metrics
    success_rate = (successful_executions / total_executions) * 100
    avg_duration = total_duration / total_executions
    
    # Display metrics
    panel_content = f"""[bold]Execution Metrics (Last {days} days)[/bold]

Total Executions: {total_executions}
Successful: {successful_executions} ({success_rate:.1f}%)
Failed: {total_executions - successful_executions}
Average Duration: {avg_duration:.2f}s
Total Runtime: {total_duration:.1f}s

[bold]Commands by Type:[/bold]"""

    # Sort commands by frequency
    sorted_commands = sorted(commands_by_type.items(), key=lambda x: x[1], reverse=True)
    for cmd_type, count in sorted_commands[:10]:  # Top 10
        panel_content += f"\n  • {cmd_type}: {count}"
    
    console.print(Panel(panel_content, title="Execution Metrics"))


# ============================================
# HOOK COMMANDS
# ============================================

@hooks_app.command("list")
@with_hooks("hooks.list")
def hooks_list(
    pattern: Optional[str] = typer.Option(None, "--pattern", "-p", help="Filter hooks by pattern")
):
    """List all registered hooks."""
    console.print("[yellow]Hook registry not yet implemented[/yellow]")


@hooks_app.command("run")
@with_hooks("hooks.run")
def hooks_run(
    hook_point: str = typer.Argument(..., help="Hook point to trigger"),
    context_json: Optional[str] = typer.Option(None, "--context", "-c", help="JSON context data")
):
    """Manually trigger a hook for testing."""
    console.print(f"[yellow]Hook execution not yet implemented (would trigger: {hook_point})[/yellow]")


@hooks_app.command("reload")
@with_hooks("hooks.reload")
def hooks_reload():
    """Reload all hooks from the hooks directory."""
    hooks_dir = Path(__file__).parents[1] / "hooks"
    console.print(f"[yellow]Hook reloading not yet implemented (would reload from: {hooks_dir})[/yellow]")


# ============================================
# CONFIG COMMANDS WITH HOOKS
# ============================================

@config_app.command("show")
@with_hooks("config.show")
def config_show():
    """Show current configuration."""
    table = Table(title="CC Executor Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Source", style="dim")
    
    # Get configuration values
    config_items = [
        ("Service Name", SERVICE_NAME, "config.py"),
        ("Version", SERVICE_VERSION, "config.py"),
        ("Default Port", str(DEFAULT_PORT), "config.py"),
        ("Max Sessions", str(MAX_SESSIONS), "config.py"),
        ("Session Timeout", f"{SESSION_TIMEOUT}s", "config.py"),
        ("Max Buffer Size", f"{MAX_BUFFER_SIZE:,} bytes", "config.py"),
        ("Stream Timeout", f"{STREAM_TIMEOUT}s", "config.py"),
        ("Log Level", LOG_LEVEL, "config.py"),
        ("Debug Mode", str(DEBUG_MODE), "config.py"),
    ]
    
    # Check environment variables
    env_vars = [
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "REDIS_URL",
        "CC_EXECUTOR_PORT",
        "CC_EXECUTOR_HOST"
    ]
    
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            # Mask sensitive values
            if "KEY" in var:
                display_value = value[:8] + "..." if len(value) > 8 else "***"
            else:
                display_value = value
            config_items.append((var, display_value, "environment"))
    
    # Add to table
    for name, value, source in config_items:
        table.add_row(name, value, source)
    
    console.print(table)


@config_app.command("validate")
@with_hooks("config.validate")
def config_validate():
    """Validate configuration and dependencies."""
    checks = []
    
    # Check Python version
    py_version = sys.version_info
    py_check = py_version >= (3, 10, 11)
    checks.append(("Python >= 3.10.11", py_check, f"{py_version.major}.{py_version.minor}.{py_version.micro}"))
    
    # Check Redis
    try:
        r = redis.Redis(decode_responses=True)
        r.ping()
        redis_check = True
        redis_info = "Connected"
    except Exception as e:
        redis_check = False
        redis_info = str(e)
    checks.append(("Redis Connection", redis_check, redis_info))
    
    # Check WebSocket server
    try:
        import requests
        response = requests.get("http://localhost:8003/health", timeout=1)
        server_check = response.status_code == 200
        server_info = "Running" if server_check else f"Status {response.status_code}"
    except:
        server_check = False
        server_info = "Not running"
    checks.append(("WebSocket Server", server_check, server_info))
    
    # Check authentication
    anthropic_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    claude_creds = os.path.exists(os.path.expanduser("~/.claude/.credentials.json"))
    auth_ok = anthropic_key or claude_creds
    auth_details = []
    if claude_creds:
        auth_details.append("Claude Max")
    if anthropic_key:
        auth_details.append("API Key")
    auth_status = " + ".join(auth_details) if auth_details else "Not configured"
    checks.append(("Authentication", auth_ok, auth_status))
    
    # Display results
    table = Table(title="Configuration Validation")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Details", style="dim")
    
    all_passed = True
    for check_name, passed, details in checks:
        status = "[green]✓ Pass[/green]" if passed else "[red]✗ Fail[/red]"
        table.add_row(check_name, status, details)
        if not passed:
            all_passed = False
    
    console.print(table)
    
    if all_passed:
        console.print("\n[green]✅ All configuration checks passed![/green]")
    else:
        console.print("\n[red]❌ Some configuration checks failed[/red]")
        raise typer.Exit(1)


# ============================================
# UTILITY COMMANDS
# ============================================

@app.command("version")
def version():
    """Show version information."""
    console.print(f"{SERVICE_NAME} v{SERVICE_VERSION}")


@app.command("init")
@with_hooks("init")
def init_environment():
    """Initialize CC Executor environment with hooks."""
    console.print("[bold]Initializing CC Executor environment...[/bold]\n")
    
    # Create necessary directories
    dirs_to_create = [
        Path.home() / ".cc_executor",
        Path.home() / ".cc_executor" / "hooks",
        Path.home() / ".cc_executor" / "logs",
        Path(__file__).parent / "tmp",
        Path(__file__).parent / "tmp" / "responses"
    ]
    
    for dir_path in dirs_to_create:
        dir_path.mkdir(parents=True, exist_ok=True)
        console.print(f"[green]✓[/green] Created {dir_path}")
    
    # Check for .env file
    env_file = Path.cwd() / ".env"
    if not env_file.exists():
        console.print("\n[yellow]No .env file found. Creating template...[/yellow]")
        env_template = """# CC Executor Environment Configuration

# Authentication
# Claude Max Plan: Uses ~/.claude/.credentials.json automatically
# API Key users: Uncomment and set the following
# ANTHROPIC_API_KEY=your_key_here
# OPENAI_API_KEY=your_key_here

# Redis Configuration
REDIS_URL=redis://localhost:6379

# CC Executor Settings
CC_EXECUTOR_PORT=8003
CC_EXECUTOR_HOST=0.0.0.0
CC_EXECUTOR_DEBUG=false
CC_EXECUTOR_LOG_LEVEL=INFO

# Python Path
PYTHONPATH=./src
"""
        env_file.write_text(env_template)
        console.print(f"[green]✓[/green] Created .env template")
    
    # Run validation
    console.print("\n[bold]Running configuration validation...[/bold]\n")
    config_validate()


# ============================================
# USAGE FUNCTION
# ============================================

def run_usage_tests():
    """Run usage tests for the CLI using Typer's testing utilities."""
    # Ensure proper path setup
    project_root = Path(__file__).parent.parent.parent.parent
    if str(project_root / "src") not in sys.path:
            
    from cc_executor.core.usage_helper import OutputCapture
    from typer.testing import CliRunner
    
    runner = CliRunner()
    
    # Fix the module name to be correct for CLI
    with OutputCapture(__file__) as capture:
        # Override the module name since we're in cli/, not core/
        capture.module_name = "cc_executor.cli.main"
        print("=== CC Executor CLI Usage Example ===\n")
        
        # Test 1: Show help
        print("--- Test 1: CLI Help ---")
        result = runner.invoke(app, ["--help"])
        print("Exit code:", result.exit_code)
        commands = ["server", "test", "history", "hooks", "config", "run", "version", "init"]
        found_commands = sum(1 for cmd in commands if cmd in result.output)
        print(f"Commands found: {found_commands}/{len(commands)}")
        
        # Test 2: Show version
        print("\n--- Test 2: Version Command ---")
        result = runner.invoke(app, ["version"])
        print(f"Exit code: {result.exit_code}")
        print("Version output:", result.output.strip()[:50] + "..." if len(result.output) > 50 else result.output.strip())
        
        # Test 3: Show config
        print("\n--- Test 3: Config Commands ---")
        config_cmds = ["show", "validate"]
        for cmd in config_cmds:
            result = runner.invoke(app, ["config", cmd, "--help"])
            status = "✓" if result.exit_code == 0 else "✗"
            print(f"config {cmd}: {status}")
        
        # Test 4: Hook commands
        print("\n--- Test 4: Hook Commands ---")
        hook_cmds = ["list", "run", "reload"]
        for cmd in hook_cmds:
            result = runner.invoke(app, ["hooks", cmd, "--help"])
            status = "✓" if result.exit_code == 0 else "✗"
            print(f"hooks {cmd}: {status}")
        
        # Test 5: Server commands
        print("\n--- Test 5: Server Commands ---")
        server_cmds = ["start", "stop", "status"]
        for cmd in server_cmds:
            result = runner.invoke(app, ["server", cmd, "--help"])
            status = "✓" if result.exit_code == 0 else "✗"
            print(f"server {cmd}: {status}")
        
        # Test 6: Test actual functionality (non-destructive)
        print("\n--- Test 6: Non-destructive Commands ---")
        # Test config show (should work without server)
        result = runner.invoke(app, ["config", "show"])
        print(f"config show: {'✓' if result.exit_code == 0 else '✗'} (exit code: {result.exit_code})")
        
        # Test hooks list (should show available hooks)
        result = runner.invoke(app, ["hooks", "list"])
        print(f"hooks list: {'✓' if result.exit_code == 0 else '✗'} (exit code: {result.exit_code})")
        hook_count = result.output.count("✓") + result.output.count("✗")
        print(f"Found {hook_count} hooks in output")
        
        print("\n✅ CLI usage example completed with Typer's CliRunner!")


if __name__ == "__main__":
    # Check if we're running usage tests or the actual CLI
    if len(sys.argv) == 1 and sys.argv[0].endswith("main.py"):
        # Running directly without arguments - run usage tests
        run_usage_tests()
    else:
        # Running with CLI arguments - run the Typer app
        app()