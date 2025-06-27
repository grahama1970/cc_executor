# Ask Gemini Flash Command

Ask Gemini Flash this question and get a quick, balanced response.

## Parameters:
- `query`: (string) The question/prompt to send to Gemini - REQUIRED, CANNOT BE EMPTY
- `output_path`: (string) Where to save the response - REQUIRED, MUST BE WRITABLE
- `system_prompt`: (string) System prompt to guide model behavior - OPTIONAL, has smart defaults
- `temperature`: (float) Temperature for response randomness (0.0-1.0) - OPTIONAL, default: 0.7
- `model`: (string) Override the default Gemini Flash model - OPTIONAL, default from env

## Implementation Notes:
- The template includes dynamic system prompts that adapt based on query type
- You can further customize the system prompt based on the specific use case
- System prompts help guide the model to provide appropriate responses
- For Gemini models, system role support may vary - the template handles both cases

## Expected Output:
- Provide clear, concise answers (limit ~500 tokens per answer/critique)
- Use creative but accurate tone
- For complex code tasks, suggest using ask-gemini-pro instead
- If unable to answer, explain why clearly

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
temperature = 0.7  # Optional - Adjust for more/less randomness
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
model = model_override or os.getenv('SLASHCMD_ASK_GEMINI_FLASH_MODEL', 'vertex_ai/gemini-2.5-flash')

# Build system prompt - use provided or generate based on query
if system_prompt == "REPLACE_WITH_SYSTEM_PROMPT_OR_NONE" or system_prompt == "None" or not system_prompt:
    # Auto-generate system prompt based on query type
    if "code" in query.lower() or "debug" in query.lower():
        system_prompt = """You are Gemini Flash, a fast coding assistant.
Provide concise, working code solutions with brief explanations.
For complex algorithms or large codebases, recommend using Gemini Pro.
Focus on clarity and correctness."""
    elif "explain" in query.lower() or "what is" in query.lower():
        system_prompt = """You are Gemini Flash, a clear and patient teacher.
Explain concepts simply and concisely, using analogies when helpful.
Limit explanations to key points unless asked for more detail."""
    else:
        system_prompt = """You are Gemini Flash, a fast and efficient AI assistant. 
Provide clear, concise answers focused on being helpful and accurate. 
Limit responses to about 500 tokens unless more detail is specifically requested.
For complex coding tasks, suggest using a more powerful model like Gemini Pro.
Be creative but factual in your responses."""

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
  )
  
  if response.choices and response.choices[0].message.content:
    result = response.choices[0].message.content
    # Write the response
    with open(output_path, "w") as f:
      f.write(result)
    
    print(f"Successfully wrote response to {output_path}")
    print(f"Response length: {len(result)} characters")
    
    # VERIFICATION: Print a checksum to prevent hallucination
    import hashlib
    checksum = hashlib.md5(result.encode()).hexdigest()[:8]
    print(f"Response checksum: {checksum}")
    print(f"Verify with: echo -n '{result[:50]}...' | md5sum")
    
    sys.exit(0)
  else:
    finish_reason = response.choices[0].finish_reason if response.choices else 'unknown'
    error_message = f"ERROR: Gemini returned empty content. Finish reason: {finish_reason}"
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
  if "GOOGLE_APPLICATION_CREDENTIALS" in error_msg:
    print(f"ERROR: Google credentials not configured. Set GOOGLE_APPLICATION_CREDENTIALS environment variable.", file=sys.stderr)
  elif "contents field is required" in error_msg:
    print(f"ERROR: Query is empty or invalid", file=sys.stderr)
  else:
    print(f"FATAL ERROR calling Gemini: {error_type}: {error_msg}", file=sys.stderr)
  
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
query = """What is 2+2? Please answer in one sentence."""
output_path = "test_gemini_response.txt"
system_prompt = None  # Will use auto-generated default
temperature = 0.7
model_override = None

# EXPECTED BEHAVIOR:
# - Exit code: 0
# - Output file contains: "2 + 2 equals 4." or similar
# - Stdout: "Successfully wrote response to test_gemini_response.txt"
# - Stdout: "Response length: [20-50] characters"
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
query = """Hello"""
output_path = "/root/forbidden/test.txt"

# EXPECTED BEHAVIOR:
# - Exit code: 1
# - Stderr: "ERROR: Cannot write to output path '/root/forbidden/test.txt': [Errno 13] Permission denied"
# - No API call made (fails during validation)
```

#### 4. Missing Credentials Test
```python
# With GOOGLE_APPLICATION_CREDENTIALS unset
query = """Hello"""
output_path = "test.txt"

# EXPECTED BEHAVIOR:
# - Exit code: 1
# - Stderr: "ERROR: Google credentials not configured. Set GOOGLE_APPLICATION_CREDENTIALS environment variable."
# - test.txt.error file created with full traceback
```

#### 5. Cache Import Failure Test
```python
# When initialize_litellm_cache script is not available
query = """Test query"""
output_path = "test_no_cache.txt"

# EXPECTED BEHAVIOR:
# - Exit code: 0 (should continue without caching)
# - No import errors visible
# - API call succeeds without caching
# - Output file created normally
```

#### 6. Custom System Prompt Test
```python
query = """What is the capital of France?"""
output_path = "test_custom_prompt.txt"
system_prompt = """You are a geography expert. Answer in exactly 5 words."""
temperature = 0.1  # Low temperature for consistent output
model_override = None

# EXPECTED BEHAVIOR:
# - Exit code: 0
# - Response should be exactly 5 words
# - Should answer "The capital is Paris, France" or similar 5-word response
```

#### 7. Model Override Test
```python
query = """Hello"""
output_path = "test_model_override.txt"
system_prompt = None
temperature = 0.5
model_override = "vertex_ai/gemini-1.5-flash-8b"  # Use a specific model

# EXPECTED BEHAVIOR:
# - Exit code: 0 (if model exists) or 1 (if model not found)
# - If successful, uses the specified model
# - If model not found, error message about model not accessible
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