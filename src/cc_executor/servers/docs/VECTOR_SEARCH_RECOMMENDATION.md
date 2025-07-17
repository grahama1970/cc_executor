# Vector Search Recommendation for Tool Journey System

## Executive Summary

**Recommendation: Start with COSINE_SIMILARITY, prepare for APPROX_NEAR**

Given your current scale (1k-10k journeys) and requirements, I recommend:
1. **Phase 1**: Use simple COSINE_SIMILARITY (immediate implementation)
2. **Phase 2**: Add APPROX_NEAR when you hit ~5,000 journeys or latency issues

## Detailed Analysis

### Your Current Situation
- **Scale**: 1,000-10,000 tool journeys
- **Dimensions**: 384 (sentence-transformers)
- **Growth**: Continuous (every completed journey)
- **Need**: Real-time recommendations

### Option 1: COSINE_SIMILARITY (Simple)

```aql
FOR doc IN log_events
    FILTER doc.event_type == "tool_journey_completed"
    LET similarity = COSINE_SIMILARITY(doc.task_embedding, @query_embedding)
    FILTER similarity > 0.7
    SORT similarity DESC
    LIMIT 10
```

**Pros:**
- ✅ Zero additional complexity
- ✅ Works immediately
- ✅ 100% accurate results
- ✅ No index maintenance
- ✅ New journeys instantly searchable

**Cons:**
- ❌ O(n) complexity - every query scans all embeddings
- ❌ At 10k journeys × 384 dims = 3.8M float comparisons per query
- ❌ Will slow down as you grow

**Performance Estimate:**
- 1k journeys: ~5-10ms per query
- 5k journeys: ~25-50ms per query  
- 10k journeys: ~50-100ms per query

### Option 2: APPROX_NEAR with Vector Index (Complex)

```aql
FOR doc IN agent_activity_search
    SEARCH ANALYZER(
        doc.event_type == "tool_journey_completed" AND
        APPROX_NEAR_COSINE(doc.task_embedding, @query_embedding, @limit),
        "identity"
    )
    LET score = COSINE_SIMILARITY(doc.task_embedding, @query_embedding)
    SORT score DESC
    RETURN doc
```

**Pros:**
- ✅ Sub-linear complexity O(sqrt(n))
- ✅ Consistent <10ms queries even at 100k+ scale
- ✅ Future-proof architecture
- ✅ Can combine with other ArangoSearch features

**Cons:**
- ❌ Requires vector index setup
- ❌ ~95-99% accurate (approximate)
- ❌ Index maintenance overhead
- ❌ More complex implementation

**Setup Required:**
1. Create ArangoSearch View with vector index
2. Configure IVF parameters (nLists, nProbe)
3. Handle index refreshing for new documents
4. Monitor and tune performance

## Recommended Approach

### Phase 1: Start Simple (Now - 5k journeys)
```python
# In mcp_tool_journey.py
similarity_query = """
FOR doc IN log_events
    FILTER doc.event_type == "tool_journey_completed"
    FILTER doc.task_embedding != null
    
    LET similarity = COSINE_SIMILARITY(doc.task_embedding, @embedding)
    FILTER similarity > 0.7
    SORT similarity DESC
    LIMIT 10
    
    RETURN {
        task: doc.task_description,
        tool_sequence: doc.tool_sequence,
        similarity: similarity
    }
"""
```

### Phase 2: Add Vector Index (5k+ journeys or latency >50ms)
```javascript
// Create view with vector index
db._createView("journey_vector_search", "arangosearch", {
    links: {
        log_events: {
            fields: {
                task_embedding: {
                    vectorIndexType: "ivf",
                    dimension: 384,
                    metric: "cosine",
                    nLists: 100,  // sqrt(10000)
                    nProbe: 20    // balance speed/accuracy
                }
            }
        }
    }
});
```

## Migration Strategy

### 1. Add Performance Monitoring (Now)
```python
# Track query performance
start = time.time()
result = execute_aql(similarity_query, {"embedding": task_embedding})
query_time = time.time() - start

# Log if slow
if query_time > 0.05:  # 50ms threshold
    logger.warning(f"Slow embedding query: {query_time}s")
```

### 2. Prepare Index-Ready Schema (Now)
```python
# Ensure embeddings are stored correctly
journey_doc = {
    "task_embedding": embedding.tolist(),  # Must be array of floats
    "embedding_model": "all-MiniLM-L6-v2",
    "embedding_dim": 384
}
```

### 3. Create Hybrid Query Function (Future)
```python
async def find_similar_journeys(embedding, use_vector_index=False):
    if use_vector_index and has_vector_view:
        # Use APPROX_NEAR
        return await execute_vector_search(embedding)
    else:
        # Use COSINE_SIMILARITY
        return await execute_similarity_search(embedding)
```

## Decision Criteria

**Stick with COSINE_SIMILARITY if:**
- Query latency stays under 50ms
- Journey count stays under 5,000
- You value simplicity over performance
- 100% accuracy is important

**Switch to APPROX_NEAR when:**
- Query latency exceeds 50ms consistently
- Journey count exceeds 5,000
- You need consistent sub-10ms responses
- 95%+ accuracy is acceptable

## Conclusion

For your current scale, the added complexity of vector indexes isn't justified. Start with COSINE_SIMILARITY and monitor performance. When you hit performance limits (likely around 5k journeys), the migration to APPROX_NEAR is straightforward.

The beauty of this approach is that your data model doesn't change - you're just adding an index and changing the query. This gives you the best of both worlds: simplicity now, scalability when needed.