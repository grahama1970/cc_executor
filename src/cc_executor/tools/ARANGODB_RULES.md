# ArangoDB Rules and Common Mistakes

This document outlines critical rules and common mistakes to avoid when writing AQL queries. Reference this whenever you encounter AQL errors or need to write complex queries.

## 🔴 Error Quick Reference

| Error Code | Error Name | Common Cause | Quick Fix |
|------------|------------|--------------|-----------|
| 1501 | ERROR_QUERY_PARSE | Syntax error | Check query syntax |
| 1504 | ERROR_QUERY_NUMBER_OUT_OF_RANGE | Number overflow | Limit numeric operations |
| 1510 | ERROR_QUERY_VARIABLE_NAME_INVALID | Invalid variable name | Use valid variable names |
| 1511 | ERROR_QUERY_VARIABLE_REDECLARED | Variable redeclared | Use unique variable names |
| 1512 | ERROR_QUERY_VARIABLE_NAME_UNKNOWN | Unknown variable | Declare variables before use |
| 1521 | ERROR_QUERY_COLLECTION_LOCK_FAILED | Can't lock collection | Check collection exists |
| 1552 | ERROR_QUERY_BIND_PARAMETER_UNDECLARED | Missing bind parameter | Provide all @parameters |
| 1553 | ERROR_QUERY_BIND_PARAMETER_TYPE | Wrong parameter type | Check parameter types |
| 1554 | ERROR_QUERY_VECTOR_SEARCH_NOT_APPLIED | Vector search failed | Check vector index exists |
| 1563 | ERROR_QUERY_ARRAY_EXPECTED | Non-array for vector | Pass arrays for vectors |
| 1210 | ERROR_ARANGO_UNIQUE_CONSTRAINT_VIOLATED | Duplicate unique key | Check before insert |
| 1211 | ERROR_ARANGO_VIEW_NOT_FOUND | View doesn't exist | Create view first |
| 1212 | ERROR_ARANGO_INDEX_NOT_FOUND | Index doesn't exist | Create required index |

## 🚫 Critical Rules - MUST FOLLOW

### 1. **NEVER Use Filters with APPROX_NEAR_COSINE**
```aql
-- ❌ WRONG - Will fail with [HTTP 500][ERR 1554]
FOR doc IN collection
    FILTER doc.category == "python"  -- NO FILTERS ALLOWED!
    LET similarity = APPROX_NEAR_COSINE(doc.embedding, @queryEmbedding)
    SORT similarity DESC
    RETURN doc

-- ✅ CORRECT - Use two-stage approach
-- Stage 1: Pure vector search
FOR doc IN collection
    LET similarity = APPROX_NEAR_COSINE(doc.embedding, @queryEmbedding)
    SORT similarity DESC
    LIMIT 50  -- Get extra results for Python filtering
    RETURN MERGE(doc, {similarity: similarity})

-- Stage 2: Filter in Python after retrieval
```

### 2. **Cannot Bind Collection or View Names**
```aql
-- ❌ WRONG - Collections/views cannot be bind variables
FOR doc IN @collectionName  -- FAILS!
    RETURN doc

-- ✅ CORRECT - Use Python f-strings or string formatting
collection_name = "agent_activity"
aql = f"""
FOR doc IN {collection_name}
    RETURN doc
"""
```

### 3. **Vector Index Structure Must Have params Sub-object**
```python
# ❌ WRONG - Flat parameters (will fail)
collection.add_index({
    "type": "vector",
    "fields": ["embedding"],
    "dimension": 1024,  # Wrong - should be in params
    "metric": "cosine"  # Wrong - should be in params
})

# ✅ CORRECT - params as sub-object
collection.add_index({
    "type": "vector",
    "fields": ["embedding"],
    "params": {  # params MUST be a sub-object
        "dimension": 1024,
        "metric": "cosine",
        "nLists": 2
    }
})
```

## ⚠️ Common Mistakes

### 4. **Embedding Dimension Mismatches**
- **Problem**: Query embedding has different dimensions than stored embeddings
- **Error**: `[HTTP 500][ERR 1554] AQL: failed vector search`
- **Solution**: Always verify dimensions match (usually 1024 for BGE models)
```aql
-- Add dimension check in queries
FOR doc IN collection
    FILTER LENGTH(doc.embedding) == 1024  -- Verify dimension
    LET similarity = APPROX_NEAR_COSINE(doc.embedding, @queryEmbedding)
    RETURN doc
```

### 5. **Using FILTER with BM25 Score**
```aql
-- ❌ WRONG - Cannot filter by score in AQL
FOR doc IN myView
    SEARCH ANALYZER(doc.text IN TOKENS(@query, "text_en"), "text_en")
    LET score = BM25(doc)
    FILTER score > 0.5  -- This can cause issues
    RETURN doc

-- ✅ CORRECT - Filter in Python after retrieval
FOR doc IN myView
    SEARCH ANALYZER(doc.text IN TOKENS(@query, "text_en"), "text_en")
    LET score = BM25(doc)
    SORT score DESC
    LIMIT 20
    RETURN {doc: doc, score: score}
```

### 6. **Forgetting to Check if Embedding Field Exists**
```aql
-- ❌ WRONG - Will fail if doc lacks embedding field
FOR doc IN collection
    LET similarity = APPROX_NEAR_COSINE(doc.embedding, @queryEmbedding)
    RETURN doc

-- ✅ CORRECT - Check field existence
FOR doc IN collection
    FILTER HAS(doc, "embedding") 
        AND IS_LIST(doc.embedding)
        AND LENGTH(doc.embedding) > 0
    LET similarity = APPROX_NEAR_COSINE(doc.embedding, @queryEmbedding)
    RETURN doc
```

### 7. **Not Handling Empty Results in Aggregations**
```aql
-- ❌ WRONG - MIN/MAX fail on empty arrays
LET scores = (FOR doc IN collection RETURN doc.score)
RETURN {min: MIN(scores), max: MAX(scores)}

-- ✅ CORRECT - Handle empty case
LET scores = (FOR doc IN collection RETURN doc.score)
RETURN {
    min: LENGTH(scores) > 0 ? MIN(scores) : null,
    max: LENGTH(scores) > 0 ? MAX(scores) : null
}
```

### 8. **Improper Use of TOKENS Function**
```aql
-- ❌ WRONG - TOKENS needs analyzer specification
SEARCH doc.text IN TOKENS(@query)

-- ✅ CORRECT - Specify analyzer
SEARCH ANALYZER(doc.text IN TOKENS(@query, "text_en"), "text_en")
```

### 9. **Graph Traversal Direction Confusion**
```aql
-- Be explicit about direction
FOR v, e, p IN 1..3 OUTBOUND @startVertex GRAPH @graphName
    RETURN v

-- OUTBOUND: follows _from → _to
-- INBOUND: follows _to → _from  
-- ANY: follows both directions
```

### 10. **Not Waiting for Index Creation**
```python
# ❌ WRONG - Using index immediately
collection.insert_many(documents)
results = db.aql.execute(search_query)  # May fail!

# ✅ CORRECT - Wait for indexing
collection.insert_many(documents)
time.sleep(2)  # Wait for ArangoSearch indexing
results = db.aql.execute(search_query)
```

### 11. **Missing or Undeclared Bind Parameters**
```aql
-- ❌ WRONG - @username not provided
FOR u IN users 
    FILTER u.name == @username  -- Error 1552 if not bound
    RETURN u

-- ✅ CORRECT - Provide all bind parameters
db.aql.execute(query, bind_vars={"username": "alice"})
```

### 12. **Wrong Type for Bind Parameters**
```python
# ❌ WRONG - Vector as string
query_vector = "[0.1, 0.2, 0.3]"  # String, not array!
db.aql.execute(aql, bind_vars={"queryEmbedding": query_vector})

# ✅ CORRECT - Vector as array
query_vector = [0.1, 0.2, 0.3]  # Actual array
db.aql.execute(aql, bind_vars={"queryEmbedding": query_vector})
```

### 13. **Variable Redeclaration**
```aql
-- ❌ WRONG - Redeclaring variable (Error 1511)
LET total = 100
LET total = 200  -- Can't redeclare!
RETURN total

-- ✅ CORRECT - Use different names
LET initial_total = 100
LET final_total = 200
RETURN final_total
```

### 14. **Subqueries in SEARCH Expressions**
```aql
-- ❌ WRONG - Subqueries in SEARCH can return incorrect results
FOR doc IN myView
    SEARCH doc.category IN (
        FOR c IN categories 
        FILTER c.active == true 
        RETURN c.name
    )
    RETURN doc

-- ✅ CORRECT - Disable optimizer rule
db.aql.execute(query, optimizer={"rules": ["-inline-subqueries"]})
```

### 15. **ArangoSearch Locale Issues**
```aql
-- ⚠️ WARNING - Operators don't respect analyzer locale
FOR doc IN myView
    SEARCH ANALYZER(doc.text > "münchen", "text_de")  -- May not work as expected
    RETURN doc

-- ✅ BETTER - Use exact matches or contains
FOR doc IN myView
    SEARCH ANALYZER(doc.text IN TOKENS("münchen", "text_de"), "text_de")
    RETURN doc
```

## 📋 Best Practices

### Two-Stage Search Pattern
When you need filtering with vector search:
```python
# Stage 1: Get vector results without filters
vector_results = get_vector_results(query_embedding, limit=100)

# Stage 2: Apply filters in Python
filtered_results = []
for result in vector_results:
    if result['category'] == target_category:
        filtered_results.append(result)
        
# Return top N after filtering
final_results = filtered_results[:10]
```

### Always Validate Before Querying
```python
# Check collection exists
if not db.has_collection(collection_name):
    return {"error": f"Collection {collection_name} not found"}

# Check view exists for text search
if not any(v["name"] == view_name for v in db.views()):
    return {"error": f"View {view_name} not found"}
```

### Error Recovery Patterns
```python
try:
    # Try vector search first
    results = vector_search(query_embedding)
except Exception as e:
    if "ERR 1554" in str(e):
        # Fallback to manual cosine similarity
        results = manual_cosine_search(query_embedding)
    else:
        raise
```

## 🔍 Debugging Tips

1. **Check ArangoDB Version**: Vector search requires 3.12+
   ```python
   version = db.version()
   print(f"ArangoDB version: {version}")
   ```

2. **Verify Index Configuration**:
   ```python
   indexes = collection.indexes()
   for idx in indexes:
       if idx.get("type") == "vector":
           print(f"Vector index: {idx}")
   ```

3. **Test with Simple Queries First**: Start with basic queries before adding complexity

4. **Use EXPLAIN to Debug AQL**:
   ```aql
   RETURN EXPLAIN("FOR doc IN collection RETURN doc")
   ```

## 📚 References

- [APPROX_NEAR_COSINE_USAGE.md](/home/graham/workspace/experiments/arangodb/docs/troubleshooting/APPROX_NEAR_COSINE_USAGE.md)
- [FIXED_SEMANTIC_SEARCH.md](/home/graham/workspace/experiments/arangodb/docs/01_architecture/architecture/FIXED_SEMANTIC_SEARCH.md)
- [ARANGO_USAGE.md](/home/graham/workspace/experiments/arangodb/docs/01_architecture/architecture/ARANGO_USAGE.md)

Remember: When in doubt, keep queries simple and do complex filtering in Python!