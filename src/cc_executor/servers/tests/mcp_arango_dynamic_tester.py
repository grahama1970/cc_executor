#!/usr/bin/env python3
"""
Dynamic MCP Arango Tools Testing Framework

This script provides a comprehensive testing approach that:
1. Tests normal operations
2. Deliberately triggers errors to test recovery
3. Uses perplexity-ask for troubleshooting
4. Learns from failures to improve future tests

Run this to guide Claude through systematic MCP testing with error recovery.
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import random
import string

class MCP_ArangoTestScenarios:
    """Dynamic test scenarios for arango-tools MCP with error recovery."""
    
    def __init__(self):
        self.test_results = []
        self.learned_patterns = []
        
    def generate_test_id(self) -> str:
        """Generate unique test ID."""
        return f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.choices(string.ascii_lowercase, k=4)}"
    
    def get_test_scenarios(self) -> List[Dict[str, Any]]:
        """Get comprehensive test scenarios with increasing complexity."""
        
        return [
            # Level 1: Basic Operations
            {
                "id": "basic_schema",
                "name": "Test Schema Discovery",
                "level": "basic",
                "steps": [
                    {
                        "action": "mcp__arango-tools__schema()",
                        "expect": "success",
                        "verify": ["collections", "graphs", "views"],
                        "on_error": "Check if ArangoDB is running on localhost:8529"
                    }
                ]
            },
            
            # Level 2: Error Recovery - Wrong Database
            {
                "id": "wrong_database",
                "name": "Test Wrong Database Error Recovery",
                "level": "error_recovery",
                "setup": "Temporarily switch to non-existent database",
                "steps": [
                    {
                        "action": "Try to query non-existent database",
                        "expect": "error",
                        "error_type": "DatabaseNotFound",
                        "recovery": [
                            "Detect database doesn't exist",
                            "Use perplexity-ask to understand ArangoDB database creation",
                            "Switch back to script_logs database",
                            "Verify connection works"
                        ]
                    }
                ]
            },
            
            # Level 3: Complex Query with Syntax Error
            {
                "id": "aql_syntax_error",
                "name": "Test AQL Syntax Error Recovery",
                "level": "error_recovery",
                "steps": [
                    {
                        "action": 'mcp__arango-tools__query("FOR doc IN LIMIT 10")',
                        "expect": "error",
                        "error_type": "AQLSyntaxError",
                        "recovery": [
                            "Parse the error message",
                            "Use perplexity-ask to understand correct AQL syntax",
                            "Retry with corrected query: FOR doc IN log_events LIMIT 10 RETURN doc",
                            "Verify results"
                        ]
                    }
                ]
            },
            
            # Level 4: Empty Results Handling
            {
                "id": "empty_results",
                "name": "Test Empty Results Scenario",
                "level": "edge_case",
                "steps": [
                    {
                        "action": 'mcp__arango-tools__query("FOR doc IN log_events FILTER doc.non_existent_field == @value RETURN doc", "{\\"value\\": \\"impossible\\"}")',
                        "expect": "empty_results",
                        "verify": "Handle gracefully, don't treat as error",
                        "follow_up": [
                            "Insert test data to ensure non-empty results",
                            "Re-run query with valid filter"
                        ]
                    }
                ]
            },
            
            # Level 5: Transaction Rollback
            {
                "id": "transaction_test",
                "name": "Test Multi-Operation Transaction",
                "level": "advanced",
                "steps": [
                    {
                        "action": "Start a complex operation",
                        "operations": [
                            "Insert parent document",
                            "Insert child document", 
                            "Create edge with invalid collection",
                            "Expect rollback of all operations"
                        ],
                        "recovery": [
                            "Detect which operation failed",
                            "Use schema() to verify valid collections",
                            "Retry with correct collection names"
                        ]
                    }
                ]
            },
            
            # Level 6: Performance Under Load
            {
                "id": "performance_test",
                "name": "Test Bulk Operations Performance",
                "level": "stress",
                "steps": [
                    {
                        "action": "Insert 100 documents rapidly",
                        "monitor": ["Response times", "Error rates", "Connection stability"],
                        "thresholds": {
                            "avg_response_ms": 100,
                            "error_rate": 0.01,
                            "success_rate": 0.99
                        }
                    }
                ]
            },
            
            # Level 7: Graph Traversal Errors
            {
                "id": "graph_traversal",
                "name": "Test Complex Graph Queries",
                "level": "advanced",
                "steps": [
                    {
                        "action": "Traverse non-existent graph",
                        "expect": "error",
                        "recovery": [
                            "List available graphs with schema()",
                            "Use correct graph name",
                            "Test various traversal depths"
                        ]
                    },
                    {
                        "action": "Traverse with infinite loop potential",
                        "safeguards": ["Set max depth", "Add cycle detection"]
                    }
                ]
            },
            
            # Level 8: Concurrent Access
            {
                "id": "concurrent_access",
                "name": "Test Concurrent Operations",
                "level": "stress",
                "steps": [
                    {
                        "action": "Simulate multiple agents accessing same documents",
                        "operations": [
                            "Agent A reads document",
                            "Agent B updates same document", 
                            "Agent A tries to update based on stale data"
                        ],
                        "verify": "Proper conflict handling"
                    }
                ]
            },
            
            # Level 9: Research Integration
            {
                "id": "research_integration",
                "name": "Test Research Cache and Learning",
                "level": "integration",
                "steps": [
                    {
                        "action": "Encounter new error type",
                        "flow": [
                            "Get unknown error from ArangoDB",
                            "Use perplexity-ask to research solution",
                            "Store research in research_cache",
                            "Verify cache hit on repeated error"
                        ]
                    }
                ]
            },
            
            # Level 10: Recovery Patterns
            {
                "id": "recovery_patterns",
                "name": "Test Learned Recovery Patterns",
                "level": "learning",
                "steps": [
                    {
                        "action": "Apply learned patterns from previous errors",
                        "patterns": [
                            "Connection timeout → Check ArangoDB service",
                            "Auth error → Verify credentials in env",
                            "Collection not found → Use schema() first",
                            "AQL syntax → Use bind variables for safety"
                        ]
                    }
                ]
            }
        ]
    
    def generate_error_scenarios(self) -> List[Dict[str, Any]]:
        """Generate specific error scenarios to test recovery."""
        
        return [
            {
                "error": "Connection refused",
                "cause": "ArangoDB not running",
                "detection": "ConnectionError in response",
                "recovery_steps": [
                    "Check if localhost:8529 is accessible",
                    "Use perplexity-ask: 'How to start ArangoDB service on Ubuntu'",
                    "Verify service status",
                    "Retry connection"
                ]
            },
            {
                "error": "Invalid query",
                "cause": "Malformed AQL syntax",
                "detection": "Parse error message for line/column",
                "recovery_steps": [
                    "Extract error position from message",
                    "Use perplexity-ask with specific AQL construct",
                    "Apply suggested fix",
                    "Test with simpler query first"
                ]
            },
            {
                "error": "Document not found",
                "cause": "Invalid document key",
                "detection": "404 or null result",
                "recovery_steps": [
                    "List documents to find valid keys",
                    "Create document if needed",
                    "Update references"
                ]
            },
            {
                "error": "Unique constraint violation",
                "cause": "Duplicate key insertion",
                "detection": "Conflict error on insert",
                "recovery_steps": [
                    "Use upsert instead of insert",
                    "Check for existing document first",
                    "Generate unique keys"
                ]
            }
        ]
    
    def generate_progressive_tests(self) -> str:
        """Generate a progressive testing guide."""
        
        guide = """
# Progressive MCP Arango Testing Guide

## Phase 1: Establish Baseline (5 min)
1. Verify connection: `mcp__arango-tools__schema()`
2. Simple query: `mcp__arango-tools__query("FOR doc IN log_events LIMIT 1 RETURN doc")`
3. Basic insert: `mcp__arango-tools__insert("Test message", "INFO")`

## Phase 2: Error Detection (10 min)
1. Trigger syntax error with bad AQL
2. Query non-existent collection
3. Use invalid bind variables
4. For each error:
   - Note exact error message
   - Use perplexity-ask for solution
   - Document recovery steps

## Phase 3: Complex Operations (15 min)
1. Multi-collection joins
2. Graph traversals with depth limits
3. Aggregation queries
4. Full-text search in views

## Phase 4: Learning Integration (10 min)
1. When encountering any error:
   ```
   error_info = {
       "error_type": "...",
       "error_message": "...",
       "context": "...",
       "attempted_query": "..."
   }
   
   # Research solution
   research = mcp__perplexity-ask__perplexity_ask({
       "messages": [{
           "role": "user",
           "content": f"ArangoDB error: {error_info}. How to fix?"
       }]
   })
   
   # Store learning
   mcp__arango-tools__insert(
       message=f"Learned solution for {error_info['error_type']}",
       level="INFO",
       error_type=error_info['error_type'],
       solution=research['solution'],
       metadata={"research_source": "perplexity"}
   )
   ```

## Phase 5: Stress Testing (5 min)
1. Rapid inserts (100+ documents)
2. Complex graph analysis
3. Concurrent operations simulation

## Success Metrics
- ✅ All basic operations work
- ✅ Error recovery successful for 5+ error types
- ✅ Learned patterns stored in database
- ✅ Performance acceptable under load
- ✅ Integration with perplexity-ask smooth
"""
        return guide


# Test execution helper
def generate_test_command(scenario: Dict[str, Any]) -> str:
    """Generate the actual command for Claude to execute."""
    if "action" in scenario:
        return scenario["action"]
    return "# Implement based on scenario description"


# Create test framework instance
tester = MCP_ArangoTestScenarios()

# Output all scenarios
print("=== MCP ARANGO DYNAMIC TEST SCENARIOS ===\n")

print("Test Scenarios:")
for scenario in tester.get_test_scenarios():
    print(f"\n{scenario['id']}: {scenario['name']} (Level: {scenario['level']})")
    
print("\n\nError Recovery Patterns:")
for error in tester.generate_error_scenarios():
    print(f"\n- {error['error']}: {error['cause']}")

print("\n\nProgressive Testing Guide:")
print(tester.generate_progressive_tests())

print("\n\n=== INSTRUCTIONS FOR CLAUDE ===")
print("""
1. Start with Phase 1 to establish baseline
2. Deliberately trigger errors in Phase 2
3. When errors occur:
   - Don't hide them - analyze them
   - Use perplexity-ask for solutions
   - Store learnings in the database
4. Progress through all phases
5. Document what works and what doesn't
6. Build a knowledge base of solutions

Remember: The goal is not just to test, but to:
- Learn from failures
- Build recovery patterns  
- Integrate with perplexity-ask
- Create a robust testing approach
""")