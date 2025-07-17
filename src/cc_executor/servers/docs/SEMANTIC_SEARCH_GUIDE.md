# Semantic Search Guide for MCP ArangoDB Tools

## Overview

Semantic search requires:
1. **Embeddings for all documents** - Vector representations of text
2. **Vector indexes or search capability** - To find similar vectors efficiently
3. **Consistent embedding generation** - Same model for queries and documents

## ArangoDB Vector Index Setup

### Prerequisites for Vector Search

1. **Enable Experimental Features**
   ```bash
   # Start ArangoDB with vector index support
   arangod --experimental-vector-index
   ```
   
   **Important**: Vector indexes are experimental and require this startup option.

2. **Documents Must Have Embeddings First**
   - Unlike other indexes, vector indexes cannot be created on empty collections
   - You must populate documents with embeddings before creating the index
   - The index trains on existing data - quality depends on having representative data

### Step-by-Step Vector Index Creation

#### Step 1: Add Embeddings to Documents
```javascript
// Documents must already have embedding field
db.log_events.save({
  error_message: "Connection timeout",
  embedding: [0.1, 0.2, 0.3, ...], // 1024-dimensional vector
  // other fields...
});
```

#### Step 2: Create Vector Index (After Embeddings Exist)
```javascript
// For L2 (Euclidean) distance
db.log_events.ensureIndex({
  name: "embedding_vector_l2",
  type: "vector",
  fields: ["embedding"],
  params: { 
    metric: "l2",
    dimension: 1024,        // Must match embedding dimensions
    nLists: 100,           // Number of clusters for indexing
    defaultNProbe: 1,      // Default search accuracy (can override in queries)
    trainingIterations: 25 // Training iterations for index quality
  }
});

// For Cosine similarity
db.log_events.ensureIndex({
  name: "embedding_vector_cosine",
  type: "vector", 
  fields: ["embedding"],
  params: {
    metric: "cosine",      // For APPROX_NEAR_COSINE queries
    dimension: 1024,
    nLists: 100,
    defaultNProbe: 1,
    trainingIterations: 25
  }
});
```

#### Step 3: Use Vector Functions in AQL
```aql
// With cosine vector index
FOR doc IN log_events
  SORT APPROX_NEAR_COSINE(doc.embedding, @query_embedding, 10) DESC
  LIMIT 10
  RETURN doc

// With L2 vector index  
FOR doc IN log_events
  SORT APPROX_NEAR_L2(doc.embedding, @query_embedding, 10)
  LIMIT 10
  RETURN doc
```

### Important Constraints

1. **Order Matters**: Embeddings first, then index
2. **No Incremental Updates**: Adding embeddings later affects index quality
3. **Training Required**: Index creation triggers training on existing data
4. **Fixed Dimensions**: All embeddings must have same dimensions

## Key Components

### 1. Embedding Generation

We use the `embedding_utils.py` from logger_agent:
- Model: `BAAI/bge-large-en` (1024 dimensions)
- Fallback: Hash-based embeddings if model unavailable
- Normalized vectors for cosine similarity

### 2. ArangoDB Search Methods

#### Method 1: APPROX_NEAR_COSINE (Experimental)
```aql
-- Requires ArangoDB 3.12+ with --experimental-vector-index
FOR doc IN collection
    FILTER doc.embedding != null
    LET similarity = APPROX_NEAR_COSINE(doc.embedding, @query_embedding)
    FILTER similarity > 0.7
    SORT similarity DESC
    LIMIT 10
    RETURN doc
```

**Status**: Not available in standard ArangoDB installations

#### Method 2: COSINE_SIMILARITY Function
```aql
-- Works in ArangoDB 3.8+
FOR doc IN collection
    FILTER doc.embedding != null
    LET similarity = COSINE_SIMILARITY(doc.embedding, @query_embedding)
    FILTER similarity > 0.7
    SORT similarity DESC
    LIMIT 10
    RETURN doc
```

**Status**: Works but scans all documents (no index support)

#### Method 3: Client-Side Similarity
```python
# Fetch documents and calculate similarity in Python
all_docs = fetch_documents_with_embeddings()
similarities = [cosine_similarity(query_emb, doc_emb) for doc_emb in all_docs]
```

**Status**: Works but inefficient for large collections

## Usage Workflow

### Step 1: Ensure Embeddings Exist

```python
# Check readiness
status = await mcp__arango-tools__check_semantic_readiness()

# Generate missing embeddings
result = await mcp__arango-tools__ensure_embeddings(
    collection="log_events",
    text_fields="error_message,resolution,fix_rationale",
    limit=1000
)
```

### Step 2: Insert with Embeddings

```python
# New documents automatically get embeddings
await mcp__arango-tools__insert(
    message="Failed to connect to Redis",
    error_type="ConnectionError",
    error_message="Redis connection timeout after 30s",
    resolution="Increased timeout to 60s and added retry logic",
    fix_rationale="Network latency was higher than expected"
)
```

### Step 3: Search Semantically

```python
# Search for similar errors
results = await mcp__arango-tools__semantic_search(
    query="database connection keeps timing out",
    collection="log_events",
    limit=5,
    min_similarity=0.6
)

# Results include similarity scores
for result in results["results"]:
    print(f"Similarity: {result['similarity']:.2f}")
    print(f"Error: {result['error_message']}")
    print(f"Fix: {result['resolution']}")
```

## Hybrid Search Pattern

Combine semantic and keyword search for best results:

```aql
-- Combine vector similarity with BM25 text search
FOR doc IN agent_activity_search
    SEARCH ANALYZER(doc.message IN TOKENS(@keywords, 'text_en'), 'text_en')
    FILTER doc.embedding != null
    
    LET text_score = BM25(doc)
    LET vector_score = COSINE_SIMILARITY(doc.embedding, @query_embedding)
    LET combined_score = (text_score * 0.3) + (vector_score * 0.7)
    
    FILTER combined_score > 0.5
    SORT combined_score DESC
    LIMIT 10
    RETURN {
        document: doc,
        text_relevance: text_score,
        semantic_similarity: vector_score,
        combined_score: combined_score
    }
```

## Performance Considerations

### 1. Embedding Generation
- ~100-200ms per document (CPU)
- ~10-50ms per document (GPU)
- Cache embeddings to avoid regeneration

### 2. Search Performance
- APPROX_NEAR_COSINE: O(log n) with index
- COSINE_SIMILARITY: O(n) full scan
- Client-side: O(n) + network transfer

### 3. Optimization Tips
- Pre-generate embeddings during insert
- Limit search to recent documents
- Use hybrid search for better relevance
- Consider embedding dimensionality reduction for speed

## Troubleshooting

### No Results from Semantic Search

1. **Check embeddings exist**:
   ```aql
   FOR doc IN log_events
       FILTER doc.embedding == null
       RETURN COUNT(doc)
   ```

2. **Verify embedding dimensions**:
   ```aql
   FOR doc IN log_events
       FILTER doc.embedding != null
       LIMIT 1
       RETURN LENGTH(doc.embedding)
   ```

3. **Test with exact document**:
   ```python
   # Get embedding from known document
   doc = get_document_by_id("log_events/12345")
   results = semantic_search(doc["error_message"])
   # Should return the same document with similarity ≈ 1.0
   ```

### Poor Search Quality

1. **Adjust similarity threshold**:
   - Start with 0.5 for broad matches
   - Use 0.8+ for near-exact matches

2. **Improve text for embedding**:
   - Combine multiple fields
   - Include context and keywords
   - Remove noise (timestamps, IDs)

3. **Use hybrid search**:
   - Semantic for concepts
   - Keywords for specific terms

### Performance Issues

1. **Batch embedding generation**:
   ```python
   # Process in batches overnight
   for batch in range(0, total, 1000):
       ensure_embeddings(limit=1000)
   ```

2. **Filter before similarity**:
   ```aql
   FOR doc IN log_events
       FILTER doc._created_at > DATE_SUBTRACT(DATE_NOW(), 30, "days")
       FILTER doc.embedding != null
       LET similarity = COSINE_SIMILARITY(doc.embedding, @query_embedding)
   ```

## Best Practices

1. **Always generate embeddings on insert** - Don't wait for search time

2. **Use meaningful text** - Combine error message, type, and resolution

3. **Monitor embedding coverage**:
   ```python
   stats = await check_semantic_readiness()
   # Aim for >90% coverage
   ```

4. **Fallback gracefully** - If semantic fails, use keyword search

5. **Cache query embeddings** - Reuse for pagination

6. **Test similarity thresholds** - Different for each use case

## Example: Complete Debugging Flow

```python
# 1. Error occurs
error_id = await mcp__arango-tools__insert(
    message="Subprocess hangs when output exceeds 64KB",
    error_type="SubprocessTimeout",
    error_message="Process.wait() never returns when stdout buffer fills",
    resolved=False
)

# 2. Search for similar issues
similar = await mcp__arango-tools__semantic_search(
    query="subprocess hanging buffer full stdout",
    min_similarity=0.6
)

# 3. Find a solution that works
# ... apply fix ...

# 4. Update with resolution (embedding auto-generated)
await mcp__arango-tools__update(
    collection="log_events",
    key=error_id["key"],
    fields={
        "resolved": True,
        "resolution": "Use asyncio with stream draining to prevent buffer deadlock",
        "fix_rationale": "subprocess.PIPE has 64KB limit, must actively read to prevent blocking"
    }
)

# 5. Create edges to helpful resources
await mcp__arango-tools__edge(
    from_id=error_id["id"],
    to_id=similar["results"][0]["id"],
    collection="error_relationships",
    relationship_type="inspired_by"
)
```

## Summary

Semantic search enhances error resolution by finding conceptually similar issues even when keywords don't match. The key is ensuring all documents have embeddings and using the appropriate search strategy for your ArangoDB version.