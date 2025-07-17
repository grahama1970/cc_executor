#!/usr/bin/env python3
"""
Super Simple CRUD interface for ArangoDB - Zero complexity for agents.

This tool provides the absolute simplest interface for agents to interact with 
ArangoDB. No async complexity, just simple function calls that work.

Usage:
    from cc_executor.tools.arango_crud_simple import db, log, error, ask, aql
    
    # Write
    log("Something happened")
    error("Failed to process", error_type="ValueError") 
    
    # Read with raw AQL
    results = aql("FOR doc IN log_events LIMIT 10 RETURN doc")
    
    # Get help with natural language
    help_prompt = ask("show me recent errors")
    # Then use the suggested AQL with aql() function

=== AGENT INSTRUCTIONS FOR THIS FILE ===
Run this script directly to test functionality:
  python arango_crud_simple.py          # Runs working_usage() 
  python arango_crud_simple.py debug    # Runs debug_function()

DO NOT create separate test files - use the debug_function() instead!
===
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import uuid

from loguru import logger
from dotenv import load_dotenv
from arango import ArangoClient
from arango.exceptions import ArangoError

# Load environment variables
load_dotenv()


class SimpleArangoDB:
    """Dead simple synchronous ArangoDB interface."""
    
    def __init__(self):
        """Initialize connection."""
        self.client = None
        self.db = None
        self._connect()
    
    def _connect(self):
        """Connect to ArangoDB."""
        try:
            self.client = ArangoClient(hosts=os.getenv("ARANGO_URL", "http://localhost:8529"))
            self.db = self.client.db(
                os.getenv("ARANGO_DATABASE", "script_logs"),
                username=os.getenv("ARANGO_USERNAME", "root"),
                password=os.getenv("ARANGO_PASSWORD", "openSesame")
            )
            logger.info("Connected to ArangoDB")
        except Exception as e:
            logger.error(f"Failed to connect to ArangoDB: {e}")
            raise
    
    def log(self, message: str, level: str = "INFO", **kwargs) -> Optional[str]:
        """Log a message to ArangoDB."""
        doc = {
            "timestamp": datetime.now().isoformat(),
            "level": level.upper(),
            "message": message,
            "script_name": kwargs.pop("script_name", "arango_crud_simple"),
            "execution_id": kwargs.pop("execution_id", str(uuid.uuid4())[:8]),
            **kwargs
        }
        
        try:
            result = self.db.collection("log_events").insert(doc)
            return result["_id"]
        except Exception as e:
            logger.error(f"Failed to log: {e}")
            return None
    
    def error(self, message: str, error_type: Optional[str] = None, **kwargs) -> Optional[str]:
        """Log an error."""
        kwargs["error_type"] = error_type or "UnknownError"
        return self.log(message, level="ERROR", **kwargs)
    
    def query(self, aql: str, bind_vars: Optional[Dict] = None) -> Union[List[Dict], Dict[str, Any]]:
        """
        Execute AQL query. Returns results or error info.
        
        Usage:
            results = db.query("FOR doc IN log_events LIMIT 5 RETURN doc")
            
            # With bind vars
            results = db.query(
                "FOR doc IN @@col FILTER doc.level == @level RETURN doc",
                {"@col": "log_events", "level": "ERROR"}
            )
        """
        try:
            cursor = self.db.aql.execute(aql, bind_vars=bind_vars or {})
            return list(cursor)
        except ArangoError as e:
            error_msg = str(e)
            logger.error(f"Query failed: {error_msg}")
            
            # Return helpful error info
            return {
                "error": True,
                "message": error_msg,
                "aql": aql,
                "bind_vars": bind_vars,
                "suggestions": self._get_suggestions(error_msg),
                "examples": {
                    "recent_logs": 'db.query("FOR doc IN log_events SORT doc.timestamp DESC LIMIT 10 RETURN doc")',
                    "count_by_level": 'db.query("FOR doc IN log_events COLLECT level = doc.level WITH COUNT INTO c RETURN {level: level, count: c}")',
                    "with_bind_vars": 'db.query("FOR doc IN @@col RETURN doc", {"@col": "log_events"})'
                }
            }
    
    def _get_suggestions(self, error: str) -> List[str]:
        """Get error suggestions."""
        suggestions = []
        
        if "not found" in error.lower():
            suggestions.append("Check collection name. Common: log_events, agent_sessions, errors_and_failures")
            suggestions.append("Use db.collections() to list all collections")
        
        if "bind" in error.lower():
            suggestions.append("For collection names use @@col not @col")
            suggestions.append('Example: {"@col": "log_events"} not {"col": "log_events"}')
        
        if "syntax" in error.lower():
            suggestions.append("Basic AQL: FOR doc IN collection FILTER x RETURN doc")
        
        return suggestions
    
    def collections(self) -> List[str]:
        """List all collections."""
        try:
            return [c["name"] for c in self.db.collections() if not c["name"].startswith("_")]
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []
    
    def sample(self, collection: str = "log_events", limit: int = 3) -> List[Dict]:
        """Get sample documents."""
        result = self.query(f"FOR doc IN {collection} SORT RAND() LIMIT @limit RETURN doc", {"limit": limit})
        if isinstance(result, dict) and result.get("error"):
            return []
        return result
    
    def ask(self, question: str) -> Dict[str, Any]:
        """
        Get help converting natural language to AQL.
        
        Returns a prompt with examples and suggestions.
        """
        # Map common questions to AQL patterns
        patterns = {
            "recent errors": {
                "aql": 'FOR doc IN log_events FILTER doc.level == "ERROR" SORT doc.timestamp DESC LIMIT 20 RETURN doc',
                "description": "Get recent error logs"
            },
            "count by": {
                "aql": "FOR doc IN log_events COLLECT level = doc.level WITH COUNT INTO count RETURN {level: level, count: count}",
                "description": "Count documents by a field"
            },
            "last hour": {
                "aql": "FOR doc IN log_events FILTER doc.timestamp > DATE_ISO8601(DATE_NOW() - 3600000) RETURN doc",
                "description": "Get logs from last hour (3600000ms)"
            },
            "search": {
                "aql": 'FOR doc IN log_events FILTER CONTAINS(LOWER(doc.message), LOWER("search term")) RETURN doc',
                "description": "Search text in messages"
            },
            "by type": {
                "aql": 'FOR doc IN log_events FILTER doc.error_type == "ImportError" RETURN doc',
                "description": "Filter by specific field value"
            }
        }
        
        # Find best matching pattern
        question_lower = question.lower()
        best_match = None
        
        for key, pattern in patterns.items():
            if any(word in question_lower for word in key.split()):
                best_match = pattern
                break
        
        if not best_match:
            best_match = patterns["recent errors"]  # Default
        
        return {
            "question": question,
            "suggested_aql": best_match["aql"],
            "description": best_match["description"],
            "usage": f'results = aql("{best_match["aql"]}")',
            "customize": "Modify the AQL above for your specific needs",
            "all_patterns": patterns,
            "tip": "Use db.query() or aql() to execute the suggested query"
        }


# Create global instance
db = SimpleArangoDB()

# Super simple shortcuts
def log(msg: str, **kwargs):
    """Log to ArangoDB."""
    return db.log(msg, **kwargs)

def error(msg: str, **kwargs):
    """Log error to ArangoDB."""
    return db.error(msg, **kwargs)

def aql(query: str, bind_vars: Optional[Dict] = None):
    """Execute AQL query."""
    return db.query(query, bind_vars)

def ask(question: str):
    """Get AQL help for natural language question."""
    return db.ask(question)

def collections():
    """List all collections."""
    return db.collections()


def working_usage():
    """
    Demonstrate proper usage of the simple CRUD tool.
    
    AGENT: This shows basic usage patterns.
    """
    logger.info("=== Simple ArangoDB CRUD Usage ===")
    
    # Test writes
    logger.info("\n1. Writing to ArangoDB:")
    
    id1 = log("Test message from simple CRUD")
    logger.info(f"   Logged with ID: {id1}")
    
    id2 = error("Test error", error_type="TestError", extra_field="test")
    logger.info(f"   Error logged with ID: {id2}")
    
    # Test reads
    logger.info("\n2. Reading with AQL:")
    
    # Simple query
    results = aql("FOR doc IN log_events SORT doc.timestamp DESC LIMIT 3 RETURN doc.message")
    if isinstance(results, list):
        logger.info(f"   Recent messages: {len(results)} found")
        for msg in results[:2]:
            logger.info(f"   - {msg[:50]}...")
    
    # Query with bind vars
    count_result = aql(
        "FOR doc IN @@col COLLECT WITH COUNT INTO total RETURN total",
        {"@col": "log_events"}
    )
    if isinstance(count_result, list) and count_result:
        logger.info(f"   Total documents: {count_result[0]}")
    
    # Test error handling
    logger.info("\n3. Error handling:")
    
    bad_result = aql("FOR doc IN nonexistent RETURN doc")
    if isinstance(bad_result, dict) and bad_result.get("error"):
        logger.info("   Query failed as expected")
        logger.info(f"   Error: {bad_result['message'][:50]}...")
        logger.info(f"   Suggestion: {bad_result['suggestions'][0] if bad_result['suggestions'] else 'None'}")
    
    # Test natural language
    logger.info("\n4. Natural language help:")
    
    help_result = ask("show me recent errors")
    logger.info(f"   Question: {help_result['question']}")
    logger.info(f"   Suggested: {help_result['suggested_aql'][:60]}...")
    logger.info(f"   Usage: {help_result['usage']}")
    
    # List collections
    logger.info("\n5. Database info:")
    
    cols = collections()
    logger.info(f"   Collections: {', '.join(cols[:5])}...")
    
    # Sample documents
    samples = db.sample("log_events", limit=1)
    if samples:
        fields = list(samples[0].keys())
        logger.info(f"   log_events fields: {', '.join(fields[:8])}...")
    
    logger.success("\n✅ Simple CRUD working correctly!")
    
    return True


def debug_function():
    """
    Debug function for testing queries.
    
    AGENT: Use this to experiment with AQL queries!
    """
    logger.info("=== Debug Mode: AQL Practice ===")
    
    # Example 1: Time-based queries
    logger.info("\n1. Time-based queries:")
    
    time_queries = [
        ("Last 5 minutes", "FOR doc IN log_events FILTER doc.timestamp > DATE_ISO8601(DATE_NOW() - 300000) RETURN doc"),
        ("Today", "FOR doc IN log_events FILTER DATE_TIMESTAMP(doc.timestamp) > DATE_TIMESTAMP(DATE_FORMAT(DATE_NOW(), '%yyyy-%mm-%dd')) RETURN doc"),
    ]
    
    for desc, query in time_queries:
        result = aql(query + " LIMIT 3")
        if isinstance(result, list):
            logger.info(f"   {desc}: {len(result)} results")
    
    # Example 2: Aggregations
    logger.info("\n2. Aggregation queries:")
    
    # Count by multiple fields
    result = aql("""
        FOR doc IN log_events
        FILTER doc.level IN ["ERROR", "WARNING"]
        COLLECT level = doc.level, script = doc.script_name WITH COUNT INTO count
        SORT count DESC
        LIMIT 5
        RETURN {level: level, script: script, count: count}
    """)
    
    if isinstance(result, list):
        logger.info("   Top error/warning sources:")
        for item in result:
            logger.info(f"   - {item}")
    
    # Example 3: Natural language variations
    logger.info("\n3. Natural language examples:")
    
    questions = [
        "find recent errors",
        "count logs by level", 
        "search for timeout",
        "logs from last hour"
    ]
    
    for q in questions:
        help_info = ask(q)
        logger.info(f"\n   Q: {q}")
        logger.info(f"   A: {help_info['usage']}")
    
    # Example 4: Complex query with error handling
    logger.info("\n4. Complex query example:")
    
    complex_aql = """
        // Find error patterns
        FOR doc IN log_events
        FILTER doc.level == "ERROR"
        FILTER doc.error_type != null
        
        // Group by error type and get samples
        COLLECT error_type = doc.error_type INTO errors
        
        LET sample_messages = (
            FOR e IN errors[* LIMIT 2]
            RETURN SUBSTRING(e.doc.message, 0, 50)
        )
        
        SORT LENGTH(errors) DESC
        LIMIT 5
        
        RETURN {
            type: error_type,
            count: LENGTH(errors),
            samples: sample_messages
        }
    """
    
    result = aql(complex_aql)
    if isinstance(result, list):
        logger.info("   Error type analysis:")
        for item in result:
            logger.info(f"   - {item['type']}: {item['count']} occurrences")
    
    logger.success("\n✅ Debug examples completed!")
    
    # Show quick reference
    logger.info("\n📝 Quick Reference:")
    logger.info("   log('message')                    # Write")
    logger.info("   error('msg', error_type='Type')   # Write error")
    logger.info("   aql('FOR doc IN...')              # Query")
    logger.info("   ask('natural language')           # Get help")
    logger.info("   collections()                     # List collections")
    
    return True


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
        debug_function()
    else:
        print("Running working usage mode...")
        working_usage()