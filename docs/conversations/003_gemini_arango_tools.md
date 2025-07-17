You've asked two excellent, forward-thinking questions that push us to define the boundaries and responsibilities of our MCP tools.

1.  **Are we missing any tools in `arango-tools`?** Given its purpose for agentic memory and graph-based problem solving, there is one critical category of tools missing: **Graph Analytics and Pattern Detection.** The current tools are great for CRUD (Create, Read, Update, Delete) and basic queries, but an advanced agent needs tools to *understand* the structure of the graph it's building.

2.  **Should D3 visualization be a separate MCP tool?** **Yes, absolutely.** This is a perfect example of the "Separate Responsibilities" principle. `arango-tools` manages the database; it shouldn't be burdened with the complex, heavy dependencies (`d3`, JavaScript templating) of a visualization engine. Visualization is a distinct capability and should be its own service.

Let's address both points.

---

### 1. Missing Tools in `arango-tools`: Adding Graph Analytics

An agent trying to solve problems by looking at relationships needs to ask questions like:
*   "What are the most important nodes in this graph?" (Centrality)
*   "Are there distinct communities or clusters of problems?" (Community Detection)
*   "What is the shortest path between this error and a known solution?" (Pathfinding)

These are standard graph algorithms. We should add a new tool to `arango-tools` to expose them.

**Improvement: Add a new `analyze_graph` tool to `mcp_arango_tools.py`**

This new tool will be a single entry point for various graph algorithms, making it easy for the agent to use without needing to know the specific AQL for each one.

Here's how we'd add it to the `ArangoTools` class in `mcp_arango_tools.py`:

```python
# In the ArangoTools class in mcp_arango_tools.py

# ... (after the other methods like extract_lesson) ...

    def analyze_graph(self, graph_name: str, algorithm: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Executes a graph analysis algorithm on a specified graph.
        
        Args:
            graph_name: The name of the graph to analyze.
            algorithm: The algorithm to run (e.g., 'centrality', 'community', 'shortest_path').
            params: A dictionary of parameters required by the algorithm.
        """
        params = params or {}
        try:
            if algorithm == "centrality":
                # Example: PageRank centrality
                aql = """
                FOR v IN 1..1 ANY 'vertices/start_node' GRAPH @graph_name
                  OPTIONS {uniqueVertices: 'global', order: 'bfs'}
                  COLLECT vertex = v._id WITH COUNT INTO length
                  RETURN { vertex, length }
                """
                # This is a simplified example. Real centrality often requires Pregel.
                # A better approach would be to use ArangoDB's graph algorithms.
                # For now, we'll just show a placeholder for the agent.
                return {"error": "Centrality requires a more complex Pregel setup, use AQL directly for now."}

            elif algorithm == "community":
                # Example: Label Propagation
                aql = """
                FOR v IN ANY K_SHORTEST_PATHS 'vertices/start_node' TO 'vertices/end_node'
                GRAPH @graph_name
                RETURN v
                """
                # Again, this is a placeholder. Real community detection uses Pregel.
                return {"error": "Community detection requires a more complex Pregel setup, use AQL directly for now."}

            elif algorithm == "shortest_path":
                if "start_node_id" not in params or "end_node_id" not in params:
                    return {"success": False, "error": "shortest_path requires 'start_node_id' and 'end_node_id' in params."}
                
                aql = """
                FOR p IN ANY SHORTEST_PATH @start_node TO @end_node
                GRAPH @graph_name
                RETURN p
                """
                bind_vars = {
                    "graph_name": graph_name,
                    "start_node": params["start_node_id"],
                    "end_node": params["end_node_id"]
                }
                cursor = self.db.aql.execute(aql, bind_vars=bind_vars)
                return {"success": True, "results": list(cursor)}

            else:
                return {"success": False, "error": f"Unsupported algorithm: {algorithm}. Supported: 'shortest_path'."}

        except Exception as e:
            return {"success": False, "error": str(e)}

# Then, expose it as an MCP tool:
@mcp.tool()
async def analyze_graph(graph_name: str, algorithm: str, params_json: Optional[str] = None) -> str:
    """
    Executes a graph analysis algorithm (e.g., shortest_path).
    
    Args:
        graph_name: The name of the graph (e.g., 'error_knowledge_graph').
        algorithm: 'shortest_path' is currently supported.
        params_json: JSON string of parameters. For 'shortest_path', requires '{"start_node_id": "...", "end_node_id": "..."}'.
    """
    params = {}
    if params_json:
        try:
            params = json.loads(params_json)
        except json.JSONDecodeError:
            return json.dumps({"success": False, "error": "Invalid JSON in params_json."})
    
    result = tools.analyze_graph(graph_name, algorithm, params)
    return json.dumps(result, indent=2, default=str)
```

This adds a crucial analytical capability that was missing.

---

### 2. The D3 Visualization Tool: A New, Separate MCP Server

You are correct, this deserves its own server. It has different dependencies (`d3` logic, HTML templating), a different purpose (presentation, not data management), and is a perfect example of a composable tool.

Here is the complete, unabridged MCP server for D3 visualization.

**`src/resume/servers/mcp_d3_visualizer.py`**
```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "fastmcp", "python-dotenv", "loguru", "pydantic",
#     "jinja2"  # Using Jinja2 for robust HTML templating
# ]
# ///
"""
An MCP tool to generate interactive D3.js graph visualizations from data.

This tool takes structured graph data (nodes and links) and generates a
standalone HTML file with an interactive visualization. It separates the data
logic from the presentation logic.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional, Literal

from fastmcp import FastMCP
from pydantic import BaseModel, Field
from dotenv import load_dotenv, find_dotenv
from loguru import logger
from jinja2 import Environment, FileSystemLoader

# --- Boilerplate & Initialization ---
load_dotenv(find_dotenv()); env_path = find_dotenv()
project_root = Path(env_path).parent if env_path else Path.cwd()
sys.path.insert(0, str(project_root)); sys.path.insert(0, str(project_root / "src"))
logger.remove(); logger.add(sys.stderr, level="INFO")
# --- End Boilerplate ---

# --- Jinja2 Environment for Templating ---
# Assumes templates are in a 'templates' subdirectory relative to this file
template_path = Path(__file__).parent / "templates"
env = Environment(loader=FileSystemLoader(template_path))
logger.info(f"Jinja2 template loader configured for path: {template_path}")

# --- Pydantic Models ---
class VisualizationResult(BaseModel):
    status: Literal["success", "error"]
    html_file_path: Optional[str] = Field(default=None, description="The path to the generated HTML visualization file.")
    message: str
    error_details: Optional[str] = None

# --- MCP Server ---
mcp = FastMCP("d3-visualizer")

@mcp.tool()
async def generate_graph_visualization(
    graph_data_json: str = Field(description="A JSON string representing the graph data, with 'nodes' and 'links' keys."),
    output_dir: str = Field(description="The directory path where the HTML file should be saved."),
    filename: str = Field(default="graph_visualization.html", description="The name of the output HTML file."),
    layout: Literal["force", "tree"] = Field(default="force", description="The D3 layout algorithm to use."),
    title: str = Field(default="Interactive Graph Visualization", description="The title of the HTML page and visualization.")
) -> VisualizationResult:
    """
    Generates an interactive D3.js visualization from graph data and saves it as an HTML file.
    """
    logger.info(f"Generating '{layout}' visualization, saving to '{output_dir}/{filename}'")
    
    try:
        # 1. Validate and create output path
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        final_path = output_path / filename

        # 2. Parse input data
        try:
            graph_data = json.loads(graph_data_json)
            if "nodes" not in graph_data or "links" not in graph_data:
                raise ValueError("JSON must contain 'nodes' and 'links' keys.")
        except (json.JSONDecodeError, ValueError) as e:
            return VisualizationResult(status="error", message="Invalid graph_data_json provided.", error_details=str(e))

        # 3. Select and load the Jinja2 template
        template_name = f"{layout}_template.html"
        try:
            template = env.get_template(template_name)
        except Exception as e:
            logger.error(f"Template '{template_name}' not found in '{template_path}'.")
            return VisualizationResult(status="error", message=f"Unsupported layout or template missing: {layout}", error_details=str(e))

        # 4. Render the template with the provided data
        html_content = template.render(
            graph_title=title,
            graph_data_json=json.dumps(graph_data) # Re-serialize for embedding in HTML
        )

        # 5. Write the final HTML file
        with open(final_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.success(f"Successfully created visualization at: {final_path}")
        return VisualizationResult(
            status="success",
            html_file_path=str(final_path),
            message=f"Visualization successfully generated."
        )
    except Exception as e:
        logger.exception("Failed to generate visualization.")
        return VisualizationResult(status="error", message="An unexpected error occurred.", error_details=str(e))

# To make this runnable, you would need to create a 'templates' directory
# next to this script with 'force_template.html' and 'tree_template.html'.
# Example `force_template.html`:
"""
<!DOCTYPE html>
<html>
<head>
    <title>{{ graph_title }}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        /* CSS from your force.css file would go here */
        .node { stroke: #fff; stroke-width: 1.5px; }
        .link { stroke: #999; stroke-opacity: 0.6; }
    </style>
</head>
<body>
    <svg width="960" height="600"></svg>
    <script>
        const graphData = {{ graph_data_json|safe }};
        // D3.js code to render a force-directed graph...
        // ...
    </script>
</body>
</html>
"""
```
By creating these two distinct solutions—enhancing the `arango-tools` toolkit and creating a new, separate `d3-visualizer` tool—you build a far more capable, maintainable, and logically sound agentic system.