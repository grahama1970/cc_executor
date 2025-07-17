# Vector Search Quick Start Guide

## Prerequisites Checklist

- [ ] ArangoDB 3.12+ installed
- [ ] Started with `arangod --experimental-vector-index`
- [ ] Python packages: `transformers`, `torch`, `python-arango`
- [ ] Access to embedding_utils.py from logger_agent

## Complete Setup Workflow

### 1. Start ArangoDB with Vector Support
```bash
# Stop existing instance
arangodb stop

# Start with experimental features
arangod --experimental-vector-index
```

### 2. Generate Embeddings FIRST
```python
# Run the setup script to add embeddings to existing documents
python mcp_semantic_search_setup.py

# Or use MCP tool for new documents
await mcp__arango-tools__ensure_embeddings(
    collection="log_events",
    text_fields="error_message,resolution,fix_rationale",
    limit=1000
)
```

### 3. Create Vector Indexes (After Embeddings)
```javascript
// In arangosh or Web UI
db._useDatabase("script_logs");

// Create cosine similarity index
db.log_events.ensureIndex({
  type: "vector",
  fields: ["embedding"],
  name: "embedding_vector_cosine",
  params: {
    metric: "cosine",
    dimension: 1024,
    nLists: 100,
    defaultNProbe: 1,
    trainingIterations: 25
  }
});
```

### 4. Test Vector Search
```python
# Using MCP tool
results = await mcp__arango-tools__semantic_search(
    query="subprocess buffer overflow timeout",
    collection="log_events",
    limit=5,
    min_similarity=0.6
)
```

## Quick Commands

### Check if Vector Search is Ready
```aql
// Check experimental features
RETURN VERSION()

// Count documents with embeddings
FOR col IN ["log_events", "debugging_sessions"]
  LET total = LENGTH(FOR doc IN COLLECTION(col) RETURN 1)
  LET with_emb = LENGTH(FOR doc IN COLLECTION(col) FILTER doc.embedding != null RETURN 1)
  RETURN {
    collection: col,
    total: total,
    with_embeddings: with_emb,
    ready: with_emb > 0
  }
```

### Manual Embedding Generation
```python
from embedding_utils import get_embedding

# Generate embedding for text
text = "Connection timeout after 30 seconds"
embedding = get_embedding(text)

# Update document
db.log_events.update({"_key": "12345"}, {
    "embedding": embedding,
    "embedding_model": "BAAI/bge-large-en",
    "embedding_generated_at": datetime.now().isoformat()
})
```

### Direct AQL Vector Search
```aql
// After vector index exists
FOR doc IN log_events
  SORT APPROX_NEAR_COSINE(doc.embedding, @query_embedding, 5) DESC
  LIMIT 5
  RETURN {
    id: doc._id,
    error: doc.error_message,
    similarity: APPROX_NEAR_COSINE(doc.embedding, @query_embedding)
  }
```

## Common Issues

### "Function 'APPROX_NEAR_COSINE' is not implemented"
- **Cause**: ArangoDB not started with `--experimental-vector-index`
- **Fix**: Restart with the flag enabled

### "No documents match your query"
- **Cause**: Documents don't have embeddings
- **Fix**: Run `ensure_embeddings()` first

### "Vector index cannot be created"
- **Cause**: No documents with embeddings in collection
- **Fix**: Generate embeddings before creating index

### Search returns poor results
- **Cause**: Low quality embeddings or wrong similarity threshold
- **Fix**: 
  - Use better text for embedding (combine multiple fields)
  - Lower similarity threshold (try 0.5 instead of 0.8)
  - Use hybrid search (combine with BM25)

## Performance Tips

1. **Batch Embedding Generation**
   ```python
   # Process overnight in batches
   for offset in range(0, total_docs, 1000):
       await ensure_embeddings(limit=1000)
   ```

2. **Optimize nProbe for Speed vs Accuracy**
   ```aql
   // Higher nProbe = better accuracy, slower
   SORT APPROX_NEAR_COSINE(doc.embedding, @query, 10) DESC
   ```

3. **Pre-filter Before Vector Search**
   ```aql
   FOR doc IN log_events
     FILTER doc.created_at > DATE_SUBTRACT(DATE_NOW(), 30, "days")
     FILTER doc.embedding != null
     SORT APPROX_NEAR_COSINE(doc.embedding, @query) DESC
     LIMIT 10
     RETURN doc
   ```

## Remember the Order!

1. **Enable** experimental features
2. **Generate** embeddings for documents
3. **Create** vector indexes
4. **Search** using vector functions

Without following this order, vector search will not work!