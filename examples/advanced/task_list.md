# Advanced CC_Execute Usage - Tool Integration & External Verification

This demonstrates advanced orchestration patterns from the README:
- Using MCP tools (perplexity-ask) for research
- Fresh context via cc_execute for implementation
- External verification with different models
- Sequential dependencies and tool chaining

## Overview

Build a quantum computing tutorial with:
1. Research using perplexity-ask (MCP tool)
2. Tutorial creation with cc_execute (fresh context)
3. External review with gemini
4. Interactive notebook generation

## Tasks

### Task 1: Research Quantum Entanglement (Direct - MCP Tool)
**Timeout**: 60s

Use the perplexity-ask MCP tool to research quantum entanglement breakthroughs from 2024-2025. Save the research findings to quantum_research.md with:
- Recent experimental breakthroughs
- New theoretical developments
- Practical applications emerging
- Key researchers and institutions

This task uses MCP tools directly without cc_execute.

### Task 2: Create Tutorial (cc_execute.md - Fresh Context)
**Timeout**: 300s (5 minutes)

Using cc_execute.md: Based on the research in quantum_research.md, create a beginner-friendly tutorial on quantum entanglement. Save as quantum_tutorial.md with:
- Introduction for non-physicists
- Core concepts explained simply
- Python code examples using qiskit
- Visual diagrams (as ASCII art or mermaid)
- Real-world applications
- Further learning resources

This needs fresh context to process the research and generate comprehensive content.

### Task 3: External Review (cc_execute.md with LiteLLM)
**Timeout**: 180s (3 minutes)

Using cc_execute.md: Review the tutorial from quantum_tutorial.md using the ask-litellm.md prompt with gemini-2.0-flash-exp model. Create review_feedback.md with:
- Technical accuracy assessment
- Pedagogical effectiveness
- Code quality review
- Suggestions for improvement
- Missing concepts to add

Fresh context ensures unbiased review.

### Task 4: Interactive Exercises (cc_execute.md)
**Timeout**: 300s (5 minutes)

Using cc_execute.md: Based on the tutorial and review feedback, create interactive Jupyter notebook exercises. Save as quantum_exercises.ipynb with:
- Exercise 1: Basic quantum states
- Exercise 2: Creating entangled states
- Exercise 3: Measuring quantum correlations
- Exercise 4: Simulating Bell's inequality
- Solutions with explanations

Each exercise should build on the previous one.

## Advanced Patterns Demonstrated

### 1. MCP Tool Integration
- Task 1 shows direct MCP tool usage (perplexity-ask)
- No cc_execute needed for simple tool calls

### 2. Fresh Context When Needed
- Tasks 2-4 use cc_execute for complex generation
- Each gets full 200K context window
- No pollution between tasks

### 3. External Model Verification
- Task 3 uses gemini via LiteLLM for independent review
- Different perspective from different model

### 4. Sequential Dependencies
- Each task builds on previous outputs
- Research → Tutorial → Review → Exercises

## Expected Outputs

```
quantum_research.md       # MCP research results
quantum_tutorial.md       # Comprehensive tutorial
review_feedback.md        # External model review
quantum_exercises.ipynb   # Interactive notebook
```

## Why This Pattern?

1. **Tool Selection**: Use the right tool for each task
   - MCP for external data (perplexity-ask)
   - cc_execute for complex generation
   - External models for verification

2. **Context Management**: 
   - Simple queries don't need fresh context
   - Complex generation benefits from isolation

3. **Quality Assurance**:
   - External review catches issues
   - Different models provide different perspectives

4. **Educational Value**:
   - Shows real-world orchestration
   - Demonstrates when to use cc_execute vs direct execution