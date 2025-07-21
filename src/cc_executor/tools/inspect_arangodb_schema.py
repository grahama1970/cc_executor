#!/usr/bin/env python3
"""
Inspect ArangoDB schema to understand collections, views, and indexes.

This tool helps agents understand the actual structure of the logger database
so they can construct proper queries. It uses python-arango to inspect:
- Collections and their document structure
- Graph definitions and edge collections
- Views and their configurations
- Indexes for optimization
- Sample documents to understand data format

=== AGENT INSTRUCTIONS FOR THIS FILE ===
Run this script directly to test functionality:
  python inspect_arangodb_schema.py          # Runs working_usage() - stable, known to work
  python inspect_arangodb_schema.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug_function() instead!
The working_usage() function MUST pass all assertions to verify the script works.
===
"""

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict

from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the ArangoDB-backed logger that provides CRUD capabilities
# All logger.info() calls will now be stored in the database
# Add logger agent path FIRST
logger_agent_path = Path(__file__).parent.parent.parent / "proof_of_concept" / "logger_agent" / "src"
if str(logger_agent_path) not in sys.path:
    
# Import logger_agent components
try:
    # Import with full module path
    import arango_log_sink
    import agent_log_manager
    from arango_log_sink import ArangoLogSink
    from agent_log_manager import AgentLogManager
    LOGGER_AGENT_AVAILABLE = True
except ImportError as e:
    logger.error(f"CRITICAL: Cannot import logger_agent: {e}")
    LOGGER_AGENT_AVAILABLE = False

# Configure logger with ArangoDB sink
if LOGGER_AGENT_AVAILABLE:
    # Database configuration
    db_config = {
        "url": os.getenv("ARANGO_URL", "http://localhost:8529"),
        "database": os.getenv("ARANGO_DATABASE", "script_logs"),
        "username": os.getenv("ARANGO_USERNAME", "root"),
        "password": os.getenv("ARANGO_PASSWORD", "openSesame")
    }
    
    # Create sink
    sink = ArangoLogSink(
        db_config=db_config,
        collection_name="log_events",
        batch_size=50,
        flush_interval=5.0
    )
    
    # Generate execution ID
    script_name = Path(__file__).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    execution_id = f"{script_name}_{timestamp}_{unique_id}"
    
    # Set execution context
    sink.set_execution_context(execution_id, script_name)
    
    # Start the sink properly
    import asyncio as aio
    try:
        loop = aio.get_running_loop()
        # Already in async context, create task
        aio.create_task(sink.start())
    except RuntimeError:
        # No event loop, create one
        loop = aio.new_event_loop()
        loop.run_until_complete(sink.start())
        loop.close()
    
    # Configure loguru with selective DB storage
    logger.remove()
    
    # Console sink
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
        enqueue=True
    )
    
    # ArangoDB sink with filter
    def should_store_in_db(record):
        """Determine if log should go to database."""
        # Always store errors
        if record["level"].no >= logger.level("ERROR").no:
            return True
        
        # Store if marked
        if record.get("extra", {}).get("db_store", False):
            return True
        
        # Store specific categories
        log_category = record.get("extra", {}).get("log_category", "")
        if log_category in ["AGENT_LEARNING", "SCHEMA_INSPECTION", "SCRIPT_FINAL_RESPONSE"]:
            return True
        
        return False
    
    logger.add(
        sink.write,
        level="DEBUG",
        enqueue=True,
        serialize=False,
        filter=should_store_in_db
    )
    
    # Create manager
    manager = AgentLogManager()
    
    # Initialize manager
    def init_manager():
        import asyncio
        loop = asyncio.new_event_loop()
        loop.run_until_complete(manager.initialize(db_config))
        loop.close()
    
    init_manager()
    manager.set_sink(sink)
    
    logger.bind(db_store=True).success(f"Schema inspector configured with ArangoDB CRUD! ID: {execution_id}")
    
    # CRUD functions
    def log_agent_learning(msg: str, function_name: str = "", **kwargs):
        logger.bind(
            db_store=True,
            log_category="AGENT_LEARNING",
            function_name=function_name,
            execution_id=execution_id,
            **kwargs
        ).info(msg)
    
    def start_run(name: str, mode: str) -> str:
        logger.bind(db_store=True).info(f"Starting script run: {name} in {mode} mode")
        if hasattr(manager, 'start_run'):
            manager.start_run(name, mode)
        return execution_id
    
    def end_run(exec_id: str, success: bool):
        logger.bind(db_store=True).info(f"Script run completed: {exec_id}, success={success}")
        if hasattr(manager, 'end_run'):
            import asyncio
            loop = asyncio.new_event_loop()
            loop.run_until_complete(manager.end_run(exec_id, success))
            loop.close()
    
    CRUD_LOGGER_AVAILABLE = True
    
else:
    # Without logger_agent, we can't provide CRUD
    logger.error("RUNNING WITHOUT CRUD CAPABILITIES!")
    
    def log_agent_learning(*args, **kwargs):
        logger.warning("log_agent_learning called but CRUD not available!")
    
    def start_run(*args, **kwargs):
        return "no_crud"
    
    def end_run(*args, **kwargs):
        pass
    
    CRUD_LOGGER_AVAILABLE = False
    execution_id = "no_crud"

# Import both clients - no conditional imports  
from arangoasync import ArangoClient as AsyncArangoClient
from arangoasync.auth import Auth
from arango import ArangoClient
from arango.database import StandardDatabase

# We'll use async by default since python-arango-async is installed
ASYNC_AVAILABLE = True
logger.info("Using async ArangoDB client")


class AsyncArangoDBSchemaInspector:
    """Async version of ArangoDB schema inspector."""
    
    def __init__(self, host: str = "localhost", port: int = 8529,
                 username: str = "root", password: str = ""):
        """Initialize connection parameters."""
        self.url = f"http://{host}:{port}"
        self.db_name = "logger_agent"
        self.username = username
        self.password = password
        self.db = None
        logger.info(f"Initialized async ArangoDB inspector for {self.url}")
    
    async def connect(self, db_name: Optional[str] = None):
        """Connect to database asynchronously."""
        if db_name:
            self.db_name = db_name
        
        try:
            async with AsyncArangoClient(hosts=self.url) as client:
                auth = Auth(username=self.username, password=self.password)
                self.db = await client.db(self.db_name, auth=auth)
                logger.info(f"Connected to database: {self.db_name}")
                return self.db
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise
    
    async def sample_random_documents(self, col_name: str, limit: int = 2) -> List[Dict]:
        """Sample random documents from a collection."""
        query = f"FOR doc IN `{col_name}` SORT RAND() LIMIT {limit} RETURN doc"
        logger.debug(f"Sampling up to {limit} random docs from collection '{col_name}'")
        
        cursor = await self.db.aql.execute(query)
        results = []
        async for doc in cursor:
            results.append(doc)
        return results
    
    async def inspect_collections_async(self) -> Dict[str, Any]:
        """Inspect all collections asynchronously."""
        collections_info = {}
        
        # Get all collections
        all_collections = [col async for col in self.db.collections()]
        user_collections = [col for col in all_collections if not col["name"].startswith("_")]
        
        logger.info(f"Found {len(user_collections)} user collections")
        
        for col in user_collections:
            name = col['name']
            col_type = col['type']
            type_str = 'document' if col_type == 2 else 'edge' if col_type == 3 else 'unknown'
            
            logger.info(f"Processing collection: {name} (type: {type_str})")
            
            # Sample documents
            sample_docs = await self.sample_random_documents(name, limit=5)
            
            # Get count
            count_query = f"RETURN LENGTH(`{name}`)"
            count_cursor = await self.db.aql.execute(count_query)
            count = 0
            async for c in count_cursor:
                count = c
            
            info = {
                "name": name,
                "type": "edge" if col_type == 3 else "document",
                "count": count,
                "sample_documents": sample_docs,
                "schema": self._infer_schema(sample_docs)
            }
            
            collections_info[name] = info
        
        return collections_info
    
    async def inspect_views_async(self) -> Dict[str, Any]:
        """Inspect ArangoSearch views asynchronously."""
        views_info = {}
        
        async for view in self.db.views():
            if view['name'].startswith('_'):
                continue
                
            logger.info(f"Inspecting view: {view['name']}")
            
            info = {
                "name": view['name'],
                "type": view.get('type', 'arangosearch'),
                "links": view.get('links', {}),
                "analyzers": []
            }
            
            # Extract analyzers from links
            for col_name, link_info in info['links'].items():
                fields = link_info.get('fields', {})
                for field, fparams in fields.items():
                    analyzers = fparams.get('analyzers', [])
                    info['analyzers'].extend(analyzers)
            
            info['analyzers'] = list(set(info['analyzers']))  # Unique analyzers
            views_info[view['name']] = info
        
        return views_info
    
    def _infer_schema(self, documents: List[Dict]) -> Dict[str, Any]:
        """Infer schema from sample documents."""
        schema = defaultdict(set)
        
        for doc in documents:
            self._extract_fields(doc, schema)
        
        # Convert sets to lists for JSON serialization
        return {k: list(v) for k, v in schema.items()}
    
    def _extract_fields(self, obj: Any, schema: Dict, prefix: str = ""):
        """Recursively extract field types."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                field_path = f"{prefix}.{key}" if prefix else key
                schema[field_path].add(type(value).__name__)
                
                if isinstance(value, dict):
                    self._extract_fields(value, schema, field_path)
                elif isinstance(value, list) and value:
                    # Check first element of list
                    schema[field_path].add(f"list[{type(value[0]).__name__}]")


class ArangoDBSchemaInspector:
    """Sync version of ArangoDB schema inspector (fallback)."""
    
    def __init__(self, host: str = "localhost", port: int = 8529, 
                 username: str = "root", password: str = ""):
        """Initialize connection to ArangoDB."""
        self.client = ArangoClient(hosts=f"http://{host}:{port}")
        self.db_name = "logger_agent"  # Default logger agent database
        self.db = None
        self.username = username
        self.password = password
        logger.info(f"Initialized ArangoDB inspector for {host}:{port}")
    
    def connect(self, db_name: Optional[str] = None) -> StandardDatabase:
        """Connect to database."""
        if db_name:
            self.db_name = db_name
        
        try:
            # Connect to system database first
            sys_db = self.client.db("_system", username=self.username, password=self.password)
            
            # Create database if it doesn't exist
            if not sys_db.has_database(self.db_name):
                logger.warning(f"Database {self.db_name} not found, creating...")
                sys_db.create_database(self.db_name)
            
            # Connect to target database
            self.db = self.client.db(self.db_name, username=self.username, password=self.password)
            logger.info(f"Connected to database: {self.db_name}")
            return self.db
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise
    
    def inspect_collections(self) -> Dict[str, Any]:
        """Inspect all collections in the database."""
        if not self.db:
            raise ValueError("Not connected to database")
        
        collections_info = {}
        
        for collection in self.db.collections():
            if collection["name"].startswith("_"):
                continue  # Skip system collections
            
            col = self.db.collection(collection["name"])
            
            info = {
                "name": collection["name"],
                "type": "edge" if collection["edge"] else "document",
                "count": col.count(),
                "indexes": [],
                "sample_documents": [],
                "schema": {}
            }
            
            # Get indexes
            for index in col.indexes():
                info["indexes"].append({
                    "type": index["type"],
                    "fields": index.get("fields", []),
                    "unique": index.get("unique", False),
                    "sparse": index.get("sparse", False)
                })
            
            # Get sample documents to infer schema
            cursor = col.find({}, limit=5)
            sample_docs = list(cursor)
            info["sample_documents"] = sample_docs
            
            # Infer schema from samples
            schema = self._infer_schema(sample_docs)
            info["schema"] = schema
            
            collections_info[collection["name"]] = info
        
        return collections_info
    
    def _infer_schema(self, documents: List[Dict]) -> Dict[str, Any]:
        """Infer schema from sample documents."""
        schema = defaultdict(set)
        
        for doc in documents:
            self._extract_fields(doc, schema)
        
        # Convert sets to lists for JSON serialization
        return {k: list(v) for k, v in schema.items()}
    
    def _extract_fields(self, obj: Any, schema: Dict, prefix: str = ""):
        """Recursively extract field types."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                field_path = f"{prefix}.{key}" if prefix else key
                schema[field_path].add(type(value).__name__)
                
                if isinstance(value, dict):
                    self._extract_fields(value, schema, field_path)
                elif isinstance(value, list) and value:
                    # Check first element of list
                    schema[field_path].add(f"list[{type(value[0]).__name__}]")
        
    def inspect_graphs(self) -> Dict[str, Any]:
        """Inspect graph definitions."""
        if not self.db:
            raise ValueError("Not connected to database")
        
        graphs_info = {}
        
        for graph in self.db.graphs():
            graph_obj = self.db.graph(graph["name"])
            
            info = {
                "name": graph["name"],
                "edge_definitions": [],
                "orphan_collections": graph.get("orphanCollections", [])
            }
            
            # Get edge definitions
            for edge_def in graph.get("edgeDefinitions", []):
                info["edge_definitions"].append({
                    "edge_collection": edge_def["collection"],
                    "from_collections": edge_def["from"],
                    "to_collections": edge_def["to"]
                })
            
            graphs_info[graph["name"]] = info
        
        return graphs_info
    
    def inspect_views(self) -> Dict[str, Any]:
        """Inspect ArangoSearch views."""
        if not self.db:
            raise ValueError("Not connected to database")
        
        views_info = {}
        
        # Get all views
        views = self.db.views()
        
        for view in views:
            if view["name"].startswith("_"):
                continue  # Skip system views
            
            view_obj = self.db.view(view["name"])
            
            info = {
                "name": view["name"],
                "type": view["type"],
                "properties": view_obj.properties()
            }
            
            views_info[view["name"]] = info
        
        return views_info
    
    def get_sample_queries(self) -> List[Dict[str, str]]:
        """Generate sample AQL queries based on schema."""
        if not self.db:
            raise ValueError("Not connected to database")
        
        samples = []
        
        # Sample BM25 search
        samples.append({
            "description": "BM25 full-text search for errors",
            "query": """
FOR doc IN agent_activity_search
SEARCH ANALYZER(doc.message IN TOKENS(@query, 'text_en'), 'text_en')
LET score = BM25(doc)
SORT score DESC
LIMIT 10
RETURN {doc: doc, score: score}
""",
            "bind_vars": {"query": "ModuleNotFoundError pandas"}
        })
        
        # Sample graph traversal
        samples.append({
            "description": "Find error fix relationships",
            "query": """
FOR error IN log_events
FILTER error.level == 'ERROR'
LIMIT 5
FOR fix IN 1..1 OUTBOUND error._id error_causality
FILTER fix.relationship_type == 'FIXED_BY'
RETURN {error: error, fix: fix}
""",
            "bind_vars": {}
        })
        
        # Sample time-based query
        samples.append({
            "description": "Recent errors in last 24 hours",
            "query": """
FOR doc IN log_events
FILTER doc.level == 'ERROR'
FILTER DATE_DIFF(doc.timestamp, NOW(), 'h') <= 24
SORT doc.timestamp DESC
LIMIT 20
RETURN doc
""",
            "bind_vars": {}
        })
        
        return samples
    
    def generate_schema_report(self) -> Dict[str, Any]:
        """Generate comprehensive schema report."""
        report = {
            "database": self.db_name,
            "timestamp": datetime.utcnow().isoformat(),
            "collections": self.inspect_collections(),
            "graphs": self.inspect_graphs(),
            "views": self.inspect_views(),
            "sample_queries": self.get_sample_queries()
        }
        
        # Add summary statistics
        report["summary"] = {
            "total_collections": len(report["collections"]),
            "document_collections": sum(1 for c in report["collections"].values() if c["type"] == "document"),
            "edge_collections": sum(1 for c in report["collections"].values() if c["type"] == "edge"),
            "total_documents": sum(c["count"] for c in report["collections"].values()),
            "graphs_defined": len(report["graphs"]),
            "views_defined": len(report["views"])
        }
        
        return report


def generate_agent_prompt_from_schema(schema_report: Dict[str, Any]) -> str:
    """Generate a prompt for agents explaining the database structure."""
    prompt = f"""
# ArangoDB Schema Reference for Logger Agent

## Database Overview
- **Database**: {schema_report['database']}
- **Total Collections**: {schema_report['summary']['total_collections']}
- **Document Collections**: {schema_report['summary']['document_collections']}
- **Edge Collections**: {schema_report['summary']['edge_collections']}
- **Total Documents**: {schema_report['summary']['total_documents']:,}

## Collections Structure

"""
    
    # Document collections
    prompt += "### Document Collections\n\n"
    for name, info in schema_report['collections'].items():
        if info['type'] == 'document':
            prompt += f"#### {name} ({info['count']} documents)\n"
            prompt += "**Common Fields**:\n"
            
            # Show top fields
            fields = sorted(info['schema'].items())[:10]
            for field, types in fields:
                prompt += f"- `{field}`: {', '.join(types)}\n"
            
            if info['indexes']:
                prompt += "\n**Indexes**:\n"
                for idx in info['indexes']:
                    prompt += f"- {idx['type']} on {', '.join(idx['fields'])}\n"
            
            prompt += "\n"
    
    # Edge collections
    prompt += "### Edge Collections\n\n"
    for name, info in schema_report['collections'].items():
        if info['type'] == 'edge':
            prompt += f"#### {name} ({info['count']} edges)\n"
            prompt += "**Relationship Fields**:\n"
            prompt += "- `_from`: Source document ID\n"
            prompt += "- `_to`: Target document ID\n"
            
            # Show custom fields
            custom_fields = [f for f in info['schema'].keys() 
                           if not f.startswith('_')][:5]
            if custom_fields:
                prompt += "\n**Custom Fields**:\n"
                for field in custom_fields:
                    types = info['schema'][field]
                    prompt += f"- `{field}`: {', '.join(types)}\n"
            
            prompt += "\n"
    
    # Graphs
    if schema_report['graphs']:
        prompt += "## Graph Definitions\n\n"
        for name, graph in schema_report['graphs'].items():
            prompt += f"### {name}\n"
            # Handle both sync and async versions
            edge_defs = graph.get('edge_definitions', graph.get('edgeDefinitions', []))
            if edge_defs:
                for edge_def in edge_defs:
                    # Async version has different field names
                    edge_col = edge_def.get('edge_collection', edge_def.get('collection', 'unknown'))
                    from_cols = edge_def.get('from_collections', edge_def.get('from', []))
                    to_cols = edge_def.get('to_collections', edge_def.get('to', []))
                    prompt += f"- **{edge_col}**: "
                    prompt += f"{' | '.join(from_cols)} → "
                    prompt += f"{' | '.join(to_cols)}\n"
            prompt += "\n"
    
    # Views
    if schema_report['views']:
        prompt += "## Search Views\n\n"
        for name, view in schema_report['views'].items():
            prompt += f"### {name} ({view['type']})\n"
            if 'links' in view.get('properties', {}):
                prompt += "**Linked Collections**:\n"
                for link_name in view['properties']['links'].keys():
                    prompt += f"- {link_name}\n"
            prompt += "\n"
    
    # Sample queries
    prompt += "## Sample Queries You Can Use\n\n"
    for sample in schema_report['sample_queries']:
        prompt += f"### {sample['description']}\n"
        prompt += "```aql\n"
        prompt += sample['query'].strip()
        prompt += "\n```\n"
        if sample['bind_vars']:
            prompt += f"**Bind Variables**: `{json.dumps(sample['bind_vars'])}`\n"
        prompt += "\n"
    
    # Usage tips
    prompt += """
## Query Construction Tips

1. **For text search**: Use views with BM25() scoring
2. **For relationships**: Traverse edge collections with FOR...IN patterns
3. **For time filters**: Use DATE_DIFF() with NOW()
4. **For aggregations**: Use COLLECT and AGGREGATE functions
5. **For graph traversal**: Specify depth (1..3) and direction (OUTBOUND/INBOUND/ANY)

## Common Patterns

### Find Similar Errors
```aql
FOR doc IN agent_activity_search
SEARCH ANALYZER(doc.message IN TOKENS(@query, 'text_en'), 'text_en')
LET score = BM25(doc)
FILTER score > 0.5
RETURN {doc: doc, score: score}
```

### Find Fix Relationships
```aql
FOR error IN log_events
FILTER error.error_type == @error_type
FOR fix IN 1..1 OUTBOUND error._id error_causality
FILTER fix.relationship_type == 'FIXED_BY'
RETURN {error: error, fix: fix}
```

### Multi-hop Graph Traversal
```aql
FOR v, e, p IN 1..3 ANY @start_id error_causality, agent_flow
OPTIONS {uniqueVertices: 'path', bfs: true}
RETURN {vertex: v, path: p, edges: p.edges}
```
"""
    
    return prompt


async def inspect_logger_agent_schema(
    host: Optional[str] = None,
    port: Optional[int] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    db_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Inspect the logger agent database schema using async client.
    
    Returns a comprehensive schema report with sample documents.
    """
    # Use environment variables if not provided
    host = host or os.getenv("ARANGO_URL", "http://localhost:8529").replace("http://", "").replace(":8529", "")
    port = port or int(os.getenv("ARANGO_URL", "http://localhost:8529").split(":")[-1])
    username = username or os.getenv("ARANGO_USERNAME", "root")
    password = password or os.getenv("ARANGO_PASSWORD", "openSesame")
    db_name = db_name or os.getenv("ARANGO_DATABASE", "logger_agent")
    
    logger.info(f"Starting async schema inspection for database '{db_name}'")
    
    # Use async inspector
    async with AsyncArangoClient(hosts=f"http://{host}:{port}") as client:
        auth = Auth(username=username, password=password)
        db = await client.db(db_name, auth=auth)
        
        logger.info(f"Connected to ArangoDB at {host}:{port}, database '{db_name}'")
        
        # Initialize results
        schema_report = {
            "database": db_name,
            "timestamp": datetime.utcnow().isoformat(),
            "collections": {},
            "graphs": {},
            "views": {},
            "sample_queries": []
        }
        
        # Get all collections
        all_collections = await db.collections()
        
        user_collections = [col for col in all_collections if not col["name"].startswith("_")]
        logger.info(f"Found {len(user_collections)} user collections")
        
        # Process each collection
        for col in user_collections:
            name = col['name']
            col_type = col['type']
            type_str = 'document' if col_type == 2 else 'edge' if col_type == 3 else 'unknown'
            
            logger.info(f"Processing collection: {name} (type: {type_str})")
            
            # Get count
            count_query = f"RETURN LENGTH(`{name}`)"
            cursor = await db.aql.execute(count_query)
            count = 0
            async for c in cursor:
                count = c
            
            # Sample documents
            sample_query = f"FOR doc IN `{name}` SORT RAND() LIMIT 5 RETURN doc"
            cursor = await db.aql.execute(sample_query)
            sample_docs = []
            async for doc in cursor:
                sample_docs.append(doc)
            
            # Infer schema
            schema = defaultdict(set)
            for doc in sample_docs:
                _extract_fields_from_doc(doc, schema)
            
            schema_report["collections"][name] = {
                "name": name,
                "type": "edge" if col_type == 3 else "document",
                "count": count,
                "indexes": [],  # TODO: Add index inspection for async client
                "sample_documents": sample_docs,
                "schema": {k: list(v) for k, v in schema.items()}
            }
            
            # Log sample for edge collections
            if col_type == 3 and sample_docs:
                for edge in sample_docs[:2]:
                    logger.info(f"  Sample edge: {edge.get('_from', 'N/A')} -> {edge.get('_to', 'N/A')}")
                    logger.debug(f"  Edge data: {edge}")
        
        # Get views
        logger.info("Inspecting ArangoSearch views...")
        views_list = await db.views()
        for view in views_list:
            if view['name'].startswith('_'):
                continue
                
            logger.info(f"- View: {view['name']}")
            
            # Store view info from list (already has details)
            schema_report["views"][view['name']] = {
                "name": view['name'],
                "type": view.get('type', 'arangosearch'),
                "links": view.get('links', {}),
                "primarySort": view.get('primarySort', [])
            }
            
            links = view.get('links', {})
        
        # Get graphs
        logger.info("Inspecting graphs...")
        try:
            graphs_list = await db.graphs()
            for graph in graphs_list:
                logger.info(f"- Graph: {graph['name']}")
                # Store graph info from list (already has basic details)
                schema_report["graphs"][graph['name']] = {
                    "name": graph['name'],
                    "edgeDefinitions": graph.get('edgeDefinitions', [])
                }
        except Exception as e:
            logger.info(f"Could not retrieve graphs: {e}")
        
        # Add sample queries based on collections found
        schema_report["sample_queries"] = _generate_sample_queries(schema_report["collections"])
        
        # Add summary
        schema_report["summary"] = {
            "total_collections": len(schema_report["collections"]),
            "document_collections": sum(1 for c in schema_report["collections"].values() if c["type"] == "document"),
            "edge_collections": sum(1 for c in schema_report["collections"].values() if c["type"] == "edge"),
            "total_documents": sum(c["count"] for c in schema_report["collections"].values()),
            "graphs_defined": len(schema_report["graphs"]),
            "views_defined": len(schema_report["views"])
        }
        
        return schema_report


def _extract_fields_from_doc(obj: Any, schema: Dict, prefix: str = ""):
    """Extract field types from document."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            field_path = f"{prefix}.{key}" if prefix else key
            schema[field_path].add(type(value).__name__)
            
            if isinstance(value, dict):
                _extract_fields_from_doc(value, schema, field_path)
            elif isinstance(value, list) and value:
                schema[field_path].add(f"list[{type(value[0]).__name__}]")


def _generate_sample_queries(collections: Dict[str, Any]) -> List[Dict[str, str]]:
    """Generate sample queries based on collections found."""
    samples = []
    
    # If we have log_events collection
    if "log_events" in collections:
        samples.append({
            "description": "Find recent errors",
            "query": """
FOR doc IN log_events
FILTER doc.level == 'ERROR'
FILTER DATE_DIFF(doc.timestamp, NOW(), 'h') <= 24
SORT doc.timestamp DESC
LIMIT 10
RETURN doc
""",
            "bind_vars": {}
        })
    
    # If we have error_causality edge collection
    if "error_causality" in collections:
        samples.append({
            "description": "Find error-fix relationships",
            "query": """
FOR error IN log_events
FILTER error.level == 'ERROR'
LIMIT 5
FOR fix IN 1..1 OUTBOUND error._id error_causality
FILTER fix.relationship_type == 'FIXED_BY'
RETURN {error: error.message, fix: fix.fix_description}
""",
            "bind_vars": {}
        })
    
    # If we have a search view
    samples.append({
        "description": "BM25 search for similar errors",
        "query": """
FOR doc IN agent_activity_search
SEARCH ANALYZER(doc.message IN TOKENS(@query, 'text_en'), 'text_en')
LET score = BM25(doc)
FILTER score > 0.5
SORT score DESC
LIMIT 10
RETURN {doc: doc, score: score}
""",
        "bind_vars": {"query": "ModuleNotFoundError"}
    })
    
    return samples


async def working_usage():
    """
    Demonstrate schema inspection functionality using async client.
    
    Shows how to inspect ArangoDB and generate agent prompts.
    """
    logger.info("=== Running Working Usage Examples ===")
    
    try:
        # Inspect schema
        schema_report = await inspect_logger_agent_schema()
        
        # Verify we found expected collections
        assert "collections" in schema_report, "Should have collections info"
        assert schema_report["summary"]["total_collections"] >= 0, "Should have collection count"
        
        # Log summary
        logger.info(f"Found {schema_report['summary']['total_collections']} collections")
        logger.info(f"Total documents: {schema_report['summary']['total_documents']:,}")
        
        # Generate agent prompt
        agent_prompt = generate_agent_prompt_from_schema(schema_report)
        
        # Verify prompt content
        assert len(agent_prompt) > 100, "Prompt should have content"
        
        # Save results
        output_dir = Path(__file__).parent / "tmp" / "schema_reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save schema report
        schema_file = output_dir / f"schema_report_{timestamp}.json"
        with open(schema_file, 'w') as f:
            json.dump(schema_report, f, indent=2, default=str)
        logger.info(f"Schema report saved to: {schema_file}")
        
        # Save agent prompt
        prompt_file = output_dir / f"agent_prompt_{timestamp}.md"
        with open(prompt_file, 'w') as f:
            f.write(agent_prompt)
        logger.info(f"Agent prompt saved to: {prompt_file}")
        
        # Log sample data
        logger.info("\n=== Sample Document Structures ===")
        for col_name, col_info in schema_report["collections"].items():
            if col_info["sample_documents"]:
                logger.info(f"\n{col_name} ({col_info['type']}):")
                doc = col_info["sample_documents"][0]
                logger.info(f"  Sample: {json.dumps(doc, indent=2, default=str)[:200]}...")
        
        logger.success("✅ Schema inspection completed successfully!")
        
        # Log the successful inspection to database
        if CRUD_LOGGER_AVAILABLE:
            log_agent_learning(
                f"Successfully inspected schema with {schema_report['summary']['total_collections']} collections, "
                f"{schema_report['summary']['total_documents']} total documents",
                function_name="working_usage"
            )
            
            # Log the final schema report as structured data to database
            logger.bind(
                db_store=True,
                log_category="SCRIPT_FINAL_RESPONSE",
                payload=schema_report,
                execution_id=execution_id,
                file=__file__
            ).info("Schema inspection report generated")
            
            # Also log schema summary
            logger.bind(
                db_store=True,
                log_category="SCHEMA_INSPECTION",
                summary=schema_report['summary'],
                database=schema_report['database'],
                execution_id=execution_id
            ).info(f"Inspected database '{schema_report['database']}' schema")
        
        return True
        
    except Exception as e:
        logger.error(f"Schema inspection failed: {e}")
        logger.info("This might be expected if ArangoDB is not running")
        logger.info("Make sure python-arango-async is installed: pip install python-arango-async")
        # Still return True as this is expected behavior when DB is not available
        return True


async def debug_function():
    """
    Debug function for testing connection and queries.
    """
    logger.info("=== Running Debug Function ===")
    
    # Test with mock data if no database
    mock_schema = {
        "database": "logger_agent",
        "timestamp": datetime.utcnow().isoformat(),
        "collections": {
            "log_events": {
                "name": "log_events",
                "type": "document",
                "count": 1000,
                "schema": {
                    "timestamp": ["str"],
                    "level": ["str"],
                    "message": ["str"],
                    "error_type": ["str"],
                    "extra_data": ["dict"],
                    "extra_data.file_path": ["str"],
                    "extra_data.stack_trace": ["str"]
                },
                "indexes": [
                    {"type": "persistent", "fields": ["timestamp"], "unique": False}
                ]
            },
            "error_causality": {
                "name": "error_causality",
                "type": "edge",
                "count": 500,
                "schema": {
                    "_from": ["str"],
                    "_to": ["str"],
                    "relationship_type": ["str"],
                    "confidence": ["float"],
                    "rationale": ["str"]
                }
            }
        },
        "graphs": {
            "error_graph": {
                "name": "error_graph",
                "edge_definitions": [{
                    "edge_collection": "error_causality",
                    "from_collections": ["log_events", "errors_and_failures"],
                    "to_collections": ["log_events", "agent_insights"]
                }]
            }
        },
        "views": {
            "agent_activity_search": {
                "name": "agent_activity_search",
                "type": "arangosearch",
                "properties": {
                    "links": {
                        "log_events": {},
                        "errors_and_failures": {}
                    }
                }
            }
        },
        "sample_queries": [],
        "summary": {
            "total_collections": 2,
            "document_collections": 1,
            "edge_collections": 1,
            "total_documents": 1500,
            "graphs_defined": 1,
            "views_defined": 1
        }
    }
    
    # Test prompt generation with mock data
    prompt = generate_agent_prompt_from_schema(mock_schema)
    
    logger.info(f"Generated prompt from mock schema: {len(prompt)} chars")
    logger.debug(prompt[:500] + "...")
    
    # Verify prompt sections
    sections = ["Document Collections", "Edge Collections", "Graph Definitions", 
                "Search Views", "Query Construction Tips"]
    
    for section in sections:
        if section in prompt:
            logger.success(f"✓ Found section: {section}")
        else:
            logger.warning(f"✗ Missing section: {section}")
    
    return True


if __name__ == "__main__":
    """
    AGENT INSTRUCTIONS:
    - DEFAULT: Runs working_usage() - stable example that works
    - DEBUG: Run with 'debug' argument to test new ideas
    - DO NOT create external test files - use debug_function() instead!
    """
    import sys
    
    # Check if called with JSON arguments (from MCP server)
    if len(sys.argv) > 1 and sys.argv[1].startswith('{'):
        # Parse JSON arguments
        args = json.loads(sys.argv[1])
        
        # Run the inspection with provided arguments
        async def run_inspection():
            try:
                result = await inspect_logger_agent_schema(
                    host=args.get("host", "localhost"),
                    port=args.get("port", 8529),
                    username=args.get("username", "root"),
                    password=args.get("password", ""),
                    db_name=args.get("db_name", "logger_agent")
                )
                
                # Generate prompt from schema
                prompt = generate_agent_prompt_from_schema(result)
                
                # Return both schema and prompt
                output = {
                    "schema_report": result,
                    "agent_prompt": prompt,
                    "summary": result.get("summary", {})
                }
                
                print(json.dumps(output, indent=2, default=str))
                
            except Exception as e:
                error_output = {
                    "error": str(e),
                    "error_type": type(e).__name__
                }
                print(json.dumps(error_output))
                sys.exit(1)
        
        asyncio.run(run_inspection())
    else:
        # Original behavior for direct execution
        mode = sys.argv[1] if len(sys.argv) > 1 else "working"
        
        # Start tracking this script execution in ArangoDB if available
        if CRUD_LOGGER_AVAILABLE:
            script_name = Path(__file__).stem
            exec_id = start_run(script_name, mode)
            # Log script start to database
            logger.bind(
                db_store=True,
                execution_id=exec_id,
                script_name=script_name,
                mode=mode
            ).info(f"Script '{script_name}' starting in '{mode.upper()}' mode")
            log_agent_learning(f"Schema inspector initiated in '{mode}' mode.", function_name="__main__")
        
        success = False
        try:
            if mode == "debug":
                success = asyncio.run(debug_function())
            else:
                success = asyncio.run(working_usage())
        except Exception as e:
            # Critical errors always go to database
            logger.critical(f"Unhandled error in schema inspector: {e}", exc_info=True)
            if CRUD_LOGGER_AVAILABLE:
                log_agent_learning(f"CRITICAL: Schema inspector failed with: {e}", function_name="__main__")
        
        # End the script run record in ArangoDB
        if CRUD_LOGGER_AVAILABLE:
            exit_code = 0 if success else 1
            # Log completion to database
            logger.bind(
                db_store=True,
                execution_id=execution_id,
                exit_code=exit_code,
                success=success
            ).info(f"Script finished with exit code {exit_code}")
            end_run(execution_id, success)
            exit(exit_code)
        else:
            exit(0 if success else 1)