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
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Literal
import uuid
from textwrap import dedent

from fastmcp import FastMCP
from functools import wraps
from loguru import logger

# Import standardized response utilities
sys.path.insert(0, str(Path(__file__).parent))
from utils.response_utils import create_success_response, create_error_response
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
        
        # Initialize Jinja2 for template rendering with auto-escaping
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
                "density": density,
                "avg_degree": avg_degree,
                "node_types": len(set(n.get("type", "default") for n in data["nodes"])),
                "link_types": len(set(l.get("type", "default") for l in data["links"])),
                "has_weights": any(l.get("value") or l.get("weight") for l in data["links"]),
                "has_labels": any(n.get("label") for n in data["nodes"])
            }
            
            # Determine visualization complexity
            if num_nodes > 500 or density > 0.5:
                analysis["visualization_complexity"] = "excessive"
                analysis["warnings"].append("Graph too large or dense for effective visualization")
                analysis["alternative_representations"].append("table")
                analysis["alternative_representations"].append("adjacency_matrix")
            elif num_nodes > 200 or density > 0.3:
                analysis["visualization_complexity"] = "high"
                analysis["warnings"].append("Consider filtered or aggregated view")
            elif num_nodes > 50:
                analysis["visualization_complexity"] = "medium"
            
            # Recommend visualizations based on specific criteria
            if analysis["visualization_complexity"] == "excessive":
                analysis["recommended_viz"] = ["table", "summary_stats"]
            else:
                # Force layouts for sparse graphs
                if density < 0.1 and num_nodes < 100:
                    if analysis["key_metrics"]["node_types"] > 2:
                        analysis["recommended_viz"].append("force-clustered")
                    else:
                        analysis["recommended_viz"].append("force")
                
                # Matrix for dense graphs
                elif density > 0.3 or (density > 0.2 and num_nodes > 50):
                    analysis["recommended_viz"].append("matrix")
                    analysis["alternative_representations"].append("heatmap")
                
                # Bipartite layout detection
                if self._detect_bipartite_structure(data):
                    analysis["patterns"].append("bipartite")
                    analysis["recommended_viz"].insert(0, "bipartite")
                
            # Detect patterns
            if any(n.get("timestamp") for n in data["nodes"]):
                analysis["patterns"].append("temporal")
                if len(set(n.get("timestamp") for n in data["nodes"] if n.get("timestamp"))) > 3:
                    analysis["recommended_viz"].append("timeline-network")
                else:
                    analysis["alternative_representations"].append("timeline")
                
            if any(n.get("category") for n in data["nodes"]):
                analysis["patterns"].append("categorical")
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
    
    def select_optimal_layout(self, data: Dict[str, Any], analysis: Dict[str, Any], goal: Optional[str] = None) -> Dict[str, Any]:
        """Select the optimal layout based on data characteristics and analysis goal.
        
        Returns layout recommendation with configuration and rationale.
        """
        recommendation = {
            "layout": "force",
            "rationale": [],
            "configuration": {},
            "alternatives": [],
            "warnings": []
        }
        
        metrics = analysis.get("key_metrics", {})
        patterns = analysis.get("patterns", [])
        node_count = metrics.get("node_count", 0)
        link_count = metrics.get("link_count", 0)
        density = metrics.get("density", 0)
        
        # Decision tree for layout selection
        
        # 1. Check for specific patterns first
        if "bipartite" in patterns:
            recommendation["layout"] = "sankey"
            recommendation["rationale"].append("Bipartite structure detected - Sankey diagram shows flow between two sets")
            recommendation["configuration"] = {
                "node_width": 20,
                "node_padding": 10,
                "align": "justify"
            }
            recommendation["alternatives"].append("bipartite-force")
            
        elif "hierarchical" in patterns or metrics.get("is_tree", False):
            if node_count > 100:
                recommendation["layout"] = "radial-tree"
                recommendation["rationale"].append("Large tree structure - radial layout uses space efficiently")
            else:
                recommendation["layout"] = "tree"
                recommendation["rationale"].append("Hierarchical structure detected - tree layout shows parent-child relationships")
            recommendation["configuration"] = {
                "node_size": [10, 40],
                "separation": "(a, b) => (a.parent == b.parent ? 1 : 2) / a.depth"
            }
            
        elif "temporal" in patterns:
            recommendation["layout"] = "timeline-force"
            recommendation["rationale"].append("Temporal data detected - timeline layout shows evolution over time")
            recommendation["configuration"] = {
                "time_scale": "linear",
                "force_in_y_only": True
            }
            
        # 2. Check density and size constraints
        elif density > 0.5 or (density > 0.3 and node_count > 100):
            recommendation["layout"] = "matrix"
            recommendation["rationale"].append(f"High density ({density:.2f}) - matrix view prevents overlapping")
            recommendation["configuration"] = {
                "cell_size": max(4, min(20, 800 / node_count)),
                "sort_by": "degree"
            }
            recommendation["warnings"].append("Graph too dense for node-link visualization")
            
        elif node_count > 500:
            recommendation["layout"] = "clustered-canvas"
            recommendation["rationale"].append("Large graph - using Canvas renderer with clustering for performance")
            recommendation["configuration"] = {
                "renderer": "canvas",
                "cluster_threshold": 0.7,
                "aggregate_small_clusters": True
            }
            recommendation["warnings"].append("Consider filtering or sampling for better performance")
            
        # 3. Check for clustering patterns
        elif metrics.get("clustering_coefficient", 0) > 0.6 or "modular" in patterns:
            recommendation["layout"] = "force-clustered"
            recommendation["rationale"].append("High clustering coefficient - grouped layout shows communities")
            recommendation["configuration"] = {
                "cluster_strength": 0.5,
                "inter_cluster_strength": 0.1,
                "show_hulls": True
            }
            
        # 4. Default cases based on size
        elif node_count < 30 and density < 0.2:
            recommendation["layout"] = "force"
            recommendation["rationale"].append("Small sparse graph - standard force layout provides clarity")
            recommendation["configuration"] = {
                "charge": -300,
                "link_distance": 60,
                "collision_radius": 15
            }
            
        elif node_count < 100:
            recommendation["layout"] = "force-directed"
            recommendation["rationale"].append("Medium-sized graph - force layout with optimized parameters")
            recommendation["configuration"] = {
                "charge": -30 * max(1, 50 / node_count),
                "link_distance": 30 * (100 / node_count) ** 0.5,
                "velocity_decay": 0.4
            }
            
        else:
            recommendation["layout"] = "force-clustered"
            recommendation["rationale"].append("Default to clustered layout for better organization")
            
        # Add goal-specific adjustments
        if goal:
            goal_lower = goal.lower()
            if "error" in goal_lower and "flow" in goal_lower:
                recommendation["alternatives"].insert(0, "sankey")
                recommendation["rationale"].append("Goal mentions flow - consider Sankey diagram")
            elif "cluster" in goal_lower or "group" in goal_lower:
                if recommendation["layout"] != "force-clustered":
                    recommendation["alternatives"].insert(0, "force-clustered")
            elif "time" in goal_lower or "temporal" in goal_lower:
                if recommendation["layout"] != "timeline-force":
                    recommendation["alternatives"].insert(0, "timeline-force")
            elif "compare" in goal_lower or "matrix" in goal_lower:
                if recommendation["layout"] != "matrix":
                    recommendation["alternatives"].insert(0, "matrix")
                    
        # Add performance considerations
        if node_count > 200:
            recommendation["configuration"]["use_webgl"] = node_count > 1000
            recommendation["configuration"]["progressive_rendering"] = True
            recommendation["configuration"]["lod_threshold"] = 0.5  # Level of detail
            
        return recommendation
    
    @property
    def use_server(self) -> bool:
        """Lazy check if visualization server is available."""
        if not self._server_checked:
            self._use_server = self._check_server_availability()
            self._server_checked = True
            logger.info(f"Visualization server: {'Available' if self._use_server else 'Not available'}")
        return self._use_server
    
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
                return create_error_response(error="Graph data must contain 'nodes' and 'links' keys"
                )
            
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
                        
                        return create_success_response(data={"filepath": str(filepath),
                            "filename": filename,
                            "layout": result["layout"],
                            "title": result["title"],
                            "server_generated": True,
                            "url": f"file://{filepath})"
                        }
                except Exception as e:
                    logger.warning(f"Server generation failed, falling back to local: {e}")
            
            # Generate visualization locally
            html_content = self._generate_html(graph_data, layout, title, config)
            
            # Write file
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            return create_success_response(data={"filepath": str(filepath),
                "filename": filename,
                "layout": layout,
                "title": title,
                "server_generated": False,
                "url": f"file://{filepath})",
                "node_count": len(graph_data["nodes"]),
                "link_count": len(graph_data["links"])
            }
            
        except Exception as e:
            logger.error(f"Visualization generation failed: {e}")
            return {
                "error": str(e),
                "success": False
            }
    
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
            
            return create_success_response(data={"filepath": str(filepath),
                "filename": filename,
                "url": f"file://{filepath})",
                "analysis": analysis,
                "visualization_type": viz_type,
                "title": title,
                "node_count": len(data.get("nodes", [])),
                "link_count": len(data.get("links", [])),
                "features": self._get_viz_features(viz_type)
            }
            
        except Exception as e:
            logger.error(f"Intelligent visualization generation failed: {e}")
            return {
                "error": str(e),
                "success": False
            }
    
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
        """Detect if the graph has a bipartite structure."""
        if not data.get("nodes") or not data.get("links"):
            return False
        
        # Simple heuristic: check if nodes can be divided into two sets
        # where links only connect between sets, not within
        node_types = {}
        for node in data["nodes"]:
            node_type = node.get("type") or node.get("category")
            if node_type:
                if node_type not in node_types:
                    node_types[node_type] = []
                node_types[node_type].append(node["id"])
        
        # If we have exactly 2 types and links go between them
        if len(node_types) == 2:
            type_list = list(node_types.keys())
            set1 = set(node_types[type_list[0]])
            set2 = set(node_types[type_list[1]])
            
            # Check if all links connect between sets
            cross_links = 0
            for link in data["links"]:
                source_id = link["source"] if isinstance(link["source"], str) else link["source"]["id"]
                target_id = link["target"] if isinstance(link["target"], str) else link["target"]["id"]
                
                if (source_id in set1 and target_id in set2) or (source_id in set2 and target_id in set1):
                    cross_links += 1
            
            # If most links are cross-links, it's likely bipartite
            return cross_links > len(data["links"]) * 0.8
        
        return False
    
    def _should_use_table(self, data: Dict[str, Any], analysis: Dict[str, Any]) -> bool:
        """Determine if data should be displayed as a table instead of visualization."""
        # Check various conditions
        if analysis["visualization_complexity"] == "excessive":
            return True
        
        # If it's just a list of items without relationships
        if "nodes" in data and len(data.get("links", [])) == 0 and len(data["nodes"]) > 20:
            return True
        
        # If density is too high for meaningful visualization
        if analysis.get("key_metrics", {}).get("density", 0) > 0.7:
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
        
        # Template selection based on layout
        if layout == "force":
            template_str = self._get_force_template()
        elif layout == "tree":
            template_str = self._get_tree_template()
        elif layout == "radial":
            template_str = self._get_radial_template()
        elif layout == "sankey":
            template_str = self._get_sankey_template()
        elif layout == "matrix":
            template_str = self._get_matrix_template()
        elif layout == "timeline-force":
            template_str = self._get_timeline_force_template()
        elif layout == "force-clustered":
            template_str = self._get_force_clustered_template()
        elif layout == "clustered-canvas":
            template_str = self._get_clustered_canvas_template()
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
        return '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{{ title }}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script src="https://unpkg.com/d3-sankey@0.12.3/dist/d3-sankey.min.js"></script>
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
        .link {
            fill: none;
            stroke-opacity: 0.5;
        }
        .link:hover {
            stroke-opacity: 0.8;
        }
        .node rect {
            cursor: move;
            fill-opacity: 0.9;
            shape-rendering: crispEdges;
        }
        .node text {
            pointer-events: none;
            text-shadow: 0 1px 0 #fff;
            font-size: 12px;
        }
        .tooltip {
            position: absolute;
            padding: 10px;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            border-radius: 5px;
            pointer-events: none;
            opacity: 0;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <svg id="visualization" width="{{ width }}" height="{{ height }}"></svg>
    <div class="tooltip"></div>
    
    <script>
        const graphData = {{ graph_data_json }};
        const width = {{ width }};
        const height = {{ height }};
        const svg = d3.select("#visualization");
        const tooltip = d3.select(".tooltip");
        
        // Transform nodes and links for sankey
        const sankeyData = {
            nodes: graphData.nodes.map((n, i) => ({...n, index: i})),
            links: graphData.links.map(l => ({
                source: typeof l.source === 'object' ? l.source.index : graphData.nodes.findIndex(n => n.id === l.source),
                target: typeof l.target === 'object' ? l.target.index : graphData.nodes.findIndex(n => n.id === l.target),
                value: l.value || 1
            }))
        };
        
        const sankey = d3.sankey()
            .nodeWidth(15)
            .nodePadding(10)
            .extent([[10, 10], [width - 10, height - 10]]);
        
        const path = d3.sankeyLinkHorizontal();
        
        sankey(sankeyData);
        
        // Color scale
        const color = d3.scaleOrdinal(d3.schemeCategory10);
        
        // Links
        svg.append("g")
            .selectAll(".link")
            .data(sankeyData.links)
            .join("path")
            .attr("class", "link")
            .attr("d", path)
            .style("stroke", d => color(d.source.name))
            .style("stroke-width", d => Math.max(1, d.width))
            .on("mouseover", function(event, d) {
                tooltip.transition().duration(200).style("opacity", .9);
                tooltip.html(`${d.source.label || d.source.id} → ${d.target.label || d.target.id}<br/>Value: ${d.value}`)
                    .style("left", (event.pageX) + "px")
                    .style("top", (event.pageY - 28) + "px");
            })
            .on("mouseout", function() {
                tooltip.transition().duration(500).style("opacity", 0);
            });
        
        // Nodes
        const node = svg.append("g")
            .selectAll(".node")
            .data(sankeyData.nodes)
            .join("g")
            .attr("class", "node");
        
        node.append("rect")
            .attr("x", d => d.x0)
            .attr("y", d => d.y0)
            .attr("height", d => d.y1 - d.y0)
            .attr("width", d => d.x1 - d.x0)
            .style("fill", d => color(d.label || d.id))
            .style("stroke", "#000");
        
        node.append("text")
            .attr("x", d => d.x0 - 6)
            .attr("y", d => (d.y1 + d.y0) / 2)
            .attr("dy", "0.35em")
            .attr("text-anchor", "end")
            .text(d => d.label || d.id)
            .filter(d => d.x0 < width / 2)
            .attr("x", d => d.x1 + 6)
            .attr("text-anchor", "start");
    </script>
</body>
</html>'''
    
    def _get_matrix_template(self) -> str:
        """Matrix/adjacency view template for dense graphs."""
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
        .cell {
            stroke: #ccc;
            stroke-width: 0.5;
        }
        .label {
            font-size: 10px;
            fill: #333;
        }
        .tooltip {
            position: absolute;
            padding: 10px;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            border-radius: 5px;
            pointer-events: none;
            opacity: 0;
            font-size: 12px;
        }
        .row-highlight {
            fill: #ff7f0e;
            opacity: 0.3;
        }
        .col-highlight {
            fill: #1f77b4;
            opacity: 0.3;
        }
    </style>
</head>
<body>
    <svg id="visualization" width="{{ width }}" height="{{ height }}"></svg>
    <div class="tooltip"></div>
    
    <script>
        const graphData = {{ graph_data_json }};
        const width = {{ width }};
        const height = {{ height }};
        const margin = {top: 80, right: 80, bottom: 20, left: 80};
        const cellSize = {{ config.cell_size | default(10) }};
        
        const svg = d3.select("#visualization");
        const tooltip = d3.select(".tooltip");
        
        // Create adjacency matrix
        const matrix = [];
        const nodeMap = new Map();
        graphData.nodes.forEach((node, i) => {
            nodeMap.set(node.id, i);
            matrix[i] = new Array(graphData.nodes.length).fill(0);
        });
        
        graphData.links.forEach(link => {
            const source = typeof link.source === 'object' ? nodeMap.get(link.source.id) : nodeMap.get(link.source);
            const target = typeof link.target === 'object' ? nodeMap.get(link.target.id) : nodeMap.get(link.target);
            if (source !== undefined && target !== undefined) {
                matrix[source][target] = link.value || 1;
                matrix[target][source] = link.value || 1;  // Undirected
            }
        });
        
        // Sort nodes by degree
        const degrees = graphData.nodes.map((_, i) => matrix[i].reduce((a, b) => a + (b > 0 ? 1 : 0), 0));
        const sortedIndices = degrees.map((_, i) => i).sort((a, b) => degrees[b] - degrees[a]);
        
        // Color scale
        const colorScale = d3.scaleSequential(d3.interpolateBlues)
            .domain([0, d3.max(matrix.flat())]);
        
        const g = svg.append("g")
            .attr("transform", `translate(${margin.left},${margin.top})`);
        
        // Row highlights
        const rowHighlights = g.append("g")
            .selectAll(".row-highlight")
            .data(sortedIndices)
            .join("rect")
            .attr("class", "row-highlight")
            .attr("x", 0)
            .attr("y", (d, i) => i * cellSize)
            .attr("width", sortedIndices.length * cellSize)
            .attr("height", cellSize)
            .style("opacity", 0);
        
        // Column highlights
        const colHighlights = g.append("g")
            .selectAll(".col-highlight")
            .data(sortedIndices)
            .join("rect")
            .attr("class", "col-highlight")
            .attr("x", (d, i) => i * cellSize)
            .attr("y", 0)
            .attr("width", cellSize)
            .attr("height", sortedIndices.length * cellSize)
            .style("opacity", 0);
        
        // Cells
        const cells = g.append("g")
            .selectAll(".cell")
            .data(sortedIndices.flatMap((i, row) => 
                sortedIndices.map((j, col) => ({
                    row: row,
                    col: col,
                    sourceIdx: i,
                    targetIdx: j,
                    value: matrix[i][j]
                }))
            ))
            .join("rect")
            .attr("class", "cell")
            .attr("x", d => d.col * cellSize)
            .attr("y", d => d.row * cellSize)
            .attr("width", cellSize - 1)
            .attr("height", cellSize - 1)
            .style("fill", d => d.value > 0 ? colorScale(d.value) : "#fff")
            .on("mouseover", function(event, d) {
                if (d.value > 0) {
                    const sourceNode = graphData.nodes[d.sourceIdx];
                    const targetNode = graphData.nodes[d.targetIdx];
                    
                    tooltip.transition().duration(200).style("opacity", .9);
                    tooltip.html(`${sourceNode.label || sourceNode.id} ↔ ${targetNode.label || targetNode.id}<br/>Value: ${d.value}`)
                        .style("left", (event.pageX) + "px")
                        .style("top", (event.pageY - 28) + "px");
                    
                    // Highlight row and column
                    rowHighlights.filter((_, i) => i === d.row).style("opacity", 1);
                    colHighlights.filter((_, i) => i === d.col).style("opacity", 1);
                }
            })
            .on("mouseout", function() {
                tooltip.transition().duration(500).style("opacity", 0);
                rowHighlights.style("opacity", 0);
                colHighlights.style("opacity", 0);
            });
        
        // Labels
        g.append("g")
            .selectAll(".row-label")
            .data(sortedIndices)
            .join("text")
            .attr("class", "label")
            .attr("x", -5)
            .attr("y", (d, i) => i * cellSize + cellSize / 2)
            .attr("dy", "0.32em")
            .attr("text-anchor", "end")
            .text(d => graphData.nodes[d].label || graphData.nodes[d].id);
        
        g.append("g")
            .selectAll(".col-label")
            .data(sortedIndices)
            .join("text")
            .attr("class", "label")
            .attr("x", (d, i) => i * cellSize + cellSize / 2)
            .attr("y", -5)
            .attr("text-anchor", "start")
            .attr("transform", (d, i) => `rotate(-90,${i * cellSize + cellSize / 2},-5)`)
            .text(d => graphData.nodes[d].label || graphData.nodes[d].id);
    </script>
</body>
</html>'''
    
    def _get_timeline_force_template(self) -> str:
        """Timeline-force hybrid template for temporal data."""
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
            cursor: pointer;
        }
        .node circle {
            stroke: #fff;
            stroke-width: 2px;
        }
        .node text {
            font-size: 10px;
            pointer-events: none;
        }
        .link {
            stroke: #999;
            stroke-opacity: 0.6;
            stroke-width: 1.5px;
        }
        .axis {
            font-size: 12px;
        }
        .axis path,
        .axis line {
            fill: none;
            stroke: #000;
            shape-rendering: crispEdges;
        }
        .timeline-line {
            stroke: #ddd;
            stroke-width: 2;
        }
        .tooltip {
            position: absolute;
            padding: 10px;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            border-radius: 5px;
            pointer-events: none;
            opacity: 0;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <svg id="visualization" width="{{ width }}" height="{{ height }}"></svg>
    <div class="tooltip"></div>
    
    <script>
        const graphData = {{ graph_data_json }};
        const width = {{ width }};
        const height = {{ height }};
        const margin = {top: 40, right: 40, bottom: 60, left: 40};
        
        const svg = d3.select("#visualization");
        const tooltip = d3.select(".tooltip");
        
        // Extract temporal data (assume nodes have 'timestamp' property)
        const timeExtent = d3.extent(graphData.nodes, d => new Date(d.timestamp || Date.now()));
        const xScale = d3.scaleTime()
            .domain(timeExtent)
            .range([margin.left, width - margin.right]);
        
        // Y-axis uses force simulation
        const yCenter = height / 2;
        
        // Draw timeline
        svg.append("line")
            .attr("class", "timeline-line")
            .attr("x1", margin.left)
            .attr("y1", yCenter)
            .attr("x2", width - margin.right)
            .attr("y2", yCenter);
        
        // X-axis
        svg.append("g")
            .attr("class", "axis")
            .attr("transform", `translate(0,${height - margin.bottom})`)
            .call(d3.axisBottom(xScale).tickFormat(d3.timeFormat("%Y-%m-%d")));
        
        // Initialize node positions based on time
        graphData.nodes.forEach(d => {
            d.x = xScale(new Date(d.timestamp || Date.now()));
            d.y = yCenter;
            d.fx = d.x;  // Fix x position
        });
        
        // Create force simulation (only for y-axis)
        const simulation = d3.forceSimulation(graphData.nodes)
            .force("y", d3.forceY(yCenter).strength(0.1))
            .force("collide", d3.forceCollide({{ config.node_radius | default(8) }} + 2))
            .force("link", d3.forceLink(graphData.links)
                .id(d => d.id)
                .distance(30)
                .strength(0.3));
        
        // Links
        const link = svg.append("g")
            .selectAll(".link")
            .data(graphData.links)
            .join("line")
            .attr("class", "link");
        
        // Nodes
        const node = svg.append("g")
            .selectAll(".node")
            .data(graphData.nodes)
            .join("g")
            .attr("class", "node")
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended));
        
        node.append("circle")
            .attr("r", {{ config.node_radius | default(8) }})
            .style("fill", d => d3.schemeCategory10[d.type ? d.type % 10 : 0]);
        
        node.append("text")
            .attr("dx", 12)
            .attr("dy", "0.35em")
            .text(d => d.label || d.id);
        
        // Tooltip
        node.on("mouseover", function(event, d) {
            tooltip.transition().duration(200).style("opacity", .9);
            const timeStr = d.timestamp ? new Date(d.timestamp).toLocaleString() : "No timestamp";
            tooltip.html(`${d.label || d.id}<br/>Time: ${timeStr}<br/>Type: ${d.type || 'Unknown'}`)
                .style("left", (event.pageX) + "px")
                .style("top", (event.pageY - 28) + "px");
        })
        .on("mouseout", function() {
            tooltip.transition().duration(500).style("opacity", 0);
        });
        
        // Update positions
        simulation.on("tick", () => {
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);
            
            node.attr("transform", d => `translate(${d.x},${d.y})`);
        });
        
        function dragstarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fy = d.y;  // Only allow vertical dragging
        }
        
        function dragged(event, d) {
            d.fy = event.y;  // Only update y
        }
        
        function dragended(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fy = null;
        }
    </script>
</body>
</html>'''
    
    def _get_force_clustered_template(self) -> str:
        """Force layout with automatic clustering."""
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
            cursor: pointer;
        }
        .node circle {
            stroke: #fff;
            stroke-width: 2px;
        }
        .node text {
            font-size: 10px;
            pointer-events: none;
        }
        .link {
            stroke: #999;
            stroke-opacity: 0.6;
        }
        .cluster-hull {
            fill: none;
            stroke-width: 20px;
            stroke-linejoin: round;
            opacity: 0.2;
        }
        .tooltip {
            position: absolute;
            padding: 10px;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            border-radius: 5px;
            pointer-events: none;
            opacity: 0;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <svg id="visualization" width="{{ width }}" height="{{ height }}"></svg>
    <div class="tooltip"></div>
    
    <script>
        const graphData = {{ graph_data_json }};
        const width = {{ width }};
        const height = {{ height }};
        const svg = d3.select("#visualization");
        const tooltip = d3.select(".tooltip");
        
        // Detect clusters (simple community detection)
        function detectClusters(nodes, links) {
            // Initialize each node in its own cluster
            nodes.forEach((node, i) => {
                node.cluster = i;
            });
            
            // Simple clustering based on connections
            for (let i = 0; i < 5; i++) {  // 5 iterations
                links.forEach(link => {
                    const source = typeof link.source === 'object' ? link.source : nodes.find(n => n.id === link.source);
                    const target = typeof link.target === 'object' ? link.target : nodes.find(n => n.id === link.target);
                    
                    if (source && target && Math.random() > 0.5) {
                        target.cluster = source.cluster;
                    }
                });
            }
            
            // Consolidate cluster IDs
            const clusterMap = new Map();
            let clusterId = 0;
            nodes.forEach(node => {
                if (!clusterMap.has(node.cluster)) {
                    clusterMap.set(node.cluster, clusterId++);
                }
                node.cluster = clusterMap.get(node.cluster);
            });
            
            return d3.max(nodes, d => d.cluster) + 1;
        }
        
        const numClusters = detectClusters(graphData.nodes, graphData.links);
        const color = d3.scaleOrdinal(d3.schemeCategory10);
        
        // Create cluster centers
        const clusters = new Array(numClusters);
        const clusterCenters = d3.range(numClusters).map(i => ({
            x: Math.cos(i / numClusters * 2 * Math.PI) * 200 + width / 2,
            y: Math.sin(i / numClusters * 2 * Math.PI) * 200 + height / 2
        }));
        
        // Force simulation
        const simulation = d3.forceSimulation(graphData.nodes)
            .force("link", d3.forceLink(graphData.links)
                .id(d => d.id)
                .distance(30))
            .force("charge", d3.forceManyBody().strength(-100))
            .force("cluster", forceCluster())
            .force("collide", d3.forceCollide({{ config.node_radius | default(8) }} + 2))
            .force("center", d3.forceCenter(width / 2, height / 2));
        
        // Custom cluster force
        function forceCluster() {
            const strength = {{ config.cluster_strength | default(0.5) }};
            let nodes;
            
            function force(alpha) {
                nodes.forEach(node => {
                    const cluster = clusterCenters[node.cluster];
                    if (cluster) {
                        const k = strength * alpha;
                        node.vx -= (node.x - cluster.x) * k;
                        node.vy -= (node.y - cluster.y) * k;
                    }
                });
            }
            
            force.initialize = function(_) {
                nodes = _;
            };
            
            return force;
        }
        
        // Hull for clusters
        const hull = svg.append("g").attr("class", "hulls");
        
        // Links
        const link = svg.append("g")
            .selectAll(".link")
            .data(graphData.links)
            .join("line")
            .attr("class", "link")
            .style("stroke-width", d => Math.sqrt(d.value || 1));
        
        // Nodes
        const node = svg.append("g")
            .selectAll(".node")
            .data(graphData.nodes)
            .join("g")
            .attr("class", "node")
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended));
        
        node.append("circle")
            .attr("r", {{ config.node_radius | default(8) }})
            .style("fill", d => color(d.cluster));
        
        node.append("text")
            .attr("dx", 12)
            .attr("dy", "0.35em")
            .text(d => d.label || d.id);
        
        // Tooltip
        node.on("mouseover", function(event, d) {
            tooltip.transition().duration(200).style("opacity", .9);
            tooltip.html(`${d.label || d.id}<br/>Cluster: ${d.cluster}<br/>Type: ${d.type || 'Unknown'}`)
                .style("left", (event.pageX) + "px")
                .style("top", (event.pageY - 28) + "px");
        })
        .on("mouseout", function() {
            tooltip.transition().duration(500).style("opacity", 0);
        });
        
        // Update positions
        simulation.on("tick", () => {
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);
            
            node.attr("transform", d => `translate(${d.x},${d.y})`);
            
            // Update cluster hulls
            if ({{ config.show_hulls | default('true') }}) {
                updateHulls();
            }
        });
        
        function updateHulls() {
            const hullData = d3.groups(graphData.nodes, d => d.cluster)
                .map(([cluster, nodes]) => ({
                    cluster: cluster,
                    points: nodes.map(d => [d.x, d.y])
                }));
            
            hull.selectAll(".cluster-hull")
                .data(hullData)
                .join("path")
                .attr("class", "cluster-hull")
                .style("fill", d => color(d.cluster))
                .style("stroke", d => color(d.cluster))
                .attr("d", d => {
                    const hullPoints = d3.polygonHull(d.points);
                    return hullPoints ? "M" + hullPoints.join("L") + "Z" : null;
                });
        }
        
        function dragstarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }
        
        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }
        
        function dragended(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }
    </script>
</body>
</html>'''
    
    def _get_clustered_canvas_template(self) -> str:
        """Canvas-based renderer for large graphs with clustering."""
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
        #canvas-container {
            position: relative;
            background-color: white;
            border: 1px solid #ddd;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        #visualization {
            cursor: move;
        }
        .tooltip {
            position: absolute;
            padding: 10px;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            border-radius: 5px;
            pointer-events: none;
            opacity: 0;
            font-size: 12px;
        }
        .controls {
            margin-bottom: 10px;
        }
        button {
            margin-right: 10px;
            padding: 5px 10px;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        button:hover {
            background: #45a049;
        }
    </style>
</head>
<body>
    <div class="controls">
        <button onclick="resetZoom()">Reset Zoom</button>
        <button onclick="toggleClusters()">Toggle Clusters</button>
        <span>Nodes: <span id="node-count">0</span></span>
    </div>
    <div id="canvas-container">
        <canvas id="visualization" width="{{ width }}" height="{{ height }}"></canvas>
    </div>
    <div class="tooltip"></div>
    
    <script>
        const graphData = {{ graph_data_json }};
        const width = {{ width }};
        const height = {{ height }};
        const canvas = document.getElementById("visualization");
        const ctx = canvas.getContext("2d");
        const tooltip = d3.select(".tooltip");
        
        let showClusters = true;
        let transform = d3.zoomIdentity;
        
        // Update node count
        document.getElementById("node-count").textContent = graphData.nodes.length;
        
        // Detect clusters
        function detectClusters(nodes, links) {
            nodes.forEach((node, i) => {
                node.cluster = i % 10;  // Simple clustering
            });
        }
        
        detectClusters(graphData.nodes, graphData.links);
        const color = d3.scaleOrdinal(d3.schemeCategory10);
        
        // Force simulation
        const simulation = d3.forceSimulation(graphData.nodes)
            .force("link", d3.forceLink(graphData.links)
                .id(d => d.id)
                .distance(30))
            .force("charge", d3.forceManyBody().strength(-50))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collide", d3.forceCollide(5));
        
        // Zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([0.1, 10])
            .on("zoom", zoomed);
        
        d3.select(canvas).call(zoom);
        
        // Mouse interaction
        let hoveredNode = null;
        
        d3.select(canvas)
            .on("mousemove", function(event) {
                const [x, y] = transform.invert(d3.pointer(event));
                hoveredNode = findNode(x, y);
                
                if (hoveredNode) {
                    tooltip.transition().duration(200).style("opacity", .9);
                    tooltip.html(`${hoveredNode.label || hoveredNode.id}<br/>Cluster: ${hoveredNode.cluster}`)
                        .style("left", (event.pageX) + "px")
                        .style("top", (event.pageY - 28) + "px");
                    canvas.style.cursor = "pointer";
                } else {
                    tooltip.transition().duration(500).style("opacity", 0);
                    canvas.style.cursor = "move";
                }
                
                draw();
            })
            .on("mouseout", function() {
                hoveredNode = null;
                tooltip.transition().duration(500).style("opacity", 0);
                draw();
            });
        
        function findNode(x, y) {
            for (const node of graphData.nodes) {
                const dx = x - node.x;
                const dy = y - node.y;
                if (dx * dx + dy * dy < 64) {  // 8^2
                    return node;
                }
            }
            return null;
        }
        
        function zoomed(event) {
            transform = event.transform;
            draw();
        }
        
        function draw() {
            ctx.save();
            ctx.clearRect(0, 0, width, height);
            ctx.translate(transform.x, transform.y);
            ctx.scale(transform.k, transform.k);
            
            // Draw cluster backgrounds
            if (showClusters) {
                const clusters = d3.groups(graphData.nodes, d => d.cluster);
                clusters.forEach(([cluster, nodes]) => {
                    if (nodes.length > 1) {
                        const points = nodes.map(d => [d.x, d.y]);
                        const hull = d3.polygonHull(points);
                        if (hull) {
                            ctx.beginPath();
                            ctx.moveTo(hull[0][0], hull[0][1]);
                            hull.forEach(point => ctx.lineTo(point[0], point[1]));
                            ctx.closePath();
                            ctx.fillStyle = color(cluster) + "20";
                            ctx.fill();
                        }
                    }
                });
            }
            
            // Draw links
            ctx.strokeStyle = "#999";
            ctx.globalAlpha = 0.6;
            graphData.links.forEach(link => {
                ctx.beginPath();
                ctx.moveTo(link.source.x, link.source.y);
                ctx.lineTo(link.target.x, link.target.y);
                ctx.stroke();
            });
            
            // Draw nodes
            ctx.globalAlpha = 1;
            graphData.nodes.forEach(node => {
                ctx.beginPath();
                ctx.arc(node.x, node.y, node === hoveredNode ? 10 : 6, 0, 2 * Math.PI);
                ctx.fillStyle = color(node.cluster);
                ctx.fill();
                ctx.strokeStyle = "#fff";
                ctx.lineWidth = 2;
                ctx.stroke();
                
                // Draw labels for hovered node
                if (node === hoveredNode) {
                    ctx.fillStyle = "#000";
                    ctx.font = "12px Arial";
                    ctx.textAlign = "center";
                    ctx.fillText(node.label || node.id, node.x, node.y - 15);
                }
            });
            
            ctx.restore();
        }
        
        simulation.on("tick", draw);
        
        function resetZoom() {
            d3.select(canvas)
                .transition()
                .duration(750)
                .call(zoom.transform, d3.zoomIdentity);
        }
        
        function toggleClusters() {
            showClusters = !showClusters;
            draw();
        }
    </script>
</body>
</html>'''
    
    def _generate_enhanced_force_layout(self, data: Dict[str, Any], layout: str, title: str, config: Dict[str, Any]) -> str:
        """Enhanced force layout with better defaults and features."""
        # Use the existing force template but with enhanced configuration
        return self._generate_html(data, layout, title, config)
    
    def _generate_clustered_force_layout(self, data: Dict[str, Any], analysis: Dict[str, Any], title: str, config: Optional[Dict[str, Any]] = None) -> str:
        """Generate a force layout with automatic clustering."""
        template = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{{ title }}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f8fafc;
        }
        .container {
            width: 100vw;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .header {
            padding: 20px;
            background: white;
            border-bottom: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .title {
            font-size: 24px;
            font-weight: 600;
            color: #1a202c;
            margin: 0;
        }
        .subtitle {
            font-size: 14px;
            color: #718096;
            margin-top: 4px;
        }
        #viz-container {
            flex: 1;
            position: relative;
            overflow: hidden;
        }
        .cluster-hull {
            fill-opacity: 0.1;
            stroke-opacity: 0.3;
            stroke-width: 2px;
        }
        .node {
            stroke: #fff;
            stroke-width: 2px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .node:hover {
            stroke-width: 4px;
            filter: brightness(1.2);
        }
        .link {
            stroke-opacity: 0.4;
            transition: all 0.3s ease;
        }
        .link.highlighted {
            stroke-opacity: 1;
            stroke-width: 3px;
        }
        .node-label {
            pointer-events: none;
            font-size: 11px;
            font-weight: 500;
            text-anchor: middle;
            fill: #2d3748;
        }
        .tooltip {
            position: absolute;
            padding: 12px;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            border-radius: 6px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.3s;
            font-size: 13px;
            line-height: 1.4;
            max-width: 300px;
        }
        .controls {
            position: absolute;
            top: 20px;
            right: 20px;
            background: white;
            padding: 16px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .control-group {
            margin-bottom: 12px;
        }
        .control-label {
            font-size: 12px;
            font-weight: 600;
            color: #4a5568;
            margin-bottom: 4px;
            display: block;
        }
        .slider {
            width: 150px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="title">{{ title }}</h1>
            <div class="subtitle">{{ subtitle }}</div>
        </div>
        <div id="viz-container">
            <svg id="visualization"></svg>
            <div class="controls">
                <div class="control-group">
                    <label class="control-label">Cluster Strength</label>
                    <input type="range" class="slider" id="cluster-strength" 
                           min="0" max="100" value="50">
                </div>
                <div class="control-group">
                    <label class="control-label">Link Distance</label>
                    <input type="range" class="slider" id="link-distance" 
                           min="10" max="200" value="60">
                </div>
            </div>
            <div class="tooltip"></div>
        </div>
    </div>
    
    <script>
        const data = {{ data_json }};
        const analysis = {{ analysis_json }};
        
        // Auto-detect clusters based on node properties
        function detectClusters(nodes) {
            const clusters = {};
            nodes.forEach(node => {
                const clusterKey = node.type || node.category || 'default';
                if (!clusters[clusterKey]) {
                    clusters[clusterKey] = {
                        id: clusterKey,
                        nodes: [],
                        color: d3.schemeTableau10[Object.keys(clusters).length % 10]
                    };
                }
                clusters[clusterKey].nodes.push(node);
                node.cluster = clusterKey;
                node.color = node.color || clusters[clusterKey].color;
            });
            return clusters;
        }
        
        const clusters = detectClusters(data.nodes);
        const width = window.innerWidth;
        const height = window.innerHeight - 80; // Account for header
        
        const svg = d3.select("#visualization")
            .attr("width", width)
            .attr("height", height);
            
        const g = svg.append("g");
        
        // Add zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on("zoom", (event) => {
                g.attr("transform", event.transform);
            });
            
        svg.call(zoom);
        
        // Create hull for clusters
        const hull = g.append("g").attr("class", "hulls");
        
        // Create force simulation with clustering
        const simulation = d3.forceSimulation(data.nodes)
            .force("link", d3.forceLink(data.links)
                .id(d => d.id)
                .distance(60))
            .force("charge", d3.forceManyBody()
                .strength(-300))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("cluster", forceCluster())
            .force("collision", d3.forceCollide().radius(15));
        
        // Custom cluster force
        function forceCluster() {
            let strength = 0.2;
            let nodes;
            
            function force(alpha) {
                const centroids = {};
                
                // Calculate cluster centroids
                Object.values(clusters).forEach(cluster => {
                    const clusterNodes = nodes.filter(n => n.cluster === cluster.id);
                    centroids[cluster.id] = {
                        x: d3.mean(clusterNodes, n => n.x) || width / 2,
                        y: d3.mean(clusterNodes, n => n.y) || height / 2
                    };
                });
                
                // Apply force toward cluster centroid
                nodes.forEach(node => {
                    const centroid = centroids[node.cluster];
                    if (centroid) {
                        node.vx += (centroid.x - node.x) * strength * alpha;
                        node.vy += (centroid.y - node.y) * strength * alpha;
                    }
                });
            }
            
            force.initialize = function(_) {
                nodes = _;
            };
            
            force.strength = function(_) {
                return arguments.length ? (strength = +_, force) : strength;
            };
            
            return force;
        }
        
        // Draw links
        const link = g.append("g")
            .selectAll("line")
            .data(data.links)
            .enter().append("line")
            .attr("class", "link")
            .attr("stroke", d => d.color || "#94a3b8")
            .attr("stroke-width", d => Math.sqrt(d.value || 1));
        
        // Draw nodes
        const node = g.append("g")
            .selectAll("circle")
            .data(data.nodes)
            .enter().append("circle")
            .attr("class", "node")
            .attr("r", d => d.size || 10)
            .attr("fill", d => d.color)
            .call(drag(simulation));
        
        // Add labels for important nodes
        const labels = g.append("g")
            .selectAll("text")
            .data(data.nodes.filter(d => d.size > 12 || d.importance > 0.5))
            .enter().append("text")
            .attr("class", "node-label")
            .text(d => d.label || d.id);
        
        // Tooltip
        const tooltip = d3.select(".tooltip");
        
        node.on("mouseover", (event, d) => {
            // Highlight connected nodes and links
            const connectedNodes = new Set();
            const connectedLinks = new Set();
            
            data.links.forEach(link => {
                if (link.source.id === d.id || link.target.id === d.id) {
                    connectedNodes.add(link.source.id);
                    connectedNodes.add(link.target.id);
                    connectedLinks.add(link);
                }
            });
            
            node.style("opacity", n => connectedNodes.has(n.id) ? 1 : 0.3);
            link.classed("highlighted", l => connectedLinks.has(l));
            
            // Show tooltip
            tooltip.transition().duration(200).style("opacity", .9);
            tooltip.html(`
                <strong>${d.label || d.id}</strong><br/>
                Type: ${d.type || 'Unknown'}<br/>
                Cluster: ${d.cluster}<br/>
                Connections: ${connectedNodes.size - 1}
                ${d.metadata ? '<br/>Metadata: ' + JSON.stringify(d.metadata) : ''}
            `)
            .style("left", (event.pageX + 10) + "px")
            .style("top", (event.pageY - 28) + "px");
        })
        .on("mouseout", () => {
            node.style("opacity", 1);
            link.classed("highlighted", false);
            tooltip.transition().duration(500).style("opacity", 0);
        });
        
        // Update positions
        simulation.on("tick", () => {
            // Update hull
            updateHulls();
            
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);
            
            node
                .attr("cx", d => d.x)
                .attr("cy", d => d.y);
                
            labels
                .attr("x", d => d.x)
                .attr("y", d => d.y + 20);
        });
        
        // Update cluster hulls
        function updateHulls() {
            const hullData = Object.values(clusters).map(cluster => {
                const points = data.nodes
                    .filter(n => n.cluster === cluster.id)
                    .map(n => [n.x, n.y]);
                    
                if (points.length >= 3) {
                    return {
                        cluster: cluster,
                        hull: d3.polygonHull(points)
                    };
                }
                return null;
            }).filter(d => d !== null);
            
            const hullPath = hull.selectAll("path")
                .data(hullData, d => d.cluster.id);
                
            hullPath.enter()
                .append("path")
                .attr("class", "cluster-hull")
                .style("fill", d => d.cluster.color)
                .style("stroke", d => d.cluster.color)
                .merge(hullPath)
                .attr("d", d => "M" + d.hull.join("L") + "Z");
                
            hullPath.exit().remove();
        }
        
        // Drag behavior
        function drag(simulation) {
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
            
            return d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended);
        }
        
        // Interactive controls
        d3.select("#cluster-strength").on("input", function() {
            simulation.force("cluster").strength(+this.value / 100);
            simulation.alpha(0.3).restart();
        });
        
        d3.select("#link-distance").on("input", function() {
            simulation.force("link").distance(+this.value);
            simulation.alpha(0.3).restart();
        });
        
        // Add keyboard shortcuts
        d3.select("body").on("keydown", (event) => {
            if (event.key === "r") {
                // Reset zoom
                svg.transition().duration(750).call(
                    zoom.transform,
                    d3.zoomIdentity
                );
            }
        });
    </script>
</body>
</html>'''
        
        return self.jinja_env.from_string(template).render(
            title=title,
            subtitle=f"Nodes: {analysis['key_metrics']['node_count']} | Links: {analysis['key_metrics']['link_count']} | Clusters: {analysis['key_metrics']['node_types']}",
            data_json=json.dumps(data),
            analysis_json=json.dumps(analysis)
        )
    
    def _generate_timeline_network(self, data: Dict[str, Any], analysis: Dict[str, Any], title: str, config: Optional[Dict[str, Any]] = None) -> str:
        """Generate a network visualization with timeline component."""
        # For now, use clustered force as a placeholder
        return self._generate_clustered_force_layout(data, analysis, title, config)
    
    def _generate_adjacency_matrix(self, data: Dict[str, Any], analysis: Dict[str, Any], title: str, config: Optional[Dict[str, Any]] = None) -> str:
        """Generate an adjacency matrix visualization for dense graphs."""
        # For now, use clustered force as a placeholder
        return self._generate_clustered_force_layout(data, analysis, title, config)
    
    def _generate_enhanced_tree_layout(self, data: Dict[str, Any], analysis: Dict[str, Any], title: str, config: Optional[Dict[str, Any]] = None) -> str:
        """Generate an enhanced tree layout."""
        # For now, use the existing tree template
        return self._get_tree_template()
    
    def _generate_table_view(self, data: Dict[str, Any], analysis: Dict[str, Any], title: str, config: Optional[Dict[str, Any]] = None) -> str:
        """Generate an interactive HTML table for data that's better suited to tabular display."""
        template = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{{ title }}</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f8fafc;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 20px;
        }
        h1 {
            color: #1a202c;
            margin-bottom: 10px;
        }
        .summary {
            color: #718096;
            margin-bottom: 20px;
            padding: 12px;
            background: #f7fafc;
            border-radius: 4px;
        }
        .controls {
            margin-bottom: 20px;
            display: flex;
            gap: 10px;
            align-items: center;
        }
        input[type="search"] {
            padding: 8px 12px;
            border: 1px solid #e2e8f0;
            border-radius: 4px;
            flex: 1;
            max-width: 300px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }
        th {
            background-color: #f7fafc;
            font-weight: 600;
            cursor: pointer;
            user-select: none;
        }
        th:hover {
            background-color: #edf2f7;
        }
        tr:hover {
            background-color: #f7fafc;
        }
        .type-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: 500;
        }
        .type-error { background: #fee; color: #c53030; }
        .type-solution { background: #e6ffed; color: #2f855a; }
        .type-pattern { background: #e6f7ff; color: #2b6cb0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>{{ title }}</h1>
        <div class="summary">
            <strong>Data Summary:</strong> 
            {{ node_count }} items | 
            {{ link_count }} relationships | 
            {{ type_count }} categories
            <br>
            <small>{{ reason }}</small>
        </div>
        
        <div class="controls">
            <input type="search" id="search" placeholder="Search...">
            <select id="filter-type">
                <option value="">All Types</option>
                {% for type in types %}
                <option value="{{ type }}">{{ type }}</option>
                {% endfor %}
            </select>
        </div>
        
        <table id="data-table">
            <thead>
                <tr>
                    {% for column in columns %}
                    <th data-sort="{{ column }}">{{ column }} ▼</th>
                    {% endfor %}
                </tr>
            </thead>
            <tbody>
                {% for node in nodes %}
                <tr>
                    {% for column in columns %}
                    <td>
                        {% if column == 'type' %}
                            <span class="type-badge type-{{ node[column] }}">{{ node[column] }}</span>
                        {% else %}
                            {{ node[column] if node[column] else '-' }}
                        {% endif %}
                    </td>
                    {% endfor %}
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    
    <script>
        // Search functionality
        document.getElementById('search').addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            const rows = document.querySelectorAll('#data-table tbody tr');
            
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(searchTerm) ? '' : 'none';
            });
        });
        
        // Sort functionality
        document.querySelectorAll('th[data-sort]').forEach(th => {
            th.addEventListener('click', function() {
                const column = this.dataset.sort;
                const tbody = document.querySelector('#data-table tbody');
                const rows = Array.from(tbody.querySelectorAll('tr'));
                
                rows.sort((a, b) => {
                    const aVal = a.querySelector(`td:nth-child(${this.cellIndex + 1})`).textContent;
                    const bVal = b.querySelector(`td:nth-child(${this.cellIndex + 1})`).textContent;
                    return aVal.localeCompare(bVal);
                });
                
                tbody.innerHTML = '';
                rows.forEach(row => tbody.appendChild(row));
            });
        });
        
        // Filter by type
        document.getElementById('filter-type').addEventListener('change', function(e) {
            const filterType = e.target.value;
            const rows = document.querySelectorAll('#data-table tbody tr');
            
            rows.forEach(row => {
                if (!filterType) {
                    row.style.display = '';
                } else {
                    const typeCell = row.querySelector('.type-badge');
                    row.style.display = typeCell && typeCell.textContent === filterType ? '' : 'none';
                }
            });
        });
    </script>
</body>
</html>'''
        
        # Prepare data for table
        nodes = data.get("nodes", [])
        columns = []
        if nodes:
            # Get all unique keys from nodes
            all_keys = set()
            for node in nodes:
                all_keys.update(node.keys())
            # Order columns sensibly
            priority_cols = ["id", "label", "type", "category"]
            columns = [col for col in priority_cols if col in all_keys]
            columns.extend(sorted([col for col in all_keys if col not in priority_cols]))
        
        types = list(set(n.get("type", "unknown") for n in nodes))
        
        reason = "Tabular view selected due to: "
        if analysis["visualization_complexity"] == "excessive":
            reason += "high complexity (too many nodes or links)"
        elif len(data.get("links", [])) == 0:
            reason += "no relationships to visualize"
        elif analysis.get("key_metrics", {}).get("density", 0) > 0.7:
            reason += "extremely dense connections"
        else:
            reason += "data structure better suited for tabular display"
        
        return self.jinja_env.from_string(template).render(
            title=title,
            nodes=nodes,
            columns=columns,
            types=types,
            node_count=len(nodes),
            link_count=len(data.get("links", [])),
            type_count=len(types),
            reason=reason
        )
    
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
                "count": len(visualizations),
                "output_dir": str(self.output_dir),
                "visualizations": visualizations[:20],  # Latest 20
                "success": True
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "success": False
            }

# Create global instance
visualizer = D3Visualizer()

@mcp.tool()
@debug_tool(mcp_logger)
async def generate_graph_visualization(
    graph_data: str,
    layout: Literal["force", "tree", "radial", "sankey", "matrix", "timeline-force", "force-clustered", "clustered-canvas"] = "force",
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
    start_time = time.time()
    try:
        # Parse graph data
        graph_dict = json.loads(graph_data)
    except json.JSONDecodeError as e:
        return create_error_response(error=f"Invalid JSON in graph_data: {str(e)}")
    
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
    
    return create_success_response(
        data=result,
        tool_name="generate_graph_visualization",
        start_time=start_time
    )

@mcp.tool()
@debug_tool(mcp_logger)
async def list_visualizations() -> str:
    """List all generated visualizations.
    
    Returns the most recent visualizations with their file paths and metadata.
    """
    start_time = time.time()
    result = visualizer.list_visualizations()
    return create_success_response(
        data=result,
        tool_name="list_visualizations",
        start_time=start_time
    )

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
    start_time = time.time()
    return create_error_response(
        error="This feature requires integration with arango-tools MCP. Use query() to fetch graph data first, then generate_graph_visualization().",
        tool_name="visualize_arango_graph",
        start_time=start_time
    )

@mcp.tool()
@debug_tool(mcp_logger)
async def generate_intelligent_visualization(
    graph_data: str,
    title: str = "Intelligent Visualization",
    analysis_goal: Optional[str] = None,
    user_preferences: Optional[str] = None
) -> str:
    """Generate an intelligent D3.js visualization based on data analysis.
    
    This tool analyzes the data structure and automatically selects the best
    visualization approach, potentially combining multiple D3 techniques.
    
    Args:
        graph_data: JSON string with data (nodes/links for graphs, or other structures)
        title: Title for the visualization
        analysis_goal: What insight to highlight (e.g., "show error clusters", "trace fix paths")
        user_preferences: JSON string with preferences (e.g., {"style": "minimal", "colors": "categorical"})
    
    Returns:
        Result with filepath, analysis, and visualization metadata
    
    The tool will:
    1. Analyze the data structure:
       - Node count: <10 (simple), 10-50 (medium), 50-200 (complex), >200 (consider alternatives)
       - Link density: sparse (<0.1), medium (0.1-0.3), dense (>0.3)
       - Data types: categorical, temporal, hierarchical, numerical, mixed
       - Patterns: clusters, cycles, trees, bipartite, time-series
    
    2. Choose optimal visualization:
       - NO VISUALIZATION: If >500 nodes or density >0.5 → return tabular summary
       - Force layout: General graphs with <100 nodes, density <0.2
       - Clustered force: When node types >2 and natural groupings exist
       - Matrix: Dense graphs (>0.3) or when comparing all-to-all relationships
       - Tree/Hierarchy: When parent-child relationships detected
       - Timeline: When temporal data spans >3 time points
       - Sankey: For flow data with source→target→value
       - Heatmap: For correlation matrices or grid data
       - Table: For lists, rankings, or when visual complexity exceeds clarity
    
    3. Generate appropriate output:
       - Custom D3 visualization with interactions
       - HTML table with sorting/filtering for data lists
       - Summary statistics when visualization would be cluttered
       - Hybrid view combining multiple techniques
    
    Example:
        generate_intelligent_visualization(
            '{"nodes": [...], "links": [...]}',
            "Error Pattern Analysis",
            "show error clusters and solution effectiveness"
        )
    """
    start_time = time.time()
    try:
        # Parse input data
        data = json.loads(graph_data)
        prefs = json.loads(user_preferences) if user_preferences else {}
        
        # Use the visualizer's intelligent generation
        result = visualizer.generate_intelligent_visualization(
            data=data,
            title=title,
            analysis_goal=analysis_goal,
            user_preferences=prefs
        )
        
        return create_success_response(
            data=result,
            tool_name="generate_intelligent_visualization",
            start_time=start_time
        )
        
    except json.JSONDecodeError as e:
        return create_error_response(
            error=f"Invalid JSON in graph_data: {str(e)}",
            tool_name="generate_intelligent_visualization",
            start_time=start_time
        )
    except Exception as e:
        logger.error(f"Intelligent visualization generation failed: {e}")
        return create_error_response(
            error=str(e),
            tool_name="generate_intelligent_visualization",
            start_time=start_time
        )

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
    
    # Example 3: Intelligent visualization
    logger.info("\n3. Creating intelligent visualization:")
    
    # Complex data that benefits from intelligent analysis
    complex_graph = {
        "nodes": [
            # Errors with different properties
            {"id": "e1", "label": "AsyncIO Error", "type": "error", "timestamp": "2024-01-15T10:00:00Z", "severity": "high"},
            {"id": "e2", "label": "Import Error", "type": "error", "timestamp": "2024-01-15T10:05:00Z", "severity": "medium"},
            {"id": "e3", "label": "Timeout", "type": "error", "timestamp": "2024-01-15T10:10:00Z", "severity": "low"},
            # Solutions
            {"id": "s1", "label": "Drain Streams", "type": "solution", "effectiveness": 0.95},
            {"id": "s2", "label": "Fix Import", "type": "solution", "effectiveness": 0.98},
            # Patterns
            {"id": "p1", "label": "Concurrency Issues", "type": "pattern", "category": "async"}
        ],
        "links": [
            {"source": "e1", "target": "s1", "type": "fixes", "strength": 0.95},
            {"source": "e2", "target": "s2", "type": "fixes", "strength": 0.98},
            {"source": "e1", "target": "p1", "type": "belongs_to"},
            {"source": "e3", "target": "p1", "type": "belongs_to"}
        ]
    }
    
    intelligent_result = visualizer.generate_intelligent_visualization(
        data=complex_graph,
        title="Intelligent Error Analysis",
        analysis_goal="show temporal patterns and solution effectiveness"
    )
    
    if intelligent_result["success"]:
        logger.success(f"Created intelligent visualization: {intelligent_result['filename']}")
        logger.info(f"Visualization type: {intelligent_result['visualization_type']}")
        logger.info(f"Analysis: {json.dumps(intelligent_result['analysis'], indent=2)}")
    
    logger.success("\n✅ D3 Visualizer working with intelligent features!")
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
    
    if args.mode == "test":
        # Quick test mode for startup verification
        print("Testing D3 Visualizer MCP server...")
        print(f"Output dir: {visualizer.output_dir}")
        print("Server ready to start.")
    elif args.mode == "debug":
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