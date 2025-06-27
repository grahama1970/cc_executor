#!/bin/bash
# Wrapper script to force VS Code to use the correct Python environment

# Set up the environment
export PYTHONPATH="./src"
source .venv/bin/activate

# Run Python with all arguments passed to this script
exec python "$@"