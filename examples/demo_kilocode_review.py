#!/usr/bin/env python3
"""
Demonstration of kilocode-review MCP tools usage.

This script shows how an AI agent would use the kilocode-review
MCP tools to perform self-correction after completing a coding task.

=== USAGE INSTRUCTIONS FOR AGENTS ===
Run this script directly to test:
  python demo_kilocode_review.py          # Runs working_usage() - stable example
  python demo_kilocode_review.py debug    # Runs debug_function() - for testing

DO NOT create separate test files - use the debug function!
"""

import json
import time
import sys
from pathlib import Path


async def working_usage():
    """Demonstrate proper usage of kilocode-review MCP tools.
    
    AGENT: Run this for stable, production-ready example.
    This function demonstrates the full workflow.
    """
    print("=== Kilocode Review MCP Tools Demo ===\n")
    
    # Step 1: Identify files to review
    # In a real scenario, the agent would track files it modified
    files_to_review = [
        "src/cc_executor/servers/mcp_tool_journey.py",
        "src/cc_executor/servers/mcp_kilocode_review.py"
    ]
    
    print("1. Files to review:")
    for f in files_to_review:
        print(f"   - {f}")
    
    # Step 2: Start the review
    print("\n2. Starting kilocode review...")
    
    # This simulates calling the MCP tool
    # In reality, the agent would call: mcp__kilocode-review__start_review
    review_request = {
        "files": " ".join(files_to_review),
        "focus": "maintainability",  # Optional focus area
        "severity": "medium"         # Minimum severity level
    }
    
    print(f"   Request: {json.dumps(review_request, indent=2)}")
    
    # Simulated response from start_review
    review_response = {
        "success": True,
        "review_id": "docs/code_review/20250117_173600_demo123",
        "message": "Review started successfully. Use get_review_results with the review_id to fetch the summary."
    }
    
    print(f"\n   Response: {json.dumps(review_response, indent=2)}")
    
    # Step 3: Wait for review completion
    print("\n3. Waiting for review to complete...")
    print("   (In production, wait 2-3 minutes)")
    
    # Simulate waiting
    for i in range(3):
        time.sleep(1)
        print(f"   ... {i+1} seconds")
    
    # Step 4: Retrieve results
    print("\n4. Retrieving review results...")
    
    # This simulates calling: mcp__kilocode-review__get_review_results
    results_request = {
        "review_id": review_response["review_id"]
    }
    
    # Simulated results
    review_results = {
        "success": True,
        "results": {
            "summary": "Review completed successfully. Found 2 actionable fixes.",
            "actionable_fixes": """### 1. Missing JSON Serialization in mcp_tool_journey.py
**File:** src/cc_executor/servers/mcp_tool_journey.py:155
**Current:**
```python
return {
    "journey_id": journey_id,
    "recommended_sequence": recommended_sequence
}
```
**Fixed:**
```python
return json.dumps({
    "journey_id": journey_id,
    "recommended_sequence": recommended_sequence
}, indent=2)
```
**Rationale:** FastMCP tools must return JSON strings, not dict objects.

### 2. Thread Safety Issue in EmbeddingProcessor
**File:** src/cc_executor/servers/mcp_tool_journey.py:86
**Current:** Missing lock acquisition before checking model_loaded
**Fixed:** Already correctly implemented with double-checked locking pattern
**Rationale:** Prevents race conditions in concurrent environments.""",
            "incompatible_suggestions": """### Standard Linter Suggestions Not Applied
1. **Import Grouping:** Project uses custom import order for MCP servers
2. **Type Hints:** Some dynamic MCP decorators obscure types by design""",
            "context_applied": """### Context Rules Applied
- FastMCP requirement: All tool returns must be JSON strings
- MCP server pattern: Lazy loading for heavy resources
- Thread safety: Required for concurrent request handling"""
        }
    }
    
    print(f"\n   Results summary: {review_results['results']['summary']}")
    
    # Step 5: Apply fixes
    print("\n5. Applying actionable fixes...")
    
    if review_results["results"]["actionable_fixes"]:
        print("   Found actionable fixes to apply:")
        # Parse and display the fixes
        fixes = review_results["results"]["actionable_fixes"]
        print(f"   {fixes[:200]}...")  # Show preview
        
        # In reality, the agent would:
        # 1. Parse the markdown to extract file paths and changes
        # 2. Open each file with the Edit tool
        # 3. Apply the changes exactly as specified
        
        print("\n   ✓ Applied all fixes successfully")
    else:
        print("   No actionable fixes required")
    
    # Step 6: Complete
    print("\n6. Task completed!")
    print("   - Code has been reviewed")
    print("   - All actionable fixes have been applied")
    print("   - Project constraints were respected")
    
    return True


async def debug_function():
    """Debug function for testing edge cases.
    
    AGENT: Use this function for experimenting! Rewrite freely.
    Currently testing: Error handling scenarios
    """
    print("=== Debug Mode: Testing Error Scenarios ===\n")
    
    # Test 1: Empty file list
    print("1. Testing empty file list:")
    empty_request = {
        "files": ""
    }
    # Expected: {"success": False, "error": "No files provided for review."}
    
    # Test 2: Non-existent review ID
    print("\n2. Testing non-existent review ID:")
    bad_results_request = {
        "review_id": "docs/code_review/nonexistent"
    }
    # Expected: {"success": False, "error": "Review directory not found: ..."}
    
    # Test 3: Multiple focus areas
    print("\n3. Testing with security focus:")
    security_request = {
        "files": "src/cc_executor/servers/*.py",
        "focus": "security",
        "severity": "critical"
    }
    print(f"   Request: {json.dumps(security_request, indent=2)}")
    
    print("\n✓ Debug scenarios completed")


if __name__ == "__main__":
    """
    AGENT INSTRUCTIONS:
    - DEFAULT: Runs working_usage() - stable example that works
    - DEBUG: Run with 'debug' argument to test new ideas
    - DO NOT create external test files - use debug_function() instead!
    """
    import asyncio
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    if mode == "debug":
        print("Running debug mode...")
        asyncio.run(debug_function())
    else:
        print("Running working usage mode...")
        asyncio.run(working_usage())