# Ask Gemini Pro Command

Ask Gemini Pro for detailed analysis, complex reasoning, or thorough responses.

## Parameters:
- `query`: (string) The full text of the question/request for Gemini Pro - REQUIRED, CANNOT BE EMPTY
- `output_path`: (string) The file path where the response should be saved - REQUIRED, MUST BE WRITABLE
- `system_prompt`: (string) System prompt to guide model behavior - OPTIONAL, has smart defaults
- `temperature`: (float) Temperature for response randomness (0.0-1.0) - OPTIONAL, default: 0.3
- `model`: (string) Override the default Gemini Pro model - OPTIONAL, default from env

## Expected Output:
- Provide detailed, thorough analysis or responses
- Include comprehensive reasoning and multiple perspectives
- Use lower temperature for precise, consistent answers
- For quick/simple tasks, suggest using ask-gemini-flash instead

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
temperature = 0.3  # Optional - Lower for more precise responses
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
model = model_override or os.getenv('SLASHCMD_ASK_GEMINI_PRO_MODEL', 'vertex_ai/gemini-2.0-pro')

# Build system prompt - use provided or generate based on query
if system_prompt == "REPLACE_WITH_SYSTEM_PROMPT_OR_NONE" or system_prompt == "None" or not system_prompt:
    # Auto-generate system prompt based on query type
    if "code" in query.lower() or "review" in query.lower() or "debug" in query.lower():
        system_prompt = """You are Gemini Pro, an advanced coding assistant.
Provide thorough code analysis with detailed explanations.
Consider edge cases, performance implications, and best practices.
Include code examples and multiple implementation approaches when relevant."""
    elif "analyze" in query.lower() or "critique" in query.lower():
        system_prompt = """You are Gemini Pro, a thoughtful analyst.
Provide comprehensive analysis considering multiple perspectives.
Include pros/cons, potential implications, and detailed reasoning.
Be thorough but organize your response with clear sections."""
    else:
        system_prompt = """You are Gemini Pro, an advanced AI assistant optimized for detailed analysis. 
Provide comprehensive, well-reasoned responses with multiple perspectives.
For simple questions, still provide complete answers but suggest Gemini Flash for efficiency.
Organize complex responses with clear sections and detailed explanations."""

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
    # NOTE: No max_tokens parameter - let Gemini Pro provide complete analysis
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
    error_message = f"ERROR: Gemini Pro returned empty content. Finish reason: {finish_reason}"
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
    print(f"FATAL ERROR calling Gemini Pro: {error_type}: {error_msg}", file=sys.stderr)
  
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
query = """Analyze this Python function and suggest improvements:
def add(a, b):
    return a + b"""
output_path = "test_gemini_pro_response.txt"
system_prompt = None  # Will use auto-generated default
temperature = 0.3
model_override = None

# EXPECTED BEHAVIOR:
# - Exit code: 0
# - Output file contains detailed analysis with multiple improvement suggestions
# - Stdout: "Successfully wrote response to test_gemini_pro_response.txt"
# - Stdout: "Response length: [500-2000] characters"
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
query = """Analyze this code"""
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

#### 5. Token Limit Test
```python
query = """Write a complete implementation of a web server in Python with all error handling"""
output_path = "test_long_response.txt"
system_prompt = None
temperature = 0.3
model_override = None

# EXPECTED BEHAVIOR:
# - Exit code: 0
# - Complete response without truncation (no max_tokens limit)
# - Response should be comprehensive (likely > 2000 characters)
# - finish_reason should be 'stop' not 'length'
```

#### 6. Custom System Prompt Test
```python
query = """What is recursion?"""
output_path = "test_custom_prompt.txt"
system_prompt = """You are a computer science professor. Explain concepts using formal definitions and mathematical notation."""
temperature = 0.1  # Low temperature for consistent output
model_override = None

# EXPECTED BEHAVIOR:
# - Exit code: 0
# - Response includes formal CS terminology and possibly mathematical notation
# - Different tone/style compared to default system prompt
```

#### 7. Model Override Test
```python
query = """Hello"""
output_path = "test_model_override.txt"
system_prompt = None
temperature = 0.3
model_override = "vertex_ai/gemini-2.0-flash"  # Use Flash instead of Pro

# EXPECTED BEHAVIOR:
# - Exit code: 0 (if model exists) or 1 (if model not found)
# - If successful, uses the Flash model (shorter response)
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

### Previous Issues Fixed:

**IMPORTANT**: These issues have been encountered and fixed:

1. **None Response Issue**: When Gemini Pro returns None:
  - **Root Cause**: Often due to hitting token limit (finish_reason='length')
  - **Fix Applied**: Removed max_tokens parameter completely
  - **Debug Info**: Always check `response.choices[0].finish_reason`

2. **Virtual Environment Issue**:
  - **Root Cause**: Script ran without venv, missing dependencies
  - **Fix Applied**: Added venv check at start of script
  - **Prevention**: Always check `.venv` in sys.executable

3. **Output Directory Permissions**:
  - **Root Cause**: Trying to write to non-existent or protected directories
  - **Fix Applied**: Pre-check directory exists and is writable
  - **Test Write**: Create temp file first to verify permissions

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


## Model Information:
- **Configured Model**: The environment variable `SLASHCMD_ASK_GEMINI_PRO_MODEL` determines the actual model
- **Common Models**:
 - `vertex_ai/gemini-2.5-pro`: Stable version
 - `vertex_ai/gemini-2.5-pro-preview-06-05`: Advanced version with enhanced capabilities
- **Best for**: Complex code generation, code reviews, debugging, architecture analysis, detailed critiques
- **Features**: Advanced reasoning, multi-modal support, function calling, detailed code analysis

## Environment Requirements:
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account JSON file
- `VERTEX_PROJECT`: Google Cloud project ID (optional, can be in credentials)
- `VERTEX_LOCATION`: Region like 'us-central1' (optional)

## Helpful Documentation:
*Read these if you get stuck or confused:*
- **Vertex AI Setup**: https://docs.litellm.ai/docs/providers/vertex
- **Gemini Models**: https://cloud.google.com/vertex-ai/docs/generative-ai/model-reference/gemini
- **Authentication**: https://cloud.google.com/docs/authentication/getting-started

## Usage Examples:
- `/user:ask-gemini-pro Review this Python class for best practices`
- `/user:ask-gemini-pro Debug this function that's causing memory leaks`
- `/user:ask-gemini-pro Refactor this code to be more efficient`
- `/user:ask-gemini-pro Write unit tests for this API endpoint`

## Notes:
- Pro model is more powerful but slower than Flash
- Optimized for complex reasoning and detailed code analysis
- Use for code reviews, debugging, and architectural decisions
- For simple code generation, consider ask-gemini-flash instead