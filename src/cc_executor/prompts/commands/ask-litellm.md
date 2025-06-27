# Ask LiteLLM — Self-Improving Prompt

## 🔴 SELF-IMPROVEMENT RULES
This prompt MUST follow the self-improvement protocol:
1. Every failure updates metrics immediately
2. Every failure fixes the root cause
3. Every failure adds a recovery test
4. Every change updates evolution history

## 🎮 GAMIFICATION METRICS
- **Success**: 0
- **Failure**: 0
- **Total Executions**: 0
- **Last Updated**: 2025-06-27
- **Success Ratio**: N/A (need 10:1 to graduate)

## Evolution History
- v1: Initial implementation - Universal LiteLLM interface
- v2: Fixed environment activation with os.execv
- v3: Added proper load_dotenv for API keys
- v4: Verified OpenAI, Vertex AI, and Perplexity providers work
- v5: Fixed Ollama to use localhost URL, added reference to ask-ollama.md

---

## 📋 TASK DEFINITION

Call any model supported by LiteLLM with proper configuration and error handling.

### Parameters:
- `model`: (string) Model name (e.g., "gpt-4", "vertex_ai/gemini-2.0-flash-exp", "perplexity/sonar") - REQUIRED
- `query`: (string) The question/prompt to send to the model - REQUIRED
- `output_path`: (string) Where to save the response - REQUIRED
- `system_prompt`: (string) System prompt to guide model behavior - OPTIONAL
- `temperature`: (float) Temperature for response randomness (0.0-1.0) - OPTIONAL, default: 0.7
- `max_tokens`: (int) Maximum tokens in response - OPTIONAL, model-specific defaults
- `vertex_json_path`: (string) Path to vertex service account JSON - OPTIONAL, for Vertex AI models
- `thinking`: (bool) Enable thinking/reasoning mode - OPTIONAL, for supported models
- `fallback_models`: (list) List of fallback models if primary fails - OPTIONAL
- `ollama_base_url`: (string) Ollama API base URL - OPTIONAL, default: http://localhost:11434

### Supported Providers & Documentation:
- **OpenAI**: https://docs.litellm.ai/docs/providers/openai
  - Models: gpt-4, gpt-3.5-turbo, o1-preview, o1-mini
- **Vertex AI**: https://docs.litellm.ai/docs/providers/vertex
  - Models: vertex_ai/gemini-2.0-flash-exp, vertex_ai/gemini-2.0-pro
  - Requires: GOOGLE_APPLICATION_CREDENTIALS or vertex_json_path
- **Ollama**: https://docs.litellm.ai/docs/providers/ollama
  - Models: ollama/llama3, ollama/codellama, ollama/phi3:mini
  - Requires: Ollama server running locally
- **Perplexity**: https://docs.litellm.ai/docs/providers/perplexity
  - Models: perplexity/sonar, perplexity/sonar-medium
  - Best for: Real-time research with citations
- **Anthropic**: https://docs.litellm.ai/docs/providers/anthropic
  - Models: anthropic/claude-3-opus, anthropic/claude-3-sonnet

### Success Criteria:
- Model responds successfully
- Response saved to output_path
- Error handling for auth/quota issues
- Proper configuration for special models (Vertex AI)
- No hallucinations in execution

---

## 🚀 IMPLEMENTATION

```python
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
```

---

## 📊 EXECUTION LOG

### Run 1: 2025-06-27 - OpenAI Test
```
MARKER_LITELLM_20250627_110636
✓ Success! Response: LiteLLM integration successful!
Model: gpt-3.5-turbo
```

### Run 2: 2025-06-27 - Vertex AI Test
```
MARKER_LITELLM_20250627_110804
✓ Success! Generated haiku about Python programming
Model: vertex_ai/gemini-2.0-flash-exp
Used default credentials from ~/.config/gcloud/
```

### Run 3: 2025-06-27 - Perplexity Test
```
MARKER_PERPLEXITY_20250627_110909
✓ Success! Got response with citations about Python 3.12 features
Model: perplexity/sonar
```

### Run 4: 2025-06-27 - Ollama Test
```
MARKER_OLLAMA_20250627_111439
✓ Success! Generated Python add function
Model: ollama/phi3:mini
Fixed URL to use localhost:11434
```

---

## 🔧 RECOVERY TESTS

### Test 1: Environment Setup
```python
def test_environment():
    """Ensure LiteLLM environment is properly configured"""
    import sys
    import os
    
    # Check we're in the correct venv
    expected_venv = '/home/graham/workspace/experiments/llm_call/.venv'
    assert expected_venv in sys.executable, f"Wrong venv. Expected {expected_venv}, got {sys.executable}"
    
    # Check .env file exists and is loaded
    env_path = '/home/graham/workspace/experiments/llm_call/.env'
    assert os.path.exists(env_path), f".env file not found at {env_path}"
    
    # Load it to ensure API keys are available
    from dotenv import load_dotenv
    load_dotenv(env_path)
    
    try:
        import litellm
        print("✓ LiteLLM installed")
    except ImportError:
        raise AssertionError("LiteLLM not installed in venv")
    
    print("✓ Environment correctly configured")
```

### Test 2: OpenAI Access
```python
def test_openai_access():
    """Test OpenAI API access"""
    import os
    from litellm import completion
    
    if "OPENAI_API_KEY" not in os.environ:
        print("⚠ OPENAI_API_KEY not set - OpenAI models will fail")
        return False
    
    try:
        # Quick test with minimal tokens
        response = completion(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'OK'"}],
            max_tokens=5
        )
        print("✓ OpenAI access confirmed")
        return True
    except Exception as e:
        print(f"✗ OpenAI access failed: {e}")
        return False
```

### Test 3: Vertex AI Access
```python
def test_vertex_access():
    """Test Vertex AI access with Gemini"""
    import os
    from litellm import completion
    
    # Check for credentials
    cred_paths = [
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", ""),
        "/home/graham/.config/gcloud/application_default_credentials.json",
        os.path.expanduser("~/.config/gcloud/application_default_credentials.json")
    ]
    
    cred_found = False
    for path in cred_paths:
        if path and os.path.exists(path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path
            cred_found = True
            print(f"✓ Using Vertex credentials: {path}")
            break
    
    if not cred_found:
        print("⚠ No Vertex AI credentials found")
        return False
    
    try:
        response = completion(
            model="vertex_ai/gemini-2.0-flash-exp",
            messages=[{"role": "user", "content": "Say 'OK'"}],
            max_tokens=5
        )
        print("✓ Vertex AI access confirmed")
        return True
    except Exception as e:
        print(f"✗ Vertex AI access failed: {e}")
        return False
```

### Test 4: Ollama Access
```python
def test_ollama_access():
    """Test Ollama server access"""
    import subprocess
    from litellm import completion
    
    # Check Docker container first
    container_name = "llm-call-ollama"
    ollama_url = "http://localhost:11434"
    
    try:
        result = subprocess.run(['docker', 'exec', container_name, 'ollama', 'list'], 
                               capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            ollama_url = f"http://{container_name}:11434"
            print(f"✓ Ollama running in Docker: {container_name}")
            models = [line.split()[0] for line in result.stdout.strip().split('\n')[1:] if line.strip()]
            print(f"  Available models: {', '.join(models[:3])}...")
        else:
            # Try local Ollama
            result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                print("✓ Ollama running locally")
    except:
        print("⚠ Ollama not accessible - install and run 'ollama serve'")
        return False
    
    try:
        # Test with a small model
        response = completion(
            model="ollama/phi3:mini",
            messages=[{"role": "user", "content": "Say 'OK'"}],
            api_base=ollama_url,
            max_tokens=5
        )
        print("✓ Ollama access confirmed")
        return True
    except Exception as e:
        print(f"✗ Ollama access failed: {e}")
        return False
```

### Test 5: Perplexity Access
```python
def test_perplexity_access():
    """Test Perplexity API access"""
    import os
    from litellm import completion
    
    if "PERPLEXITY_API_KEY" not in os.environ:
        print("⚠ PERPLEXITY_API_KEY not set - Perplexity models will fail")
        return False
    
    try:
        response = completion(
            model="perplexity/sonar",
            messages=[{"role": "user", "content": "What is 2+2?"}],
            max_tokens=10
        )
        print("✓ Perplexity access confirmed")
        return True
    except Exception as e:
        print(f"✗ Perplexity access failed: {e}")
        return False
```

### Test 6: Run All Provider Tests
```python
def test_all_providers():
    """Test access to all providers"""
    print("Testing LiteLLM Provider Access:")
    print("-" * 40)
    
    results = {
        "OpenAI": test_openai_access(),
        "Vertex AI": test_vertex_access(),
        "Ollama": test_ollama_access(),
        "Perplexity": test_perplexity_access()
    }
    
    print("\nSummary:")
    working = sum(1 for v in results.values() if v)
    print(f"✓ {working}/4 providers accessible")
    
    if working == 0:
        print("\n⚠️ No providers accessible! Check your configuration.")
    elif working < 4:
        print("\n💡 Tip: Configure missing providers for full functionality")
```

---

## 🛠️ COMMON FAILURES & FIXES

### Failure 1: Missing API Keys
**Symptom**: Authentication errors
**Fix**: Ensure .env file has required keys (OPENAI_API_KEY, PERPLEXITY_API_KEY, etc.)
**Recovery**: Add fallback models that use available keys

### Failure 2: Vertex AI Auth
**Symptom**: Vertex AI models fail with auth error
**Fix**: Set GOOGLE_APPLICATION_CREDENTIALS or use vertex_json_path parameter
**Recovery**: Use gcloud auth or service account JSON

### Failure 3: Model Not Found
**Symptom**: Model name not recognized
**Fix**: Check exact model name in LiteLLM docs
**Recovery**: Use model list command or fallback to known model

### Failure 4: Rate Limits
**Symptom**: 429 errors or quota exceeded
**Fix**: Use caching, reduce temperature, add delays
**Recovery**: Automatic fallback to other models

---

## 📝 USAGE EXAMPLES

### Provider-Specific Examples

#### OpenAI
```python
# GPT-4 for complex reasoning
model="gpt-4" 
query="Analyze this algorithm's time complexity..."
output_path="/tmp/analysis.md"

# GPT-3.5 for quick tasks
model="gpt-3.5-turbo" 
temperature=0.3
```

#### Vertex AI (Gemini)
```python
# Gemini 2.0 with thinking mode
model="vertex_ai/gemini-2.0-flash-exp"
thinking=True
vertex_json_path="/home/graham/.config/gcloud/service-account.json"

# Gemini Pro for detailed analysis
model="vertex_ai/gemini-2.0-pro"
system_prompt="Provide thorough technical analysis"
```

#### Ollama (Local Models)
```python
# Llama 3 for general tasks
model="ollama/llama3"
ollama_base_url="http://localhost:11434"

# CodeLlama for programming
model="ollama/codellama"
query="Refactor this Python function..."

# Phi3 for quick responses
model="ollama/phi3:mini"
```

#### Perplexity (Research)
```python
# Real-time research with citations
model="perplexity/sonar-medium"
query="Latest breakthroughs in quantum computing 2025"
temperature=0.5

# Quick factual queries
model="perplexity/sonar"
```

### Advanced Configurations
```python
# Multi-provider fallback chain
model="vertex_ai/gemini-2.0-flash-exp"
fallback_models=["gpt-4", "ollama/llama3", "perplexity/sonar"]

# Custom system prompts by task
system_prompt="You are a security expert. Analyze for vulnerabilities."

# Model-specific parameters
max_tokens=4000  # For long responses
temperature=0.1  # For deterministic output
```

---

## 🎯 GRADUATION CRITERIA

When this prompt achieves 10:1 success ratio:
1. Move implementation to `src/cc_executor/utils/litellm_interface.py`
2. Create proper CLI with click
3. Add comprehensive model catalog
4. Implement response caching
5. Add streaming support for long responses