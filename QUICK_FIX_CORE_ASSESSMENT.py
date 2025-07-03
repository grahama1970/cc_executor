#!/usr/bin/env python3
"""Quick assessment of core components without hanging."""
import subprocess
import sys
from pathlib import Path

def main():
    """Run core assessment with proper environment."""
    # Kill any existing processes
    subprocess.run(['pkill', '-f', 'websocket_handler'], check=False)
    subprocess.run(['pkill', '-f', 'assess_all'], check=False)
    
    # Activate venv and run assessment
    cmd = """
    source .venv/bin/activate && \
    export PYTHONPATH=./src && \
    export ASSESSMENT_NO_HOOKS=1 && \
    python src/cc_executor/core/assess_all_core_usage.py
    """
    
    result = subprocess.run(cmd, shell=True, executable='/bin/bash')
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())