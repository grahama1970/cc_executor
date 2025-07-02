#!/usr/bin/env python3
"""
Medium Stress Test Runner - Executes the runner from the prompt file.
"""
import sys
import subprocess
from pathlib import Path

PROMPT_PATH = Path("/home/graham/workspace/experiments/cc_executor/tests/stress/prompts/medium_stress_tests_prompt.md")

def extract_and_run_code():
    """Extract the implementation code from the prompt and run it."""
    with open(PROMPT_PATH, 'r') as f:
        content = f.read()
    
    # Find the implementation code block
    start_marker = "```python\n#!/usr/bin/env python3"
    end_marker = "\n```\n\n### **Task Execution Plan"
    
    start_idx = content.find(start_marker)
    if start_idx == -1:
        print("❌ Could not find implementation code in prompt")
        sys.exit(1)
    
    end_idx = content.find(end_marker, start_idx)
    if end_idx == -1:
        print("❌ Could not find end of implementation code")
        sys.exit(1)
    
    # Extract the code (skip the ```python\n part)
    code = content[start_idx + len("```python\n"):end_idx]
    
    # Write to temp file and execute
    temp_file = Path("/tmp/medium_stress_test_runner.py")
    with open(temp_file, 'w') as f:
        f.write(code)
    
    # Execute the extracted code
    result = subprocess.run([sys.executable, str(temp_file)] + sys.argv[1:], 
                          capture_output=False)
    sys.exit(result.returncode)

if __name__ == "__main__":
    extract_and_run_code()