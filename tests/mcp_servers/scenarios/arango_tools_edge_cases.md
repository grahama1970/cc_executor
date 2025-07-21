# ArangoDB Tools Edge Cases and Failure Scenarios (UPDATED)

## Overview

This document outlines edge cases, failure scenarios, and stress tests that should be performed to ensure the robustness of the ArangoDB tools integration. 

**NEW**: All scenarios now include response validation using the response-validator MCP tool to ensure data integrity and prevent hallucinations in LLM-assisted operations.

## Edge Case Categories

### 1. Data Volume Edge Cases

#### Scenario: Large Result Sets
```python
# Test 1: Query returning millions of documents
result = await mcp__arango_tools__query(
    "FOR doc IN log_events RETURN doc",  # No LIMIT!
    '{"stream": true}'  # Should implement streaming
)

# VALIDATION: Check if result is actually from corpus
if result.get("success") and result.get("results"):
    # Validate first few results are real documents
    sample_results = result["results"][:5] if isinstance(result["results"], list) else []
    for doc in sample_results:
        validation = await mcp__response_validator__validate_llm_response(
            response=json.dumps(doc),
            validation_type="format"
        )
        assert json.loads(validation)["data"]["validation_passed"], "Invalid document format"

# Test 2: Visualization with too many nodes
viz_data = await mcp__arango_tools__get_visualization_data(
    query_type="network",
    collection="log_events",
    limit=10000  # D3 performance limit test
)

# VALIDATION: Ensure visualization data is properly structured
if viz_data.get("success"):
    validation = await mcp__response_validator__validate_llm_response(
        response=json.dumps(viz_data["data"]),
        validation_type="content",
        expected_content=["nodes", "links", "metadata"]
    )
    assert json.loads(validation)["data"]["validation_passed"], "Invalid visualization structure"

# Test 3: Cluster detection on massive graphs
clusters = await mcp__arango_tools__find_clusters(
    graph_name="error_causality",
    max_iterations=1000,  # Convergence test
    min_cluster_size=1
)

# VALIDATION: Verify clusters contain real nodes
if clusters.get("success") and clusters.get("clusters"):
    # Check that cluster nodes exist in database
    for cluster in clusters["clusters"][:3]:  # Check first 3 clusters
        node_check = await mcp__arango_tools__query(
            f"FOR node IN {cluster['collection']} FILTER node._key IN @keys RETURN node._key",
            json.dumps({"keys": cluster["nodes"][:5]})  # Check first 5 nodes
        )
        assert node_check.get("success"), "Failed to verify cluster nodes"
```

**Expected Behavior**:
- Implement pagination or streaming
- Warn when visualization limits exceeded
- Timeout protection for long-running algorithms
- All results must be validated against actual database content

---

### 2. Data Quality Edge Cases

#### Scenario: Malformed or Missing Data
```python
# Test 1: Insert with missing required fields
result = await mcp__arango_tools__insert(
    message=None,  # Required field is None
    level="INFO"
)

# VALIDATION: Ensure error response is properly formatted
validation = await mcp__response_validator__validate_llm_response(
    response=json.dumps(result),
    validation_type="content",
    expected_content=["error", "message", "required"]
)
assert not result.get("success"), "Should fail with missing required field"
assert json.loads(validation)["data"]["validation_passed"], "Error response malformed"

# Test 2: Query with invalid AQL syntax
result = await mcp__arango_tools__query(
    "FOR doc IN FILTER"  # Incomplete query
)

# VALIDATION: Check error includes helpful suggestions
if not result.get("success"):
    # Use perplexity to validate error message quality
    perplexity_check = await mcp__perplexity_ask__perplexity_ask({
        "messages": [{
            "role": "user",
            "content": f"Is this a helpful AQL error message: '{result.get('error')}'"
        }]
    })
    
    # Validate perplexity response
    validation = await mcp__response_validator__validate_llm_response(
        response=str(perplexity_check),
        validation_type="quality",
        prompt="AQL error message quality check"
    )

# Test 3: English to AQL with ambiguous input
result = await mcp__arango_tools__english_to_aql(
    "Find the thing that broke yesterday maybe"
)

# VALIDATION: Ensure generated AQL is valid
if result.get("success") and result.get("aql"):
    # Test the generated query
    test_query = await mcp__arango_tools__query(
        result["aql"],
        limit=1  # Just test syntax
    )
    
    # Validate query result format
    validation = await mcp__response_validator__validate_llm_response(
        response=json.dumps(test_query),
        validation_type="format"
    )
    assert json.loads(validation)["data"]["validation_passed"], "Generated AQL produced invalid results"

# Test 4: Edge with non-existent nodes
result = await mcp__arango_tools__edge(
    from_id="non_existent/12345",
    to_id="also_missing/67890",
    collection="error_causality"
)

# VALIDATION: Verify error mentions node validation
validation = await mcp__response_validator__validate_llm_response(
    response=json.dumps(result),
    validation_type="content",
    expected_content=["node", "exist", "not found"]
)
assert not result.get("success"), "Should fail with non-existent nodes"
```

**Expected Behavior**:
- Clear validation errors
- Helpful suggestions for fixes
- Graceful degradation
- All error messages must be validated for quality and usefulness

---

### 3. Concurrency Edge Cases

#### Scenario: Simultaneous Operations
```python
import asyncio

# Test 1: Parallel inserts with same key
async def parallel_inserts():
    tasks = []
    for i in range(100):
        task = mcp__arango_tools__insert(
            message=f"Concurrent insert {i}",
            _key="same_key"  # Conflict!
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

# Test 2: Read-modify-write race condition
async def race_condition():
    # Two processes trying to increment a counter
    doc = await mcp__arango_tools__query(
        "FOR d IN counters FILTER d._key == 'counter1' RETURN d"
    )
    
    # Simulate delay
    await asyncio.sleep(0.1)
    
    # Both try to update
    result = await mcp__arango_tools__upsert(
        collection="counters",
        search='{"_key": "counter1"}',
        update=f'{{"count": {doc["count"] + 1}}}'
    )
```

**Expected Behavior**:
- Proper conflict resolution
- Transaction support where needed
- Clear error messages for conflicts

---

### 4. Resource Exhaustion Edge Cases

#### Scenario: Memory and Connection Limits
```python
# Test 1: Memory exhaustion with large documents
huge_doc = await mcp__arango_tools__insert(
    message="Large document",
    metadata=json.dumps({"data": "x" * 100_000_000})  # 100MB string
)

# Test 2: Connection pool exhaustion
async def exhaust_connections():
    tasks = []
    for i in range(1000):  # More than connection pool size
        task = mcp__arango_tools__query(
            f"FOR doc IN log_events SKIP {i*100} LIMIT 100 RETURN doc"
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)

# Test 3: Graph traversal depth explosion
result = await mcp__arango_tools__query(
    "FOR v, e, p IN 1..100 OUTBOUND 'start/node' error_causality RETURN p"
)
```

**Expected Behavior**:
- Document size limits enforced
- Connection pooling works correctly
- Query complexity limits

---

### 5. Time-based Edge Cases

#### Scenario: Clock Skew and Time Zones
```python
# Test 1: Future timestamps
result = await mcp__arango_tools__insert(
    message="Future event",
    timestamp="2030-01-01T00:00:00Z"
)

# Test 2: Time series with gaps
analysis = await mcp__arango_tools__analyze_time_series(
    collection="metrics",
    metric_field="value",
    time_field="timestamp",
    window="hour"
    # What if there are 3-day gaps in data?
)

# Test 3: Pattern evolution with time travel
evolution = await mcp__arango_tools__track_pattern_evolution(
    collection="patterns",
    time_field="discovered_at",
    # What if times are out of order?
)
```

**Expected Behavior**:
- Handle time anomalies gracefully
- Fill gaps appropriately
- Warn about suspicious timestamps

---

### 6. Integration Failure Cascades

#### Scenario: Multi-Tool Pipeline Failures
```python
# Test: What happens when middle step fails?
async def pipeline_failure_test():
    try:
        # Step 1: Extract PDF (succeeds)
        pdf_result = await mcp__pdf_extractor__extract_pdf_content(
            pdf_path="/test/sample.pdf"
        )
        
        # Step 2: Structure document (fails due to malformed data)
        structured = await mcp__document_structurer__process_document_fully(
            marker_json_string="INVALID JSON{{{",  # Malformed!
        )
        
        # Step 3: Should never reach here
        stored = await mcp__arango_tools__insert(
            message="This should not execute",
            metadata=structured
        )
        
    except Exception as e:
        # How do we clean up step 1?
        # How do we report partial success?
        return {"partial_success": True, "failed_at": "structuring"}
```

**Expected Behavior**:
- Proper error propagation
- Cleanup of partial results
- Transaction-like rollback where possible

---

### 7. Visualization-Specific Edge Cases

#### Scenario: D3 Rendering Limits
```python
# Test 1: Cyclic graph visualization
cyclic_data = {
    "nodes": [
        {"id": "A"}, {"id": "B"}, {"id": "C"}
    ],
    "links": [
        {"source": "A", "target": "B"},
        {"source": "B", "target": "C"},
        {"source": "C", "target": "A"}  # Cycle!
    ]
}

result = await mcp__d3_visualizer__generate_graph_visualization(
    graph_data=json.dumps(cyclic_data),
    layout="tree"  # Trees can't handle cycles!
)

# Test 2: Disconnected components
disconnected = await mcp__arango_tools__get_visualization_data(
    query_type="network",
    collection="orphaned_nodes"  # No edges!
)

# Test 3: Self-referencing nodes
self_ref = await mcp__arango_tools__prepare_graph_for_d3(
    graph_name="recursive_dependencies"
)
```

**Expected Behavior**:
- Detect incompatible layouts
- Handle disconnected graphs
- Prevent infinite loops

---

### 8. Natural Language Edge Cases

#### Scenario: Ambiguous English Queries
```python
# Test 1: Vague temporal references
result = await mcp__arango_tools__english_to_aql(
    "Find errors from recently"  # How recent is "recently"?
)

# VALIDATION: Ensure AQL includes reasonable time bounds
if result.get("success") and result.get("aql"):
    # Check if query has time filter
    validation = await mcp__response_validator__validate_llm_response(
        response=result["aql"],
        validation_type="content",
        expected_content=["DATE", "timestamp", "FILTER"]
    )
    
    # Ask perplexity about reasonable interpretation
    interpretation_check = await mcp__perplexity_ask__perplexity_ask({
        "messages": [{
            "role": "user",
            "content": "In database queries, what is a reasonable time range for 'recently'? Provide specific hours/days."
        }]
    })
    
    # Validate perplexity's response is grounded
    validation2 = await mcp__response_validator__validate_llm_response(
        response=str(interpretation_check),
        validation_type="content",
        expected_content=["hours", "days", "24", "48", "7"]
    )

# Test 2: Typos and misspellings
result = await mcp__arango_tools__english_to_aql(
    "Fnd all erors with tipe AttributError"  # Typos
)

# VALIDATION: Check if tool corrected typos
if result.get("success"):
    # Verify corrected query contains proper terms
    validation = await mcp__response_validator__validate_llm_response(
        response=result["aql"],
        validation_type="content",
        expected_content=["error", "type", "AttributError", "Find"]
    )
    assert json.loads(validation)["data"]["validation_passed"], "Failed to correct typos"
    
    # Check explanation mentions corrections
    if result.get("explanation"):
        explanation_validation = await mcp__response_validator__validate_llm_response(
            response=result["explanation"],
            validation_type="content",
            expected_content=["corrected", "typo", "assumed"]
        )

# Test 3: Complex boolean logic
result = await mcp__arango_tools__english_to_aql(
    "Find all errors that are either TypeError or ValueError but not both and only if they happened on weekends"
)

# VALIDATION: Verify complex logic is properly structured
if result.get("success") and result.get("aql"):
    # Use LLM to validate logic correctness
    logic_check = await mcp__universal_llm_executor__execute_llm(
        llm="gemini",
        prompt=f"Does this AQL query correctly implement 'either TypeError or ValueError but not both and only on weekends'? Query: {result['aql']}",
        json_schema='{"correct": "boolean", "explanation": "string", "issues": "array"}'
    )
    
    # Parse and validate LLM response
    parsed = await mcp__universal_llm_executor__parse_llm_output(
        content=logic_check.get("stdout", "")
    )
    
    if parsed.get("success") and parsed.get("parsed"):
        # Validate the analysis makes sense
        analysis_validation = await mcp__response_validator__validate_llm_response(
            response=json.dumps(parsed["parsed"]),
            validation_type="content",
            expected_content=["correct", "explanation"]
        )

# Test 4: Non-existent fields
result = await mcp__arango_tools__english_to_aql(
    "Show me all documents with a flux_capacitor field"
)

# VALIDATION: Check for field existence warning
if result.get("success"):
    # First, check if field exists in schema
    schema_check = await mcp__arango_tools__schema()
    
    # Query should work but with warning
    test_result = await mcp__arango_tools__query(
        result["aql"],
        limit=10
    )
    
    # Validate warning about non-existent field
    if result.get("warnings") or test_result.get("warnings"):
        warning_validation = await mcp__response_validator__validate_llm_response(
            response=json.dumps(result.get("warnings", test_result.get("warnings", []))),
            validation_type="content",
            expected_content=["field", "exist", "flux_capacitor"]
        )
```

**Expected Behavior**:
- Reasonable defaults for vague terms
- Fuzzy matching for typos
- Clear explanation of query interpretation
- Warnings for non-existent fields
- All interpretations must be validated with external sources (perplexity/LLMs)

---

### 9. Security Edge Cases

#### Scenario: Injection Attempts
```python
# Test 1: AQL injection
result = await mcp__arango_tools__query(
    'FOR doc IN log_events FILTER doc.message == @message RETURN doc',
    '{"message": "\\" OR 1==1 OR \\""}'  # Injection attempt
)

# Test 2: Path traversal in file operations
result = await mcp__arango_tools__insert(
    message="Test",
    file_path="../../../../../../etc/passwd"  # Path traversal
)

# Test 3: Resource exhaustion via regex
result = await mcp__arango_tools__english_to_aql(
    "Find all errors matching " + "a?" * 1000 + "a" * 1000  # ReDoS
)
```

**Expected Behavior**:
- Proper parameterization prevents injection
- Path validation and sanitization
- Regex complexity limits

---

### 10. Recovery and Resilience Edge Cases

#### Scenario: Database Connection Issues
```python
# Test 1: Connection drops mid-query
# Simulate by killing ArangoDB during operation

# Test 2: Partial write failures
async def test_partial_writes():
    # Insert 1000 documents, fail at 500
    documents = [{"message": f"Doc {i}"} for i in range(1000)]
    
    # Simulate failure midway
    # How many were written? Can we resume?

# Test 3: Network timeout during large result retrieval
# Set unreasonably low timeout
```

**Expected Behavior**:
- Automatic retry with backoff
- Clear indication of partial success
- Ability to resume operations

---

## 11. LLM Response Validation Edge Cases

### Scenario: Preventing Hallucinations in Knowledge Base

```python
# Test 1: LLM generates solution that doesn't exist in corpus
llm_response = await mcp__universal_llm_executor__execute_llm(
    llm="gemini",
    prompt="How to fix CUDA out of memory error in PyTorch?",
    json_schema='{"solution": "string", "steps": "array", "references": "array"}'
)

# Parse the response
parsed = await mcp__universal_llm_executor__parse_llm_output(
    content=llm_response.get("stdout", "")
)

if parsed.get("success") and parsed.get("parsed"):
    solution_data = parsed["parsed"]
    
    # VALIDATION 1: Check if solution references exist in corpus
    for ref in solution_data.get("references", []):
        corpus_check = await mcp__arango_tools__query(
            "FOR doc IN research_cache FILTER doc.content =~ @ref RETURN doc",
            json.dumps({"ref": ref})
        )
        
        if not corpus_check.get("results"):
            # Reference not found - potential hallucination
            logger.warning(f"Reference '{ref}' not found in corpus")
    
    # VALIDATION 2: Validate solution steps are grounded
    for step in solution_data.get("steps", []):
        step_validation = await mcp__response_validator__validate_llm_response(
            response=step,
            validation_type="quality",
            prompt="PyTorch CUDA memory management step"
        )
        
        # Check for hallucination indicators
        validation_result = json.loads(step_validation)
        if validation_result["data"].get("quality_indicators", {}).get("has_disclaimers"):
            logger.warning(f"Step contains disclaimers: {step}")

# Test 2: Multi-model consensus validation
question = "What is the correct way to handle ArangoDB transaction deadlocks?"

# Get responses from multiple models
responses = await mcp__litellm_batch__process_batch_requests(
    json.dumps([
        {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": question}]},
        {"model": "claude-3-haiku-20240307", "messages": [{"role": "user", "content": question}]},
        {"model": "gemini-pro", "messages": [{"role": "user", "content": question}]}
    ])
)

# VALIDATION: Check consensus across models
if responses.get("success"):
    batch_results = json.loads(responses)
    
    # Extract key claims from each response
    claims_by_model = {}
    for result in batch_results:
        if result.get("status") == "success":
            model = result.get("model")
            response_text = result.get("response", {}).get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # Validate response format
            format_check = await mcp__response_validator__validate_llm_response(
                response=response_text,
                validation_type="content",
                expected_content=["transaction", "deadlock", "ArangoDB"]
            )
            
            # Extract claims (simplified - in practice use NLP)
            claims_by_model[model] = response_text
    
    # Check for contradictions
    if len(set(claims_by_model.values())) == len(claims_by_model):
        logger.warning("Models provided completely different answers - low confidence")

# Test 3: Validate against documentation
doc_question = "What is the syntax for ArangoDB UPSERT operation?"

# Get LLM response
llm_result = await mcp__universal_llm_executor__execute_llm(
    llm="claude",
    prompt=doc_question,
    json_schema='{"syntax": "string", "example": "string", "documentation_link": "string"}'
)

# VALIDATION: Cross-check with actual ArangoDB documentation
if llm_result.get("success"):
    parsed = await mcp__universal_llm_executor__parse_llm_output(
        content=llm_result.get("stdout", "")
    )
    
    if parsed.get("success") and parsed.get("parsed"):
        syntax_info = parsed["parsed"]
        
        # Search our knowledge base for UPSERT documentation
        doc_search = await mcp__arango_tools__query(
            "FOR doc IN glossary_terms FILTER doc.term =~ 'UPSERT' RETURN doc"
        )
        
        # Validate LLM response against stored documentation
        if doc_search.get("results"):
            stored_syntax = doc_search["results"][0].get("definition", "")
            
            # Use response validator to check consistency
            consistency_check = await mcp__response_validator__validate_llm_response(
                response=syntax_info.get("syntax", ""),
                validation_type="content",
                expected_content=["FOR", "IN", "INSERT", "UPDATE", "UPSERT"]
            )
            
            if not json.loads(consistency_check)["data"]["validation_passed"]:
                logger.error("LLM syntax doesn't match documented syntax")

# Test 4: Recursive validation with perplexity
complex_claim = "Redis Cluster uses a master-slave architecture with 16384 hash slots"

# First, ask LLM
llm_response = await mcp__universal_llm_executor__execute_llm(
    llm="gemini",
    prompt=f"Is this statement correct: {complex_claim}",
    json_schema='{"correct": "boolean", "explanation": "string", "corrections": "array"}'
)

# Parse response
parsed = await mcp__universal_llm_executor__parse_llm_output(
    content=llm_response.get("stdout", "")
)

if parsed.get("success") and parsed.get("parsed"):
    llm_answer = parsed["parsed"]
    
    # VALIDATION: Use perplexity to verify the LLM's answer
    perplexity_check = await mcp__perplexity_ask__perplexity_ask({
        "messages": [{
            "role": "user",
            "content": f"Verify this Redis Cluster information: {llm_answer.get('explanation', '')}"
        }]
    })
    
    # Validate perplexity response has citations
    perplexity_validation = await mcp__response_validator__validate_llm_response(
        response=str(perplexity_check),
        validation_type="content",
        expected_content=["Redis", "Cluster", "hash slots", "16384"]
    )
    
    # Final validation: Check both responses align
    if llm_answer.get("correct") and "16384" not in str(perplexity_check):
        logger.error("LLM and Perplexity disagree on hash slot count")
```

### Expected Behavior:
- All LLM-generated content must be validated against corpus
- Multi-model consensus required for critical information
- Documentation must be cross-referenced
- Perplexity used for external validation with citations
- Hallucination indicators trigger warnings
- Contradictions between sources are flagged

---

## Testing Checklist

### For Each Edge Case:
- [ ] Document expected behavior
- [ ] Implement test case
- [ ] Verify error handling
- [ ] Check error message clarity
- [ ] Ensure no data corruption
- [ ] Validate recovery mechanism
- [ ] Update documentation

### Performance Benchmarks:
- [ ] Query response time < 100ms for simple queries
- [ ] Visualization prep < 500ms for 1000 nodes
- [ ] Pattern detection < 5s for 10000 nodes
- [ ] English to AQL conversion < 200ms

### Resource Limits:
- [ ] Max document size: 16MB
- [ ] Max query result: 100MB
- [ ] Max visualization nodes: 5000
- [ ] Max concurrent connections: 100

---

## Failure Recovery Strategies

### 1. Graceful Degradation
- Fallback to simpler queries
- Reduce result set sizes
- Switch to alternative algorithms

### 2. Circuit Breakers
- Prevent cascade failures
- Temporary disable failing operations
- Automatic recovery detection

### 3. Monitoring and Alerts
- Track error rates
- Monitor performance degradation
- Alert on resource exhaustion

### 4. Data Integrity
- Transaction support where critical
- Validation before operations
- Audit trail for changes

## 12. Database Resilience and Recovery Scenarios

### Scenario: Database Connection Failures During Learning

```python
# Test 1: Connection loss during multi-step transaction
async def test_connection_resilience():
    # Start a learning session
    session_id = await mcp__arango_tools__insert(
        message="Starting critical learning session",
        metadata=json.dumps({"importance": "high"})
    )
    
    # Simulate connection failure scenarios
    try:
        # Attempt complex operation
        result = await mcp__arango_tools__query(
            "FOR doc IN log_events COLLECT type = doc.error_type INTO errors RETURN {type: type, count: LENGTH(errors)}",
            timeout=5  # Short timeout to simulate failure
        )
    except Exception as e:
        # VALIDATION: Ensure error is handled gracefully
        error_validation = await mcp__response_validator__validate_llm_response(
            response=str(e),
            validation_type="content",
            expected_content=["connection", "timeout", "retry"]
        )
        
        # Use perplexity to find best recovery strategy
        recovery_strategy = await mcp__perplexity_ask__perplexity_ask({
            "messages": [{
                "role": "user",
                "content": f"Best practice for recovering from ArangoDB connection error: {str(e)}"
            }]
        })
        
        # Implement retry with exponential backoff
        retry_count = 0
        while retry_count < 3:
            await asyncio.sleep(2 ** retry_count)
            try:
                # Retry the operation
                result = await mcp__arango_tools__query(
                    "FOR doc IN log_events LIMIT 1 RETURN doc"
                )
                if result.get("success"):
                    break
            except:
                retry_count += 1
        
        # Verify session integrity after recovery
        session_check = await mcp__arango_tools__query(
            f"FOR s IN agent_sessions FILTER s._id == '{session_id}' RETURN s"
        )
        assert session_check.get("results"), "Session lost during recovery"

# Test 2: Partial write during bulk operation
async def test_partial_write_recovery():
    documents = []
    for i in range(1000):
        documents.append({
            "message": f"Test document {i}",
            "batch_id": "test_batch_001",
            "sequence": i
        })
    
    # Insert documents in batches
    inserted_count = 0
    failed_at = -1
    
    for i in range(0, len(documents), 100):
        batch = documents[i:i+100]
        
        # Simulate failure at batch 5
        if i == 500:
            # Force a failure
            result = {"success": False, "error": "Connection reset"}
        else:
            # Normal insert
            batch_result = []
            for doc in batch:
                result = await mcp__arango_tools__insert(
                    message=doc["message"],
                    metadata=json.dumps(doc)
                )
                if result.get("success"):
                    batch_result.append(result["id"])
            
            result = {"success": True, "inserted": len(batch_result)}
        
        if result.get("success"):
            inserted_count += len(batch)
        else:
            failed_at = i
            break
    
    # VALIDATION: Verify partial write state
    if failed_at >= 0:
        # Check what was actually written
        verify_query = await mcp__arango_tools__query(
            "FOR doc IN log_events FILTER doc.batch_id == 'test_batch_001' COLLECT WITH COUNT INTO total RETURN total"
        )
        
        actual_count = verify_query.get("results", [0])[0]
        assert actual_count == failed_at, f"Expected {failed_at} documents, found {actual_count}"
        
        # Implement recovery - resume from where we left off
        resume_from = failed_at
        for i in range(resume_from, len(documents), 100):
            batch = documents[i:i+100]
            for doc in batch:
                # Add recovery marker
                doc["recovered"] = True
                doc["recovery_attempt"] = 1
                
                result = await mcp__arango_tools__insert(
                    message=doc["message"],
                    metadata=json.dumps(doc)
                )
        
        # Final validation
        final_check = await mcp__arango_tools__query(
            "FOR doc IN log_events FILTER doc.batch_id == 'test_batch_001' RETURN doc"
        )
        assert len(final_check.get("results", [])) == len(documents), "Recovery incomplete"

# Test 3: Concurrent access conflicts
async def test_concurrent_access():
    # Create a shared resource
    resource_id = await mcp__arango_tools__insert(
        message="Shared counter",
        metadata=json.dumps({"counter": 0, "lock": False})
    )
    
    # Simulate multiple agents trying to update
    async def update_counter(agent_id):
        for _ in range(10):
            # Read current value
            current = await mcp__arango_tools__query(
                f"FOR doc IN log_events FILTER doc._id == '{resource_id}' RETURN doc"
            )
            
            if current.get("results"):
                doc = current["results"][0]
                
                # Check if locked
                if doc.get("lock"):
                    await asyncio.sleep(0.1)
                    continue
                
                # Try to acquire lock
                lock_result = await mcp__arango_tools__upsert(
                    collection="log_events",
                    search=json.dumps({"_id": resource_id, "lock": False}),
                    update=json.dumps({"lock": True, "locked_by": agent_id})
                )
                
                if lock_result.get("success"):
                    # Update counter
                    new_value = doc.get("counter", 0) + 1
                    update_result = await mcp__arango_tools__upsert(
                        collection="log_events",
                        search=json.dumps({"_id": resource_id}),
                        update=json.dumps({
                            "counter": new_value,
                            "lock": False,
                            "last_updated_by": agent_id
                        })
                    )
    
    # Run concurrent updates
    agents = []
    for i in range(5):
        agents.append(update_counter(f"agent_{i}"))
    
    await asyncio.gather(*agents)
    
    # VALIDATION: Verify final state is consistent
    final_state = await mcp__arango_tools__query(
        f"FOR doc IN log_events FILTER doc._id == '{resource_id}' RETURN doc"
    )
    
    final_doc = final_state.get("results", [{}])[0]
    expected_count = 50  # 5 agents * 10 updates each
    actual_count = final_doc.get("counter", 0)
    
    # Some updates may have failed due to conflicts - that's OK
    assert actual_count > 0, "No updates succeeded"
    assert actual_count <= expected_count, "Counter exceeded maximum possible value"
    
    # Check for data consistency
    consistency_check = await mcp__universal_llm_executor__execute_llm(
        llm="gemini",
        prompt=f"Is this counter value reasonable given 5 agents each trying 10 updates with conflicts? Value: {actual_count}",
        json_schema='{"reasonable": "boolean", "explanation": "string"}'
    )

# Test 4: Recovery from corrupted data
async def test_data_corruption_recovery():
    # Insert some "corrupted" data
    corrupted_id = await mcp__arango_tools__insert(
        message="Corrupted entry",
        metadata='{"invalid": json"syntax"}'  # Invalid JSON
    )
    
    # Try to query the corrupted data
    try:
        result = await mcp__arango_tools__query(
            "FOR doc IN log_events FILTER doc.metadata != null RETURN doc"
        )
        
        # Process results, handling corruption
        clean_results = []
        corrupted_results = []
        
        for doc in result.get("results", []):
            try:
                # Try to parse metadata
                if isinstance(doc.get("metadata"), str):
                    json.loads(doc["metadata"])
                clean_results.append(doc)
            except json.JSONDecodeError:
                corrupted_results.append(doc)
                
                # Attempt to repair with json-repair
                repair_attempt = await mcp__response_validator__validate_llm_response(
                    response=doc.get("metadata", ""),
                    validation_type="format"
                )
                
                if json.loads(repair_attempt).get("data", {}).get("repaired"):
                    # Update with repaired data
                    await mcp__arango_tools__upsert(
                        collection="log_events",
                        search=json.dumps({"_id": doc["_id"]}),
                        update=json.dumps({
                            "metadata": json.loads(repair_attempt)["data"]["repaired"],
                            "repaired": True
                        })
                    )
        
        # Log corruption incident
        await mcp__arango_tools__insert(
            message="Data corruption detected and handled",
            level="WARNING",
            metadata=json.dumps({
                "corrupted_count": len(corrupted_results),
                "clean_count": len(clean_results),
                "repair_attempted": True
            })
        )
        
    except Exception as e:
        # Even if query fails, system should recover
        logger.error(f"Query failed on corrupted data: {e}")
        
        # Create recovery marker
        await mcp__arango_tools__insert(
            message="System recovered from corruption error",
            level="INFO",
            error_type="DataCorruption",
            resolved=True
        )
```

### Expected Behavior:
- Connection failures trigger automatic retry with backoff
- Partial writes are detected and can be resumed
- Concurrent access is handled with optimistic locking
- Corrupted data is quarantined and repaired when possible
- All recovery actions are logged for learning
- System remains operational despite failures

---

These edge cases ensure the system remains robust under adverse conditions and provides a good user experience even when things go wrong.