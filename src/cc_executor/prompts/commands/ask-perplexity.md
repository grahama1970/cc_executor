# Ask Perplexity Command

Research this topic using Perplexity and return real-time information with sources.

## Parameters:
- `query`: (string) The research question to ask Perplexity - REQUIRED, CANNOT BE EMPTY
- `output_path`: (string) Where to save the response - REQUIRED, MUST BE WRITABLE
- `system_prompt`: (string) System prompt to guide model behavior - OPTIONAL, has smart defaults
- `temperature`: (float) Temperature for response randomness (0.0-1.0) - OPTIONAL, default: 0.5
- `model`: (string) Override the default Perplexity model - OPTIONAL, default from env

## Expected Output:
- Provide current, factual information with citations
- Include sources like [1], [2] for each claim
- If information is unavailable or uncertain, state clearly
- Focus on accuracy over completeness

## Code Example:
```python
#!/usr/bin/env python3
# This is a sample implementation. You should adapt it based on the specific query.
import sys
import os

# Ensure virtual environment is active
if '.venv' not in sys.executable:
    print("ERROR: Virtual environment not active. Please run: source /home/graham/workspace/experiments/llm_call/.venv/bin/activate", file=sys.stderr)
    sys.exit(1)

from dotenv import load_dotenv
load_dotenv('/home/graham/workspace/experiments/llm_call/.env')
from litellm import completion

# Initialize caching for better performance
try:
    sys.path.append('/home/graham/workspace/experiments/llm_call/src/llm_call/usage/docs/tasks/claude_poll_poc_v2/scripts')
    from initialize_litellm_cache import initialize_litellm_cache
    initialize_litellm_cache()
except ImportError:
    # If script not available, caching is optional
    pass

# Parameters - REPLACE WITH ACTUAL VALUES
query = """REPLACE_WITH_QUERY_TEXT"""  # Required - Must not be empty
output_path = "REPLACE_WITH_OUTPUT_PATH"  # Required - Must be a writable path
system_prompt = """REPLACE_WITH_SYSTEM_PROMPT_OR_NONE"""  # Optional - Set to None for auto-generated
temperature = 0.5  # Optional - Adjust for more/less randomness
model_override = None  # Optional - Set to specific model name to override default

# Validate inputs
if not query.strip():
    print("ERROR: Query cannot be empty", file=sys.stderr)
    sys.exit(1)

if not output_path:
    print("ERROR: Output path must be specified", file=sys.stderr)
    sys.exit(1)

# Test if we can write to the output directory
try:
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # Test write permissions
    test_file = output_path + '.tmp'
    with open(test_file, 'w') as f:
        f.write('test')
    os.remove(test_file)
except Exception as e:
    print(f"ERROR: Cannot write to output path '{output_path}': {e}", file=sys.stderr)
    sys.exit(1)

# Get model from environment or use override
model = model_override or os.getenv('SLASHCMD_ASK_PERPLEXITY_MODEL', 'sonar-pro')

# Build system prompt - use provided or generate based on query
if system_prompt == "REPLACE_WITH_SYSTEM_PROMPT_OR_NONE" or system_prompt == "None" or not system_prompt:
    # Auto-generate system prompt based on query type
    if "research" in query.lower() or "sources" in query.lower():
        system_prompt = """You are Perplexity, a research assistant with real-time web access.
Provide factual, up-to-date information with clear source citations.
Include relevant citations like [1], [2] for each claim.
Prioritize accuracy and credibility over comprehensiveness."""
    elif "news" in query.lower() or "latest" in query.lower() or "current" in query.lower():
        system_prompt = """You are Perplexity, focusing on current events and recent developments.
Provide the most recent information available with timestamps when possible.
Cite all sources and clearly indicate the date of information.
If information is rapidly changing, note this in your response."""
    else:
        system_prompt = """You are Perplexity, an AI assistant with real-time web search capabilities.
Provide accurate, factual information with proper source citations.
Always include citations like [1], [2] for verifiable claims.
If information is uncertain or unavailable, state this clearly.
For quick lookups without sources needed, suggest using a different model."""

# Build messages with system prompt
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": query}
]

# Make the API call
try:
  response = completion(
    model=model,
    messages=messages,
    temperature=temperature
    # NOTE: No max_tokens - let Perplexity provide complete research results
  )
  
  if response.choices and response.choices[0].message.content:
    result = response.choices[0].message.content
    # Write the response
    with open(output_path, "w") as f:
      f.write(result)
    
    print(f"Successfully wrote response to {output_path}")
    print(f"Response length: {len(result)} characters")
    
    # Check if response includes citations
    if '[1]' in result or '[2]' in result:
        print("Response includes source citations")
    else:
        print("WARNING: Response may lack source citations")
    
    # VERIFICATION: Print a checksum to prevent hallucination
    import hashlib
    checksum = hashlib.md5(result.encode()).hexdigest()[:8]
    print(f"Response checksum: {checksum}")
    print(f"Verify with: echo -n '{result[:50]}...' | md5sum")
    
    sys.exit(0)
  else:
    finish_reason = response.choices[0].finish_reason if response.choices else 'unknown'
    error_message = f"ERROR: Perplexity returned empty content. Finish reason: {finish_reason}"
    print(error_message, file=sys.stderr)
    # Try to write error info if possible
    try:
      with open(output_path, "w") as f:
        f.write(error_message)
    except:
      pass  # Ignore write errors in error handler
    
    sys.exit(1)
    
except Exception as e:
  error_type = type(e).__name__
  error_msg = str(e)
  
  # Check for common errors
  if "API key" in error_msg or "PERPLEXITY_API_KEY" in error_msg:
    print(f"ERROR: Perplexity API key not configured. Set PERPLEXITY_API_KEY environment variable.", file=sys.stderr)
  elif "model not found" in error_msg:
    print(f"ERROR: Model '{model}' not available. Check SLASHCMD_ASK_PERPLEXITY_MODEL setting.", file=sys.stderr)
  else:
    print(f"FATAL ERROR calling Perplexity: {error_type}: {error_msg}", file=sys.stderr)
  
  # Try to write detailed error info if possible
  try:
    import traceback
    with open(output_path + '.error', "w") as f:
      f.write(f"FATAL ERROR:\n{traceback.format_exc()}")
    print(f"Detailed error written to {output_path}.error", file=sys.stderr)
  except:
    pass  # Ignore write errors in error handler
  
  sys.exit(1)
```

---
## [TESTING & SELF_CORRECTION]

**Purpose:** This section defines test cases AND how to fix the template when tests fail.

### Test Cases

#### 1. Basic Success Test
```python
query = """What are the latest developments in quantum computing in 2024?"""
output_path = "test_perplexity_response.txt"
system_prompt = None  # Will use auto-generated default
temperature = 0.5
model_override = None

# EXPECTED BEHAVIOR:
# - Exit code: 0
# - Output file contains response with citations like [1], [2]
# - Stdout: "Successfully wrote response to test_perplexity_response.txt"
# - Stdout: "Response includes source citations"
```

#### 2. Empty Query Test
```python
query = """"""
output_path = "test_empty.txt"

# EXPECTED BEHAVIOR:
# - Exit code: 1
# - Stderr: "ERROR: Query cannot be empty"
# - No output file created
```

#### 3. Invalid Output Path Test
```python
query = """Latest AI news"""
output_path = "/root/forbidden/test.txt"

# EXPECTED BEHAVIOR:
# - Exit code: 1
# - Stderr: "ERROR: Cannot write to output path '/root/forbidden/test.txt': [Errno 13] Permission denied"
# - No API call made (fails during validation)
```

#### 4. Missing API Key Test
```python
# With PERPLEXITY_API_KEY unset
query = """Test query"""
output_path = "test.txt"

# EXPECTED BEHAVIOR:
# - Exit code: 1
# - Stderr: "ERROR: Perplexity API key not configured. Set PERPLEXITY_API_KEY environment variable."
# - test.txt.error file created with full traceback
```

#### 5. Citation Verification Test
```python
query = """What is the current population of Tokyo?"""
output_path = "test_citations.txt"
system_prompt = None
temperature = 0.5
model_override = None

# EXPECTED BEHAVIOR:
# - Exit code: 0
# - Response includes numbered citations [1], [2], etc.
# - Response may include source URLs at the end
# - Stdout: "Response includes source citations"
```

#### 6. Custom System Prompt Test
```python
query = """Explain blockchain technology"""
output_path = "test_custom_prompt.txt"
system_prompt = """You are a technical writer. Explain complex topics in simple terms without using jargon. Do not include citations."""
temperature = 0.3
model_override = None

# EXPECTED BEHAVIOR:
# - Exit code: 0
# - Response in simple language without technical jargon
# - May or may not include citations (depends on Perplexity's behavior)
```

#### 7. Model Override Test
```python
query = """Hello"""
output_path = "test_model_override.txt"
system_prompt = None
temperature = 0.5
model_override = "sonar"  # Use basic sonar model

# EXPECTED BEHAVIOR:
# - Exit code: 0 (if model exists) or 1 (if model not found)
# - If successful, uses the basic sonar model
# - If model not found, error message about model not available
```

### Self-Correction Process

**When a test fails:**

1. **Run the failing test** and capture:
   - Exit code
   - Stderr output
   - Stdout output
   - Any files created

2. **Compare to expected behavior** and identify the discrepancy

3. **Diagnose the root cause:**
   - **Code Bug**: The Python code doesn't handle the case correctly
   - **Wrong Expectation**: The expected behavior is incorrect
   - **Missing Validation**: The code should catch this error earlier
   - **Poor Error Message**: The error exists but message is unclear
   - **External Issue**: Environment problem (don't modify template)

4. **Fix the template:**
   ```json
   {
     "failed_test": "Test name that failed",
     "actual_behavior": "What actually happened",
     "expected_behavior": "What should have happened", 
     "root_cause": "Why it failed",
     "fix_applied": "What changes were made to the template",
     "revised_template": "Complete updated template content"
   }
   ```

5. **Verify the fix** by running ALL test cases

### Verification Against Hallucination

**CRITICAL**: The implementing agent MUST verify their own outputs to prevent hallucination.

**Self-verification process**:
1. After running the code, capture the output
2. Check the transcript to verify the output matches:
```bash
# Check your own execution in the logs
tail -n 100 ~/.claude/projects/*/*.jsonl | grep -A5 -B5 "output_path_value\|unique_output_text"
```
3. Verify the file exists and contains what you reported:
```bash
cat <output_path> && ls -la <output_path>
```

**Example self-check**:
```python
# After writing response
print(f"SELF-CHECK: Response starts with '{result[:30]}'")
print(f"SELF-CHECK: File size is {os.path.getsize(output_path)} bytes")
# Then grep for these unique strings in the transcript
```

This prevents the implementing agent from hallucinating successful execution when it actually failed.

### Previous Issues Fixed:

**IMPORTANT**: These issues have been encountered and fixed:

1. **Citation Handling**:
  - **Root Cause**: Perplexity includes citations [1], [2] in responses
  - **Fix Applied**: Added citation detection and warning
  - **Note**: Citations are part of the value, not a bug

2. **Virtual Environment Issue**:
  - **Root Cause**: Script ran without venv, missing dependencies
  - **Fix Applied**: Added venv check at start of script
  - **Prevention**: Always check `.venv` in sys.executable

3. **API Key Error Messages**:
  - **Root Cause**: Generic error messages don't help users
  - **Fix Applied**: Specific check for "API key" in error message
  - **Clear Message**: Points directly to PERPLEXITY_API_KEY env var

4. **Output Path Validation**:
  - **Root Cause**: Would fail after API call if path invalid
  - **Fix Applied**: Pre-validate directory exists and is writable
  - **Benefit**: Saves API calls when output path is invalid

### Adding New Test Cases

When you discover a new failure mode, add it as a test case:

```python
#### N. [Descriptive Name] Test
query = """[test input]"""
output_path = "[test path]"

# EXPECTED BEHAVIOR:
# - Exit code: [0 or 1]
# - Stderr: "[expected error message]"
# - Stdout: "[expected success message]"
# - Files: [what files should/shouldn't exist]
```

This ensures the template continuously improves and doesn't regress.


## Model Selection:
- **sonar-reasoning-pro**: For complex analytical research requiring deep thinking
- **sonar-pro**: For general-purpose research queries  
- **sonar-deep-research**: For comprehensive research requiring multiple sources
- **sonar**: For simple, quick lookups

## Parameters:
- `reasoning_effort="high"`: Use for complex analysis (requires LiteLLM v1.72.6+)
- Always include proper error handling
- Return actual results with sources, not hallucinated content

## Helpful Documentation:
*Read these if you get stuck or confused:*
- **Perplexity Setup**: https://docs.litellm.ai/docs/providers/perplexity
- **LiteLLM Completion**: https://docs.litellm.ai/docs/completion/quick_start
- **Reasoning Parameters**: https://docs.litellm.ai/docs/providers/perplexity#reasoning-effort

Usage: `/user:ask-perplexity today's weather forecast with analysis`