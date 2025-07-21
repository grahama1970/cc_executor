#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "fastmcp",
#     "loguru",
#     "pandas",
#     "numpy",
#     "mcp-logger-utils>=0.1.5"
# ]
# ///
"""MCP D3 Visualization Advisor

This MCP server analyzes data using pandas and returns comprehensive guidance prompts
that tell agents exactly when to use which visualization type.
"""

import json
import sys
import time
from typing import Dict, Any, Optional, List, Literal, Union
from datetime import datetime
from pathlib import Path
from io import StringIO

import pandas as pd
import numpy as np
from fastmcp import FastMCP, Context
from loguru import logger

# Import standardized response utilities
sys.path.insert(0, str(Path(__file__).parent))
from utils.response_utils import create_success_response, create_error_response

# Import from our shared PyPI package
from mcp_logger_utils import MCPLogger, debug_tool

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")

# Initialize MCP server and logger
mcp = FastMCP("d3-visualization-advisor")
mcp_logger = MCPLogger("d3-visualization-advisor")

@mcp.tool()
@debug_tool(mcp_logger)
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
        JSON response with visualization guide and metadata
    """
    import time
    start_time = time.time()
    
    try:
        data_obj = json.loads(data)
        constraints_obj = json.loads(constraints) if constraints else {}
        
        # Analyze the data
        analysis = _analyze_data_structure(data_obj)
        
        # Generate comprehensive guide
        guide = _generate_visualization_guide(analysis, data_obj, purpose, constraints_obj)
        
        # Return standardized JSON response
        return create_success_response(
            data={
                "guide": guide,
                "analysis_summary": {
                    "data_type": analysis.get("shape", {}).get("type", "unknown"),
                    "patterns": analysis.get("patterns", []),
                    "issues": analysis.get("issues", []),
                    "recommended_visualizations": list(analysis.get("visualization_scores", {}).keys())[:3]
                }
            },
            tool_name="analyze_and_recommend_visualization",
            start_time=start_time
        )
        
    except json.JSONDecodeError as e:
        return create_error_response(
            error=f"Error parsing JSON: {str(e)}",
            tool_name="analyze_and_recommend_visualization",
            start_time=start_time
        )
    except Exception as e:
        logger.error(f"Error analyzing data: {e}")
        return create_error_response(
            error=f"Error analyzing data: {str(e)}",
            tool_name="analyze_and_recommend_visualization",
            start_time=start_time
        )


def _analyze_data_structure(data: Any) -> Dict[str, Any]:
    """Perform comprehensive data analysis using pandas."""
    analysis = {
        "shape": {},
        "metrics": {},
        "patterns": [],
        "issues": [],
        "pandas_analysis": {},
        "data_quality": {},
        "statistical_summary": {},
        "graph_metrics": {},
        "visualization_scores": {}
    }
    
    # Initialize nodes and links
    nodes = []
    links = []
    
    # Network/Graph data analysis - check both D3 format and ArangoDB format
    if isinstance(data, dict) and "nodes" in data and "links" in data:
        # D3.js format
        nodes = data.get("nodes", [])
        links = data.get("links", [])
        
        analysis["shape"] = {
            "type": "network",
            "node_count": len(nodes),
            "link_count": len(links),
            "format": "d3"
        }
        
        # Calculate density
        if len(nodes) > 1:
            analysis["metrics"]["density"] = len(links) / (len(nodes) * (len(nodes) - 1))
        else:
            analysis["metrics"]["density"] = 0
            
        # Calculate comprehensive graph metrics
        graph_metrics = _calculate_graph_metrics(nodes, links)
        analysis["graph_metrics"] = graph_metrics
        
        # Calculate visualization suitability scores
        viz_scores = _calculate_visualization_scores(nodes, links, graph_metrics)
        analysis["visualization_scores"] = viz_scores
        
        # Pattern detection
        if _is_bipartite(nodes, links):
            analysis["patterns"].append("bipartite")
            
        if _has_temporal_data(nodes):
            analysis["patterns"].append("temporal")
            
        if _is_hierarchical(nodes, links):
            analysis["patterns"].append("hierarchical")
            
        if all("value" in l or "weight" in l for l in links):
            analysis["patterns"].append("weighted_flow")
            
        # Advanced pattern detection
        advanced_patterns = _detect_advanced_patterns(nodes, links, graph_metrics)
        analysis["patterns"].extend(advanced_patterns)
        
        # Issues detection
        if len(nodes) > 500:
            analysis["issues"].append("high_node_count")
        if analysis["metrics"]["density"] > 0.5:
            analysis["issues"].append("too_dense")
        if graph_metrics.get("clustering_coefficient", 0) > 0.7:
            analysis["issues"].append("highly_clustered")
        if graph_metrics.get("average_degree", 0) > 50:
            analysis["issues"].append("high_degree_nodes")
        
    elif isinstance(data, list) and data and all(isinstance(item, dict) for item in data):
        # Check for ArangoDB edge format (_from, _to fields)
        if all({"_from", "_to"}.issubset(item.keys()) for item in data[:5]):
            # ArangoDB edge collection format
            analysis["shape"] = {
                "type": "network",
                "format": "arangodb_edges",
                "edge_count": len(data),
                "node_count": len(set([item.get("_from") for item in data] + [item.get("_to") for item in data]))
            }
            
            # Convert to nodes/links for further analysis
            nodes_set = set()
            links = []
            for edge in data:
                source = edge.get("_from", "").split("/")[-1]  # Extract ID from collection/id format
                target = edge.get("_to", "").split("/")[-1]
                nodes_set.add(source)
                nodes_set.add(target)
                links.append({"source": source, "target": target, **{k: v for k, v in edge.items() if k not in ["_from", "_to"]}})
            
            nodes = [{"id": node_id} for node_id in nodes_set]
            analysis["patterns"].append("arangodb_graph")
            
            # Network analysis for ArangoDB data
            if len(nodes) > 1:
                analysis["metrics"]["density"] = len(links) / (len(nodes) * (len(nodes) - 1))
            else:
                analysis["metrics"]["density"] = 0
                
            # Calculate comprehensive graph metrics
            graph_metrics = _calculate_graph_metrics(nodes, links)
            analysis["graph_metrics"] = graph_metrics
            
            # Calculate visualization suitability scores
            viz_scores = _calculate_visualization_scores(nodes, links, graph_metrics)
            analysis["visualization_scores"] = viz_scores
                
            # Check for patterns
            if _is_bipartite(nodes, links):
                analysis["patterns"].append("bipartite")
                
            if _has_temporal_data(nodes):
                analysis["patterns"].append("temporal")
                
            if _is_hierarchical(nodes, links):
                analysis["patterns"].append("hierarchical")
                
            if all("value" in l or "weight" in l for l in links):
                analysis["patterns"].append("weighted_flow")
                
            # Advanced pattern detection
            advanced_patterns = _detect_advanced_patterns(nodes, links, graph_metrics)
            analysis["patterns"].extend(advanced_patterns)
                
            # Check for issues
            if len(nodes) > 500:
                analysis["issues"].append("high_node_count")
            if analysis["metrics"]["density"] > 0.5:
                analysis["issues"].append("too_dense")
            if graph_metrics.get("clustering_coefficient", 0) > 0.7:
                analysis["issues"].append("highly_clustered")
            if graph_metrics.get("average_degree", 0) > 50:
                analysis["issues"].append("high_degree_nodes")
                
        # Check for ArangoDB path format (from graph traversals)
        elif any("vertices" in item or "edges" in item for item in data[:5] if isinstance(item, dict)):
            analysis["shape"] = {
                "type": "network",
                "format": "arangodb_paths",
                "path_count": len(data)
            }
            analysis["patterns"].append("graph_traversal")
            
        # Regular tabular data (not ArangoDB format)
        else:
            analysis["shape"] = {
                "type": "tabular",
                "row_count": len(data),
                "columns": list(data[0].keys()) if data else []
            }
            
            if data:
                # Convert to pandas DataFrame for deep analysis
                df = pd.DataFrame(data)
                
                # Pandas comprehensive analysis
                analysis["pandas_analysis"] = _perform_pandas_analysis(df)
                analysis["data_quality"] = _analyze_data_quality(df)
                analysis["statistical_summary"] = _get_statistical_summary(df)
                
                # Pattern detection based on pandas analysis
                patterns = _detect_patterns_from_pandas(df, analysis["pandas_analysis"])
                analysis["patterns"].extend(patterns)
                    
                # Check issues
                if len(data) > 1000:
                    analysis["issues"].append("large_dataset")
                if len(data) < 3:
                    analysis["issues"].append("too_few_rows")
                
    # Hierarchical data
    elif isinstance(data, dict) and ("children" in data or "parent" in data):
        analysis["shape"] = {
            "type": "hierarchical",
            "depth": _calculate_tree_depth(data),
            "leaf_count": _count_leaves(data)
        }
        
        if analysis["shape"]["depth"] > 5:
            analysis["issues"].append("deep_hierarchy")
            
    else:
        analysis["shape"]["type"] = "unknown"
        
    return analysis


def _generate_visualization_guide(analysis: Dict, data: Any, purpose: Optional[str], constraints: Dict) -> str:
    """Generate the comprehensive visualization guide."""
    
    guide = f"""# D3.js Visualization Recommendation Guide

## Your Data Analysis

**Data Shape**: {analysis['shape']['type']}
**Key Metrics**: {json.dumps(analysis['metrics'], indent=2)}
**Detected Patterns**: {', '.join(analysis['patterns']) if analysis['patterns'] else 'None'}
**Potential Issues**: {', '.join(analysis['issues']) if analysis['issues'] else 'None'}
**Purpose**: {purpose or 'General visualization'}

"""
    
    # Add graph metrics if available
    if analysis.get('graph_metrics'):
        guide += f"""## Graph Metrics Summary

- **Nodes**: {analysis['graph_metrics']['node_count']}
- **Edges**: {analysis['graph_metrics']['edge_count']}
- **Density**: {analysis['graph_metrics']['density']:.3f}
- **Average Degree**: {analysis['graph_metrics']['average_degree']:.2f}
- **Clustering Coefficient**: {analysis['graph_metrics']['clustering_coefficient']:.3f}
- **Is Tree**: {analysis['graph_metrics']['is_tree']}
- **Has Cycles**: {analysis['graph_metrics']['has_cycles']}
- **Centralization**: {analysis['graph_metrics']['centralization']:.3f}

"""
    
    # Add visualization scores if available
    if analysis.get('visualization_scores'):
        scores = analysis['visualization_scores']
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        guide += """## Visualization Suitability Scores

Based on your data characteristics, here are the recommended visualizations:

"""
        for viz_type, score in sorted_scores[:5]:  # Top 5 recommendations
            if score > 0.3:  # Only show decent scores
                viz_name = viz_type.replace('_', ' ').title()
                guide += f"- **{viz_name}**: {score:.2f}/1.0"
                if score > 0.8:
                    guide += " ⭐ HIGHLY RECOMMENDED"
                elif score > 0.6:
                    guide += " ✓ Good fit"
                guide += "\n"
        
        guide += "\n"

    # Add pandas analysis if available
    if analysis.get('pandas_analysis'):
        guide += _format_pandas_analysis(analysis['pandas_analysis'], analysis['data_quality'], analysis['statistical_summary'])
        guide += "\n"

    # Add specific recommendations based on data type
    if analysis['shape']['type'] == 'network':
        guide += _get_network_recommendations(analysis, data)
    elif analysis['shape']['type'] == 'tabular':
        guide += _get_tabular_recommendations(analysis, data)
    elif analysis['shape']['type'] == 'hierarchical':
        guide += _get_hierarchical_recommendations(analysis, data)
    else:
        guide += _get_general_recommendations(analysis)
        
    # Add decision flowchart
    guide += """
## Quick Decision Flowchart

```
Is your data a network/graph?
├─ Yes → Check node count
│   ├─ >500 nodes → Use MATRIX or TABLE
│   ├─ 100-500 nodes → Use CLUSTERED FORCE LAYOUT
│   └─ <100 nodes → Check density
│       ├─ >0.3 density → Use MATRIX
│       └─ <0.3 density → Check patterns
│           ├─ Bipartite → Use SANKEY or BIPARTITE LAYOUT
│           ├─ Hierarchical → Use TREE or RADIAL TREE
│           └─ General → Use FORCE-DIRECTED GRAPH
│
└─ No → Is it tabular data?
    ├─ Yes → Check row count
    │   ├─ >1000 rows → Use AGGREGATED CHARTS or TABLE
    │   ├─ <10 rows → Use TEXT SUMMARY
    │   └─ 10-1000 rows → Check patterns
    │       ├─ Time series → Use LINE CHART
    │       ├─ Categories → Use BAR CHART
    │       ├─ Distribution → Use HISTOGRAM
    │       ├─ Correlation → Use SCATTER PLOT
    │       └─ Part-of-whole → Use PIE/DONUT CHART
    │
    └─ No → Is it hierarchical?
        ├─ Yes → Check depth
        │   ├─ >5 levels → Use TREEMAP or SUNBURST
        │   └─ ≤5 levels → Use TREE or DENDROGRAM
        └─ No → Use TABLE or custom visualization
```
"""
    
    # Add specific code examples
    guide += _get_code_examples(analysis)
    
    return guide


def _get_network_recommendations(analysis: Dict, data: Dict) -> str:
    """Generate network-specific recommendations."""
    
    shape = analysis['shape']
    node_count = shape.get('node_count', shape.get('edge_count', 0))
    density = analysis['metrics'].get('density', 0)
    patterns = analysis['patterns']
    
    rec = """## Network Visualization Recommendations

"""
    
    # ArangoDB-specific guidance
    if 'arangodb_graph' in patterns:
        rec += """### 🔷 ArangoDB Graph Data Detected!

Your data appears to be from an ArangoDB edge collection with `_from` and `_to` fields.

**Data Format**: ArangoDB Edge Collection
**Detected**: {} edges connecting {} unique nodes

""".format(shape.get('edge_count', 0), node_count)
        
        if shape.get('format') == 'arangodb_paths':
            rec += """**Graph Traversal Results**: Your data contains path objects from a graph traversal query.

Consider extracting and visualizing:
- The full path (vertices + edges)
- Just the shortest paths
- Path statistics (length distribution)

"""
    
    # Primary recommendation
    if 'high_node_count' in analysis['issues']:
        rec += """### 🚫 DO NOT USE: Force-Directed Graph
**Why**: With {} nodes, you'll get an unreadable "hairball" that provides no insight.

### ✅ RECOMMENDED: Adjacency Matrix
**Why**: 
- Scales to thousands of nodes
- Every connection visible as a cell
- Patterns emerge through color intensity
- No overlapping elements

**When to use this**:
```
if (nodes.length > 500 || density > 0.5) {
    return "adjacency_matrix";
}
```

**D3 Implementation**:
```javascript
// Create matrix data structure
const matrix = [];
nodes.forEach((source, i) => {
    nodes.forEach((target, j) => {
        const link = links.find(l => 
            (l.source === source.id && l.target === target.id)
        );
        matrix.push({
            x: i, y: j,
            value: link ? link.value : 0
        });
    });
});

// Use color scale for values
const color = d3.scaleSequential(d3.interpolateBlues)
    .domain([0, d3.max(matrix, d => d.value)]);
```

### ✅ ALTERNATIVE: Aggregated Summary Table
**Why**: Sometimes the best visualization is no visualization.

**Features**:
- Group nodes by type/category
- Show connection counts
- Sortable, searchable
- Link to detailed views

""".format(node_count)
        
    elif 'bipartite' in patterns:
        rec += """### ✅ RECOMMENDED: Sankey Diagram
**Why**: Your data has two distinct node types with flows between them.

**Perfect for**:
- Error → Solution mappings
- Source → Destination flows  
- User → Product interactions
- Any bipartite relationship

**When to use this**:
```
if (nodeTypes.length === 2 && hasFlowValues) {
    return "sankey_diagram";
}
```

**D3 Implementation**:
```javascript
import {sankey, sankeyLinkHorizontal} from "d3-sankey";

const sankeyLayout = sankey()
    .nodeWidth(15)
    .nodePadding(10)
    .extent([[1, 1], [width - 1, height - 6]]);

const {nodes, links} = sankeyLayout({
    nodes: data.nodes.map(d => ({...d})),
    links: data.links.map(d => ({...d}))
});

// Draw links with gradient
const link = svg.append("g")
    .selectAll("path")
    .data(links)
    .join("path")
    .attr("d", sankeyLinkHorizontal())
    .attr("stroke-width", d => Math.max(1, d.width));
```

### ✅ ALTERNATIVE: Bipartite Layout
**Why**: Clear two-column layout showing relationships.

**When to use**:
- Simpler than Sankey
- Don't need flow widths
- Want clear type separation

"""
        
    elif density > 0.3:
        rec += """### 🚫 DO NOT USE: Standard Force Layout
**Why**: With {:.1%} density, nodes will overlap heavily.

### ✅ RECOMMENDED: Matrix Visualization
**Why**: Dense networks are better shown as matrices where patterns are visible through color.

**Alternative approaches**:
1. **Chord Diagram** - If showing mutual relationships
2. **Edge Bundling** - If you must use node-link
3. **Filtered View** - Show only important edges

""".format(density)
        
    else:
        # Good for standard force layout
        rec += """### ✅ RECOMMENDED: Force-Directed Graph
**Why**: With {} nodes and {:.1%} density, this will create a readable, explorable visualization.

**Best practices**:
```javascript
// Adaptive parameters based on data
const simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links)
        .distance(d => {
            // Increase distance for fewer nodes
            const baseDist = 30;
            const scaleFactor = Math.sqrt(100 / nodes.length);
            return baseDist * scaleFactor;
        }))
    .force("charge", d3.forceManyBody()
        .strength(-30 * Math.max(1, 50 / nodes.length)))
    .force("collision", d3.forceCollide()
        .radius(d => d.radius || 5));

// Add clustering for categories
if (hasCategories) {
    simulation.force("cluster", forceCluster());
}
```

**Enhancements**:
- Color by category
- Size by importance
- Cluster similar nodes
- Add convex hulls for groups

""".format(node_count, density)
        
    # Add pattern-specific recommendations
    if 'temporal' in patterns:
        rec += """
### 📅 Temporal Pattern Detected!

Consider a **Timeline Layout**:
```javascript
// Position nodes along time axis
const timeScale = d3.scaleTime()
    .domain(d3.extent(nodes, d => new Date(d.timestamp)))
    .range([0, width]);

// Force only controls y-position
simulation
    .force("x", d3.forceX(d => timeScale(new Date(d.timestamp))).strength(1))
    .force("y", d3.forceY(height / 2).strength(0.1));
```
"""
        
    if 'hierarchical' in patterns:
        rec += """
### 🌳 Hierarchical Structure Detected!

Consider a **Tree Layout**:
```javascript
const tree = d3.tree()
    .size([height, width - 160]);

const root = d3.hierarchy(data);
const treeData = tree(root);

// Or use radial layout for space efficiency
const radialTree = d3.tree()
    .size([2 * Math.PI, radius])
    .separation((a, b) => (a.parent == b.parent ? 1 : 2) / a.depth);
```
"""
        
    return rec


def _get_tabular_recommendations(analysis: Dict, data: List) -> str:
    """Generate tabular data recommendations based on pandas analysis."""
    
    row_count = analysis['shape']['row_count']
    patterns = analysis['patterns']
    pandas_analysis = analysis.get('pandas_analysis', {})
    
    rec = """## Tabular Data Visualization Recommendations

"""
    
    if 'too_few_rows' in analysis['issues']:
        rec += """### 🚫 DO NOT USE: Any Chart
**Why**: With only {} rows, a chart adds no value over showing the numbers directly.

### ✅ RECOMMENDED: Summary Cards or Table
**Why**: Clear, direct presentation of the few data points.

**Implementation**:
```javascript
// Create cards for each row
const cards = d3.select('#container')
    .selectAll('.card')
    .data(data)
    .join('div')
    .attr('class', 'card')
    .html(d => `
        <h3>${d.name}</h3>
        <div class="value">${d.value}</div>
        <div class="detail">${d.description}</div>
    `);
```

""".format(row_count)
        
    elif 'time_series' in patterns:
        rec += """### ✅ RECOMMENDED: Line Chart
**Why**: You have temporal data with numeric values - perfect for showing trends over time.

**When to use**:
```
if (hasDateColumn && hasNumericColumn && rows > 2) {
    return "line_chart";
}
```

**D3 Implementation**:
```javascript
// Parse dates
const parseTime = d3.timeParse("%Y-%m-%d");
data.forEach(d => {
    d.date = parseTime(d.dateString);
    d.value = +d.value;
});

// Scales
const x = d3.scaleTime()
    .domain(d3.extent(data, d => d.date))
    .range([0, width]);

const y = d3.scaleLinear()
    .domain([0, d3.max(data, d => d.value)])
    .nice()
    .range([height, 0]);

// Line generator with curve
const line = d3.line()
    .x(d => x(d.date))
    .y(d => y(d.value))
    .curve(d3.curveMonotoneX);

// Add area fill
const area = d3.area()
    .x(d => x(d.date))
    .y0(height)
    .y1(d => y(d.value))
    .curve(d3.curveMonotoneX);
```

**Enhancements**:
- Multiple lines for categories
- Brush for time selection
- Annotations for key events
- Hover tooltips with values

"""
        
    elif pandas_analysis.get('categorical_columns') and pandas_analysis.get('numeric_columns'):
        rec += """### ✅ RECOMMENDED: Bar Chart
**Why**: You have categories and values - ideal for comparison.

**When to use**:
```
if (hasCategoryColumn && hasValueColumn && categories < 20) {
    return "bar_chart";
}
```

**Variations**:
- **Grouped bars** - Multiple values per category
- **Stacked bars** - Show composition
- **Horizontal bars** - Long category names

**D3 Implementation**:
```javascript
const x = d3.scaleBand()
    .domain(data.map(d => d.category))
    .range([0, width])
    .padding(0.1);

const y = d3.scaleLinear()
    .domain([0, d3.max(data, d => d.value)])
    .nice()
    .range([height, 0]);

// Bars with animation
const bars = svg.selectAll('.bar')
    .data(data)
    .join('rect')
    .attr('class', 'bar')
    .attr('x', d => x(d.category))
    .attr('width', x.bandwidth())
    .attr('y', height)
    .attr('height', 0)
    .transition()
    .duration(800)
    .attr('y', d => y(d.value))
    .attr('height', d => height - y(d.value));
```

"""
        
    elif 'multivariate' in patterns:
        rec += """### ✅ RECOMMENDED: Scatter Plot
**Why**: You have multiple numeric variables - perfect for showing correlations.

**When to use**:
```
if (numericColumns >= 2) {
    return "scatter_plot";
}
```

**Advanced options**:
- **Scatter plot matrix** - All variable pairs
- **Bubble chart** - Third variable as size
- **Connected scatter** - If temporal

"""
        
    if row_count > 100:
        rec += """
### 📊 Large Dataset Considerations

With {} rows, consider:

1. **Aggregation First**
```javascript
// Group and summarize before visualizing
const summary = d3.rollup(data,
    v => ({
        count: v.length,
        total: d3.sum(v, d => d.value),
        avg: d3.mean(v, d => d.value)
    }),
    d => d.category
);
```

2. **Interactive Table with Visualizations**
- Sortable columns
- Search/filter
- Inline sparklines
- Export functionality

3. **Overview + Detail**
- Aggregated chart as overview
- Brush to select range
- Detailed view of selection

""".format(row_count)
        
    return rec


def _get_hierarchical_recommendations(analysis: Dict, data: Dict) -> str:
    """Generate hierarchical data recommendations."""
    
    depth = analysis['shape']['depth']
    leaf_count = analysis['shape']['leaf_count']
    
    rec = """## Hierarchical Data Visualization Recommendations

"""
    
    if depth > 5:
        rec += """### 🚫 DO NOT USE: Standard Tree
**Why**: With {} levels deep, a tree will be extremely wide or require excessive scrolling.

### ✅ RECOMMENDED: Treemap
**Why**: 
- Space-efficient rectangle packing
- Shows size and hierarchy together
- All levels visible at once

**D3 Implementation**:
```javascript
const treemap = d3.treemap()
    .size([width, height])
    .padding(1)
    .round(true);

const root = d3.hierarchy(data)
    .sum(d => d.value)
    .sort((a, b) => b.value - a.value);

treemap(root);

// Draw rectangles
const leaf = svg.selectAll("g")
    .data(root.leaves())
    .join("g")
    .attr("transform", d => `translate(${d.x0},${d.y0})`);

leaf.append("rect")
    .attr("width", d => d.x1 - d.x0)
    .attr("height", d => d.y1 - d.y0)
    .attr("fill", d => color(d.parent.data.name));
```

### ✅ ALTERNATIVE: Sunburst Diagram
**Why**: Radial space-filling showing hierarchy as rings.

""".format(depth)
        
    else:
        rec += """### ✅ RECOMMENDED: Interactive Tree
**Why**: With {} levels, a tree provides clear parent-child relationships.

**Options**:
1. **Collapsible Tree** - Click to expand/collapse
2. **Radial Tree** - Space-efficient circular layout
3. **Dendrogram** - If showing similarity/clustering

**D3 Implementation**:
```javascript
const tree = d3.tree()
    .size([height, width - 160]);

const root = d3.hierarchy(data);
const treeData = tree(root);

// Draw links (paths between nodes)
const link = svg.selectAll(".link")
    .data(treeData.links())
    .join("path")
    .attr("class", "link")
    .attr("d", d => `
        M${d.source.y},${d.source.x}
        C${(d.source.y + d.target.y) / 2},${d.source.x}
         ${(d.source.y + d.target.y) / 2},${d.target.x}
         ${d.target.y},${d.target.x}
    `);

// Draw nodes
const node = svg.selectAll(".node")
    .data(treeData.descendants())
    .join("g")
    .attr("class", "node")
    .attr("transform", d => `translate(${d.y},${d.x})`);
```

""".format(depth)
        
    return rec


def _get_general_recommendations(analysis: Dict) -> str:
    """Fallback recommendations for unknown data types."""
    return """## General Visualization Recommendations

Your data structure is not immediately recognizable. Consider:

1. **Start with a Table**
   - Explore the data structure
   - Add sorting and filtering
   - Identify patterns manually

2. **Custom Visualization**
   - Design based on your specific needs
   - Combine multiple techniques
   - Focus on your key insight

3. **Ask clarifying questions**:
   - What story are you trying to tell?
   - Who is your audience?
   - What decisions will be made?

"""


def _get_code_examples(analysis: Dict) -> str:
    """Add relevant code examples based on analysis."""
    
    examples = """
## D3.js Code Patterns

### Always Start With:
```javascript
// Container setup
const margin = {top: 20, right: 20, bottom: 40, left: 40};
const width = 800 - margin.left - margin.right;
const height = 600 - margin.top - margin.bottom;

const svg = d3.select("#chart")
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom);

const g = svg.append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);
```

### Add Responsiveness:
```javascript
function resize() {
    const newWidth = container.clientWidth - margin.left - margin.right;
    svg.attr("width", newWidth + margin.left + margin.right);
    x.range([0, newWidth]);
    // Redraw elements
}
window.addEventListener("resize", resize);
```

### Always Include Tooltips:
```javascript
const tooltip = d3.select("body").append("div")
    .attr("class", "tooltip")
    .style("opacity", 0);

element.on("mouseover", (event, d) => {
    tooltip.transition().duration(200).style("opacity", .9);
    tooltip.html(formatTooltip(d))
        .style("left", (event.pageX + 10) + "px")
        .style("top", (event.pageY - 28) + "px");
})
.on("mouseout", () => {
    tooltip.transition().duration(500).style("opacity", 0);
});
```

### Performance for Large Data:
```javascript
// Use canvas for >1000 elements
if (data.length > 1000) {
    const canvas = d3.select("#chart")
        .append("canvas")
        .attr("width", width)
        .attr("height", height);
    
    const context = canvas.node().getContext("2d");
    // Draw with canvas API
}

// Or use sampling
const sampledData = data.filter((d, i) => i % sampleRate === 0);
```
"""
    
    return examples


def _perform_pandas_analysis(df: pd.DataFrame) -> Dict[str, Any]:
    """Perform comprehensive pandas analysis on the dataframe."""
    analysis = {
        "shape": {
            "rows": len(df),
            "columns": len(df.columns),
            "memory_usage": df.memory_usage(deep=True).sum() / 1024 / 1024,  # MB
            "column_names": df.columns.tolist()
        },
        "dtypes": {},
        "temporal_columns": [],
        "numeric_columns": [],
        "categorical_columns": [],
        "distributions": {},
        "correlations": {},
        "unique_values": {},
        "cardinality": {}
    }
    
    # Analyze each column
    for col in df.columns:
        # Data type analysis
        dtype = str(df[col].dtype)
        analysis["dtypes"][col] = dtype
        
        # Try to infer better types
        if df[col].dtype == 'object':
            # Check if it's actually numeric
            try:
                pd.to_numeric(df[col], errors='raise')
                analysis["numeric_columns"].append(col)
                df[col] = pd.to_numeric(df[col], errors='coerce')
            except:
                # Check if it's temporal
                try:
                    pd.to_datetime(df[col], errors='raise')
                    analysis["temporal_columns"].append(col)
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                except:
                    # It's categorical
                    analysis["categorical_columns"].append(col)
        elif np.issubdtype(df[col].dtype, np.number):
            analysis["numeric_columns"].append(col)
        
        # Cardinality (unique values ratio)
        unique_count = df[col].nunique()
        analysis["unique_values"][col] = unique_count
        analysis["cardinality"][col] = unique_count / len(df) if len(df) > 0 else 0
    
    # Numeric column analysis
    if analysis["numeric_columns"]:
        numeric_df = df[analysis["numeric_columns"]]
        
        # Distributions
        for col in analysis["numeric_columns"]:
            if df[col].notna().sum() > 0:  # Has non-null values
                analysis["distributions"][col] = {
                    "mean": float(df[col].mean()),
                    "std": float(df[col].std()),
                    "min": float(df[col].min()),
                    "25%": float(df[col].quantile(0.25)),
                    "50%": float(df[col].quantile(0.50)),
                    "75%": float(df[col].quantile(0.75)),
                    "max": float(df[col].max()),
                    "skew": float(df[col].skew()),
                    "kurtosis": float(df[col].kurtosis()),
                    "zeros": int((df[col] == 0).sum()),
                    "positive": int((df[col] > 0).sum()),
                    "negative": int((df[col] < 0).sum())
                }
        
        # Correlations
        if len(analysis["numeric_columns"]) > 1:
            corr_matrix = numeric_df.corr()
            analysis["correlations"] = {
                "matrix": corr_matrix.to_dict(),
                "high_correlations": []
            }
            
            # Find high correlations
            for i in range(len(corr_matrix.columns)):
                for j in range(i+1, len(corr_matrix.columns)):
                    corr_value = corr_matrix.iloc[i, j]
                    if abs(corr_value) > 0.7:
                        analysis["correlations"]["high_correlations"].append({
                            "col1": corr_matrix.columns[i],
                            "col2": corr_matrix.columns[j],
                            "correlation": float(corr_value)
                        })
    
    # Temporal analysis
    if analysis["temporal_columns"]:
        for col in analysis["temporal_columns"]:
            if df[col].notna().sum() > 0:
                analysis["distributions"][col] = {
                    "min_date": str(df[col].min()),
                    "max_date": str(df[col].max()),
                    "date_range_days": (df[col].max() - df[col].min()).days,
                    "unique_dates": df[col].nunique(),
                    "frequency": _detect_time_frequency(df[col])
                }
    
    return analysis


def _analyze_data_quality(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze data quality issues."""
    quality = {
        "missing_values": {},
        "whitespace_issues": {},
        "duplicates": {
            "total_duplicate_rows": len(df[df.duplicated()]),
            "duplicate_columns": []
        },
        "outliers": {},
        "data_consistency": []
    }
    
    # Missing values analysis
    for col in df.columns:
        null_count = df[col].isna().sum()
        if null_count > 0:
            quality["missing_values"][col] = {
                "count": int(null_count),
                "percentage": float(null_count / len(df) * 100)
            }
    
    # Whitespace issues for string columns
    for col in df.select_dtypes(include=['object']).columns:
        # Check for leading/trailing whitespace
        whitespace_count = df[col].apply(lambda x: isinstance(x, str) and (x != x.strip())).sum()
        if whitespace_count > 0:
            quality["whitespace_issues"][col] = int(whitespace_count)
        
        # Check for empty strings
        empty_string_count = (df[col] == '').sum()
        if empty_string_count > 0:
            quality["data_consistency"].append(f"Column '{col}' has {empty_string_count} empty strings")
    
    # Outliers for numeric columns
    for col in df.select_dtypes(include=[np.number]).columns:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)][col]
        if len(outliers) > 0:
            quality["outliers"][col] = {
                "count": len(outliers),
                "percentage": float(len(outliers) / len(df) * 100),
                "lower_bound": float(lower_bound),
                "upper_bound": float(upper_bound),
                "examples": outliers.head(5).tolist()
            }
    
    # Check for duplicate columns (same data)
    for i, col1 in enumerate(df.columns):
        for col2 in df.columns[i+1:]:
            if df[col1].equals(df[col2]):
                quality["duplicates"]["duplicate_columns"].append([col1, col2])
    
    return quality


def _get_statistical_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """Get statistical summary of the data."""
    summary = {
        "numeric_summary": {},
        "categorical_summary": {},
        "temporal_summary": {},
        "overall_patterns": []
    }
    
    # Numeric columns summary
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 0:
        summary["numeric_summary"] = {
            "count": len(numeric_cols),
            "columns": numeric_cols.tolist(),
            "all_positive": {col: bool((df[col] >= 0).all()) for col in numeric_cols},
            "has_zeros": {col: bool((df[col] == 0).any()) for col in numeric_cols},
            "variance": {col: float(df[col].var()) for col in numeric_cols}
        }
        
        # Check for potential percentages
        for col in numeric_cols:
            if (df[col] >= 0).all() and (df[col] <= 100).all():
                summary["overall_patterns"].append(f"Column '{col}' might be percentages (0-100 range)")
            elif (df[col] >= 0).all() and (df[col] <= 1).all():
                summary["overall_patterns"].append(f"Column '{col}' might be proportions (0-1 range)")
    
    # Categorical columns summary
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns
    if len(categorical_cols) > 0:
        summary["categorical_summary"] = {
            "count": len(categorical_cols),
            "columns": categorical_cols.tolist(),
            "unique_counts": {col: df[col].nunique() for col in categorical_cols},
            "most_frequent": {}
        }
        
        for col in categorical_cols:
            value_counts = df[col].value_counts()
            summary["categorical_summary"]["most_frequent"][col] = {
                "value": str(value_counts.index[0]) if len(value_counts) > 0 else None,
                "count": int(value_counts.iloc[0]) if len(value_counts) > 0 else 0,
                "percentage": float(value_counts.iloc[0] / len(df) * 100) if len(value_counts) > 0 else 0
            }
    
    # Check for ID columns
    for col in df.columns:
        if df[col].nunique() == len(df):
            summary["overall_patterns"].append(f"Column '{col}' appears to be a unique identifier")
    
    return summary


def _detect_patterns_from_pandas(df: pd.DataFrame, pandas_analysis: Dict[str, Any]) -> List[str]:
    """Detect visualization-relevant patterns from pandas analysis."""
    patterns = []
    
    # Time series pattern
    if pandas_analysis["temporal_columns"] and pandas_analysis["numeric_columns"]:
        patterns.append("time_series")
        
        # Check if it's regular time series
        for time_col in pandas_analysis["temporal_columns"]:
            freq = pandas_analysis["distributions"].get(time_col, {}).get("frequency")
            if freq and freq != "irregular":
                patterns.append(f"regular_time_series_{freq}")
    
    # Correlation pattern
    if pandas_analysis["correlations"].get("high_correlations"):
        patterns.append("high_correlation")
        patterns.append("multivariate")
    
    # Distribution patterns
    for col, dist in pandas_analysis["distributions"].items():
        if isinstance(dist, dict) and "skew" in dist:
            if abs(dist["skew"]) > 2:
                patterns.append("skewed_distribution")
                break
    
    # Categorical patterns
    if pandas_analysis["categorical_columns"]:
        # Check for hierarchical categories (e.g., Country > State > City)
        for col in pandas_analysis["categorical_columns"]:
            if any(sep in str(df[col].iloc[0]) for sep in ['/', '>', '->', '|'] if len(df) > 0):
                patterns.append("hierarchical_categories")
                break
    
    # Part-of-whole pattern
    numeric_cols = pandas_analysis["numeric_columns"]
    if len(numeric_cols) > 2:
        # Check if numeric columns sum to a total
        for i in range(len(df)):
            row_sum = df.iloc[i][numeric_cols].sum()
            if all(abs(row_sum - 100) < 0.01 for i in range(min(5, len(df)))):
                patterns.append("part_of_whole")
                break
    
    # Geographic pattern
    geo_keywords = ['lat', 'lon', 'latitude', 'longitude', 'country', 'state', 'city', 'zip', 'postal']
    if any(any(keyword in col.lower() for keyword in geo_keywords) for col in df.columns):
        patterns.append("geographic")
    
    return patterns


def _format_pandas_analysis(pandas_analysis: Dict, data_quality: Dict, statistical_summary: Dict) -> str:
    """Format pandas analysis into readable guide section."""
    guide = """## Detailed Pandas Analysis

### Data Overview
"""
    
    # Shape information
    shape = pandas_analysis['shape']
    guide += f"- **Rows**: {shape['rows']:,}\n"
    guide += f"- **Columns**: {shape['columns']}\n"
    guide += f"- **Memory Usage**: {shape['memory_usage']:.2f} MB\n"
    
    # Column types
    guide += "\n### Column Types\n"
    if pandas_analysis['numeric_columns']:
        guide += f"- **Numeric**: {', '.join(pandas_analysis['numeric_columns'])}\n"
    if pandas_analysis['temporal_columns']:
        guide += f"- **Temporal**: {', '.join(pandas_analysis['temporal_columns'])}\n"
    if pandas_analysis['categorical_columns']:
        guide += f"- **Categorical**: {', '.join(pandas_analysis['categorical_columns'])}\n"
    
    # Data quality issues
    if data_quality['missing_values']:
        guide += "\n### ⚠️ Missing Values\n"
        for col, info in data_quality['missing_values'].items():
            guide += f"- **{col}**: {info['count']} missing ({info['percentage']:.1f}%)\n"
    
    if data_quality['outliers']:
        guide += "\n### 📊 Outliers Detected\n"
        for col, info in data_quality['outliers'].items():
            guide += f"- **{col}**: {info['count']} outliers ({info['percentage']:.1f}%)\n"
            guide += f"  - Normal range: [{info['lower_bound']:.2f}, {info['upper_bound']:.2f}]\n"
    
    if data_quality['whitespace_issues']:
        guide += "\n### 🔧 Data Cleaning Needed\n"
        guide += "- Whitespace issues in: " + ", ".join(data_quality['whitespace_issues'].keys()) + "\n"
    
    # Statistical insights
    if statistical_summary['overall_patterns']:
        guide += "\n### 💡 Key Insights\n"
        for pattern in statistical_summary['overall_patterns']:
            guide += f"- {pattern}\n"
    
    # Correlations
    if pandas_analysis.get('correlations', {}).get('high_correlations'):
        guide += "\n### 🔗 Strong Correlations\n"
        for corr in pandas_analysis['correlations']['high_correlations']:
            guide += f"- **{corr['col1']}** ↔ **{corr['col2']}**: {corr['correlation']:.2f}\n"
    
    # Distribution insights
    if pandas_analysis['distributions']:
        guide += "\n### 📈 Distribution Insights\n"
        for col, dist in pandas_analysis['distributions'].items():
            if isinstance(dist, dict) and 'skew' in dist:
                if abs(dist['skew']) > 2:
                    guide += f"- **{col}**: Highly skewed (skewness: {dist['skew']:.2f})\n"
                if dist.get('zeros', 0) > shape['rows'] * 0.5:
                    guide += f"- **{col}**: Many zeros ({dist['zeros']} out of {shape['rows']})\n"
    
    # Temporal insights
    temporal_insights = []
    for col in pandas_analysis['temporal_columns']:
        dist = pandas_analysis['distributions'].get(col, {})
        if dist and 'frequency' in dist:
            temporal_insights.append(f"**{col}**: {dist['frequency']} frequency, spanning {dist.get('date_range_days', 'unknown')} days")
    
    if temporal_insights:
        guide += "\n### 📅 Temporal Data\n"
        for insight in temporal_insights:
            guide += f"- {insight}\n"
    
    return guide


def _detect_time_frequency(time_series: pd.Series) -> str:
    """Detect the frequency of a time series."""
    if len(time_series) < 2:
        return "insufficient_data"
    
    # Calculate differences between consecutive timestamps
    sorted_times = time_series.dropna().sort_values()
    if len(sorted_times) < 2:
        return "insufficient_data"
        
    diffs = sorted_times.diff().dropna()
    
    # Check for common frequencies
    median_diff = diffs.median()
    
    if median_diff <= pd.Timedelta(minutes=1):
        return "minutely"
    elif median_diff <= pd.Timedelta(hours=1):
        return "hourly"
    elif median_diff <= pd.Timedelta(days=1):
        return "daily"
    elif median_diff <= pd.Timedelta(days=7):
        return "weekly"
    elif median_diff <= pd.Timedelta(days=31):
        return "monthly"
    elif median_diff <= pd.Timedelta(days=366):
        return "yearly"
    else:
        return "irregular"


# Helper functions
def _is_bipartite(nodes: List[Dict], links: List[Dict]) -> bool:
    """Check if graph has bipartite structure."""
    if not nodes:
        return False
        
    types = set(n.get("type") for n in nodes if "type" in n)
    if len(types) != 2:
        return False
        
    # Verify links only connect different types
    node_types = {n.get("id"): n.get("type") for n in nodes}
    for link in links:
        source_type = node_types.get(link.get("source"))
        target_type = node_types.get(link.get("target"))
        if source_type and target_type and source_type == target_type:
            return False
            
    return True


def _has_temporal_data(nodes: List[Dict]) -> bool:
    """Check if nodes contain temporal data."""
    temporal_keys = ["timestamp", "time", "date", "datetime", "created_at", "updated_at"]
    return any(any(key in node for key in temporal_keys) for node in nodes)


def _is_hierarchical(nodes: List[Dict], links: List[Dict]) -> bool:
    """Check if network represents a hierarchy."""
    if not nodes or not links:
        return False
        
    # Check for parent references
    if any("parent" in node for node in nodes):
        return True
        
    # Check if it's a tree (no cycles, single root)
    # This is a simplified check
    in_degree = {}
    for link in links:
        target = link.get("target")
        in_degree[target] = in_degree.get(target, 0) + 1
        
    # Tree has exactly one root (no incoming edges)
    roots = [n for n in nodes if n.get("id") not in in_degree]
    return len(roots) == 1


def _is_date_string(value: str) -> bool:
    """Simple check if string looks like a date."""
    import re
    date_patterns = [
        r'^\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
        r'^\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
        r'^\d{4}-\d{2}-\d{2}T',  # ISO format
    ]
    return any(re.match(pattern, value) for pattern in date_patterns)


def _calculate_tree_depth(data: Dict, depth: int = 0) -> int:
    """Calculate maximum depth of tree."""
    if not isinstance(data, dict):
        return depth
        
    if "children" in data and data["children"]:
        child_depths = [_calculate_tree_depth(child, depth + 1) for child in data["children"]]
        return max(child_depths)
        
    return depth


def _count_leaves(data: Dict) -> int:
    """Count leaf nodes in tree."""
    if not isinstance(data, dict):
        return 0
        
    if "children" not in data or not data["children"]:
        return 1
        
    return sum(_count_leaves(child) for child in data["children"])


def _calculate_graph_metrics(nodes: List[Dict], links: List[Dict]) -> Dict[str, Any]:
    """Calculate comprehensive graph metrics for visualization decisions."""
    metrics = {
        "node_count": len(nodes),
        "edge_count": len(links),
        "density": 0,
        "average_degree": 0,
        "max_degree": 0,
        "min_degree": 0,
        "degree_variance": 0,
        "clustering_coefficient": 0,
        "connected_components": 1,
        "diameter": 0,
        "is_tree": False,
        "is_dag": False,
        "has_cycles": False,
        "modularity_hint": 0,
        "centralization": 0
    }
    
    if not nodes:
        return metrics
    
    # Build adjacency structure
    adjacency = {}
    degree_counts = {}
    
    for node in nodes:
        node_id = node.get("id")
        adjacency[node_id] = set()
        degree_counts[node_id] = 0
    
    # Build adjacency lists
    for link in links:
        source = link.get("source")
        target = link.get("target")
        if source in adjacency and target in adjacency:
            adjacency[source].add(target)
            adjacency[target].add(source)
            degree_counts[source] += 1
            degree_counts[target] += 1
    
    # Degree statistics
    degrees = list(degree_counts.values())
    if degrees:
        metrics["average_degree"] = sum(degrees) / len(degrees)
        metrics["max_degree"] = max(degrees)
        metrics["min_degree"] = min(degrees)
        metrics["degree_variance"] = np.var(degrees) if len(degrees) > 1 else 0
    
    # Density (already calculated, but recalculate for consistency)
    max_edges = len(nodes) * (len(nodes) - 1) / 2
    metrics["density"] = len(links) / max_edges if max_edges > 0 else 0
    
    # Clustering coefficient (simplified)
    if len(nodes) > 2:
        node_clustering = []
        for node_id, neighbors in adjacency.items():
            if len(neighbors) >= 2:
                # Count edges between neighbors
                neighbor_edges = 0
                neighbor_list = list(neighbors)
                for i in range(len(neighbor_list)):
                    for j in range(i + 1, len(neighbor_list)):
                        if neighbor_list[j] in adjacency[neighbor_list[i]]:
                            neighbor_edges += 1
                
                possible_edges = len(neighbors) * (len(neighbors) - 1) / 2
                if possible_edges > 0:
                    node_clustering.append(neighbor_edges / possible_edges)
        
        if node_clustering:
            metrics["clustering_coefficient"] = sum(node_clustering) / len(node_clustering)
    
    # Detect if it's a tree or DAG
    metrics["is_tree"] = len(links) == len(nodes) - 1 and _is_connected(adjacency)
    metrics["has_cycles"] = _has_cycles(adjacency)
    metrics["is_dag"] = not metrics["has_cycles"] and _is_directed_graph(links)
    
    # Centralization (degree centralization)
    if len(nodes) > 2 and metrics["max_degree"] > 0:
        centralization_sum = sum(metrics["max_degree"] - d for d in degrees)
        max_centralization = (len(nodes) - 1) * (len(nodes) - 2)
        metrics["centralization"] = centralization_sum / max_centralization if max_centralization > 0 else 0
    
    # Modularity hint (simplified - just check for clear clusters)
    if metrics["clustering_coefficient"] > 0.3 and metrics["density"] < 0.3:
        metrics["modularity_hint"] = 1  # Likely has community structure
    
    return metrics


def _calculate_visualization_scores(nodes: List[Dict], links: List[Dict], metrics: Dict[str, Any]) -> Dict[str, float]:
    """Calculate suitability scores for different visualization types."""
    scores = {
        "force_directed": 0,
        "matrix": 0,
        "tree": 0,
        "radial_tree": 0,
        "sankey": 0,
        "chord": 0,
        "hierarchical_edge_bundling": 0,
        "arc_diagram": 0,
        "bipartite": 0,
        "clustered_force": 0
    }
    
    node_count = len(nodes)
    edge_count = len(links)
    density = metrics.get("density", 0)
    
    # Force-directed layout scoring
    if node_count <= 200 and density < 0.3:
        scores["force_directed"] = 0.9
    elif node_count <= 500 and density < 0.2:
        scores["force_directed"] = 0.7
    else:
        scores["force_directed"] = max(0, 1 - (node_count / 1000) - density)
    
    # Matrix visualization scoring
    if node_count > 100 or density > 0.3:
        scores["matrix"] = min(1, 0.5 + (density * 0.5) + (node_count / 1000))
    else:
        scores["matrix"] = 0.3
    
    # Tree layout scoring
    if metrics.get("is_tree", False):
        scores["tree"] = 1.0
        scores["radial_tree"] = 0.9 if node_count > 50 else 0.7
    elif metrics.get("is_dag", False):
        scores["tree"] = 0.8
        scores["radial_tree"] = 0.7
    
    # Sankey diagram scoring
    if _is_bipartite(nodes, links) or all("value" in l or "weight" in l for l in links):
        scores["sankey"] = 0.9
    
    # Clustered force layout
    if metrics.get("clustering_coefficient", 0) > 0.5 and node_count < 500:
        scores["clustered_force"] = 0.9
    
    # Arc diagram for ordered data
    if node_count < 100 and any("order" in n or "index" in n for n in nodes):
        scores["arc_diagram"] = 0.7
    
    # Normalize scores
    max_score = max(scores.values()) if scores.values() else 1
    if max_score > 0:
        for key in scores:
            scores[key] = scores[key] / max_score
    
    return scores


def _detect_advanced_patterns(nodes: List[Dict], links: List[Dict], metrics: Dict[str, Any]) -> List[str]:
    """Detect advanced graph patterns for visualization."""
    patterns = []
    
    # Hub and spoke pattern
    if metrics.get("max_degree", 0) > len(nodes) * 0.3:
        patterns.append("hub_and_spoke")
    
    # Small world network
    if metrics.get("clustering_coefficient", 0) > 0.5 and metrics.get("average_degree", 0) > 2:
        patterns.append("small_world")
    
    # Scale-free network (power law distribution hint)
    if metrics.get("degree_variance", 0) > metrics.get("average_degree", 1) * 2:
        patterns.append("scale_free")
    
    # Modular/Community structure
    if metrics.get("modularity_hint", 0) > 0:
        patterns.append("modular")
    
    # Star pattern
    if metrics.get("centralization", 0) > 0.8:
        patterns.append("star")
    
    # Chain/Path pattern
    if metrics.get("average_degree", 0) <= 2.1 and metrics.get("is_tree", False):
        patterns.append("chain")
    
    # Complete or near-complete graph
    if metrics.get("density", 0) > 0.8:
        patterns.append("complete_graph")
    
    # Sparse graph
    if metrics.get("density", 0) < 0.1:
        patterns.append("sparse")
    
    return patterns


def _is_connected(adjacency: Dict[str, set]) -> bool:
    """Check if graph is connected using DFS."""
    if not adjacency:
        return True
    
    visited = set()
    start = next(iter(adjacency.keys()))
    stack = [start]
    
    while stack:
        node = stack.pop()
        if node not in visited:
            visited.add(node)
            stack.extend(adjacency[node] - visited)
    
    return len(visited) == len(adjacency)


def _has_cycles(adjacency: Dict[str, set]) -> bool:
    """Detect if graph has cycles using DFS."""
    visited = set()
    rec_stack = set()
    
    def dfs(node, parent=None):
        visited.add(node)
        rec_stack.add(node)
        
        for neighbor in adjacency.get(node, set()):
            if neighbor not in visited:
                if dfs(neighbor, node):
                    return True
            elif neighbor != parent and neighbor in rec_stack:
                return True
        
        rec_stack.remove(node)
        return False
    
    for node in adjacency:
        if node not in visited:
            if dfs(node):
                return True
    
    return False


def _is_directed_graph(links: List[Dict]) -> bool:
    """Check if the graph is directed based on link properties."""
    # Simple heuristic: if links have direction indicators
    return any("directed" in link or "arrow" in link for link in links)


# Serve the MCP server
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test mode
        print("D3 Visualization Advisor")
        print("\nThis tool analyzes your data and tells you:")
        print("- Which visualizations to use and why")
        print("- Which to avoid and why")
        print("- Specific thresholds and decision logic")
        print("- Complete D3.js code examples")
        
        # Test with sample data
        test_network = {
            "nodes": [{"id": "a", "type": "user"}, {"id": "b", "type": "item"}],
            "links": [{"source": "a", "target": "b"}]
        }
        
        # Direct function call for testing
        import asyncio
        async def test():
            return await analyze_and_recommend_visualization.fn(
                data=json.dumps(test_network),
                purpose="Show user-item interactions"
            )
        result = asyncio.run(test())
        print("\nSample output:")
        print(result[:500] + "...")
    else:
        # Run as MCP server
        import asyncio
        asyncio.run(mcp.run())