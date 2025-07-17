# CC Executor Context

## Project Type
MCP (Model Context Protocol) services and tools for Claude Code integration

## Critical Constraints

1. **Subprocess Tool Architecture**: 
   - Tools in `src/cc_executor/tools/*.py` are CLI scripts that parse `sys.argv`
   - They CANNOT be converted to importable modules
   - Subprocess execution is REQUIRED, not a performance bug

2. **FastMCP Parameter Limitations**:
   - FastMCP has validation bugs with `Dict[str, Any]` and `List[str]` parameters
   - All complex parameters MUST be JSON strings
   - Example: `async def query(data: str)` not `async def query(data: Dict)`

3. **Backward Compatibility**:
   - Used by production Claude Code instances
   - Breaking changes are forbidden
   - Add warnings, not errors, for deprecated patterns
   - Keep default values even if insecure (with warnings)

4. **File Organization Rules**:
   - Never create `*_optimized.py`, `*_refactored.py`, or similar variants
   - Modify files in place
   - Don't create new directories for refactoring

5. **Error Handling Requirements**:
   - MCP tools must ALWAYS return valid JSON
   - Never let exceptions crash the MCP server
   - Defensive programming is mandatory

## Intentional Design Decisions

- **Subprocess Overhead**: Acceptable trade-off for reliability and isolation
- **Embedded HTML**: Keeps deployment simple (single file)
- **Default Passwords**: Balance between security and developer experience
- **Monolithic Classes**: If it works reliably, don't split it
- **Global Variables in Tools**: Required for script-style execution
- **Synchronous Operations**: Some tools must remain sync for compatibility

## What NOT to "Fix"

1. Don't suggest converting subprocess tools to direct imports
2. Don't split embedded HTML templates into separate files  
3. Don't remove defaults that would break existing deployments
4. Don't add type hints that FastMCP can't handle (Dict, List params)
5. Don't create "clean" abstractions that add complexity without benefit

## Performance Expectations

- Subprocess spawn time: 200-500ms is normal and acceptable
- Memory usage: Not a constraint
- Startup time: Not critical for MCP tools
- Concurrency: Handled by Claude Code, not our concern

## Integration Points

- Called by Claude Code via MCP protocol
- Must work with `uv run --script` execution pattern
- WebSocket server on port 8003/8004
- Returns JSON-RPC 2.0 formatted responses

## Security Notes

- Default credentials are for development only
- Production deployments should set environment variables
- All user inputs must be sanitized before subprocess execution

## Testing Requirements

- Manual testing with actual Claude Code is required
- Unit tests may not catch MCP integration issues
- Subprocess behavior differs in test vs production environments

---
**Remember**: This codebase prioritizes "working reliably in production" over "clean code principles".