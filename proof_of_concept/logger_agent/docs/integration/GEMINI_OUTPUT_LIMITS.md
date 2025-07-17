# Handling Gemini's 8K Output Token Limit

## The Problem

Gemini Flash has a 1M token input window but only 8,192 output tokens. This means:
- Can send massive context (multiple files, documentation, examples)
- Can only receive ~30KB of fixed code back
- A single large file can exceed this limit

## Recommended Strategies

### 1. One File Per Request (Best Practice)

```python
async def fix_multiple_files(files_with_issues: dict):
    """Fix multiple files by sending them one at a time."""
    results = []
    
    for file_path, issues in files_with_issues.items():
        # Create focused issue report for single file
        issue_report = create_single_file_issue_report(
            file_path=file_path,
            issues=issues,
            include_context=True
        )
        
        # Send to Gemini
        result = await send_to_gemini(issue_report, max_tokens=8000)
        results.append(result)
        
        # Apply fix immediately
        if result['success']:
            apply_single_file_fix(result['output_file'])
    
    return results
```

### 2. Function-Level Fixes

```python
def create_function_fix_request(file_path: str, function_issues: list):
    """Request fixes for specific functions only."""
    return f"""
# Fix Specific Functions

File: {file_path}

## Issues to Fix:
{format_function_issues(function_issues)}

## Instructions:
- Return ONLY the fixed functions
- Include complete function definitions
- Maintain exact indentation
- Use markers: <!-- FUNCTION_START: function_name --> 

## Functions to Fix:
{extract_functions_with_context(file_path, function_issues)}
"""
```

### 3. Incremental Fixing

```python
class IncrementalFixer:
    """Fix large files incrementally."""
    
    def __init__(self, file_path: str, issues: list):
        self.file_path = file_path
        self.issues = self.categorize_issues(issues)
        self.sections = self.split_file_logically()
    
    async def fix_all(self):
        """Fix file section by section."""
        fixed_sections = []
        
        for section in self.sections:
            if self.has_issues_in_section(section):
                fixed = await self.fix_section(section)
                fixed_sections.append(fixed)
            else:
                fixed_sections.append(section['content'])
        
        return self.merge_sections(fixed_sections)
```

## Example: Multi-File Fix Workflow

```python
# workflow_example.py

async def fix_codebase_issues(issue_analysis: dict):
    """Complete workflow for fixing multiple files."""
    
    # Step 1: Prioritize files by severity
    files_by_priority = prioritize_files(issue_analysis)
    
    # Step 2: Fix critical files first
    for priority, files in files_by_priority.items():
        for file_path in files:
            logger.info(f"Fixing {priority} issues in {file_path}")
            
            # Create focused issue report
            issue_report = IssueReport(
                file_path=file_path,
                issues=issue_analysis[file_path],
                context_files=[],  # Only include if absolutely necessary
                max_output_size="7500 tokens"
            )
            
            # Send to Gemini
            response = await send_to_gemini(
                issue_file=issue_report.save(),
                max_tokens=7500  # Leave buffer
            )
            
            if response['success']:
                # Extract and validate
                extracted = await extract_gemini_code(response['output_file'])
                
                # Test before applying
                if await test_fixed_code(extracted['files'][0]):
                    apply_fix(file_path, extracted['files'][0]['content'])
                else:
                    logger.error(f"Fix failed tests for {file_path}")
```

## Cost Optimization

### Batch Related Issues

```python
def batch_similar_issues(all_issues: dict) -> list:
    """Group similar issues across files."""
    batches = []
    
    # Group by issue type
    deprecation_batch = {
        "type": "deprecation_warnings",
        "files": [],
        "common_fix": "logger.bind -> logger.contextualize"
    }
    
    async_batch = {
        "type": "async_await_errors", 
        "files": [],
        "common_fix": "wrap in asyncio.to_thread"
    }
    
    # Create targeted fixes
    for file, issues in all_issues.items():
        for issue in issues:
            if "deprecation" in issue['type']:
                deprecation_batch['files'].append({
                    'path': file,
                    'locations': issue['locations']
                })
    
    return batches
```

### Template-Based Fixes

```python
# For common patterns, use templates
COMMON_FIXES = {
    "logger_bind_deprecation": {
        "pattern": r"logger\.bind\((.*?)\)",
        "template": "with logger.contextualize({params}):",
        "instruction": "Convert logger.bind() to contextualize context manager"
    },
    "await_dict_error": {
        "pattern": r"await self\.db\.collection\([^)]+\)\.(insert|update|delete)\(",
        "template": "await asyncio.to_thread(self.db.collection({collection}).{method},",
        "instruction": "Wrap synchronous DB operations in asyncio.to_thread"
    }
}
```

## Monitoring Token Usage

```python
class TokenMonitor:
    """Monitor and predict token usage."""
    
    def estimate_output_tokens(self, file_size: int, issue_count: int) -> int:
        """Estimate output tokens needed."""
        # Rough estimates
        base_tokens = file_size * 0.25  # ~4 chars per token
        overhead = 500  # Markdown, comments
        fix_expansion = issue_count * 200  # Extra code for fixes
        
        return int(base_tokens + overhead + fix_expansion)
    
    def split_if_needed(self, file_path: str, estimated_tokens: int) -> list:
        """Split file if output would exceed limit."""
        if estimated_tokens > 7000:  # Leave buffer
            return self.split_file_intelligently(file_path)
        return [file_path]
```

## Best Practices

1. **Always estimate output size** before sending to Gemini
2. **Use focused, single-file requests** whenever possible
3. **Include minimal context** - Gemini has 1M input but only 8K output
4. **Test fixes immediately** before applying to detect Gemini errors
5. **Cache common fixes** to avoid repeated API calls
6. **Monitor costs** - multiple calls add up quickly

## Example Cost Calculation

```
Single large file (2000 lines):
- One call: $0.0023
- Split into 3 sections: $0.0069
- Fix 10 files individually: $0.023
- Fix 10 files with batching: ~$0.015
```

The key is balancing thoroughness with token limits and costs.