# MCP Tools Availability Status

**Date**: 2025-01-17  
**Tested By**: Claude Code  

## Summary

After removing the conflicting local `.mcp.json` file, I can confirm which MCP tools are actually available in Claude's environment.

## Available MCP Servers (Working)

### ✅ cc-execute
- `mcp__cc-execute__get_executor_status` - Returns service health
- `mcp__cc-execute__execute_task` - Execute complex tasks
- `mcp__cc-execute__verify_execution` - Verify execution results
- Resources: executor-logs, executor-config

### ✅ perplexity-ask
- `mcp__perplexity-ask__perplexity_ask` - Get real-time information with citations

### ✅ github
- `mcp__github__search_repositories` - Search GitHub repos
- `mcp__github__create_repository` - Create new repositories
- All other GitHub operations (issues, PRs, etc.)

### ✅ ripgrep
- `mcp__ripgrep__search` - Search files with patterns
- `mcp__ripgrep__advanced-search` - Advanced search options
- `mcp__ripgrep__count-matches` - Count pattern matches

### ✅ puppeteer
- `mcp__puppeteer__puppeteer_navigate` - Navigate to URLs
- `mcp__puppeteer__puppeteer_screenshot` - Take screenshots
- Resources: Browser console logs

### ✅ arxiv-minimal
- `mcp__arxiv-minimal__test_tool` - Simple test function
- `mcp__arxiv-minimal__pdf_learning` - PDF annotation extraction

### ✅ brave-search
- `mcp__brave-search__brave_web_search` - Web search
- `mcp__brave-search__brave_local_search` - Local business search

### ✅ resume-* servers (8 servers)
- All resume-related MCP servers are available
- Including health-check, litellm, pdf-extractor, etc.

### ✅ logger-tools (Partial)
- `mcp__logger-tools__inspect_arangodb_schema` - Available but has execution errors
- Other logger tools appear to have issues

## Unavailable MCP Servers (Not Registered)

### ❌ arango-tools
- Despite being configured in `.mcp.json`, not available as `mcp__arango-tools__*`
- Server is running (verified with ps aux) but not registered with Claude

### ❌ d3-visualizer
- Not available as `mcp__d3-visualizer__*`

### ❌ tool-journey
- Not available as `mcp__tool-journey__*`

### ❌ tool-sequence-optimizer
- Not available as `mcp__tool-sequence-optimizer__*`

### ❌ kilocode-review
- Not available as `mcp__kilocode-review__*`

### ❌ arxiv (full server)
- The full arxiv server tools are not available
- Only arxiv-minimal is working

## Root Cause Analysis

1. **Configuration Location**: The global MCP configuration at `/home/graham/.claude/claude_code/.mcp.json` is the only one that matters. Local `.mcp.json` files cause conflicts.

2. **Server Registration**: Some servers are configured and running (processes exist) but aren't registered with Claude's MCP tool registry. This suggests:
   - Possible initialization failures
   - Protocol mismatch issues
   - FastMCP vs raw MCP SDK differences

3. **Partial Availability**: Some servers like logger-tools are partially available (tools can be called but fail during execution).

## Recommendations

1. **Focus on Available Tools**: Use the working MCP tools (cc-execute, perplexity-ask, github, etc.) for immediate needs.

2. **Debug Registration Issues**: The unavailable servers need investigation into why they're not registering properly with Claude despite being configured.

3. **Use Alternative Methods**: For unavailable tools like arango-tools, consider:
   - Direct Python script execution
   - Using cc-execute to run the scripts
   - Creating wrapper scripts

4. **Verify Server Startup**: Check server logs for initialization errors that might prevent registration.

## Next Steps

1. Check MCP server logs for registration failures
2. Verify FastMCP versions and compatibility
3. Consider restarting Claude to reload MCP configurations
4. Test individual server startup outside of Claude environment