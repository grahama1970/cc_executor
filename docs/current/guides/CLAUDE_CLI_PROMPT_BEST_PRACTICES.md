# Claude CLI Prompt Best Practices

## Critical Learning: Claude CLI Is Less Resilient Than Main Agent

This document captures hard-won knowledge about why certain prompts fail with Claude CLI but work fine with the main Claude agent. Understanding these differences is crucial for writing reliable cc_executor tasks.

## The Core Discovery

**Claude CLI instances cannot recover from ambiguous prompts the way the main Claude agent can.**

### Main Claude Agent (Resilient)
- Understands context and intent
- Can handle "Write me a function" 
- Asks for clarification when confused
- Gracefully recovers from ambiguity

### Claude CLI (Fragile)
- Takes commands literally
- Hangs on imperative commands
- Cannot ask for clarification
- Times out instead of recovering

## Critical Rules for Claude CLI

### 1. ALWAYS Use Question Format, Not Commands

**❌ Commands That Cause Timeouts:**
```bash
# These WILL hang or timeout:
claude -p "Write a Python function to calculate factorial"
claude -p "Create a web scraper in Python"  
claude -p "Generate 20 haikus about programming"
claude -p "Build a REST API"
claude -p "Implement a sorting algorithm"
```

**✅ Questions That Work Reliably:**
```bash
# These work consistently:
claude -p "What is a Python function that calculates factorial?"
claude -p "What is a Python web scraper example?"
claude -p "What are 20 haikus about programming?"
claude -p "What is a REST API architecture?"
claude -p "What is a sorting algorithm implementation?"
```

### 2. Why This Happens

Claude CLI interprets imperative verbs as execution requests:
- "Write" → Tries to write files
- "Create" → Attempts to create resources
- "Generate" → Triggers generation mode
- "Build" → Initiates build processes

This causes the CLI to enter states it cannot recover from.

### 3. The Question Format Solution

By phrasing as "What is...", we:
- Signal we want information, not action
- Avoid triggering execution modes
- Keep Claude in explanation mode
- Ensure predictable responses

## Real Examples from Stress Testing

### 🔴 Failed → ✅ Fixed: Command Timeout
```bash
# FAILED: Timeout after 180s
claude -p "Write a Python function to calculate factorial"

# FIXED: Returned in 4.5s
claude -p "What is a Python function that calculates factorial?"
```

### 🔴 Failed → ✅ Fixed: Execution Confusion
```bash
# FAILED: "Execution error" 
claude -p "Implement recursion with a Python example"

# FIXED: Clear explanation returned
claude -p "What is recursion in programming? Provide an explanation (not code execution) with a Python example."
```

### 🔴 Failed → ✅ Fixed: Creation Ambiguity
```bash
# FAILED: Attempted file creation, hung
claude -p "Create a todo list application"

# FIXED: Returned architecture description
claude -p "What is the architecture for a todo list application?"
```

## Additional Fragility Patterns

### 1. Multi-Step Instructions
**❌ Claude CLI Cannot Handle:**
```bash
claude -p "First analyze this code, then refactor it, then write tests"
# Hangs trying to coordinate multiple actions
```

**✅ Break Into Separate Calls:**
```bash
claude -p "What is an analysis of this code?"
claude -p "What is a refactored version of this code?"
claude -p "What are unit tests for this code?"
```

### 2. Interactive Patterns
**❌ Never Use:**
- "Guide me through..."
- "Help me write..."
- "Ask me about..."

These assume bidirectional communication that Claude CLI cannot provide.

### 3. Tool Usage Assumptions
**❌ Avoid:**
```bash
claude -p "Use MCP tools to search GitHub"
# Tools may not be available or cause hangs
```

**✅ Direct Questions:**
```bash
claude -p "What are examples of Python web scrapers?"
```

## Critical: Claude CLI Tool Limitations

### Tools NOT Available in Claude CLI
Unlike the web interface, Claude CLI instances do **NOT** have access to:

**❌ Productivity Tools:**
- `Task` tool - Cannot use task management
- `TodoRead`/`TodoWrite` - No todo list functionality
- Built-in workflow management tools

**❌ UI/Interactive Features:**
- File upload/download via drag & drop
- Image analysis via direct upload
- Interactive buttons or elements
- Session/thread management UI

**❌ Rich Formatting:**
- Rendered markdown tables
- Syntax-highlighted code blocks (only raw text)
- Inline images or graphics
- Formatted output display

### What Claude CLI CAN Do

**✅ Code/File Operations:**
- Direct file editing and creation
- Reading project files
- Filesystem navigation

**✅ Shell Integration:**
- Execute terminal commands
- Git operations
- Command chaining

**✅ MCP Tools (automatically detected):**
- cc_executor automatically finds and uses `.mcp.json`
- Searches: current dir, `~/.claude/claude_code/`, `~/`
- Available tools depend on your MCP configuration
- Common tools: perplexity-ask, github, ripgrep, etc.

### Implications for Prompts

**❌ Never write prompts that assume:**
```bash
# These will fail - tools not available
claude -p "Use the Task tool to break this down"
claude -p "Add this to your todo list"
claude -p "Create a task list for this project"
```

**✅ Instead, ask for the output directly:**
```bash
# Work around missing tools
claude -p "What are the steps to implement this feature?"
claude -p "What is a task breakdown for this project?"
claude -p "What should be the implementation order?"
```

## Critical Flags for Non-Interactive Use

When using Claude CLI programmatically (in cc_executor):

```bash
claude -p "Your prompt" \
  --dangerously-skip-permissions \   # Skips interactive confirmations
  --mcp-config .mcp.json            # Only if MCP tools needed
  # Note: --output-format and --allowedTools may not be valid flags
```

**Important:** The exact flags depend on your Claude CLI version. Always check with `claude --help`.

## The Golden Rule

> **If you can't run it successfully in your terminal, it won't work in cc_executor.**

Always test prompts manually first:
```bash
timeout 180 claude -p "Your prompt here" --output-format stream-json
```

## Why This Matters for cc_executor

1. **Task Reliability**: Using correct prompt format ensures tasks complete
2. **Timeout Prevention**: Question format avoids 180s+ timeouts
3. **Predictable Output**: Questions get explanations, not execution attempts
4. **Error Recovery**: Clearer failures when things go wrong

## Quick Reference: Verb Transformation

| Imperative (Fails) | Question (Works) |
|-------------------|------------------|
| Write... | What is a ... that...? |
| Create... | What is a ... for...? |
| Generate... | What are ... that...? |
| Build... | What is the architecture for...? |
| Implement... | What is an implementation of...? |
| Make... | What is a way to make...? |
| Design... | What is a design for...? |
| Develop... | What is a development approach for...? |

## Testing Checklist

Before using any prompt in cc_executor:

- [ ] Phrase as a question, not a command
- [ ] Test manually with timeout
- [ ] Verify response is appropriate
- [ ] No "Execution error" messages
- [ ] Response time < 180s
- [ ] Add safety flags for programmatic use
- [ ] Don't assume Task/Todo tools are available
- [ ] Don't rely on UI features or rich formatting

## Summary

Claude CLI is powerful but fragile. Unlike the main Claude interface which can handle ambiguity gracefully, Claude CLI:
1. Needs explicit, unambiguous question-format prompts
2. Lacks access to productivity tools (Task, Todo, etc.)
3. Cannot use UI/interactive features
4. Is designed for code automation, not general productivity

This isn't a bug—it's a fundamental characteristic of how the CLI is designed for programmatic use rather than interactive sessions.

By following these patterns and understanding the limitations, we can achieve near-100% success rates with Claude CLI in automated environments like cc_executor.