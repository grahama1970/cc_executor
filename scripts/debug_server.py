#!/usr/bin/env python3
"""Start a debug server for VS Code to attach to"""

import sys
import subprocess
import os

if len(sys.argv) < 2:
    print("Usage: python debug_server.py <script.py> [args...]")
    sys.exit(1)

script = sys.argv[1]
args = sys.argv[2:]

# Activate the virtual environment
venv_python = "/home/graham/workspace/experiments/cc_executor/.venv/bin/python"

# Set up the environment
env = os.environ.copy()
env['PYTHONPATH'] = '/home/graham/workspace/experiments/cc_executor/src'

print("Starting debug server on port 5678...")
print("In VS Code:")
print("1. Set your breakpoints")
print("2. Run the 'Python Debugger: Attach' configuration")
print("3. The script will start executing once attached")
print()

# Run with debugpy
cmd = [venv_python, '-m', 'debugpy', '--listen', '5678', '--wait-for-client', script] + args
subprocess.run(cmd, env=env)