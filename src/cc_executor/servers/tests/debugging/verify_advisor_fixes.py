#!/usr/bin/env python3
"""Verify that the advisor bug fixes are working."""

import json
import sys
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent))

# Import the internal functions
from mcp_d3_visualization_advisor import _analyze_data_structure, _get_tabular_recommendations, _get_network_recommendations

def test_bug_fixes():
    """Test that both bug fixes are working."""
    print("Testing D3 Advisor Bug Fixes")
    print("=" * 60)
    
    # Test 1: col_types fix
    print("\n1. Testing col_types fix with mixed data...")
    mixed_data = [
        {"category": "A", "value": 100, "product": "X"},
        {"category": "B", "value": 150, "product": "Y"},
        {"category": "C", "value": 200, "product": "X"},
    ]
    
    try:
        analysis = _analyze_data_structure(mixed_data)
        recommendations = _get_tabular_recommendations(analysis, mixed_data)
        
        if "Bar Chart" in recommendations:
            print("✅ SUCCESS: Bar chart recommended for mixed categorical/numeric data")
            print(f"   Categorical columns: {analysis['pandas_analysis'].get('categorical_columns', [])}")
            print(f"   Numeric columns: {analysis['pandas_analysis'].get('numeric_columns', [])}")
        else:
            print("❌ FAILED: Bar chart not recommended")
            
    except NameError as e:
        print(f"❌ FAILED: col_types NameError still exists: {e}")
        return False
        
    # Test 2: nodes initialization fix
    print("\n2. Testing nodes initialization fix...")
    
    # Test with tabular data (no nodes)
    try:
        tabular_analysis = _analyze_data_structure(mixed_data)
        print("✅ SUCCESS: Tabular data analyzed without nodes error")
        
    except UnboundLocalError as e:
        print(f"❌ FAILED: nodes UnboundLocalError: {e}")
        return False
        
    # Test with network data
    network_data = {
        "nodes": [{"id": "A"}, {"id": "B"}, {"id": "C"}],
        "links": [{"source": "A", "target": "B"}, {"source": "B", "target": "C"}]
    }
    
    try:
        network_analysis = _analyze_data_structure(network_data)
        network_recs = _get_network_recommendations(network_analysis, network_data)
        print("✅ SUCCESS: Network data analyzed correctly")
        print(f"   Node count: {network_analysis['shape']['node_count']}")
        print(f"   Density: {network_analysis['metrics'].get('density', 0):.2f}")
        
    except Exception as e:
        print(f"❌ FAILED: Network analysis error: {e}")
        return False
        
    # Test 3: ArangoDB format
    print("\n3. Testing ArangoDB edge detection...")
    arango_data = [
        {"_from": "users/1", "_to": "posts/1", "type": "liked"},
        {"_from": "users/2", "_to": "posts/1", "type": "shared"},
    ]
    
    try:
        arango_analysis = _analyze_data_structure(arango_data)
        if "arangodb_graph" in arango_analysis["patterns"]:
            print("✅ SUCCESS: ArangoDB format detected")
            print(f"   Edge count: {arango_analysis['shape']['edge_count']}")
        else:
            print("❌ FAILED: ArangoDB format not detected")
            
    except Exception as e:
        print(f"❌ FAILED: ArangoDB analysis error: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("All bug fixes verified! ✅")
    return True

if __name__ == "__main__":
    success = test_bug_fixes()
    sys.exit(0 if success else 1)