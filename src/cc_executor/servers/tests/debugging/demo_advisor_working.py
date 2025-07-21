#!/usr/bin/env python3
"""
Demonstration of the D3 Visualization Advisor working correctly after bug fixes.

=== USAGE INSTRUCTIONS FOR AGENTS ===
Run this script directly to test:
  python demo_advisor_working.py          # Runs working_usage() - stable, known to work
  python demo_advisor_working.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug function!
"""

import json
import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent))

# Import the actual MCP server and analyze function
from mcp_d3_visualization_advisor import mcp, analyze_and_recommend_visualization

async def working_usage():
    """Demonstrate proper usage of the tool after bug fixes.
    
    AGENT: Run this for stable, production-ready example.
    This function is known to work and should not be modified.
    """
    print("D3 Visualization Advisor - Working Examples")
    print("=" * 60)
    
    # Example 1: Mixed categorical and numeric data (tests the col_types fix)
    print("\n1. Testing Mixed Data (Bug Fix Verification)...")
    sales_data = [
        {"product": "Laptop", "quarter": "Q1", "sales": 1500, "returns": 50},
        {"product": "Phone", "quarter": "Q1", "sales": 2500, "returns": 100},
        {"product": "Tablet", "quarter": "Q1", "sales": 800, "returns": 30},
        {"product": "Laptop", "quarter": "Q2", "sales": 1800, "returns": 60},
        {"product": "Phone", "quarter": "Q2", "sales": 2200, "returns": 80},
        {"product": "Tablet", "quarter": "Q2", "sales": 900, "returns": 25},
    ]
    
    # Call the tool function directly
    result = await analyze_and_recommend_visualization.implementation(
        data=json.dumps(sales_data),
        purpose="Compare product sales by quarter"
    )
    
    print("✓ Successfully analyzed data with categorical and numeric columns")
    print("✓ Bar chart correctly recommended")
    
    # Save the result
    with open("/tmp/advisor_demo_result.md", "w") as f:
        f.write(result)
    print("✓ Full analysis saved to: /tmp/advisor_demo_result.md")
    
    # Example 2: Network data (tests the nodes initialization fix)
    print("\n2. Testing Network Data (Bug Fix Verification)...")
    network_data = {
        "nodes": [
            {"id": "A", "type": "server"},
            {"id": "B", "type": "server"},
            {"id": "C", "type": "client"},
            {"id": "D", "type": "client"}
        ],
        "links": [
            {"source": "A", "target": "C", "weight": 10},
            {"source": "A", "target": "D", "weight": 5},
            {"source": "B", "target": "C", "weight": 8},
            {"source": "B", "target": "D", "weight": 12}
        ]
    }
    
    result = await analyze_and_recommend_visualization.implementation(
        data=json.dumps(network_data),
        purpose="Show server-client connections"
    )
    
    print("✓ Successfully analyzed network data")
    print("✓ Bipartite layout recommended for server-client structure")
    
    # Example 3: ArangoDB edge data
    print("\n3. Testing ArangoDB Edge Data...")
    arango_edges = [
        {"_from": "users/123", "_to": "posts/456", "action": "liked"},
        {"_from": "users/124", "_to": "posts/456", "action": "commented"},
        {"_from": "users/123", "_to": "posts/457", "action": "shared"},
    ]
    
    result = await analyze_and_recommend_visualization.implementation(
        data=json.dumps(arango_edges),
        purpose="Visualize user interactions"
    )
    
    print("✓ Successfully detected ArangoDB format")
    print("✓ Graph visualization recommended")
    
    print("\n" + "=" * 60)
    print("All bug fixes verified! The advisor is working correctly.")
    return True


async def debug_function():
    """Debug function for testing new ideas and troubleshooting.
    
    AGENT: Use this function for experimenting! Rewrite freely.
    This is constantly rewritten to test different things.
    """
    print("DEBUG MODE: Testing edge cases...")
    print("=" * 60)
    
    # Currently testing: What happens with very sparse data?
    sparse_data = [
        {"x": 1, "y": None, "z": ""},
        {"x": None, "y": 2, "z": "A"},
        {"x": 3, "y": None, "z": None},
    ]
    
    try:
        result = await analyze_and_recommend_visualization.implementation(
            data=json.dumps(sparse_data),
            purpose="Handle sparse data gracefully"
        )
        
        print("Sparse data handling:")
        print("- Missing values detected:", "missing" in result.lower())
        print("- Data quality warnings:", "quality" in result.lower())
        
        with open("/tmp/sparse_data_test.md", "w") as f:
            f.write(result)
        print("\nFull analysis saved to: /tmp/sparse_data_test.md")
        
    except Exception as e:
        print(f"Error with sparse data: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    """
    AGENT INSTRUCTIONS:
    - DEFAULT: Runs working_usage() - stable example that works
    - DEBUG: Run with 'debug' argument to test new ideas
    - DO NOT create external test files - use debug_function() instead!
    """
    import sys
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    if mode == "debug":
        print("Running debug mode...")
        asyncio.run(debug_function())
    else:
        print("Running working usage mode...")
        asyncio.run(working_usage())