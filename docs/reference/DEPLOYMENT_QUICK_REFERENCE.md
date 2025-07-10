# Agent Deployment Quick Reference Card

## One-Command Validation
```bash
python scripts/validate_deployment.py
```

## Phase Checklist

### ☐ Phase 1: UUID4 Pattern (ALL Python Scripts)
```bash
find src -name "*.py" | xargs -I {} python {} 
# Every script must print: "Execution verified: {uuid}"
```

### ☐ Phase 2: Reasonableness Check
```bash
ls tmp/responses/*_response_*.json
# Every file must have real data, not mocks
```

### ☐ Phase 3: MCP Tools (ALL 70+)
```bash
python scripts/test_all_mcp_tools.py
# 100% pass rate required
```

### ☐ Phase 4: Code Review (3 Rounds)
```bash
# Round 1
echo "Review request" > docs/tasks/reviewer/incoming/round1_request.md
# Wait for: docs/tasks/executor/incoming/round1_fixes.json

# Round 2 (after fixes)
echo "Review request" > docs/tasks/reviewer/incoming/round2_request.md
# Wait for: docs/tasks/executor/incoming/round2_fixes.json

# Round 3 (final)
echo "Review request" > docs/tasks/reviewer/incoming/round3_request.md
# Wait for: "APPROVED FOR DEPLOYMENT"
```

### ☐ Phase 5: Final Validation
```bash
rm -rf tmp/responses/*
python scripts/run_comprehensive_assessment.py
# Must show 100% pass rate
```

## Critical Rules

1. **UUID4 = TRUTH**: No UUID4 = Hallucination
2. **BOTH Locations**: Console AND JSON file
3. **Real Data Only**: No mocks, fixtures, or fake data
4. **All Tools Pass**: Test all 70+ MCP tools
5. **3 Full Reviews**: Not 1, not 2, exactly 3
6. **o3 Reviews**: Not self-review, o3 model does it
7. **100% Required**: No partial passes

## File Naming
```
{script_name}_response_{YYYYMMDD_HHMMSS}.json
```

## Directory Flow
```
docs/tasks/reviewer/incoming/ → o3 → docs/tasks/executor/incoming/
```

## Anti-Hallucination Pattern
```python
# At the VERY END of execution
execution_id = str(uuid.uuid4())
print(f"\nExecution verified: {execution_id}")

# Also save to JSON
data['execution_id'] = execution_id
```

## Emergency Debug
```bash
# Check transcript for UUID
rg "Execution verified" ~/.claude/projects/-*/*.jsonl | tail -5

# Verify no hallucination
rg "YOUR_UUID_HERE" ~/.claude/projects/-*/*.jsonl
```

---
**REMEMBER**: We check EVERYTHING. No shortcuts. No lies. UUID4 or death.