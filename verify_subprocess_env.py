#!/usr/bin/env python3
"""Verify that subprocess actually inherits the environment we set."""
import subprocess
import os
import sys
from pathlib import Path

def test_subprocess_environment():
    """Test if subprocess inherits environment variables."""
    print("=== SUBPROCESS ENVIRONMENT VERIFICATION ===\n")
    
    # 1. Check parent process environment
    print("1. PARENT PROCESS:")
    print(f"   Python: {sys.executable}")
    print(f"   VIRTUAL_ENV: {os.environ.get('VIRTUAL_ENV', 'NOT SET')}")
    print(f"   PATH starts with: {os.environ.get('PATH', '').split(':')[0]}")
    
    # 2. Run subprocess WITHOUT environment setup
    print("\n2. SUBPROCESS WITHOUT ENV SETUP:")
    result = subprocess.run(
        ["python3", "-c", "import sys, os; print(f'Python: {sys.executable}'); print(f'VIRTUAL_ENV: {os.environ.get(\"VIRTUAL_ENV\", \"NOT SET\")}')"],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    
    # 3. Run subprocess WITH environment setup
    print("3. SUBPROCESS WITH ENV SETUP:")
    venv_path = Path(__file__).parent / ".venv"
    env = os.environ.copy()
    env["VIRTUAL_ENV"] = str(venv_path)
    env["PATH"] = f"{venv_path}/bin:" + env["PATH"]
    
    result = subprocess.run(
        ["python3", "-c", "import sys, os; print(f'Python: {sys.executable}'); print(f'VIRTUAL_ENV: {os.environ.get(\"VIRTUAL_ENV\", \"NOT SET\")}')"],
        env=env,
        capture_output=True,
        text=True
    )
    print(result.stdout)
    
    # 4. Test Claude command with proper environment
    print("4. TESTING CLAUDE COMMAND:")
    claude_cmd = ["which", "claude"]
    
    # Without env
    result1 = subprocess.run(claude_cmd, capture_output=True, text=True)
    print(f"   Without env: {result1.stdout.strip() if result1.returncode == 0 else 'NOT FOUND'}")
    
    # With env
    result2 = subprocess.run(claude_cmd, env=env, capture_output=True, text=True)
    print(f"   With env: {result2.stdout.strip() if result2.returncode == 0 else 'NOT FOUND'}")

if __name__ == "__main__":
    test_subprocess_environment()