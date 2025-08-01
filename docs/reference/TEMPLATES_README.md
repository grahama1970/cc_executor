# CC Executor Documentation Templates

## Overview

This directory contains standardized templates for writing consistent, high-quality code in the CC Executor project. These templates are based on best practices learned from developing and refining the project.

**Last Updated**: 2025-01-04 (Cleaned up archived templates)

## Available Templates

### 1. [PYTHON_SCRIPT_TEMPLATE.md](./PYTHON_SCRIPT_TEMPLATE.md)
**Purpose**: Standard structure for all Python scripts in the project

**Key Features**:
- Comprehensive docstring format with examples
- Functions outside `__main__` block pattern
- Single `asyncio.run()` enforcement
- Loguru logging configuration
- Redis/ArangoDB integration patterns
- Results saved to `tmp/responses/` with timestamps
- **NEW**: Breakpoint comments for debugging guidance

**When to Use**: Creating any new Python script in the project

### 2. [CODE_REVIEW_REQUEST_TEMPLATE.md](./CODE_REVIEW_REQUEST_TEMPLATE.md)
**Purpose**: Standardized format for requesting code reviews

**Key Features**:
- Structured change documentation
- Testing verification checklist
- Performance and security considerations
- Clear review focus areas
- Definition of done criteria
- **UPDATED**: Added known anti-patterns from project experience
- **UPDATED**: Sequential execution verification checks

**When to Use**: Submitting code for review

### 3. [ASYNC_PATTERNS_TEMPLATE.md](./ASYNC_PATTERNS_TEMPLATE.md)
**Purpose**: Best practices for asynchronous operations

**Key Features**:
- Single entry point pattern
- Subprocess stream draining (prevents deadlock)
- WebSocket connection management
- Resource cleanup patterns
- Common pitfalls and solutions

**When to Use**: Writing async code, especially with subprocesses or WebSockets

### 4. [DATA_STORAGE_PATTERNS.md](./DATA_STORAGE_PATTERNS.md)
**Purpose**: Patterns for data storage across different backends

**Key Features**:
- Redis for caching and metrics
- File system for results and logs
- ArangoDB for complex relationships
- Hybrid storage for large data
- Storage decision matrix

**When to Use**: Implementing data persistence or caching

### 5. [TASK_LIST_REPORT_TEMPLATE.md](./TASK_LIST_REPORT_TEMPLATE.md)
**Purpose**: Comprehensive reporting structure for task list executions

**Key Features**:
- Raw JSON output for each task (anti-hallucination)
- Agent reasonableness assessment per task
- Cross-task dependency verification
- File system verification commands
- Confidence levels and pattern analysis
- Full execution evidence trail

**When to Use**: Generating reports after task list execution via hooks

### 6. [CORE_ASSESSMENT_REPORT_TEMPLATE.md](./CORE_ASSESSMENT_REPORT_TEMPLATE.md)
**Purpose**: Assessment template for testing all script `if __name__ == "__main__"` blocks

**Key Features**:
- Tests every Python script's demo/usage code
- Verifies reasonable output from each component
- Validates numerical values are in expected ranges
- Requires reading full JSON output files (anti-hallucination)
- Agent assessment of functionality demonstration
- System health analysis based on all outputs
- **v1.3**: Added UUID4 anti-hallucination verification

**When to Use**: After each code review round to verify all scripts work correctly

### 7. [PROMPT_TEMPLATE.md](./PROMPT_TEMPLATE.md)
**Purpose**: Gamified self-improving prompt template with anti-hallucination measures

**Key Features**:
- UUID4 generation and verification (at END of JSON)
- Success/failure tracking with 10:1 graduation requirement
- Self-recovery patterns for automatic improvement
- Raw output saving to prevent fabrication
- Gamification rules that prevent giving up
- Comprehensive debugging resources
- Evolution history tracking with UUIDs

**When to Use**: Creating new self-improving prompts that need to graduate to production code

## Quick Start Guide

### Creating a New Script

1. Copy the structure from [PYTHON_SCRIPT_TEMPLATE.md](./PYTHON_SCRIPT_TEMPLATE.md)
2. Replace placeholder content with your implementation
3. Ensure all checklist items are satisfied
4. Run the script to verify the `__main__` block works
5. Save results to `tmp/responses/` for verification

### Requesting a Code Review

1. Use [CODE_REVIEW_REQUEST_TEMPLATE.md](./CODE_REVIEW_REQUEST_TEMPLATE.md)
2. Fill in all sections completely
3. Run all tests and document results
4. Highlight specific areas needing attention
5. Submit with clear title and description

### Implementing Async Operations

1. Review [ASYNC_PATTERNS_TEMPLATE.md](./ASYNC_PATTERNS_TEMPLATE.md)
2. Choose appropriate pattern for your use case
3. Pay special attention to subprocess stream draining
4. Implement proper cleanup and cancellation
5. Test timeout and error scenarios

### Choosing Storage Solutions

1. Consult the decision matrix in [DATA_STORAGE_PATTERNS.md](./DATA_STORAGE_PATTERNS.md)
2. Implement with graceful degradation
3. Use appropriate TTLs for temporary data
4. Include metadata with stored results
5. Plan for service unavailability

### Running Script Assessments

1. Use [CORE_ASSESSMENT_REPORT_TEMPLATE.md](./CORE_ASSESSMENT_REPORT_TEMPLATE.md)
2. Run all `if __name__ == "__main__"` blocks in core/, cli/, client/, and hooks/
3. Capture output to JSON files in tmp/responses/
4. Read FULL JSON files (not truncated output)
5. Assess if each output demonstrates the component's functionality
6. Validate all numerical values are reasonable
7. Generate comprehensive report with system health assessment

## Assessment Workflow After Code Reviews

After each code review round, run a comprehensive assessment:

1. **Execute Assessment Scripts**:
   - Run `assess_all_core_usage.py` for core/ directory
   - Run `assess_all_cli_usage.py` for cli/ directory  
   - Run `assess_all_client_usage.py` for client/ directory
   - Run `assess_all_hooks_usage.py` for hooks/ directory

2. **Generate Reports**:
   - Each assessment creates JSON files in `tmp/responses/`
   - Read FULL JSON files, not truncated console output
   - Use CORE_ASSESSMENT_REPORT_TEMPLATE.md structure

3. **Verify Functionality**:
   - Each script's `__main__` block should demonstrate its purpose
   - Output should be reasonable and error-free
   - Numbers should be in valid ranges
   - No infinite loops or crashes

4. **System Health Check**:
   - Aggregate results show overall system health
   - Identify any broken components
   - Ensure critical components (websocket_handler.py) work

## Core Principles

### 1. Consistency
All scripts follow the same structure, making the codebase predictable and maintainable.

### 2. Testability
Every script includes runnable examples in the `__main__` block with assertions. These are tested after each code review round.

### 3. Debuggability
Results are saved to `tmp/responses/` with timestamps for forensic analysis.

### 4. Robustness
Graceful degradation when external services (Redis, ArangoDB) are unavailable.

### 5. Documentation
Real-world examples and third-party links in every script.

## Common Patterns Across Templates

### Logging Setup
```python
from loguru import logger

# Remove default handler
logger.remove()

# Add custom format
logger.add(sys.stderr, 
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)
```

### Service Availability Check
```python
try:
    redis_client = redis.Redis(decode_responses=True)
    redis_client.ping()
    REDIS_AVAILABLE = True
except Exception:
    logger.warning("Redis not available - some features will be limited")
    redis_client = None
    REDIS_AVAILABLE = False
```

### Results Saving
```python
def save_results(results: Dict[str, Any]) -> Path:
    output_dir = Path(__file__).parent / "tmp" / "responses"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{Path(__file__).stem}_results_{timestamp}.json"
    
    with open(output_dir / filename, 'w') as f:
        json.dump(results, f, indent=2, sort_keys=True)
    
    return output_dir / filename
```

### Single Async Entry Point
```python
async def main():
    """Main entry point for all async operations."""
    # All async code here
    pass

if __name__ == "__main__":
    # Only ONE asyncio.run() call
    asyncio.run(main())
```

## Evolution and Updates

These templates evolve based on project experience. When updating:

1. Document the change reason
2. Update all affected templates
3. Include migration notes for existing code
4. Update this README with new patterns

## Contributing

To propose template improvements:

1. Identify the pattern through real usage
2. Verify it solves a common problem
3. Ensure it doesn't add unnecessary complexity
4. Document with clear examples
5. Submit with rationale and impact analysis

## Archived Templates

The following templates have been moved to the `archive/` directory as they are superseded or no longer relevant:

1. **SELF_IMPROVING_PROMPT_TEMPLATE.md** - Replaced by graduated Python scripts
2. **SELF_IMPROVING_TASK_LIST_TEMPLATE.md** - Replaced by TASK_LIST_TEMPLATE_GUIDE.md
3. **PROMPT_SYSTEM_GUIDELINES.md** - Specific to old prompt system
4. **REVIEW_PROMPT_AND_CODE_TEMPLATE.md** - Replaced by updated CODE_REVIEW_REQUEST_TEMPLATE.md
5. **REASONABLE_OUTPUT_ASSESSMENT.md** - Superseded by proper testing patterns

These are preserved for historical reference but should not be used for new development.

## Summary

These templates encapsulate hard-won knowledge from building CC Executor. They help maintain consistency, prevent common errors, and speed up development by providing proven patterns for common tasks.

Use them as starting points, but always consider the specific needs of your implementation. The goal is consistency and quality, not rigid adherence to rules.