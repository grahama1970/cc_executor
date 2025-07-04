#!/usr/bin/env python3
"""
Usage demonstration for the CC Executor CLI main.py.
Shows how the CLI works without actually blocking on input.
"""

import subprocess
import sys
import os
from pathlib import Path

def demonstrate_cli_usage():
    """Demonstrate CLI functionality without blocking."""
    print("=== CC Executor CLI Usage Demonstration ===\n")
    
    cli_path = Path(__file__).parent / "main.py"
    
    # Test 1: Show help
    print("1. Testing --help flag:")
    print("-" * 50)
    result = subprocess.run(
        [sys.executable, str(cli_path), "--help"],
        capture_output=True,
        text=True,
        timeout=5
    )
    print(f"Exit code: {result.returncode}")
    print(f"Output:\n{result.stdout[:500]}...")  # First 500 chars
    
    # Test 2: Show version
    print("\n2. Testing --version flag:")
    print("-" * 50)
    result = subprocess.run(
        [sys.executable, str(cli_path), "--version"],
        capture_output=True,
        text=True,
        timeout=5
    )
    print(f"Exit code: {result.returncode}")
    print(f"Output: {result.stdout.strip()}")
    
    # Test 3: Show available commands
    print("\n3. Testing server status (should fail gracefully):")
    print("-" * 50)
    result = subprocess.run(
        [sys.executable, str(cli_path), "server", "status"],
        capture_output=True,
        text=True,
        timeout=5
    )
    print(f"Exit code: {result.returncode}")
    print(f"Output: {result.stdout}")
    if result.stderr:
        print(f"Error: {result.stderr[:200]}...")
    
    # Test 4: Config show
    print("\n4. Testing config show:")
    print("-" * 50)
    result = subprocess.run(
        [sys.executable, str(cli_path), "config", "show"],
        capture_output=True,
        text=True,
        timeout=5
    )
    print(f"Exit code: {result.returncode}")
    print(f"Output:\n{result.stdout[:300]}...")
    
    print("\n✅ CLI usage demonstration complete")
    print(f"CLI has Typer commands for: server, execute, stress, history, hooks, config")
    
    # Validate that we saw expected output
    assert "cc-executor" in result.stdout or result.returncode == 0, "CLI did not produce expected output"
    
    return True

if __name__ == "__main__":
    try:
        demonstrate_cli_usage()
    except Exception as e:
        print(f"Error demonstrating CLI: {e}")
        sys.exit(1)