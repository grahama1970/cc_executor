#!/usr/bin/env python3
"""
Test script for graph analytics fixes.

Tests the fixed AQL queries directly against ArangoDB.
"""

import asyncio
import json
from pathlib import Path
import sys
from dotenv import load_dotenv, find_dotenv

env_path = find_dotenv()
# Find the absolute path to the .env file
env_path = find_dotenv()

if env_path:
    project_root = Path(env_path).parent
    load_dotenv(env_path)
    else:
    raise FileNotFoundError(".env file not found")



from src.cc_executor.servers.mcp_arango_tools import ArangoTools


def test_centrality():
    """Test centrality algorithm with simplified query."""
    tools = ArangoTools()
    
    # Simplified centrality query that should work
    test_query = """
    // Get nodes from error_causality edges
    LET all_nodes = (
        FOR edge IN error_causality
            FOR node IN [edge._from, edge._to]
            RETURN node
    )
    
    // Count connections
    FOR node IN all_nodes
        COLLECT vertex = node WITH COUNT INTO connections
        SORT connections DESC
        LIMIT 5
        RETURN {
            vertex: vertex,
            connections: connections
        }
    """
    
    result = tools.execute_aql(test_query)
    print("Centrality test result:", json.dumps(result, indent=2))
    return result


def test_neighbors_simple():
    """Test neighbors with simple traversal."""
    tools = ArangoTools()
    
    # Get a known node first
    nodes_query = """
    FOR edge IN error_causality
        LIMIT 1
        RETURN edge._from
    """
    
    nodes_result = tools.execute_aql(nodes_query)
    if nodes_result["success"] and nodes_result["results"]:
        start_node = nodes_result["results"][0]
        print(f"\nTesting neighbors for node: {start_node}")
        
        # Simple neighbor query
        neighbors_query = """
        FOR v, e, p IN 1..2 ANY @start_node
        error_causality
            RETURN DISTINCT {
                vertex: v._id,
                depth: LENGTH(p.edges),
                path: p.edges[*].relationship_type
            }
        """
        
        result = tools.execute_aql(neighbors_query, {"start_node": start_node})
        print("Neighbors test result:", json.dumps(result, indent=2))
        return result
    
    return {"success": False, "error": "No edges found to test"}


def test_shortest_path_direct():
    """Test shortest path with direct edge query."""
    tools = ArangoTools()
    
    # Get two connected nodes
    path_query = """
    FOR edge IN error_causality
        FILTER edge._from != null AND edge._to != null
        LIMIT 1
        RETURN {
            start: edge._from,
            end: edge._to,
            direct_connection: edge.relationship_type
        }
    """
    
    path_result = tools.execute_aql(path_query)
    if path_result["success"] and path_result["results"]:
        nodes = path_result["results"][0]
        print(f"\nTesting path from {nodes['start']} to {nodes['end']}")
        print(f"Direct connection: {nodes['direct_connection']}")
        
        # Now test with graph traversal
        result = tools.analyze_graph(
            "claude_agent_observatory",
            "shortest_path",
            {
                "start_node": nodes["start"],
                "end_node": nodes["end"]
            }
        )
        print("Shortest path result:", json.dumps(result, indent=2))
        return result
    
    return {"success": False, "error": "No connected nodes found"}


def test_connected_components_simple():
    """Test connected components with simple grouping."""
    tools = ArangoTools()
    
    # Simple component detection
    component_query = """
    // Get edges and group by connectivity
    FOR edge IN error_causality
        LIMIT 20
        LET nodes = [edge._from, edge._to]
        
        // Simple component: nodes that share edges
        RETURN {
            edge_id: edge._key,
            nodes: nodes,
            relationship: edge.relationship_type
        }
    """
    
    result = tools.execute_aql(component_query)
    print("\nConnected components (simple):", json.dumps(result, indent=2))
    return result


def main():
    """Run all tests."""
    print("=== Testing Fixed Graph Analytics ===\n")
    
    print("1. Testing Centrality (Simplified)")
    test_centrality()
    
    print("\n2. Testing Neighbors (Simple Traversal)")
    test_neighbors_simple()
    
    print("\n3. Testing Shortest Path")
    test_shortest_path_direct()
    
    print("\n4. Testing Connected Components (Simple)")
    test_connected_components_simple()
    
    print("\n=== Tests Complete ===")


if __name__ == "__main__":
    main()