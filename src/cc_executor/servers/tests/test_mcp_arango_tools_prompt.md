# MCP Arango Tools Test Task List

This prompt guides systematic testing of all MCP tools in the arango-tools server. Each task includes a realistic usage scenario to verify the tool works correctly.

## Prerequisites

Before starting, ensure:
1. ArangoDB is running on localhost:8529
2. The `script_logs` database exists
3. The arango-tools MCP server is available in Claude

## Task List

### Task 1: Test Schema Tool
**Tool**: `mcp__arango-tools__schema()`

**Scenario**: A new developer joins the team and needs to understand the database structure for the logger agent system.

**Test Steps**:
1. Call the schema tool with no parameters
2. Verify it returns:
   - List of all collections with their types (document/edge)
   - Sample fields for each collection
   - Available views
   - Graph definitions
   - Common query examples

**Expected Outcome**: Complete schema overview of the script_logs database

---

### Task 2: Test Query Tool - Basic Query
**Tool**: `mcp__arango-tools__query(aql, bind_vars)`

**Scenario**: An engineer needs to find the last 5 error logs to debug a production issue.

**Test Steps**:
1. Execute query: `FOR doc IN log_events FILTER doc.level == 'ERROR' SORT doc.timestamp DESC LIMIT 5 RETURN doc`
2. Verify the query executes successfully
3. Check that results are properly formatted

**Expected Outcome**: Returns up to 5 error log entries (or empty array if no errors)

---

### Task 3: Test Query Tool - With Bind Variables
**Tool**: `mcp__arango-tools__query(aql, bind_vars)`

**Scenario**: Search for all logs from a specific script within the last hour.

**Test Steps**:
1. Create bind variables JSON: `{"@collection": "log_events", "script": "test_script.py", "since": "2024-01-18T00:00:00Z"}`
2. Execute query: `FOR doc IN @@collection FILTER doc.script_name == @script AND doc.timestamp >= @since RETURN doc`
3. Verify bind variables are properly applied

**Expected Outcome**: Filtered results based on script name and timestamp

---

### Task 4: Test Insert Tool - Log Event
**Tool**: `mcp__arango-tools__insert(message, level, **kwargs)`

**Scenario**: A monitoring script needs to log a successful health check.

**Test Steps**:
1. Insert a log with:
   - message: "Health check completed successfully"
   - level: "INFO"
   - script_name: "health_monitor.py"
   - execution_id: "health_check_12345"
   - metadata: `{"services_checked": 5, "all_healthy": true}`
2. Verify the document is created with a unique _key
3. Check that timestamp is automatically added

**Expected Outcome**: New log event created with all fields properly stored

---

### Task 5: Test Insert Tool - Error Log
**Tool**: `mcp__arango-tools__insert(message, level, **kwargs)`

**Scenario**: An AI agent encounters an import error and needs to log it for future learning.

**Test Steps**:
1. Insert an error log with:
   - message: "ModuleNotFoundError: No module named 'pandas'"
   - level: "ERROR"
   - error_type: "ModuleNotFoundError"
   - script_name: "data_analyzer.py"
   - resolved: false
   - fix_description: null
2. Save the returned document ID for the next task

**Expected Outcome**: Error log created in errors_and_failures collection

---

### Task 6: Test Edge Tool - Link Error to Fix
**Tool**: `mcp__arango-tools__edge(from_id, to_id, collection, **kwargs)`

**Scenario**: The AI agent fixed the pandas error by installing it, and needs to link the error to its fix.

**Test Steps**:
1. Insert a fix log:
   - message: "Fixed ModuleNotFoundError by running: uv add pandas"
   - level: "INFO"
   - script_name: "data_analyzer.py"
2. Create an edge in error_causality collection:
   - from_id: [error document ID from Task 5]
   - to_id: [fix document ID]
   - relationship_type: "fixed_by"
   - fix_time_minutes: 2
3. Verify the edge is created

**Expected Outcome**: Error and fix are linked in the graph

---

### Task 7: Test Upsert Tool - Update Script Run Status
**Tool**: `mcp__arango-tools__upsert(collection, search, update, create)`

**Scenario**: Track script execution status, updating if exists or creating if new.

**Test Steps**:
1. Upsert a script run:
   - collection: "script_runs"
   - search: `{"script_name": "daily_report.py", "execution_id": "daily_20240118"}`
   - update: `{"status": "completed", "end_time": "2024-01-18T12:00:00Z", "duration_seconds": 45}`
   - create: `{"start_time": "2024-01-18T11:59:15Z"}`
2. Run the same upsert again with status "failed" to test update behavior
3. Verify the document is updated, not duplicated

**Expected Outcome**: Single document that gets updated on subsequent calls

---

### Task 8: Test Complex Graph Query
**Tool**: `mcp__arango-tools__query(aql, bind_vars)`

**Scenario**: Find all errors that were successfully resolved and their fix methods.

**Test Steps**:
1. Execute graph traversal query:
```aql
FOR error IN errors_and_failures
  FILTER error.resolved == true
  FOR v, e IN 1..1 OUTBOUND error error_causality
    FILTER e.relationship_type == "fixed_by"
    RETURN {
      error: error.message,
      error_type: error.error_type,
      fix: v.message,
      time_to_fix: e.fix_time_minutes
    }
```
2. Verify the query returns linked errors and fixes

**Expected Outcome**: List of resolved errors with their corresponding fixes

---

### Task 9: Test Research Integration
**Tool**: `mcp__arango-tools__query(aql, bind_vars)`

**Scenario**: Find patterns in errors to generate learning insights.

**Test Steps**:
1. Query for error patterns:
```aql
FOR doc IN errors_and_failures
  COLLECT error_type = doc.error_type WITH COUNT INTO count
  FILTER count > 1
  SORT count DESC
  RETURN {
    error_type: error_type,
    occurrences: count
  }
```
2. For the most common error type, find all instances
3. Check if any have stored fix_description

**Expected Outcome**: Statistics on error patterns for agent learning

---

### Task 10: Test View Search
**Tool**: `mcp__arango-tools__query(aql, bind_vars)`

**Scenario**: Use the search view to find logs containing specific keywords.

**Test Steps**:
1. Search using the log_search_view:
```aql
FOR doc IN log_search_view
  SEARCH ANALYZER(doc.message IN TOKENS("import error module", "text_en"), "text_en")
  SORT BM25(doc) DESC
  LIMIT 10
  RETURN {
    message: doc.message,
    score: BM25(doc)
  }
```
2. Verify full-text search results

**Expected Outcome**: Relevant logs based on search terms

---

## Verification Checklist

After completing all tasks, verify:
- [ ] All 5 MCP tools are functional (schema, query, insert, edge, upsert)
- [ ] Data persists correctly in collections
- [ ] Graph relationships work as expected
- [ ] Error handling provides helpful suggestions
- [ ] Views enable efficient searching
- [ ] The logger agent can learn from stored data

## Advanced Testing (Optional)

1. **Stress Test**: Insert 100 logs rapidly and verify performance
2. **Graph Traversal**: Follow multi-hop relationships in the claude_agent_observatory graph
3. **Glossary Integration**: Test the glossary term functions (if implemented)
4. **Cache Behavior**: Verify research_cache prevents duplicate lookups

## Success Criteria

The arango-tools MCP server is considered fully functional when:
1. All basic CRUD operations work
2. Graph relationships can be created and queried
3. Complex AQL queries execute successfully
4. Error messages are helpful and actionable
5. The tool integrates smoothly with the logger agent workflow