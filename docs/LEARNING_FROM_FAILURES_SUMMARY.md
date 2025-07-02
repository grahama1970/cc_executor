# Learning from Failures: Stress Test Philosophy

## Core Principle

**Timeouts and errors are GOOD!** They teach us how to write better prompts.

## The Learning Cycle

```
1. Write prompt
2. Test it
3. If timeout/error → Analyze why
4. Amend prompt based on failure pattern
5. Test improved version
6. Document the learning
7. Add to CLAUDE_CODE_PROMPT_RULES.md
```

## Key Discoveries from Failures

### 1. Terse Response Pattern
- **Symptom**: Got "3.14159265359" for "What is pi?"
- **Learning**: Ultra-specific questions get ultra-specific answers
- **Solution**: Always ask for context/explanation
- **Fixed**: "What is pi and why is it important? Include value and uses."

### 2. Execution Ambiguity Pattern
- **Symptom**: "Execution error" or file creation when asking for code
- **Learning**: "Show me", "with example" triggers execution
- **Solution**: Use "What is" and clarify "(not execution)"
- **Fixed**: "What is a Python factorial function? Explain with code example."

### 3. Command Timeout Pattern
- **Symptom**: Timeout on "Write a story about AI"
- **Learning**: Imperative commands hang
- **Solution**: Rephrase as questions
- **Fixed**: "What is a story outline about AI?"

### 4. Missing Structure Pattern
- **Symptom**: Rambling, incomplete responses
- **Learning**: Complex topics need structure
- **Solution**: Specify what to include
- **Fixed**: "What is X? Include: 1) A, 2) B, 3) C"

## Implementation

### 1. Self-Reflecting Prompts
All prompts now include self-evaluation:
```
[Question]
After answering, evaluate against:
1. [Criterion 1]
2. [Criterion 2]
If missing any, provide improved version.
```

### 2. Failure Discovery Tests
Created `failure_discovery_tasks.json` with prompts designed to fail:
- Tests ambiguous execution patterns
- Tests terse response triggers
- Tests command timeouts
- Documents improved versions

### 3. Enhanced Documentation
- Added "Learning from Failures" section to CLAUDE_CODE_PROMPT_RULES.md
- Created failure → success pattern mappings
- Documented real examples with timings

## Results

- Started with 38.5% success rate
- Through failure analysis, reached 100% on safe prompts
- Each failure taught us a reusable pattern
- Built comprehensive prompt engineering knowledge base

## Philosophy

> "A stress test that never fails teaches nothing. A stress test that fails and leads to improvement teaches everything."

The goal is NOT 100% success rate. The goal is continuous learning and improvement through systematic failure analysis.