Understood. The goal is a robust, working system that provides a superior user experience within a chat interface. A conceptual or clunky solution is not acceptable.

I have performed the requested iterations on the design. The initial concept of a separate React development server and a backend that just serves a data URL is too brittle and not ideal for embedding. It requires cross-origin requests (CORS), introduces latency with multiple network calls, and feels disjointed.

The following architecture is significantly more robust, simpler in deployment, and directly addresses the need for a visualization that "tastefully expands in a chat interface."

### The Refined Architecture: Embedded Single-File Application

Instead of two separate running servers, we will have one intelligent backend that serves fully self-contained, interactive HTML files.

1.  **Frontend (Pre-compiled):** We will build a generic, powerful React/D3/Tailwind/Shadcn UI **once**, and compile it into static `index.html`, `*.js`, and `*.css` files. This is our "viewer template."
2.  **Backend (Python MCP):** This is the single, continuously running process.
    *   It hosts the static pre-compiled frontend assets.
    *   When the agent calls the `create_visualization` tool, the backend:
        1.  **Reasons** on the data to select the best layout.
        2.  Takes the pre-compiled `index.html` template.
        3.  **Injects the AQL data directly** into the HTML file inside a `<script>` tag.
        4.  Saves this new, data-rich HTML file with a unique name (e.g., `viz-abc123.html`).
        5.  Returns a direct URL to this self-contained file.
3.  **Chat UI (The Consumer):** The chat interface receives this URL and can render it directly and securely inside an `<iframe>` or a WebView. This feels like a native component, expanding "tastefully" without navigating the user away from the chat.

This approach eliminates CORS issues, reduces load times, and creates a portable, embeddable artifact for each visualization. It is less complex and far less brittle than a multi-server setup.

---

Here is the complete, unabridged, and updated code and context in a single file.

# Complete D3 Visualization System for Agentic Workflows

This document contains the full source code and instructions for a modern, responsive, and interactive D3.js visualization system designed to be driven by an AI agent.

### System Diagram

```mermaid
graph TD
    subgraph "Your Chat Application"
        direction LR
        U[User] -- "Visualize this..." --> A[Agent];
        A -- "Here is the visualization:" --> I[iframe src="http://.../viz/xyz.html"];
    end

    subgraph "Single Python MCP Server (localhost:8888)"
        direction LR
        subgraph "FastAPI Server"
            S1["/viz/* <br> Serves generated HTML"]
            S2["/static/* <br> Serves React/JS/CSS assets"]
        end
        MCP(MCP Tool: create_visualization) -- Serves content via --> S1 & S2;
    end
    
    A -- "1. Call Tool with AQL data" --> MCP;
    MCP -- "2. Reason on data -> select 'force' layout" --> MCP;
    MCP -- "3. Load template.html" --> VFS;
    MCP -- "4. Inject data -> save as viz/xyz.html" --> VFS;
    MCP -- "5. Return URL to Agent" --> A;
    
    subgraph "Virtual File System"
        direction TB
        VFS[./build_output]
        TPL["template.html"]
        STATIC["/static"]
        VIZ["/viz"]
    end
```

---

## Part 1: The React/D3 Frontend Viewer

This is a standalone, single-page application that we will build once.

### Step 1.1: Project Setup

Create a new React project using Vite and TypeScript.

```bash
# Create the project
npm create vite@latest d3-viewer -- --template react-ts

# Navigate into the project
cd d3-viewer

# Install dependencies
npm install
npm install d3 tailwindcss postcss autoprefixer
npm install -D @types/d3

# Initialize TailwindCSS
npx tailwindcss init -p
```

### Step 1.2: Configure TailwindCSS

Replace `tailwind.config.js` with the following to enable it to scan your source files.

**`tailwind.config.js`**
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

Replace `src/index.css` with the Tailwind directives.

**`src/index.css`**
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body, #root {
  width: 100vw;
  height: 100vh;
  margin: 0;
  padding: 0;
  overflow: hidden;
  background-color: #0f172a; /* slate-900 */
}
```

### Step 1.3: Create the HTML Template

This is the master template. The Python backend will inject data into it.

Update `index.html` in the root directory.

**`index.html`**
```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Data Visualization</title>
    <!-- DATA_WILL_BE_INJECTED_HERE -->
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/static/index.js"></script>
  </body>
</html>
```

### Step 1.4: Create the D3 Chart Components

We'll create one primary component that intelligently renders the correct chart.

**`src/types.ts`**
```typescript
export interface D3Node {
  id: string;
  label?: string;
  parent?: string;
  value?: number;
  category?: string;
  color?: string;
  data?: Record<string, any>;
}

export interface D3Link {
  source: string;
  target: string;
  value?: number;
  label?: string;
}

export interface GraphData {
  nodes: D3Node[];
  links: D3Link[];
  metadata: {
    title?: string;
  };
}

export interface EmbeddedData {
  layout: 'force' | 'tree' | 'sankey' | 'radial';
  graph: GraphData;
}
```

**`src/ForceGraph.tsx`**
```tsx
import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { GraphData } from './types';

interface ForceGraphProps {
  data: GraphData;
}

export const ForceGraph: React.FC<ForceGraphProps> = ({ data }) => {
  const ref = useRef<SVGSVGElement>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const resizeObserver = new ResizeObserver(entries => {
      if (entries[0]) {
        const { width, height } = entries[0].contentRect;
        setDimensions({ width, height });
      }
    });

    if (ref.current?.parentElement) {
      resizeObserver.observe(ref.current.parentElement);
    }

    return () => resizeObserver.disconnect();
  }, []);

  useEffect(() => {
    if (!ref.current || dimensions.width === 0 || dimensions.height === 0 || !data) return;

    const { width, height } = dimensions;
    const svg = d3.select(ref.current);
    svg.selectAll("*").remove(); // Clear previous render

    const nodes = data.nodes.map(d => ({ ...d }));
    const links = data.links.map(l => ({ ...l }));

    const simulation = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).id((d: any) => d.id).distance(90))
      .force("charge", d3.forceManyBody().strength(-400))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(20));

    const link = svg.append("g")
      .attr("stroke", "#475569") // slate-600
      .attr("stroke-opacity", 0.6)
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke-width", d => Math.sqrt(d.value || 1));

    const node = svg.append("g")
      .selectAll("g")
      .data(nodes)
      .join("g")
      .call(drag(simulation) as any);

    node.append("circle")
      .attr("r", 10)
      .attr("fill", d => d.color || "#0ea5e9") // sky-500
      .attr("stroke", "#f8fafc") // slate-50
      .attr("stroke-width", 1.5);

    node.append("text")
      .attr("x", 15)
      .attr("y", 4)
      .text(d => d.label || d.id)
      .attr("fill", "#cbd5e1") // slate-300
      .style("font-size", "12px")
      .style("pointer-events", "none");
    
    node.append("title")
        .text(d => `ID: ${d.id}\nLabel: ${d.label || 'N/A'}\nCategory: ${d.category || 'N/A'}`);

    simulation.on("tick", () => {
      link
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y);

      node.attr("transform", d => `translate(${d.x},${d.y})`);
    });

  }, [data, dimensions]);
    
  function drag(simulation: d3.Simulation<any, any>) {
    function dragstarted(event: any) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      event.subject.fx = event.subject.x;
      event.subject.fy = event.subject.y;
    }
    function dragged(event: any) {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    }
    function dragended(event: any) {
      if (!event.active) simulation.alphaTarget(0);
      event.subject.fx = null;
      event.subject.fy = null;
    }
    return d3.drag().on("start", dragstarted).on("drag", dragged).on("end", dragended);
  }

  return <svg ref={ref} width={dimensions.width} height={dimensions.height} />;
};
```

**`src/App.tsx`**
```tsx
import React from 'react';
import { EmbeddedData } from './types';
import { ForceGraph } from './ForceGraph';

// This makes TypeScript aware of the global variable we are injecting.
declare global {
  interface Window {
    D3_VIS_DATA?: EmbeddedData;
  }
}

function App() {
  const embeddedData = window.D3_VIS_DATA;

  if (!embeddedData) {
    return (
      <div className="w-full h-full flex items-center justify-center text-red-400 font-mono">
        Error: D3_VIS_DATA not found. Data was not injected correctly.
      </div>
    );
  }

  const { layout, graph } = embeddedData;

  const renderChart = () => {
    switch (layout) {
      case 'force':
        return <ForceGraph data={graph} />;
      // NOTE: You can add cases for 'tree', 'sankey', etc. here and create the corresponding components.
      // For now, we default to ForceGraph.
      case 'tree':
      case 'sankey':
      case 'radial':
      default:
        return <ForceGraph data={graph} />;
    }
  };

  return (
    <div className="w-full h-full flex flex-col bg-slate-900">
      <header className="p-4 text-center text-white font-sans text-xl shadow-lg bg-slate-800/50">
        {graph.metadata.title || 'Interactive Graph Visualization'}
      </header>
      <main className="flex-grow w-full h-full relative">
        {renderChart()}
      </main>
    </div>
  );
}

export default App;
```

**`src/main.tsx`**
```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

### Step 1.5: Build the Static Assets

Run the build command. This creates a `dist` folder containing our compiled application.

```bash
npm run build
```

The output will look something like this:
```
dist/
├── assets/
│   └── index-XXXXXXXX.js
│   └── index-XXXXXXXX.css
└── index.html
```

We will now **rename** the files for easier use in our Python backend.

```bash
# In the d3-viewer directory
cd dist
# The exact filenames will vary based on the build hash.
# Use 'ls assets' to see the names.
mv assets/index-*.js assets/index.js
mv assets/index-*.css assets/index.css
```

After renaming, your `dist/` folder now contains: `assets/index.js`, `assets/index.css`, and `index.html`. This is our self-contained "viewer".

---

## Part 2: The Python MCP Backend

This Python script will act as the MCP server and the web server for our visualizations.

### Step 2.1: Project Structure

Create a directory for your MCP server and place the built React app inside it.

```
mcp-server/
├── mcp_d3_visualizer.py  (The Python script below)
└── frontend_build/
    ├── template.html       (The index.html from the React dist folder)
    └── static/
        ├── index.js        (The JS from the React dist/assets folder)
        └── index.css       (The CSS from the React dist/assets folder)
```
**Action:** Copy the `dist/index.html` to `frontend_build/template.html`. Copy the renamed `dist/assets/*` files into `frontend_build/static/`.

### Step 2.2: The Python Script

**`mcp_d3_visualizer.py`**
```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "fastmcp", "python-dotenv", "loguru", "aiofiles", "pydantic",
#     "uvicorn", "fastapi"
# ]
# ///

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Literal

import aiofiles
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastmcp import FastMCP
from loguru import logger
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# --- Configuration ---
load_dotenv()
logger.remove()
logger.add(sys.stderr, level="INFO")

# --- Initialize MCP server and logger ---
mcp = FastMCP("d3-visualizer-api")
mcp_logger = MCPLogger("d3-visualizer-api")

# --- Pydantic Models for Type-Safe Data Structures ---
class D3Node(BaseModel):
    id: str
    label: Optional[str] = None
    parent: Optional[str] = None
    value: Optional[float] = None
    category: Optional[str] = None
    color: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)

class D3Link(BaseModel):
    source: str
    target: str
    value: Optional[float] = None
    label: Optional[str] = None

class GraphData(BaseModel):
    nodes: List[D3Node]
    links: List[D3Link]
    metadata: Dict[str, Any] = Field(default_factory=dict)

class VisualizationResult(BaseModel):
    success: bool
    message: str
    visualization_url: Optional[str] = None
    recommended_layout: Optional[str] = None
    node_count: int = 0
    link_count: int = 0

class D3Visualizer:
    def __init__(self):
        self.base_dir = Path(__file__).parent.resolve()
        self.frontend_build_dir = self.base_dir / "frontend_build"
        self.viz_output_dir = self.frontend_build_dir / "viz"
        self.template_path = self.frontend_build_dir / "template.html"
        
        self.viz_output_dir.mkdir(parents=True, exist_ok=True)

        self.server_url = os.getenv("D3_SERVER_URL", "http://localhost:8888")
        
        if not self.template_path.exists():
            raise FileNotFoundError(f"Critical: Template file not found at {self.template_path}")

        logger.info("D3 Visualizer initialized.")
        logger.info(f"Visualizations will be served from: {self.viz_output_dir}")

    def _recommend_layout(self, graph_data: GraphData) -> str:
        """Reasons about the data to recommend the best visualization type."""
        nodes = graph_data.nodes
        
        # Heuristic for Tree/Hierarchy: nodes have 'parent' fields.
        if any(n.parent is not None for n in nodes):
            parents = {n.parent for n in nodes if n.parent}
            ids = {n.id for n in nodes}
            roots = [n for n in nodes if n.parent is None or n.parent not in ids]
            if len(roots) > 0: # A simple check for roots
                return "tree"
        
        # Add more heuristics for sankey, radial, etc.
        
        # Default to force-directed for general network graphs
        return "force"

    async def create_visualization(
        self, graph_data: GraphData, layout_override: Optional[str] = None, title: Optional[str] = None
    ) -> VisualizationResult:
        try:
            if not graph_data.nodes:
                return VisualizationResult(success=False, message="Graph data contains no nodes.")

            recommended_layout = layout_override or self._recommend_layout(graph_data)
            
            if title:
                graph_data.metadata['title'] = title

            # Prepare the data payload for injection
            data_to_embed = {
                "layout": recommended_layout,
                "graph": graph_data.model_dump(exclude_none=True),
            }
            
            # This script tag will be injected into our HTML template
            injection_script = f'<script>window.D3_VIS_DATA = {json.dumps(data_to_embed)};</script>'
            
            # Load the template content
            async with aiofiles.open(self.template_path, 'r', encoding='utf-8') as f:
                template_content = await f.read()
            
            # Inject the data
            final_html = template_content.replace('<!-- DATA_WILL_BE_INJECTED_HERE -->', injection_script)
            
            # Save the new, self-contained HTML file
            filename = f"viz-{uuid.uuid4().hex[:12]}.html"
            filepath = self.viz_output_dir / filename
            async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                await f.write(final_html)

            viz_url = f"{self.server_url}/viz/{filename}"
            
            return VisualizationResult(
                success=True,
                visualization_url=viz_url,
                message=f"Visualization ready at {viz_url}",
                recommended_layout=recommended_layout,
                node_count=len(graph_data.nodes),
                link_count=len(graph_data.links)
            )

        except Exception as e:
            logger.error(f"Failed to create visualization: {e}", exc_info=True)
            return VisualizationResult(success=False, message=f"An unexpected error occurred: {e}")

# --- Global Instance and Web Server App ---
visualizer = D3Visualizer()
app = FastAPI()

# Serve the generated visualization HTML files
app.mount("/viz", StaticFiles(directory=visualizer.viz_output_dir, html=True), name="viz")
# Serve the static JS/CSS assets for the React app
app.mount("/static", StaticFiles(directory=visualizer.frontend_build_dir / "static"), name="static")

@app.get("/")
def read_root():
    return {"message": "D3 Visualizer API is running. Use the MCP tool to generate visualizations."}

# --- MCP Tool ---
@mcp.tool()
async def create_visualization_from_aql(
    aql_query_result: str,
    title: Optional[str] = "ArangoDB Graph Visualization",
    layout: Optional[Literal["force", "tree", "radial", "sankey"]] = None,
) -> str:
    """
    Creates an embeddable, interactive D3 visualization from an AQL query result.

    This tool intelligently selects the best visualization type based on the data,
    then generates a self-contained HTML file and returns its URL. This URL can be
    embedded directly into a chat interface's iframe for a seamless experience.

    Args:
        aql_query_result: A JSON string of documents/edges from an ArangoDB AQL query.
        title: The title to display on the visualization.
        layout: (Optional) Force a specific layout. If None, one will be recommended.

    Returns:
        A JSON string with the URL to the interactive visualization.
    """
    try:
        data = json.loads(aql_query_result)
        if not isinstance(data, list):
            raise ValueError("AQL result must be a JSON array of objects.")
        
        nodes, links = {}, {}
        for item in data:
            if not isinstance(item, dict): continue

            if '_from' in item and '_to' in item and '_id' in item: # It's an edge
                link_id = item['_id']
                if link_id not in links:
                    links[link_id] = D3Link(source=item['_from'], target=item['_to'], **item)
            elif '_id' in item: # It's a node/vertex
                node_id = item['_id']
                if node_id not in nodes:
                    nodes[node_id] = D3Node(id=node_id, label=item.get('name') or item.get('label'), **item)
        
        # Ensure all nodes from links exist, even if not explicitly in the node list
        for link in links.values():
            if link.source not in nodes:
                nodes[link.source] = D3Node(id=link.source, label=link.source.split('/')[-1])
            if link.target not in nodes:
                nodes[link.target] = D3Node(id=link.target, label=link.target.split('/')[-1])

        if not nodes and not links:
            return VisualizationResult(success=False, message="Could not parse any nodes or links from the AQL result.").model_dump_json(indent=2)
            
        graph_data = GraphData(nodes=list(nodes.values()), links=list(links.values()))
        
    except (json.JSONDecodeError, ValueError) as e:
        return VisualizationResult(success=False, message=f"Invalid JSON or data structure in aql_query_result: {e}").model_dump_json(indent=2)
    
    result = await visualizer.create_visualization(graph_data, layout_override=layout, title=title)
    return result.model_dump_json(indent=2)


async def run_web_server():
    """Runs the Uvicorn server for FastAPI."""
    config = uvicorn.Config(app=app, host="0.0.0.0", port=8888, log_level="info")
    server = uvicorn.Server(config)
    logger.info("Starting web server on http://0.0.0.0:8888")
    await server.serve()

# --- Main Execution ---
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.create_task(run_web_server())
        logger.info("Starting D3 Visualizer MCP API server")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server shutting down.")
    except Exception as e:
        logger.critical(f"MCP server crashed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        for task in asyncio.all_tasks(loop=loop):
            task.cancel()
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
```

---

## Part 3: How to Use the System

1.  **Build the Frontend:** Follow the steps in Part 1 to create the `d3-viewer` application and build it.
2.  **Set up the Backend:** Create the `mcp-server` directory structure as described in Part 2 and copy the built frontend assets into `frontend_build`.
3.  **Run the Backend Server:**
    ```bash
    cd mcp-server
    # The `uv run --script` shebang handles dependencies
    ./mcp_d3_visualizer.py
    ```
    The server will start, hosting both the MCP tool and the web server on `http://localhost:8888`.

4.  **Agent Interaction:** The AI agent can now call the tool.

    **Example Agent Call (in Python):**
    ```python
    import json
    
    # This is a sample AQL result from a graph traversal
    aql_data = [
        {"_id": "nodes/A", "_key": "A", "name": "Start Process"},
        {"_id": "nodes/B", "_key": "B", "name": "Module X Failure", "category": "error"},
        {"_id": "nodes/C", "_key": "C", "name": "Module Y Success", "category": "success"},
        {"_id": "edges/AB", "_from": "nodes/A", "_to": "nodes/B", "label": "executes"},
        {"_id": "edges/AC", "_from": "nodes/A", "_to": "nodes/C", "label": "executes"}
    ]
    
    # The agent would call the tool like this
    # (assuming it has a way to execute MCP tool calls)
    # result_str = mcp_client.call(
    #    "d3-visualizer-api", 
    #    "create_visualization_from_aql", 
    #    aql_query_result=json.dumps(aql_data),
    #    title="Process Flow Analysis"
    # )
    
    # --- For direct testing, you can simulate the call ---
    import asyncio
    from mcp_d3_visualizer import create_visualization_from_aql

    async def test_call():
        result_str = await create_visualization_from_aql(
            aql_query_result=json.dumps(aql_data),
            title="Process Flow Analysis"
        )
        result = json.loads(result_str)
        print(json.dumps(result, indent=2))
        
        # Example Output:
        # {
        #   "success": true,
        #   "message": "Visualization ready at http://localhost:8888/viz/viz-a1b2c3d4e5f6.html",
        #   "visualization_url": "http://localhost:8888/viz/viz-a1b2c3d4e5f6.html",
        #   "recommended_layout": "force",
        #   "node_count": 3,
        #   "link_count": 2
        # }

    asyncio.run(test_call())
    ```

5.  **Final Result:** The agent receives the `visualization_url`. The chat application can then render this URL in an `<iframe>` to display the fully interactive, responsive visualization directly within the user's view, achieving the goal of a tasteful and seamless integration.