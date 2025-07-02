# Stress Test Prompt Analysis Report

## Summary
Analysis of unified_stress_test_tasks.json to identify prompts likely to hang and provide simplified alternatives.

## High-Risk Prompts (Likely to Hang)

### 1. **simple_1** - Daily Standup (Interactive)
**Problem**: Uses interactive prompts "Ask me what I worked on..."
**Risk**: HIGH - Claude CLI might wait for user input
**Simplified**: 
```
"What is a template for a daily standup update that includes sections for yesterday's work, today's plans, and blockers?"
```

### 2. **long_1** - Epic Story (5000 words)
**Problem**: Requests 5000 word story with streaming
**Risk**: HIGH - Long generation + streaming can timeout
**Simplified**:
```
"What is a brief 500-word outline for a science fiction story about a programmer discovering sentient code?"
```

### 3. **long_2** - Comprehensive Guide (10,000 words)
**Problem**: Requests 10,000 word guide with code examples
**Risk**: EXTREME - Very long generation will timeout
**Simplified**:
```
"What is a concise checklist (under 1000 words) for building production-ready Python applications?"
```

### 4. **complex_1** - Full Stack App
**Problem**: Multi-step guide with "Show all code and explanations for each step"
**Risk**: HIGH - Step-by-step format may trigger interactive mode
**Simplified**:
```
"What is a high-level architecture overview for a todo app using FastAPI and React?"
```

### 5. **extreme_3** - Ultimate Stress (100 Python scripts)
**Problem**: Requests 100 different Python scripts with full code
**Risk**: EXTREME - Massive output will timeout
**Simplified**:
```
"What is a list of 10 common Python script categories with one example function for each?"
```

### 6. **extreme_2** - Infinite Improvement
**Problem**: "improve it 10 times" with iterative improvements
**Risk**: HIGH - Iterative nature may cause confusion
**Simplified**:
```
"What is the most production-ready version of a hello world program in Python?"
```

### 7. **rapid_1** - Hundred Questions
**Problem**: "[... continue with 95 more simple questions]" is vague
**Risk**: MEDIUM - Incomplete prompt may cause confusion
**Simplified**:
```
"What is the answer to these 5 yes/no questions: Is Python interpreted? Is Java compiled? Is 2+2=4? Is the sky blue? Is water wet?"
```

### 8. **advanced_1**, **advanced_2**, **advanced_3** - Multi-turn orchestration
**Problem**: Complex multi-step execution with "find and use" instructions
**Risk**: HIGH - Requires file system operations and iterations
**Simplified versions provided below

## Recommended Simplified Task List

```json
{
  "simplified_stress_tests": {
    "simple": [
      {
        "id": "simple_1_safe",
        "request": "What is a template for a daily standup update with sections for yesterday, today, and blockers?",
        "timeout": 30
      },
      {
        "id": "simple_2_safe", 
        "request": "What is a quick chicken and rice recipe that takes 30 minutes using tomatoes, onions, and garlic?",
        "timeout": 30
      },
      {
        "id": "simple_3_safe",
        "request": "What is the result of these calculations: 15+27, 83-46, 12*9, 144/12, 2^8?",
        "timeout": 30
      }
    ],
    "medium": [
      {
        "id": "medium_1_safe",
        "request": "What is Python code for 5 common functions: area of circle, celsius to fahrenheit, prime check, string reverse, and factorial?",
        "timeout": 60
      },
      {
        "id": "medium_2_safe",
        "request": "What is a collection of 5 haikus about programming concepts: variables, loops, functions, debugging, and git?",
        "timeout": 60
      }
    ],
    "long": [
      {
        "id": "long_1_safe",
        "request": "What is a 500-word story outline about a programmer discovering sentient code?",
        "timeout": 90
      },
      {
        "id": "long_2_safe",
        "request": "What is a 1000-word checklist for building production Python applications covering architecture, testing, and deployment?",
        "timeout": 120
      }
    ],
    "complex": [
      {
        "id": "complex_1_safe",
        "request": "What is the architecture for a todo app with database schema, FastAPI backend, and React frontend?",
        "timeout": 120
      },
      {
        "id": "complex_2_safe",
        "request": "What is an improved version of this Python function with tests and documentation: def process_data(data): result = []; for i in range(len(data)): if data[i] > 0: result.append(data[i] * 2); return result",
        "timeout": 90
      }
    ]
  }
}
```

## Key Patterns to Avoid

1. **Interactive Prompts**: "Ask me...", "Guide me through..."
2. **Excessive Length**: Requests for 5000+ words
3. **Step-by-Step Instructions**: "First do X, then Y, then Z..."
4. **Iterative Requests**: "improve it N times"
5. **Vague Continuations**: "[... continue with more]"
6. **File System Operations**: "find and use", "create files"
7. **Multiple Models**: Complex orchestration with external tools

## Safe Prompt Formula

Always use: **"What is..."** format with:
- Clear, specific request
- Reasonable length constraints
- No interactive elements
- No file system operations
- Single, atomic task

## Testing Recommendations

1. Start with simplified prompts to establish baseline
2. Gradually increase complexity while monitoring for hangs
3. Set aggressive timeouts (30-120 seconds max)
4. Use stall detection (no output for 20+ seconds = likely hang)
5. Monitor Claude CLI process for zombie/hanging states