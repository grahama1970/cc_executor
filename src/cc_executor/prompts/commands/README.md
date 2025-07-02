# Research Collaborator Commands

## Final Structure

After extensive testing and iteration, we have consolidated to two essential files:

### 1. research-collaborator.md
The complete, production-ready implementation that:
- Reads and applies CLAUDE_CODE_PROMPT_RULES.md
- Transforms all queries to safe "What is..." format
- Uses BOTH perplexity-ask (MCP) and gemini-cli concurrently
- Supports multi-turn conversations
- Includes UUID verification
- Generates comprehensive reports with prettified JSON

### 2. research-collaborator-template.md
A simpler template for cases where you want to:
- Separate the research question from the prompt
- Use with custom question files
- Focus on single-turn research

## Archived Versions

The following versions were archived to `archive/` as they were iterations leading to the final solution:
- research-collaborator-v8.md - Early attempt
- research-collaborator-v12.md - Simplified but incomplete
- research-collaborator-final.md - Missing multi-turn support
- research-collaborator-multi-turn.md - Missing query transformation
- research-collaborator-optimized.md - Over-engineered
- research-collaborator-original.md - The very first version

## Usage

For most use cases, use the main version:
```bash
REQUEST="What is the best Python async pattern?" \
bash src/cc_executor/prompts/scripts/run_research_collaborator.sh
```

For separated questions, use the template version:
```bash
PROMPT_FILE=research-collaborator-template.md \
QUESTION_FILE=/tmp/my_question.md \
bash src/cc_executor/prompts/scripts/run_research_collaborator_v2.sh
```

## Key Lessons

1. **Query Format Matters**: Claude CLI hangs on commands, works with questions
2. **Concurrent Execution**: Both tools must run simultaneously via asyncio
3. **UUID Verification**: Essential for proving execution happened
4. **Rule Application**: Must transform queries according to CLAUDE_CODE_PROMPT_RULES.md
5. **Keep It Simple**: Too many versions create confusion

The final `research-collaborator.md` incorporates all these lessons into a working solution.