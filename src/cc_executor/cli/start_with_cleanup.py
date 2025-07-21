#!/usr/bin/env python3
"""
Enhanced server start command that properly handles port conflicts.
Integrates ServerManager to kill existing processes and find available ports.
"""

import asyncio
import sys
import os
from pathlib import Path
import subprocess
import typer
from rich.console import Console


from cc_executor.utils.server_manager import ServerManager

console = Console()
app = typer.Typer()

async def start_server_with_cleanup(
    port: int = 8003,
    host: str = "0.0.0.0",
    debug: bool = False,
    force: bool = False
):
    """Start server with proper cleanup of existing processes."""
    
    # Initialize server manager
    manager = ServerManager(server_name="cc_executor", default_port=port)
    
    console.print(f"[bold blue]Preparing to start CC Executor on {host}:{port}[/bold blue]")
    
    # Step 1: Find and kill existing processes
    existing = manager.find_server_processes()
    if existing:
        console.print(f"[yellow]Found {len(existing)} existing server process(es)[/yellow]")
        for proc in existing:
            console.print(f"  PID: {proc['pid']}, Age: {proc['age']/60:.1f} minutes")
        
        if force or typer.confirm("Kill existing processes?"):
            killed = await manager.kill_server_processes(force=force)
            console.print(f"[green]✓ Killed {killed} process(es)[/green]")
        else:
            console.print("[red]✗ Cannot start with existing processes running[/red]")
            raise typer.Exit(1)
    
    # Step 2: Ensure port is available
    actual_port = await manager.ensure_clean_start(port)
    if actual_port != port:
        console.print(f"[yellow]Port {port} unavailable, using {actual_port}[/yellow]")
    
    # Step 3: Start the server
    env = os.environ.copy()
    
    # Ensure virtual environment
    if 'VIRTUAL_ENV' not in env:
        venv_path = Path(__file__).parents[4] / ".venv"
        if venv_path.exists():
            env['VIRTUAL_ENV'] = str(venv_path)
            env['PATH'] = f"{venv_path}/bin:{env['PATH']}"
    
    # Set debug mode
    if debug:
        env['DEBUG'] = 'true'
        env['LOG_LEVEL'] = 'DEBUG'
    
    # Build command
    cmd = [
        sys.executable,
        "-m", "cc_executor.core.main",
        "--port", str(actual_port),
        "--host", host,
        "--server"
    ]
    
    console.print(f"[bold green]Starting server on {host}:{actual_port}[/bold green]")
    
    # Start server
    try:
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE if not debug else None,
            stderr=subprocess.PIPE if not debug else None,
            start_new_session=True,
            preexec_fn=os.setsid if hasattr(os, 'setsid') else None
        )
        
        # Save process info
        manager.server_process = process
        
        # Save PID
        pid_file = Path.home() / ".cc_executor.pid"
        pid_file.write_text(str(process.pid))
        
        console.print(f"[green]✓ Server started successfully[/green]")
        console.print(f"  PID: {process.pid}")
        console.print(f"  WebSocket URL: ws://{host}:{actual_port}/ws/mcp")
        
        # If running in foreground, wait
        if debug:
            process.wait()
        
    except Exception as e:
        console.print(f"[red]✗ Failed to start server: {e}[/red]")
        raise typer.Exit(1)

@app.command()
def start(
    port: int = typer.Option(8003, "--port", "-p", help="Port to listen on"),
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind to"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode"),
    force: bool = typer.Option(False, "--force", "-f", help="Force kill existing processes")
):
    """Start CC Executor with automatic cleanup of existing processes."""
    asyncio.run(start_server_with_cleanup(port, host, debug, force))

@app.command()
def stop():
    """Stop all CC Executor processes."""
    async def stop_all():
        manager = ServerManager(server_name="cc_executor")
        killed = await manager.kill_server_processes()
        if killed:
            console.print(f"[green]✓ Stopped {killed} server process(es)[/green]")
        else:
            console.print("[yellow]No server processes found[/yellow]")
    
    asyncio.run(stop_all())

@app.command()
def status():
    """Show status of CC Executor processes."""
    manager = ServerManager(server_name="cc_executor")
    processes = manager.find_server_processes()
    
    if not processes:
        console.print("[yellow]No CC Executor processes running[/yellow]")
        return
    
    console.print(f"[bold]Found {len(processes)} CC Executor process(es):[/bold]")
    for proc in processes:
        console.print(f"\n[cyan]Process {proc['pid']}:[/cyan]")
        console.print(f"  Command: {proc['cmdline']}")
        console.print(f"  Age: {proc['age']/60:.1f} minutes")
        
    # Check ports
    for port in [8003, 8004]:
        if manager.is_port_in_use(port):
            console.print(f"\n[yellow]Port {port} is in use[/yellow]")

if __name__ == "__main__":
    app()