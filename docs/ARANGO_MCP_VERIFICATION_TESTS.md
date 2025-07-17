# ArangoDB MCP Tools - Verification Test Suite

This document contains comprehensive tests for ALL ArangoDB MCP tools. Each test includes:
- The exact command to run
- Expected output structure
- Unique markers for transcript verification
- Pass/Fail status

## Test Execution Date: 2025-01-16

## 1. Schema Tool Test

### Test 1.1: Get Database Schema
```python
# Command
result = await mcp__arango-tools__schema()

# Expected: JSON with collections, views, graphs
# Marker: SCHEMA_TEST_20250116_1
```

## 2. Query Tool Tests

### Test 2.1: Basic Query
```python
# Command
result = await mcp__arango-tools__query(
    "FOR doc IN log_events LIMIT 3 RETURN doc"
)

# Expected: JSON with success=true and data array
# Marker: QUERY_BASIC_20250116_1
```

### Test 2.2: Query with Bind Variables
```python
# Command
result = await mcp__arango-tools__query(
    "FOR doc IN @@col FILTER doc.level == @level LIMIT 2 RETURN doc",
    {"@col": "log_events", "level": "ERROR"}
)

# Expected: JSON with filtered results
# Marker: QUERY_BIND_20250116_2
```

### Test 2.3: Failed Query with Recovery Suggestions
```python
# Command - Intentionally wrong function
result = await mcp__arango-tools__query(
    "FOR doc IN log_events RETURN FAKE_FUNCTION(doc)"
)

# Expected: Error with use_these_tools suggestions
# Marker: QUERY_FAIL_20250116_3
```

## 3. Natural Language to AQL

### Test 3.1: Convert English to AQL
```python
# Command
result = await mcp__arango-tools__english_to_aql(
    "find recent errors from last hour"
)

# Expected: AQL pattern with bind_vars
# Marker: ENGLISH_AQL_20250116_1
```

## 4. CRUD Operations

### Test 4.1: Insert Document
```python
# Command
result = await mcp__arango-tools__insert(
    message="MCP Test Insert MARKER_INSERT_20250116",
    level="INFO",
    script_name="mcp_test.py",
    execution_id="test_exec_123"
)

# Expected: JSON with success=true and key
# Marker: INSERT_TEST_20250116_1
```

### Test 4.2: Get Document
```python
# Command - Use key from previous insert
result = await mcp__arango-tools__get(
    "log_events",
    "KEY_FROM_INSERT"  # Will use actual key
)

# Expected: Document data
# Marker: GET_TEST_20250116_2
```

### Test 4.3: Update Document
```python
# Command
result = await mcp__arango-tools__update(
    collection="log_events",
    key="KEY_FROM_INSERT",
    fields={
        "resolved": True,
        "resolution": "Test resolution UPDATE_MARKER_20250116"
    }
)

# Expected: Success message
# Marker: UPDATE_TEST_20250116_3
```

### Test 4.4: Upsert Document
```python
# Command
result = await mcp__arango-tools__upsert(
    collection="script_runs",
    search={"script_name": "upsert_test_20250116.py"},
    update={"last_run": "2025-01-16", "run_count": 1},
    create={"first_run": "2025-01-16"}
)

# Expected: Success with upserted document
# Marker: UPSERT_TEST_20250116_4
```

### Test 4.5: Delete Document
```python
# Command
result = await mcp__arango-tools__delete(
    "log_events",
    "KEY_FROM_INSERT"
)

# Expected: Deletion confirmation
# Marker: DELETE_TEST_20250116_5
```

## 5. Edge Operations

### Test 5.1: Create Edge
```python
# Command - First create two documents to link
doc1 = await mcp__arango-tools__insert(
    message="Error document EDGE_TEST_FROM_20250116",
    level="ERROR"
)
doc2 = await mcp__arango-tools__insert(
    message="Fix document EDGE_TEST_TO_20250116",
    level="INFO"
)

# Create edge
result = await mcp__arango-tools__edge(
    from_id=f"log_events/{doc1['key']}",
    to_id=f"log_events/{doc2['key']}",
    collection="error_causality",
    relationship_type="fixed_by",
    fix_time_minutes=15
)

# Expected: Edge creation success
# Marker: EDGE_CREATE_20250116_1
```

## 6. Glossary Operations

### Test 6.1: Add Glossary Term
```python
# Command
result = await mcp__arango-tools__add_glossary_term(
    term="TEST_TERM_20250116",
    definition="A test term for MCP verification",
    category="test",
    examples=["Example usage of TEST_TERM_20250116"],
    tags=["mcp", "test", "verification"]
)

# Expected: Term creation/update success
# Marker: GLOSSARY_ADD_20250116_1
```

### Test 6.2: Link Glossary Terms
```python
# Command - Add second term then link
await mcp__arango-tools__add_glossary_term(
    term="TEST_RELATED_20250116",
    definition="Related test term",
    category="test"
)

result = await mcp__arango-tools__link_glossary_terms(
    from_term="TEST_TERM_20250116",
    to_term="TEST_RELATED_20250116",
    relationship="related_to",
    context="Testing term relationships"
)

# Expected: Relationship created
# Marker: GLOSSARY_LINK_20250116_2
```

### Test 6.3: Link Term to Log
```python
# Command
log_doc = await mcp__arango-tools__insert(
    message="Log with TEST_TERM_20250116 mentioned",
    level="INFO"
)

result = await mcp__arango-tools__link_term_to_log(
    term="TEST_TERM_20250116",
    log_id=log_doc['key'],
    relationship="mentioned_in",
    context="Term appears in log message"
)

# Expected: Term-log link created
# Marker: TERM_LOG_LINK_20250116_3
```

## 7. Complex Query Tests

### Test 7.1: Graph Traversal Query
```python
# Command - Find related items through edges
result = await mcp__arango-tools__query("""
    FOR v, e, p IN 1..2 ANY 'log_events/KEY' error_causality
        RETURN {
            vertex: v._key,
            edge_type: e.relationship_type,
            depth: LENGTH(p.edges)
        }
""", {"KEY": doc1['key']})  # Using key from edge test

# Expected: Graph traversal results
# Marker: GRAPH_QUERY_20250116_1
```

### Test 7.2: Aggregation Query
```python
# Command
result = await mcp__arango-tools__query("""
    FOR doc IN log_events
        FILTER doc.test_marker == @marker
        COLLECT level = doc.level WITH COUNT INTO count
        RETURN {level: level, count: count}
""", {"marker": "20250116"})

# Expected: Aggregated counts
# Marker: AGG_QUERY_20250116_2
```

## 8. Error Recovery Test

### Test 8.1: Trigger Research Suggestions
```python
# Command - Use non-existent collection
result = await mcp__arango-tools__query(
    "FOR doc IN fake_collection_20250116 RETURN doc"
)

# Expected: Error with research_help and recovery_steps
# Should include:
# - use_these_tools with context7 and perplexity suggestions
# - recovery_steps array
# Marker: RECOVERY_TEST_20250116_1
```

## Verification Script

```python
# After running all tests, verify with:
markers = [
    "SCHEMA_TEST_20250116_1",
    "QUERY_BASIC_20250116_1", 
    "QUERY_BIND_20250116_2",
    "QUERY_FAIL_20250116_3",
    "ENGLISH_AQL_20250116_1",
    "INSERT_TEST_20250116_1",
    "GET_TEST_20250116_2",
    "UPDATE_TEST_20250116_3",
    "UPSERT_TEST_20250116_4",
    "DELETE_TEST_20250116_5",
    "EDGE_CREATE_20250116_1",
    "GLOSSARY_ADD_20250116_1",
    "GLOSSARY_LINK_20250116_2",
    "TERM_LOG_LINK_20250116_3",
    "GRAPH_QUERY_20250116_1",
    "AGG_QUERY_20250116_2",
    "RECOVERY_TEST_20250116_1"
]

# Verify each marker appears in transcript
for marker in markers:
    cmd = f'rg "{marker}" ~/.claude/projects/-home-graham-workspace-experiments-cc-executor/*.jsonl | tail -3'
    # Run and check output
```

## Test Status

| Test | Description | Status | Verified |
|------|-------------|--------|----------|
| 1.1 | Get Schema | PENDING | [ ] |
| 2.1 | Basic Query | PENDING | [ ] |
| 2.2 | Query with Bind Vars | PENDING | [ ] |
| 2.3 | Failed Query Recovery | PENDING | [ ] |
| 3.1 | English to AQL | PENDING | [ ] |
| 4.1 | Insert Document | PENDING | [ ] |
| 4.2 | Get Document | PENDING | [ ] |
| 4.3 | Update Document | PENDING | [ ] |
| 4.4 | Upsert Document | PENDING | [ ] |
| 4.5 | Delete Document | PENDING | [ ] |
| 5.1 | Create Edge | PENDING | [ ] |
| 6.1 | Add Glossary Term | PENDING | [ ] |
| 6.2 | Link Terms | PENDING | [ ] |
| 6.3 | Link Term to Log | PENDING | [ ] |
| 7.1 | Graph Traversal | PENDING | [ ] |
| 7.2 | Aggregation | PENDING | [ ] |
| 8.1 | Error Recovery | PENDING | [ ] |

## How to Use This Document

1. Run each test command sequentially
2. Note the actual output
3. Verify the marker appears in transcript using ripgrep
4. Update status to PASS/FAIL
5. Check the [ ] box when verified

This ensures every tool function is tested and results are non-hallucinated.