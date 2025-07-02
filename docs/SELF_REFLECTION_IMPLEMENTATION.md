# Self-Reflection Implementation for Stress Tests

## Overview

We've implemented a self-reflection mechanism that allows Claude to evaluate and improve its own responses within a single API call, reducing the need for external retries and improving response quality.

## Key Components

### 1. Self-Reflecting Prompts

All prompts now include self-evaluation criteria:

```bash
[Original Question]

After providing your answer, evaluate it against these criteria:
1. [Specific criterion 1]
2. [Specific criterion 2]
3. [Specific criterion 3]

If your response doesn't fully satisfy all criteria, provide an improved version.
Label versions as "Initial Response:" and "Improved Response:" if needed.
Maximum self-improvements: [N]
```

### 2. Task Type-Specific Criteria

Different task types have tailored criteria:

- **Template tasks**: All sections included, clear format, helpful examples
- **Creative tasks**: Answers the question, includes all elements, actionable
- **Calculation tasks**: Shows all results, clearly labeled, accurate
- **Code tasks**: Working examples, helpful comments, educational
- **Explanation tasks**: Clear definition, key concepts, good examples

### 3. Enhanced WebSocket Handler

`websocket_handler_self_reflecting.py` detects and reports self-reflection progress:

```python
# Detects patterns like:
- "Self-evaluation:"
- "Version 1:", "Version 2:"
- "✓ Criterion met" / "✗ Criterion not met"
- "provide improved version"

# Sends notifications:
{
  "method": "process.reflection",
  "params": {
    "status": "reflecting",
    "version": 2,
    "criteria_met": 2,
    "criteria_total": 3,
    "improvement_needed": true
  }
}
```

### 4. Test Configuration

New JSON file: `unified_stress_test_tasks_self_reflecting.json`

```json
{
  "self_reflection_config": {
    "enabled": true,
    "default_max_iterations": 2,
    "version_markers": ["Initial Response:", "Improved Response:"]
  },
  "categories": {
    "simple": {
      "tasks": [{
        "natural_language_request": "[question with self-reflection]",
        "self_reflection": {
          "enabled": true,
          "max_iterations": 2,
          "task_type": "template"
        },
        "verification": {
          "reflection_patterns": ["criteria", "evaluate", "Response:"],
          "timeout": 270  // 1.5x normal timeout
        }
      }]
    }
  }
}
```

## Results

Initial testing shows:
- **75% success rate** (3/4 tests passed)
- **100% self-reflection detection** (all tests showed evaluation)
- **Average 1 version per test** (most got it right first time)
- **20.2s average execution time** (reasonable for reflection)

## Benefits

1. **Higher Quality Responses**: Claude catches omissions before returning
2. **Fewer External Retries**: Issues fixed within single API call
3. **Better Test Stability**: Less reliance on exact pattern matching
4. **Transparent Progress**: WebSocket notifications show reflection status

## Implementation Status

✅ Created self-reflecting prompt templates
✅ Generated transformed test JSON with all prompts updated
✅ Built test runner for self-reflecting prompts
✅ Documented patterns in CLAUDE_CODE_PROMPT_RULES.md
✅ Created enhanced WebSocket handler (ready to integrate)
⏳ Full stress test run pending
⏳ WebSocket integration pending

## Next Steps

1. Run full stress test suite with self-reflecting prompts
2. Compare success rates vs. original prompts
3. Integrate enhanced WebSocket handler if improvement confirmed
4. Update all prompt templates to use self-reflection by default