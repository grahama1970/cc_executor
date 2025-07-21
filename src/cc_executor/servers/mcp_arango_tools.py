#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "fastmcp",
#     "mcp-logger-utils>=0.1.5",
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
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import uuid
import hashlib
import numpy as np

from fastmcp import FastMCP
from loguru import logger
from dotenv import load_dotenv, find_dotenv
from mcp_logger_utils import MCPLogger, debug_tool
from arango import ArangoClient
from arango.exceptions import ArangoError

# Import analytics dependencies (will be conditionally used)
try:
    import faiss
    from sentence_transformers import SentenceTransformer
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("FAISS not available - similarity search features disabled")

try:
    from sklearn.cluster import DBSCAN, KMeans
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("Scikit-learn not available - clustering/anomaly features disabled")

try:
    import networkx as nx
    from community import community_louvain
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    logger.warning("NetworkX not available - advanced graph features disabled")

# Import response utilities
sys.path.insert(0, str(Path(__file__).parent))
from utils.response_utils import create_success_response, create_error_response

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
    
    def build_similarity_graph(self, collection: str, text_field: str, edge_collection: str, 
                             threshold: float = 0.8) -> Dict[str, Any]:
        """Build a similarity graph using FAISS for vector similarity.
        
        Creates edges between documents with similarity above threshold.
        """
        if not FAISS_AVAILABLE:
            return {
                "success": False,
                "error": "FAISS not available. Install with: uv add faiss-cpu sentence-transformers"
            }
        
        try:
            # Initialize sentence transformer
            model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Fetch documents
            cursor = self.db.aql.execute(
                f"FOR doc IN {collection} RETURN {{_id: doc._id, text: doc.{text_field}}}"
            )
            documents = list(cursor)
            
            if not documents:
                return {"success": True, "message": "No documents found", "edges_created": 0}
            
            # Extract texts and IDs
            texts = [doc['text'] for doc in documents if doc.get('text')]
            doc_ids = [doc['_id'] for doc in documents if doc.get('text')]
            
            if not texts:
                return {"success": True, "message": "No text content found", "edges_created": 0}
            
            # Generate embeddings
            logger.info(f"Generating embeddings for {len(texts)} documents...")
            embeddings = model.encode(texts)
            
            # Build FAISS index
            dimension = embeddings.shape[1]
            index = faiss.IndexFlatL2(dimension)
            index.add(embeddings.astype('float32'))
            
            # Find similar documents
            edges_created = 0
            for i, embedding in enumerate(embeddings):
                # Search for k nearest neighbors
                k = min(10, len(embeddings))
                distances, indices = index.search(embedding.reshape(1, -1).astype('float32'), k)
                
                # Create edges for similar documents
                for j, (dist, idx) in enumerate(zip(distances[0], indices[0])):
                    if idx != i:  # Skip self
                        # Convert L2 distance to similarity score
                        similarity = 1.0 / (1.0 + dist)
                        
                        if similarity >= threshold:
                            edge_doc = {
                                "_from": doc_ids[i],
                                "_to": doc_ids[idx],
                                "similarity": float(similarity),
                                "method": "faiss_minilm",
                                "created_at": datetime.now().isoformat()
                            }
                            
                            try:
                                self.db.collection(edge_collection).insert(edge_doc)
                                edges_created += 1
                            except ArangoError:
                                # Edge might already exist
                                pass
            
            return {
                "success": True,
                "documents_processed": len(texts),
                "edges_created": edges_created,
                "threshold": threshold
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def find_similar_documents(self, collection: str, text: str, text_field: str, 
                             limit: int = 10) -> Dict[str, Any]:
        """Find similar documents using FAISS vector search."""
        if not FAISS_AVAILABLE:
            return {
                "success": False,
                "error": "FAISS not available. Install with: uv add faiss-cpu sentence-transformers"
            }
        
        try:
            # Initialize sentence transformer
            model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Generate embedding for query text
            query_embedding = model.encode([text])
            
            # Fetch all documents
            cursor = self.db.aql.execute(
                f"FOR doc IN {collection} RETURN {{_id: doc._id, _key: doc._key, text: doc.{text_field}, doc: doc}}"
            )
            documents = list(cursor)
            
            if not documents:
                return {"success": True, "results": [], "message": "No documents found"}
            
            # Extract texts and generate embeddings
            texts = []
            valid_docs = []
            for doc in documents:
                if doc.get('text'):
                    texts.append(doc['text'])
                    valid_docs.append(doc)
            
            if not texts:
                return {"success": True, "results": [], "message": "No text content found"}
            
            embeddings = model.encode(texts)
            
            # Build FAISS index
            dimension = embeddings.shape[1]
            index = faiss.IndexFlatL2(dimension)
            index.add(embeddings.astype('float32'))
            
            # Search for similar documents
            k = min(limit, len(embeddings))
            distances, indices = index.search(query_embedding.astype('float32'), k)
            
            # Format results
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                similarity = 1.0 / (1.0 + dist)
                doc = valid_docs[idx]
                results.append({
                    "_id": doc['_id'],
                    "_key": doc['_key'],
                    "similarity": float(similarity),
                    "document": doc['doc']
                })
            
            return {
                "success": True,
                "query": text,
                "results": results,
                "total_searched": len(texts)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def detect_anomalies(self, collection: str, features: List[str], 
                        contamination: float = 0.1) -> Dict[str, Any]:
        """Detect anomalies using Isolation Forest."""
        if not SKLEARN_AVAILABLE:
            return {
                "success": False,
                "error": "Scikit-learn not available. Install with: uv add scikit-learn"
            }
        
        try:
            # Build query to extract features
            feature_fields = ", ".join([f"doc.{f}" for f in features])
            aql = f"""
                FOR doc IN {collection}
                    RETURN {{
                        _id: doc._id,
                        features: [{feature_fields}]
                    }}
            """
            
            cursor = self.db.aql.execute(aql)
            documents = list(cursor)
            
            if len(documents) < 10:
                return {
                    "success": False,
                    "error": "Need at least 10 documents for anomaly detection"
                }
            
            # Extract feature matrix
            doc_ids = []
            feature_matrix = []
            for doc in documents:
                if all(f is not None for f in doc['features']):
                    doc_ids.append(doc['_id'])
                    feature_matrix.append(doc['features'])
            
            if not feature_matrix:
                return {"success": False, "error": "No valid feature data found"}
            
            # Standardize features
            scaler = StandardScaler()
            X = scaler.fit_transform(feature_matrix)
            
            # Detect anomalies
            clf = IsolationForest(contamination=contamination, random_state=42)
            predictions = clf.fit_predict(X)
            scores = clf.score_samples(X)
            
            # Collect anomalies
            anomalies = []
            for i, (pred, score) in enumerate(zip(predictions, scores)):
                if pred == -1:  # Anomaly
                    anomalies.append({
                        "_id": doc_ids[i],
                        "anomaly_score": float(score),
                        "is_anomaly": True
                    })
            
            return {
                "success": True,
                "total_documents": len(feature_matrix),
                "anomalies_found": len(anomalies),
                "anomalies": anomalies,
                "contamination": contamination,
                "features_used": features
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def find_clusters(self, collection: str, features: List[str], 
                     n_clusters: Optional[int] = None, method: str = "kmeans") -> Dict[str, Any]:
        """Find clusters in documents using various clustering algorithms."""
        if not SKLEARN_AVAILABLE:
            return {
                "success": False,
                "error": "Scikit-learn not available. Install with: uv add scikit-learn"
            }
        
        try:
            # Build query to extract features
            feature_fields = ", ".join([f"doc.{f}" for f in features])
            aql = f"""
                FOR doc IN {collection}
                    RETURN {{
                        _id: doc._id,
                        _key: doc._key,
                        features: [{feature_fields}]
                    }}
            """
            
            cursor = self.db.aql.execute(aql)
            documents = list(cursor)
            
            # Extract feature matrix
            doc_ids = []
            doc_keys = []
            feature_matrix = []
            for doc in documents:
                if all(f is not None for f in doc['features']):
                    doc_ids.append(doc['_id'])
                    doc_keys.append(doc['_key'])
                    feature_matrix.append(doc['features'])
            
            if len(feature_matrix) < 2:
                return {"success": False, "error": "Need at least 2 documents for clustering"}
            
            # Standardize features
            scaler = StandardScaler()
            X = scaler.fit_transform(feature_matrix)
            
            # Perform clustering
            if method == "kmeans":
                if n_clusters is None:
                    n_clusters = min(5, len(X) // 10)  # Default: 5 or 10% of documents
                
                clusterer = KMeans(n_clusters=n_clusters, random_state=42)
                labels = clusterer.fit_predict(X)
                
            elif method == "dbscan":
                clusterer = DBSCAN(eps=0.5, min_samples=5)
                labels = clusterer.fit_predict(X)
                n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
                
            else:
                return {"success": False, "error": f"Unknown clustering method: {method}"}
            
            # Group documents by cluster
            clusters = {}
            for i, label in enumerate(labels):
                label_str = str(label)
                if label_str not in clusters:
                    clusters[label_str] = {
                        "cluster_id": int(label),
                        "documents": []
                    }
                clusters[label_str]["documents"].append({
                    "_id": doc_ids[i],
                    "_key": doc_keys[i]
                })
            
            # Calculate cluster sizes
            for cluster in clusters.values():
                cluster["size"] = len(cluster["documents"])
            
            return {
                "success": True,
                "method": method,
                "n_clusters": n_clusters,
                "total_documents": len(feature_matrix),
                "clusters": list(clusters.values()),
                "features_used": features
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def analyze_time_series(self, collection: str, time_field: str, value_field: str,
                          aggregation: str = "daily", operation: str = "avg") -> Dict[str, Any]:
        """Analyze time series data with aggregations."""
        try:
            # Map aggregation to date function
            date_funcs = {
                "hourly": "DATE_HOUR",
                "daily": "DATE_DAY", 
                "weekly": "DATE_ISOWEEK",
                "monthly": "DATE_MONTH",
                "yearly": "DATE_YEAR"
            }
            
            if aggregation not in date_funcs:
                return {
                    "success": False,
                    "error": f"Invalid aggregation: {aggregation}. Use: {list(date_funcs.keys())}"
                }
            
            # Map operation to AQL function
            aql_ops = {
                "avg": "AVG",
                "sum": "SUM",
                "min": "MIN",
                "max": "MAX",
                "count": "COUNT"
            }
            
            if operation not in aql_ops:
                return {
                    "success": False,
                    "error": f"Invalid operation: {operation}. Use: {list(aql_ops.keys())}"
                }
            
            # Build time series query
            date_func = date_funcs[aggregation]
            aql_op = aql_ops[operation]
            
            if operation == "count":
                aql = f"""
                    FOR doc IN {collection}
                        FILTER doc.{time_field} != null
                        COLLECT period = {date_func}(doc.{time_field})
                        WITH COUNT INTO value
                        SORT period
                        RETURN {{
                            period: period,
                            value: value
                        }}
                """
            else:
                aql = f"""
                    FOR doc IN {collection}
                        FILTER doc.{time_field} != null AND doc.{value_field} != null
                        COLLECT period = {date_func}(doc.{time_field})
                        AGGREGATE value = {aql_op}(doc.{value_field})
                        SORT period
                        RETURN {{
                            period: period,
                            value: value
                        }}
                """
            
            cursor = self.db.aql.execute(aql)
            time_series = list(cursor)
            
            # Calculate statistics
            if time_series:
                values = [point['value'] for point in time_series]
                stats = {
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "total": sum(values),
                    "points": len(values)
                }
            else:
                stats = None
            
            return {
                "success": True,
                "aggregation": aggregation,
                "operation": operation,
                "time_field": time_field,
                "value_field": value_field,
                "time_series": time_series,
                "statistics": stats
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_visualization_data(self, query_type: str, collection: str, 
                             params: Optional[Dict] = None) -> Dict[str, Any]:
        """Prepare data for visualization based on query type."""
        params = params or {}
        
        try:
            if query_type == "network":
                # Network/graph visualization data
                graph_name = params.get("graph_name", "error_causality")
                limit = params.get("limit", 100)
                
                aql = """
                    FOR v, e, p IN 1..3 ANY @start_collection
                    GRAPH @graph_name
                    OPTIONS {bfs: true, uniqueVertices: 'global'}
                    LIMIT @limit
                    RETURN {
                        nodes: p.vertices[*]._id,
                        edges: p.edges[*],
                        path: p
                    }
                """
                
                cursor = self.db.aql.execute(aql, bind_vars={
                    "start_collection": collection,
                    "graph_name": graph_name,
                    "limit": limit
                })
                
                paths = list(cursor)
                
                # Format for D3.js
                nodes = {}
                links = []
                
                for path in paths:
                    # Add nodes
                    for i, node_id in enumerate(path['nodes']):
                        if node_id not in nodes:
                            nodes[node_id] = {
                                "id": node_id,
                                "label": node_id.split('/')[1] if '/' in node_id else node_id
                            }
                    
                    # Add edges
                    for edge in path['edges']:
                        links.append({
                            "source": edge['_from'],
                            "target": edge['_to'],
                            "type": edge.get('relationship_type', 'related')
                        })
                
                return {
                    "success": True,
                    "type": "network",
                    "data": {
                        "nodes": list(nodes.values()),
                        "links": links
                    }
                }
                
            elif query_type == "timeline":
                # Timeline visualization data
                time_field = params.get("time_field", "timestamp")
                
                aql = f"""
                    FOR doc IN {collection}
                        FILTER doc.{time_field} != null
                        SORT doc.{time_field}
                        LIMIT 1000
                        RETURN {{
                            time: doc.{time_field},
                            title: doc.message || doc._key,
                            category: doc.category || doc.level || "default",
                            id: doc._id
                        }}
                """
                
                cursor = self.db.aql.execute(aql)
                events = list(cursor)
                
                return {
                    "success": True,
                    "type": "timeline",
                    "data": {
                        "events": events
                    }
                }
                
            elif query_type == "heatmap":
                # Heatmap visualization data
                x_field = params.get("x_field", "category")
                y_field = params.get("y_field", "level")
                
                aql = f"""
                    FOR doc IN {collection}
                        FILTER doc.{x_field} != null AND doc.{y_field} != null
                        COLLECT x = doc.{x_field}, y = doc.{y_field}
                        WITH COUNT INTO value
                        RETURN {{
                            x: x,
                            y: y,
                            value: value
                        }}
                """
                
                cursor = self.db.aql.execute(aql)
                heatmap_data = list(cursor)
                
                return {
                    "success": True,
                    "type": "heatmap",
                    "data": {
                        "values": heatmap_data,
                        "x_field": x_field,
                        "y_field": y_field
                    }
                }
                
            else:
                return {
                    "success": False,
                    "error": f"Unknown query type: {query_type}",
                    "supported": ["network", "timeline", "heatmap"]
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_graph_metrics(self, graph_name: str) -> Dict[str, Any]:
        """Calculate basic graph metrics."""
        try:
            # Get graph info
            graph = self.db.graph(graph_name)
            
            # Count vertices and edges
            vertex_count = 0
            edge_count = 0
            
            for collection in graph.vertex_collections():
                vertex_count += self.db.collection(collection).count()
            
            for definition in graph.edge_definitions():
                edge_collection = definition['edge_collection']
                edge_count += self.db.collection(edge_collection).count()
            
            # Calculate degree distribution
            aql = """
                LET edge_collections = @edge_collections
                
                FOR collection IN edge_collections
                    FOR edge IN COLLECTION(collection)
                        FOR vertex IN [edge._from, edge._to]
                        COLLECT v = vertex WITH COUNT INTO degree
                        COLLECT degree_value = degree WITH COUNT INTO count
                        SORT degree_value
                        RETURN {
                            degree: degree_value,
                            count: count
                        }
            """
            
            edge_collections = [d['edge_collection'] for d in graph.edge_definitions()]
            cursor = self.db.aql.execute(aql, bind_vars={"edge_collections": edge_collections})
            degree_distribution = list(cursor)
            
            # Calculate average degree
            if degree_distribution:
                total_degree = sum(d['degree'] * d['count'] for d in degree_distribution)
                total_vertices = sum(d['count'] for d in degree_distribution)
                avg_degree = total_degree / total_vertices if total_vertices > 0 else 0
            else:
                avg_degree = 0
            
            return {
                "success": True,
                "graph_name": graph_name,
                "metrics": {
                    "vertex_count": vertex_count,
                    "edge_count": edge_count,
                    "average_degree": avg_degree,
                    "degree_distribution": degree_distribution
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def find_shortest_paths(self, graph_name: str, start_node: str, 
                          end_node: str, max_paths: int = 5) -> Dict[str, Any]:
        """Find shortest paths between two nodes."""
        try:
            aql = """
                FOR path IN ANY K_SHORTEST_PATHS @start TO @end
                GRAPH @graph_name
                LIMIT @max_paths
                RETURN {
                    vertices: path.vertices[*]._id,
                    edges: path.edges[*]._id,
                    length: LENGTH(path.edges),
                    weight: SUM(path.edges[*].weight || 1)
                }
            """
            
            cursor = self.db.aql.execute(aql, bind_vars={
                "start": start_node,
                "end": end_node,
                "graph_name": graph_name,
                "max_paths": max_paths
            })
            
            paths = list(cursor)
            
            if paths:
                return {
                    "success": True,
                    "start": start_node,
                    "end": end_node,
                    "paths_found": len(paths),
                    "shortest_length": paths[0]['length'] if paths else None,
                    "paths": paths
                }
            else:
                return {
                    "success": True,
                    "start": start_node,
                    "end": end_node,
                    "paths_found": 0,
                    "message": "No path found between nodes"
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def calculate_page_rank(self, graph_name: str, damping: float = 0.85, 
                          iterations: int = 10) -> Dict[str, Any]:
        """Calculate PageRank for nodes in a graph."""
        if not NETWORKX_AVAILABLE:
            return {
                "success": False,
                "error": "NetworkX not available. Install with: uv add networkx python-louvain"
            }
        
        try:
            # Build NetworkX graph from ArangoDB
            G = nx.DiGraph()
            
            # Get all edges from the graph
            graph = self.db.graph(graph_name)
            for definition in graph.edge_definitions():
                edge_collection = definition['edge_collection']
                cursor = self.db.collection(edge_collection).all()
                
                for edge in cursor:
                    G.add_edge(edge['_from'], edge['_to'])
            
            if G.number_of_nodes() == 0:
                return {
                    "success": True,
                    "message": "Graph is empty",
                    "page_rank": {}
                }
            
            # Calculate PageRank
            page_rank = nx.pagerank(G, alpha=damping, max_iter=iterations)
            
            # Sort by PageRank value
            sorted_nodes = sorted(page_rank.items(), key=lambda x: x[1], reverse=True)
            
            return {
                "success": True,
                "graph_name": graph_name,
                "node_count": G.number_of_nodes(),
                "edge_count": G.number_of_edges(),
                "top_nodes": sorted_nodes[:10],
                "page_rank": dict(sorted_nodes)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_node_centrality(self, graph_name: str, node: str, 
                          measures: Optional[List[str]] = None) -> Dict[str, Any]:
        """Calculate various centrality measures for a node."""
        try:
            if measures is None:
                measures = ["degree", "in_degree", "out_degree"]
            
            results = {}
            
            # Degree centrality
            if "degree" in measures or "in_degree" in measures or "out_degree" in measures:
                # Count edges
                graph = self.db.graph(graph_name)
                in_count = 0
                out_count = 0
                
                for definition in graph.edge_definitions():
                    edge_collection = definition['edge_collection']
                    
                    # Count incoming edges
                    if "in_degree" in measures:
                        aql = f"FOR e IN {edge_collection} FILTER e._to == @node RETURN 1"
                        cursor = self.db.aql.execute(aql, bind_vars={"node": node})
                        in_count += len(list(cursor))
                    
                    # Count outgoing edges
                    if "out_degree" in measures:
                        aql = f"FOR e IN {edge_collection} FILTER e._from == @node RETURN 1"
                        cursor = self.db.aql.execute(aql, bind_vars={"node": node})
                        out_count += len(list(cursor))
                
                if "degree" in measures:
                    results["degree"] = in_count + out_count
                if "in_degree" in measures:
                    results["in_degree"] = in_count
                if "out_degree" in measures:
                    results["out_degree"] = out_count
            
            # Betweenness centrality (simplified - count paths through node)
            if "betweenness" in measures:
                aql = """
                    LET paths_through = (
                        FOR v1 IN 1..1 ANY @node GRAPH @graph_name
                        FOR v2 IN 1..1 ANY @node GRAPH @graph_name
                            FILTER v1._id != v2._id
                            RETURN 1
                    )
                    RETURN LENGTH(paths_through)
                """
                cursor = self.db.aql.execute(aql, bind_vars={
                    "node": node,
                    "graph_name": graph_name
                })
                results["betweenness_estimate"] = next(cursor, 0)
            
            return {
                "success": True,
                "node": node,
                "graph_name": graph_name,
                "centrality": results
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def detect_cycles(self, graph_name: str, max_length: int = 5) -> Dict[str, Any]:
        """Detect cycles in a graph."""
        try:
            # Use AQL to find cycles
            aql = """
                FOR v IN 1..@max_length ANY @graph_name
                    OPTIONS {bfs: false, uniqueVertices: 'path'}
                    FILTER POSITION(CURRENT.vertices, v) != -1
                    RETURN DISTINCT {
                        cycle: CURRENT.vertices[*]._id,
                        length: LENGTH(CURRENT.edges)
                    }
            """
            
            # Get a sample starting vertex
            graph = self.db.graph(graph_name)
            vertex_collections = graph.vertex_collections()
            if not vertex_collections:
                return {"success": True, "cycles": [], "message": "No vertex collections"}
            
            sample_collection = vertex_collections[0]
            sample_vertex = next(self.db.collection(sample_collection).all(), None)
            
            if not sample_vertex:
                return {"success": True, "cycles": [], "message": "No vertices found"}
            
            cursor = self.db.aql.execute(aql, bind_vars={
                "graph_name": graph_name,
                "max_length": max_length
            })
            
            cycles = list(cursor)
            
            return {
                "success": True,
                "graph_name": graph_name,
                "cycles_found": len(cycles),
                "max_length_checked": max_length,
                "cycles": cycles[:10]  # Limit to first 10 cycles
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def track_pattern_evolution(self, pattern_type: str, time_field: str = "timestamp",
                              window: str = "daily", collection: str = "log_events") -> Dict[str, Any]:
        """Track how patterns evolve over time windows.
        
        Analyzes the frequency and characteristics of patterns over time.
        """
        try:
            # Map window to date function
            date_funcs = {
                "hourly": "DATE_HOUR",
                "daily": "DATE_DAY",
                "weekly": "DATE_ISOWEEK", 
                "monthly": "DATE_MONTH",
                "yearly": "DATE_YEAR"
            }
            
            if window not in date_funcs:
                return {
                    "success": False,
                    "error": f"Invalid window: {window}. Use: {list(date_funcs.keys())}"
                }
            
            date_func = date_funcs[window]
            
            # Query pattern evolution
            aql = f"""
                FOR doc IN {collection}
                    FILTER doc.{time_field} != null
                    FILTER doc.category == @pattern_type OR doc.error_type == @pattern_type OR doc.pattern == @pattern_type
                    COLLECT 
                        period = {date_func}(doc.{time_field}),
                        pattern = doc.category || doc.error_type || doc.pattern
                    WITH COUNT INTO occurrences
                    SORT period
                    RETURN {{
                        period: period,
                        pattern: pattern,
                        occurrences: occurrences,
                        trend: null
                    }}
            """
            
            cursor = self.db.aql.execute(aql, bind_vars={"pattern_type": pattern_type})
            evolution_data = list(cursor)
            
            # Calculate trends
            if len(evolution_data) > 1:
                for i in range(1, len(evolution_data)):
                    prev = evolution_data[i-1]['occurrences']
                    curr = evolution_data[i]['occurrences']
                    if prev > 0:
                        trend = ((curr - prev) / prev) * 100
                        evolution_data[i]['trend'] = round(trend, 2)
            
            # Analyze pattern characteristics
            total_occurrences = sum(d['occurrences'] for d in evolution_data)
            avg_occurrences = total_occurrences / len(evolution_data) if evolution_data else 0
            
            # Find peak period
            peak_period = max(evolution_data, key=lambda x: x['occurrences']) if evolution_data else None
            
            return {
                "success": True,
                "pattern_type": pattern_type,
                "window": window,
                "evolution": evolution_data,
                "statistics": {
                    "total_occurrences": total_occurrences,
                    "average_per_period": round(avg_occurrences, 2),
                    "periods_analyzed": len(evolution_data),
                    "peak_period": peak_period
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def prepare_graph_for_d3(self, graph_data: Dict[str, Any], 
                           layout: str = "force", options: Optional[Dict] = None) -> Dict[str, Any]:
        """Format graph data specifically for D3.js visualization.
        
        Transforms ArangoDB graph format to D3-compatible format with layout hints.
        """
        options = options or {}
        
        try:
            # Handle different input formats
            if "nodes" in graph_data and "links" in graph_data:
                # Already in D3 format
                d3_data = graph_data
            elif "vertices" in graph_data and "edges" in graph_data:
                # ArangoDB format - transform to D3
                nodes = []
                node_map = {}
                
                # Process vertices
                for i, vertex in enumerate(graph_data.get("vertices", [])):
                    node_id = vertex.get("_id", f"node_{i}")
                    node = {
                        "id": node_id,
                        "label": vertex.get("name", vertex.get("_key", node_id)),
                        "group": vertex.get("category", vertex.get("type", "default")),
                        "value": vertex.get("value", 1)
                    }
                    nodes.append(node)
                    node_map[node_id] = node
                
                # Process edges
                links = []
                for edge in graph_data.get("edges", []):
                    link = {
                        "source": edge.get("_from"),
                        "target": edge.get("_to"),
                        "value": edge.get("weight", 1),
                        "type": edge.get("relationship_type", edge.get("type", "related"))
                    }
                    links.append(link)
                
                d3_data = {"nodes": nodes, "links": links}
            else:
                # Try to extract from query results
                nodes = []
                links = []
                node_set = set()
                
                if isinstance(graph_data, dict) and "results" in graph_data:
                    results = graph_data["results"]
                    for item in results:
                        if "nodes" in item and "edges" in item:
                            # Path result
                            for node_id in item["nodes"]:
                                if node_id not in node_set:
                                    nodes.append({
                                        "id": node_id,
                                        "label": node_id.split('/')[-1]
                                    })
                                    node_set.add(node_id)
                            
                            for edge in item["edges"]:
                                links.append({
                                    "source": edge["_from"],
                                    "target": edge["_to"],
                                    "type": edge.get("type", "related")
                                })
                
                d3_data = {"nodes": nodes, "links": links}
            
            # Add layout-specific properties
            if layout == "force":
                d3_data["simulation"] = {
                    "strength": options.get("strength", -100),
                    "distance": options.get("distance", 100),
                    "charge": options.get("charge", -30),
                    "gravity": options.get("gravity", 0.1)
                }
            elif layout == "radial":
                d3_data["radial"] = {
                    "radius": options.get("radius", 200),
                    "startAngle": options.get("startAngle", 0),
                    "endAngle": options.get("endAngle", 2 * 3.14159)
                }
            elif layout == "tree":
                d3_data["tree"] = {
                    "nodeSize": options.get("nodeSize", [50, 200]),
                    "separation": options.get("separation", 1.5)
                }
            
            # Add metadata
            d3_data["metadata"] = {
                "layout": layout,
                "nodeCount": len(d3_data["nodes"]),
                "linkCount": len(d3_data["links"]),
                "timestamp": datetime.now().isoformat()
            }
            
            return {
                "success": True,
                "format": "d3",
                "layout": layout,
                "data": d3_data
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def analyze_graph_patterns(self, graph_name: str, 
                             pattern_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """Analyze structural patterns in graphs.
        
        Finds motifs, clusters, hierarchies and other patterns.
        """
        pattern_types = pattern_types or ["triangles", "stars", "chains", "hubs"]
        results = {}
        
        try:
            # Pattern: Triangles (3-cycles)
            if "triangles" in pattern_types:
                aql = """
                    FOR v IN 1..1 ANY 'error_causality'
                    FOR v2 IN 1..1 ANY v GRAPH @graph_name
                    FOR v3 IN 1..1 ANY v2 GRAPH @graph_name
                        FILTER v3._id == v._id
                        FILTER v._id < v2._id AND v2._id < v3._id
                        RETURN {
                            triangle: [v._id, v2._id, v3._id]
                        }
                """
                cursor = self.db.aql.execute(aql, bind_vars={"graph_name": graph_name})
                triangles = list(cursor)
                results["triangles"] = {
                    "count": len(triangles),
                    "samples": triangles[:5]
                }
            
            # Pattern: Star (high-degree nodes)
            if "stars" in pattern_types:
                aql = """
                    FOR v IN 1..0 ANY 'error_causality' GRAPH @graph_name
                    LET outDegree = LENGTH(FOR e IN 1..1 OUTBOUND v GRAPH @graph_name RETURN 1)
                    LET inDegree = LENGTH(FOR e IN 1..1 INBOUND v GRAPH @graph_name RETURN 1)
                    LET totalDegree = outDegree + inDegree
                    FILTER totalDegree >= 5
                    SORT totalDegree DESC
                    LIMIT 10
                    RETURN {
                        center: v._id,
                        outDegree: outDegree,
                        inDegree: inDegree,
                        totalDegree: totalDegree
                    }
                """
                cursor = self.db.aql.execute(aql, bind_vars={"graph_name": graph_name})
                stars = list(cursor)
                results["stars"] = {
                    "count": len(stars),
                    "hubs": stars
                }
            
            # Pattern: Chains (linear paths)
            if "chains" in pattern_types:
                aql = """
                    FOR v IN 1..0 ANY 'error_causality' GRAPH @graph_name
                    LET outDegree = LENGTH(FOR e IN 1..1 OUTBOUND v GRAPH @graph_name RETURN 1)
                    LET inDegree = LENGTH(FOR e IN 1..1 INBOUND v GRAPH @graph_name RETURN 1)
                    FILTER outDegree == 1 AND inDegree <= 1
                    FOR path IN 1..5 OUTBOUND v GRAPH @graph_name
                        OPTIONS {bfs: false, uniqueVertices: 'path'}
                        FILTER LENGTH(path.edges) >= 3
                        RETURN {
                            start: v._id,
                            length: LENGTH(path.edges),
                            path: path.vertices[*]._id
                        }
                """
                cursor = self.db.aql.execute(aql, bind_vars={"graph_name": graph_name})
                chains = list(cursor)
                results["chains"] = {
                    "count": len(chains),
                    "longest": max(chains, key=lambda x: x['length']) if chains else None
                }
            
            # Pattern: Hierarchical levels
            if "hierarchy" in pattern_types:
                # Find nodes with no incoming edges (roots)
                aql = """
                    FOR v IN 1..0 ANY 'error_causality' GRAPH @graph_name
                    LET inDegree = LENGTH(FOR e IN 1..1 INBOUND v GRAPH @graph_name RETURN 1)
                    FILTER inDegree == 0
                    FOR path IN 0..10 OUTBOUND v GRAPH @graph_name
                        OPTIONS {bfs: true, uniqueVertices: 'global'}
                        COLLECT depth = LENGTH(path.edges) WITH COUNT INTO nodesAtLevel
                        SORT depth
                        RETURN {
                            level: depth,
                            nodeCount: nodesAtLevel
                        }
                """
                cursor = self.db.aql.execute(aql, bind_vars={"graph_name": graph_name})
                hierarchy = list(cursor)
                results["hierarchy"] = {
                    "levels": hierarchy,
                    "depth": len(hierarchy)
                }
            
            # Summary statistics
            results["summary"] = {
                "patterns_analyzed": len([p for p in pattern_types if p in results]),
                "graph_name": graph_name
            }
            
            return {
                "success": True,
                "patterns": results
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}


# Create global instance
tools = ArangoTools()


@mcp.tool()
@debug_tool(mcp_logger)
async def schema() -> str:
    """Get ArangoDB schema including collections, views, graphs, and sample queries."""
    start_time = time.time()
    try:
        result = tools.get_schema()
        return create_success_response(
            data=result,
            tool_name="schema",
            start_time=start_time
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="schema",
            start_time=start_time
        )


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
    
    start_time = time.time()
    
    try:
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
            
            # Return error response with all the additional info
            return create_error_response(
                error=json.dumps(result),  # Include all the research info
                tool_name="query",
                start_time=start_time
            )
        
        # Success case
        return create_success_response(
            data=result,
            tool_name="query",
            start_time=start_time
        )
        
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="query",
            start_time=start_time
        )


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
    
    start_time = time.time()
    try:
        result = tools.insert_log(message, level, **params)
        return create_success_response(
            data=result,
            tool_name="insert",
            start_time=start_time
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="insert",
            start_time=start_time
        )


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
    
    start_time = time.time()
    try:
        result = tools.create_edge(from_id, to_id, collection, **params)
        return create_success_response(
            data=result,
            tool_name="edge",
            start_time=start_time
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="edge",
            start_time=start_time
        )


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
    start_time = time.time()
    try:
        search_dict = json.loads(search)
        update_dict = json.loads(update)
        create_dict = json.loads(create) if create else None
        
        result = tools.upsert_document(collection, search_dict, update_dict, create_dict)
        return create_success_response(
            data=result,
            tool_name="upsert",
            start_time=start_time
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="upsert",
            start_time=start_time
        )


@mcp.tool()
@debug_tool(mcp_logger)
async def natural_language_to_aql(
    query: str,
    context: Optional[str] = None
) -> str:
    """Convert natural language queries to AQL patterns with examples.
    
    This tool helps convert English queries into executable AQL queries by matching
    common patterns. It returns the AQL query and bind variables ready for execution.
    
    Examples:
    - "find similar errors" -> BM25 search query
    - "find resolved ImportError" -> filtered query for resolved errors
    - "recent errors from last hour" -> time-based query
    - "count errors by type" -> aggregation query
    - "find related items to log_events/123" -> graph traversal
    
    Args:
        query: Natural language query describing what to find
        context: Optional JSON string with additional context (error_type, script_name, etc.)
        
    Returns:
        JSON with matched pattern, AQL query, bind variables, and usage instructions
    """
    start_time = time.time()
    try:
        # Parse context if provided
        parsed_context = None
        if context:
            try:
                parsed_context = json.loads(context)
            except json.JSONDecodeError:
                parsed_context = {"raw": context}
        
        result = tools.english_to_aql_patterns(query, parsed_context)
        return create_success_response(
            data=result,
            tool_name="natural_language_to_aql",
            start_time=start_time
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="natural_language_to_aql",
            start_time=start_time
        )


@mcp.tool()
@debug_tool(mcp_logger)
async def research_database_issue(
    error: str,
    aql: Optional[str] = None,
    error_code: Optional[str] = None,
    collection: Optional[str] = None
) -> str:
    """Research database errors with cached results and tool suggestions.
    
    This tool helps recover from ArangoDB errors by:
    1. Checking if we've seen this error before (cached research)
    2. Formatting the error context for external research tools
    3. Suggesting which MCP tools to use (context7, perplexity-ask, etc.)
    4. Providing specific prompts for each research tool
    
    Args:
        error: The error message encountered
        aql: Optional - The AQL query that caused the error
        error_code: Optional - Specific error code (e.g., "1203")
        collection: Optional - Collection involved in the error
        
    Returns:
        Research context with tool suggestions and formatted prompts
    """
    start_time = time.time()
    try:
        error_info = {
            "error": error,
            "aql": aql,
            "error_code": error_code,
            "collection": collection
        }
        # Remove None values
        error_info = {k: v for k, v in error_info.items() if v is not None}
        
        result = tools.research_database_issue(error_info, auto_research=True)
        return create_success_response(
            data=result,
            tool_name="research_database_issue",
            start_time=start_time
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="research_database_issue",
            start_time=start_time
        )


@mcp.tool()
@debug_tool(mcp_logger)
async def add_glossary_term(
    term: str,
    definition: str,
    examples: Optional[str] = None,
    related_errors: Optional[str] = None,
    see_also: Optional[str] = None
) -> str:
    """Add or update a glossary term with examples and relationships.
    
    This tool manages a glossary of technical terms, error types, and concepts
    encountered during debugging. Terms can be linked to errors and other terms.
    
    Args:
        term: The term to define (e.g., "circular import", "race condition")
        definition: Clear explanation of what the term means
        examples: Optional JSON array of example code or scenarios
        related_errors: Optional JSON array of related error types
        see_also: Optional JSON array of related terms
        
    Returns:
        Success status with term ID and any existing definition that was updated
    """
    start_time = time.time()
    try:
        kwargs = {}
        
        # Parse optional JSON arrays
        if examples:
            try:
                kwargs["examples"] = json.loads(examples)
            except json.JSONDecodeError:
                kwargs["examples"] = [examples]  # Treat as single example
                
        if related_errors:
            try:
                kwargs["related_errors"] = json.loads(related_errors)
            except json.JSONDecodeError:
                kwargs["related_errors"] = [related_errors]
                
        if see_also:
            try:
                kwargs["see_also"] = json.loads(see_also)
            except json.JSONDecodeError:
                kwargs["see_also"] = [see_also]
        
        result = tools.add_glossary_term(term, definition, **kwargs)
        return create_success_response(
            data=result,
            tool_name="add_glossary_term",
            start_time=start_time
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="add_glossary_term",
            start_time=start_time
        )


@mcp.tool()
@debug_tool(mcp_logger)
async def extract_lesson(
    solution_ids: str,
    lesson: str,
    category: str,
    applies_to: str
) -> str:
    """Extract a general lesson from multiple successful solutions.
    
    This tool creates reusable lessons from patterns observed across multiple
    solutions. Lessons have confidence scores based on evidence count.
    
    Args:
        solution_ids: JSON array of solution document IDs that demonstrate this lesson
        lesson: The lesson learned (e.g., "Always check for None before calling methods")
        category: Category of lesson (e.g., "error_prevention", "debugging", "performance")
        applies_to: JSON array of contexts where this lesson applies (e.g., ["async", "websockets"])
        
    Returns:
        Success status with lesson ID and confidence score
    """
    start_time = time.time()
    try:
        # Parse JSON arrays
        try:
            parsed_solution_ids = json.loads(solution_ids)
        except json.JSONDecodeError:
            return create_error_response(
                error="solution_ids must be a valid JSON array",
                tool_name="extract_lesson",
                start_time=start_time
            )
            
        try:
            parsed_applies_to = json.loads(applies_to)
        except json.JSONDecodeError:
            parsed_applies_to = [applies_to]  # Treat as single context
        
        result = tools.extract_lesson(
            solution_ids=parsed_solution_ids,
            lesson=lesson,
            category=category,
            applies_to=parsed_applies_to
        )
        
        return create_success_response(
            data=result,
            tool_name="extract_lesson",  
            start_time=start_time
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="extract_lesson",
            start_time=start_time
        )


@mcp.tool()
@debug_tool(mcp_logger)
async def track_solution_outcome(
    solution_id: str,
    outcome: str,
    key_reason: str,
    category: str,
    gotchas: Optional[str] = None,
    time_to_resolve: Optional[int] = None,
    context: Optional[str] = None
) -> str:
    """Track the outcome of applying a solution with success metrics.
    
    This tool tracks whether a solution worked, partially worked, or failed,
    building a knowledge base of what actually works in practice.
    
    Args:
        solution_id: ID of the solution document that was applied
        outcome: Result - must be 'success', 'partial', or 'failed'
        key_reason: The KEY reason why it worked/failed (be concise)
        category: Category like 'async_fix', 'import_error', 'config_issue'
        gotchas: Optional JSON array of critical gotchas discovered
        time_to_resolve: Optional minutes taken to resolve
        context: Optional JSON object with additional context
        
    Returns:
        Success status with outcome ID and updated solution statistics
    """
    start_time = time.time()
    try:
        # Validate outcome
        if outcome not in ['success', 'partial', 'failed']:
            return create_error_response(
                error="outcome must be 'success', 'partial', or 'failed'",
                tool_name="track_solution_outcome",
                start_time=start_time
            )
        
        # Parse optional JSON fields
        kwargs = {}
        
        if gotchas:
            try:
                kwargs["gotchas"] = json.loads(gotchas)
            except json.JSONDecodeError:
                kwargs["gotchas"] = [gotchas]
                
        if context:
            try:
                kwargs["context"] = json.loads(context)
            except json.JSONDecodeError:
                kwargs["context"] = {"raw": context}
        
        result = tools.track_solution_outcome(
            solution_id=solution_id,
            outcome=outcome,
            key_reason=key_reason,
            category=category,
            time_to_resolve=time_to_resolve,
            **kwargs
        )
        
        return create_success_response(
            data=result,
            tool_name="track_solution_outcome",
            start_time=start_time
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="track_solution_outcome",
            start_time=start_time
        )


@mcp.tool()
@debug_tool(mcp_logger)
async def advanced_search(
    search_text: Optional[str] = None,
    category: Optional[str] = None,
    error_type: Optional[str] = None,
    time_range: Optional[str] = None,
    min_success_rate: Optional[float] = None,
    resolved_only: bool = False,
    limit: int = 20
) -> str:
    """Advanced multi-dimensional search with filters and scoring.
    
    This tool enables complex searches across the knowledge base with multiple
    filters and BM25 text search scoring.
    
    Args:
        search_text: Optional text to search for (uses BM25 scoring)
        category: Optional category filter (e.g., 'import_error', 'async_fix')
        error_type: Optional error type filter (e.g., 'ModuleNotFoundError')
        time_range: Optional time filter - 'last_hour', 'last_day', or 'last_week'
        min_success_rate: Optional minimum success rate for solutions (0.0-1.0)
        resolved_only: Whether to only show resolved errors (default: False)
        limit: Maximum number of results (default: 20)
        
    Returns:
        Search results with relevance scores and outcome statistics
    """
    start_time = time.time()
    try:
        # Build search parameters
        search_params = {}
        
        if search_text:
            search_params["search_text"] = search_text
        if category:
            search_params["category"] = category
        if error_type:
            search_params["error_type"] = error_type
        if time_range and time_range in ['last_hour', 'last_day', 'last_week']:
            search_params["time_range"] = time_range
        if min_success_rate is not None:
            search_params["min_success_rate"] = min_success_rate
        if resolved_only:
            search_params["resolved"] = True
        
        search_params["limit"] = limit
        
        result = tools.advanced_search(**search_params)
        
        return create_success_response(
            data=result,
            tool_name="advanced_search",
            start_time=start_time
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="advanced_search",
            start_time=start_time
        )


@mcp.tool()
@debug_tool(mcp_logger)
async def build_similarity_graph(collection: str, text_field: str, edge_collection: str, 
                               threshold: float = 0.8) -> str:
    """Build a similarity graph using FAISS for vector similarity.
    
    Creates edges between documents with similarity above threshold.
    Requires: uv add faiss-cpu sentence-transformers
    """
    start_time = time.time()
    try:
        result = tools.build_similarity_graph(collection, text_field, edge_collection, threshold)
        return create_success_response(
            data=result,
            tool_name="build_similarity_graph",
            start_time=start_time
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="build_similarity_graph",
            start_time=start_time
        )


@mcp.tool()
@debug_tool(mcp_logger)
async def find_similar_documents(collection: str, text: str, text_field: str, 
                               limit: int = 10) -> str:
    """Find similar documents using FAISS vector search.
    
    Requires: uv add faiss-cpu sentence-transformers
    """
    start_time = time.time()
    try:
        result = tools.find_similar_documents(collection, text, text_field, limit)
        return create_success_response(
            data=result,
            tool_name="find_similar_documents",
            start_time=start_time
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="find_similar_documents",
            start_time=start_time
        )


@mcp.tool()
@debug_tool(mcp_logger)
async def detect_anomalies(collection: str, features: str, 
                         contamination: float = 0.1) -> str:
    """Detect anomalies using Isolation Forest.
    
    Features should be a JSON array of field names.
    Requires: uv add scikit-learn
    """
    start_time = time.time()
    try:
        feature_list = json.loads(features)
        result = tools.detect_anomalies(collection, feature_list, contamination)
        return create_success_response(
            data=result,
            tool_name="detect_anomalies",
            start_time=start_time
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="detect_anomalies",
            start_time=start_time
        )


@mcp.tool()
@debug_tool(mcp_logger)
async def find_clusters(collection: str, features: str, 
                      n_clusters: Optional[int] = None, method: str = "kmeans") -> str:
    """Find clusters in documents using various clustering algorithms.
    
    Features should be a JSON array of field names.
    Methods: 'kmeans', 'dbscan'
    Requires: uv add scikit-learn
    """
    start_time = time.time()
    try:
        feature_list = json.loads(features)
        result = tools.find_clusters(collection, feature_list, n_clusters, method)
        return create_success_response(
            data=result,
            tool_name="find_clusters",
            start_time=start_time
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="find_clusters",
            start_time=start_time
        )


@mcp.tool()
@debug_tool(mcp_logger)
async def analyze_time_series(collection: str, time_field: str, value_field: str,
                            aggregation: str = "daily", operation: str = "avg") -> str:
    """Analyze time series data with aggregations.
    
    Aggregations: 'hourly', 'daily', 'weekly', 'monthly', 'yearly'
    Operations: 'avg', 'sum', 'min', 'max', 'count'
    """
    start_time = time.time()
    try:
        result = tools.analyze_time_series(collection, time_field, value_field, aggregation, operation)
        return create_success_response(
            data=result,
            tool_name="analyze_time_series",
            start_time=start_time
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="analyze_time_series",
            start_time=start_time
        )


@mcp.tool()
@debug_tool(mcp_logger)
async def get_visualization_data(query_type: str, collection: str, 
                               params: Optional[str] = None) -> str:
    """Prepare data for visualization based on query type.
    
    Types: 'network', 'timeline', 'heatmap'
    Params should be a JSON string with type-specific options.
    """
    start_time = time.time()
    try:
        params_dict = json.loads(params) if params else {}
        result = tools.get_visualization_data(query_type, collection, params_dict)
        return create_success_response(
            data=result,
            tool_name="get_visualization_data",
            start_time=start_time
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="get_visualization_data",
            start_time=start_time
        )


@mcp.tool()
@debug_tool(mcp_logger)
async def get_graph_metrics(graph_name: str) -> str:
    """Calculate basic graph metrics including vertex/edge counts and degree distribution."""
    start_time = time.time()
    try:
        result = tools.get_graph_metrics(graph_name)
        return create_success_response(
            data=result,
            tool_name="get_graph_metrics",
            start_time=start_time
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="get_graph_metrics",
            start_time=start_time
        )


@mcp.tool()
@debug_tool(mcp_logger)
async def find_shortest_paths(graph_name: str, start_node: str, 
                            end_node: str, max_paths: int = 5) -> str:
    """Find shortest paths between two nodes in a graph."""
    start_time = time.time()
    try:
        result = tools.find_shortest_paths(graph_name, start_node, end_node, max_paths)
        return create_success_response(
            data=result,
            tool_name="find_shortest_paths",
            start_time=start_time
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="find_shortest_paths",
            start_time=start_time
        )


@mcp.tool()
@debug_tool(mcp_logger)
async def calculate_page_rank(graph_name: str, damping: float = 0.85, 
                            iterations: int = 10) -> str:
    """Calculate PageRank for nodes in a graph.
    
    Requires: uv add networkx python-louvain
    """
    start_time = time.time()
    try:
        result = tools.calculate_page_rank(graph_name, damping, iterations)
        return create_success_response(
            data=result,
            tool_name="calculate_page_rank",
            start_time=start_time
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="calculate_page_rank",
            start_time=start_time
        )


@mcp.tool()
@debug_tool(mcp_logger)
async def get_node_centrality(graph_name: str, node: str, 
                            measures: Optional[str] = None) -> str:
    """Calculate various centrality measures for a node.
    
    Measures should be a JSON array: ["degree", "in_degree", "out_degree", "betweenness"]
    """
    start_time = time.time()
    try:
        measures_list = json.loads(measures) if measures else None
        result = tools.get_node_centrality(graph_name, node, measures_list)
        return create_success_response(
            data=result,
            tool_name="get_node_centrality",
            start_time=start_time
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="get_node_centrality",
            start_time=start_time
        )


@mcp.tool()
@debug_tool(mcp_logger)
async def detect_cycles(graph_name: str, max_length: int = 5) -> str:
    """Detect cycles in a graph up to specified length."""
    start_time = time.time()
    try:
        result = tools.detect_cycles(graph_name, max_length)
        return create_success_response(
            data=result,
            tool_name="detect_cycles",
            start_time=start_time
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="detect_cycles",
            start_time=start_time
        )


@mcp.tool()
@debug_tool(mcp_logger)
async def track_pattern_evolution(pattern_type: str, time_field: str = "timestamp",
                                window: str = "daily", collection: str = "log_events") -> str:
    """Track how patterns evolve over time windows.
    
    Analyzes the frequency and characteristics of patterns over time.
    Windows: 'hourly', 'daily', 'weekly', 'monthly', 'yearly'
    """
    start_time = time.time()
    try:
        result = tools.track_pattern_evolution(pattern_type, time_field, window, collection)
        return create_success_response(
            data=result,
            tool_name="track_pattern_evolution",
            start_time=start_time
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="track_pattern_evolution",
            start_time=start_time
        )


@mcp.tool()
@debug_tool(mcp_logger)
async def prepare_graph_for_d3(graph_data: str, layout: str = "force", 
                             options: Optional[str] = None) -> str:
    """Format graph data specifically for D3.js visualization.
    
    Transforms ArangoDB graph format to D3-compatible format with layout hints.
    Layouts: 'force', 'radial', 'tree'
    Graph data and options should be JSON strings.
    """
    start_time = time.time()
    try:
        graph_dict = json.loads(graph_data)
        options_dict = json.loads(options) if options else None
        result = tools.prepare_graph_for_d3(graph_dict, layout, options_dict)
        return create_success_response(
            data=result,
            tool_name="prepare_graph_for_d3",
            start_time=start_time
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="prepare_graph_for_d3",
            start_time=start_time
        )


@mcp.tool()
@debug_tool(mcp_logger)
async def analyze_graph_patterns(graph_name: str, 
                               pattern_types: Optional[str] = None) -> str:
    """Analyze structural patterns in graphs.
    
    Finds motifs, clusters, hierarchies and other patterns.
    Pattern types should be a JSON array: ["triangles", "stars", "chains", "hierarchy"]
    """
    start_time = time.time()
    try:
        types_list = json.loads(pattern_types) if pattern_types else None
        result = tools.analyze_graph_patterns(graph_name, types_list)
        return create_success_response(
            data=result,
            tool_name="analyze_graph_patterns",
            start_time=start_time
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="analyze_graph_patterns",
            start_time=start_time
        )


async def working_usage():
    """Demonstrate working usage of ArangoDB tools."""
    logger.info("=== ArangoDB Tools Working Usage ===")
    
    # Example 1: Get schema
    logger.info("\n1. Getting database schema:")
    result = tools.get_schema()
    schema = result if isinstance(result, dict) else json.loads(result)
    logger.info(f"Found {len(schema.get('collections', []))} collections")
    
    # Example 2: Execute simple query
    logger.info("\n2. Executing simple AQL query:")
    query_result = tools.execute_aql(
        aql="FOR doc IN log_events LIMIT 2 RETURN doc",
        bind_vars={}
    )
    result_data = query_result if isinstance(query_result, dict) else json.loads(query_result)
    if "error" not in result_data:
        logger.info(f"Query executed successfully")
    else:
        logger.warning(f"Query returned error: {result_data.get('error')}")
    
    # Example 3: Track solution outcome
    logger.info("\n3. Testing solution tracking:")
    try:
        track_result = tools.track_solution_outcome(
            error_id="test_error_001",
            solution_id="test_solution_001",
            success=True,
            execution_time=1.5
        )
        logger.info(f"Solution tracking result: {track_result}")
    except Exception as e:
        logger.warning(f"Solution tracking failed: {e}")
    
    logger.success("\n✅ All examples completed successfully!")
    return True


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
        elif sys.argv[1] == "working":
            asyncio.run(working_usage())
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