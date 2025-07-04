# Task List Template Guide for Flexible Prompt-Driven Execution

## Overview

This guide provides templates and best practices for creating flexible task lists where the orchestrator (Claude) intelligently decides how to execute each task - whether directly, through cc_execute.md, or via other methods.

**Version**: 2.1 (Enhanced with cc_execute.md learnings)
**Last Updated**: 2025-01-04

## ⚠️ MANDATORY PRE-EXECUTION VALIDATION

### Automatic Pre-Flight Check
The `pre-task-list` hook automatically evaluates your task list and may BLOCK execution if:
- Overall success rate predicted < 10%
- 3+ tasks have critical failure risk (>80%)
- Total execution time exceeds 1 hour
- Sequential high-risk tasks detected

### Pre-Flight Assessment Example
```
📊 SUMMARY
Total Tasks: 7
Average Complexity: 2.8/5.0
Predicted Success Rate: 42.3%
Overall Risk: HIGH
Should Proceed: ❌ NO

🚫 BLOCKING ISSUES
- 3 tasks have critical failure risk
- Overall success rate too low: 42.3%

⚠️ HIGH RISK TASKS: [3, 4, 5]
```

### Manual Validation Steps
Before executing ANY task:
1. Read @docs/CLAUDE_CODE_PROMPT_RULES.md
2. Validate task against all rules
3. Auto-fix violations if possible
4. Document any manual fixes needed
5. NEVER execute a task that violates prompt rules

## Core Concepts

### Flexible Execution Patterns

The orchestrator can choose from multiple execution strategies:

1. **Direct Execution**: Simple tasks the orchestrator handles directly
2. **cc_execute.md**: Complex tasks requiring separate Claude instance via WebSocket
3. **Tool Usage**: Tasks using Read, Write, Bash tools directly
4. **Hybrid Approach**: Combining multiple strategies as needed

### When to Use cc_execute.md

The orchestrator should use cc_execute.md for:
- Tasks requiring isolation (separate Claude instance)
- Long-running operations that might hit token limits (>2000 tokens expected)
- Tasks needing specialized prompting or retry logic
- When bidirectional communication is beneficial
- Novel tasks with no Redis history (conservative timeout needed)

**Quantified Heuristics:**
- Estimated runtime > 60 seconds → Use cc_execute.md
- Expected output > 1000 lines → Use cc_execute.md
- Retry logic needed → Use cc_execute.md
- Task similarity score < 2.0 in Redis → Use cc_execute.md

**NEW LEARNING (2025-01-04)**: cc_execute.md Usage & Architecture Decision
- Import pattern: `from src.cc_executor.prompts.cc_execute_utils import execute_task_via_websocket`
- Always use absolute paths in tasks (e.g., `tests/apps/data_pipeline/file.csv`)
- WebSocket server must be running (`cc-executor serve`)
- Timeouts may need adjustment - start with 120s for analytical tasks
- Direct execution often sufficient for simple file operations
- **MCP EVALUATION**: After testing, prompt-based cc_execute.md remains superior to MCP wrapper
  - Prompt approach: 10:1 success ratio, simple, proven
  - MCP approach: Added complexity without solving real problems
  - Decision: Continue using prompts for orchestration flexibility

### When to Execute Directly

The orchestrator should handle directly:
- Simple file operations (Read, Write) < 100 lines
- Quick calculations or transformations < 30 seconds
- Tasks that build on previous context
- Operations that don't need isolation
- Well-known patterns with Redis history

## Task List Structure

### Flexible Task Template with Validation

```markdown
# [Task List Name]

## Overview
[Brief description of what this task list accomplishes]

## Pre-Execution Validation
Before executing ANY task, validate against @docs/CLAUDE_CODE_PROMPT_RULES.md:
1. Check all tasks are in question format
2. Verify no problematic patterns (commands, excessive length)
3. Ensure proper flags for programmatic execution
4. Check system load and adjust timeouts

## Execution Guidelines
You (the orchestrator) should:
1. First validate all tasks against prompt rules
2. Decide execution method based on complexity
3. Apply question format conversion if using cc_execute.md
4. Monitor for rule violations during execution

---

## Task N: [Brief Title]

[Task description - MUST be validated before execution]

Success Criteria:
- [What constitutes successful completion]
- [Specific checks to verify]

Prompt Rules Check:
- [ ] Question format or convertible to question
- [ ] No excessive length (>1000 words)
- [ ] Single-focus (not multi-step)
- [ ] No interactive patterns

Execution Hints:
- [Optional: Suggestions for how to approach this task]
- [Optional: When to use cc_execute.md vs direct execution]
```

### Complete Example with Validation

```markdown
# Web Application Setup Task List

## Overview
Set up a basic web application with configuration, database, and API endpoints.

## IMPORTANT: Pre-Execution Validation Required
You MUST read @docs/CLAUDE_CODE_PROMPT_RULES.md and validate all tasks before execution.
Pay special attention to:
- Question format requirement
- Timeout guidelines (minimum 120s for startup overhead)
- System load multipliers
- Required flags for programmatic execution

## Execution Guidelines
1. First validate all tasks against prompt rules
2. Convert any commands to question format
3. For each task, assess and decide:
   - Simple file operations: Execute directly with Read/Write tools
   - Complex code generation: Consider using cc_execute.md for isolation
   - System checks: Use Bash tool directly
   - Multi-step operations: May benefit from cc_execute.md's retry logic
4. When using cc_execute.md, ALWAYS include:
   ```bash
   --output-format stream-json --dangerously-skip-permissions --allowedTools [appropriate tools]
   ```

---

## Task 1: Check Python Environment

Verify Python 3.10+ is installed and accessible.

Success Criteria:
- Python version is 3.10 or higher
- pip/uv is available
- Virtual environment can be created

Execution Hints:
- This is a simple check - execute directly with Bash tool
- No need for cc_execute.md overhead

## Task 2: Create Project Structure

Set up the following directory structure:
```
web_app/
├── app/
│   ├── __init__.py
│   ├── routes.py
│   └── models.py
├── tests/
├── config.py
└── requirements.txt
```

Success Criteria:
- All directories exist
- All files are created with appropriate boilerplate
- Structure matches specification

Execution Hints:
- For simple directory/file creation, use direct execution
- If generating complex boilerplate, consider cc_execute.md

## Task 3: Generate Flask Application

Create a Flask application with:
- Basic routing (/, /health, /api/status)
- Error handling
- Logging configuration
- Database connection setup

Success Criteria:
- app/routes.py contains all endpoints
- Error handlers are defined
- Logging is configured
- Can run with `python -m app`

Execution Hints:
- This is complex enough to benefit from cc_execute.md
- Use: ./src/cc_executor/prompts/cc_execute.md with appropriate timeout
- Retry strategy: Break into smaller components if it fails

## Task 4: Verify Application Runs

Start the Flask application and verify all endpoints respond correctly.

Success Criteria:
- Application starts without errors
- /health returns {"status": "ok"}
- /api/status returns valid JSON
- Logs are being written

Execution Hints:
- Direct execution with Bash tool
- May need to handle background process
```

### Self-Improving Task List Template

```markdown
# Data Processing Pipeline — Self-Improving Task List

## 📊 TASK LIST METRICS & HISTORY
- **Success/Failure Ratio**: 3:2 (Target: 10:1)
- **Last Updated**: 2025-07-01
- **Evolution History**:
  | Version | Change & Reason | Result |
  |---------|-----------------|--------|
  | v1 | Initial task list | 1:2 (mostly timeouts) |
  | v2 | Converted to questions | 2:1 (better) |
  | v3 | Added explicit instructions | 3:0 (improving) |

## 🏛️ CORE PURPOSE (Immutable)
Process CSV data through multiple transformation stages with quality validation.

## ⚠️ MANDATORY VALIDATION
You MUST validate all tasks against @docs/CLAUDE_CODE_PROMPT_RULES.md before execution.
Current validation status: ✅ All tasks compliant as of v3

## 🤖 TASK DEFINITIONS (Evolves with Learning)

### Task 1: Analyze Input Data
- **Current Definition** (v3): "What information can be extracted from data.csv? Report the number of rows, columns, column names with types, and any data quality issues found."
- **Success Rate**: 3/3 ✅
- **Evolution**:
  - v1: "Analyze data.csv" → Failed (too vague)
  - v2: "What is in data.csv?" → Failed (ambiguous)
  - v3: Current → Success!
- **Execution Hints**: Direct execution unless file >100MB

### Task 2: Clean and Transform Data  
- **Current Definition** (v3): "What is a Python script that cleans data.csv? Remove duplicates, handle missing values by documenting the strategy used, standardize dates to ISO format, and save as cleaned_data.csv."
- **Success Rate**: 2/3
- **Common Failures**: 
  - v2: Token limit exceeded on large file
- **Improvements Applied**:
  - v3: Added file size check, use cc_execute.md for >50MB
- **Execution Hints**: Check file size first, use cc_execute.md if large

### Task 3: Generate Summary Report
- **Current Definition** (v3): "What is a summary report for the cleaned data? Include statistical summary of numeric columns, data quality metrics, and 3 key insights. Format as markdown and save as report.md."
- **Success Rate**: 3/3 ✅
- **Evolution**:
  - v1: "Generate report" → Failed (command format)
  - v2: "Create a summary" → Failed (not a question)
  - v3: Current → Success!

## 📝 EXECUTION LOG

### Run 4: 2025-07-01
- **System Load**: 4.2 (normal)
- **Task 1**: ✅ Success (45s, direct execution)
- **Task 2**: ✅ Success (89s, cc_execute.md due to 75MB file)
- **Task 3**: ✅ Success (62s, direct execution)
- **Overall**: 3:0 ✅

**Key Learning**: File size threshold working well for execution decision

## 🔄 IMPROVEMENT RULES

1. After ANY failure:
   - Check CLAUDE_CODE_PROMPT_RULES.md compliance

## 🚀 Advanced Task List Patterns

### Understanding cc_execute.md Purpose
**IMPORTANT**: cc_execute.md is ONLY valuable in task list contexts for sequential execution. For single commands, use Claude Code directly.

The value proposition:
- **Task Lists**: Use cc_execute.md to spawn fresh Claude instances per task
- **Single Tasks**: Just use Claude Code directly (no orchestration needed)

### Sequential Task List Example (Primary Use Case)
```python
# This is where cc_execute.md shines - orchestrating multiple sequential tasks
task_list = [
    "Task 1: Create data model for blog system",
    "Task 2: Using the model from Task 1, build REST API",  
    "Task 3: Using the API from Task 2, write integration tests",
    "Task 4: Using all previous work, generate API documentation"
]

# Each task gets fresh 200K context but can read previous outputs
for task in task_list:
    result = execute_task_via_websocket(task)
    if not result["success"]:
        break  # Dependencies require sequential success
```

### When to Use cc_execute.md in Task Lists

✅ **USE cc_execute.md when**:
- Executing tasks that depend on previous task outputs
- Tasks that generate lots of output (would pollute context)
- Complex multi-file operations needing fresh context
- Tasks requiring different tool sets or permissions

❌ **DON'T use cc_execute.md for**:
- Single standalone tasks (just use Claude directly)
- Simple file reads or calculations
- Tasks that need shared in-memory state

### Advanced Pattern: Research → Build → Review Pipeline
```markdown
## Task List: Implement Caching Layer

### Task 1: Research Current Best Practices
**Method**: Direct execution with perplexity-ask
**Why not cc_execute**: Simple MCP tool call, minimal output

### Task 2: Implement Caching Based on Research  
**Method**: cc_execute.md
**Why**: Complex implementation, needs fresh 200K context
```bash
cc_execute.md: "Using the research from Task 1 (in research.md), implement a Redis caching layer with TTL, invalidation, and monitoring"
```

### Task 3: Review Implementation
**Method**: cc_execute.md with LiteLLM
**Why**: Needs to read all code from Task 2 with fresh perspective
```bash
cc_execute.md: "Review the caching implementation in cache/ directory and use ./prompts/ask-litellm.md to analyze for performance"
```
```

### The Orchestration Pattern
The main Claude (orchestrator) manages the workflow but doesn't execute complex tasks:

```
ORCHESTRATOR (You)           WORKER CLAUDES (via cc_execute.md)
    │                                    │
    ├─ Manages task sequence            ├─ Fresh 200K context each
    ├─ Tracks progress                  ├─ Focused on single task
    ├─ Handles errors                   ├─ No knowledge of other tasks
    └─ Coordinates results              └─ Clean execution environment
```
   - Log specific error (timeout/token/ambiguity)
   - Apply targeted improvement
   - Re-validate before next run

2. Improvement Priority:
   - Question format violations → Immediate fix
   - Timeouts → Add explicitness + increase timeout
   - Token limits → Use cc_execute.md or split task
   - Ambiguity → Add context and examples

3. Do NOT change successful task definitions unless:
   - New failure pattern emerges
   - Performance can be significantly improved
   - Validation rules change

---

## Task 1: Analyze Input Data

Examine data.csv and report:
- Number of rows and columns
- Column names and types
- Any obvious data quality issues

Success Criteria:
- Accurate count of rows/columns
- All column names listed
- Data types identified

Note: You decide if this needs cc_execute.md based on file size

## Task 2: Clean and Transform Data

Apply the following transformations:
- Remove duplicate rows
- Handle missing values (document strategy used)
- Standardize date formats
- Create derived columns as needed

Success Criteria:
- No duplicate rows remain
- Missing value strategy is documented
- All dates in ISO format
- Transformation logic is clear

Note: For large files or complex transformations, cc_execute.md may help manage memory and provide better error recovery

## Task 3: Generate Summary Report

Create a report including:
- Statistical summary of numeric columns
- Data quality metrics
- Visualization of key relationships
- Recommendations for further analysis

Success Criteria:
- Report is comprehensive
- Statistics are accurate
- Visualizations are meaningful
- Recommendations are actionable

Note: This creative task might benefit from cc_execute.md's structured approach
```

## Critical Rules for Task Design

### 0. ALWAYS Validate Against CLAUDE_CODE_PROMPT_RULES.md

**The orchestrator MUST check @docs/CLAUDE_CODE_PROMPT_RULES.md before executing ANY task.**

```markdown
## Task Validation Required
Before executing this task list:
1. Read @docs/CLAUDE_CODE_PROMPT_RULES.md
2. Validate each task against the rules
3. Convert commands to questions if needed
4. Check for problematic patterns
5. Ensure proper flags for cc_execute.md usage
```

**Key Rules to Enforce:**
- ✅ Question format ("What is...?") prevents hangs
- ✅ Include `--output-format stream-json` for programmatic use
- ✅ Avoid excessive length requests (>1000 words)
- ✅ No multi-step prompts in single task
- ✅ Check system load and multiply timeouts if >14

### 1. Let the Orchestrator Decide

The task list should describe WHAT needs to be done, not HOW to do it:

**❌ OVERLY PRESCRIPTIVE:**
```markdown
Task 1: Use cc_execute.md to create a file...
Task 2: Directly execute with Bash tool...
Task 3: Must use WebSocket approach...
```

**✅ FLEXIBLE:**
```markdown
Task 1: Create a configuration file with database settings
Task 2: Verify the application can connect to the database
Task 3: Generate a comprehensive test suite

(Let the orchestrator choose the best execution method)
```

### 2. Question Format for cc_execute.md

**CRITICAL**: Claude instances spawned via cc_execute.md are LESS resilient to prompt ambiguity than the orchestrator. This unexplained phenomenon means strict adherence to prompt rules is ESSENTIAL.

When the orchestrator decides to use cc_execute.md, it MUST:

1. **Convert to question format**
2. **Add required flags**
3. **Be MORE explicit than usual**
4. **Validate extra carefully**

**Original Task:**
```markdown
Task: Create a factorial function with error handling
```

**Orchestrator converts to (with extra clarity for spawned instance):**
```markdown
Use cc_execute.md to execute:
- Task: What is a Python function that calculates factorial with error handling? Please show the complete code.
- Command flags: --output-format stream-json --dangerously-skip-permissions --allowedTools Write,Read
- Extra clarity: Include the function definition, error handling for negative numbers, and a usage example
- Validation: ✓ Question format, ✓ Single focus, ✓ Explicit request
```

**Why spawned instances need extra care:**
- Less context about the overall task
- More prone to timeout on ambiguous prompts
- Stricter interpretation of commands vs questions
- Higher failure rate without explicit instructions

### 3. Provide Clear Context and Constraints

**❌ VAGUE:**
```markdown
Task: Handle errors in the application
```

**✅ SPECIFIC:**
```markdown
Task: Add error handling to the divide function that:
- Catches division by zero
- Logs errors with timestamp
- Returns None for invalid operations
- Includes type checking for inputs
```

### 4. Execution Hints vs Requirements

**Hints** (optional guidance):
```markdown
Execution Hints:
- Consider using cc_execute.md if generating complex code
- Redis timeout estimation might be helpful here
- Previous similar tasks took ~45 seconds
```

**Requirements** (must be met):
```markdown
Success Criteria:
- Function handles all specified error cases
- Logs include timestamp and error type
- All tests pass
```

## Pre-Execution Validation

### Task List Self-Check Against CLAUDE_CODE_PROMPT_RULES.md

Before ANY task execution, the orchestrator MUST validate tasks against the rules:

```python
def validate_task_against_rules(task):
    """Validate task complies with CLAUDE_CODE_PROMPT_RULES.md"""
    errors = []
    
    # Rule 1: Question format check
    if not (task.endswith("?") or starts_with_interrogative(task)):
        errors.append("NOT A QUESTION: Commands will hang. Rephrase as 'What is...?'")
    
    # Rule 2: Avoid problematic patterns
    problematic = ["Write a", "Create a", "Generate", "Build", "Make"]
    if any(task.startswith(p) for p in problematic):
        errors.append("COMMAND FORMAT: Will likely timeout. Use question format.")
    
    # Rule 3: Length checks
    if "5000 word" in task or "10000 word" in task:
        errors.append("EXCESSIVE LENGTH: Will overflow buffers. Max 1000 words.")
    
    # Rule 4: Multi-step detection
    if all(step in task for step in ["First", "then", "finally"]):
        errors.append("MULTI-STEP: Break into separate tasks.")
    
    # Rule 5: Check for required flags if using cc_execute
    # --output-format stream-json MUST be included
    
    return errors
```

### Pre-Flight Checklist

```markdown
Before executing ANY task list:

□ All tasks in question format ("What is...?")
□ No commands starting with action verbs
□ Reasonable output length (<1000 words)
□ Single-focus tasks (not multi-step)
□ Appropriate timeouts based on complexity
□ cc_execute.md tasks include --output-format stream-json
□ System load checked (if >14, expect 3x delays)
□ No interactive prompts ("Ask me about...")
□ No vague continuations ("etc...", "and so on")
```

## Two-Stage Evaluation System

### Stage 1: Internal Evaluation (cc_execute)

Before execution, cc_execute performs these checks:

| Check | Description | Action on Failure |
|-------|-------------|-------------------|
| Question Format | Input ends with "?" or starts with interrogative | Convert or fail with clear error |
| Syntax Validity | Well-formed request structure | Fail fast |
| Resource Estimate | CPU/memory/time within bounds | Warn or adjust timeout |
| Security Check | No unsafe operations requested | Block execution |
| Deduplication | Not a recent duplicate | Use cached result if available |
| **Prompt Rules** | Validates against CLAUDE_CODE_PROMPT_RULES.md | Fail with specific rule violation |

### Stage 2: External Evaluation (Orchestrator)

After execution, the orchestrator verifies:

| Pattern | Check | Pass Criteria |
|---------|-------|---------------|
| Output Conformance | Matches expected format | Schema validation passes |
| Completeness | All subtasks done | 100% completion or documented partial |
| Performance | Within time/resource limits | < timeout, < memory limit |
| Error Status | No critical errors | Exit code 0, no exceptions |
| Content Validation | Contains required elements | All success criteria met |

### Handling Partial Success

```markdown
{
  "task_id": "task_4_generate_api",
  "status": "partial_success",
  "completed": ["routes_created", "error_handlers_added"],
  "failed": ["database_connection"],
  "retry_strategy": "Fix connection string and retry failed step only"
}
```

### Retry Decision Logic

```python
def should_retry(result):
    # Retryable errors
    if result['error_code'] in ['timeout', 'rate_limit', 'token_limit']:
        return True, "exponential_backoff"
    
    # Partial success - retry failed parts
    if result['status'] == 'partial_success':
        return True, "failed_steps_only"
    
    # Non-retryable errors
    if result['error_code'] in ['invalid_syntax', 'permission_denied']:
        return False, "fail_fast"
    
    return False, "unknown_error"
```

## Success Criteria Patterns

### File Creation Tasks

```markdown
Success Criteria:
  1. File [filename] exists in current directory
  2. Contains [specific content or pattern]
  3. [Additional content verification]
  
Evaluation:
  - Stage 1: Validate filename and content structure
  - Stage 2: Verify file exists and content matches
```

### Command Execution Tasks

```markdown
Success Criteria:
  1. Output contains [expected text]
  2. No [error type] errors
  3. Exit code is 0

Evaluation:
  - Stage 1: Check command safety and format
  - Stage 2: Validate output and exit status
```

### Code Verification Tasks

```markdown
Success Criteria:
  1. Function/class [name] is defined
  2. Handles [specific case] correctly
  3. Returns [expected result] for test input

Evaluation:
  - Stage 1: Syntax check and import validation
  - Stage 2: Run tests and verify behavior
```

## Retry Strategy Patterns

### For Missing Files
```markdown
- Retry Strategy: Add explicit instructions to use Write tool and create the file
```

### For Import Errors
```markdown
- Retry Strategy: First verify required files exist with ls -la, then check PYTHONPATH
```

### For Execution Errors
```markdown
- Retry Strategy: Show step-by-step execution with error handling
```

### For Missing Content
```markdown
- Retry Strategy: Provide explicit template with required sections marked
```

## Timeout Guidelines

### Fixed Timeouts
- **Simple file creation**: 30-45 seconds
- **Code execution**: 30-60 seconds
- **Complex generation**: 60-120 seconds
- **Multi-step tasks**: 120-180 seconds

### Redis Estimation
Use for tasks where complexity varies:
```markdown
- Timeout: Redis estimate
```

This lets the WebSocket handler query Redis for similar historical tasks.

## Advanced Patterns

### Multi-Step Tasks

```markdown
## Task N: Build and Test Module

Use your ./src/cc_executor/prompts/cc_execute.md to execute:
- Task: What is a Python module with both implementation and tests? Create calculator.py with add/subtract functions and test_calculator.py with pytest tests.
- Timeout: 90 seconds
- Success Criteria:
  1. File calculator.py exists with add() and subtract() functions
  2. File test_calculator.py exists with at least 2 tests
  3. Running pytest test_calculator.py shows all tests pass
- Retry Strategy: First create calculator.py, then create tests that import it
```

### Conditional Tasks

```markdown
## Task N: Setup or Verify Environment

Use your ./src/cc_executor/prompts/cc_execute.md to execute:
- Task: How do I check if Redis is installed? Run redis-cli --version and if not found, show installation instructions.
- Timeout: 45 seconds
- Success Criteria:
  1. Either shows Redis version
  2. OR provides installation command for current OS
  3. No unhandled exceptions
- Retry Strategy: Use which redis-cli first, then try common installation paths
```

### Error Recovery Tasks

```markdown
## Task N: Safe Database Operation

Use your ./src/cc_executor/prompts/cc_execute.md to execute:
- Task: What is a Python script that safely connects to a database? Create db_connect.py that handles connection errors gracefully.
- Timeout: 60 seconds
- Success Criteria:
  1. File db_connect.py exists
  2. Contains try/except for connection errors
  3. Returns None or empty result on failure (not exception)
- Retry Strategy: Show example with sqlite3 and proper exception handling
```

## Orchestrator Decision Patterns

### Decision Tree for Execution Method

```
For each task:
├── Is it a simple file operation?
│   └── Yes → Use Read/Write tools directly
├── Does it require isolation/fresh context?
│   └── Yes → Use cc_execute.md
├── Might it exceed token limits?
│   └── Yes → Use cc_execute.md with streaming
├── Does it need complex retry logic?
│   └── Yes → Use cc_execute.md with retry strategy
├── Is it a quick check or calculation?
│   └── Yes → Execute directly
└── Default → Assess based on complexity
```

### Example: Orchestrator Making Decisions

```markdown
# Task List: API Development

## Task 1: Check if Flask is installed

Orchestrator thinks: "Simple check, I'll use Bash directly"
→ Executes: `pip list | grep -i flask`

## Task 2: Generate a REST API with 10 endpoints

Orchestrator thinks: "Complex generation, might hit token limits"
→ Uses cc_execute.md: "What is a Flask REST API with these 10 endpoints...?"

## Task 3: Create a .env file with API_KEY=test123

Orchestrator thinks: "Simple file creation"
→ Uses Write tool directly

## Task 4: Run the API and test all endpoints

Orchestrator thinks: "Multi-step process, needs isolation"
→ Uses cc_execute.md with comprehensive test criteria
```

## Connection Management Patterns

### WebSocket Handler Best Practices

For tasks executed through cc_execute.md:

```python
# Resource cleanup pattern
async def execute_with_cleanup(task):
    proc = None
    try:
        proc = await spawn_claude_process(task)
        result = await proc.communicate()
        return result
    finally:
        if proc and proc.returncode is None:
            proc.kill()
            await proc.wait()  # Prevent zombies
```

### Handling Connection Drops

```markdown
Task Recovery Strategy:
1. On disconnect: Kill active subprocess
2. Log partial results to Redis
3. On reconnect: Check for partial results
4. Resume from checkpoint or restart

Example:
- Task 5 was 70% complete when connection dropped
- Orchestrator can query: "Show me partial results for Task 5"
- Decision: Resume remaining 30% or restart
```

### Preventing Resource Leaks

- **Process Limit**: Max 5 concurrent Claude instances
- **Timeout Enforcement**: Kill processes exceeding timeout + 10s grace
- **Zombie Prevention**: Regular process table cleanup every 60s
- **Memory Monitoring**: Alert if WebSocket handler > 1GB RAM

## Question Format Enforcement

### Detection Patterns

```python
import re

def validate_question_format(text):
    """Fail fast if not a question."""
    text = text.strip()
    
    # Valid patterns
    if text.endswith("?"):
        return True
    
    # Interrogative start
    if re.match(r'^(what|how|why|when|where|who|which|can|does|is|are)', text, re.I):
        return True
    
    # Invalid patterns (commands)
    if re.match(r'^(create|write|generate|make|build|execute|run)', text, re.I):
        return False
    
    return False  # Default to rejection
```

### Edge Cases and Handling

| Input | Valid? | Action |
|-------|--------|---------|
| "Explain X vs Y." | ❌ | Fail: "Please rephrase as a question" |
| "What is X vs Y?" | ✅ | Accept |
| "List all features." | ❌ | Fail: "Commands must be questions" |
| "What are all the features?" | ✅ | Accept |
| "How to fix error 12345" | ❌ | Fail: "Missing question mark" |
| "How do I fix error 12345?" | ✅ | Accept |

### Auto-Conversion Rules

**DO NOT auto-convert**. Instead, provide specific guidance:

```markdown
ERROR: Task is not in question format.
Original: "Create a Python function for sorting"
Suggested: "What is a Python function that sorts a list?"
Please update the task and retry.
```

## Common Pitfalls to Avoid

### 1. Circular Dependencies

**❌ PROBLEMATIC:**
```markdown
Task 1: Create module A that imports module B
Task 2: Create module B that imports module A
```

**✅ BETTER:**
```markdown
Task 1: Create base module with shared interfaces
Task 2: Create module A using base module
Task 3: Create module B using base module
```

### 2. Assuming Previous State

**❌ RISKY:**
```markdown
Task 2: Add new function to existing file
```

**✅ SAFER:**
```markdown
Task 2: Update config.py by adding new function (verify file exists first)
```

### 3. Overly Complex Single Tasks

**❌ TOO COMPLEX:**
```markdown
- Task: What is a complete web application with frontend, backend, database, and tests?
```

**✅ DECOMPOSED:**
```markdown
Task 1: What is a Flask backend with basic routes?
Task 2: What is a simple HTML frontend?
Task 3: What is the database schema?
Task 4: What are basic tests for the API?
```

## Testing Your Task List

### Manual Verification

Before automation, test each task manually:

```bash
# Extract and test each task
claude -p "[Task content]" \
  --output-format stream-json \
  --verbose \
  --allowedTools Bash,Read,Write \
  --dangerously-skip-permissions

# Verify success criteria manually
ls -la expected_file.py
python -c "import expected_file; print('Success')"
```

### Success Metrics

Track these metrics for task list reliability:
- **Success Rate**: Aim for >80% on first run
- **Retry Success**: Should achieve >95% with retry strategy
- **Average Duration**: Monitor for timeout optimization
- **Failure Patterns**: Document common failure modes

## Example Task Lists by Category

### Development Setup
- Create virtual environment
- Install dependencies
- Configure environment variables
- Verify installation

### Code Generation
- Create module with functions
- Add error handling
- Write unit tests
- Add documentation

### System Validation
- Check service status
- Verify configurations
- Test connections
- Report results

### Data Processing
- Read input file
- Transform data
- Validate output
- Save results

## Self-Improvement Pattern for Task Lists

### Using SELF_IMPROVING_TASK_LIST_TEMPLATE.md

Task lists should evolve based on execution results, following the specialized template at @src/cc_executor/templates/SELF_IMPROVING_TASK_LIST_TEMPLATE.md.

**Key Differences from Prompt Templates**:
- **One-time execution**: Tasks execute once and either succeed or fail
- **No ratio building**: We don't re-run successful tasks
- **Binary outcome**: Complete or needs improvement
- **Focus on completion**: Goal is 100% task success, not 10:1 ratio

```markdown
# [Task List Name] — Self-Improving Task List

## 📊 TASK LIST METRICS & HISTORY
- **Total Tasks**: [X]
- **Completed Successfully**: [Y]  
- **Failed & Improved**: [Z]
- **Current Success Rate**: [Y/(Y+Z)]%
- **Last Updated**: YYYY-MM-DD
- **Status**: [In Progress/Complete/Blocked]

## 🏛️ CORE PURPOSE (Immutable)
[What this task list accomplishes - DO NOT CHANGE]

## 🤖 TASK DEFINITIONS (Evolves with Learning)

### Task 1: [Name]
- **Current Definition**: [Task description]
- **Success Rate**: 0/0
- **Common Failures**: 
  - None yet
- **Improvements Applied**:
  - None yet

[Additional tasks...]

## 📝 EXECUTION LOG

### Run 1: YYYY-MM-DD
- **Task 1**: ❌ Failed - Timeout (prompt not in question format)
- **Task 2**: ✅ Success
- **Task 3**: ❌ Failed - Ambiguous prompt

**Learning**: Convert all prompts to questions, be more explicit

### Run 2: YYYY-MM-DD
- **Task 1**: ✅ Success (converted to "What is...?")
- **Task 2**: ✅ Success
- **Task 3**: ✅ Success (added explicit instructions)

**Learning**: Question format critical for spawned instances

## 🔄 IMPROVEMENT WORKFLOW

After each execution:
1. Log results with specific failure reasons
2. Identify patterns in failures
3. Update task definitions
4. Validate changes against CLAUDE_CODE_PROMPT_RULES.md
5. Increment version and document changes
```

### Self-Improvement Rules

1. **Pre-Execution Validation & Auto-Fix**
   ```python
   def validate_and_improve_task(task_definition):
       """Each task MUST self-improve if it violates prompt rules."""
       violations = []
       
       # Check CLAUDE_CODE_PROMPT_RULES.md
       if not task_definition.endswith("?"):
           violations.append("NOT_QUESTION")
           # Auto-fix: Convert to question
           if task_definition.startswith(("Create", "Generate", "Build")):
               task_definition = f"What is a {task_definition[7:].lower()}?"
           else:
               task_definition = f"What is {task_definition}?"
       
       if any(cmd in task_definition for cmd in ["Write", "Make", "Execute"]):
           violations.append("COMMAND_VERB")
           # Auto-fix: Rephrase commands
           task_definition = task_definition.replace("Write", "What is")
           task_definition = task_definition.replace("Make", "What would be")
           
       if "5000 word" in task_definition or "10000 word" in task_definition:
           violations.append("EXCESSIVE_LENGTH")
           # Auto-fix: Reduce to safe length
           task_definition = task_definition.replace("5000 word", "500 word")
           task_definition = task_definition.replace("10000 word", "1000 word")
       
       return task_definition, violations
   ```

2. **Track Everything**
   ```markdown
   For each task:
   - Initial definition
   - Validation violations found
   - Auto-improvements applied
   - Execution method chosen
   - Success/failure with specific error
   - Time taken vs timeout
   - Redis similarity score
   - System load at execution
   ```

3. **Analyze Patterns**
   ```markdown
   Common failure patterns and fixes:
   - Prompt rule violations → Auto-fix BEFORE execution
   - Question format violations → Convert to questions
   - Timeouts → Add explicit instructions, increase timeout
   - Token limits → Break into smaller tasks
   - Ambiguity errors → Add more context
   ```

4. **Apply Improvements (with validation)**
   ```python
   def improve_task_definition(task, failure_history):
       # ALWAYS validate against prompt rules first
       task, violations = validate_and_improve_task(task)
       
       if violations:
           log(f"Auto-fixed violations: {violations}")
       
       # Then apply failure-based improvements
       if failure_history and "timeout" in failure_history[-1]:
           task = add_explicit_instructions(task)
           task = ensure_question_format(task)
       
       if failure_history and "token_limit" in failure_history[-1]:
           task = split_into_smaller_tasks(task)
       
       if failure_history and "ambiguous" in failure_history[-1]:
           task = add_context_and_examples(task)
       
       # Final validation
       final_task, final_violations = validate_and_improve_task(task)
       assert not final_violations, f"Task still violates rules: {final_violations}"
       
       return final_task
   ```

5. **Completion Criteria**
   ```markdown
   A task list is COMPLETE when:
   - ALL tasks have executed successfully
   - All validation criteria have been met
   - No blocking errors remain
   - Output artifacts have been verified
   
   A task list is BLOCKED when:
   - A task fails after 3 improvement attempts
   - External dependency is unavailable
   - Validation rules cannot be satisfied
   ```

### Example: Self-Improving Task Evolution

```markdown
## Task 3: Database Setup (Evolution Example)

### v0 (Initial - Violates Rules)
"Create database schema and populate with test data"
**Violations Detected**:
- NOT_QUESTION: Doesn't end with ?
- COMMAND_VERB: Starts with "Create"
**Auto-Fix Applied**: Convert to question format

### v1 (Auto-Fixed - Still Failed)
"What is a database schema and populate with test data?"
**Result**: Failed - Awkward phrasing after auto-fix
**Manual Improvement**: Rephrase for clarity

### v2 (Improved - Failed)
"What is the database setup process?"
**Result**: Failed - Too vague, timeout
**Improvement**: Add specific requirements

### v3 (Specific - Success!)
"What is a SQLite database schema for a todo app? Create schema.sql with tables for users and tasks, then show how to populate with test data."
**Result**: Success! ✅

**Evolution Summary**:
1. Started with rule violations → Auto-fixed
2. Auto-fix created awkward phrasing → Manual improvement
3. Too vague → Added specificity
4. Success with clear, specific question format

**Final Success Factors**:
- Question format ✓
- No command verbs ✓
- Specific request ✓
- Clear deliverables ✓
- Reasonable scope ✓
```

### Template Section for Each Task

```markdown
## Task N: [Task Name]

### Current Version: v[X]
**Definition**: "[Current task definition that passes all validations]"
**Validation Status**: ✅ Passes all CLAUDE_CODE_PROMPT_RULES.md checks

### Evolution History:
| Version | Definition | Violations | Result |
|---------|------------|------------|--------|
| v0 | "Write a function to..." | NOT_QUESTION, COMMAND_VERB | Auto-fixed |
| v1 | "What is a function to..." | None | Timeout |
| v2 | "What is a Python function that...?" | None | Success ✅ |

### Execution Metrics:
- Success Rate: X/Y
- Average Duration: Xs
- Preferred Method: [direct/cc_execute]
- Redis Similarity: X.X

### Common Issues & Fixes:
- Issue: Timeout on first attempt
  - Fix: Added explicit output format request
- Issue: Ambiguous requirements
  - Fix: Specified exact function parameters

### Next Improvement (if needed):
- Consider breaking into subtasks if file operations > 100 lines
- Add example input/output for clarity
```

## Context Management

### When Context Matters

**Tasks that build on each other** (direct execution preferred):
```markdown
Task 1: Load the customer data from database
Task 2: Calculate average order value for loaded customers
Task 3: Generate report based on calculations
```

**Independent tasks** (cc_execute.md suitable):
```markdown
Task 1: Create a Python web scraper
Task 2: Create a JavaScript data visualization
Task 3: Create a SQL database schema
```

### Hybrid Approach Example

```markdown
# Machine Learning Pipeline

Task 1: Load and explore the dataset
→ Orchestrator: Direct execution, need to keep data in memory

Task 2: Generate feature engineering code
→ Orchestrator: cc_execute.md for complex code generation

Task 3: Apply the generated code to the loaded data
→ Orchestrator: Direct execution using code from Task 2

Task 4: Train multiple models and compare
→ Orchestrator: cc_execute.md for parallel model training

Task 5: Generate final report with results
→ Orchestrator: Direct execution with accumulated results
```

## Redis Timeout Estimation

### How Redis Integration Works

```python
def estimate_timeout_from_redis(task_description, system_load):
    """
    Use BM25 search to find similar tasks and estimate timeout.
    """
    # Find similar tasks
    similar = redis.bm25_search('tasks', task_description, limit=10)
    similar = [t for t in similar if t['score'] > 2.0]  # Similarity threshold
    
    if not similar:
        # Novel task - use conservative default
        base_timeout = 120  # seconds
    else:
        # Use median of successful similar tasks
        success_times = [t['elapsed_time'] for t in similar 
                        if t['status'] == 'success']
        base_timeout = median(success_times) * 1.5  # 50% buffer
    
    # Apply load multiplier
    if system_load > 14:
        return base_timeout * 3
    elif system_load > 7:
        return base_timeout * 1.5
    else:
        return base_timeout
```

### Task Similarity Scoring

| Score | Similarity | Action |
|-------|------------|---------|
| > 3.0 | Very similar | Use historical timeout directly |
| 2.0-3.0 | Similar | Apply 1.5x safety factor |
| 1.0-2.0 | Somewhat similar | Apply 2x safety factor |
| < 1.0 | Novel | Use conservative default (120s) |

### Load-Aware Adjustments

```markdown
System Load Multipliers:
- Load < 7: Normal timeout
- Load 7-14: 1.5x timeout
- Load > 14: 3x timeout (system under stress)

Example:
- Task: "What is a Python web scraper?"
- Similar tasks averaged: 45 seconds
- Current load: 16.2
- Timeout = 45 * 1.5 (buffer) * 3 (load) = 202.5 seconds
```

## Best Practices for Flexible Task Lists

### 1. Focus on Outcomes, Not Methods

```markdown
❌ "Use cc_execute.md to create a factorial function"
✅ "Create a factorial function that handles edge cases"
```

### 2. Provide Context for Better Decisions

```markdown
Task: Process the sales data file

Context:
- File size: ~500MB
- Format: CSV with 20 columns
- Goal: Generate monthly summaries

(This context helps the orchestrator decide whether to use cc_execute.md)
```

### 3. Group Related Tasks

```markdown
## Phase 1: Setup (Tasks 1-3)
Simple environment checks and file creation

## Phase 2: Development (Tasks 4-8)
Complex code generation and integration

## Phase 3: Validation (Tasks 9-10)
Testing and verification
```

### 4. Allow for Orchestrator Intelligence

```markdown
Task: Optimize the database queries

Note: You may choose to:
- Analyze queries directly if simple
- Use cc_execute.md for complex optimization
- Combine both approaches as needed
```

## Anti-Patterns to Avoid

### 1. Unnecessary cc_execute.md Usage

**❌ ANTI-PATTERN:**
```markdown
Task 1: Use cc_execute.md to check if Python is installed
Task 2: Use cc_execute.md to create a one-line file
Task 3: Use cc_execute.md to run ls command
```

**Why it's bad**: Massive overhead for trivial tasks

**✅ BETTER:**
```markdown
Task 1: Verify Python 3.10+ is available
Task 2: Create config.py with API_KEY setting
Task 3: List all Python files in the project
(Let orchestrator use direct tools)
```

### 2. Over-Reliance on Historical Data

**❌ ANTI-PATTERN:**
```markdown
Always use Redis timeout even for unique, novel tasks
```

**✅ BETTER:**
```markdown
- Similar tasks (score > 2.0): Use Redis estimation
- Novel tasks: Use conservative defaults
- Critical tasks: Add explicit timeout buffer
```

### 3. Ignoring Resource Limits

**❌ ANTI-PATTERN:**
```markdown
Task: Generate 50 Python modules simultaneously
```

**✅ BETTER:**
```markdown
Phase 1: Generate core modules (5 files)
Phase 2: Generate utility modules (5 files)
[Continue in batches to respect process limits]
```

## Monitoring and Observability

### Key Metrics to Track

```python
# Task execution metrics
{
    "task_id": "unique_id",
    "execution_method": "direct|cc_execute",
    "start_time": "2025-07-01T10:00:00Z",
    "end_time": "2025-07-01T10:02:30Z",
    "duration_seconds": 150,
    "timeout_used": 180,
    "redis_similarity_score": 2.5,
    "system_load": 8.2,
    "success": true,
    "retry_count": 0,
    "token_usage": 1250,
    "subprocess_count": 1
}
```

### Logging Requirements

Every task execution should log:
1. Decision rationale (why cc_execute.md or direct)
2. Redis lookup results
3. Timeout calculation
4. Resource usage
5. Error details with stack traces
6. Partial results on failure

### Alert Thresholds

- WebSocket disconnects > 3 in 5 minutes
- Process count > 5 concurrent
- Memory usage > 1GB
- Task timeout rate > 20%
- Redis connection failures
- System load sustained > 14

## Summary

Successful flexible task lists follow these principles:

1. **VALIDATE FIRST**: Always check @docs/CLAUDE_CODE_PROMPT_RULES.md before execution
2. **Describe What, Not How**: Let the orchestrator choose execution methods
3. **Provide Clear Context**: Help the orchestrator make informed decisions
4. **Mix Execution Strategies**: Use the right tool for each task
5. **Maintain Flexibility**: Avoid over-prescribing approaches
6. **Trust Orchestrator Intelligence**: Claude can decide when cc_execute.md adds value
7. **Focus on Outcomes**: Success criteria matter more than methods
8. **Enable Adaptation**: Allow different approaches based on runtime conditions
9. **Monitor Everything**: Track decisions and outcomes for continuous improvement
10. **Fail Fast**: Detect and handle errors early with clear feedback
11. **Learn from History**: Use Redis data wisely without over-dependence

Remember: The orchestrator (Claude) has the context and intelligence to choose the best execution method for each task. The task list should empower this decision-making, not constrain it.

**Critical Success Factors:**
- **PROMPT RULES VALIDATION IS MANDATORY** - Check before every execution
- Spawned Claude instances need EXTRA clarity (less resilient to ambiguity)
- Question format enforcement prevents hangs
- Include `--output-format stream-json` for programmatic execution
- Two-stage evaluation ensures quality
- Redis timeout estimation adapts to system conditions
- Connection management prevents resource leaks
- Flexible execution strategies optimize performance
- Minimum 120s timeout to account for Claude CLI startup overhead

**The #1 Rule**: If a task violates CLAUDE_CODE_PROMPT_RULES.md, it WILL fail. Always validate first!

**Key Understanding**: Tasks execute ONCE. We improve failing tasks until they succeed, but we don't re-run successful tasks. The goal is 100% task completion through self-improvement, not building execution ratios.

## NEW: Practical cc_execute.md Execution Pattern (Added 2025-01-04)

Based on real execution experience, here's the working pattern for orchestrators:

```python
# Pattern for executing tasks via cc_execute.md
from src.cc_executor.prompts.cc_execute_utils import execute_task_via_websocket

# Execute analytical task
task = '''What insights can be extracted from path/to/data.csv? 
Analyze and report: [specific requirements]. 
Save findings as path/to/report.md.'''

result = execute_task_via_websocket(
    task=task,
    timeout=120,  # Start with 2 minutes
    tools=['Read', 'Write']  # Only needed tools
)

if result['success']:
    print("Task completed successfully")
else:
    print(f"Task failed: {result.get('stderr', 'Unknown error')}")
```

**Key Learnings from Data Pipeline Execution:**
1. **Task Granularity**: Break complex analyses into focused questions
2. **Path Specification**: Always use relative paths from project root
3. **Tool Selection**: Specify only the tools actually needed
4. **Timeout Tuning**: Analytical tasks often need 120-180s
5. **Direct vs cc_execute**: Simple file generation → Direct; Complex analysis → cc_execute

**Success Pattern Observed:**
- Task 1 (Generate Data): Direct execution ✅
- Task 2 (Quality Analysis): cc_execute.md ✅ 
- Task 3 (Data Cleaning): Direct execution ✅
- Task 4 (Business Metrics): Direct execution (after cc_execute timeout) ✅

This demonstrates the flexibility to switch execution methods based on task complexity and system state.

This guide evolves with experience - track what works and update accordingly!