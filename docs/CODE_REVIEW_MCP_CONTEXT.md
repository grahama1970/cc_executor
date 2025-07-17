# MCP-Specific Context for Code Reviews

When reviewing code for MCP (Model Context Protocol) servers, please consider these critical constraints:

## 1. MCP Tools Are Not Regular Python Modules

**Context:** MCP tools in this codebase are designed as standalone scripts that:
- Parse command-line arguments via `sys.argv[1]`
- Have `if __name__ == "__main__"` blocks
- Are executed via `uv run` in subprocesses

**Why This Matters:** 
- Direct imports won't work without rewriting all tools
- The "inefficient" subprocess approach is intentional and required
- Performance optimization here would break functionality

**Review Guidance:** Don't suggest converting script-based tools to importable modules unless you're prepared to rewrite the entire tool ecosystem.

## 2. FastMCP Has Specific Limitations

**Context:** FastMCP doesn't properly validate dictionary/list parameters.

**Required Pattern:**
```python
# ❌ WRONG - Will fail
async def query(data: Dict[str, Any]) -> str:

# ✅ CORRECT - Use JSON strings
async def query(data: str) -> str:  # data is JSON string
    parsed = json.loads(data)
```

**Review Guidance:** Any suggestion to use typed dictionaries or lists as parameters will break the MCP server.

## 3. Backward Compatibility Is Critical

**Context:** MCP servers are used by Claude Code users who:
- May not have latest dependencies
- Expect stable APIs
- Often use default configurations

**Example:** Removing default passwords breaks existing deployments. Better to warn than crash.

**Review Guidance:** Suggest deprecation warnings rather than breaking changes.

## 4. File Organization Rules

**Context:** 
- DO NOT create new files with similar names (e.g., `tool_optimized.py`)
- DO NOT create new directories for refactoring
- Modify existing files in place if changes are needed

**Why:** Duplicate files create confusion and maintenance burden.

## 5. HTML Templates in Code Are Acceptable

**Context:** For visualization tools, embedded HTML templates:
- Keep everything in one file
- Reduce deployment complexity
- Work reliably across environments

**Review Guidance:** Unless templates are >1000 lines, leave them embedded.

## 6. Error Handling Must Be Defensive

**Context:** MCP tools run in subprocess isolation and must:
- Never crash the MCP server
- Always return valid JSON
- Log warnings rather than raise exceptions for non-critical issues

## Recommended Review Checklist for MCP Code:

1. **Will this break existing MCP integrations?**
2. **Does this require changes to how Claude calls the tools?**
3. **Will this work with FastMCP's limitations?**
4. **Is backward compatibility maintained?**
5. **Are we solving a real problem or just making "clean code"?**

## Example Review Feedback Template:

```
### Security Issues:
✅ Hard-coded credentials - Real issue, but maintain backward compatibility

### Performance:
⚠️ Subprocess spawning - Intentional design for MCP tools, not a bug

### Code Organization:
💭 Consider refactoring only if:
- All existing APIs remain identical
- Extensive testing confirms no behavior changes
- The current code is actually causing problems

### General Principle:
"Working code > Clean code" for production MCP servers
```

## What Reviewers Should Know About MCP:

1. **MCP is a protocol** for AI assistants to interact with tools
2. **Stability is paramount** - Breaking changes affect many users
3. **The "inefficiencies" are often intentional** design choices
4. **Test with actual Claude Code** before suggesting major changes

## Red Flags in Code Reviews:

- "Just refactor to use imports" - Probably breaks MCP tools
- "Use proper typing" - FastMCP doesn't support it
- "Split into multiple files" - Creates maintenance burden
- "Remove defaults" - Breaks existing deployments
- "Make it async all the way" - Some tools must be sync

Remember: Code that looks "wrong" to a traditional Python reviewer might be exactly right for MCP constraints.