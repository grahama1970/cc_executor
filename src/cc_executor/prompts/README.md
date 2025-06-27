# CC-Executor Prompts Index

This directory contains self-improving prompts and their supporting code for the CC-Executor system.

## 🎯 Self-Improving Prompts

### 1. **haiku_generator_20.md**
- **Purpose**: Generate 20 haikus using Claude via WebSocket MCP
- **Status**: Success ratio 5:0 (needs 10:1 to graduate)
- **Uses**: `websocket_orchestrator.py`
- **Patterns**: Looks for "haiku", "nature", "tree", "wind", "water", "sky", "mountain"

### 2. **redis_task_timing.md**
- **Purpose**: Estimate task complexity and track execution history in Redis
- **Status**: Initial implementation (0:0)
- **Features**:
  - Classifies commands by category, complexity, and question type
  - Stores execution history in Redis
  - Finds similar tasks for better estimates
  - Handles word numbers (e.g., "twenty haikus")

### 3. **hallucination_checker.md**
- **Purpose**: Verify that claimed executions actually happened
- **Status**: Initial implementation (0:0)
- **Patterns**: Searches for markers in transcript files
- **Usage**: Include verification patterns after every significant task

## 🔧 Supporting Code

### 1. **websocket_orchestrator.py**
- Orchestrates prompt execution via WebSocket MCP
- Integrates with Redis for adaptive timeouts
- Monitors execution in real-time
- Cancels on errors or timeouts

### 2. **redis_task_timing.py**
- Auto-extracted from `redis_task_timing.md`
- Provides `RedisTaskTimer` class
- Used by orchestrator for complexity estimation

## 📊 Integration Flow

```
haiku_generator_20.md
    ↓ uses
websocket_orchestrator.py
    ↓ imports
redis_task_timing.py
    ↓ stores/retrieves
Redis (execution history)
    
All prompts can use:
    ↓
hallucination_checker.md
    ↓ verifies in
~/.claude/projects/*/transcripts
```

## 🚀 Quick Start

1. **Run a self-improving prompt**:
   ```bash
   python src/cc_executor/prompts/websocket_orchestrator.py haiku20
   ```

2. **Verify Redis timing**:
   ```bash
   python src/cc_executor/prompts/redis_task_timing.py
   ```

3. **Check for hallucinations**:
   - Every prompt should include unique markers
   - Verify markers exist in transcripts
   - See `hallucination_checker.md` for patterns

## 📈 Graduation Criteria

Prompts graduate from `.md` to `.py` when they achieve:
- 10:1 success ratio
- All recovery tests pass
- No manual interventions required
- Consistent execution times

## 🔍 Pattern Dependencies

### haiku_generator_20.md
- Must output: haikus about nature
- Must include: nature keywords
- Format: 5-7-5 syllables
- No code blocks

### redis_task_timing.md
- Redis must be running
- Uses keys: `cc_executor:times:{category}:{task}:*`
- Falls back gracefully if Redis unavailable

### hallucination_checker.md
- Requires: Unique markers in output
- Searches: `~/.claude/projects/*/` for transcripts
- Returns: ✅ VERIFIED or ❌ HALLUCINATED