# Archived Files

This directory contains files that have been superseded by newer implementations but are kept for historical reference.

## mcp_arango_crud.py.archived_20250716

**Archived Date**: 2025-07-16
**Reason**: Superseded by mcp_arango_tools.py
**Original Location**: src/cc_executor/servers/mcp_arango_crud.py

### Why Archived
- Limited functionality (only 2 tools: query and log)
- All functionality is available in mcp_arango_tools.py
- mcp_arango_tools.py provides:
  - Full CRUD operations (insert, upsert, update, delete, query, get)
  - Edge creation and management
  - Schema introspection
  - Graph analytics
  - Glossary management
  - Learning system integration
  - Advanced search capabilities
  - Better error handling

### Original Functionality
The archived file provided:
1. `query` tool - Natural language or AQL queries
2. `log` tool - Simple logging to log_events collection

Both of these are fully replaced by:
1. `execute_aql` / `query` in mcp_arango_tools.py
2. `insert` in mcp_arango_tools.py (with better validation)

### Migration Guide
If you were using mcp_arango_crud.py:
- Replace `mcp__arango-crud__query` with `mcp__arango-tools__query` or `mcp__arango-tools__execute_aql`
- Replace `mcp__arango-crud__log` with `mcp__arango-tools__insert`