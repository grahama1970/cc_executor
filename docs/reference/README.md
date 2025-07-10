# Templates Directory - ArXiv MCP Server

## Purpose
This directory contains **copy-and-fill templates** for the ArXiv MCP Server project. Templates are documents with placeholders that you copy and modify for specific tasks.

## 📄 Available Templates

### 1. `PYTHON_SCRIPT_TEMPLATE.md`
**Purpose**: Template for creating new Python scripts  
**Key Feature**: Includes anti-hallucination UUID4 pattern  
**When to Use**: Starting any new .py file in the project  
**Critical**: UUID4 must be at the VERY END of execution  

### 2. `CODE_REVIEW_REQUEST_TEMPLATE.md`
**Purpose**: Template for requesting code review from o3 model  
**When to Use**: After all assessments pass, before deployment  
**Where to Save**: `docs/tasks/reviewer/incoming/code_review_roundN_request.md`  
**Process**: o3 responds in `docs/tasks/executor/incoming/`  

### 3. `PYTHON_CODE_ASSESSMENT_REPORT_TEMPLATE.md`
**Purpose**: Template for documenting script assessment results  
**When to Use**: After running comprehensive assessment  
**Includes**: UUID4 verification, reasonableness assessment, fix history  

### 4. `DOCKER_DEPLOYMENT_TEMPLATE.md`
**Purpose**: Docker configuration template  
**When to Use**: Setting up Docker deployment  
**Includes**: Dockerfile and docker-compose.yml examples  

### 5. `PROMPT_TEMPLATE.md`
**Purpose**: Template for creating new prompts  
**When to Use**: Adding prompt-based functionality  
**Note**: Specific to prompt systems, not general Python scripts  

## 🚀 How to Use Templates

### Step 1: Choose Template
Identify which template matches your task from the list above.

### Step 2: Copy Template
```bash
# Never edit templates directly - always copy first
cp templates/PYTHON_SCRIPT_TEMPLATE.md ~/my_new_script_plan.md
```

### Step 3: Fill Placeholders
Replace all placeholders with your specific information:
- `[placeholder]` → actual value
- `{variable}` → your data
- Example sections → real implementation

### Step 4: Use Filled Template
- For scripts: Implement following the pattern
- For reviews: Place in correct directory
- For reports: Save with assessment results

## ❌ What Does NOT Belong Here

### Guides and Instructions
These belong in `/guides/`:
- How-to documents
- Process explanations  
- Concept clarifications
- Workflow descriptions

### Completed Documents
Once filled, templates become:
- Actual Python files in `src/`
- Review requests in `docs/tasks/`
- Reports in results directories

### Reference Documentation
- API documentation
- Architecture documents
- Design decisions

## 📋 Template Usage Examples

### Using Python Script Template

```python
# After copying PYTHON_SCRIPT_TEMPLATE.md, you implement:

#!/usr/bin/env python3
"""
Search ArXiv papers by keyword.
[Rest of docstring following template...]
"""

if __name__ == "__main__":
    import json
    import uuid
    from datetime import datetime
    from pathlib import Path
    
    # Run actual search functionality
    results = search_arxiv("quantum computing", max_results=5)
    
    # Save output following template pattern
    output_dir = Path("tmp/responses")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"search_response_{timestamp}.json"
    filepath = output_dir / filename
    
    output = {
        "timestamp": datetime.now().isoformat(),
        "script": "search.py",
        "result": results
    }
    
    with open(filepath, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"Results saved to: {filepath}")
    
    # CRITICAL: UUID4 at the VERY END
    execution_id = str(uuid.uuid4())
    print(f"\nExecution verified: {execution_id}")
    
    # Append to JSON
    with open(filepath, 'r+') as f:
        data = json.load(f)
        data['execution_id'] = execution_id
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()
```

### Using Code Review Template

```markdown
# After copying CODE_REVIEW_REQUEST_TEMPLATE.md, you fill in:

# Code Review Request - Round 1

## Pre-conditions Verified
- [x] All 45 Python scripts have UUID4 pattern
- [x] All outputs saved to tmp/responses/
- [x] All outputs assessed as reasonable
- [x] 70 MCP tools tested successfully

## Statistics
- Python scripts: 45 total, 45 with UUID4
- Reasonable outputs: 45/45
- MCP tools: 70 total, 70 pass
- Integration tests: 5/5 pass

[Rest of filled template...]
```

## 🔑 Key Principles

1. **Templates are for copying** - Never edit originals
2. **Follow patterns exactly** - Especially UUID4 placement
3. **Real data only** - No mocks in examples
4. **Clear placeholders** - Easy to identify what to replace

## 📚 Related Documentation

- **For Instructions**: See `/guides/` directory
- **For Process**: Read guides before using templates
- **For Examples**: Check completed implementations in `src/`

## 🚨 Critical Reminders

### Anti-Hallucination Pattern
Every Python script template includes the UUID4 pattern. This MUST be at the END of execution to prevent agent hallucination.

### Directory Discipline
- Templates stay here
- Filled templates go to appropriate locations
- Never mix templates with guides

### Real Execution
Templates assume real data and actual execution. No mock data, no fake results.

## Need Help?

1. **Confused about a template?** → Read the corresponding guide in `/guides/`
2. **Not sure which template?** → Check the main development README
3. **Template missing something?** → The pattern might be in a guide instead

Remember: Templates are what you COPY, guides are what you READ.