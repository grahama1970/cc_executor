# LESSONS_LEARNED.md - MCP System Knowledge Base

> **PURPOSE**: Document crucial learnings from using MCP tools that supplement the QUICK_GUIDE.md
> **UPDATED**: 2025-07-20

## 1. Solution Validation Best Practices

### ImportError Resolution Pattern
**Learning**: When validating stored solutions for ImportErrors, follow a systematic approach:

1. **Query Structure**: Use OUTBOUND traversal from errors_and_failures to find connected solutions
   ```aql
   FOR error IN errors_and_failures
     FILTER error.resolved == true
     LET solution = (
       FOR v IN 1..1 OUTBOUND error._id error_causality
         FILTER v.fix_description != null
         RETURN v
     )[0]
     RETURN {error: error, solution: solution}
   ```

2. **Outcome Tracking**: Always track solution outcomes in `solution_outcomes` collection with:
   - `solution_id`: Reference to the fix
   - `error_id`: Reference to the original error
   - `outcome`: "success" or "failure"
   - `success_score`: 0.0 to 1.0
   - `time_to_fix_seconds`: Actual time taken
   - `validation_id`: Reference to the validation log entry

3. **Metrics Calculation**: Use COLLECT with INTO for grouping and counting:
   ```aql
   FOR error IN errors_and_failures
     LET pattern = REGEX_REPLACE(error.message, "'[^']+'", "'MODULE'")
     COLLECT error_pattern = pattern INTO group
     LET total = LENGTH(group)
     LET resolved = LENGTH(FOR e IN group FILTER e.error.resolved == true RETURN 1)
     RETURN {pattern: error_pattern, resolution_rate: resolved / total}
   ```

**Key Insight**: Package installation solutions (`uv add`) have shown 100% success rate for ImportError fixes.

## 2. AQL Query Patterns

### Common Pitfall: AGGREGATE with COLLECT
**Error**: Cannot use AGGREGATE keyword directly after COLLECT
```aql
// WRONG L
COLLECT pattern = error.type
AGGREGATE count = COUNT(1)  // Syntax error!

// CORRECT 
COLLECT pattern = error.type INTO group
LET count = LENGTH(group)
```

### Pattern Matching for Error Messages
**Learning**: Use REGEX_REPLACE to normalize error messages for pattern analysis:
```aql
LET pattern = REGEX_REPLACE(error.message, "'[^']+'", "'MODULE'")
// Converts "No module named 'pandas'" ’ "No module named 'MODULE'"
```

## 3. Boolean Parameters in MCP Tools

**Issue**: Direct boolean parameters often fail validation in MCP tools
**Solution**: Pass booleans inside metadata JSON strings:
```python
# WRONG L
await mcp__arango_tools__insert(
    resolved=True  # Validation error!
)

# CORRECT 
await mcp__arango_tools__insert(
    metadata='{"resolved": true}'
)
```

## 4. Edge Creation Best Practices

**Learning**: When linking errors to solutions across collections:
1. Ensure both documents exist first
2. Use consistent collection references (e.g., `errors_and_failures/123` not `log_events/123`)
3. Include metadata for tracking:
   ```python
   await mcp__arango_tools__edge(
       from_id="errors_and_failures/123",
       to_id="log_events/456",
       collection="error_causality",
       relationship_type="fixed_by",
       metadata='{"fix_time_minutes": 5, "confidence": 0.95}'
   )
   ```

## 5. Collection Relationships

**Key Collections for Solution Tracking**:
- `errors_and_failures`: Central error registry
- `log_events`: All system events including fixes
- `solution_outcomes`: Tracks effectiveness of applied solutions
- `lessons_learned`: Aggregated insights from solution validation
- `error_causality`: Edge collection linking errors to fixes

**Graph Traversal**: Use `error_causality` edges to navigate between:
- Error ’ Solution (OUTBOUND)
- Solution ’ Errors it fixed (INBOUND)

## 6. Performance Considerations

**Learning**: When calculating metrics across large datasets:
1. Use LIMIT for initial testing
2. Pre-filter with indexes where possible
3. Aggregate in AQL rather than post-processing
4. Consider caching frequent metric calculations in `lessons_learned`

---

**Remember**: These lessons supplement the QUICK_GUIDE.md. Always check both documents when executing complex scenarios.