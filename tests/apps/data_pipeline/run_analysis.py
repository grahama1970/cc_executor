#!/usr/bin/env python3
import subprocess
import sys
import os

# Change to the script directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Run the analyze_sales.py script
result = subprocess.run([sys.executable, 'analyze_sales.py'], 
                       capture_output=True, 
                       text=True)

# Print output
print("STDOUT:")
print(result.stdout)
if result.stderr:
    print("\nSTDERR:")
    print(result.stderr)

# Check if metrics.json was created
if os.path.exists('metrics.json'):
    print("\n✓ metrics.json was created successfully")
    with open('metrics.json', 'r') as f:
        import json
        metrics = json.load(f)
        print("\nMetrics content:")
        print(json.dumps(metrics, indent=2))
else:
    print("\n✗ metrics.json was NOT created")

sys.exit(result.returncode)