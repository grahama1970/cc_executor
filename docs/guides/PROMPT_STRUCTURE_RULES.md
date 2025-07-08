# MANDATORY PROMPT STRUCTURE RULES

## 🚨 CRITICAL: All Prompts MUST Follow This EXACT Structure

### Why Structure Matters
- **Consistency** enables the gamification system to work
- **Automation** requires predictable patterns for metrics updates
- **Graduation** depends on standardized format
- **Verification** needs uniform marker patterns
- **Decomposition** breaks complex prompts into single-focus tasks

## Required Sections (IN THIS ORDER)

### 1. Title
```markdown
# [Module Name] Runtime Generation
```

### 2. Gamification Rules Block
```markdown
## 🎮 GAMIFICATION RULES

### Current Score
- **Success**: 0
- **Failure**: 0
- **Total Executions**: 0
- **Last Updated**: YYYY-MM-DD
- **Success Ratio**: N/A (need to reach 10:1)
```
**CRITICAL**: These fields MUST use this exact format for regex parsing

### 3. Execution Tracking
Standard warnings about hallucination and verification requirements

### 4. Purpose Section
Clear, concise description of module functionality

### 5. Parameters Section
Document all expected parameters with types

### 6. Code Example Section
MUST include these mandatory functions:
- `update_metrics(success, markdown_file)` - Updates the markdown file
- `test_main_functionality()` - Tests core features
- `test_failure_recovery()` - Tests error scenarios
- `if __name__ == "__main__":` block with standard structure

### 7. How to Execute Section
Standard sed extraction command

### 8. Expected Output Section
Example of successful execution output

### 9. Graduation Criteria Section
Path where module will be placed after 10:1 ratio

## CRITICAL: Task Decomposition Rules

### Multi-Task Detection
Complex prompts often contain multiple implied tasks that MUST be decomposed:

**❌ BAD - Multiple Tasks in One Prompt:**
```
"Create a Python web scraper that fetches news articles, stores them in a database, and generates a daily summary report"
```

**✅ GOOD - Decomposed into Single Tasks:**
```
Task 1: "What is a Python web scraper that fetches news articles?"
Task 2: "What is a database schema for storing news articles?"
Task 3: "What is Python code to save articles to a database?"
Task 4: "What is a Python script that generates summary reports from articles?"
```

### Decomposition Triggers
Automatically decompose when prompt contains:
- Multiple verbs: "create AND store AND generate"
- Sequential steps: "first..., then..., finally..."
- Multiple outputs: "scraper, database, and report"
- Complex requirements: more than 2 distinct features

### Decomposition Algorithm
```python
def decompose_task(prompt):
    """Break complex prompts into atomic tasks"""
    indicators = {
        'conjunctions': ['and', 'then', 'also', 'plus', 'with'],
        'sequences': ['first', 'second', 'next', 'finally'],
        'multiples': ['both', 'all', 'each', 'every']
    }
    
    # Count complexity indicators
    complexity = 0
    for category, words in indicators.items():
        for word in words:
            complexity += prompt.lower().count(word)
    
    # If complexity > 2, decompose
    if complexity > 2:
        return split_into_atomic_tasks(prompt)
    return [prompt]  # Already atomic
```

### Task Atomicity Rules
Each decomposed task MUST:
1. Have a single clear objective
2. Produce one type of output
3. Be testable independently
4. Complete in under 60 seconds
5. Not depend on other task outputs

## Mandatory Code Components

### 1. Metrics Update Function
```python
def update_metrics(success, markdown_file):
    """Update success/failure metrics in the markdown file after execution"""
    # MUST use regex to find and update:
    # - Success**: \d+
    # - Failure**: \d+
    # - Total Executions**: \d+
    # - Last Updated**: YYYY-MM-DD
    # - Success Ratio**: [ratio]
```

### 2. Test Marker Generation
```python
test_marker = f"MODULE_NAME_TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
```

### 3. Transcript Verification
```python
print(f"rg '{test_marker}' ~/.claude/projects/{project_dir}/*.jsonl | jq -r '.content'")
```

### 4. Main Test Structure
```python
if __name__ == "__main__":
    # 1. Find markdown file
    # 2. Generate test marker
    # 3. Print header
    # 4. Run main tests
    # 5. Run recovery tests
    # 6. Update metrics
    # 7. Print hallucination warning
```

## Validation Checklist

Before committing any prompt, verify:
- [ ] Uses exact gamification header format
- [ ] Has update_metrics() function
- [ ] Has test_main_functionality() function
- [ ] Has test_failure_recovery() function
- [ ] Generates unique test markers
- [ ] Prints transcript verification commands
- [ ] Updates metrics after EVERY execution
- [ ] Has hallucination warning at the end
- [ ] Recovery tests handle at least 3 failure scenarios
- [ ] All regex patterns match the standard format

## Common Mistakes to Avoid

1. **Different metric field names** - Use EXACT field names
2. **Missing Total Executions** - This field is REQUIRED
3. **Not updating metrics** - MUST call update_metrics()
4. **Hardcoded paths** - Use dynamic path finding
5. **Missing recovery tests** - At least 3 scenarios required
6. **Non-standard markers** - Use MODULE_NAME_TEST_ format

## Enforcement

Any prompt that doesn't follow this structure:
- Will not track metrics correctly
- Cannot graduate to Python files
- Will break the gamification system
- Must be immediately fixed

Use PROMPT_TEMPLATE.md as the base for ALL new prompts!