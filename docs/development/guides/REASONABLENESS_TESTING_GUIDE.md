# Reasonableness-Based Testing Approach

## Core Philosophy
**No pytest, No unittest** - We use real execution with reasonableness assessment because:
- Agents cannot reliably understand mock objects or test fixtures
- Real data produces real results that can be verified
- Each script demonstrates its actual functionality
- Outputs are saved with UUID4 keys for verification

## The Approach

### 1. Every Python Script Must Demonstrate Itself

```python
if __name__ == "__main__":
    import json
    import uuid
    from datetime import datetime
    from pathlib import Path
    
    # Generate unique execution ID
    execution_id = str(uuid.uuid4())
    
    # Run real functionality with real data
    test_input = "real data that makes sense"
    result = actual_function(test_input)
    
    # Save with UUID for verification
    output = {
        "execution_id": execution_id,
        "timestamp": datetime.now().isoformat(),
        "script": __file__,
        "input": test_input,
        "output": result,
        "success": True
    }
    
    # Save to tmp/responses/
    filename = f"tmp/responses/{Path(__file__).stem}_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"✓ Execution {execution_id} complete. Results: {filename}")
```

### 2. Reasonableness Assessment (Not Testing)

We assess outputs by asking:
- Does this output make sense for what the script does?
- Is there real data, not placeholders?
- Did actual processing occur?
- Are the values within expected ranges?

**NOT** by:
- Checking assertions
- Running test suites
- Mocking dependencies
- Using fixtures

### 3. UUID4 Verification

The execution_id serves as proof:
```json
{
  "execution_id": "a7f3b2c1-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
  "timestamp": "2025-01-06T10:30:00",
  "output": {
    "papers_found": 5,
    "search_term": "quantum computing",
    "results": [...]
  }
}
```

This UUID proves:
- The execution actually happened
- We can trace specific runs
- No hallucination of results

## Example: Search Tool Assessment

### Step 1: Run the Script
```bash
python src/arxiv_mcp_server/tools/search.py
```

### Step 2: Read the Output
```bash
cat tmp/responses/search_response_20250106_103000.json
```

### Step 3: Assess Reasonableness

**REASONABLE Output**:
```json
{
  "execution_id": "d4f5e6a7-8b9c-0d1e-2f3a-4b5c6d7e8f9a",
  "timestamp": "2025-01-06T10:30:00",
  "input": "quantum computing applications",
  "output": {
    "papers": [
      {
        "id": "2301.00774",
        "title": "Quantum Machine Learning: What Quantum Computing...",
        "authors": ["Maria Schuld", "Francesco Petruccione"],
        "abstract": "Machine learning algorithms based on quantum..."
      }
    ],
    "total_results": 2847
  }
}
```

**Why it's reasonable**:
- Real ArXiv paper IDs (YYMM.NNNNN format)
- Actual paper titles (not "Test Paper 1")
- Real author names
- Substantive abstracts
- Plausible result count

**UNREASONABLE Output**:
```json
{
  "execution_id": "12345",  // Not a real UUID4
  "output": "Not implemented"  // No actual results
}
```

## The Assessment Process

### Phase 1: Individual Script Validation
```python
# For each script in the codebase
for script in find_all_python_scripts():
    # 1. Run it
    result = run_script(script)
    
    # 2. Check output file exists
    output_file = find_latest_output(script)
    
    # 3. Load and assess
    data = json.load(output_file)
    
    # 4. Check reasonableness
    is_reasonable = assess_output_reasonableness(data)
    
    # 5. If unreasonable, fix and retry
    if not is_reasonable:
        fix_script(script)
        # Retry up to 3 times
```

### Phase 2: MCP Endpoint Validation
Only after all scripts produce reasonable outputs:
```python
# Start MCP server
server = start_mcp_server()

# Test each endpoint with real data
for endpoint in mcp_endpoints:
    result = call_endpoint(endpoint, real_input)
    assess_reasonableness(result)
```

### Phase 3: Workflow Integration
Test real research workflows:
1. Search for papers on "transformer architectures"
2. Download the top 3 results
3. Extract key findings
4. Generate a research report

Each step must produce reasonable, verifiable output.

## Key Principles

### 1. Real Data Only
- No mock data
- No test fixtures  
- No synthetic examples
- Use actual ArXiv papers

### 2. Execution Proof
- Every run gets a UUID4
- Timestamp everything
- Save all outputs
- Enable verification

### 3. Reasonableness Over Correctness
We ask "Does this make sense?" not "Is this exactly correct?"

Examples:
- A search returning 0-10000 results is reasonable
- A paper ID like "2301.00774" is reasonable
- An empty author list is unreasonable
- A 10GB response file is unreasonable

### 4. Fix, Don't Test
When output is unreasonable:
1. Identify what's wrong
2. Fix the actual code
3. Run again with real data
4. Assess new output

## Anti-Patterns to Avoid

### ❌ Don't Write Traditional Tests
```python
# WRONG - Don't do this
def test_search():
    mock_api = Mock()
    mock_api.search.return_value = [...]
    assert search(mock_api, "test") == expected
```

### ❌ Don't Use Fixtures
```python
# WRONG - Don't do this
@pytest.fixture
def sample_paper():
    return {"id": "test123", "title": "Test"}
```

### ✅ Do Write Demonstration Code
```python
# RIGHT - Do this
if __name__ == "__main__":
    # Search for real papers
    results = search("quantum computing", max_results=5)
    
    # Save real results
    save_output({
        "execution_id": str(uuid.uuid4()),
        "results": results
    })
```

## Verification Commands

After running assessments, verify execution happened:

```bash
# Check for UUID in output
grep -r "execution_id" tmp/responses/ | grep -E "[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"

# Verify timestamps are recent
find tmp/responses -name "*.json" -mtime -1 | xargs jq '.timestamp'

# Check file sizes are reasonable
find tmp/responses -name "*.json" -size +1k -size -1M | wc -l
```

## Summary

This approach ensures:
1. **Real Execution**: No mocking, real data only
2. **Verifiable Results**: UUID4 + timestamps prove execution
3. **Reasonableness**: Human-like assessment of outputs
4. **Practical Focus**: Does it work with real data?
5. **Agent-Friendly**: No complex test frameworks to understand

The goal is working code that produces reasonable outputs, not passing test suites.