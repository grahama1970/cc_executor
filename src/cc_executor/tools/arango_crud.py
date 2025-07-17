#!/usr/bin/env python3
"""
Simple CRUD interface for ArangoDB - Making database access as easy as print().

This tool provides a dead-simple interface for agents to interact with ArangoDB
without dealing with async complexity, imports, or AQL syntax.

Usage:
    from cc_executor.tools.arango_crud import db
    
    # Write
    db.log("Something happened")
    db.error("Failed to process", error_type="ValueError") 
    db.learning("Discovered that X solves Y")
    
    # Read
    errors = db.recent_errors(hours=1)
    similar = db.find_similar("ModuleNotFoundError")
    fixes = db.get_fixes("ImportError")

=== AGENT INSTRUCTIONS FOR THIS FILE ===
Run this script directly to test functionality:
  python arango_crud.py          # Runs working_usage() - stable, known to work
  python arango_crud.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug_function() instead!
===
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import uuid

from loguru import logger
from dotenv import load_dotenv
import nest_asyncio

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Load environment variables
load_dotenv()

# Import our other tools for integration
from inspect_arangodb_schema import inspect_logger_agent_schema
from query_converter import generate_agent_prompt

# Add logger agent path
logger_agent_path = Path(__file__).parent.parent.parent / "proof_of_concept" / "logger_agent" / "src"
if str(logger_agent_path) not in sys.path:
    sys.path.insert(0, str(logger_agent_path))

# Import logger agent components
try:
    from agent_log_manager import get_log_manager, AgentLogManager
    from arango import ArangoClient
    ARANGO_AVAILABLE = True
except ImportError as e:
    logger.error(f"Cannot import required components: {e}")
    ARANGO_AVAILABLE = False


class SimpleCRUD:
    """
    Simple, synchronous CRUD interface for ArangoDB.
    Handles all async complexity internally.
    """
    
    def __init__(self):
        """Initialize the CRUD interface."""
        self._manager = None
        self._db = None
        self._initialized = False
        self._loop = None
        
    def _ensure_initialized(self):
        """Ensure we have a database connection."""
        if self._initialized and self._manager:
            return
            
        # Get or create event loop
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        
        # Initialize manager
        future = asyncio.run_coroutine_threadsafe(
            self._init_async(),
            self._loop
        )
        future.result(timeout=10)
        
    async def _init_async(self):
        """Async initialization."""
        if not ARANGO_AVAILABLE:
            raise RuntimeError("ArangoDB components not available")
            
        self._manager = await get_log_manager()
        self._db = self._manager.db
        self._initialized = True
        logger.info("SimpleCRUD initialized with ArangoDB")
        
    def _run_async(self, coro):
        """Run an async coroutine and return the result."""
        self._ensure_initialized()
        
        # Check if coroutine is already awaited
        import inspect
        if not inspect.iscoroutine(coro):
            return coro  # Already a result, not a coroutine
        
        # Try to get current event loop
        try:
            loop = asyncio.get_running_loop()
            # We're already in an event loop, use nest_asyncio
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(coro)
        except RuntimeError:
            # No running loop, create one
            if not self._loop or not self._loop.is_running():
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
            
            # Run in thread-safe manner
            future = asyncio.run_coroutine_threadsafe(coro, self._loop)
            return future.result(timeout=30)
    
    # ==================== WRITE METHODS ====================
    
    def log(self, message: str, level: str = "INFO", **kwargs):
        """
        Log a message to ArangoDB.
        
        Args:
            message: Log message
            level: Log level (INFO, WARNING, ERROR, etc.)
            **kwargs: Additional fields to store
            
        Returns:
            Document ID if successful, None otherwise
        """
        doc = {
            "timestamp": datetime.now().isoformat(),
            "level": level.upper(),
            "message": message,
            "script_name": kwargs.pop("script_name", "arango_crud"),
            "execution_id": kwargs.pop("execution_id", str(uuid.uuid4())[:8]),
            **kwargs
        }
        
        try:
            result = self._run_async(self._insert_document("log_events", doc))
            return result.get("_id") if result else None
        except Exception as e:
            logger.error(f"Failed to log: {e}")
            return None
    
    def error(self, message: str, error_type: Optional[str] = None, **kwargs):
        """Log an error with additional context."""
        kwargs["error_type"] = error_type or "UnknownError"
        return self.log(message, level="ERROR", **kwargs)
    
    def learning(self, insight: str, category: str = "general", **kwargs):
        """Log an agent learning/insight."""
        kwargs["log_category"] = "AGENT_LEARNING"
        kwargs["insight_category"] = category
        return self.log(f"LEARNING: {insight}", level="INFO", **kwargs)
    
    def success(self, message: str, **kwargs):
        """Log a success event."""
        return self.log(message, level="SUCCESS", **kwargs)
    
    # ==================== READ METHODS ====================
    
    def recent_errors(self, hours: int = 24) -> List[Dict]:
        """Get recent errors from the database."""
        aql = """
        FOR doc IN log_events
        FILTER doc.level IN ["ERROR", "CRITICAL"]
        FILTER doc.timestamp > DATE_ISO8601(DATE_NOW() - @ms)
        SORT doc.timestamp DESC
        LIMIT 100
        RETURN {
            id: doc._id,
            timestamp: doc.timestamp,
            message: doc.message,
            error_type: doc.error_type,
            script: doc.script_name
        }
        """
        
        ms = hours * 3600 * 1000  # Convert hours to milliseconds
        return self.query(aql, {"ms": ms})
    
    def find_similar(self, error_message: str, limit: int = 10) -> List[Dict]:
        """Find similar errors or log entries."""
        # First try BM25 search if search view exists
        aql_search = """
        FOR doc IN log_search_view
        SEARCH ANALYZER(doc.message IN TOKENS(@query, 'text_en'), 'text_en')
        LET score = BM25(doc)
        FILTER score > 0.5
        SORT score DESC
        LIMIT @limit
        RETURN {
            id: doc._id,
            message: doc.message,
            level: doc.level,
            timestamp: doc.timestamp,
            score: score
        }
        """
        
        try:
            results = self.query(aql_search, {"query": error_message, "limit": limit})
            if results:
                return results
        except:
            pass
        
        # Fallback to simple LIKE search
        aql_like = """
        FOR doc IN log_events
        FILTER CONTAINS(LOWER(doc.message), LOWER(@query))
        SORT doc.timestamp DESC
        LIMIT @limit
        RETURN {
            id: doc._id,
            message: doc.message,
            level: doc.level,
            timestamp: doc.timestamp
        }
        """
        
        return self.query(aql_like, {"query": error_message, "limit": limit})
    
    def get_fixes(self, error_type: str) -> List[Dict]:
        """Get known fixes for an error type."""
        aql = """
        FOR doc IN log_events
        FILTER doc.error_type == @error_type
        FILTER doc.resolved == true OR doc.fix_description != null
        SORT doc.timestamp DESC
        LIMIT 20
        RETURN {
            error: doc.message,
            fix: doc.fix_description,
            resolved_at: doc.resolved_at,
            time_to_fix: doc.resolution_time_minutes
        }
        """
        
        return self.query(aql, {"error_type": error_type})
    
    def count(self, collection: str = "log_events", filter_dict: Optional[Dict] = None) -> int:
        """Count documents in a collection with optional filter."""
        if filter_dict:
            conditions = []
            for key, value in filter_dict.items():
                conditions.append(f"doc.{key} == @{key}")
            
            aql = f"""
            FOR doc IN {collection}
            FILTER {' AND '.join(conditions)}
            COLLECT WITH COUNT INTO total
            RETURN total
            """
            
            result = self.query(aql, filter_dict)
        else:
            aql = f"""
            FOR doc IN {collection}
            COLLECT WITH COUNT INTO total
            RETURN total
            """
            
            result = self.query(aql)
        
        return result[0] if result else 0
    
    def query(self, aql: str, bind_vars: Optional[Dict] = None) -> Union[List[Dict], Dict[str, Any]]:
        """
        Execute a raw AQL query with helpful error recovery.
        
        Args:
            aql: AQL query string
            bind_vars: Bind variables for the query
            
        Returns:
            List of results OR error dict with recovery suggestions
        """
        try:
            results = self._run_async(
                self._execute_query(aql, bind_vars or {})
            )
            return results
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Query failed: {error_msg}")
            
            # Return helpful error information
            return {
                "error": True,
                "message": error_msg,
                "aql": aql,
                "bind_vars": bind_vars,
                "suggestions": self._get_error_suggestions(error_msg, aql) or ["Check the AQL syntax and collection names"],
                "example_queries": self._get_example_queries(),
                "schema_hint": "Run db.schema() to see available collections and fields"
            }
    
    def _get_error_suggestions(self, error: str, aql: str) -> List[str]:
        """Get suggestions based on common AQL errors."""
        suggestions = []
        
        if "collection or view not found" in error.lower():
            suggestions.append("Collection might not exist. Run db.collections() to see available collections.")
            suggestions.append("Common collections: log_events, agent_sessions, errors_and_failures")
        
        if "bind parameter" in error.lower():
            suggestions.append("Missing bind parameter. Check your bind_vars dictionary.")
            suggestions.append("Example: db.query('FOR doc IN @@col RETURN doc', {'@col': 'log_events'})")
        
        if "syntax error" in error.lower():
            suggestions.append("AQL syntax error. Check for missing keywords or quotes.")
            suggestions.append("Basic syntax: FOR doc IN collection FILTER condition RETURN doc")
        
        if "1544" in error:  # Common APPROX_NEAR error
            suggestions.append("Cannot use filters with APPROX_NEAR. Remove FILTER after APPROX_NEAR.")
        
        if "attribute" in error.lower() and "not found" in error.lower():
            suggestions.append("Field might not exist. Use db.sample_docs() to see document structure.")
        
        return suggestions
    
    def _get_example_queries(self) -> Dict[str, Dict[str, Any]]:
        """Return helpful example queries."""
        return {
            "recent_logs": {
                "aql": "FOR doc IN log_events FILTER doc.timestamp > DATE_ISO8601(DATE_NOW() - 3600000) SORT doc.timestamp DESC LIMIT 10 RETURN doc",
                "bind_vars": {},
                "description": "Get logs from last hour"
            },
            "count_by_level": {
                "aql": "FOR doc IN log_events COLLECT level = doc.level WITH COUNT INTO count RETURN {level: level, count: count}",
                "bind_vars": {},
                "description": "Count logs by level"
            },
            "search_text": {
                "aql": "FOR doc IN log_events FILTER CONTAINS(LOWER(doc.message), LOWER(@search)) LIMIT 20 RETURN doc",
                "bind_vars": {"search": "error"},
                "description": "Search for text in messages"
            },
            "with_collection_bind": {
                "aql": "FOR doc IN @@collection LIMIT 5 RETURN doc",
                "bind_vars": {"@collection": "log_events"},
                "description": "Query with bound collection name"
            }
        }
    
    # ==================== PRIVATE ASYNC METHODS ====================
    
    async def _insert_document(self, collection: str, doc: Dict) -> Optional[Dict]:
        """Insert a document into a collection."""
        try:
            col = self._db[collection]
            result = await col.insert(doc)
            return result
        except Exception as e:
            logger.error(f"Insert failed: {e}")
            return None
    
    async def _execute_query(self, aql: str, bind_vars: Dict) -> List[Dict]:
        """Execute an AQL query."""
        try:
            cursor = await self._db.aql.execute(aql, bind_vars=bind_vars)
            results = []
            async for doc in cursor:
                results.append(doc)
            return results
        except Exception as e:
            # Re-raise with more context
            raise Exception(f"AQL execution failed: {str(e)}")
    
    # ==================== CONVENIENCE METHODS ====================
    
    def recent_logs(self, minutes: int = 5, level: Optional[str] = None) -> List[Dict]:
        """Get logs from the last N minutes."""
        aql = """
        FOR doc IN log_events
        FILTER doc.timestamp > DATE_ISO8601(DATE_NOW() - @ms)
        """
        
        if level:
            aql += "\nFILTER doc.level == @level"
        
        aql += """
        SORT doc.timestamp DESC
        LIMIT 50
        RETURN doc
        """
        
        bind_vars = {"ms": minutes * 60 * 1000}
        if level:
            bind_vars["level"] = level.upper()
            
        return self.query(aql, bind_vars)
    
    def search_text(self, text: str, collection: str = "log_events") -> List[Dict]:
        """Simple text search across all text fields."""
        aql = f"""
        FOR doc IN {collection}
        FILTER CONTAINS(LOWER(TO_STRING(doc)), LOWER(@text))
        SORT doc.timestamp DESC
        LIMIT 50
        RETURN doc
        """
        
        return self.query(aql, {"text": text})
    
    def get_by_id(self, doc_id: str) -> Optional[Dict]:
        """Get a document by its ID."""
        aql = """
        RETURN DOCUMENT(@id)
        """
        
        results = self.query(aql, {"id": doc_id})
        return results[0] if results else None
    
    # ==================== NATURAL LANGUAGE METHODS ====================
    
    def ask(self, question: str, context: Optional[Dict] = None) -> Union[List[Dict], Dict[str, Any]]:
        """
        Ask a natural language question and get results from ArangoDB.
        Returns either results or a helpful prompt with AQL suggestions.
        
        Examples:
            db.ask("show me errors from the last hour")
            db.ask("find similar ImportError bugs")
            db.ask("what functions are related to main.py?")
        """
        try:
            # Generate AQL from natural language
            prompt = self._run_async(generate_agent_prompt(
                natural_query=question,
                error_type=context.get("error_type") if context else None,
                error_message=context.get("error_message") if context else None,
                file_path=context.get("file_path") if context else None,
                include_schema_info=True  # Include schema for better context
            ))
            
            # Return the full prompt for agent to use
            return {
                "natural_query": question,
                "aql_prompt": prompt,
                "suggested_approach": [
                    "1. Review the AQL examples in the prompt",
                    "2. Pick the most relevant example",
                    "3. Modify it for your specific needs",
                    "4. Use db.query(aql, bind_vars) to execute",
                    "5. If it fails, check the error suggestions"
                ],
                "quick_example": self._extract_best_example(prompt, question),
                "tip": "You can always use db.query() directly with AQL if you prefer"
            }
                
        except Exception as e:
            logger.error(f"Natural language query failed: {e}")
            return {
                "error": True,
                "message": str(e),
                "fallback": "Use db.query() with raw AQL instead"
            }
    
    def _extract_best_example(self, prompt: str, question: str) -> Dict[str, Any]:
        """Extract the most relevant example from the prompt."""
        # This is a simplified version - just get the first AQL block
        lines = prompt.split('\n')
        
        for i, line in enumerate(lines):
            if "```aql" in line:
                aql_lines = []
                for j in range(i+1, len(lines)):
                    if "```" in lines[j]:
                        aql = "\n".join(aql_lines)
                        
                        # Look for bind vars
                        bind_vars = {}
                        for k in range(j+1, min(j+5, len(lines))):
                            if "Bind vars" in lines[k] and "{" in lines[k]:
                                try:
                                    json_str = lines[k][lines[k].index("{"):]
                                    bind_vars = json.loads(json_str)
                                except:
                                    pass
                                break
                        
                        return {
                            "aql": aql,
                            "bind_vars": bind_vars,
                            "usage": f"db.query('''{aql}''', {bind_vars})"
                        }
                    else:
                        aql_lines.append(lines[j])
        
        # Fallback
        return {
            "aql": "FOR doc IN log_events SORT doc.timestamp DESC LIMIT 10 RETURN doc",
            "bind_vars": {},
            "usage": "db.query('FOR doc IN log_events SORT doc.timestamp DESC LIMIT 10 RETURN doc')"
        }
    
    def _extract_aql_from_prompt(self, prompt: str, question: str) -> tuple[Optional[str], Dict]:
        """Extract the most relevant AQL query from the generated prompt."""
        # Simple heuristic: find the first code block after a matching section
        lines = prompt.split('\n')
        
        # Keywords to match questions to examples
        patterns = [
            ("similar", "Find similar errors/bugs"),
            ("fixed", "How was this fixed?"),
            ("recent", "Recent errors/bugs"),
            ("related", "What's related/connected?"),
            ("count", "Count/group by"),
            ("unresolved", "Unresolved/pending"),
            ("file", "In specific file/path"),
            ("quick", "Fixed quickly/slowly")
        ]
        
        # Find matching pattern
        question_lower = question.lower()
        matched_section = None
        
        for keyword, section_title in patterns:
            if keyword in question_lower:
                matched_section = section_title
                break
        
        if not matched_section:
            # Default to recent errors
            matched_section = "Recent errors/bugs"
        
        # Extract AQL from the matched section
        in_section = False
        in_aql = False
        aql_lines = []
        bind_vars = {}
        
        for i, line in enumerate(lines):
            if matched_section in line:
                in_section = True
            elif in_section and line.startswith("```aql"):
                in_aql = True
            elif in_aql and line.startswith("```"):
                # Found complete AQL block
                aql = "\n".join(aql_lines)
                
                # Look for bind vars
                for j in range(i+1, min(i+5, len(lines))):
                    if "Bind vars" in lines[j] and "{" in lines[j]:
                        try:
                            # Extract JSON from the line
                            json_str = lines[j][lines[j].index("{"):]
                            bind_vars = json.loads(json_str)
                        except:
                            pass
                        break
                
                return aql, bind_vars
            elif in_aql:
                aql_lines.append(line)
            elif in_section and line.startswith("###"):
                # Next section, stop
                break
        
        # Fallback: simple recent query
        return """
        FOR doc IN log_events
        SORT doc.timestamp DESC
        LIMIT 20
        RETURN doc
        """, {}
    
    def schema(self, save_to_file: bool = False) -> Dict:
        """
        Get the current database schema.
        Uses inspect_arangodb_schema tool.
        
        Args:
            save_to_file: Whether to save schema report to file
            
        Returns:
            Schema dictionary
        """
        try:
            schema_report = self._run_async(inspect_logger_agent_schema(
                host="localhost",
                port=8529,
                username=os.getenv("ARANGO_USERNAME", "root"),
                password=os.getenv("ARANGO_PASSWORD", "openSesame"),
                db_name=os.getenv("ARANGO_DATABASE", "script_logs")
            ))
            
            return schema_report
            
        except Exception as e:
            logger.error(f"Failed to get schema: {e}")
            return {"error": str(e)}
    
    def collections(self) -> List[str]:
        """Get list of all collections."""
        schema = self.schema()
        if "error" not in schema:
            return list(schema.get("collections", {}).keys())
        return []
    
    def sample_docs(self, collection: str = "log_events", limit: int = 3) -> List[Dict]:
        """Get sample documents from a collection."""
        aql = f"""
        FOR doc IN {collection}
        SORT RAND()
        LIMIT @limit
        RETURN doc
        """
        
        return self.query(aql, {"limit": limit})


# Create global instance
db = SimpleCRUD()

# ==================== SUPER SIMPLE SHORTCUTS ====================
# These make it as easy as possible for agents to use

def log(msg: str, **kwargs):
    """Shortcut for db.log()"""
    return db.log(msg, **kwargs)

def error(msg: str, **kwargs):
    """Shortcut for db.error()"""
    return db.error(msg, **kwargs)

def ask(question: str):
    """Shortcut for db.ask() - returns AQL prompt for natural language queries"""
    return db.ask(question)

def aql(query: str, bind_vars: Optional[Dict] = None):
    """Shortcut for db.query() - execute raw AQL"""
    return db.query(query, bind_vars)

def find(text: str):
    """Shortcut for db.find_similar()"""
    return db.find_similar(text)


async def working_usage():
    """
    Demonstrate proper usage of the CRUD tool.
    
    AGENT: Run this for stable, production-ready example.
    """
    logger.info("=== SimpleCRUD Working Usage ===")
    
    # Test writes
    logger.info("Testing write operations...")
    
    # Log various events
    id1 = db.log("Starting CRUD test")
    assert id1 is not None, "Failed to log message"
    logger.success(f"✓ Logged message with ID: {id1}")
    
    id2 = db.error("Test error message", error_type="TestError", test_field="test_value")
    assert id2 is not None, "Failed to log error"
    logger.success(f"✓ Logged error with ID: {id2}")
    
    id3 = db.learning("CRUD operations are simpler with this interface", category="tools")
    assert id3 is not None, "Failed to log learning"
    logger.success(f"✓ Logged learning with ID: {id3}")
    
    # Test reads
    logger.info("\nTesting read operations...")
    
    # Count documents
    total = db.count()
    logger.info(f"Total documents in log_events: {total}")
    assert total > 0, "Should have at least our test documents"
    
    # Recent errors
    errors = db.recent_errors(hours=1)
    logger.info(f"Found {len(errors)} recent errors")
    assert any(e.get("error_type") == "TestError" for e in errors), "Should find our test error"
    
    # Search for our test message
    similar = db.find_similar("CRUD test")
    logger.info(f"Found {len(similar)} similar messages")
    assert len(similar) > 0, "Should find similar messages"
    
    # Recent logs
    recent = db.recent_logs(minutes=1)
    logger.info(f"Found {len(recent)} logs in last minute")
    assert len(recent) >= 3, "Should have at least our 3 test logs"
    
    # Get by ID
    doc = db.get_by_id(id1)
    assert doc is not None, "Should retrieve document by ID"
    assert "Starting CRUD test" in doc.get("message", ""), "Should have correct message"
    logger.success("✓ Retrieved document by ID")
    
    # Raw query
    results = db.query("""
        FOR doc IN log_events
        FILTER doc.script_name == @script
        COLLECT WITH COUNT INTO total
        RETURN total
    """, {"script": "arango_crud"})
    
    count = results[0] if results else 0
    logger.info(f"Found {count} documents from arango_crud script")
    assert count >= 3, "Should have at least our test documents"
    
    # Test natural language queries
    logger.info("\nTesting natural language queries...")
    
    # Ask questions in plain English
    nl_results = db.ask("show me recent errors")
    logger.info(f"Natural language query returned {len(nl_results)} results")
    assert len(nl_results) > 0, "Should find some results"
    
    # Test schema inspection
    logger.info("\nTesting schema inspection...")
    
    collections = db.collections()
    logger.info(f"Found {len(collections)} collections: {', '.join(collections[:5])}...")
    assert "log_events" in collections, "Should have log_events collection"
    
    # Get sample docs
    samples = db.sample_docs("log_events", limit=2)
    logger.info(f"Retrieved {len(samples)} sample documents")
    assert len(samples) > 0, "Should get sample documents"
    
    # Test shortcuts
    logger.info("\nTesting global shortcuts...")
    
    # These shortcuts make it super easy
    log_id = log("Test from global shortcut")
    assert log_id is not None, "Global log shortcut should work"
    
    error_id = error("Test error from shortcut", error_type="ShortcutError")
    assert error_id is not None, "Global error shortcut should work"
    
    findings = find("shortcut")
    logger.info(f"Found {len(findings)} documents with 'shortcut'")
    
    nl_results2 = ask("count errors by type")
    logger.info(f"Asked about error counts, got {len(nl_results2)} results")
    
    logger.success("\n✅ All CRUD tests passed!")
    logger.info("\n📝 Remember: You can use these super simple methods:")
    logger.info("  - log('message') - Log anything")
    logger.info("  - error('message', error_type='Type') - Log errors")
    logger.info("  - ask('show me recent errors') - Natural language queries")
    logger.info("  - find('search term') - Find similar logs")
    logger.info("  - db.schema() - Get database structure")
    logger.info("  - db.collections() - List all collections")
    
    return True


async def debug_function():
    """
    Debug function showing how agents should use this tool.
    
    AGENT: This demonstrates error recovery and natural language queries!
    """
    logger.info("=== Debug Mode: How to Use CRUD Effectively ===")
    
    # Test 1: Natural language to AQL
    logger.info("\nTest 1: Natural Language Queries")
    
    # Ask a question and get AQL prompt
    prompt_result = db.ask("show me errors from the last 2 hours")
    
    if "aql_prompt" in prompt_result:
        logger.info("Got AQL prompt for natural language query")
        logger.info(f"Suggested approach: {prompt_result['suggested_approach'][0]}")
        
        # Extract and execute the suggested query
        example = prompt_result["quick_example"]
        logger.info(f"\nSuggested AQL: {example['aql'][:100]}...")
        logger.info(f"Usage: {example['usage']}")
    
    # Test 2: Direct AQL with error handling
    logger.info("\nTest 2: Direct AQL with Error Recovery")
    
    # Try a query that might fail
    result = db.query("""
        FOR doc IN nonexistent_collection
        RETURN doc
    """)
    
    if isinstance(result, dict) and result.get("error"):
        logger.warning("Query failed as expected!")
        logger.info(f"Error: {result['message']}")
        logger.info("Suggestions:")
        for suggestion in result["suggestions"]:
            logger.info(f"  - {suggestion}")
        
        # Show available collections
        collections = db.collections()
        logger.info(f"\nAvailable collections: {', '.join(collections[:5])}...")
        
        # Try again with correct collection
        result = db.query("FOR doc IN log_events LIMIT 3 RETURN doc.message")
        logger.success(f"Fixed query returned {len(result)} results")
    
    # Test 3: Using bind parameters
    logger.info("\nTest 3: Using Bind Parameters")
    
    # Wrong way (will fail)
    bad_result = db.query("""
        FOR doc IN @collection
        RETURN doc
    """, {"collection": "log_events"})
    
    if isinstance(bad_result, dict) and bad_result.get("error"):
        logger.info("Bind parameter error detected")
        logger.info(f"Suggestion: {bad_result['suggestions'][0]}")
        
        # Right way
        good_result = db.query("""
            FOR doc IN @@collection
            LIMIT 3
            RETURN doc._key
        """, {"@collection": "log_events"})
        
        logger.success(f"Correct bind syntax returned {len(good_result)} keys")
    
    # Test 4: Schema exploration
    logger.info("\nTest 4: Schema Exploration")
    
    # Get schema to understand database
    schema = db.schema()
    if "collections" in schema:
        logger.info(f"Database has {len(schema['collections'])} collections")
        
        # Get sample from a collection to see fields
        samples = db.sample_docs("log_events", limit=1)
        if samples:
            fields = list(samples[0].keys())
            logger.info(f"log_events fields: {', '.join(fields[:8])}...")
    
    # Test 5: Practical examples
    logger.info("\nTest 5: Practical Query Examples")
    
    # Count errors by type
    error_counts = db.query("""
        FOR doc IN log_events
        FILTER doc.level == "ERROR"
        FILTER doc.error_type != null
        COLLECT error_type = doc.error_type WITH COUNT INTO count
        SORT count DESC
        LIMIT 5
        RETURN {type: error_type, count: count}
    """)
    
    if not isinstance(error_counts, dict):  # Success
        logger.info("Top error types:")
        for item in error_counts:
            logger.info(f"  {item['type']}: {item['count']}")
    
    # Test shortcuts
    logger.info("\nTest 6: Using Global Shortcuts")
    
    # Super simple logging
    log("Test from shortcut")
    error("Test error", error_type="DebugError")
    
    # Direct AQL shortcut
    recent = aql("FOR doc IN log_events SORT doc.timestamp DESC LIMIT 2 RETURN doc.message")
    if not isinstance(recent, dict):  # Success
        logger.info(f"Recent messages: {recent}")
    
    logger.success("\n✅ Debug demonstration completed!")
    logger.info("\n🔑 Key Takeaways:")
    logger.info("  1. Use db.ask() to get AQL suggestions from natural language")
    logger.info("  2. Check if query results are dict (error) or list (success)")
    logger.info("  3. Error results include helpful suggestions")
    logger.info("  4. Use @@collection for bound collection names")
    logger.info("  5. db.schema() and db.sample_docs() help explore structure")
    
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
        asyncio.run(debug_function())
    else:
        print("Running working usage mode...")
        asyncio.run(working_usage())