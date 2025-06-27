#!/usr/bin/env python3
"""Universal LiteLLM interface - Call any supported model with proper configuration"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

# CRITICAL: Must activate the llm_call virtual environment
# This ensures litellm and all dependencies are available
if '/home/graham/workspace/experiments/llm_call/.venv' not in sys.executable:
    venv_python = '/home/graham/workspace/experiments/llm_call/.venv/bin/python'
    if os.path.exists(venv_python):
        # Re-execute this script with the correct Python interpreter
        os.execv(venv_python, [venv_python] + sys.argv)
    else:
        print("ERROR: Virtual environment not found. Please ensure /home/graham/workspace/experiments/llm_call/.venv exists", file=sys.stderr)
        sys.exit(1)

# Load environment variables - REQUIRED for API keys
from dotenv import load_dotenv
env_path = '/home/graham/workspace/experiments/llm_call/.env'
if not os.path.exists(env_path):
    print(f"ERROR: .env file not found at {env_path}", file=sys.stderr)
    print("This file must contain your API keys (OPENAI_API_KEY, PERPLEXITY_API_KEY, etc.)", file=sys.stderr)
    sys.exit(1)

load_dotenv(env_path)

try:
    from litellm import completion
    import litellm
except ImportError:
    print("ERROR: litellm not installed. Run: pip install litellm", file=sys.stderr)
    sys.exit(1)

# Initialize caching for better performance
try:
    sys.path.append('/home/graham/workspace/experiments/llm_call/src/llm_call/usage/docs/tasks/claude_poll_poc_v2/scripts')
    from initialize_litellm_cache import initialize_litellm_cache
    initialize_litellm_cache()
except ImportError:
    # Caching is optional
    pass

# Parameters - REPLACE WITH ACTUAL VALUES
model = "REPLACE_WITH_MODEL_NAME"  # e.g., "gpt-4", "vertex_ai/gemini-2.0-flash-exp"
query = """REPLACE_WITH_QUERY_TEXT"""  # Required - Must not be empty
output_path = "REPLACE_WITH_OUTPUT_PATH"  # Required - Must be a writable path
system_prompt = None  # Optional - Set to string or None for auto-generated
temperature = 0.7  # Optional - Adjust for more/less randomness
max_tokens = None  # Optional - Model-specific defaults
vertex_json_path = None  # Optional - For Vertex AI models  
thinking = False  # Optional - Enable thinking mode for supported models
fallback_models = []  # Optional - e.g., ["gpt-3.5-turbo", "perplexity/sonar"]
ollama_base_url = None  # Optional - Override default Ollama URL

# Validate inputs
if not query or not query.strip():
    print("ERROR: Query cannot be empty", file=sys.stderr)
    sys.exit(1)

if not output_path:
    print("ERROR: Output path must be specified", file=sys.stderr)
    sys.exit(1)

if not model:
    print("ERROR: Model must be specified", file=sys.stderr)
    sys.exit(1)

# Ensure output directory exists
output_dir = os.path.dirname(output_path)
if output_dir and not os.path.exists(output_dir):
    os.makedirs(output_dir, exist_ok=True)

# Configure for specific model types
extra_kwargs = {}
ollama_base_url = "http://localhost:11434"  # Default Ollama URL

# Provider-specific configuration based on LiteLLM docs
if model.startswith("vertex_ai/"):
    # Vertex AI configuration: https://docs.litellm.ai/docs/providers/vertex
    if vertex_json_path and os.path.exists(vertex_json_path):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = vertex_json_path
    elif "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
        # Try default locations
        default_creds = [
            "/home/graham/.config/gcloud/application_default_credentials.json",
            os.path.expanduser("~/.config/gcloud/application_default_credentials.json")
        ]
        for cred_path in default_creds:
            if os.path.exists(cred_path):
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred_path
                print(f"Using default credentials: {cred_path}", file=sys.stderr)
                break
        else:
            print("WARNING: Vertex AI model requested but no credentials found", file=sys.stderr)
    
    # Enable thinking for Gemini 2.0 models
    if thinking and "gemini-2.0" in model:
        extra_kwargs["thinking"] = True

elif model.startswith("ollama/"):
    # Ollama configuration: https://docs.litellm.ai/docs/providers/ollama
    # For complex Ollama model selection and Docker handling, see:
    # /home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts/commands/ask-ollama.md
    
    # Use standard localhost URL (Docker container exposes port to host)
    ollama_base_url = os.getenv('OLLAMA_API_BASE_URL', 'http://localhost:11434')
    extra_kwargs["api_base"] = ollama_base_url
    
    # Note: For advanced Ollama features like automatic model selection based on
    # query type, use the dedicated ask-ollama.md command instead

elif model.startswith("perplexity/"):
    # Perplexity configuration: https://docs.litellm.ai/docs/providers/perplexity
    # Perplexity requires API key in PERPLEXITY_API_KEY env var
    if "PERPLEXITY_API_KEY" not in os.environ:
        print("WARNING: Perplexity model requested but PERPLEXITY_API_KEY not set", file=sys.stderr)

# Auto-generate system prompt if not provided
if system_prompt is None:
    # Analyze query type and generate appropriate system prompt
    query_lower = query.lower()
    if any(word in query_lower for word in ["code", "program", "function", "implement"]):
        system_prompt = "You are an expert programmer. Provide clear, well-commented code with explanations."
    elif any(word in query_lower for word in ["research", "explain", "what is", "how does"]):
        system_prompt = "You are a knowledgeable assistant. Provide accurate, well-researched answers with sources when applicable."
    elif any(word in query_lower for word in ["review", "critique", "analyze", "evaluate"]):
        system_prompt = "You are a thorough reviewer. Provide constructive, detailed analysis with specific suggestions."
    else:
        system_prompt = "You are a helpful assistant. Provide clear, concise, and accurate responses."

# Build messages
messages = []
if system_prompt:
    # Some models don't support system role, handle gracefully
    try:
        messages.append({"role": "system", "content": system_prompt})
    except:
        # Prepend to user message instead
        query = f"{system_prompt}\n\n{query}"

messages.append({"role": "user", "content": query})

# Function to attempt completion
def try_completion(model_name: str, messages: List[Dict], **kwargs) -> Optional[Any]:
    """Attempt completion with a specific model"""
    try:
        print(f"Calling {model_name}...", file=sys.stderr)
        
        # Model-specific adjustments
        if model_name.startswith("perplexity/"):
            # Perplexity prefers lower temperature for factual responses
            kwargs["temperature"] = min(kwargs.get("temperature", 0.5), 0.5)
        elif "o1" in model_name:
            # OpenAI o1 models don't support temperature
            kwargs.pop("temperature", None)
            kwargs.pop("max_tokens", None)
        
        response = completion(
            model=model_name,
            messages=messages,
            temperature=kwargs.get("temperature", temperature),
            max_tokens=kwargs.get("max_tokens", max_tokens),
            **kwargs.get("extra", {})
        )
        return response
        
    except Exception as e:
        error_msg = str(e)
        print(f"ERROR with {model_name}: {error_msg}", file=sys.stderr)
        
        # Check for specific error types
        if "quota" in error_msg.lower() or "rate" in error_msg.lower():
            print("Rate limit or quota exceeded", file=sys.stderr)
        elif "auth" in error_msg.lower() or "credentials" in error_msg.lower():
            print("Authentication error - check API keys/credentials", file=sys.stderr)
        elif "model" in error_msg.lower() and "not found" in error_msg.lower():
            print(f"Model {model_name} not found or not accessible", file=sys.stderr)
        
        return None

# Try primary model
response = try_completion(model, messages, extra=extra_kwargs)

# Try fallback models if primary fails
if response is None and fallback_models:
    print(f"\nTrying fallback models...", file=sys.stderr)
    for fallback in fallback_models:
        response = try_completion(fallback, messages, extra=extra_kwargs)
        if response:
            print(f"Success with fallback model: {fallback}", file=sys.stderr)
            model = fallback  # Update for logging
            break

if response is None:
    print("\nAll models failed. Check your configuration and API keys.", file=sys.stderr)
    sys.exit(1)

# Extract response content
try:
    content = response.choices[0].message.content
except (AttributeError, IndexError):
    print("ERROR: Unexpected response format", file=sys.stderr)
    print(f"Response: {response}", file=sys.stderr)
    sys.exit(1)

# Save response
try:
    with open(output_path, 'w', encoding='utf-8') as f:
        # Save metadata and response
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "query": query,
            "system_prompt": system_prompt,
            "temperature": temperature,
            "thinking_enabled": extra_kwargs.get("thinking", False)
        }
        
        f.write(f"# LiteLLM Response\n\n")
        f.write(f"## Metadata\n")
        f.write(f"```json\n{json.dumps(metadata, indent=2)}\n```\n\n")
        f.write(f"## Response\n\n")
        f.write(content)
        
    print(f"\n✓ Response saved to: {output_path}", file=sys.stderr)
    
    # Show preview
    preview_lines = content.split('\n')[:10]
    preview = '\n'.join(preview_lines)
    if len(content.split('\n')) > 10:
        preview += "\n[... truncated ...]"
    print(f"\nPreview:\n{preview}")
    
except Exception as e:
    print(f"ERROR saving response: {e}", file=sys.stderr)
    sys.exit(1)

# Success marker for verification
print(f"\nMARKER_LITELLM_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
