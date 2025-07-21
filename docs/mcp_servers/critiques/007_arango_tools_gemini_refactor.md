Of course. The current `mcp_arango_tools.py` has grown to encompass several distinct responsibilities: core database operations (CRUD), knowledge management (glossary/learning), advanced data science (clustering/FAISS), and administration (backups).

The optimum refactor for agent understanding is to split this monolithic server into multiple, purpose-driven MCP servers. This aligns with the principle that "self-contained is easier for the agent to understand." An agent can reason about "which tool do I need for this task?" more effectively when the tools are granular.

Here is the suggested refactor into four distinct, self-contained MCP servers:

1.  **`arango-core-tools`**: For fundamental, high-frequency database interactions (CRUD, AQL).
2.  **`arango-analytics-tools`**: For complex data science, clustering, and similarity tasks (the FAISS part).
3.  **`arango-learning-tools`**: For managing the agent's knowledge base and learning from outcomes.
4.  **`arango-admin-tools`**: For database maintenance tasks like backups and pruning.

This structure isolates dependencies (e.g., `faiss`, `scikit-learn` are only needed by `arango-analytics-tools`) and makes the agent's choice of tool much clearer.

---

### Step 1: Create a Shared Utility for the Database Connection

To avoid repeating code, we'll create a small utility for handling the ArangoDB connection.

**`src/cc_executor/servers/arango_client_util.py`**
```python
import os
from loguru import logger
from arango import ArangoClient

def get_arango_db_connection():
    """
    Establishes and returns a connection to the ArangoDB database.
    This centralized function ensures consistent connection logic across all
    ArangoDB-related MCP servers.
    """
    try:
        password = os.getenv("ARANGO_PASSWORD", "")
        if not password:
            logger.warning(
                "⚠️  ARANGO_PASSWORD not set - using insecure default 'openSesame'. "
                "Please set ARANGO_PASSWORD in your .env file for production use!"
            )
            password = "openSesame"

        client = ArangoClient(hosts=os.getenv("ARANGO_URL", "http://localhost:8529"))
        db = client.db(
            os.getenv("ARANGO_DATABASE", "script_logs"),
            username=os.getenv("ARANGO_USERNAME", "root"),
            password=password,
            verify=True # Good practice to verify connection
        )
        logger.info(f"Successfully connected to ArangoDB database: {db.name}")
        return db
    except Exception as e:
        logger.error(f"Fatal: Failed to connect to ArangoDB: {e}")
        raise

```

---

### Step 2: Refactor into Four New MCP Servers

Now, here are the four refactored, self-contained server files.

#### 1. The Core Tool: `arango_core_tools.py`

This server handles the absolute basics. It's lightweight and will be used most often.

**`src/cc_executor/servers/arango_core_tools.py`**
```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "fastmcp", "python-dotenv", "python-arango", "loguru",
#     "mcp-logger-utils>=0.1.5"
# ]
# ///
"""
MCP Server for Core ArangoDB Tools - CRUD, AQL, and Schema.
"""
import json
import sys
from typing import Dict, Any, Optional

from fastmcp import FastMCP
from loguru import logger
from dotenv import load_dotenv, find_dotenv
from mcp_logger_utils import MCPLogger, debug_tool
from arango.exceptions import ArangoError

# Assumes arango_client_util.py is in the same directory or PYTHONPATH
from arango_client_util import get_arango_db_connection

# Load environment variables
load_dotenv(find_dotenv())

# Initialize
mcp = FastMCP("arango-core-tools")
mcp_logger = MCPLogger("arango-core-tools")

class ArangoCoreTools:
    """Core ArangoDB tools for MCP: Schema, Query, and CRUD."""

    def __init__(self):
        """Initialize connection."""
        self.db = get_arango_db_connection()

    def get_schema(self) -> Dict[str, Any]:
        """Get database schema information."""
        try:
            collections = {c['name']: {'type': c['type']} for c in self.db.collections() if not c['name'].startswith('_')}
            graphs = {g['name']: {'edges': g['edge_definitions']} for g in self.db.graphs()}
            return {"success": True, "database": self.db.name, "collections": collections, "graphs": graphs}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute_aql(self, aql: str, bind_vars: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute AQL query."""
        try:
            cursor = self.db.aql.execute(aql, bind_vars=bind_vars or {})
            results = list(cursor)
            return {"success": True, "count": len(results), "results": results}
        except ArangoError as e:
            return {"success": False, "error": str(e), "aql": aql}

    def insert(self, collection: str, document: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a document."""
        try:
            result = self.db.collection(collection).insert(document)
            return {"success": True, "id": result["_id"], "key": result["_key"]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_edge(self, collection: str, from_id: str, to_id: str, edge_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Create an edge between two documents."""
        edge_doc = {"_from": from_id, "_to": to_id, **(edge_data or {})}
        try:
            result = self.db.collection(collection).insert(edge_doc)
            return {"success": True, "id": result["_id"], "key": result["_key"]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_document(self, collection: str, key: str) -> Dict[str, Any]:
        """Get a single document by key."""
        try:
            doc = self.db.collection(collection).get(key)
            if doc is None:
                return {"success": False, "error": "Document not found"}
            return {"success": True, "document": doc}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def upsert(self, collection: str, search: Dict, update: Dict, insert: Dict) -> Dict[str, Any]:
        """Upsert a document."""
        aql = "UPSERT @search INSERT @insert UPDATE @update IN @@collection RETURN { doc: NEW, type: OLD ? 'updated' : 'inserted' }"
        bind_vars = {"@collection": collection, "search": search, "insert": insert, "update": update}
        return self.execute_aql(aql, bind_vars)

tools = ArangoCoreTools()

@mcp.tool()
@debug_tool(mcp_logger)
async def schema() -> str:
    """Get ArangoDB schema including collections and graphs."""
    return json.dumps(tools.get_schema(), indent=2)

@mcp.tool()
@debug_tool(mcp_logger)
async def query(aql: str, bind_vars: Optional[str] = None) -> str:
    """Execute an AQL query. Bind vars must be a JSON string."""
    parsed_bind_vars = json.loads(bind_vars) if bind_vars else {}
    result = tools.execute_aql(aql, parsed_bind_vars)
    return json.dumps(result, indent=2)

@mcp.tool()
@debug_tool(mcp_logger)
async def insert(collection: str, document: str) -> str:
    """Insert a document. Document must be a JSON string."""
    doc_dict = json.loads(document)
    return json.dumps(tools.insert(collection, doc_dict), indent=2)

@mcp.tool()
@debug_tool(mcp_logger)
async def get(collection: str, key: str) -> str:
    """Get a document by its _key."""
    return json.dumps(tools.get_document(collection, key), indent=2)

@mcp.tool()
@debug_tool(mcp_logger)
async def edge(collection: str, from_id: str, to_id: str, data: Optional[str] = None) -> str:
    """Create an edge. Data must be a JSON string."""
    data_dict = json.loads(data) if data else {}
    return json.dumps(tools.create_edge(collection, from_id, to_id, data_dict), indent=2)
    
@mcp.tool()
@debug_tool(mcp_logger)
async def upsert(collection: str, search: str, update: str, create: str) -> str:
    """Update a document if it exists, otherwise create it. All params must be JSON strings."""
    search_dict = json.loads(search)
    update_dict = json.loads(update)
    create_dict = json.loads(create)
    # The insert document should contain the search fields as well
    insert_doc = {**search_dict, **create_dict}
    return json.dumps(tools.upsert(collection, search_dict, update_dict, insert_doc), indent=2)

if __name__ == "__main__":
    mcp.run()
```

---
#### 2. The Analytics Tool: `arango_analytics_tools.py`

This server contains all the heavy data science and FAISS logic. It has more dependencies.

**`src/cc_executor/servers/arango_analytics_tools.py`**
```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "fastmcp", "python-dotenv", "python-arango", "loguru",
#     "mcp-logger-utils>=0.1.5",
#     "faiss-cpu", "scikit-learn", "numpy", "networkx", "python-louvain", "sentence-transformers"
# ]
# ///
"""
MCP Server for Advanced ArangoDB Analytics - Clustering, Similarity, and Graphs.
"""
import json
import sys
from typing import Dict, Any, Optional, List

from fastmcp import FastMCP
from loguru import logger
from dotenv import load_dotenv, find_dotenv
from mcp_logger_utils import MCPLogger, debug_tool

# Assumes arango_client_util.py is in the same directory or PYTHONPATH
from arango_client_util import get_arango_db_connection

# Load environment variables
load_dotenv(find_dotenv())

# Initialize
mcp = FastMCP("arango-analytics-tools")
mcp_logger = MCPLogger("arango-analytics-tools")

class ArangoAnalyticsTools:
    """Advanced analytics for ArangoDB data."""

    def __init__(self):
        self.db = get_arango_db_connection()

    def build_similarity_graph(self, collection: str, text_field: str, edge_collection: str, threshold: float):
        """(Implementation from original file)
        Uses FAISS and SentenceTransformers to build a similarity graph.
        """
        # --- [Copy and paste the full implementation of build_similarity_graph here] ---
        # Make sure to import dependencies like faiss, numpy, etc. inside the function
        # to handle potential import errors gracefully.
        try:
            from sentence_transformers import SentenceTransformer
            import faiss
            import numpy as np
            
            # ... rest of the function logic
            logger.info("Building similarity graph...")
            # This is a placeholder for the full logic
            return {"success": True, "message": "Placeholder for build_similarity_graph logic."}

        except ImportError as e:
            return {"success": False, "error": f"Missing dependency: {e}. Please install.", "fix": "uv pip install faiss-cpu sentence-transformers numpy"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cluster_analysis(self, collection: str, text_field: str, n_clusters: int):
        """(Implementation from original file)
        Performs clustering on documents using scikit-learn.
        """
        # --- [Copy and paste the full implementation of cluster_analysis here] ---
        # Make sure to import dependencies like sklearn inside the function.
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.cluster import KMeans

            # ... rest of the function logic
            logger.info("Performing cluster analysis...")
            # This is a placeholder for the full logic
            return {"success": True, "message": "Placeholder for cluster_analysis logic."}
        
        except ImportError as e:
            return {"success": False, "error": f"Missing dependency: {e}. Please install.", "fix": "uv pip install scikit-learn"}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    # --- [Copy other analytics methods: find_similar_documents, detect_communities, etc.] ---


tools = ArangoAnalyticsTools()

@mcp.tool()
@debug_tool(mcp_logger)
async def cluster(collection: str, text_field: str, n_clusters: int = 5) -> str:
    """Perform KMeans clustering on documents based on a text field."""
    result = tools.cluster_analysis(collection, text_field, n_clusters)
    return json.dumps(result, indent=2)

@mcp.tool()
@debug_tool(mcp_logger)
async def build_similarity_graph(collection: str, text_field: str, edge_collection: str, threshold: float = 0.8) -> str:
    """Build a graph connecting similar documents using FAISS."""
    result = tools.build_similarity_graph(collection, text_field, edge_collection, threshold)
    return json.dumps(result, indent=2)

# --- [Add MCP tool wrappers for other analytics methods] ---

if __name__ == "__main__":
    mcp.run()
```
*(Note: For brevity, the full implementation of the analytics methods is omitted, but you would copy them from the original file into the placeholder sections.)*

---
#### 3. The Learning Tool: `arango_learning_tools.py`

Focuses on the agent's internal knowledge base and feedback loops.

**`src/cc_executor/servers/arango_learning_tools.py`**
```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "fastmcp", "python-dotenv", "python-arango", "loguru",
#     "mcp-logger-utils>=0.1.5"
# ]
# ///
"""
MCP Server for Agent Learning - Glossary, Outcomes, and Lessons.
"""
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List

from fastmcp import FastMCP
from loguru import logger
from dotenv import load_dotenv, find_dotenv
from mcp_logger_utils import MCPLogger, debug_tool

from arango_client_util import get_arango_db_connection

load_dotenv(find_dotenv())
mcp = FastMCP("arango-learning-tools")
mcp_logger = MCPLogger("arango-learning-tools")

class ArangoLearningTools:
    """Tools for agent's knowledge management and learning."""

    def __init__(self):
        self.db = get_arango_db_connection()
        self._ensure_collections()

    def _ensure_collections(self):
        """Ensure all required learning collections exist."""
        collections = {
            "glossary_terms": False, "term_relationships": True,
            "solution_outcomes": False, "lessons_learned": False,
            "solution_to_lesson": True, "research_cache": False
        }
        for name, is_edge in collections.items():
            if not self.db.has_collection(name):
                self.db.create_collection(name, edge=is_edge)
                logger.info(f"Created collection: {name}")

    def add_glossary_term(self, term: str, definition: str, metadata: dict):
        """(Implementation from original file)"""
        # --- [Copy and paste the full implementation of add_glossary_term here] ---
        return {"success": True, "message": "Placeholder for add_glossary_term logic."}


    def track_solution_outcome(self, solution_id: str, outcome: str, metadata: dict):
        """(Implementation from original file)"""
        # --- [Copy and paste the full implementation of track_solution_outcome here] ---
        return {"success": True, "message": "Placeholder for track_solution_outcome logic."}
        
    def research_database_issue(self, error_info: Dict):
        """(Implementation from original file)"""
        # --- [Copy and paste the full implementation of research_database_issue here] ---
        return {"success": True, "message": "Placeholder for research_database_issue logic."}
        
    # --- [Copy other learning methods: link_glossary_terms, discover_patterns, etc.] ---

tools = ArangoLearningTools()

@mcp.tool()
@debug_tool(mcp_logger)
async def add_term(term: str, definition: str, metadata: Optional[str] = None) -> str:
    """Add a term to the glossary. Metadata is a JSON string."""
    meta_dict = json.loads(metadata) if metadata else {}
    return json.dumps(tools.add_glossary_term(term, definition, meta_dict), indent=2)

@mcp.tool()
@debug_tool(mcp_logger)
async def track_outcome(solution_id: str, outcome: str, metadata: Optional[str] = None) -> str:
    """Track the outcome of a solution. Metadata is a JSON string."""
    meta_dict = json.loads(metadata) if metadata else {}
    return json.dumps(tools.track_solution_outcome(solution_id, outcome, meta_dict), indent=2)

@mcp.tool()
@debug_tool(mcp_logger)
async def research_error(error_context: str) -> str:
    """Generates research steps for a database error. Error context is a JSON string."""
    error_dict = json.loads(error_context)
    return json.dumps(tools.research_database_issue(error_dict), indent=2)

# --- [Add MCP tool wrappers for other learning methods] ---

if __name__ == "__main__":
    mcp.run()
```

---
#### 4. The Admin Tool: `arango_admin_tools.py`

For potentially slow or privileged database maintenance operations.

**`src/cc_executor/servers/arango_admin_tools.py`**
```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "fastmcp", "python-dotenv", "python-arango", "loguru",
#     "mcp-logger-utils>=0.1.5"
# ]
# ///
"""
MCP Server for ArangoDB Administration - Backups and Pruning.
"""
import json
import sys
import os
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from fastmcp import FastMCP
from loguru import logger
from dotenv import load_dotenv, find_dotenv
from mcp_logger_utils import MCPLogger, debug_tool

from arango_client_util import get_arango_db_connection

load_dotenv(find_dotenv())
mcp = FastMCP("arango-admin-tools")
mcp_logger = MCPLogger("arango-admin-tools")

class ArangoAdminTools:
    """Administrative tools for database maintenance."""

    def __init__(self):
        self.db = get_arango_db_connection()

    def prune_old_documents(self, days_old: int, collections: List[str], dry_run: bool):
        """(Implementation from original file)"""
        # --- [Copy and paste the full implementation of prune_old_documents here] ---
        return {"success": True, "message": "Placeholder for prune_old_documents logic."}

    def backup_database(self, backup_name: str, collections: Optional[List[str]]):
        """(Implementation from original file)"""
        # --- [Copy and paste the full implementation of backup_database here] ---
        return {"success": True, "message": "Placeholder for backup_database logic."}

tools = ArangoAdminTools()

@mcp.tool()
@debug_tool(mcp_logger)
async def prune(days_old: int, collections: str, dry_run: bool = True) -> str:
    """Prune old documents. Collections is a JSON array string."""
    col_list = json.loads(collections)
    return json.dumps(tools.prune_old_documents(days_old, col_list, dry_run), indent=2)

@mcp.tool()
@debug_tool(mcp_logger)
async def backup(backup_name: str, collections: Optional[str] = None) -> str:
    """Backup the database. Collections is an optional JSON array string."""
    col_list = json.loads(collections) if collections else None
    return json.dumps(tools.backup_database(backup_name, col_list), indent=2)

if __name__ == "__main__":
    mcp.run()
```

### Summary of Benefits

This refactor provides:

1.  **Clarity for the Agent**: An agent wanting to store a log uses `arango-core-tools.insert`. An agent wanting to find similar past errors uses `arango-analytics-tools.find_similar`. The intent is clear from the tool server's name.
2.  **Efficiency**: The lightweight `arango-core-tools` server can be loaded quickly for common tasks. The heavy `arango-analytics-tools` with its ML libraries is only loaded when needed.
3.  **Improved Maintainability**: Each file is smaller, focused, and easier to debug or extend.
4.  **Isolated Dependencies**: A missing `faiss` library won't prevent the core database tools from starting.
5.  **Simpler Tool Signatures**: The tool functions in each server can be made simpler and more direct, as they don't have to accommodate dozens of unrelated use cases in one function signature.