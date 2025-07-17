#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "fastmcp",
#     "python-dotenv",
#     "python-arango",
#     "loguru"
# ]
# ///
"""
MCP Server for ArangoDB Tools - Unified interface for schema, queries, and CRUD.

This MCP server provides agents with easy access to ArangoDB operations.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import uuid
import hashlib
import pickle

from fastmcp import FastMCP
from loguru import logger
from dotenv import load_dotenv, find_dotenv

# Add MCP logger utility
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.mcp_logger import MCPLogger, debug_tool
from arango import ArangoClient
from arango.exceptions import ArangoError

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")

# Load environment variables - searches up directory tree
load_dotenv(find_dotenv())

# Initialize MCP server and logger
mcp = FastMCP("arango-tools")
mcp_logger = MCPLogger("arango-tools")


class ArangoTools:
    """Unified ArangoDB tools for MCP."""
    
    def __init__(self):
        """Initialize connection."""
        self.client = None
        self.db = None
        self._connect()
        self._ensure_glossary_collections()
        self._init_research_cache()
    
    def _connect(self):
        """Connect to ArangoDB."""
        try:
            # Get password from environment with warning if using default
            password = os.getenv("ARANGO_PASSWORD", "")
            if not password:
                logger.warning(
                    "⚠️  ARANGO_PASSWORD not set - using insecure default 'openSesame'. "
                    "Please set ARANGO_PASSWORD in your .env file for production use!"
                )
                password = "openSesame"
            
            self.client = ArangoClient(hosts=os.getenv("ARANGO_URL", "http://localhost:8529"))
            self.db = self.client.db(
                os.getenv("ARANGO_DATABASE", "script_logs"),
                username=os.getenv("ARANGO_USERNAME", "root"),
                password=password
            )
            logger.info("Connected to ArangoDB")
        except Exception as e:
            logger.error(f"Failed to connect to ArangoDB: {e}")
            raise
    
    def _ensure_glossary_collections(self):
        """Ensure glossary and learning collections exist."""
        # Main glossary collection
        if not self.db.has_collection("glossary_terms"):
            self.db.create_collection("glossary_terms")
            logger.info("Created glossary_terms collection")
        
        # Relationships between terms (reuse existing if possible)
        if not self.db.has_collection("term_relationships"):
            self.db.create_collection("term_relationships", edge=True)
            logger.info("Created term_relationships edge collection")
        
        # Research results cache
        if not self.db.has_collection("research_cache"):
            self.db.create_collection("research_cache")
            logger.info("Created research_cache collection")
        
        # Learning system collections
        if not self.db.has_collection("solution_outcomes"):
            self.db.create_collection("solution_outcomes")
            logger.info("Created solution_outcomes collection")
        
        if not self.db.has_collection("lessons_learned"):
            self.db.create_collection("lessons_learned")
            logger.info("Created lessons_learned collection")
        
        if not self.db.has_collection("solution_to_lesson"):
            self.db.create_collection("solution_to_lesson", edge=True)
            logger.info("Created solution_to_lesson edge collection")
    
    def _init_research_cache(self):
        """Initialize research cache settings."""
        self.research_cache_ttl = 7 * 24 * 60 * 60 * 1000  # 7 days in milliseconds
        self.research_cache_dir = Path.home() / ".cache" / "arango_research"
        self.research_cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_schema(self) -> Dict[str, Any]:
        """Get database schema information."""
        try:
            # Get collections
            collections = {}
            for col in self.db.collections():
                if not col["name"].startswith("_"):
                    # Get sample document to show structure
                    sample = None
                    try:
                        cursor = self.db.aql.execute(
                            f"FOR doc IN {col['name']} LIMIT 1 RETURN doc"
                        )
                        samples = list(cursor)
                        if samples:
                            sample = {k: type(v).__name__ for k, v in samples[0].items()}
                    except:
                        pass
                    
                    collections[col["name"]] = {
                        "type": col["type"],
                        "count": col.get("count", 0),
                        "sample_fields": sample
                    }
            
            # Get views
            views = []
            for view in self.db.views():
                if not view["name"].startswith("_"):
                    views.append({
                        "name": view["name"],
                        "type": view["type"],
                        "links": list(view.get("links", {}).keys())
                    })
            
            # Get graphs
            graphs = []
            try:
                for graph in self.db.graphs():
                    graph_info = self.db.graph(graph["name"])
                    graphs.append({
                        "name": graph["name"],
                        "edge_collections": list(graph_info.edge_definitions())
                    })
            except:
                pass
            
            return {
                "success": True,
                "database": self.db.name,
                "collections": collections,
                "views": views,
                "graphs": graphs,
                "common_queries": {
                    "recent_logs": "FOR doc IN log_events SORT doc.timestamp DESC LIMIT 10 RETURN doc",
                    "count_by_level": "FOR doc IN log_events COLLECT level = doc.level WITH COUNT INTO c RETURN {level: level, count: c}",
                    "search_errors": "FOR doc IN log_events FILTER doc.level == 'ERROR' RETURN doc"
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def execute_aql(self, aql: str, bind_vars: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute AQL query."""
        try:
            cursor = self.db.aql.execute(aql, bind_vars=bind_vars or {})
            results = list(cursor)
            return {
                "success": True,
                "count": len(results),
                "results": results
            }
        except ArangoError as e:
            error_msg = str(e)
            return {
                "success": False,
                "error": error_msg,
                "suggestions": self._get_error_suggestions(error_msg),
                "aql": aql,
                "bind_vars": bind_vars
            }
    
    def _get_error_suggestions(self, error: str) -> List[str]:
        """Get suggestions for common errors."""
        suggestions = []
        
        if "not found" in error.lower():
            suggestions.append("Check collection name. Use schema() to list collections")
            suggestions.append("Common collections: log_events, agent_sessions, errors_and_failures")
        
        if "bind" in error.lower():
            suggestions.append("Collection names need @@: {@col: 'log_events'}")
            suggestions.append("Regular values need @: {level: 'ERROR'}")
        
        if "syntax" in error.lower():
            suggestions.append("Basic syntax: FOR doc IN collection FILTER x RETURN doc")
            suggestions.append("Check for missing quotes or parentheses")
        
        if "1554" in error:  # APPROX_NEAR_COSINE error
            suggestions.append("Cannot use filters with APPROX_NEAR_COSINE")
            suggestions.append("Remove FILTER clauses when using vector search")
        
        return suggestions
    
    def insert_log(self, message: str, level: str = "INFO", **kwargs) -> Dict[str, Any]:
        """Insert a log event."""
        doc = {
            "timestamp": datetime.now().isoformat(),
            "level": level.upper(),
            "message": message,
            "script_name": kwargs.pop("script_name", "mcp_arango_tools"),
            "execution_id": kwargs.pop("execution_id", str(uuid.uuid4())[:8]),
            **kwargs
        }
        
        try:
            result = self.db.collection("log_events").insert(doc)
            return {
                "success": True,
                "id": result["_id"],
                "message": "Inserted successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def create_edge(self, from_id: str, to_id: str, edge_collection: str, **kwargs) -> Dict[str, Any]:
        """Create an edge between two documents."""
        edge_doc = {
            "_from": from_id,
            "_to": to_id,
            "created_at": datetime.now().isoformat(),
            **kwargs
        }
        
        try:
            result = self.db.collection(edge_collection).insert(edge_doc)
            return {
                "success": True,
                "id": result["_id"],
                "message": f"Edge created from {from_id} to {to_id}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "suggestion": "Check that both document IDs exist and edge collection is valid"
            }
    
    def upsert_document(self, collection: str, search_fields: Dict[str, Any], 
                       update_fields: Dict[str, Any], create_fields: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Upsert a document - update if exists, create if not."""
        try:
            # Build the upsert query
            aql = """
            UPSERT @search
            INSERT @create
            UPDATE @update
            IN @@collection
            RETURN NEW
            """
            
            # Prepare create document (merge search + create fields)
            create_doc = {**search_fields, **(create_fields or {}), **update_fields}
            create_doc["created_at"] = datetime.now().isoformat()
            
            # Add required fields for specific collections
            if collection == "script_runs" and "execution_id" not in create_doc:
                # Generate execution_id for script_runs
                create_doc["execution_id"] = f"{create_doc.get('script_name', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
                create_doc["start_time"] = create_doc.get("start_time", datetime.now().isoformat())
                create_doc["status"] = create_doc.get("status", "running")
                create_doc["pid"] = create_doc.get("pid", os.getpid())
                create_doc["hostname"] = create_doc.get("hostname", os.uname().nodename)
            
            # Update document includes modified timestamp
            update_doc = {**update_fields, "modified_at": datetime.now().isoformat()}
            
            bind_vars = {
                "@collection": collection,
                "search": search_fields,
                "create": create_doc,
                "update": update_doc
            }
            
            cursor = self.db.aql.execute(aql, bind_vars=bind_vars)
            result = list(cursor)
            
            return {
                "success": True,
                "document": result[0] if result else None,
                "message": "Document upserted successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "suggestion": "Check collection name and field syntax. For script_runs, required fields: execution_id, script_name, start_time, status"
            }
    
    def update_document(self, collection: str, doc_key: str, update_fields: Dict[str, Any]) -> Dict[str, Any]:
        """Update a specific document by key."""
        try:
            doc_id = f"{collection}/{doc_key}" if "/" not in doc_key else doc_key
            update_fields["modified_at"] = datetime.now().isoformat()
            
            result = self.db.collection(collection).update({
                "_key": doc_key.split("/")[-1],
                **update_fields
            })
            
            return {
                "success": True,
                "id": doc_id,
                "message": "Document updated successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "suggestion": "Check document exists and fields are valid"
            }
    
    def delete_document(self, collection: str, doc_key: str) -> Dict[str, Any]:
        """Delete a document by key."""
        try:
            doc_key = doc_key.split("/")[-1]  # Extract key if full ID provided
            result = self.db.collection(collection).delete(doc_key)
            
            return {
                "success": True,
                "deleted": True,
                "message": f"Document {collection}/{doc_key} deleted"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "suggestion": "Check document exists"
            }
    
    def get_document(self, collection: str, doc_key: str) -> Dict[str, Any]:
        """Get a single document by key."""
        try:
            doc_key = doc_key.split("/")[-1]  # Extract key if full ID provided
            doc = self.db.collection(collection).get(doc_key)
            
            if doc is None:
                return {
                    "success": False,
                    "error": "Document not found"
                }
            
            return {
                "success": True,
                "document": doc
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def english_to_aql_patterns(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Convert natural language to AQL patterns."""
        
        patterns = {
            "similar": {
                "pattern": "find similar errors/scripts/bugs",
                "aql": """FOR doc IN log_search_view
SEARCH ANALYZER(doc.message IN TOKENS(@query, 'text_en'), 'text_en')
LET score = BM25(doc)
FILTER score > 0.5
SORT score DESC
LIMIT 10
RETURN doc""",
                "bind_vars": {"query": "your search terms"},
                "note": "Uses BM25 search on log_search_view"
            },
            "resolved": {
                "pattern": "find resolved/fixed errors",
                "aql": """FOR doc IN log_events
FILTER doc.resolved == true
FILTER doc.error_type == @error_type
SORT doc.resolved_at DESC
LIMIT 10
RETURN {
    error: doc.message,
    fix: doc.fix_description,
    time_to_fix: doc.resolution_time_minutes
}""",
                "bind_vars": {"error_type": "ImportError"},
                "note": "Find errors that have been resolved"
            },
            "recent": {
                "pattern": "recent errors/logs from last hour/day",
                "aql": """FOR doc IN log_events
FILTER doc.timestamp > DATE_ISO8601(DATE_NOW() - @ms)
SORT doc.timestamp DESC
LIMIT 50
RETURN doc""",
                "bind_vars": {"ms": 3600000},
                "note": "1 hour = 3600000ms, 1 day = 86400000ms"
            },
            "count": {
                "pattern": "count by type/level/field",
                "aql": """FOR doc IN log_events
COLLECT field = doc.error_type WITH COUNT INTO count
SORT count DESC
RETURN {type: field, count: count}""",
                "bind_vars": {},
                "note": "Group and count by any field"
            },
            "graph": {
                "pattern": "find related/connected items",
                "aql": """FOR v, e, p IN 1..@depth ANY @start_id error_causality, agent_flow
RETURN DISTINCT {
    item: v,
    distance: LENGTH(p.edges),
    connection_type: p.edges[-1].relationship_type
}""",
                "bind_vars": {"depth": 2, "start_id": "log_events/12345"},
                "note": "Graph traversal to find relationships"
            }
        }
        
        # Find best matching pattern
        query_lower = query.lower()
        best_match = None
        
        for key, pattern_info in patterns.items():
            if key in query_lower or any(word in query_lower for word in pattern_info["pattern"].split("/")):
                best_match = pattern_info
                break
        
        if not best_match:
            best_match = patterns["similar"]  # Default
        
        # Add context if provided
        if context:
            if context.get("error_type"):
                best_match["bind_vars"]["error_type"] = context["error_type"]
            if context.get("script_name"):
                best_match["bind_vars"]["script"] = context["script_name"]
        
        return {
            "success": True,
            "query": query,
            "matched_pattern": best_match["pattern"],
            "aql": best_match["aql"],
            "bind_vars": best_match["bind_vars"],
            "note": best_match["note"],
            "all_patterns": {k: v["pattern"] for k, v in patterns.items()},
            "usage": f"Execute with query() using the AQL and bind_vars above"
        }
    
    def add_glossary_term(self, term: str, definition: str, **kwargs) -> Dict[str, Any]:
        """Add or update a glossary term."""
        normalized_term = term.lower().strip()
        
        doc = {
            "term": term,
            "normalized_term": normalized_term,
            "definition": definition,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "usage_count": 0,
            "category": kwargs.get("category", "general"),
            "aliases": kwargs.get("aliases", []),
            "context": kwargs.get("context", ""),
            "examples": kwargs.get("examples", []),
            "related_errors": kwargs.get("related_errors", []),
            "tags": kwargs.get("tags", []),
            "source": kwargs.get("source", "agent_learning"),
            "confidence": kwargs.get("confidence", 0.8)
        }
        
        try:
            # Check if term exists
            existing_query = """
            FOR doc IN glossary_terms
                FILTER doc.normalized_term == @normalized_term
                LIMIT 1
                RETURN doc
            """
            
            cursor = self.db.aql.execute(
                existing_query,
                bind_vars={"normalized_term": normalized_term}
            )
            existing = list(cursor)
            
            if existing:
                # Update existing term
                update_doc = {
                    "definition": definition,
                    "updated_at": datetime.now().isoformat(),
                    "usage_count": existing[0].get("usage_count", 0) + 1
                }
                
                # Merge arrays
                if "aliases" in kwargs:
                    update_doc["aliases"] = list(set(existing[0].get("aliases", []) + kwargs["aliases"]))
                if "examples" in kwargs:
                    update_doc["examples"] = existing[0].get("examples", []) + kwargs["examples"]
                if "tags" in kwargs:
                    update_doc["tags"] = list(set(existing[0].get("tags", []) + kwargs["tags"]))
                if "related_errors" in kwargs:
                    update_doc["related_errors"] = list(set(existing[0].get("related_errors", []) + kwargs["related_errors"]))
                
                result = self.db.collection("glossary_terms").update({
                    "_key": existing[0]["_key"],
                    **update_doc
                })
                
                return {
                    "success": True,
                    "action": "updated",
                    "term": term,
                    "id": existing[0]["_id"],
                    "message": f"Updated existing term: {term}"
                }
            else:
                # Insert new term
                result = self.db.collection("glossary_terms").insert(doc)
                
                return {
                    "success": True,
                    "action": "created",
                    "term": term,
                    "id": result["_id"],
                    "message": f"Added new term: {term}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "term": term
            }
    
    def link_glossary_terms(self, from_term: str, to_term: str, relationship: str, **kwargs) -> Dict[str, Any]:
        """Create relationship between glossary terms."""
        try:
            # Find both terms
            find_query = """
            FOR doc IN glossary_terms
                FILTER doc.normalized_term IN [@from_term, @to_term]
                RETURN {id: doc._id, term: doc.term, normalized: doc.normalized_term}
            """
            
            cursor = self.db.aql.execute(
                find_query,
                bind_vars={
                    "from_term": from_term.lower().strip(),
                    "to_term": to_term.lower().strip()
                }
            )
            terms = list(cursor)
            
            if len(terms) < 2:
                return {
                    "success": False,
                    "error": "One or both terms not found",
                    "found_terms": [t["term"] for t in terms]
                }
            
            # Find the IDs
            from_id = next(t["id"] for t in terms if t["normalized"] == from_term.lower().strip())
            to_id = next(t["id"] for t in terms if t["normalized"] == to_term.lower().strip())
            
            # Create edge
            edge_doc = {
                "_from": from_id,
                "_to": to_id,
                "relationship": relationship,
                "created_at": datetime.now().isoformat(),
                "strength": kwargs.get("strength", 0.8),
                "context": kwargs.get("context", ""),
                "bidirectional": kwargs.get("bidirectional", False)
            }
            
            result = self.db.collection("term_relationships").insert(edge_doc)
            
            # Create reverse edge if bidirectional
            if kwargs.get("bidirectional", False):
                reverse_edge = {
                    "_from": to_id,
                    "_to": from_id,
                    "relationship": relationship,
                    "created_at": datetime.now().isoformat(),
                    "strength": kwargs.get("strength", 0.8),
                    "context": kwargs.get("context", ""),
                    "reverse_of": result["_id"]
                }
                self.db.collection("term_relationships").insert(reverse_edge)
            
            return {
                "success": True,
                "from_term": from_term,
                "to_term": to_term,
                "relationship": relationship,
                "message": f"Linked '{from_term}' --[{relationship}]--> '{to_term}'"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def link_term_to_log(self, term: str, log_id: str, relationship: str = "mentioned_in", **kwargs) -> Dict[str, Any]:
        """Create edge from glossary term to log event."""
        try:
            # Find the term
            term_query = """
            FOR doc IN glossary_terms
                FILTER doc.normalized_term == @normalized_term
                LIMIT 1
                RETURN doc
            """
            
            cursor = self.db.aql.execute(
                term_query,
                bind_vars={"normalized_term": term.lower().strip()}
            )
            term_docs = list(cursor)
            
            if not term_docs:
                return {
                    "success": False,
                    "error": f"Term '{term}' not found in glossary"
                }
            
            term_id = term_docs[0]["_id"]
            
            # Ensure log_id has collection prefix
            if "/" not in log_id:
                log_id = f"log_events/{log_id}"
            
            # Create edge in term_relationships
            edge_doc = {
                "_from": term_id,
                "_to": log_id,
                "relationship": relationship,
                "created_at": datetime.now().isoformat(),
                "context": kwargs.get("context", ""),
                "identified_by": kwargs.get("identified_by", "agent"),
                "confidence": kwargs.get("confidence", 0.8)
            }
            
            result = self.db.collection("term_relationships").insert(edge_doc)
            
            # Also increment usage count for the term
            self.db.collection("glossary_terms").update({
                "_key": term_docs[0]["_key"],
                "usage_count": term_docs[0].get("usage_count", 0) + 1,
                "last_seen": datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "term": term,
                "log_id": log_id,
                "relationship": relationship,
                "message": f"Linked term '{term}' --[{relationship}]--> log {log_id}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def research_database_issue(self, error_info: Dict[str, Any], auto_research: bool = False) -> Dict[str, Any]:
        """Prepare research context for database errors and issues.
        
        This method helps agents recover from errors by:
        1. Formatting error context for research
        2. Suggesting which MCP tools to use
        3. Caching research results
        
        Args:
            error_info: Dict containing error details, query, schema, etc.
            auto_research: Whether to include auto-research recommendations
            
        Returns:
            Research request with formatted prompts and tool suggestions
        """
        # Build comprehensive context
        context_parts = []
        
        # Error details
        if "error" in error_info:
            context_parts.append(f"Error Message: {error_info['error']}")
        if "error_code" in error_info:
            context_parts.append(f"Error Code: {error_info['error_code']}")
        if "aql" in error_info:
            context_parts.append(f"AQL Query:\n```aql\n{error_info['aql']}\n```")
        if "bind_vars" in error_info:
            context_parts.append(f"Bind Variables: {json.dumps(error_info['bind_vars'], indent=2)}")
        
        # Schema context
        if "collection" in error_info:
            schema_info = self._get_collection_schema(error_info["collection"])
            if schema_info:
                context_parts.append(f"Collection Schema:\n{json.dumps(schema_info, indent=2)}")
        
        # Create cache key
        cache_key = hashlib.sha256(
            json.dumps(error_info, sort_keys=True).encode()
        ).hexdigest()[:16]
        
        # Check cache first
        cached = self._check_research_cache(cache_key)
        if cached:
            return {
                "success": True,
                "cached": True,
                "research": cached,
                "message": "Found cached research for this issue"
            }
        
        # Build research prompts for different tools
        research_request = {
            "error_summary": error_info.get("error", "Unknown error"),
            "cache_key": cache_key,
            "created_at": datetime.now().isoformat(),
            
            # Tool-specific prompts
            "tool_suggestions": {
                
                # 1. Context7 for AQL documentation
                "context7": {
                    "action": "Use context7 to get ArangoDB AQL documentation",
                    "steps": [
                        "await mcp__context7__resolve-library-id('arangodb')",
                        "await mcp__context7__get-library-docs(context7_id, topic='aql queries')"
                    ],
                    "when": "For AQL syntax errors, unknown functions, or query optimization"
                },
                
                # 2. Perplexity for specific error research
                "perplexity": {
                    "action": "Research the specific error with perplexity-ask",
                    "prompt": f"""ArangoDB Error Analysis:

{chr(10).join(context_parts)}

Please provide:
1. Root cause of this error
2. Correct syntax or approach
3. Common mistakes that lead to this error
4. Best practices to avoid it
5. Example of working solution

Focus on ArangoDB {error_info.get('version', '3.11')} specific solutions.""",
                    "when": "For specific error codes, unusual behaviors, or complex issues"
                },
                
                # 3. Internal glossary check
                "glossary": {
                    "action": "Check internal glossary for related terms",
                    "aql": """
FOR term IN glossary_terms
    FILTER term.related_errors ANY == @error_type
    RETURN {
        term: term.term,
        definition: term.definition,
        examples: term.examples
    }""",
                    "bind_vars": {"error_type": error_info.get("error_type", "")},
                    "when": "To understand technical terms in the error"
                }
            },
            
            # Suggested recovery workflow
            "recovery_workflow": [
                "1. Check glossary for any unfamiliar terms in the error",
                "2. Use context7 to get official AQL documentation if syntax-related",
                "3. Use perplexity-ask for specific error code research if needed",
                "4. Update glossary with new terms discovered",
                "5. Link solution to this error for future reference"
            ]
        }
        
        # Store research request
        try:
            self.db.collection("research_cache").insert({
                "cache_key": cache_key,
                "error_info": error_info,
                "research_request": research_request,
                "status": "pending",
                "created_at": datetime.now().isoformat()
            })
        except:
            pass
        
        return {
            "success": True,
            "research_request": research_request,
            "message": "Research request prepared with tool suggestions",
            "next_steps": "Use the suggested tools in the recovery workflow"
        }
    
    def _get_collection_schema(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """Get schema for a specific collection."""
        try:
            col = self.db.collection(collection_name)
            # Get a sample document
            sample_cursor = self.db.aql.execute(
                f"FOR doc IN {collection_name} LIMIT 1 RETURN doc"
            )
            samples = list(sample_cursor)
            
            if samples:
                sample = samples[0]
                return {
                    "name": collection_name,
                    "type": "edge" if col.properties().get("type") == 3 else "document",
                    "sample_fields": {k: type(v).__name__ for k, v in sample.items()},
                    "count": col.count()
                }
        except:
            pass
        return None
    
    def _check_research_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Check for cached research results."""
        try:
            aql = """
            FOR doc IN research_cache
                FILTER doc.cache_key == @cache_key
                FILTER doc.status == "completed"
                FILTER doc.created_at > DATE_ISO8601(DATE_NOW() - 7*24*60*60*1000)
                LIMIT 1
                RETURN doc.research_result
            """
            cursor = self.db.aql.execute(aql, bind_vars={"cache_key": cache_key})
            results = list(cursor)
            return results[0] if results else None
        except:
            return None
    
    def save_research_result(self, cache_key: str, research_result: Dict[str, Any]) -> Dict[str, Any]:
        """Save research results to cache."""
        try:
            # Update the cache
            aql = """
            FOR doc IN research_cache
                FILTER doc.cache_key == @cache_key
                UPDATE doc WITH {
                    status: "completed",
                    research_result: @result,
                    completed_at: DATE_ISO8601(DATE_NOW())
                } IN research_cache
                RETURN NEW
            """
            
            self.db.aql.execute(
                aql,
                bind_vars={"cache_key": cache_key, "result": research_result}
            )
            
            # Extract and add any new terms to glossary
            if "terms" in research_result:
                for term_data in research_result["terms"]:
                    self.add_glossary_term(
                        term_data["term"],
                        term_data["definition"],
                        category="researched",
                        source="error_research",
                        confidence=0.9
                    )
            
            return {
                "success": True,
                "message": "Research results cached successfully",
                "cache_key": cache_key
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def track_solution_outcome(self, solution_id: str, outcome: str, key_reason: str, 
                             category: str, gotchas: Optional[List[str]] = None, 
                             time_to_resolve: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        """Track the outcome of applying a solution with key reasons and gotchas.
        
        Args:
            solution_id: ID of the solution that was applied
            outcome: 'success', 'partial', or 'failed'
            key_reason: The KEY reason why it worked/failed (not exhaustive)
            category: Category like 'async_fix', 'import_error', 'config_issue'
            gotchas: List of critical gotchas to remember
            time_to_resolve: Minutes taken to resolve
        """
        try:
            # Create outcome document
            outcome_doc = {
                "solution_id": solution_id,
                "outcome": outcome,
                "key_reason": key_reason,
                "category": category,
                "gotchas": gotchas or [],
                "time_to_resolve": time_to_resolve,
                "applied_at": datetime.now().isoformat(),
                "context": kwargs.get("context", {}),
                "success_score": 1.0 if outcome == "success" else 0.5 if outcome == "partial" else 0.0
            }
            
            # Ensure collection exists (in case it wasn't created on startup)
            if not self.db.has_collection("solution_outcomes"):
                self.db.create_collection("solution_outcomes")
            
            # Insert into solution_outcomes collection
            result = self.db.collection("solution_outcomes").insert(outcome_doc)
            outcome_id = result["_id"]
            
            # Update the original solution with outcome stats
            update_query = """
            FOR doc IN log_events
                FILTER doc._id == @solution_id
                LET outcomes = (
                    FOR o IN solution_outcomes
                        FILTER o.solution_id == @solution_id
                        COLLECT outcome = o.outcome WITH COUNT INTO count
                        RETURN {outcome: outcome, count: count}
                )
                UPDATE doc WITH {
                    last_outcome: @outcome,
                    last_applied: DATE_ISO8601(DATE_NOW()),
                    success_rate: (
                        FOR o IN solution_outcomes
                            FILTER o.solution_id == @solution_id
                            COLLECT AGGREGATE avg_score = AVG(o.success_score)
                            RETURN avg_score
                    )[0],
                    total_applications: LENGTH(outcomes)
                } IN log_events
                RETURN NEW
            """
            
            self.db.aql.execute(update_query, bind_vars={
                "solution_id": solution_id,
                "outcome": outcome
            })
            
            return {
                "success": True,
                "outcome_id": outcome_id,
                "message": f"Tracked {outcome} outcome for solution"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def discover_patterns(self, problem_id: str, search_depth: int = 2, 
                         min_similarity: float = 0.5) -> Dict[str, Any]:
        """Discover patterns by finding similar problems and their solutions."""
        try:
            # Multi-faceted pattern discovery query
            patterns_query = """
            LET problem = DOCUMENT(@problem_id)
            
            // 1. Find problems with similar error types
            LET similar_by_type = (
                FOR doc IN log_events
                    FILTER doc.error_type == problem.error_type
                    FILTER doc._id != @problem_id
                    FILTER doc.resolved == true
                    RETURN {
                        problem: doc,
                        similarity_type: "same_error_type",
                        solution: doc.resolution,
                        key_reason: (
                            FOR o IN solution_outcomes
                                FILTER o.solution_id == doc._id
                                FILTER o.outcome == "success"
                                LIMIT 1
                                RETURN o.key_reason
                        )[0]
                    }
            )
            
            // 2. Find problems via text similarity
            LET similar_by_text = (
                FOR doc IN log_search_view
                    SEARCH ANALYZER(doc.message IN TOKENS(problem.message, 'text_en'), 'text_en')
                    LET score = BM25(doc)
                    FILTER score > @min_similarity
                    FILTER doc._id != @problem_id
                    FILTER doc.resolved == true
                    SORT score DESC
                    LIMIT 10
                    RETURN {
                        problem: doc,
                        similarity_type: "text_similarity",
                        similarity_score: score,
                        solution: doc.resolution
                    }
            )
            
            // 3. Find connected problems via graph traversal
            LET graph_connected = (
                FOR v, e, p IN 1..@depth ANY @problem_id 
                    error_causality, term_relationships
                    FILTER v.resolved == true
                    RETURN DISTINCT {
                        problem: v,
                        similarity_type: "graph_connection",
                        path: p.edges[*].relationship_type,
                        solution: v.resolution
                    }
            )
            
            // 4. Analyze successful solution categories
            LET successful_categories = (
                FOR outcome IN solution_outcomes
                    FILTER outcome.outcome == "success"
                    FILTER outcome.category IN similar_by_type[*].problem.category OR
                           outcome.category IN similar_by_text[*].problem.category
                    COLLECT category = outcome.category WITH COUNT INTO count
                    SORT count DESC
                    RETURN {category: category, success_count: count}
            )
            
            RETURN {
                similar_by_type: similar_by_type,
                similar_by_text: similar_by_text,
                graph_connected: graph_connected,
                successful_categories: successful_categories,
                total_patterns: LENGTH(similar_by_type) + LENGTH(similar_by_text) + LENGTH(graph_connected)
            }
            """
            
            cursor = self.db.aql.execute(patterns_query, bind_vars={
                "problem_id": problem_id,
                "depth": search_depth,
                "min_similarity": min_similarity
            })
            
            results = list(cursor)[0]
            
            return {
                "success": True,
                "patterns": results,
                "summary": {
                    "total_similar": results["total_patterns"],
                    "top_categories": results["successful_categories"][:3]
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def extract_lesson(self, solution_ids: List[str], lesson: str, 
                      category: str, applies_to: List[str]) -> Dict[str, Any]:
        """Extract a general lesson learned from multiple solutions."""
        try:
            # Create lesson document
            lesson_doc = {
                "lesson": lesson,
                "category": category,
                "applies_to": applies_to,
                "derived_from": solution_ids,
                "evidence_count": len(solution_ids),
                "created_at": datetime.now().isoformat(),
                "confidence": min(1.0, len(solution_ids) * 0.2),  # More evidence = higher confidence
                "type": "general_principle"
            }
            
            # Insert into lessons_learned collection
            result = self.db.collection("lessons_learned").insert(lesson_doc)
            lesson_id = result["_id"]
            
            # Create edges from solutions to lesson
            for solution_id in solution_ids:
                edge_doc = {
                    "_from": solution_id,
                    "_to": lesson_id,
                    "relationship": "demonstrates_principle",
                    "created_at": datetime.now().isoformat()
                }
                self.db.collection("solution_to_lesson").insert(edge_doc)
            
            return {
                "success": True,
                "lesson_id": lesson_id,
                "message": f"Extracted lesson from {len(solution_ids)} solutions"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def advanced_search(self, **search_params) -> Dict[str, Any]:
        """Advanced multi-dimensional search with filters."""
        try:
            # Build dynamic query based on parameters
            filters = []
            bind_vars = {}
            
            # Category filter
            if "category" in search_params:
                filters.append("FILTER doc.category == @category")
                bind_vars["category"] = search_params["category"]
            
            # Error type filter
            if "error_type" in search_params:
                filters.append("FILTER doc.error_type == @error_type")
                bind_vars["error_type"] = search_params["error_type"]
            
            # Time range filter
            if "time_range" in search_params:
                if search_params["time_range"] == "last_hour":
                    filters.append("FILTER doc.timestamp > DATE_ISO8601(DATE_NOW() - 3600000)")
                elif search_params["time_range"] == "last_day":
                    filters.append("FILTER doc.timestamp > DATE_ISO8601(DATE_NOW() - 86400000)")
                elif search_params["time_range"] == "last_week":
                    filters.append("FILTER doc.timestamp > DATE_ISO8601(DATE_NOW() - 604800000)")
            
            # Success rate filter (for solutions)
            if "min_success_rate" in search_params:
                filters.append("FILTER doc.success_rate >= @min_success_rate")
                bind_vars["min_success_rate"] = search_params["min_success_rate"]
            
            # Text search
            if "search_text" in search_params:
                # Use BM25 search view
                base_query = f"""
                FOR doc IN log_search_view
                    SEARCH ANALYZER(doc.message IN TOKENS(@search_text, 'text_en'), 'text_en')
                    LET score = BM25(doc)
                    {' '.join(filters)}
                    SORT score DESC
                    LIMIT @limit
                    RETURN {{
                        document: doc,
                        score: score,
                        outcomes: (
                            FOR o IN solution_outcomes
                                FILTER o.solution_id == doc._id
                                RETURN o
                        )
                    }}
                """
                bind_vars["search_text"] = search_params["search_text"]
            else:
                # Regular collection query
                base_query = f"""
                FOR doc IN log_events
                    {' '.join(filters)}
                    SORT doc.timestamp DESC
                    LIMIT @limit
                    RETURN {{
                        document: doc,
                        outcomes: (
                            FOR o IN solution_outcomes
                                FILTER o.solution_id == doc._id
                                RETURN o
                        )
                    }}
                """
            
            bind_vars["limit"] = search_params.get("limit", 20)
            
            cursor = self.db.aql.execute(base_query, bind_vars=bind_vars)
            results = list(cursor)
            
            return {
                "success": True,
                "count": len(results),
                "results": results,
                "filters_applied": list(search_params.keys())
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def analyze_graph(self, graph_name: str, algorithm: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute graph analysis algorithms.
        
        Args:
            graph_name: Name of the graph to analyze
            algorithm: Algorithm to run ('shortest_path', 'connected_components', 'neighbors')
            params: Algorithm-specific parameters
        
        Returns:
            Analysis results
        """
        params = params or {}
        
        try:
            if algorithm == "shortest_path":
                # Validate required parameters
                if "start_node" not in params or "end_node" not in params:
                    return {
                        "success": False,
                        "error": "shortest_path requires 'start_node' and 'end_node' parameters"
                    }
                
                # Find shortest path
                aql = """
                FOR path IN ANY SHORTEST_PATH @start TO @end
                GRAPH @graph_name
                RETURN {
                    vertices: path.vertices[*]._id,
                    edges: path.edges[*]._id,
                    length: LENGTH(path.edges),
                    path: path
                }
                """
                
                cursor = self.db.aql.execute(aql, bind_vars={
                    "start": params["start_node"],
                    "end": params["end_node"],
                    "graph_name": graph_name
                })
                
                paths = list(cursor)
                if paths:
                    return {
                        "success": True,
                        "algorithm": "shortest_path",
                        "path_found": True,
                        "result": paths[0]
                    }
                else:
                    return {
                        "success": True,
                        "algorithm": "shortest_path",
                        "path_found": False,
                        "message": "No path found between the nodes"
                    }
            
            elif algorithm == "connected_components":
                # Find weakly connected components - simplified approach
                aql = """
                // Get vertices with their connections
                FOR edge IN error_causality
                    LIMIT 100
                    LET from_id = edge._from
                    LET to_id = edge._to
                    
                    // Find connected vertices
                    LET connected = (
                        FOR v, e, p IN 1..10 ANY from_id 
                        GRAPH @graph_name
                        OPTIONS {bfs: true, uniqueVertices: 'global'}
                        RETURN DISTINCT v._id
                    )
                    
                    COLLECT component_key = SORTED(connected)[0] INTO group
                    LET component_size = LENGTH(group)
                    
                    RETURN {
                        representative: component_key,
                        size: component_size,
                        sample_members: group[*].from_id[0..5],
                        graph_name: @graph_name
                    }
                """
                
                cursor = self.db.aql.execute(aql, bind_vars={
                    "graph_name": graph_name
                })
                
                components = list(cursor)
                return {
                    "success": True,
                    "algorithm": "connected_components",
                    "components": components,
                    "total_components": len(components)
                }
            
            elif algorithm == "neighbors":
                # Find neighbors of a node
                if "node" not in params:
                    return {
                        "success": False,
                        "error": "neighbors requires 'node' parameter"
                    }
                
                depth = params.get("depth", 1)
                direction = params.get("direction", "ANY")  # ANY, OUTBOUND, INBOUND
                
                aql = f"""
                FOR vertex, edge, path IN 1..@depth {direction} @start_node 
                GRAPH @graph_name
                OPTIONS {{bfs: true, uniqueVertices: 'global'}}
                    LET current_depth = LENGTH(path.edges)
                    COLLECT depth = current_depth INTO nodes
                    SORT depth
                    RETURN {{
                        depth: depth,
                        count: LENGTH(nodes),
                        vertices: nodes[*].vertex._id
                    }}
                """
                
                cursor = self.db.aql.execute(aql, bind_vars={
                    "start_node": params["node"],
                    "depth": depth,
                    "graph_name": graph_name
                })
                
                neighbors = list(cursor)
                return {
                    "success": True,
                    "algorithm": "neighbors",
                    "node": params["node"],
                    "direction": direction,
                    "max_depth": depth,
                    "neighbors_by_depth": neighbors
                }
            
            elif algorithm == "centrality":
                # Basic degree centrality - analyze nodes in the graph
                aql = """
                // Get all connections from relevant edge collections
                LET all_connections = UNION(
                    (FOR edge IN error_causality
                        FOR node IN [edge._from, edge._to]
                        RETURN node),
                    (FOR edge IN agent_flow
                        FOR node IN [edge._from, edge._to]
                        RETURN node),
                    (FOR edge IN artifact_lineage
                        FOR node IN [edge._from, edge._to]
                        RETURN node),
                    (FOR edge IN insight_applications
                        FOR node IN [edge._from, edge._to]
                        RETURN node),
                    (FOR edge IN tool_dependencies
                        FOR node IN [edge._from, edge._to]
                        RETURN node)
                )
                
                // Count connections per node
                FOR node IN all_connections
                    COLLECT vertex = node WITH COUNT INTO total_connections
                    SORT total_connections DESC
                    LIMIT 20
                    
                    // Get detailed degree for top nodes
                    LET in_degree = LENGTH(UNION(
                        (FOR e IN error_causality FILTER e._to == vertex RETURN 1),
                        (FOR e IN agent_flow FILTER e._to == vertex RETURN 1),
                        (FOR e IN artifact_lineage FILTER e._to == vertex RETURN 1),
                        (FOR e IN insight_applications FILTER e._to == vertex RETURN 1),
                        (FOR e IN tool_dependencies FILTER e._to == vertex RETURN 1)
                    ))
                    
                    LET out_degree = LENGTH(UNION(
                        (FOR e IN error_causality FILTER e._from == vertex RETURN 1),
                        (FOR e IN agent_flow FILTER e._from == vertex RETURN 1),
                        (FOR e IN artifact_lineage FILTER e._from == vertex RETURN 1),
                        (FOR e IN insight_applications FILTER e._from == vertex RETURN 1),
                        (FOR e IN tool_dependencies FILTER e._from == vertex RETURN 1)
                    ))
                    
                    RETURN {
                        vertex: vertex,
                        total_connections: total_connections,
                        in_degree: in_degree,
                        out_degree: out_degree
                    }
                """
                
                cursor = self.db.aql.execute(aql)
                
                centrality = list(cursor)
                return {
                    "success": True,
                    "algorithm": "centrality",
                    "type": "degree_centrality",
                    "top_nodes": centrality,
                    "note": "For PageRank or Betweenness centrality, use ArangoDB Pregel"
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown algorithm: {algorithm}",
                    "supported": ["shortest_path", "connected_components", "neighbors", "centrality"]
                }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "algorithm": algorithm
            }
    
    def find_tool_sequences(self, task_pattern: str, min_success_rate: float = 0.7,
                           limit: int = 10) -> Dict[str, Any]:
        """Find successful tool sequences for tasks matching a pattern.
        
        Uses BM25 search if view exists, falls back to pattern matching.
        """
        try:
            # Check if we have a search view
            schema = self.get_schema()
            has_search_view = any(v["name"] == "agent_activity_search" 
                                for v in schema.get("views", []))
            
            if has_search_view:
                # Use BM25 search
                query = """
                FOR doc IN agent_activity_search
                    SEARCH ANALYZER(
                        doc.event_type == "tool_journey_completed" AND
                        PHRASE(doc.task_description, @pattern, "text_en"),
                        "text_en"
                    )
                    
                    LET score = BM25(doc)
                    FILTER score > 0.3
                    FILTER doc.success_rate >= @min_rate
                    
                    SORT score DESC, doc.success_rate DESC
                    LIMIT @limit
                    
                    RETURN {
                        task: doc.task_description,
                        tool_sequence: doc.tool_sequence,
                        success_rate: doc.success_rate,
                        duration: doc.duration,
                        similarity_score: score,
                        journey_id: doc._key
                    }
                """
            else:
                # Fallback to pattern matching
                query = """
                FOR doc IN log_events
                    FILTER doc.event_type == "tool_journey_completed"
                    FILTER doc.outcome == "success"
                    FILTER doc.success_rate >= @min_rate
                    FILTER CONTAINS(LOWER(doc.task_description), LOWER(@pattern))
                    
                    SORT doc.success_rate DESC, doc.duration ASC
                    LIMIT @limit
                    
                    RETURN {
                        task: doc.task_description,
                        tool_sequence: doc.tool_sequence,
                        success_rate: doc.success_rate,
                        duration: doc.duration,
                        journey_id: doc._key
                    }
                """
            
            result = self.execute_aql(query, {
                "pattern": task_pattern,
                "min_rate": min_success_rate,
                "limit": limit
            })
            
            if result["success"]:
                return {
                    "success": True,
                    "count": result["count"],
                    "sequences": result["results"],
                    "search_method": "BM25" if has_search_view else "pattern_match"
                }
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def analyze_tool_performance(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """Analyze tool usage patterns and performance metrics."""
        try:
            query = """
            LET cutoff_time = DATE_SUBTRACT(DATE_NOW(), @hours, "hours")
            
            // Analyze completed journeys
            LET journey_stats = (
                FOR doc IN log_events
                    FILTER doc.event_type == "tool_journey_completed"
                    FILTER doc.timestamp >= cutoff_time
                    
                    COLLECT sequence = doc.tool_sequence
                    AGGREGATE 
                        total = COUNT(1),
                        successes = SUM(doc.outcome == "success" ? 1 : 0),
                        avg_duration = AVG(doc.duration)
                        
                    LET success_rate = successes / total
                    
                    FILTER total >= 3  // Minimum sample size
                    SORT success_rate DESC
                    LIMIT 10
                    
                    RETURN {
                        sequence: sequence,
                        usage_count: total,
                        success_rate: success_rate,
                        avg_duration: avg_duration
                    }
            )
            
            // Most used individual tools
            LET tool_usage = (
                FOR doc IN log_events
                    FILTER doc.event_type == "tool_journey_completed"
                    FILTER doc.timestamp >= cutoff_time
                    
                    FOR tool IN (doc.tool_sequence || [])
                        COLLECT tool_name = tool
                        WITH COUNT INTO uses
                        
                        SORT uses DESC
                        LIMIT 10
                        
                        RETURN {
                            tool: tool_name,
                            usage_count: uses
                        }
            )
            
            RETURN {
                top_sequences: journey_stats,
                most_used_tools: tool_usage,
                time_range_hours: @hours
            }
            """
            
            result = self.execute_aql(query, {"hours": time_range_hours})
            
            if result["success"] and result["results"]:
                stats = result["results"][0]
                return {
                    "success": True,
                    "top_sequences": stats["top_sequences"],
                    "most_used_tools": stats["most_used_tools"],
                    "time_range_hours": stats["time_range_hours"]
                }
            
            return {"success": False, "error": "No data found"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def store_tool_journey(self, journey_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store a completed tool journey for learning."""
        try:
            # Ensure required fields
            journey_data["event_type"] = "tool_journey_completed"
            journey_data["timestamp"] = journey_data.get("timestamp", 
                                                         datetime.now().isoformat())
            
            # Calculate success rate if not provided
            if "success_rate" not in journey_data:
                journey_data["success_rate"] = 1.0 if journey_data.get("outcome") == "success" else 0.0
            
            # Store in log_events
            return self.insert("log_events", journey_data)
            
        except Exception as e:
            return {"success": False, "error": str(e)}


# Create global instance
tools = ArangoTools()


@mcp.tool()
@debug_tool(mcp_logger)
async def schema() -> str:
    """Get ArangoDB schema including collections, views, graphs, and sample queries."""
    result = tools.get_schema()
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
@debug_tool(mcp_logger)
async def query(aql: str, bind_vars: Optional[str] = None) -> str:
    """Execute AQL query with optional bind variables.
    
    Examples:
    - query("FOR doc IN log_events LIMIT 5 RETURN doc")
    - query("FOR doc IN @@col FILTER doc.level == @level RETURN doc", '{"@col": "log_events", "level": "ERROR"}')
    
    Use english_to_aql first if you need help constructing queries.
    
    If the query fails, this tool will automatically provide:
    - Error-specific suggestions
    - Research recommendations using context7 for AQL docs
    - Perplexity-ask prompts for specific errors
    - Cached solutions from previous similar errors
    
    Args:
        aql: The AQL query string
        bind_vars: Optional JSON string of bind variables
    """
    # Parse bind_vars if provided as JSON string
    parsed_bind_vars = None
    if bind_vars:
        try:
            parsed_bind_vars = json.loads(bind_vars)
        except json.JSONDecodeError as e:
            return json.dumps({
                "success": False,
                "error": f"Invalid JSON in bind_vars: {str(e)}",
                "suggestion": "Ensure bind_vars is a valid JSON string"
            }, indent=2)
    
    result = tools.execute_aql(aql, parsed_bind_vars)
    
    # If query failed, add research suggestions
    if not result.get("success", True) and "error" in result:
        # Prepare error context for research
        error_info = {
            "error": result["error"],
            "aql": aql,
            "bind_vars": bind_vars,
            "suggestions": result.get("suggestions", [])
        }
        
        # Get research suggestions
        research = tools.research_database_issue(error_info)
        
        # Add research info to result
        result["research_help"] = research.get("research_request", {})
        result["recovery_steps"] = research.get("research_request", {}).get("recovery_workflow", [])
        
        # Add explicit tool suggestions
        result["use_these_tools"] = {
            "for_aql_syntax": "await mcp__context7__resolve-library-id('arangodb') then get-library-docs with topic='aql'",
            "for_error_research": "await mcp__perplexity-ask__perplexity_ask with the error context",
            "for_terms": "await mcp__arango-tools__query to search glossary_terms"
        }
    
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
@debug_tool(mcp_logger)
async def insert(
    message: str,
    level: str = "INFO",
    error_type: Optional[str] = None,
    script_name: Optional[str] = None,
    fix_description: Optional[str] = None,
    fix_rationale: Optional[str] = None,
    resolved: Optional[bool] = None,
    execution_id: Optional[str] = None,
    task_id: Optional[str] = None,
    duration: Optional[float] = None,
    metadata: Optional[str] = None  # JSON string for additional data
) -> str:
    """Insert a log event or data into the database."""
    # Collect all parameters
    params = {
        "error_type": error_type,
        "script_name": script_name,
        "fix_description": fix_description,
        "fix_rationale": fix_rationale,
        "resolved": resolved,
        "execution_id": execution_id,
        "task_id": task_id,
        "duration": duration
    }
    
    # Parse metadata if provided
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
            params.update(metadata_dict)
        except:
            pass
    
    # Remove None values
    params = {k: v for k, v in params.items() if v is not None}
    
    result = tools.insert_log(message, level, **params)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
@debug_tool(mcp_logger)
async def edge(
    from_id: str,
    to_id: str,
    collection: str,
    relationship_type: Optional[str] = None,
    fix_time_minutes: Optional[int] = None,
    sequence: Optional[float] = None,
    metadata: Optional[str] = None  # JSON string for additional edge properties
) -> str:
    """Create an edge between two documents in a graph.
    
    Examples:
    - Link error to fix: edge("log_events/123", "log_events/456", "error_causality", "fixed_by")
    - Link related scripts: edge("scripts/a.py", "scripts/b.py", "script_dependencies", "imports")
    
    Common edge collections: error_causality, agent_flow, script_dependencies
    """
    params = {}
    if relationship_type:
        params["relationship_type"] = relationship_type
    if fix_time_minutes is not None:
        params["fix_time_minutes"] = fix_time_minutes
    if sequence is not None:
        params["sequence"] = sequence
    
    # Parse metadata if provided
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
            params.update(metadata_dict)
        except:
            pass
    
    result = tools.create_edge(from_id, to_id, collection, **params)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
@debug_tool(mcp_logger)
async def upsert(
    collection: str,
    search: str,
    update: str,
    create: Optional[str] = None
) -> str:
    """Update a document if it exists, create if not (upsert operation).
    
    Examples:
    - Track script runs: upsert("script_runs", '{"script_name": "test.py"}', '{"last_run": "2024-01-15", "run_count": 5}')
    - Update error status: upsert("log_events", '{"_key": "123"}', '{"resolved": true, "fix_description": "Fixed"}')
    
    The search fields identify the document, update fields are applied to existing or new documents.
    """
    try:
        search_dict = json.loads(search)
        update_dict = json.loads(update)
        create_dict = json.loads(create) if create else None
        
        result = tools.upsert_document(collection, search_dict, update_dict, create_dict)
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e), "type": type(e).__name__}, indent=2)


if __name__ == "__main__":
    # Run as MCP server
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            # Run tests
            print("Testing ArangoDB MCP server...")
            print(f"Environment: ARANGO_DATABASE={os.getenv('ARANGO_DATABASE', 'Not set')}")
            print(f"Tools instance: {tools}")
            print("Server ready to start.")
        else:
            try:
                logger.info("Starting ArangoDB MCP server")
                mcp.run()
            except Exception as e:
                logger.critical(f"MCP Server crashed: {e}", exc_info=True)
                mcp_logger.log_error(e, {"context": "server_startup"})
                sys.exit(1)
    else:
        try:
            logger.info("Starting ArangoDB MCP server")
            mcp.run()
        except Exception as e:
            logger.critical(f"MCP Server crashed: {e}", exc_info=True)
            mcp_logger.log_error(e, {"context": "server_startup"})
            sys.exit(1)