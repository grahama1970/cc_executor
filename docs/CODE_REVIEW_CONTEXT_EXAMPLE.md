# How Context Would Have Fixed the Code Review

## Original Review Command (Missing Context)
```bash
/review-two-phase src/cc_executor/servers/mcp_*.py
```

### Results:
- ❌ Suggested removing subprocess execution (would break everything)
- ❌ Suggested using Dict/List parameters (would fail with FastMCP)  
- ❌ Suggested removing default password (would break existing deployments)
- ❌ Suggested major refactoring (high risk, no real benefit)

## Improved Review Command (With Context)
```bash
/review-with-context src/cc_executor/servers/mcp_*.py \
  --context "CC Executor MCP Services. CRITICAL: 1) Tools are CLI scripts using subprocess - this is REQUIRED 2) FastMCP needs JSON strings not Dict/List 3) Backward compatibility mandatory 4) No duplicate files 5) Defensive errors only. DESIGN: Subprocess overhead acceptable. Embedded HTML intentional."
```

### Expected Results:
- ✅ Security: "Add warning for default password while maintaining compatibility"
- ✅ Performance: "Subprocess overhead noted as acceptable per context"
- ✅ Architecture: "Monolithic class works reliably - no change recommended"
- ✅ Templates: "Embedded HTML noted as intentional design decision"

## Key Difference

Without context, the reviewers applied general Python best practices that were **wrong for this specific domain**.

With context, they would understand:
1. **The "inefficiencies" are requirements**
2. **The "anti-patterns" are MCP constraints**
3. **Backward compatibility trumps clean code**
4. **Working code > Perfect code**

## Lesson Learned

**Context is not optional** - it's the difference between helpful and harmful code reviews. The same code can be:
- ❌ "Wrong" by general standards
- ✅ "Right" for specific constraints

Always provide domain context to get useful reviews!