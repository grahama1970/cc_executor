# CC-Executor Context — CLAUDE.md

> **Project-specific guidelines for CC-Executor development**

## 🎮 GAMIFICATION RULES

**MANDATORY FOR ALL PROMPTS:**
1. Start with metrics header: Success/Failure/Total/Last Updated/Ratio
2. Track EVERY execution (success or failure)
3. Update metrics immediately after execution
4. Achieve 10:1 success ratio to graduate
5. If graduated file fails, reset to 0:0

**PROMPT STRUCTURE:**
```markdown
# [Module Name]

## 🎮 GAMIFICATION METRICS
- **Success**: 0
- **Failure**: 0
- **Total Executions**: 0
- **Last Updated**: YYYY-MM-DD
- **Success Ratio**: N/A (need 10:1 to graduate)

## Purpose
[What this module does]

## Code
```python
# Module code here
```

## Usage
[How to test this module]
```

## 📁 PROJECT STRUCTURE
```
src/cc_executor/setup/
├── prompts/              # Markdown prompts (must reach 10:1)
│   ├── orchestrator/     # Main setup coordinator
│   ├── container/        # Container management
│   ├── docker/          # Docker building
│   ├── api/             # API generation
│   ├── testing/         # Test functions
│   └── monitoring/      # Metrics & verification
├── generated/           # Files created by prompts
└── graduated/           # Prompts that reached 10:1
```

## 🚀 EXECUTION PATTERN
```bash
# Extract and run any prompt
sed -n '/^```python$/,/^```$/p' prompts/[category]/[module].md | sed '1d;$d' > temp.py && python temp.py; rm -f temp.py
```

## ✅ VERIFICATION
- Every execution must be verifiable in transcripts
- Use markers like CC_EXECUTOR_SETUP_YYYYMMDD_HHMMSS
- Check with: `rg "MARKER" ~/.claude/projects/*/*.jsonl`

## 🚫 FORBIDDEN
- Creating Python files directly (must start as prompts)
- Claiming success without verification
- Forgetting to update metrics
- Hallucinating results

---

*Remember: The gamification system exists because of reliability issues. Be meticulous.*
