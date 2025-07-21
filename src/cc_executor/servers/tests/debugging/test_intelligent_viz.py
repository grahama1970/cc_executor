#!/usr/bin/env python3
"""Test intelligent visualization decision-making with edge cases.

This script tests that the intelligent visualization correctly:
1. Returns tables for excessive nodes (>500)
2. Chooses matrix visualization for dense graphs
3. Detects bipartite structures
4. Handles temporal data appropriately
"""

import json
import asyncio
from pathlib import Path
import sys

# Add the servers directory to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_d3_visualizer import D3Visualizer

def test_edge_cases():
    """Test various edge cases for intelligent visualization."""
    # Create a visualizer instance
    visualizer = D3Visualizer()
    
    print("Testing Intelligent Visualization Edge Cases")
    print("=" * 50)
    
    # Test 1: Excessive nodes - should return table
    print("\n1. Testing excessive nodes (600 nodes)...")
    large_data = {
        "nodes": [{"id": f"n{i}", "label": f"Node {i}", "type": f"type{i%5}"} 
                  for i in range(600)],
        "links": [{"source": f"n{i}", "target": f"n{(i+1)%600}"} 
                  for i in range(600)]
    }
    
    result = visualizer.generate_intelligent_visualization(
        data=large_data,
        title="Large Network Test"
    )
    
    if result['success']:
        analysis = result['analysis']
        print(f"  Node count: {analysis['key_metrics']['node_count']}")
        print(f"  Visualization complexity: {analysis['visualization_complexity']}")
        print(f"  Recommended: {analysis['recommended_viz']}")
        print(f"  Created file: {result['filename']}")
    else:
        print(f"  ✗ Failed to generate visualization: {result.get('error', 'Unknown error')}")
    
    # Check if it created a table
    if result['success']:
        file_path = str(Path("/tmp/visualizations") / result['filename'])
        with open(file_path, 'r') as f:
            content = f.read()
            if '<table' in content.lower():
                print("  ✓ Correctly generated table for excessive nodes")
            else:
                print("  ✗ Failed to generate table")
    
    # Test 2: Dense graph - should use matrix
    print("\n2. Testing dense graph (20 nodes, density > 0.3)...")
    dense_data = {
        "nodes": [{"id": f"n{i}", "label": f"Node {i}"} for i in range(20)],
        "links": []
    }
    
    # Create dense connections (>0.3 density)
    for i in range(20):
        for j in range(i+1, min(i+8, 20)):  # Connect each node to next 7
            dense_data["links"].append({
                "source": f"n{i}", 
                "target": f"n{j}",
                "value": 1
            })
    
    result = visualizer.generate_intelligent_visualization(
        data=dense_data,
        title="Dense Network Test"
    )
    
    if result['success']:
        analysis = result['analysis']
        print(f"  Density: {analysis['key_metrics']['density']:.3f}")
        print(f"  Recommended: {analysis['recommended_viz']}")
        print(f"  Visualization type: {result['visualization_type']}")
    
    # Test 3: Bipartite graph
    print("\n3. Testing bipartite structure...")
    bipartite_data = {
        "nodes": [
            {"id": "u1", "label": "User 1", "type": "user"},
            {"id": "u2", "label": "User 2", "type": "user"},
            {"id": "u3", "label": "User 3", "type": "user"},
            {"id": "p1", "label": "Product 1", "type": "product"},
            {"id": "p2", "label": "Product 2", "type": "product"},
            {"id": "p3", "label": "Product 3", "type": "product"}
        ],
        "links": [
            {"source": "u1", "target": "p1"},
            {"source": "u1", "target": "p2"},
            {"source": "u2", "target": "p2"},
            {"source": "u2", "target": "p3"},
            {"source": "u3", "target": "p1"},
            {"source": "u3", "target": "p3"}
        ]
    }
    
    result = visualizer.generate_intelligent_visualization(
        data=bipartite_data,
        title="Bipartite Test"
    )
    
    if result['success']:
        analysis = result['analysis']
        if 'bipartite' in analysis['patterns']:
            print("  ✓ Correctly detected bipartite structure")
        else:
            print("  ✗ Failed to detect bipartite structure")
        print(f"  Patterns: {analysis['patterns']}")
        print(f"  Visualization type: {result['visualization_type']}")
    
    # Test 4: Temporal data
    print("\n4. Testing temporal data...")
    temporal_data = {
        "nodes": [
            {"id": "e1", "label": "Event 1", "timestamp": "2024-01-01T10:00:00Z"},
            {"id": "e2", "label": "Event 2", "timestamp": "2024-01-02T10:00:00Z"},
            {"id": "e3", "label": "Event 3", "timestamp": "2024-01-03T10:00:00Z"},
            {"id": "e4", "label": "Event 4", "timestamp": "2024-01-04T10:00:00Z"}
        ],
        "links": [
            {"source": "e1", "target": "e2"},
            {"source": "e2", "target": "e3"},
            {"source": "e3", "target": "e4"}
        ]
    }
    
    result = visualizer.generate_intelligent_visualization(
        data=temporal_data,
        title="Temporal Test"
    )
    
    if result['success']:
        analysis = result['analysis']
        if 'temporal' in analysis['patterns']:
            print("  ✓ Correctly detected temporal pattern")
        else:
            print("  ✗ Failed to detect temporal pattern")
        print(f"  Patterns: {analysis['patterns']}")
        print(f"  Visualization type: {result['visualization_type']}")
    
    # Test 5: Empty data
    print("\n5. Testing empty data handling...")
    empty_data = {"nodes": [], "links": []}
    
    result = visualizer.generate_intelligent_visualization(
        data=empty_data,
        title="Empty Test"
    )
    
    if result['success']:
        print(f"  Handled empty data: {result['visualization_type']}")
    else:
        print(f"  ✗ Failed on empty data: {result.get('error', 'Unknown error')}")
    
    # Test 6: Analysis goal influence
    print("\n6. Testing analysis goal influence...")
    error_data = {
        "nodes": [
            {"id": "e1", "label": "Error A", "type": "error", "cluster": "auth"},
            {"id": "e2", "label": "Error B", "type": "error", "cluster": "db"},
            {"id": "s1", "label": "Fix A", "type": "solution"},
            {"id": "s2", "label": "Fix B", "type": "solution"}
        ],
        "links": [
            {"source": "e1", "target": "s1", "type": "fixes"},
            {"source": "e2", "target": "s2", "type": "fixes"}
        ]
    }
    
    result = visualizer.generate_intelligent_visualization(
        data=error_data,
        title="Error Analysis",
        analysis_goal="show error clusters and their solutions"
    )
    
    if result['success']:
        print(f"  Goal-influenced viz type: {result['visualization_type']}")
        print(f"  Analysis goal worked: {'cluster' in result['visualization_type'].lower()}")
    
    print("\n" + "=" * 50)
    print("Edge case testing complete!")
    
    # Clean up test files
    print("\nCleaning up test files...")
    import shutil
    viz_dir = Path("/tmp/visualizations")
    if viz_dir.exists():
        for file in viz_dir.glob("*Test*.html"):
            file.unlink()
            print(f"  Removed: {file.name}")

if __name__ == "__main__":
    test_edge_cases()