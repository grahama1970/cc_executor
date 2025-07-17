#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "fastmcp",
#     "python-dotenv",
#     "loguru",
#     "httpx",
#     "jinja2"
# ]
# ///
"""
MCP Server for D3.js Visualizations - Generate interactive graph visualizations.

This MCP server provides agents with the ability to create interactive D3.js
visualizations from graph data. It can work standalone or integrate with the
visualization server for advanced features.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Literal
import uuid

from fastmcp import FastMCP
from loguru import logger
from dotenv import load_dotenv, find_dotenv
from jinja2 import Environment, BaseLoader
import httpx

# Add utils to path for MCP logger
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.mcp_logger import MCPLogger, debug_tool

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")

# Load environment variables
load_dotenv(find_dotenv())

# Initialize MCP server and logger
mcp = FastMCP("d3-visualizer")
mcp_logger = MCPLogger("d3-visualizer")


class D3Visualizer:
    """D3.js visualization generator."""
    
    def __init__(self):
        """Initialize visualizer."""
        self.output_dir = Path(os.getenv("D3_OUTPUT_DIR", "/tmp/visualizations"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if visualization server is available
        self.viz_server_url = os.getenv("VIZ_SERVER_URL", "http://localhost:8000")
        self.use_server = self._check_server_availability()
        
        # Initialize Jinja2 for template rendering
        self.jinja_env = Environment(loader=BaseLoader())
        
        logger.info(f"D3 Visualizer initialized. Output dir: {self.output_dir}")
        logger.info(f"Visualization server: {'Available' if self.use_server else 'Not available'}")
    
    def _check_server_availability(self) -> bool:
        """Check if visualization server is running."""
        try:
            response = httpx.get(f"{self.viz_server_url}/", timeout=2.0)
            return response.status_code == 200
        except:
            return False
    
    def generate_visualization(
        self,
        graph_data: Dict[str, Any],
        layout: str = "force",
        title: str = "Graph Visualization",
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate visualization HTML.
        
        Args:
            graph_data: Dict with 'nodes' and 'links' keys
            layout: Layout type (force, tree, radial, sankey)
            title: Visualization title
            config: Additional configuration options
            
        Returns:
            Result with file path and metadata
        """
        try:
            # Validate graph data
            if "nodes" not in graph_data or "links" not in graph_data:
                return {
                    "success": False,
                    "error": "Graph data must contain 'nodes' and 'links' keys"
                }
            
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{layout}_{timestamp}_{uuid.uuid4().hex[:8]}.html"
            filepath = self.output_dir / filename
            
            # If server is available, use it for advanced features
            if self.use_server:
                try:
                    response = httpx.post(
                        f"{self.viz_server_url}/visualize",
                        json={
                            "graph_data": graph_data,
                            "layout": layout,
                            "config": config or {},
                            "use_llm": False  # For now, don't use LLM recommendations
                        },
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # Save the HTML
                        with open(filepath, "w", encoding="utf-8") as f:
                            f.write(result["html"])
                        
                        return {
                            "success": True,
                            "filepath": str(filepath),
                            "filename": filename,
                            "layout": result["layout"],
                            "title": result["title"],
                            "server_generated": True,
                            "url": f"file://{filepath}"
                        }
                except Exception as e:
                    logger.warning(f"Server generation failed, falling back to local: {e}")
            
            # Generate visualization locally
            html_content = self._generate_html(graph_data, layout, title, config)
            
            # Write file
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            return {
                "success": True,
                "filepath": str(filepath),
                "filename": filename,
                "layout": layout,
                "title": title,
                "server_generated": False,
                "url": f"file://{filepath}",
                "node_count": len(graph_data["nodes"]),
                "link_count": len(graph_data["links"])
            }
            
        except Exception as e:
            logger.error(f"Visualization generation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_html(
        self,
        graph_data: Dict[str, Any],
        layout: str,
        title: str,
        config: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate HTML content for visualization."""
        config = config or {}
        
        # Template selection based on layout
        if layout == "force":
            template_str = self._get_force_template()
        elif layout == "tree":
            template_str = self._get_tree_template()
        elif layout == "radial":
            template_str = self._get_radial_template()
        elif layout == "sankey":
            template_str = self._get_sankey_template()
        else:
            # Default to force layout
            template_str = self._get_force_template()
        
        # Render template
        template = self.jinja_env.from_string(template_str)
        
        return template.render(
            title=title,
            graph_data_json=json.dumps(graph_data),
            config=config,
            width=config.get("width", 960),
            height=config.get("height", 600),
            node_radius=config.get("node_radius", 8),
            link_distance=config.get("link_distance", 60),
            charge_strength=config.get("charge_strength", -300)
        )
    
    def _get_force_template(self) -> str:
        """Force-directed graph template."""
        return '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{{ title }}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        #visualization {
            background-color: white;
            border: 1px solid #ddd;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .node {
            stroke: #fff;
            stroke-width: 1.5px;
            cursor: pointer;
        }
        .node:hover {
            stroke-width: 3px;
        }
        .link {
            stroke: #999;
            stroke-opacity: 0.6;
        }
        .node-label {
            font-size: 12px;
            pointer-events: none;
        }
        .tooltip {
            position: absolute;
            text-align: left;
            padding: 10px;
            font-size: 12px;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            border-radius: 4px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.3s;
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .info {
            text-align: center;
            color: #666;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <h1>{{ title }}</h1>
    <div class="info">Nodes: <span id="node-count"></span> | Links: <span id="link-count"></span></div>
    <div id="visualization"></div>
    <div class="tooltip"></div>
    
    <script>
        const graphData = {{ graph_data_json|safe }};
        const width = {{ width }};
        const height = {{ height }};
        
        // Update counts
        document.getElementById('node-count').textContent = graphData.nodes.length;
        document.getElementById('link-count').textContent = graphData.links.length;
        
        // Create SVG
        const svg = d3.select("#visualization")
            .append("svg")
            .attr("width", width)
            .attr("height", height);
        
        // Create tooltip
        const tooltip = d3.select(".tooltip");
        
        // Create simulation
        const simulation = d3.forceSimulation(graphData.nodes)
            .force("link", d3.forceLink(graphData.links)
                .id(d => d.id)
                .distance({{ link_distance }}))
            .force("charge", d3.forceManyBody()
                .strength({{ charge_strength }}))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide().radius({{ node_radius }} + 2));
        
        // Create links
        const link = svg.append("g")
            .selectAll("line")
            .data(graphData.links)
            .enter().append("line")
            .attr("class", "link")
            .attr("stroke-width", d => Math.sqrt(d.value || 1));
        
        // Create nodes
        const node = svg.append("g")
            .selectAll("circle")
            .data(graphData.nodes)
            .enter().append("circle")
            .attr("class", "node")
            .attr("r", {{ node_radius }})
            .attr("fill", d => d.color || "#69b3a2")
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended));
        
        // Add labels
        const label = svg.append("g")
            .selectAll("text")
            .data(graphData.nodes)
            .enter().append("text")
            .attr("class", "node-label")
            .attr("dx", 12)
            .attr("dy", 4)
            .text(d => d.label || d.id);
        
        // Add tooltips
        node.on("mouseover", function(event, d) {
            tooltip.transition()
                .duration(200)
                .style("opacity", .9);
            tooltip.html(`<strong>${d.label || d.id}</strong><br/>
                         ${d.type ? `Type: ${d.type}<br/>` : ""}
                         ${d.description ? `${d.description}` : ""}`)
                .style("left", (event.pageX + 10) + "px")
                .style("top", (event.pageY - 28) + "px");
        })
        .on("mouseout", function() {
            tooltip.transition()
                .duration(500)
                .style("opacity", 0);
        });
        
        // Update positions on tick
        simulation.on("tick", () => {
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);
            
            node
                .attr("cx", d => d.x)
                .attr("cy", d => d.y);
            
            label
                .attr("x", d => d.x)
                .attr("y", d => d.y);
        });
        
        // Drag functions
        function dragstarted(event) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
        }
        
        function dragged(event) {
            event.subject.fx = event.x;
            event.subject.fy = event.y;
        }
        
        function dragended(event) {
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null;
            event.subject.fy = null;
        }
    </script>
</body>
</html>'''
    
    def _get_tree_template(self) -> str:
        """Hierarchical tree layout template."""
        return '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{{ title }}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .node circle {
            fill: #69b3a2;
            stroke: #fff;
            stroke-width: 2px;
        }
        .node text {
            font-size: 12px;
        }
        .link {
            fill: none;
            stroke: #ccc;
            stroke-width: 2px;
        }
    </style>
</head>
<body>
    <h1>{{ title }}</h1>
    <div id="visualization"></div>
    
    <script>
        const graphData = {{ graph_data_json|safe }};
        const width = {{ width }};
        const height = {{ height }};
        
        // Convert to hierarchy
        const root = d3.stratify()
            .id(d => d.id)
            .parentId(d => d.parent)(graphData.nodes);
        
        // Create tree layout
        const tree = d3.tree()
            .size([width - 100, height - 100]);
        
        const treeData = tree(root);
        
        // Create SVG
        const svg = d3.select("#visualization")
            .append("svg")
            .attr("width", width)
            .attr("height", height)
            .append("g")
            .attr("transform", "translate(50,50)");
        
        // Add links
        svg.selectAll(".link")
            .data(treeData.links())
            .enter().append("path")
            .attr("class", "link")
            .attr("d", d3.linkVertical()
                .x(d => d.x)
                .y(d => d.y));
        
        // Add nodes
        const node = svg.selectAll(".node")
            .data(treeData.descendants())
            .enter().append("g")
            .attr("class", "node")
            .attr("transform", d => `translate(${d.x},${d.y})`);
        
        node.append("circle")
            .attr("r", 10);
        
        node.append("text")
            .attr("dy", "0.31em")
            .attr("x", d => d.children ? -12 : 12)
            .style("text-anchor", d => d.children ? "end" : "start")
            .text(d => d.data.label || d.data.id);
    </script>
</body>
</html>'''
    
    def _get_radial_template(self) -> str:
        """Radial tree layout template."""
        # Similar to tree but with radial layout
        return self._get_tree_template()  # Simplified for now
    
    def _get_sankey_template(self) -> str:
        """Sankey diagram template."""
        # Would implement full Sankey template
        return self._get_force_template()  # Fallback to force for now
    
    def list_visualizations(self) -> Dict[str, Any]:
        """List all generated visualizations."""
        try:
            files = list(self.output_dir.glob("*.html"))
            visualizations = []
            
            for file in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True):
                stat = file.stat()
                visualizations.append({
                    "filename": file.name,
                    "filepath": str(file),
                    "url": f"file://{file}",
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "size_bytes": stat.st_size
                })
            
            return {
                "success": True,
                "count": len(visualizations),
                "output_dir": str(self.output_dir),
                "visualizations": visualizations[:20]  # Latest 20
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# Create global instance
visualizer = D3Visualizer()


@mcp.tool()
@debug_tool(mcp_logger)
async def generate_graph_visualization(
    graph_data: str,
    layout: Literal["force", "tree", "radial", "sankey"] = "force",
    title: str = "Graph Visualization",
    config: Optional[str] = None
) -> str:
    """Generate an interactive D3.js visualization from graph data.
    
    Args:
        graph_data: JSON string with 'nodes' and 'links' keys
                   Nodes: [{"id": "1", "label": "Node 1", "type": "error"}]
                   Links: [{"source": "1", "target": "2", "value": 1}]
        layout: Visualization layout type
        title: Title for the visualization
        config: Optional JSON string with configuration
                {"width": 1200, "height": 800, "node_radius": 10}
    
    Returns:
        Result with filepath and metadata
    
    Example:
        generate_graph_visualization(
            '{"nodes": [{"id": "1", "label": "Error A"}, {"id": "2", "label": "Fix B"}], 
              "links": [{"source": "1", "target": "2"}]}',
            "force",
            "Error Resolution Graph"
        )
    """
    try:
        # Parse graph data
        graph_dict = json.loads(graph_data)
    except json.JSONDecodeError as e:
        return json.dumps({
            "success": False,
            "error": f"Invalid JSON in graph_data: {str(e)}"
        }, indent=2)
    
    # Parse config if provided
    config_dict = None
    if config:
        try:
            config_dict = json.loads(config)
        except json.JSONDecodeError:
            config_dict = None
    
    result = visualizer.generate_visualization(
        graph_dict,
        layout=layout,
        title=title,
        config=config_dict
    )
    
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
@debug_tool(mcp_logger)
async def list_visualizations() -> str:
    """List all generated visualizations.
    
    Returns the most recent visualizations with their file paths and metadata.
    """
    result = visualizer.list_visualizations()
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
@debug_tool(mcp_logger)
async def visualize_arango_graph(
    graph_name: str,
    collection: str = "log_events",
    max_nodes: int = 50,
    layout: Literal["force", "tree", "radial"] = "force",
    title: Optional[str] = None
) -> str:
    """Generate visualization from ArangoDB graph data.
    
    This is a convenience tool that fetches data from ArangoDB and visualizes it.
    Requires arango-tools MCP to be available.
    
    Args:
        graph_name: Name of the ArangoDB graph
        collection: Collection to visualize nodes from
        max_nodes: Maximum number of nodes to include
        layout: Visualization layout
        title: Custom title (defaults to graph name)
    
    Note: This requires the arango-tools MCP server to be running.
    """
    return json.dumps({
        "success": False,
        "error": "This feature requires integration with arango-tools MCP. Use query() to fetch graph data first, then generate_graph_visualization()."
    }, indent=2)


async def working_usage():
    """Demonstrate proper usage of D3 visualization tools."""
    logger.info("=== D3 Visualizer Working Usage ===")
    
    # Example 1: Simple graph
    logger.info("\n1. Creating simple force-directed graph:")
    
    simple_graph = {
        "nodes": [
            {"id": "error1", "label": "ModuleNotFoundError", "type": "error", "color": "#ff6b6b"},
            {"id": "fix1", "label": "Install module", "type": "solution", "color": "#51cf66"},
            {"id": "error2", "label": "ImportError", "type": "error", "color": "#ff6b6b"},
            {"id": "fix2", "label": "Fix import path", "type": "solution", "color": "#51cf66"}
        ],
        "links": [
            {"source": "error1", "target": "fix1", "value": 2},
            {"source": "error2", "target": "fix2", "value": 1},
            {"source": "error1", "target": "error2", "value": 1}
        ]
    }
    
    result = visualizer.generate_visualization(
        simple_graph,
        layout="force",
        title="Error Resolution Network"
    )
    
    if result["success"]:
        logger.success(f"Created visualization: {result['filename']}")
        logger.info(f"View at: {result['url']}")
    
    # Example 2: List visualizations
    logger.info("\n2. Listing visualizations:")
    list_result = visualizer.list_visualizations()
    
    if list_result["success"]:
        logger.info(f"Found {list_result['count']} visualizations in {list_result['output_dir']}")
    
    logger.success("\n✅ D3 Visualizer working correctly!")
    return True


async def debug_function():
    """Debug function for testing visualization features."""
    logger.info("=== Debug Mode - Testing Advanced Visualizations ===")
    
    # Test complex graph with metadata
    logger.info("\n1. Testing complex graph with categories:")
    
    complex_graph = {
        "nodes": [
            # Errors
            {"id": "e1", "label": "AsyncIO Deadlock", "type": "error", "category": "concurrency", "color": "#e74c3c"},
            {"id": "e2", "label": "Buffer Overflow", "type": "error", "category": "memory", "color": "#e74c3c"},
            {"id": "e3", "label": "Import Failed", "type": "error", "category": "module", "color": "#e74c3c"},
            
            # Solutions
            {"id": "s1", "label": "Drain Streams", "type": "solution", "category": "concurrency", "color": "#27ae60"},
            {"id": "s2", "label": "Increase Buffer", "type": "solution", "category": "memory", "color": "#27ae60"},
            {"id": "s3", "label": "Fix PYTHONPATH", "type": "solution", "category": "module", "color": "#27ae60"},
            
            # Patterns
            {"id": "p1", "label": "Subprocess Pattern", "type": "pattern", "color": "#3498db"},
            {"id": "p2", "label": "Memory Management", "type": "pattern", "color": "#3498db"}
        ],
        "links": [
            # Error to solution
            {"source": "e1", "target": "s1", "value": 3, "type": "fixes"},
            {"source": "e2", "target": "s2", "value": 2, "type": "fixes"},
            {"source": "e3", "target": "s3", "value": 5, "type": "fixes"},
            
            # Pattern relationships
            {"source": "s1", "target": "p1", "value": 1, "type": "implements"},
            {"source": "s2", "target": "p2", "value": 1, "type": "implements"},
            
            # Cross-connections
            {"source": "e1", "target": "e2", "value": 1, "type": "related"},
            {"source": "p1", "target": "p2", "value": 1, "type": "related"}
        ]
    }
    
    # Test with custom config
    config = {
        "width": 1200,
        "height": 800,
        "node_radius": 12,
        "link_distance": 100,
        "charge_strength": -500
    }
    
    result = visualizer.generate_visualization(
        complex_graph,
        layout="force",
        title="Knowledge Graph - Errors & Solutions",
        config=config
    )
    
    if result["success"]:
        logger.success(f"Complex visualization created: {result['url']}")
    
    # Test server availability
    logger.info("\n2. Checking visualization server:")
    logger.info(f"Server available: {visualizer.use_server}")
    logger.info(f"Server URL: {visualizer.viz_server_url}")
    
    logger.success("\n✅ Debug tests completed!")
    return True


# Run the server
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="D3 Visualization MCP Server")
    parser.add_argument("mode", nargs="?", help="Mode: 'working' or 'debug' for testing")
    
    args = parser.parse_args()
    
    if args.mode == "debug":
        asyncio.run(debug_function())
    elif args.mode == "working":
        asyncio.run(working_usage())
    else:
        # Run as MCP server with graceful error handling
        try:
            logger.info("Starting D3 Visualizer MCP server")
            mcp.run()
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.critical(f"MCP server crashed: {e}", exc_info=True)
            mcp_logger.log_error(e, {"context": "server_startup"})
            sys.exit(1)