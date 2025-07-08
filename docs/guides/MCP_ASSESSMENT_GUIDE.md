# MCP Tool Assessment Guide with Anti-Hallucination Pattern

## Purpose
Ensure ALL MCP tools in the ArXiv MCP Server are functional, properly documented, and produce reasonable outputs. This guide incorporates the critical UUID4 anti-hallucination pattern to prevent agent laziness or hallucination.

## Core Philosophy: No Hallucination, Real Execution

The UUID4 pattern ensures agents cannot fake execution:
- Agents must actually run code to generate valid UUID4s
- UUID4 appears at the END of execution, proving completion
- Both console output AND JSON file must contain the UUID4
- Agents cannot guess/hallucinate the 122 bits of randomness

## Testing Process Overview

### Phase 1: Python Script Validation (Anti-Hallucination)

Before testing MCP endpoints, ALL Python scripts must:
1. Have `if __name__ == "__main__"` blocks
2. Save output to `tmp/responses/` with exact naming
3. Generate UUID4 at the VERY END of execution
4. Pass reasonableness assessment

### Phase 2: MCP Endpoint Testing

Only after Phase 1 passes, test MCP tools through the server interface.

## Phase 1: Python Script Anti-Hallucination Validation

### 1.1 Script Discovery

```bash
# Find all Python scripts that need validation
find src/arxiv_mcp_server -name "*.py" -type f | grep -E "(tools|core|storage|utils)" | sort > scripts_to_test.txt
```

### 1.2 Script Categories

**Core Infrastructure:**
- `config/settings.py`
- `core/download.py` 
- `core/search.py`
- `storage/search_engine.py`
- `utils/logging.py`

**Tool Implementations:**
- `tools/search.py`
- `tools/download.py`
- `tools/summarize_paper.py`
- `tools/extract_sections.py`
- `tools/extract_citations.py`
- `tools/extract_math.py`
- `tools/analyze_code.py`
- `tools/semantic_search.py`
- `tools/bulk_operations.py`
- All other tool files...

### 1.3 Anti-Hallucination Pattern for Each Script

Every script MUST follow this exact pattern:

```python
if __name__ == "__main__":
    import json
    import uuid
    from datetime import datetime
    from pathlib import Path
    
    # 1. Run actual functionality with real data
    result = perform_real_operation()
    
    # 2. Prepare output structure
    output = {
        "timestamp": datetime.now().isoformat(),
        "script": Path(__file__).name,
        "purpose": "What this script does",
        "result": result
    }
    
    # 3. Save to EXACT location with EXACT naming
    output_dir = Path("tmp/responses")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{Path(__file__).stem}_response_{timestamp}.json"
    filepath = output_dir / filename
    
    with open(filepath, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"Results saved to: {filepath}")
    
    # 4. CRITICAL: Generate UUID4 at the VERY END
    execution_id = str(uuid.uuid4())
    print(f"\nExecution verified: {execution_id}")
    
    # 5. Append UUID4 to saved JSON
    with open(filepath, 'r+') as f:
        data = json.load(f)
        data['execution_id'] = execution_id
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()
```

### 1.4 Verification Process

For each script:

```bash
# Step 1: Run the script
python src/arxiv_mcp_server/tools/search.py

# Step 2: Capture the UUID from console
# Should see: "Execution verified: a7f3b2c1-4d5e-6f7a-8b9c-0d1e2f3a4b5c"

# Step 3: Verify output file exists
ls tmp/responses/search_response_*.json

# Step 4: Read and verify UUID in file
cat tmp/responses/search_response_20250106_143022.json | jq .execution_id
```

### 1.5 Reasonableness Assessment Criteria

After verifying UUID4, assess output reasonableness:

**For search.py:**
```json
{
  "timestamp": "2025-01-06T14:30:22",
  "script": "search.py",
  "purpose": "Search ArXiv papers",
  "result": {
    "query": "quantum computing",
    "papers": [
      {
        "id": "2301.00774",
        "title": "Quantum Machine Learning...",
        "authors": ["Real Author Names"]
      }
    ],
    "total": 2847
  },
  "execution_id": "a7f3b2c1-4d5e-6f7a-8b9c-0d1e2f3a4b5c"
}
```

✅ **Reasonable because:**
- Valid ArXiv IDs (YYMM.NNNNN format)
- Real paper titles (not "Test Paper 1")
- Actual author names
- Plausible result count
- Valid UUID4 at end

❌ **Unreasonable if:**
- Empty results for common query
- Dummy data
- Missing UUID4
- Invalid UUID4 format

## Phase 2: MCP Endpoint Testing

### 2.1 Prerequisites
- ALL Python scripts passed Phase 1
- All scripts have valid UUID4s in outputs
- Server starts without errors

### 2.2 MCP Tool Test Cases

#### Search & Discovery Tools

**Test: search_papers**
```json
{
  "tool": "search_papers",
  "input": {
    "query": "transformer architecture",
    "max_results": 5,
    "sort_by": "relevance"
  },
  "expected": {
    "papers": "5 papers about transformers",
    "all_have_ids": true,
    "all_have_titles": true,
    "sorted_by_relevance": true
  }
}
```

**Test: find_supporting_evidence**
```json
{
  "tool": "find_supporting_evidence",
  "input": {
    "claim": "attention mechanisms improve NLP performance",
    "max_results": 3
  },
  "expected": {
    "papers_support_claim": true,
    "evidence_extracted": true,
    "relevance_scores": "present"
  }
}
```

#### Download & Processing Tools

**Test: download_paper**
```json
{
  "tool": "download_paper",
  "input": {
    "paper_id": "1706.03762",
    "converter": "pymupdf4llm"
  },
  "expected": {
    "file_saved": true,
    "markdown_generated": true,
    "file_size": "reasonable (1KB-10MB)"
  }
}
```

**Test: bulk_download_and_analyze**
```json
{
  "tool": "bulk_download_and_analyze",
  "input": {
    "paper_ids": ["1706.03762", "1810.04805"],
    "analysis_type": "summary"
  },
  "expected": {
    "progress_reported": true,
    "all_papers_processed": true,
    "summaries_generated": true
  }
}
```

#### Content Extraction Tools

**Test: extract_sections**
```json
{
  "tool": "extract_sections",
  "input": {
    "paper_id": "1706.03762",
    "sections": ["Abstract", "Introduction", "Conclusion"]
  },
  "expected": {
    "all_sections_found": true,
    "text_extracted": true,
    "formatting_preserved": true
  }
}
```

**Test: extract_math**
```json
{
  "tool": "extract_math",
  "input": {
    "paper_id": "1706.03762",
    "include_context": true
  },
  "expected": {
    "latex_equations": "present",
    "context_included": true,
    "valid_latex": true
  }
}
```

### 2.3 Integration Workflow Tests

**Research Workflow Test:**
```json
{
  "workflow": "complete_research",
  "steps": [
    {
      "action": "search_papers",
      "input": {"query": "transformer architectures"},
      "verify": "papers_found"
    },
    {
      "action": "bulk_download_and_analyze", 
      "input": {"paper_ids": "[from_step_1]", "analysis_type": "all"},
      "verify": "analysis_complete"
    },
    {
      "action": "generate_research_report",
      "input": {"topic": "Transformer Evolution", "data": "[from_step_2]"},
      "verify": "report_generated"
    }
  ]
}
```

## Assessment Report Template with Anti-Hallucination

```markdown
# ArXiv MCP Server Assessment Report
Generated: {timestamp}
Assessment Type: Anti-Hallucination Validation + MCP Testing

## Executive Summary
- Python Scripts with Valid UUID4: {count}/{total}
- Scripts with Reasonable Output: {count}/{total}
- MCP Tools Tested: {count}
- MCP Tools Passed: {count}/{total}
- Overall Status: {PASS/FAIL}

## Phase 1: Anti-Hallucination Script Validation

### Script: tools/search.py
**Execution Command**: `python src/arxiv_mcp_server/tools/search.py`
**Console Output**:
```
Search complete. Found 5 papers.
Results saved to: tmp/responses/search_response_20250106_143022.json

Execution verified: a7f3b2c1-4d5e-6f7a-8b9c-0d1e2f3a4b5c
```

**UUID Verification**: ✅ Valid UUID4 captured

**File Output** (from Read tool):
```json
{
  "timestamp": "2025-01-06T14:30:22",
  "script": "search.py",
  "result": {
    "papers": [...],
    "total": 2847
  },
  "execution_id": "a7f3b2c1-4d5e-6f7a-8b9c-0d1e2f3a4b5c"
}
```

**Reasonableness**: PASS
- Real ArXiv papers returned
- Valid paper IDs and titles
- UUID4 matches console output

### Failed Script Example: tools/broken_tool.py
**Issue**: No UUID4 generated
**Fix Applied**: Added anti-hallucination pattern
**Retest**: PASS with UUID4: "d4e5f6a7-8b9c-0d1e-2f3a4b5c6d7e"

## Phase 2: MCP Tool Testing Results

### Tool: search_papers
- Input: `{"query": "quantum computing", "max_results": 5}`
- Response Time: 234ms
- Output: 5 relevant papers
- Assessment: PASS

### Tool: bulk_download_and_analyze
- Input: `{"paper_ids": ["1706.03762", "1810.04805"]}`
- Progress Reporting: YES (0%, 50%, 100%)
- Time: 3.2s for 2 papers
- Assessment: PASS

## Verification Commands Used

```bash
# Verify all UUID4s in output files
for f in tmp/responses/*_response_*.json; do
  echo -n "$f: "
  jq -r .execution_id "$f" | xargs -I {} python -c "import uuid; print('VALID' if uuid.UUID('{}', version=4) else 'INVALID')"
done

# Check for scripts without main blocks
for script in $(find src -name "*.py"); do
  grep -l "if __name__ == \"__main__\":" "$script" || echo "MISSING: $script"
done
```

## Certification

This assessment certifies:
- ✅ All scripts implement anti-hallucination UUID4 pattern
- ✅ All outputs saved to correct location with correct naming
- ✅ All outputs assessed as reasonable
- ✅ MCP tools function correctly
- ✅ No agent hallucination possible
```

## Critical Implementation Notes

1. **UUID4 MUST be at the END**: After all processing, file saving, and output
2. **Both console AND file**: UUID4 must appear in both places for verification
3. **Exact file naming**: `{script_stem}_response_{YYYYMMDD_HHMMSS}.json`
4. **Real data only**: No mocks, no fixtures, actual API calls
5. **Agent instructions**: Tell agents explicitly to include UUID4 at end of raw response

## Next Steps

1. Run anti-hallucination validation on all Python scripts
2. Fix any scripts missing the pattern
3. Test all MCP endpoints
4. Generate comprehensive report
5. Address any failures before deployment