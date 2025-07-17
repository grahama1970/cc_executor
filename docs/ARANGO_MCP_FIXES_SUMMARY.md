# ArangoDB MCP Tools - Fixes Applied

## Date: 2025-01-16

## Fixed Issues

### 1. Query Bind Variables ✅
**Problem**: MCP tool couldn't accept dictionary parameters for bind_vars
**Solution**: Changed bind_vars parameter from `Dict[str, Any]` to `str` (JSON string)
**Implementation**:
```python
# Before
async def query(aql: str, bind_vars: Optional[Dict[str, Any]] = None) -> str:

# After  
async def query(aql: str, bind_vars: Optional[str] = None) -> str:
    # Parse JSON string to dict
    parsed_bind_vars = None
    if bind_vars:
        try:
            parsed_bind_vars = json.loads(bind_vars)
        except json.JSONDecodeError as e:
            return json.dumps({"success": False, "error": f"Invalid JSON in bind_vars: {str(e)}"})
```

**Usage**:
```python
# Pass bind_vars as JSON string
await mcp__arango-tools__query(
    "FOR doc IN @@col FILTER doc.level == @level RETURN doc",
    '{"@col": "log_events", "level": "ERROR"}'
)
```

### 2. Upsert Operation ✅
**Problem**: Schema validation error for script_runs collection
**Solution**: 
1. Changed upsert parameters to accept JSON strings
2. Added automatic field generation for script_runs collection

**Implementation**:
```python
# Changed parameters to JSON strings
async def upsert(
    collection: str,
    search: str,  # JSON string
    update: str,  # JSON string
    create: Optional[str] = None  # JSON string
) -> str:

# Added required fields for script_runs
if collection == "script_runs" and "execution_id" not in create_doc:
    create_doc["execution_id"] = f"{create_doc.get('script_name', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    create_doc["start_time"] = create_doc.get("start_time", datetime.now().isoformat())
    create_doc["status"] = create_doc.get("status", "running")
    create_doc["pid"] = create_doc.get("pid", os.getpid())
    create_doc["hostname"] = create_doc.get("hostname", os.uname().nodename)
```

### 3. Update Operation ✅
**Problem**: Also affected by dictionary parameter issue
**Solution**: Changed fields parameter to JSON string
```python
async def update(
    collection: str,
    key: str,
    fields: str  # JSON string
) -> str:
```

### 4. BM25 Search View ✅
**Problem**: Referenced non-existent `agent_activity_search` view
**Solution**: Updated to use existing `log_search_view`
```python
"aql": """FOR doc IN log_search_view
SEARCH ANALYZER(doc.message IN TOKENS(@query, 'text_en'), 'text_en')
LET score = BM25(doc)
FILTER score > 0.5
SORT score DESC
LIMIT 10
RETURN doc"""
```

## Important Note

**⚠️ RELOAD REQUIRED**: After these changes, the MCP tools need to be reloaded:
1. User should run the `/mcp` command in Claude
2. This will reload the MCP servers with the updated code

## Testing After Reload

Once reloaded, test with:

```python
# Test bind variables
await mcp__arango-tools__query(
    "FOR doc IN @@col FILTER doc.level == @level LIMIT 2 RETURN doc",
    '{"@col": "log_events", "level": "ERROR"}'
)

# Test upsert
await mcp__arango-tools__upsert(
    "script_runs",
    '{"script_name": "test_script.py"}',
    '{"last_run": "2025-01-16", "run_count": 1}'
)

# Test BM25 search
await mcp__arango-tools__query(
    """FOR doc IN log_search_view
       SEARCH ANALYZER(doc.message IN TOKENS(@query, 'text_en'), 'text_en')
       LET score = BM25(doc)
       FILTER score > 0.5
       SORT score DESC
       LIMIT 10
       RETURN {message: doc.message, score: score}""",
    '{"query": "test insert marker"}'
)
```

## Summary

All requested fixes have been implemented:
- ✅ Query bind variables now accept JSON strings
- ✅ Upsert operation handles schema validation with auto-generated fields
- ✅ Update operation accepts JSON strings
- ✅ BM25 search uses correct view name

The core issue was that FastMCP doesn't properly handle dictionary parameters, so we converted all dict parameters to JSON strings that are parsed within the functions.