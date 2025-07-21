# Arango Tools MCP Usage Task List

These tasks will naturally prompt Claude to use the arango-tools MCP in various scenarios, including error cases.

## Task 1: Database Health Check
"I need to check if my logger database is set up correctly. Can you show me what collections and graphs are available in the ArangoDB database?"

*This prompts: `mcp__arango-tools__schema()`*

---

## Task 2: Find Recent Errors
"Can you search for any ERROR level logs from the last 24 hours? I'm trying to debug some issues."

*This prompts: `mcp__arango-tools__query()` with timestamp filtering*

---

## Task 3: Track Script Execution
"I just ran a script called 'data_migration.py'. Can you log that it started successfully with execution ID 'migrate_20240118_1234'?"

*This prompts: `mcp__arango-tools__insert()` with script tracking*

---

## Task 4: Debug Module Import Error
"My script just failed with 'ModuleNotFoundError: No module named requests'. Can you log this error and mark it as unresolved?"

*This prompts: `mcp__arango-tools__insert()` with error details*

---

## Task 5: Link Error to Solution
"I fixed the requests error by running 'uv add requests'. Can you create a relationship showing that this fix resolved the previous error?"

*This prompts: `mcp__arango-tools__edge()` to link error and solution*

---

## Task 6: Search Non-Existent Data
"Can you find all logs from a script called 'totally_fake_script.py'? I think it might have run last week."

*This prompts: `mcp__arango-tools__query()` that returns empty results*

---

## Task 7: Bad Query Syntax
"I need to search for logs but I forgot the AQL syntax. Can you try: 'GET ALL FROM log_events WHERE level = ERROR'?"

*This prompts: `mcp__arango-tools__query()` with invalid AQL, triggering error recovery*

---

## Task 8: Update Script Status
"The 'data_migration.py' script with execution ID 'migrate_20240118_1234' just finished. Can you update its status to 'completed' with duration of 45 seconds? Create the record if it doesn't exist."

*This prompts: `mcp__arango-tools__upsert()`*

---

## Task 9: Complex Pattern Search
"I'm seeing repeated 'ConnectionTimeout' errors. Can you find all similar errors and check if any were resolved? I want to know the fix patterns."

*This prompts: Complex `mcp__arango-tools__query()` with graph traversal*

---

## Task 10: Wrong Database Query
"Can you check what's in the 'production_metrics' database? I think we might have some data there."

*This prompts: Attempting to query non-existent database, requiring error handling*

---

## Task 11: Performance Analysis
"How many tool executions happened in the last hour? Group them by tool name and show me which tools are used most."

*This prompts: Aggregation query with `mcp__arango-tools__query()`*

---

## Task 12: Circular Reference Check
"I'm worried about circular dependencies. Can you trace the graph relationships starting from any error that was marked as 'fixed_by' something that itself had errors?"

*This prompts: Complex graph traversal that might find cycles*

---

## Task 13: Bulk Insert Test
"I need to import 50 log entries from my test run. Here's the first one: {message: 'Test 1', level: 'DEBUG'}. Can you insert them all with timestamps 1 second apart?"

*This prompts: Multiple `mcp__arango-tools__insert()` calls*

---

## Task 14: Research Unknown Error
"I got this weird ArangoDB error: 'collection not found: agent_memories'. What does this mean and how do I fix it?"

*This prompts: Using perplexity-ask along with arango-tools to understand and fix the issue*

---

## Task 15: View Search Test
"Can you search for any logs that mention 'memory' or 'RAM' using the full-text search capability?"

*This prompts: `mcp__arango-tools__query()` using search views*

---

## Error Recovery Scenarios

### Scenario A: Connection Issues
"The database seems slow. Can you run a simple health check query and tell me the response time?"

*If connection fails, this prompts troubleshooting with perplexity-ask*

### Scenario B: Invalid Document Structure  
"Log this error but use 'priority' instead of 'level': {message: 'Test', priority: 'HIGH'}"

*This prompts handling of invalid field names*

### Scenario C: Permission Errors
"Can you drop the entire log_events collection and recreate it?"

*This likely triggers permission errors to handle*

---

## Multi-Step Workflows

### Workflow 1: Error Resolution Pipeline
1. "Find the most recent ModuleNotFoundError"
2. "Check if it has any linked solutions"
3. "If not, research a solution using perplexity"
4. "Create a solution document and link it"
5. "Update the error as resolved"

### Workflow 2: Performance Investigation
1. "Show me the slowest tool executions from today"
2. "For each slow execution, find any associated errors"
3. "Create a summary of performance bottlenecks"
4. "Store this analysis as an insight"

---

## Expected Behaviors

When given these tasks, Claude should:
1. ✅ Use the appropriate arango-tools function
2. ✅ Handle empty results gracefully  
3. ✅ Recognize and recover from errors
4. ✅ Use perplexity-ask when confused
5. ✅ Chain operations for complex workflows
6. ✅ Provide clear feedback on what happened

## Usage Instructions

Simply copy any task from this list and paste it to Claude. The natural language prompts will cause Claude to:
- Interpret the need
- Select the right tool
- Execute the operation
- Handle any errors
- Report the results

This is more natural than explicit tool calls and tests real-world usage patterns.