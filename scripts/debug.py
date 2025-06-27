#!/usr/bin/env python3
"""Debug helper to run Python files with proper environment"""

import sys
import os
import subprocess

if len(sys.argv) < 2:
    print("Usage: python debug.py <script.py>")
    sys.exit(1)

# Set up environment
env = os.environ.copy()
env['PYTHONPATH'] = './src'

# Run the script with debugpy for VS Code attachment
cmd = [
    '.venv/bin/python',
    '-m', 'debugpy',
    '--listen', '5678',
    '--wait-for-client',
    sys.argv[1]
] + sys.argv[2:]

print(f"Starting debug server on port 5678...")
print(f"Attach VS Code debugger now!")
subprocess.run(cmd, env=env)