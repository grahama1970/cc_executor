#!/usr/bin/env python3
"""Test implementation of ask-litellm prompt"""

import sys
import os

# First, ensure we're in the right environment
if '.venv' not in sys.executable:
    # Try to activate the venv
    venv_path = '/home/graham/workspace/experiments/llm_call/.venv/bin/python'
    if os.path.exists(venv_path):
        print(f"Re-running with venv: {venv_path}", file=sys.stderr)
        os.execv(venv_path, [venv_path] + sys.argv)
    else:
        print("ERROR: Virtual environment not active. Please run: source /home/graham/workspace/experiments/llm_call/.venv/bin/activate", file=sys.stderr)
        sys.exit(1)

# Load environment variables - CRITICAL for API keys
from dotenv import load_dotenv
env_path = '/home/graham/workspace/experiments/llm_call/.env'
if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"✓ Loaded .env from {env_path}", file=sys.stderr)
else:
    print(f"WARNING: .env not found at {env_path}", file=sys.stderr)

# Now import litellm
try:
    from litellm import completion
    import litellm
    print("✓ LiteLLM imported successfully", file=sys.stderr)
except ImportError as e:
    print(f"ERROR: litellm not installed: {e}", file=sys.stderr)
    print("Run: pip install litellm", file=sys.stderr)
    sys.exit(1)

# Test parameters
model = "gpt-3.5-turbo"  # Start with OpenAI
query = "Say 'Hello from LiteLLM!'"
output_path = "/tmp/litellm_test.md"

print(f"\nTesting LiteLLM with model: {model}", file=sys.stderr)
print(f"Query: {query}", file=sys.stderr)

# Quick environment check
print("\nEnvironment check:", file=sys.stderr)
api_keys = {
    "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", "NOT SET"),
    "PERPLEXITY_API_KEY": os.environ.get("PERPLEXITY_API_KEY", "NOT SET"),
    "GOOGLE_APPLICATION_CREDENTIALS": os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "NOT SET")
}

for key, value in api_keys.items():
    if value != "NOT SET":
        print(f"  {key}: {value[:20]}...", file=sys.stderr)
    else:
        print(f"  {key}: NOT SET", file=sys.stderr)

# Try the completion
try:
    print(f"\nCalling {model}...", file=sys.stderr)
    
    response = completion(
        model=model,
        messages=[{"role": "user", "content": query}],
        max_tokens=50
    )
    
    content = response.choices[0].message.content
    print(f"\n✓ Success! Response: {content}", file=sys.stderr)
    
    # Save to file
    with open(output_path, 'w') as f:
        f.write(f"# LiteLLM Test Response\n\n")
        f.write(f"Model: {model}\n\n")
        f.write(f"Response:\n{content}")
    
    print(f"\nSaved to: {output_path}")
    print(f"\nMARKER_LITELLM_TEST_SUCCESS")
    
except Exception as e:
    print(f"\n✗ Error: {e}", file=sys.stderr)
    print(f"Error type: {type(e).__name__}", file=sys.stderr)
    
    # Check specific error types
    error_msg = str(e).lower()
    if "api" in error_msg and "key" in error_msg:
        print("\nLikely issue: Missing or invalid API key", file=sys.stderr)
        print("Solution: Ensure OPENAI_API_KEY is set in .env file", file=sys.stderr)
    
    sys.exit(1)