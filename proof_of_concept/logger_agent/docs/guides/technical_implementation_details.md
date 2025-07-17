# Technical Implementation Details: Gemini Batch Processing

## How Tools Are Discovered and Executed

### 1. Tool Discovery Mechanism

The tools in `.claude/tools/` are **NOT** in tools.json. They use a special annotation format:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "litellm",
#     "python-dotenv",
#     "loguru",
# ]
# ///

# @tool
# tool_name: SendToGeminiBatch
# description: Sends multiple files to Gemini for fixing
# input_schema:
#   type: object
#   properties:
#     issue_report_file:
#       type: string
#       description: Path to markdown file
```

This annotation format allows Claude Code to:
1. Discover the tool automatically
2. Understand its parameters
3. Execute it with `uv run`

### 2. Tool Execution by Agent

When I (the agent) want to use these tools, I execute them as subprocess commands:

```python
# I don't use a special tool function - I use Bash:
uv run .claude/tools/send_to_gemini_batch.py '{
    "issue_report_file": "tmp/issues/fix_logger_bind.md",
    "files_to_fix": ["src/arango_log_sink.py"],
    "max_tokens": 7500
}'
```

## The Complete Code Flow

### Step 1: SendToGeminiBatch Tool

**Key Functions:**

```python
def extract_context_sections(issue_report: str) -> dict:
    """Extract different sections from the issue report."""
    sections = {
        'header': '',
        'context_files': {},
        'requirements': '',
        'footer': ''
    }
    
    # Extract all context files using regex
    context_pattern = r'<!-- CODE_CONTEXT_START: (.*?) -->\n```.*?\n(.*?)\n```\n<!-- CODE_CONTEXT_END: .*? -->'
    for match in re.finditer(context_pattern, issue_report, re.DOTALL):
        file_path = match.group(1)
        file_content = match.group(2)
        sections['context_files'][file_path] = file_content
```

**For Each File to Fix:**

```python
def create_single_file_request(sections: dict, file_to_fix: str) -> str:
    """Create a focused request for a single file with all context."""
    
    request = f"""{sections['header']}

## Current Focus: Fix {file_to_fix}

**IMPORTANT**: Fix ONLY {file_to_fix} in this response.

## All Context Files (For Reference)
"""
    
    # Include ALL context files, marking the one to fix
    for file_path, content in sections['context_files'].items():
        if file_path == file_to_fix:
            request += f"<!-- CODE_CONTEXT_START: {file_path} --> **[THIS IS THE FILE TO FIX]**\n"
        else:
            request += f"<!-- CODE_CONTEXT_START: {file_path} -->\n"
        request += f"```python\n{content}\n```\n"
```

**API Call to Gemini:**

```python
async def send_single_file_to_gemini(request_content: str, output_file: str, temperature: float = 0.1, max_tokens: int = 7500) -> dict:
    """Send a single file fix request to Gemini."""
    
    # Call Gemini Flash via LiteLLM
    response = litellm.completion(
        model="vertex_ai/gemini-1.5-flash",
        messages=[{"role": "user", "content": request_content}],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    
    # Extract response
    gemini_response = response.choices[0].message.content.strip()
    
    # Calculate cost using LiteLLM
    from litellm import completion_cost
    cost = completion_cost(completion_response=response)
    
    # Save response with cost summary
    Path(output_file).write_text(gemini_response + cost_summary)
```

### Step 2: Extract Code from Markdown Response

**The Extraction Script (`extract_code_from_markdown.py`):**

```python
class CodeExtractor:
    def extract(self) -> Dict[str, any]:
        """Extract all code files from markdown."""
        content = self.markdown_file.read_text()
        
        # Pattern to match code blocks with CODE_FILE markers
        pattern = r'<!-- CODE_FILE_START: (.*?) -->\n```(?:.*?)\n(.*?)\n```\n<!-- CODE_FILE_END: (.*?) -->'
        
        matches = re.finditer(pattern, content, re.DOTALL)
        
        for match in matches:
            start_path = match.group(1).strip()  # e.g., "src/arango_log_sink.py"
            code_content = match.group(2)         # The actual Python code
            end_path = match.group(3).strip()
            
            # Validate matching paths
            if start_path != end_path:
                self.errors.append(f"Mismatched file paths")
                continue
            
            # Create full path
            full_path = self.output_dir / start_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(code_content)
```

**The ExtractGeminiCode Tool Wrapper:**

```python
def main():
    # This tool calls the extraction script
    result = subprocess.run(
        [sys.executable, str(extract_script), str(markdown_path), str(output_path), "--validate"],
        capture_output=True,
        text=True
    )
    
    # Returns summary without loading full content
    extraction_summary = {
        "success": True,
        "output_directory": str(output_path),
        "files": [
            {
                "path": "src/arango_log_sink.py",
                "full_path": "/path/to/tmp/gemini_extracted_20250715_063317/src/arango_log_sink.py",
                "size": 15234,
                "lines": 522
            }
        ]
    }
```

### Step 3: How the Agent Uses This

Here's exactly what happens when I process files:

1. **I execute the batch tool:**
```bash
$ uv run .claude/tools/send_to_gemini_batch.py '{"issue_report_file": "tmp/issues/fix_logger_bind.md", "files_to_fix": ["src/arango_log_sink.py"]}'
```

2. **The tool outputs JSON to stdout:**
```json
{
  "success": true,
  "output_directory": "tmp/gemini_batch_20250715_063222",
  "files_processed": 1,
  "total_cost": 0.0016,
  "results": [
    {
      "success": true,
      "output_file": "tmp/gemini_batch_20250715_063222/response_1_arango_log_sink.md",
      "cost": 0.0016,
      "code_files": ["src/arango_log_sink.py"],
      "has_code_markers": true
    }
  ]
}
```

3. **I extract the code:**
```bash
$ uv run .claude/tools/extract_gemini_code.py '{"markdown_file": "tmp/gemini_batch_20250715_063222/response_1_arango_log_sink.md"}'
```

4. **The extraction tool outputs:**
```json
{
  "success": true,
  "output_directory": "tmp/gemini_extracted_20250715_063317",
  "files": [
    {
      "path": "src/arango_log_sink.py",
      "full_path": "tmp/gemini_extracted_20250715_063317/src/arango_log_sink.py",
      "lines": 522
    }
  ]
}
```

5. **I apply the fix:**
```bash
$ cp tmp/gemini_extracted_20250715_063317/src/arango_log_sink.py src/arango_log_sink.py
```

## Why This Architecture?

### 1. **Not Using tools.json**
- These are project-specific tools
- They use `uv run --script` for dependency management
- They're discoverable through `@tool` annotations

### 2. **Subprocess Execution**
- I execute them using the Bash tool
- They communicate via JSON on stdout
- Errors are reported via exit codes and stderr

### 3. **File-Based Communication**
- Tools write files to tmp/ directories
- I read/copy files using standard file operations
- This avoids loading large content into memory

### 4. **Batch Processing Logic**
- Each file gets its own Gemini API call (to handle 8K output limit)
- But ALL files are sent as context (utilizing 1M input limit)
- This ensures Gemini understands relationships between files

## The Markdown Format Gemini Must Follow

Gemini's response MUST include:

```markdown
<!-- CODE_FILE_START: src/arango_log_sink.py -->
```python
#!/usr/bin/env python3
# Complete file content - no ellipsis, no placeholders
# All 500+ lines of actual code
```
<!-- CODE_FILE_END: src/arango_log_sink.py -->
```

The extraction regex specifically looks for:
- `<!-- CODE_FILE_START: (.*?) -->` - captures filename
- ` ```python\n(.*?)\n``` ` - captures code content
- `<!-- CODE_FILE_END: (.*?) -->` - validates matching filename

## Error Handling and Retries

### First Attempt Failure:
```python
# If extraction finds no code markers:
if not code_files:
    # I analyze Gemini's response manually
    # Create new issue report with clearer instructions
    # Retry with more explicit format requirements
```

### Second Attempt Failure:
```python
# After 2 failures, I create a failure report:
failure_report = {
    "file": "src/problematic_file.py",
    "attempt_1": {
        "error": "No code markers found",
        "gemini_response_excerpt": "..."
    },
    "attempt_2": {
        "error": "Incomplete code - used ellipsis",
        "gemini_response_excerpt": "..."
    },
    "recommended_approach": "Manual intervention needed"
}
```

## Key Implementation Details

1. **Cost Tracking**: Uses LiteLLM's `completion_cost()` function
2. **Token Management**: Each file limited to 7500 output tokens (safety margin from 8192)
3. **Progress Reporting**: Real-time output during batch processing
4. **Validation**: Python syntax checking in extraction script
5. **Metadata**: Tracks usage, costs, and timestamps for debugging

This is the complete technical implementation - no hidden tools.json entries, just Python scripts executed via subprocess with JSON communication.