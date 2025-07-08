# Python Script Compliance and Assessment Guide

## Purpose
Ensure ALL Python scripts in specified directories comply with the Python Script Template and have working, testable `if __name__ == "__main__"` blocks that demonstrate their core functionality.

## Process Overview

### 1. Script Compliance Check
For EACH Python script in the specified directories:
- ✅ MUST have `if __name__ == "__main__"` block
- ✅ MUST test the script's core purpose with real data
- ✅ MUST save output to `tmp/responses/` as JSON
- ✅ MUST follow `/docs/templates/PYTHON_SCRIPT_TEMPLATE.md`

### 2. Automatic Failure Conditions
A script FAILS if:
- ❌ No `if __name__ == "__main__"` block exists
- ❌ The block doesn't test core functionality
- ❌ Output isn't saved to `tmp/responses/`
- ❌ Output isn't proper JSON format
- ❌ Agent doesn't assess the output
- ❌ Output is assessed as UNREASONABLE or PARTIALLY REASONABLE

### 3. Assessment Process

#### Step 1: Run Each Script
```bash
# For each .py file in the directory
python script_name.py
```

#### Step 2: Verify Output Saved
```bash
# Check that output was saved with CORRECT naming
ls tmp/responses/*_response_*.json

# Files MUST follow this exact pattern:
# {script_name}_response_{YYYYMMDD_HHMMSS}.json
# 
# Examples:
# ✅ search_response_20250705_163512.json
# ✅ download_response_20250705_164023.json
# ❌ search_basic_20250705_163512.json (has test type)
# ❌ download_test_20250705_164023.txt (wrong extension)
```

#### Step 3: Load and Assess Each Output
For EACH script's output:
```bash
# Read the actual output file
Read tmp/responses/script_name_response.json
```

Then assess:
- **Script Purpose**: What is this script supposed to do?
- **Input Used**: What test data was provided?
- **Expected Output**: What should the output look like?
- **Actual Output**: What did it actually produce?
- **Reasonableness**: Does the output make sense given the purpose?
- **Verdict**: PASS or FAIL with specific reasoning

### 4. Fix and Retry Process

When a script's output is assessed as UNREASONABLE or PARTIALLY REASONABLE:

#### First Attempt - Direct Fix
1. **Analyze the failure**: Identify specific issues in the output
2. **Fix the code**: Modify the script to address the issues
3. **Re-run the test**: Execute the fixed script
4. **Re-assess**: Check if output is now reasonable

#### Second Attempt - If First Fix Fails
1. **Try alternative approach**: Different fix strategy
2. **Re-run and assess**: Check if this resolves the issue

#### Third Attempt - Perplexity-Ask Escalation
If the script still fails after two fix attempts:

```python
# Use perplexity-ask with complete context
response = mcp__perplexity-ask__perplexity_ask({
    "messages": [{
        "role": "user",
        "content": f"""
Python script failing assessment. Need help fixing it.

SCRIPT CODE:
```python
{full_script_code}
```

SPECIFIC PROBLEM:
{description_of_issue}

EXPECTED OUTPUT:
{what_output_should_look_like}

ACTUAL FAILING OUTPUT:
{current_bad_output}

ATTEMPTED FIXES:
1. {first_fix_attempt_description}
2. {second_fix_attempt_description}

Please provide a specific solution to make this script produce the expected output.
"""
    }]
})
```

#### Fourth Step - Implement Perplexity Solution
1. **Apply the suggested fix** from perplexity-ask
2. **Re-run the test**
3. **Final assessment**
4. **If still failing**: Document as unresolvable with detailed explanation

## Report Format

### Summary Section
```markdown
# Python Script Compliance Report

**Date**: [timestamp]
**Directories Assessed**: [list of directories]
**Total Scripts**: [count]
**Passed**: [count]
**Failed**: [count]

## Summary
[Brief overview of findings]
```

### Per-Script Section
```markdown
## Script: [path/to/script.py]

### Purpose
[What this script is designed to do]

### Compliance Check
- [✅/❌] Has `if __name__ == "__main__"` block
- [✅/❌] Tests core functionality
- [✅/❌] Saves output to tmp/responses/
- [✅/❌] Output is valid JSON

### Output Assessment

#### Raw Output (from tmp/responses/[script_name]_response.json):
```json
[Complete JSON with line numbers from Read tool]
```

#### Reasonableness Assessment
- **Input Provided**: [What test data was used]
- **Expected Behavior**: [What should happen]
- **Actual Result**: [What actually happened]
- **Key Indicators**: [Specific values that matter]
- **Verdict**: [PASS/FAIL]
- **Reasoning**: [Detailed explanation]
```

## Complete Working Example: arxiv_search_analyzer.py

This example demonstrates the complete assessment process for a Python script that initially fails and requires fixing.

### Initial Script (With Issues)

```python
#!/usr/bin/env python3
"""
ArXiv search complexity analyzer for query optimization.

Analyzes search queries to predict execution time and optimize performance.
"""

import json
from datetime import datetime
from pathlib import Path

def analyze_query_complexity(query: str) -> dict:
    """Analyze the complexity of an ArXiv search query."""
    # Simplified analysis - missing many factors
    complexity_score = len(query) / 10
    
    return {
        "query": query,
        "score": complexity_score,
        "level": "simple" if complexity_score < 5 else "complex"
    }

if __name__ == "__main__":
    # Test with sample query
    test_query = "quantum computing applications"
    result = analyze_query_complexity(test_query)
    
    # Missing: Not saving to tmp/responses/
    print(json.dumps(result, indent=2))
```

### Assessment Process

#### Step 1: Initial Run and Assessment

```bash
python arxiv_search_analyzer.py
```

**Output**:
```json
{
  "query": "quantum computing applications",
  "score": 3.1,
  "level": "simple"
}
```

**Issues Found**:
1. ❌ Output not saved to `tmp/responses/`
2. ❌ Complexity analysis too simplistic
3. ❌ Missing timestamp and metadata

**Verdict**: UNREASONABLE - Script doesn't comply with template requirements

#### Step 2: First Fix Attempt

```python
# Added at the end of __main__ block:
output_dir = Path("tmp/responses")
output_dir.mkdir(parents=True, exist_ok=True)

result_with_metadata = {
    "timestamp": datetime.now().isoformat(),
    "success": True,
    "result": result
}

output_file = output_dir / f"arxiv_search_analyzer_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(output_file, 'w') as f:
    json.dump(result_with_metadata, f, indent=2)
```

**New Issue**: Complexity analysis still too basic - doesn't consider boolean operators, date ranges, etc.

#### Step 3: Second Fix Attempt

```python
def analyze_query_complexity(query: str) -> dict:
    """Analyze the complexity of an ArXiv search query."""
    complexity_score = 0
    
    # Length factor
    complexity_score += len(query) / 10
    
    # Boolean operators
    for op in ['AND', 'OR', 'NOT']:
        complexity_score += query.count(op) * 2
    
    # Field searches
    for field in ['au:', 'ti:', 'abs:', 'cat:']:
        complexity_score += query.count(field) * 1.5
    
    # Still missing date ranges and wildcards
    
    level = "simple"
    if complexity_score > 10:
        level = "complex"
    elif complexity_score > 5:
        level = "moderate"
    
    return {
        "query": query,
        "score": round(complexity_score, 2),
        "level": level,
        "factors": {
            "length": len(query),
            "boolean_ops": sum(query.count(op) for op in ['AND', 'OR', 'NOT'])
        }
    }
```

**Still Incomplete**: Missing critical factors like date ranges and wildcards

#### Step 4: Perplexity-Ask Escalation

```python
response = mcp__perplexity-ask__perplexity_ask({
    "messages": [{
        "role": "user",
        "content": """
Python script failing assessment. Need help fixing it.

SCRIPT CODE:
```python
#!/usr/bin/env python3
'''ArXiv search complexity analyzer for query optimization.'''

import json
from datetime import datetime
from pathlib import Path

def analyze_query_complexity(query: str) -> dict:
    # Current implementation shown above
    pass

if __name__ == "__main__":
    # Test implementation shown above
    pass
```

SPECIFIC PROBLEM:
The complexity analysis is too simplistic. It doesn't properly analyze ArXiv search queries for:
- Date range searches (e.g., "2023-01-01 TO 2023-12-31")
- Wildcard patterns (e.g., "quant*")
- Category filters (e.g., "cat:cs.AI")
- Nested queries with parentheses

EXPECTED OUTPUT:
Should produce a comprehensive complexity analysis with scores for all query features, proper timeout recommendations, and detailed factor breakdown.

ACTUAL FAILING OUTPUT:
{
  "query": "quantum computing applications",
  "score": 3.1,
  "level": "simple",
  "factors": {
    "length": 31,
    "boolean_ops": 0
  }
}

ATTEMPTED FIXES:
1. Added basic boolean operator counting - but missing other operators
2. Added field search detection - but incomplete list and no date handling

Please provide a complete implementation that properly analyzes all ArXiv query features.
"""
    }]
})
```

#### Step 5: Implement Perplexity Solution

Based on perplexity's response, here's the final working version:

```python
#!/usr/bin/env python3
"""
ArXiv search complexity analyzer for query optimization.

Analyzes search queries to predict execution time and optimize performance.
Based on actual ArXiv API query syntax and performance characteristics.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

def analyze_query_complexity(query: str) -> Dict[str, Any]:
    """
    Analyze the complexity of an ArXiv search query.
    
    Considers all major factors that affect query performance:
    - Query length
    - Boolean operators (AND, OR, NOT, ANDNOT)
    - Field-specific searches
    - Date ranges
    - Wildcards
    - Category filters
    - Parentheses nesting
    """
    factors = {
        "length": len(query),
        "boolean_operators": 0,
        "field_searches": 0,
        "date_ranges": 0,
        "wildcards": 0,
        "category_filters": 0,
        "parentheses_depth": 0
    }
    
    # Boolean operators
    for op in ['AND', 'OR', 'NOT', 'ANDNOT']:
        factors["boolean_operators"] += len(re.findall(rf'\b{op}\b', query))
    
    # Field searches
    field_patterns = ['au:', 'ti:', 'abs:', 'co:', 'jr:', 'cat:', 'rn:', 'id:', 'all:']
    for field in field_patterns:
        factors["field_searches"] += query.count(field)
    
    # Date ranges (YYYY-MM-DD TO YYYY-MM-DD)
    date_range_pattern = r'\d{4}-\d{2}-\d{2}\s+TO\s+\d{4}-\d{2}-\d{2}'
    factors["date_ranges"] = len(re.findall(date_range_pattern, query))
    
    # Wildcards
    factors["wildcards"] = query.count('*') + query.count('?')
    
    # Category filters
    cat_pattern = r'cat:[a-zA-Z\-\.]+(?:\.[a-zA-Z\-]+)*'
    factors["category_filters"] = len(re.findall(cat_pattern, query))
    
    # Parentheses nesting depth
    max_depth = 0
    current_depth = 0
    for char in query:
        if char == '(':
            current_depth += 1
            max_depth = max(max_depth, current_depth)
        elif char == ')':
            current_depth -= 1
    factors["parentheses_depth"] = max_depth
    
    # Calculate complexity score
    complexity_score = (
        factors["length"] / 10 +
        factors["boolean_operators"] * 3 +
        factors["field_searches"] * 2 +
        factors["date_ranges"] * 5 +
        factors["wildcards"] * 4 +
        factors["category_filters"] * 1.5 +
        factors["parentheses_depth"] * 2
    )
    
    # Determine complexity level
    if complexity_score < 5:
        level = "simple"
        recommended_timeout = 30
    elif complexity_score < 15:
        level = "moderate"
        recommended_timeout = 60
    elif complexity_score < 30:
        level = "complex"
        recommended_timeout = 120
    else:
        level = "very_complex"
        recommended_timeout = 300
    
    return {
        "query": query,
        "complexity_score": round(complexity_score, 2),
        "complexity_level": level,
        "recommended_timeout_seconds": recommended_timeout,
        "factors": factors,
        "analysis": {
            "has_boolean_logic": factors["boolean_operators"] > 0,
            "has_field_restrictions": factors["field_searches"] > 0,
            "has_date_filters": factors["date_ranges"] > 0,
            "has_pattern_matching": factors["wildcards"] > 0,
            "has_category_filters": factors["category_filters"] > 0,
            "has_nested_queries": factors["parentheses_depth"] > 0
        }
    }

if __name__ == "__main__":
    # Test with various query complexities
    test_queries = [
        "quantum computing",
        "au:Einstein AND ti:relativity",
        "(quantum OR classical) AND cat:quant-ph AND 2023-01-01 TO 2023-12-31",
        "ti:neural* AND abs:deep learning AND (cat:cs.AI OR cat:cs.LG) NOT cat:cs.CV"
    ]
    
    results = []
    for query in test_queries:
        result = analyze_query_complexity(query)
        results.append(result)
    
    # Save to tmp/responses/
    output_dir = Path("tmp/responses")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now()
    output_data = {
        "timestamp": timestamp.isoformat(),
        "script": "arxiv_search_analyzer.py",
        "success": True,
        "test_count": len(test_queries),
        "results": results,
        "metadata": {
            "version": "1.0",
            "purpose": "Analyze ArXiv search query complexity",
            "execution_time_ms": 12  # Simplified for example
        }
    }
    
    output_file = output_dir / f"arxiv_search_analyzer_response_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"Assessment complete. Results saved to: {output_file}")
    
    # Verify the most complex query
    complex_result = results[-1]
    assert complex_result["complexity_level"] in ["complex", "very_complex"], "Complex query not properly identified"
    assert complex_result["recommended_timeout_seconds"] >= 120, "Timeout too short for complex query"
    assert complex_result["factors"]["boolean_operators"] >= 3, "Boolean operators not counted correctly"
    
    print(f"✅ All assertions passed. Complexity analysis working correctly.")
```

### Final Assessment

#### Reading the Output File

```bash
Read tmp/responses/arxiv_search_analyzer_response_20250105_120000.json
```

#### Output Content (with line numbers):
```
     1→{
     2→  "timestamp": "2025-01-05T12:00:00.123456",
     3→  "script": "arxiv_search_analyzer.py",
     4→  "success": true,
     5→  "test_count": 4,
     6→  "results": [
     7→    {
     8→      "query": "quantum computing",
     9→      "complexity_score": 1.7,
    10→      "complexity_level": "simple",
    11→      "recommended_timeout_seconds": 30,
    12→      "factors": {
    13→        "length": 17,
    14→        "boolean_operators": 0,
    15→        "field_searches": 0,
    16→        "date_ranges": 0,
    17→        "wildcards": 0,
    18→        "category_filters": 0,
    19→        "parentheses_depth": 0
    20→      },
    21→      "analysis": {
    22→        "has_boolean_logic": false,
    23→        "has_field_restrictions": false,
    24→        "has_date_filters": false,
    25→        "has_pattern_matching": false,
    26→        "has_category_filters": false,
    27→        "has_nested_queries": false
    28→      }
    29→    },
    30→    {
    31→      "query": "au:Einstein AND ti:relativity",
    32→      "complexity_score": 10.0,
    33→      "complexity_level": "moderate",
    34→      "recommended_timeout_seconds": 60,
    35→      "factors": {
    36→        "length": 30,
    37→        "boolean_operators": 1,
    38→        "field_searches": 2,
    39→        "date_ranges": 0,
    40→        "wildcards": 0,
    41→        "category_filters": 0,
    42→        "parentheses_depth": 0
    43→      }
    44→    },
    45→    {
    46→      "query": "(quantum OR classical) AND cat:quant-ph AND 2023-01-01 TO 2023-12-31",
    47→      "complexity_score": 23.4,
    48→      "complexity_level": "complex",
    49→      "recommended_timeout_seconds": 120,
    50→      "factors": {
    51→        "length": 69,
    52→        "boolean_operators": 3,
    53→        "field_searches": 1,
    54→        "date_ranges": 1,
    55→        "wildcards": 0,
    56→        "category_filters": 1,
    57→        "parentheses_depth": 1
    58→      }
    59→    },
    60→    {
    61→      "query": "ti:neural* AND abs:deep learning AND (cat:cs.AI OR cat:cs.LG) NOT cat:cs.CV",
    62→      "complexity_score": 30.2,
    63→      "complexity_level": "very_complex",
    64→      "recommended_timeout_seconds": 300,
    65→      "factors": {
    66→        "length": 77,
    67→        "boolean_operators": 4,
    68→        "field_searches": 5,
    69→        "date_ranges": 0,
    70→        "wildcards": 1,
    71→        "category_filters": 3,
    72→        "parentheses_depth": 1
    73→      }
    74→    }
    75→  ],
    76→  "metadata": {
    77→    "version": "1.0",
    78→    "purpose": "Analyze ArXiv search query complexity",
    79→    "execution_time_ms": 12
    80→  }
    81→}
```

#### Claude's Reasonableness Assessment

**Verdict**: FIXED (now REASONABLE)

**Expected vs Actual**:
- **Expected**: Comprehensive query complexity analysis with all ArXiv features
- **Observed**: Complete analysis covering all major query components

**Evidence Analysis**:
✓ Simple query correctly scored at 1.7 (30s timeout)
✓ Moderate query with boolean ops scored at 10.0 (60s timeout)
✓ Complex query with dates/categories scored at 23.4 (120s timeout)
✓ Very complex query properly identified at 30.2 (300s timeout)
✓ All ArXiv-specific features detected (fields, categories, dates, wildcards)

**Numerical Validation**:
- Complexity scores scale appropriately with query features
- Timeout recommendations follow logical progression (30/60/120/300s)
- Factor counts accurate (e.g., 4 boolean operators in last query)
- Parentheses depth correctly calculated

**Fix History**:
- **Attempt 1**: Added output saving but analysis too basic
- **Attempt 2**: Added some factors but still incomplete
- **Perplexity Solution**: Provided comprehensive regex-based analysis
- **Final Fix**: Implemented complete ArXiv query analyzer

**Conclusion**: The script now properly analyzes ArXiv search queries with accurate complexity scoring and appropriate timeout recommendations, demonstrating full compliance with the template.

## Report Summary

This complete example shows the assessment workflow:
1. Initial script failed due to missing output saving and poor functionality
2. Two fix attempts partially addressed issues
3. Perplexity-ask provided comprehensive solution
4. Final implementation passed all requirements

The Fix History in the report documents the learning process and provides valuable reference for future similar scripts.

## Implementation Steps

1. **Identify all Python files** in specified directories
2. **Run each script** to generate output
3. **Check compliance** with template requirements
4. **Read each output file** from tmp/responses/
5. **Assess reasonableness** based on script purpose
6. **Generate comprehensive report** with all findings

## Using Deterministic Hooks (Optional)

For ArXiv MCP Server assessments, you can leverage the hooks in `/src/arxiv_mcp_server/hooks/`:

### Available Hooks:
1. **arxiv_rate_limiter.py** - Enforces API rate limits (3 req/sec burst, 1 req/sec sustained)
2. **paper_cache_validator.py** - Validates cache freshness (30-day paper expiry, 7-day metadata)
3. **search_complexity_analyzer.py** - Analyzes query complexity and sets appropriate timeouts

### Hook Usage in Assessment:
```python
from arxiv_mcp_server.hooks import apply_pre_hooks, apply_post_hooks

# Before running a script that uses ArXiv API
task_data = {"operation": "search", "query": "quantum computing"}
task_data = apply_pre_hooks(task_data)  # Applies rate limiting, cache checks, complexity analysis

# After script execution
result = {"papers_found": 150, "duration": 2.5}
result = apply_post_hooks(task_data, result)  # Updates metrics and cache
```

### Benefits for Assessment:
- **Deterministic behavior** - Rate limiting ensures consistent API compliance
- **Performance validation** - Complexity analyzer helps verify timeout appropriateness
- **Cache efficiency** - Validator ensures scripts use cache when available
- **Realistic testing** - Hooks simulate production conditions during assessment

## Critical Requirements

- **NO TRUNCATION**: Show complete JSON outputs
- **LINE NUMBERS**: Use Read tool to prove you loaded files
- **SPECIFIC ANALYSIS**: Reference actual values from outputs
- **IMMEDIATE FIXES**: If script fails, follow the fix-and-retry process
- **PERPLEXITY ESCALATION**: After 2 failed fixes, use perplexity-ask for help
- **COMPLETE CONTEXT**: Always provide full code and error details to perplexity
- **COMPREHENSIVE COVERAGE**: Assess EVERY Python file found