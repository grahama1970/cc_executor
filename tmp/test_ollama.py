#!/usr/bin/env python3
"""Test Ollama through LiteLLM"""

import sys
import os
import subprocess
from datetime import datetime

# CRITICAL: Must activate the llm_call virtual environment
if '/home/graham/workspace/experiments/llm_call/.venv' not in sys.executable:
    venv_python = '/home/graham/workspace/experiments/llm_call/.venv/bin/python'
    if os.path.exists(venv_python):
        os.execv(venv_python, [venv_python] + sys.argv)
    else:
        print("ERROR: Virtual environment not found", file=sys.stderr)
        sys.exit(1)

# Load environment variables
from dotenv import load_dotenv
load_dotenv('/home/graham/workspace/experiments/llm_call/.env')

from litellm import completion

# First check if Ollama is available
print("Checking Ollama availability...", file=sys.stderr)

ollama_available = False
ollama_url = "http://localhost:11434"
available_models = []

# Check Docker container
container_name = os.getenv('OLLAMA_DOCKER_CONTAINER', 'llm-call-ollama')
try:
    result = subprocess.run(['docker', 'exec', container_name, 'ollama', 'list'], 
                           capture_output=True, text=True, timeout=2)
    if result.returncode == 0:
        # Use localhost, not container name for API calls
        ollama_url = "http://localhost:11434"
        print(f"✓ Ollama found in Docker: {container_name}", file=sys.stderr)
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        available_models = [line.split()[0] for line in lines if line.strip()]
        ollama_available = True
except:
    # Try local Ollama
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            print("✓ Ollama found locally", file=sys.stderr)
            lines = result.stdout.strip().split('\n')[1:]
            available_models = [line.split()[0] for line in lines if line.strip()]
            ollama_available = True
    except:
        pass

if not ollama_available:
    print("✗ Ollama not available", file=sys.stderr)
    print("To install: https://ollama.ai/download", file=sys.stderr)
    sys.exit(1)

print(f"Available models: {', '.join(available_models[:3])}{'...' if len(available_models) > 3 else ''}", file=sys.stderr)

# Pick a small model for testing
model = "ollama/phi3:mini"
if "phi3:mini" not in available_models and available_models:
    model = f"ollama/{available_models[0]}"
    print(f"Using available model: {model}", file=sys.stderr)

query = "Write a simple Python function to add two numbers."
output_path = "/tmp/litellm_ollama_test.md"

try:
    print(f"\nCalling {model}...", file=sys.stderr)
    
    response = completion(
        model=model,
        messages=[{"role": "user", "content": query}],
        api_base=ollama_url,
        temperature=0.5,
        max_tokens=200
    )
    
    content = response.choices[0].message.content
    
    if not content:
        print("ERROR: Empty response", file=sys.stderr)
        sys.exit(1)
    
    # Save response
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# Ollama Response\n\n")
        f.write(f"Model: {model}\n")
        f.write(f"Base URL: {ollama_url}\n\n")
        f.write(f"## Response\n\n")
        f.write(content)
    
    print(f"✓ Success! Response saved to: {output_path}")
    print(f"\nMARKER_OLLAMA_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
except Exception as e:
    print(f"✗ Error: {e}", file=sys.stderr)
    # If Ollama fails, it's likely not installed/running
    print("\nTip: Make sure Ollama is running with 'ollama serve'", file=sys.stderr)
    sys.exit(1)