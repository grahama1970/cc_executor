Of course. Here is the first round of critique and iteration on the provided files. I've focused on iterative changes that improve robustness, reduce code duplication, and fix latent issues without introducing unnecessary complexity.

---

## Round 1: Critique and Iteration

### Critiquing `src/cc_executor/servers/mcp_d3_visualizer.py`

This server is well-structured with a `D3Visualizer` class and clear separation of concerns between general-purpose and "intelligent" visualization. However, it has some areas for improvement.

*   **Incomplete Features:** Several visualization methods (`_get_radial_template`, `_get_sankey_template`, etc.) are placeholders that fall back to the force layout. This can be misleading. It's better to implement them or clearly indicate they are not supported.
*   **Template Management:** The HTML/JS templates are embedded as large, multi-line strings. This makes them difficult to read, maintain, and edit. The "clustered" layout template, for example, duplicates a lot of HTML/CSS from the basic force layout.
*   **Inconsistent Configuration:** The `config` dictionary is passed around but not consistently used. The advanced `_generate_clustered_force_layout` ignores it and derives dimensions from the window, while the basic template uses it for width, height, etc.
*   **Stubbed Tool:** The `visualize_arango_graph` tool is a stub that always returns an error. The error message could be more helpful by guiding the user on how to achieve their goal using other available tools.

### Iteration on `src/cc_executor/servers/mcp_d3_visualizer.py`

I will now provide an iterated version of the file that addresses the critique. The key changes are:

1.  **Implement a Placeholder:** I've implemented a basic but functional `_generate_adjacency_matrix` to replace one of the placeholders. This is a valuable alternative for dense graphs, which the analysis logic already identifies.
2.  **Refactor Templates:** I've introduced a simple base template (`_get_base_template`) and refactored the force layout to inject its specific JavaScript. This demonstrates a pattern to reduce duplication.
3.  **Improve `visualize_arango_graph`:** The error message now provides a helpful, actionable example for the user.
4.  **Consolidate Logic:** The `_should_use_table` logic has been slightly simplified to rely more on the upstream `analysis` dictionary.

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "fastmcp",
#     "python-dotenv",
#     "loguru",
#     "httpx",
#     "jinja2",
#     "mcp-logger-utils>=0.1.5"
# ]
# ///

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Literal
import uuid
from textwrap import dedent

from fastmcp import FastMCP
from functools import wraps
from loguru import logger
from dotenv import load_dotenv, find_dotenv
from jinja2 import Environment, BaseLoader
import httpx

# Import from mcp-logger-utils package
from mcp_logger_utils import MCPLogger, debug_tool

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

        # Lazy load server availability
        self.viz_server_url = os.getenv("VIZ_SERVER_URL", "http://localhost:8000")
        self._server_checked = False
        self._use_server = False

        # Initialize Jinja2 for template rendering
        self.jinja_env = Environment(loader=BaseLoader(), autoescape=True)

        logger.info(f"D3 Visualizer initialized. Output dir: {self.output_dir}")

    def analyze_data_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the data to determine best visualization approach."""
        analysis = {
            "data_type": "unknown",
            "recommended_viz": [],
            "key_metrics": {},
            "patterns": [],
            "warnings": [],
            "visualization_complexity": "low",  # low, medium, high, excessive
            "alternative_representations": []
        }

        # Check if it's graph data
        if "nodes" in data and "links" in data:
            analysis["data_type"] = "graph"
            num_nodes = len(data["nodes"])
            num_links = len(data["links"])

            # Calculate graph metrics
            density = num_links / (num_nodes * (num_nodes - 1)) if num_nodes > 1 else 0
            avg_degree = (2 * num_links / num_nodes) if num_nodes > 0 else 0

            analysis["key_metrics"] = {
                "node_count": num_nodes,
                "link_count": num_links,
                "density": f"{density:.3f}",
                "avg_degree": f"{avg_degree:.2f}",
                "node_types": len(set(n.get("type", n.get("category", "default")) for n in data["nodes"])),
                "link_types": len(set(l.get("type", "default") for l in data["links"])),
                "has_weights": any(l.get("value") or l.get("weight") for l in data["links"]),
                "has_labels": any(n.get("label") for n in data["nodes"])
            }

            # Determine visualization complexity
            if num_nodes > 500 or density > 0.5:
                analysis["visualization_complexity"] = "excessive"
                analysis["warnings"].append("Graph too large or dense for effective visualization.")
                analysis["alternative_representations"].extend(["table", "adjacency_matrix"])
            elif num_nodes > 200 or density > 0.3:
                analysis["visualization_complexity"] = "high"
                analysis["warnings"].append("Consider filtered or aggregated view.")
            elif num_nodes > 50:
                analysis["visualization_complexity"] = "medium"

            # Recommend visualizations based on specific criteria
            if analysis["visualization_complexity"] == "excessive":
                analysis["recommended_viz"] = ["table", "summary_stats"]
            else:
                # Matrix for dense graphs
                if density > 0.3 or (density > 0.2 and num_nodes > 50):
                    analysis["recommended_viz"].append("matrix")
                    analysis["alternative_representations"].append("heatmap")

                # Bipartite layout detection
                if self._detect_bipartite_structure(data):
                    analysis["patterns"].append("bipartite")
                    # Sankey is great for bipartite flows
                    analysis["recommended_viz"].insert(0, "sankey")

                # Force layouts for sparse graphs
                if density < 0.2 and num_nodes < 200:
                    if analysis["key_metrics"]["node_types"] > 1:
                        analysis["recommended_viz"].insert(0, "force-clustered")
                    else:
                        analysis["recommended_viz"].insert(0, "force")

            # Detect patterns
            if any(n.get("timestamp") for n in data["nodes"]):
                analysis["patterns"].append("temporal")
                if len(set(n.get("timestamp") for n in data["nodes"] if n.get("timestamp"))) > 3:
                    # timeline-network is a specialized, complex view
                    analysis["alternative_representations"].append("timeline-network")
                analysis["alternative_representations"].append("timeline")

            if any(n.get("category") for n in data["nodes"]):
                analysis["patterns"].append("categorical")
                # Grouped force is a good default for categorical data
                if "force-clustered" not in analysis["recommended_viz"]:
                    analysis["recommended_viz"].append("grouped-force")

        # Check if it's time series data
        elif "series" in data or "timeline" in data:
            analysis["data_type"] = "timeseries"
            analysis["recommended_viz"].extend(["timeline", "stream", "horizon"])

        # Check if it's hierarchical data
        elif any(key in str(data) for key in ["children", "parent", "_children"]):
            analysis["data_type"] = "hierarchical"
            analysis["recommended_viz"].extend(["tree", "treemap", "sunburst", "circle-pack"])

        # Default to force if no recommendations
        if not analysis["recommended_viz"]:
            analysis["recommended_viz"].append("force")

        return analysis

    @property
    def use_server(self) -> bool:
        """Lazy check if visualization server is available."""
        if not self._server_checked:
            try:
                # Add a specific health check endpoint for clarity
                response = httpx.get(f"{self.viz_server_url}/health", timeout=2.0)
                self._use_server = response.status_code == 200
            except httpx.RequestError:
                self._use_server = False
            self._server_checked = True
            logger.info(f"Visualization server: {'Available' if self._use_server else 'Not available'}")
        return self._use_server

    def _check_server_availability(self) -> bool:
        """Check if visualization server is running."""
        try:
            response = httpx.get(f"{self.viz_server_url}/health", timeout=2.0)
            return response.status_code == 200
        except httpx.RequestError:
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
            layout: Layout type (force, tree, radial, sankey, matrix)
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
            config = config or {}

            # If server is available, use it for advanced features
            if self.use_server:
                try:
                    response = httpx.post(
                        f"{self.viz_server_url}/visualize",
                        json={
                            "graph_data": graph_data,
                            "layout": layout,
                            "config": config,
                            "use_llm": False
                        },
                        timeout=30.0
                    )

                    if response.status_code == 200:
                        result = response.json()
                        filepath.write_text(result["html"], encoding="utf-8")

                        return {
                            "success": True,
                            "filepath": str(filepath),
                            "filename": filename,
                            "layout": result["layout"],
                            "title": result["title"],
                            "server_generated": True,
                            "url": f"file://{filepath}"
                        }
                    else:
                         logger.warning(f"Server generation returned status {response.status_code}, falling back to local.")

                except Exception as e:
                    logger.warning(f"Server generation failed, falling back to local: {e}")

            # Generate visualization locally
            html_content = self._generate_html(graph_data, layout, title, config)
            filepath.write_text(html_content, encoding="utf-8")

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
            logger.error(f"Visualization generation failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    # ... (generate_intelligent_visualization remains largely the same)
    def generate_intelligent_visualization(
        self,
        data: Dict[str, Any],
        title: str = "Intelligent Visualization",
        analysis_goal: Optional[str] = None,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate an intelligent visualization based on data analysis.
        
        This method analyzes the data and creates a custom visualization
        that best represents the patterns and relationships found.
        """
        try:
            # Analyze data structure
            analysis = self.analyze_data_structure(data)
            
            # Adjust recommendations based on analysis goal
            if analysis_goal:
                if "cluster" in analysis_goal.lower():
                    analysis["recommended_viz"].insert(0, "force-clustered")
                elif "time" in analysis_goal.lower() or "timeline" in analysis_goal.lower():
                    analysis["recommended_viz"].insert(0, "timeline-network")
                elif "dense" in analysis_goal.lower() or "matrix" in analysis_goal.lower():
                    analysis["recommended_viz"].insert(0, "matrix")
                elif "hierarchy" in analysis_goal.lower() or "tree" in analysis_goal.lower():
                    analysis["recommended_viz"].insert(0, "tree")
            
            # Check if we should use a table instead
            if self._should_use_table(data, analysis):
                viz_type = "table"
                html_content = self._generate_table_view(data, analysis, title, user_preferences)
            else:
                # Get the best visualization type
                viz_type = analysis["recommended_viz"][0] if analysis["recommended_viz"] else "force"
                
                # Generate appropriate visualization
                if viz_type == "force-clustered":
                    html_content = self._generate_clustered_force_layout(data, analysis, title, user_preferences)
                elif viz_type == "timeline-network":
                    html_content = self._generate_timeline_network(data, analysis, title, user_preferences)
                elif viz_type == "matrix":
                    html_content = self._generate_adjacency_matrix(data, analysis, title, user_preferences)
                elif viz_type == "tree":
                    html_content = self._generate_enhanced_tree_layout(data, analysis, title, user_preferences)
                elif viz_type == "table" or viz_type == "summary_stats":
                    html_content = self._generate_table_view(data, analysis, title, user_preferences)
                else:
                    # Use enhanced force layout as default
                    config = user_preferences or {}
                    html_content = self._generate_enhanced_force_layout(data, viz_type, title, config)
            
            # Save visualization
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{viz_type}_{timestamp}_{uuid.uuid4().hex[:8]}.html"
            filepath = self.output_dir / filename
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            return {
                "success": True,
                "filepath": str(filepath),
                "filename": filename,
                "url": f"file://{filepath}",
                "analysis": analysis,
                "visualization_type": viz_type,
                "title": title,
                "node_count": len(data.get("nodes", [])),
                "link_count": len(data.get("links", [])),
                "features": self._get_viz_features(viz_type)
            }
            
        except Exception as e:
            logger.error(f"Intelligent visualization generation failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    # ... (rest of generate_intelligent_visualization)

    def _get_viz_features(self, viz_type: str) -> List[str]:
        """Get features for a visualization type."""
        base_features = ["interactive", "responsive", "tooltips", "zoom-pan"]
        
        type_features = {
            "force-clustered": ["auto-clustering", "hull-visualization", "force-controls"],
            "timeline-network": ["temporal-layout", "time-scrubbing", "event-highlights"],
            "matrix": ["sortable", "cell-highlighting", "pattern-detection"],
            "tree": ["collapsible", "path-highlighting", "depth-control"]
        }
        
        return base_features + type_features.get(viz_type, [])
    
    def _detect_bipartite_structure(self, data: Dict[str, Any]) -> bool:
        """Detect if the graph has a bipartite structure using a more robust type check."""
        if not data.get("nodes") or not data.get("links"):
            return False

        # Use a more robust check for node type/category
        def get_node_group(node):
            return node.get("type") or node.get("category")

        node_groups = {get_node_group(n) for n in data["nodes"] if get_node_group(n)}
        
        # If we have exactly 2 types/categories, check if links go between them
        if len(node_groups) == 2:
            group_list = list(node_groups)
            node_map = {n["id"]: get_node_group(n) for n in data["nodes"]}
            
            # Check if most links connect between the two groups
            cross_links = 0
            for link in data["links"]:
                source_id = link["source"]["id"] if isinstance(link["source"], dict) else link["source"]
                target_id = link["target"]["id"] if isinstance(link["target"], dict) else link["target"]
                
                source_group = node_map.get(source_id)
                target_group = node_map.get(target_id)
                
                if source_group and target_group and source_group != target_group:
                    cross_links += 1
            
            # If a high percentage of links are cross-links, it's likely bipartite
            return cross_links / len(data["links"]) > 0.9 if data["links"] else False
        
        return False

    def _should_use_table(self, data: Dict[str, Any], analysis: Dict[str, Any]) -> bool:
        """Determine if data should be displayed as a table instead of visualization."""
        if analysis["visualization_complexity"] == "excessive":
            return True

        if "nodes" in data and not data.get("links"):
             # If it's just a list of items without relationships
            return True

        # If nodes have many attributes that need to be compared
        if data.get("nodes"):
            sample_node = data["nodes"][0] if data["nodes"] else {}
            if len(sample_node.keys()) > 10:  # Many attributes to show
                return True

        return False

    def _generate_html(
        self,
        graph_data: Dict[str, Any],
        layout: str,
        title: str,
        config: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate HTML content for visualization."""
        config = config or {}
        
        template_map = {
            "force": self._get_force_template,
            "tree": self._get_tree_template,
            "radial": self._get_radial_template,
            "sankey": self._get_sankey_template,
            "matrix": self._get_matrix_template,
        }
        
        # Default to force layout if the requested layout is not found
        template_func = template_map.get(layout, self._get_force_template)
        template_str = template_func()
        
        # Render template
        template = self.jinja_env.from_string(template_str)
        
        return template.render(
            title=title,
            graph_data_json=json.dumps(graph_data),
            config_json=json.dumps(config), # Pass the whole config object
            width=config.get("width", 960),
            height=config.get("height", 600),
        )
        
    def _get_base_template(self) -> str:
        """A base HTML template with placeholders for styles and scripts."""
        return dedent('''\
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{{ title }}</title>
            <script src="https://d3js.org/d3.v7.min.js"></script>
            <style>
                body {
                    font-family: Arial, sans-serif; margin: 0; padding: 20px;
                    background-color: #f5f5f5;
                }
                #visualization {
                    background-color: white; border: 1px solid #ddd;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .tooltip {
                    position: absolute; text-align: left; padding: 10px;
                    font-size: 12px; background: rgba(0, 0, 0, 0.8);
                    color: white; border-radius: 4px; pointer-events: none;
                    opacity: 0; transition: opacity 0.3s;
                }
                h1 { color: #333; text-align: center; }
                .info { text-align: center; color: #666; margin-bottom: 20px; }
                {% block styles %}{% endblock %}
            </style>
        </head>
        <body>
            <h1>{{ title }}</h1>
            <div class="info">Nodes: <span id="node-count"></span> | Links: <span id="link-count"></span></div>
            <div id="visualization"></div>
            <div class="tooltip"></div>
            
            <script>
                const graphData = {{ graph_data_json|safe }};
                const config = {{ config_json|safe }};
                const width = config.width || {{ width }};
                const height = config.height || {{ height }};
                
                document.getElementById('node-count').textContent = graphData.nodes.length;
                document.getElementById('link-count').textContent = graphData.links.length;
                
                const svg = d3.select("#visualization")
                    .append("svg")
                    .attr("width", width)
                    .attr("height", height);
                
                const tooltip = d3.select(".tooltip");
                
                {% block script %}{% endblock %}
            </script>
        </body>
        </html>''')

    def _get_force_template(self) -> str:
        """Force-directed graph template, extending the base."""
        base_template = self._get_base_template()
        force_styles = dedent('''\
            .node { stroke: #fff; stroke-width: 1.5px; cursor: pointer; }
            .node:hover { stroke-width: 3px; }
            .link { stroke: #999; stroke-opacity: 0.6; }
            .node-label { font-size: 12px; pointer-events: none; }
        ''')
        force_script = dedent('''\
            const linkDistance = config.link_distance || 60;
            const chargeStrength = config.charge_strength || -300;
            const nodeRadius = config.node_radius || 8;

            const simulation = d3.forceSimulation(graphData.nodes)
                .force("link", d3.forceLink(graphData.links).id(d => d.id).distance(linkDistance))
                .force("charge", d3.forceManyBody().strength(chargeStrength))
                .force("center", d3.forceCenter(width / 2, height / 2))
                .force("collision", d3.forceCollide().radius(nodeRadius + 2));
            
            const link = svg.append("g").selectAll("line").data(graphData.links)
                .enter().append("line").attr("class", "link")
                .attr("stroke-width", d => Math.sqrt(d.value || 1));
            
            const node = svg.append("g").selectAll("circle").data(graphData.nodes)
                .enter().append("circle").attr("class", "node")
                .attr("r", nodeRadius).attr("fill", d => d.color || "#69b3a2")
                .call(d3.drag().on("start", dragstarted).on("drag", dragged).on("end", dragended));
            
            const label = svg.append("g").selectAll("text").data(graphData.nodes)
                .enter().append("text").attr("class", "node-label")
                .attr("dx", 12).attr("dy", 4).text(d => d.label || d.id);
            
            node.on("mouseover", (event, d) => {
                tooltip.transition().duration(200).style("opacity", .9);
                tooltip.html(`<strong>${d.label || d.id}</strong><br/>` +
                             `${d.type ? `Type: ${d.type}<br/>` : ""}` +
                             `${d.description ? `${d.description}` : ""}`)
                    .style("left", (event.pageX + 10) + "px")
                    .style("top", (event.pageY - 28) + "px");
            }).on("mouseout", () => {
                tooltip.transition().duration(500).style("opacity", 0);
            });
            
            simulation.on("tick", () => {
                link.attr("x1", d => d.source.x).attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
                node.attr("cx", d => d.x).attr("cy", d => d.y);
                label.attr("x", d => d.x).attr("y", d => d.y);
            });
            
            function dragstarted(event) {
                if (!event.active) simulation.alphaTarget(0.3).restart();
                event.subject.fx = event.subject.x;
                event.subject.fy = event.subject.y;
            }
            function dragged(event) { event.subject.fx = event.x; event.subject.fy = event.y; }
            function dragended(event) {
                if (!event.active) simulation.alphaTarget(0);
                event.subject.fx = null;
                event.subject.fy = null;
            }
        ''')
        return base_template.replace("{% block styles %}", force_styles).replace("{% block script %}", force_script)

    # ... (_get_tree_template remains similar, can be refactored later)

    def _get_radial_template(self) -> str:
        """Radial tree layout template."""
        logger.warning("Radial layout not fully implemented, falling back to tree layout.")
        return self._get_tree_template()

    def _get_sankey_template(self) -> str:
        """Sankey diagram template."""
        logger.warning("Sankey layout not fully implemented, falling back to force layout.")
        return self._get_force_template()
        
    def _get_matrix_template(self) -> str:
        """Adjacency matrix template. Good for dense graphs."""
        base_template = self._get_base_template()
        matrix_styles = dedent('''\
            .grid { stroke: #ccc; stroke-width: 1px; }
            .cell { stroke: #fff; stroke-width: 0.5px; }
            .cell:hover { stroke: #000; stroke-width: 2px; }
        ''')
        matrix_script = dedent('''\
            const nodes = graphData.nodes;
            const links = graphData.links;
            const nodeMap = new Map(nodes.map((d, i) => [d.id, i]));
            
            const matrix = nodes.map(() => nodes.map(() => ({ value: 0 })));
            links.forEach(link => {
                const sourceIdx = nodeMap.get(link.source.id || link.source);
                const targetIdx = nodeMap.get(link.target.id || link.target);
                if (sourceIdx !== undefined && targetIdx !== undefined) {
                    matrix[sourceIdx][targetIdx].value = link.value || 1;
                    matrix[targetIdx][sourceIdx].value = link.value || 1; // Assuming undirected
                }
            });

            const margin = { top: 80, right: 0, bottom: 10, left: 80 };
            const vizWidth = width - margin.left - margin.right;
            const vizHeight = height - margin.top - margin.bottom;

            const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);
            
            const x = d3.scaleBand().range([0, vizWidth]).domain(d3.range(nodes.length)).padding(0.05);
            const y = d3.scaleBand().range([0, vizHeight]).domain(d3.range(nodes.length)).padding(0.05);
            
            const color = d3.scaleSequential(d3.interpolateBlues).domain([0, d3.max(links, l => l.value) || 1]);
            
            g.selectAll(".row")
                .data(matrix).enter().append("g")
                .attr("class", "row")
                .attr("transform", (d, i) => `translate(0, ${y(i)})`)
                .selectAll(".cell")
                .data(d => d).enter().append("rect")
                .attr("class", "cell")
                .attr("x", (d, i) => x(i))
                .attr("width", x.bandwidth())
                .attr("height", y.bandwidth())
                .style("fill", d => color(d.value));

            // Add labels
            g.append("g").call(d3.axisTop(x).tickFormat(i => nodes[i].label || nodes[i].id))
                .selectAll("text").attr("transform", "rotate(-90)").style("text-anchor", "start");
            g.append("g").call(d3.axisLeft(y).tickFormat(i => nodes[i].label || nodes[i].id));
        ''')
        return base_template.replace("{% block styles %}", matrix_styles).replace("{% block script %}", matrix_script)
    
    # ... (_generate_clustered_force_layout and other generators remain)
    def _generate_enhanced_force_layout(self, data: Dict[str, Any], layout: str, title: str, config: Dict[str, Any]) -> str:
        """Enhanced force layout with better defaults and features."""
        # Use the existing force template but with enhanced configuration
        return self._generate_html(data, layout, title, config)
    
    def _generate_clustered_force_layout(self, data: Dict[str, Any], analysis: Dict[str, Any], title: str, config: Optional[Dict[str, Any]] = None) -> str:
        """Generate a force layout with automatic clustering."""
        template = '''<!DOCTYPE html>...''' # (template content omitted for brevity)
        
        return self.jinja_env.from_string(template).render(
            title=title,
            subtitle=f"Nodes: {analysis['key_metrics']['node_count']} | Links: {analysis['key_metrics']['link_count']} | Clusters: {analysis['key_metrics']['node_types']}",
            data_json=json.dumps(data),
            analysis_json=json.dumps(analysis)
        )
    
    def _generate_timeline_network(self, data: Dict[str, Any], analysis: Dict[str, Any], title: str, config: Optional[Dict[str, Any]] = None) -> str:
        """Generate a network visualization with timeline component."""
        # For now, use clustered force as a placeholder
        logger.warning("Timeline network not implemented, falling back to clustered force layout.")
        return self._generate_clustered_force_layout(data, analysis, title, config)
    
    def _generate_adjacency_matrix(self, data: Dict[str, Any], analysis: Dict[str, Any], title: str, config: Optional[Dict[str, Any]] = None) -> str:
        """Generate an adjacency matrix visualization for dense graphs."""
        return self._generate_html(data, "matrix", title, config)

    # ... (rest of class)

# ... (MCP tool definitions remain largely the same, but with one change)

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
    suggestion = dedent(f"""
    {{
        "success": false,
        "error": "This tool requires chaining commands. First, get the data from ArangoDB, then pass it to the visualizer.",
        "suggestion": "Try running these commands in sequence:",
        "example_steps": [
            "arango-tools.query('FOR v, e, p IN 1..2 OUTBOUND \\"nodes/{collection}\\" GRAPH \\"{graph_name}\\" LIMIT {max_nodes} RETURN {{nodes: p.vertices, links: p.edges}}')",
            "d3-visualizer.generate_intelligent_visualization(graph_data=<output_from_previous_step>)"
        ]
    }}
    """)
    return suggestion

# ... (rest of file)
```

---

### Critiquing `src/cc_executor/servers/mcp_d3_visualization_advisor.py`

This advisor is a powerful tool, leveraging pandas for deep data analysis. The quality of its recommendations is high.

*   **Brittleness:** The analysis functions (`_is_bipartite`, `_is_hierarchical`) make assumptions about the data structure (e.g., expecting a `type` key) that are less flexible than the `visualizer`'s own analysis.
*   **Latent Bug:** The `_get_tabular_recommendations` function references a `col_types` variable that is not defined within its scope, which will cause a `NameError`.
*   **Analysis Inconsistency:** The pandas analysis code uses `pd.to_numeric(..., errors='raise')` inside a `try/except` block. It's safer and more idiomatic to use `errors='coerce'`, which automatically handles non-numeric values by converting them to `NaN`, preventing the analysis from crashing on dirty data.
*   **Redundant Logic:** There is significant overlap in the data analysis logic between this file and the `visualizer`. For example, both calculate density and detect patterns. Consolidating this would be ideal, but a good first step is to ensure they are consistent.

### Iteration on `src/cc_executor/servers/mcp_d3_visualization_advisor.py`

I will now provide an iterated version of the file that addresses the critique. The key changes are:

1.  **Fix `NameError` Bug:** I've corrected the reference to `col_types`, using the `pandas_analysis` dictionary instead, which correctly holds the column type information.
2.  **Improve Analysis Robustness:** The graph analysis functions (`_is_bipartite`, `_has_temporal_data`) now check for multiple common key names (e.g., `type` or `category`).
3.  **Safer Pandas Parsing:** I've switched the pandas type conversion to use `errors='coerce'` to gracefully handle bad data without crashing.
4.  **Enhanced Recommendations:** I've added a recommendation for the "Clustered Force Layout" to better align with the capabilities of the `visualizer`.

```python
#!/usr/bin/env python3
"""MCP D3 Visualization Advisor

This MCP server analyzes data using pandas and returns comprehensive guidance prompts
that tell agents exactly when to use which visualization type.
"""

import json
from typing import Dict, Any, Optional, List, Literal, Union
from datetime import datetime
from pathlib import Path
from fastmcp import FastMCP, Context
from loguru import logger
import sys
import pandas as pd
import numpy as np
from io import StringIO

# Setup logging
logger.remove()
logger.add(sys.stderr, level="INFO")

# Initialize MCP server
mcp = FastMCP("d3-visualization-advisor")

@mcp.tool()
async def analyze_and_recommend_visualization(
    data: str,
    purpose: Optional[str] = None,
    constraints: Optional[str] = None
) -> str:
    """Analyze data and return comprehensive visualization recommendations.
    
    This tool examines your data structure and returns a detailed guide
    explaining which D3.js visualizations to use and why.
    
    Args:
        data: JSON string of the data to visualize
        purpose: What insight you're trying to show (optional)
        constraints: Any constraints like max dimensions, style preferences (optional)
    
    Returns:
        Comprehensive markdown guide with specific recommendations
    """
    try:
        data_obj = json.loads(data)
        constraints_obj = json.loads(constraints) if constraints else {}
        
        # Analyze the data
        analysis = _analyze_data_structure(data_obj)
        
        # Generate comprehensive guide
        guide = _generate_visualization_guide(analysis, data_obj, purpose, constraints_obj)
        
        return guide
        
    except json.JSONDecodeError as e:
        return f"Error parsing JSON: {str(e)}"
    except Exception as e:
        logger.error(f"Error analyzing data: {e}", exc_info=True)
        return f"Error: {str(e)}"


def _analyze_data_structure(data: Any) -> Dict[str, Any]:
    """Perform comprehensive data analysis using pandas."""
    analysis = {
        "shape": {},
        "metrics": {},
        "patterns": [],
        "issues": [],
        "pandas_analysis": {},
        "data_quality": {},
        "statistical_summary": {}
    }
    
    # Network/Graph data analysis
    nodes, links = [], []
    is_network = False
    if isinstance(data, dict) and "nodes" in data and "links" in data:
        # D3.js format
        nodes = data.get("nodes", [])
        links = data.get("links", [])
        analysis["shape"] = {"type": "network", "format": "d3"}
        is_network = True

    elif isinstance(data, list) and data and all(isinstance(item, dict) for item in data):
        # Check for ArangoDB edge format (_from, _to fields)
        if all({"_from", "_to"}.issubset(item.keys()) for item in data[:5]):
            analysis["shape"] = {"type": "network", "format": "arangodb_edges"}
            analysis["patterns"].append("arangodb_graph")
            nodes_set = set()
            for edge in data:
                # Handle both full ID and simple ID
                source = str(edge.get("_from", "")).split("/")[-1]
                target = str(edge.get("_to", "")).split("/")[-1]
                nodes_set.add(source)
                nodes_set.add(target)
                links.append({"source": source, "target": target, **{k: v for k, v in edge.items() if k not in ["_from", "_to", "_id", "_key", "_rev"]}})
            nodes = [{"id": node_id} for node_id in nodes_set]
            analysis["shape"]["edge_count"] = len(links)
            is_network = True
    
    if is_network:
        analysis["shape"]["node_count"] = len(nodes)
        analysis["shape"]["link_count"] = len(links)
        
        if len(nodes) > 1:
            analysis["metrics"]["density"] = len(links) / (len(nodes) * (len(nodes) - 1))
        else:
            analysis["metrics"]["density"] = 0
            
        if _is_bipartite(nodes, links): analysis["patterns"].append("bipartite")
        if _has_temporal_data(nodes): analysis["patterns"].append("temporal")
        if _is_hierarchical(nodes, links): analysis["patterns"].append("hierarchical")
        if all("value" in l or "weight" in l for l in links): analysis["patterns"].append("weighted_flow")
            
        if len(nodes) > 500: analysis["issues"].append("high_node_count")
        if analysis["metrics"].get("density", 0) > 0.5: analysis["issues"].append("too_dense")
            
    # Tabular data analysis
    elif isinstance(data, list) and data and all(isinstance(item, dict) for item in data):
        analysis["shape"] = {"type": "tabular", "row_count": len(data), "columns": list(data[0].keys())}
        df = pd.DataFrame(data)
        analysis["pandas_analysis"] = _perform_pandas_analysis(df)
        analysis["data_quality"] = _analyze_data_quality(df)
        analysis["statistical_summary"] = _get_statistical_summary(df)
        analysis["patterns"].extend(_detect_patterns_from_pandas(df, analysis["pandas_analysis"]))
                
        if len(data) > 1000: analysis["issues"].append("large_dataset")
        if len(data) < 3: analysis["issues"].append("too_few_rows")
                
    # Hierarchical data
    elif isinstance(data, dict) and ("children" in data or "name" in data and "parent" in data):
        analysis["shape"] = {"type": "hierarchical", "depth": _calculate_tree_depth(data), "leaf_count": _count_leaves(data)}
        if analysis["shape"]["depth"] > 5: analysis["issues"].append("deep_hierarchy")
            
    else:
        analysis["shape"]["type"] = "unknown"
        
    return analysis

# ... (_generate_visualization_guide remains the same)

def _get_network_recommendations(analysis: Dict, data: Dict) -> str:
    """Generate network-specific recommendations."""
    
    # ... (code before this point is the same)
    
    # Primary recommendation
    if 'high_node_count' in analysis['issues']:
        rec += """### 🚫 DO NOT USE: Force-Directed Graph ...""" # (omitted for brevity)
    elif 'bipartite' in patterns:
        rec += """### ✅ RECOMMENDED: Sankey Diagram ...""" # (omitted for brevity)
    elif analysis.get('metrics', {}).get('density', 0) > 0.3:
        rec += """### 🚫 DO NOT USE: Standard Force Layout ...""" # (omitted for brevity)
    else:
        # Good for standard force layout
        node_count = analysis['shape'].get('node_count', 0)
        density = analysis['metrics'].get('density', 0)
        rec += f"""### ✅ RECOMMENDED: Force-Directed Graph
**Why**: With {node_count} nodes and {density:.1%} density, this will create a readable, explorable visualization.

**Enhancements**:
- **Clustering**: If you have categories (like `type` or `category` on nodes), use a **Clustered Force Layout**. This groups related nodes visually and is highly recommended.
- **Color**: Use color to represent node types.
- **Size**: Use size to represent node importance (e.g., number of connections).

**Best practices**:
```javascript
// Adaptive parameters based on data
const simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links)
        .distance(d => 30 * Math.sqrt(100 / Math.max(1, nodes.length))))
    .force("charge", d3.forceManyBody()
        .strength(-30 * Math.max(1, 50 / Math.max(1, nodes.length))))
    .force("collision", d3.forceCollide().radius(d => (d.radius || 5) + 2));

// Add clustering for categories
if (hasCategories) {{
    simulation.force("cluster", forceCluster()); // See visualizer's clustered layout for implementation
}}
```
"""
    # ... (rest of function is the same)
    return rec

def _get_tabular_recommendations(analysis: Dict, data: List) -> str:
    """Generate tabular data recommendations based on pandas analysis."""
    row_count = analysis['shape']['row_count']
    patterns = analysis['patterns']
    pandas_analysis = analysis.get('pandas_analysis', {})
    
    rec = "## Tabular Data Visualization Recommendations\n\n"
    
    if 'too_few_rows' in analysis['issues']:
        rec += f"""### 🚫 DO NOT USE: Any Chart ...""" # (omitted)
        
    elif 'time_series' in patterns:
        rec += """### ✅ RECOMMENDED: Line Chart ...""" # (omitted)
        
    # **FIXED BUG HERE**: Changed `col_types` to `pandas_analysis`
    elif pandas_analysis.get('categorical_columns') and pandas_analysis.get('numeric_columns'):
        rec += """### ✅ RECOMMENDED: Bar Chart
**Why**: You have categories and values - ideal for comparison.

**When to use**:
```
// Heuristic
const categoricalCols = {len(pandas_analysis.get('categorical_columns', []))};
const numericCols = {len(pandas_analysis.get('numeric_columns', []))};
if (categoricalCols >= 1 && numericCols >= 1) {{
    return "bar_chart";
}}
```

**Variations**:
- **Grouped bars** - Multiple values per category
- **Stacked bars** - Show composition
- **Horizontal bars** - Long category names

**D3 Implementation**: ...
"""
        
    elif 'multivariate' in patterns:
        rec += """### ✅ RECOMMENDED: Scatter Plot ...""" # (omitted)
        
    if row_count > 100:
        rec += f"""
### 📊 Large Dataset Considerations
With {row_count} rows, consider: ...
"""
        
    return rec
    
# ... (_get_hierarchical_recommendations, _get_general_recommendations, etc. remain the same)


def _perform_pandas_analysis(df: pd.DataFrame) -> Dict[str, Any]:
    """Perform comprehensive pandas analysis on the dataframe."""
    analysis = { ... } # (omitted)
    
    # Analyze each column
    for col in df.columns:
        analysis["dtypes"][col] = str(df[col].dtype)
        
        # Try to infer better types
        if df[col].dtype == 'object':
            # **FIX**: Use errors='coerce' for safer parsing
            numeric_col = pd.to_numeric(df[col], errors='coerce')
            if numeric_col.notna().sum() / df[col].notna().sum() > 0.8: # If >80% parse as numeric
                analysis["numeric_columns"].append(col)
                df[col] = numeric_col
            else:
                datetime_col = pd.to_datetime(df[col], errors='coerce')
                if datetime_col.notna().sum() / df[col].notna().sum() > 0.8: # If >80% parse as datetime
                    analysis["temporal_columns"].append(col)
                    df[col] = datetime_col
                else:
                    analysis["categorical_columns"].append(col)
        elif np.issubdtype(df[col].dtype, np.number):
            analysis["numeric_columns"].append(col)
        elif np.issubdtype(df[col].dtype, np.datetime64):
            analysis["temporal_columns"].append(col)
        
        unique_count = df[col].nunique()
        analysis["unique_values"][col] = unique_count
        analysis["cardinality"][col] = unique_count / len(df) if len(df) > 0 else 0
    
    # ... (rest of function remains the same)
    return analysis

# ... (_analyze_data_quality, _get_statistical_summary, etc. remain the same)

# Helper functions
def _is_bipartite(nodes: List[Dict], links: List[Dict]) -> bool:
    """Check if graph has bipartite structure."""
    if not nodes or not links:
        return False
        
    def get_node_group(node):
        return node.get("type") or node.get("category")

    groups = {get_node_group(n) for n in nodes if get_node_group(n)}
    if len(groups) != 2:
        return False
        
    node_map = {n["id"]: get_node_group(n) for n in nodes}
    for link in links:
        source_group = node_map.get(str(link.get("source")))
        target_group = node_map.get(str(link.get("target")))
        if source_group and target_group and source_group == target_group:
            return False # Link within the same group
            
    return True


def _has_temporal_data(nodes: List[Dict]) -> bool:
    """Check if nodes contain temporal data."""
    temporal_keys = ["timestamp", "time", "date", "datetime", "created_at", "updated_at"]
    return any(any(key in node for key in temporal_keys) for node in nodes)

# ... (rest of file)
```

---
## Round 2: Critique and Iteration

The first round of changes has improved the robustness and consistency of both servers. Now, let's focus on scalability, maintainability, and making the tools even more user-friendly.

### Critiquing `src/cc_executor/servers/mcp_d3_visualizer.py` (Post-Round 1)

*   **Template Management:** Using `_get_base_template` and string replacement is a step up, but it's still cumbersome. The standard and most maintainable approach for Jinja2 is to load templates from the filesystem. This separates the presentation (HTML/JS) from the logic (Python) completely.
*   **Dispatch Logic:** The `generate_intelligent_visualization` method has a growing `if/elif` chain to map a visualization type string to its generation function. As more visualizations are added, this will become unwieldy. A dispatch dictionary is a cleaner, more scalable pattern.
*   **Server Fallback Ambiguity:** The fallback from the remote visualization server is resilient, but it hides the reason for the failure. Logging the specific exception is good, but the caller of the tool receives no information about *why* the generation was local instead of remote.

### Iteration on `src/cc_executor/servers/mcp_d3_visualizer.py` (Round 2)

I will now provide an iterated version of the file that addresses the Round 2 critique.

**Key Changes:**

1.  **Filesystem Template Loading:** I will refactor the class to load Jinja2 templates from a `templates` subdirectory. This requires creating a small directory structure and template files.
2.  **Dispatch Dictionary:** The `if/elif` block in `generate_intelligent_visualization` is replaced with a dictionary mapping `viz_type` to the appropriate generation method, making the code cleaner and easier to extend.
3.  **Clearer Fallback Information:** When the remote server call fails, a `fallback_reason` is now added to the returned dictionary to provide more context to the user or calling agent.

*(To implement this, imagine a `templates` directory next to the script)*

**`templates/base.html`**
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{{ title }}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body { font-family: sans-serif; margin: 20px; background-color: #f9f9f9; }
        #visualization { background-color: white; border: 1px solid #ccc; }
        .tooltip { position: absolute; padding: 8px; background: #333; color: white; border-radius: 4px; pointer-events: none; opacity: 0; }
        h1 { text-align: center; }
        .info { text-align: center; color: #666; margin-bottom: 1em; }
        {% block styles %}{% endblock %}
    </style>
</head>
<body>
    <h1>{{ title }}</h1>
    <div class="info">Nodes: <span id="node-count">0</span> | Links: <span id="link-count">0</span></div>
    <div id="visualization"></div>
    <div class="tooltip"></div>
    <script>
        const graphData = {{ graph_data_json|safe }};
        const config = {{ config_json|safe }};
        const width = config.width || 960;
        const height = config.height || 600;

        document.getElementById('node-count').textContent = graphData.nodes.length;
        document.getElementById('link-count').textContent = graphData.links.length;

        const svg = d3.select("#visualization").append("svg")
            .attr("viewBox", `0 0 ${width} ${height}`)
            .attr("width", "100%")
            .attr("height", "auto");

        const tooltip = d3.select(".tooltip");
        const g = svg.append("g");

        // Add zoom/pan
        svg.call(d3.zoom().on("zoom", (event) => {
            g.attr("transform", event.transform);
        }));

        {% block script %}{% endblock %}
    </script>
</body>
</html>
```

**`templates/force.js`**
```javascript
{% block script %}
const linkDistance = config.link_distance || 80;
const chargeStrength = config.charge_strength || -400;
const nodeRadius = config.node_radius || 10;

const simulation = d3.forceSimulation(graphData.nodes)
    .force("link", d3.forceLink(graphData.links).id(d => d.id).distance(linkDistance))
    .force("charge", d3.forceManyBody().strength(chargeStrength))
    .force("center", d3.forceCenter(width / 2, height / 2));

const link = g.append("g")
    .attr("stroke", "#999").attr("stroke-opacity", 0.6)
    .selectAll("line").data(graphData.links).join("line")
    .attr("stroke-width", d => Math.sqrt(d.value || 1));

const node = g.append("g")
    .attr("stroke", "#fff").attr("stroke-width", 1.5)
    .selectAll("circle").data(graphData.nodes).join("circle")
    .attr("r", nodeRadius).attr("fill", d => d.color || "#1f77b4")
    .call(drag(simulation));

node.append("title").text(d => d.label || d.id);

simulation.on("tick", () => {
    link.attr("x1", d => d.source.x).attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
    node.attr("cx", d => d.x).attr("cy", d => d.y);
});

function drag(simulation) {
    function dragstarted(event) { if (!event.active) simulation.alphaTarget(0.3).restart(); event.subject.fx = event.subject.x; event.subject.fy = event.subject.y; }
    function dragged(event) { event.subject.fx = event.x; event.subject.fy = event.y; }
    function dragended(event) { if (!event.active) simulation.alphaTarget(0); event.subject.fx = null; event.subject.fy = null; }
    return d3.drag().on("start", dragstarted).on("drag", dragged).on("end", dragended);
}
{% endblock %}
```
*(Similar `.js` and `.css` files would be created for other layouts)*

**Updated `mcp_d3_visualizer.py`:**

```python
# ... (imports)
from jinja2 import Environment, FileSystemLoader

# ... (init)

class D3Visualizer:
    def __init__(self):
        # ...
        # **CHANGE**: Use FileSystemLoader
        template_dir = Path(__file__).parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir), 
            autoescape=True
        )
        # ...

    def generate_visualization(self, ...) -> Dict[str, Any]:
        # ...
        fallback_reason = None
        if self.use_server:
            try:
                # ... (server call)
            except Exception as e:
                fallback_reason = f"Server call failed: {e}"
                logger.warning(f"Server generation failed, falling back to local. Reason: {fallback_reason}")
        
        # ... (local generation)
        
        result = {
            "success": True,
            "filepath": str(filepath),
            # ...
            "server_generated": False,
            "url": f"file://{filepath}",
        }
        if fallback_reason:
            result["fallback_reason"] = fallback_reason
        return result

    def generate_intelligent_visualization(self, ...) -> Dict[str, Any]:
        try:
            # ... (analysis)

            # **CHANGE**: Use a dispatch dictionary
            viz_generators = {
                "table": self._generate_table_view,
                "summary_stats": self._generate_table_view,
                "force-clustered": self._generate_clustered_force_layout,
                "timeline-network": self._generate_timeline_network,
                "matrix": self._generate_adjacency_matrix,
                "tree": self._generate_enhanced_tree_layout,
                "force": self._generate_enhanced_force_layout
            }

            if self._should_use_table(data, analysis):
                viz_type = "table"
            else:
                viz_type = analysis["recommended_viz"][0] if analysis["recommended_viz"] else "force"

            generator_func = viz_generators.get(viz_type, self._generate_enhanced_force_layout)
            
            # For functions that don't take analysis/prefs, we prepare a wrapper or adjust call
            if viz_type in ["force", "matrix", "tree"]:
                 html_content = generator_func(data, viz_type, title, user_preferences or {})
            else:
                 html_content = generator_func(data, analysis, title, user_preferences)
            
            # ... (save and return)
        # ... (exception handling)
    
    def _generate_html(self, ...) -> str:
        # **CHANGE**: Load from file
        template = self.jinja_env.get_template("base.html")
        
        # We can pass script/style content as variables to the base template
        # For simplicity here, I'll just show the concept for one template
        script_template = self.jinja_env.get_template(f"{layout}.js")
        script_content = script_template.render(config=config)
        
        return template.render(
            title=title,
            graph_data_json=json.dumps(graph_data),
            config_json=json.dumps(config or {}),
            script_block=script_content,
        )
# ... (rest of file)
```

---

### Critiquing `src/cc_executor/servers/mcp_d3_visualization_advisor.py` (Post-Round 1)

*   **Input Flexibility:** The tool only accepts JSON strings. Data analysts frequently work with CSV. Forcing them to convert large CSVs to JSON first is an unnecessary hurdle. The tool could be more useful if it handled CSV input directly.
*   **Monolithic Functions:** The `_analyze_data_structure` and `_generate_visualization_guide` functions are very large. Breaking them down would improve readability and make them easier to test and maintain.
*   **Guide Generation:** The guide is built using a series of f-strings. This is functional but brittle. A small change in formatting requires careful editing of Python strings. Using a template engine (like Jinja2, which is already a dependency in the other server) would be a much cleaner solution.
*   **Actionable Insights:** The pandas analysis is excellent at identifying issues like high-cardinality columns but doesn't suggest a solution. The advice could be more proactive.

### Iteration on `src/cc_executor/servers/mcp_d3_visualization_advisor.py` (Round 2)

I will now provide an iterated version of the file that addresses the Round 2 critique.

**Key Changes:**
1.  **CSV Input Support:** The main tool function now attempts to parse the input as JSON, and if that fails, it tries to read it as a CSV. This makes the tool more versatile.
2.  **Refactor with Jinja2:** The guide generation logic is refactored to use a Jinja2 template, making the guide's structure much easier to manage.
3.  **Decomposed Analysis:** The main analysis function is broken down into smaller, type-specific helpers.
4.  **More Actionable Advice:** The analysis for high-cardinality categorical columns now includes a specific recommendation to group infrequent values into an "Other" category.

*(Imagine a `advisor_templates/guide.md` file)*
```markdown
# D3.js Visualization Recommendation Guide

## Your Data Analysis
**Data Shape**: {{ analysis.shape.type }}
**Key Metrics**: {{ analysis.metrics | tojson(indent=2) }}
**Detected Patterns**: {{ analysis.patterns | join(', ') if analysis.patterns else 'None' }}
**Potential Issues**: {{ analysis.issues | join(', ') if analysis.issues else 'None' }}
**Purpose**: {{ purpose or 'General visualization' }}

{% if analysis.get('pandas_analysis') %}
{{ render_pandas_analysis(analysis.pandas_analysis, analysis.data_quality, analysis.statistical_summary) }}
{% endif %}

{% if analysis.shape.type == 'network' %}
{{ render_network_recommendations(analysis, data) }}
{% elif analysis.shape.type == 'tabular' %}
{{ render_tabular_recommendations(analysis, data) }}
{% elif analysis.shape.type == 'hierarchical' %}
{{ render_hierarchical_recommendations(analysis, data) }}
{% else %}
{{ render_general_recommendations(analysis) }}
{% endif %}

## Quick Decision Flowchart
...
```

**Updated `mcp_d3_visualization_advisor.py`:**
```python
# ... (imports)
from jinja2 import Environment, FileSystemLoader

# ... (init)
template_dir = Path(__file__).parent / "advisor_templates"
jinja_env = Environment(loader=FileSystemLoader(template_dir))

def _format_pandas_analysis_for_template(pandas_analysis, ...):
    # This function would now return a dictionary of formatted strings
    # to be rendered by the Jinja2 template, rather than one big string.
    return {"overview": "...", "quality_issues": "..."}

jinja_env.globals['render_pandas_analysis'] = _format_pandas_analysis_for_template
# ... register other render helpers

@mcp.tool()
async def analyze_and_recommend_visualization(
    data: str,
    #...
) -> str:
    """..."""
    try:
        data_obj = None
        data_format = "json"
        try:
            data_obj = json.loads(data)
        except json.JSONDecodeError:
            # **CHANGE**: Add CSV fallback
            try:
                data_obj = pd.read_csv(StringIO(data)).to_dict(orient='records')
                data_format = "csv"
                logger.info("Detected and parsed CSV data.")
            except Exception as csv_error:
                return f"Error: Input is not valid JSON and could not be parsed as CSV. CSV Error: {csv_error}"

        constraints_obj = json.loads(constraints) if constraints else {}
        analysis = _analyze_data_structure(data_obj)
        analysis['data_format'] = data_format

        # **CHANGE**: Use Jinja2 template
        template = jinja_env.get_template("guide.md")
        return template.render(
            analysis=analysis,
            data=data_obj,
            purpose=purpose,
            constraints=constraints_obj
        )
    # ... (exception handling)

def _analyze_data_structure(data: Any) -> Dict[str, Any]:
    # **CHANGE**: Decomposed logic
    if isinstance(data, dict) and "nodes" in data and "links" in data:
        return _analyze_network_data(data)
    elif isinstance(data, list) and data and all(isinstance(item, dict) for item in data):
        # Could be network (arango) or tabular
        if all({"_from", "_to"}.issubset(item.keys()) for item in data[:5]):
             return _analyze_network_data(data, format="arangodb_edges")
        else:
             return _analyze_tabular_data(data)
    elif isinstance(data, dict) and "children" in data:
        return _analyze_hierarchical_data(data)
    else:
        return {"shape": {"type": "unknown"}, "issues": ["Unrecognized data structure"]}

# ... Implement _analyze_network_data, _analyze_tabular_data, etc.

def _get_statistical_summary(df: pd.DataFrame) -> Dict[str, Any]:
    summary = { ... }
    # ...
    # **CHANGE**: More actionable advice
    if len(categorical_cols) > 0:
        summary["categorical_summary"] = { ... }
        for col, unique_count in summary["categorical_summary"]["unique_counts"].items():
            if unique_count > 20 and unique_count / len(df) < 0.5: # High but not an ID
                 summary["overall_patterns"].append(
                    f"Column '{col}' has high cardinality ({unique_count} unique values). "
                    "Consider grouping infrequent values into an 'Other' category before visualizing."
                )

    # ...
    return summary
```