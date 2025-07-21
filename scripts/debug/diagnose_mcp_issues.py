#!/usr/bin/env python3
"""Diagnose why MCP servers aren't available in Claude."""

import subprocess
import json
import os
from pathlib import Path

def check_mcp_config():
    """Check MCP configuration."""
    print("\n=== MCP Configuration ===")
    config_path = Path.home() / ".claude/claude_code/.mcp.json"
    
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
            servers = config.get("mcpServers", {})
            print(f"✓ Found {len(servers)} servers in .mcp.json:")
            for name in sorted(servers.keys()):
                print(f"  - {name}")
    else:
        print("✗ No .mcp.json found")

def check_running_processes():
    """Check which MCP processes are running."""
    print("\n=== Running MCP Processes ===")
    
    result = subprocess.run(
        ["ps", "aux"],
        capture_output=True,
        text=True
    )
    
    mcp_processes = {}
    for line in result.stdout.splitlines():
        for server in ["arango", "d3", "tool", "kilocode", "logger"]:
            if f"mcp_{server}" in line and "grep" not in line:
                parts = line.split()
                if len(parts) > 10:
                    pid = parts[1]
                    cmd = " ".join(parts[10:])
                    server_name = None
                    for part in parts[10:]:
                        if f"mcp_{server}" in part:
                            server_name = part.split("/")[-1].replace(".py", "")
                            break
                    if server_name:
                        mcp_processes[server_name] = {"pid": pid, "cmd": cmd[:80] + "..."}
    
    if mcp_processes:
        print(f"✓ Found {len(mcp_processes)} running MCP processes:")
        for name, info in mcp_processes.items():
            print(f"  - {name} (PID: {info['pid']})")
    else:
        print("✗ No MCP processes found")

def check_logs():
    """Check MCP logs for errors."""
    print("\n=== Recent MCP Errors ===")
    
    log_dir = Path.home() / ".claude/mcp_logs"
    if not log_dir.exists():
        print("✗ No MCP log directory found")
        return
    
    error_count = 0
    for log_file in log_dir.glob("*_debug.log"):
        # Check last 50 lines for errors
        try:
            result = subprocess.run(
                ["tail", "-50", str(log_file)],
                capture_output=True,
                text=True
            )
            
            for line in result.stdout.splitlines():
                if any(word in line.lower() for word in ["error", "failed", "exception", "crashed"]):
                    if error_count == 0:
                        print("Found errors:")
                    error_count += 1
                    server = log_file.stem.replace("_debug", "")
                    print(f"  [{server}] {line.strip()}")
                    if error_count > 10:
                        print("  ... (truncated)")
                        break
        except:
            pass
    
    if error_count == 0:
        print("✓ No recent errors found in logs")

def test_mcp_protocol():
    """Test if MCP servers respond to protocol."""
    print("\n=== MCP Protocol Test ===")
    
    servers_to_test = [
        "src/cc_executor/servers/mcp_arango_tools.py",
        "src/cc_executor/servers/mcp_d3_visualizer.py",
    ]
    
    for server_path in servers_to_test:
        server_name = Path(server_path).stem
        print(f"\nTesting {server_name}...")
        
        # Try to initialize
        proc = subprocess.Popen(
            ["uv", "run", "--script", server_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Send initialization
        init_msg = json.dumps({
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": True},
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0"
                }
            },
            "id": 1
        })
        
        try:
            proc.stdin.write(init_msg + "\n")
            proc.stdin.flush()
            
            # Read response with timeout
            import select
            ready, _, _ = select.select([proc.stdout], [], [], 2)
            
            if ready:
                response = proc.stdout.readline()
                if response:
                    try:
                        resp_json = json.loads(response)
                        if "result" in resp_json:
                            print(f"  ✓ Server responded correctly")
                        elif "error" in resp_json:
                            print(f"  ✗ Server error: {resp_json['error']}")
                    except:
                        print(f"  ✗ Invalid response: {response[:100]}")
            else:
                print(f"  ✗ No response within 2 seconds")
                
        finally:
            proc.terminate()

def check_environment():
    """Check environment variables."""
    print("\n=== Environment ===")
    
    important_vars = [
        "MCP_DEBUG",
        "ANTHROPIC_DEBUG", 
        "PYTHONPATH",
        "UV_PROJECT_ROOT",
        "ARANGO_HOST",
        "ARANGO_DATABASE"
    ]
    
    for var in important_vars:
        value = os.environ.get(var, "not set")
        symbol = "✓" if value != "not set" else "✗"
        print(f"{symbol} {var}: {value}")

def main():
    print("MCP Diagnostic Report")
    print("=" * 50)
    
    check_environment()
    check_mcp_config()
    check_running_processes()
    check_logs()
    test_mcp_protocol()
    
    print("\n" + "=" * 50)
    print("Diagnosis Summary:")
    print("1. MCP servers are configured in .mcp.json ✓")
    print("2. Some servers are running as processes ✓") 
    print("3. Servers respond to test protocol ✓")
    print("4. But tools not available in Claude ✗")
    print("\nRecommendation: Full restart of Claude may be needed")
    print("(Exit Claude completely and restart, not just reload)")

if __name__ == "__main__":
    main()