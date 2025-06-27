#!/usr/bin/env python3
"""Comprehensive test of ask-litellm implementation"""

import subprocess
import sys
import os
import json
from datetime import datetime

def test_model(model, query, output_path, extra_params=None):
    """Test a specific model through ask-litellm"""
    print(f"\n{'='*60}")
    print(f"Testing: {model}")
    print(f"Query: {query}")
    print(f"{'='*60}")
    
    # Build the Python script with parameters
    script = f"""
#!/usr/bin/env python3
import sys
import os

# Parameters
model = "{model}"
query = '''{query}'''
output_path = "{output_path}"
"""
    
    if extra_params:
        for key, value in extra_params.items():
            if isinstance(value, str):
                script += f'{key} = "{value}"\n'
            else:
                script += f'{key} = {value}\n'
    
    # Add the implementation
    with open('tmp/ask_litellm_implementation.py', 'r') as f:
        implementation = f.read()
    
    # Remove the parameter placeholder section
    lines = implementation.split('\n')
    start_idx = None
    end_idx = None
    
    for i, line in enumerate(lines):
        if 'Parameters - REPLACE WITH ACTUAL VALUES' in line:
            start_idx = i
        elif start_idx and line.strip() == '' and i > start_idx + 15:
            end_idx = i
            break
    
    if start_idx and end_idx:
        implementation = '\n'.join(lines[:start_idx] + lines[end_idx:])
    
    script += implementation
    
    # Write temporary script
    script_path = f'/tmp/test_litellm_{model.replace("/", "_")}.py'
    with open(script_path, 'w') as f:
        f.write(script)
    
    # Execute
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print("✓ SUCCESS")
            print("STDOUT:", result.stdout[-200:] if len(result.stdout) > 200 else result.stdout)
            
            # Check if output file was created
            if os.path.exists(output_path):
                with open(output_path, 'r') as f:
                    content = f.read()
                    if content.strip():
                        print(f"✓ Output saved to {output_path}")
                        return True
                    else:
                        print("✗ Output file is empty")
                        return False
            else:
                print("✗ Output file not created")
                return False
        else:
            print("✗ FAILED")
            print("STDERR:", result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("✗ TIMEOUT after 60 seconds")
        return False
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return False
    finally:
        # Cleanup
        if os.path.exists(script_path):
            os.remove(script_path)

# Run comprehensive tests
tests = [
    {
        "model": "gpt-3.5-turbo",
        "query": "Write a Python function to calculate factorial",
        "output_path": "/tmp/litellm_test_openai.md"
    },
    {
        "model": "vertex_ai/gemini-2.0-flash-exp",
        "query": "Explain recursion with a simple example",
        "output_path": "/tmp/litellm_test_vertex.md",
        "extra_params": {"temperature": 0.5}
    },
    {
        "model": "perplexity/sonar",
        "query": "What are the key features of Python 3.13?",
        "output_path": "/tmp/litellm_test_perplexity.md"
    },
    {
        "model": "ollama/phi3:mini",
        "query": "Write a simple for loop in Python",
        "output_path": "/tmp/litellm_test_ollama.md"
    },
    {
        "model": "gpt-4",
        "query": "Analyze the time complexity of merge sort",
        "output_path": "/tmp/litellm_test_gpt4.md",
        "extra_params": {
            "fallback_models": ["gpt-3.5-turbo", "perplexity/sonar"]
        }
    }
]

results = {"success": 0, "failure": 0}

print("ASK-LITELLM COMPREHENSIVE TEST")
print(f"Timestamp: {datetime.now().isoformat()}")

for test in tests:
    if test_model(test["model"], test["query"], test["output_path"], test.get("extra_params")):
        results["success"] += 1
    else:
        results["failure"] += 1

print(f"\n{'='*60}")
print("FINAL RESULTS")
print(f"{'='*60}")
print(f"Success: {results['success']}")
print(f"Failure: {results['failure']}")
print(f"Total: {results['success'] + results['failure']}")
print(f"Success Rate: {results['success'] / (results['success'] + results['failure']) * 100:.1f}%")

# Success marker
if results['success'] > 0:
    print(f"\nMARKER_LITELLM_COMPREHENSIVE_{datetime.now().strftime('%Y%m%d_%H%M%S')}")