# Agent Workflow Example: ArangoDB → Intelligence → D3 → Verify

This document shows the complete workflow of how an agent uses the MCP tools to create intelligent visualizations.

## Step 1: Agent Gets Data from ArangoDB

```python
# Agent executes ArangoDB query
arango_result = await mcp__arangodb__query({
    "query": """
    FOR doc IN error_logs
        FILTER doc.timestamp > DATE_NOW() - 7 * 24 * 60 * 60 * 1000
        COLLECT error_type = doc.error_type, solution = doc.solution
        AGGREGATE count = COUNT(1)
        RETURN {
            source: error_type,
            target: solution,
            value: count
        }
    """
})

# Result might look like:
data = {
    "nodes": [
        {"id": "timeout_error", "type": "error", "count": 45},
        {"id": "connection_error", "type": "error", "count": 23},
        {"id": "auth_error", "type": "error", "count": 12},
        {"id": "retry_solution", "type": "solution", "effectiveness": 0.78},
        {"id": "cache_solution", "type": "solution", "effectiveness": 0.92},
        {"id": "refresh_token", "type": "solution", "effectiveness": 0.95}
    ],
    "links": [
        {"source": "timeout_error", "target": "retry_solution", "value": 35},
        {"source": "timeout_error", "target": "cache_solution", "value": 10},
        {"source": "connection_error", "target": "retry_solution", "value": 20},
        {"source": "auth_error", "target": "refresh_token", "value": 12}
    ]
}
```

## Step 2: Agent Calls chart_intel for Analysis

```python
# Agent asks for intelligence about this data
intel_result = await mcp__d3_intelligence__chart_intel({
    "data": json.dumps(data),
    "purpose": "show which solutions are most effective for each error type",
    "context": "for DevOps team dashboard"
})
```

### Intelligence Response:

```markdown
# Chart Intelligence Report

## Data Analysis

### Shape and Structure
{
  "type": "network",
  "node_count": 6,
  "link_count": 4,
  "is_directed": true,
  "has_weights": true
}

### Detected Patterns
bipartite, flow

### Data Quality Issues
✓ No major quality issues detected

## Visualization Recommendations

### Recommended Visualizations

**1. Sankey Diagram**
   - Perfect for showing flow from errors to solutions with weights

**2. Bipartite Layout**
   - Two-column layout clearly separates errors and solutions

**3. Chord Diagram**
   - If you want to emphasize the circular relationship

### Visualizations to Avoid

**❌ Standard force layout**
   - Bipartite structure would be lost in general layout

## D3.js Code Generation Guidance

For a Sankey diagram with your data:
- Use d3-sankey plugin for layout calculation
- Color errors in red shades, solutions in green shades
- Width of flows should represent the count
- Add hover tooltips showing exact numbers
- Consider adding effectiveness as opacity
```

## Step 3: Agent Decides and Generates D3 Code

Based on the intelligence, the agent decides:

> "Given that the data is bipartite (errors → solutions) with weighted flows, and the purpose is to show effectiveness, I'll create a Sankey diagram. This will clearly show which solutions handle which errors and in what volume."

```javascript
// Agent generates custom D3 code
const d3_code = `
// Set up dimensions
const margin = {top: 40, right: 100, bottom: 40, left: 100};
const width = 800 - margin.left - margin.right;
const height = 400 - margin.top - margin.bottom;

// Create SVG
const svg = d3.select('#chart')
    .append('svg')
    .attr('width', width + margin.left + margin.right)
    .attr('height', height + margin.top + margin.bottom);

const g = svg.append('g')
    .attr('transform', \`translate(\${margin.left},\${margin.top})\`);

// Create Sankey generator
const sankey = d3.sankey()
    .nodeWidth(20)
    .nodePadding(10)
    .extent([[0, 0], [width, height]]);

// Prepare data for Sankey
const sankeyData = sankey({
    nodes: data.nodes.map(d => ({...d})),
    links: data.links.map(d => ({...d}))
});

// Color scales
const errorColor = d3.scaleOrdinal()
    .domain(['error'])
    .range(['#e74c3c', '#c0392b', '#e67e22']);

const solutionColor = d3.scaleOrdinal()
    .domain(['solution'])
    .range(['#27ae60', '#2ecc71', '#16a085']);

// Draw links (flows)
const link = g.append('g')
    .selectAll('.link')
    .data(sankeyData.links)
    .join('path')
    .attr('class', 'link')
    .attr('d', d3.sankeyLinkHorizontal())
    .attr('stroke-width', d => Math.max(1, d.width))
    .attr('fill', 'none')
    .attr('stroke', d => d.source.type === 'error' ? '#e74c3c' : '#27ae60')
    .attr('opacity', 0.5);

// Draw nodes
const node = g.append('g')
    .selectAll('.node')
    .data(sankeyData.nodes)
    .join('g')
    .attr('class', 'node')
    .attr('transform', d => \`translate(\${d.x0},\${d.y0})\`);

node.append('rect')
    .attr('height', d => d.y1 - d.y0)
    .attr('width', sankey.nodeWidth())
    .attr('fill', d => d.type === 'error' ? errorColor(d.id) : solutionColor(d.id))
    .attr('stroke', '#000')
    .attr('stroke-width', 1);

// Add labels
node.append('text')
    .attr('x', d => d.type === 'error' ? -6 : sankey.nodeWidth() + 6)
    .attr('y', d => (d.y1 - d.y0) / 2)
    .attr('dy', '0.35em')
    .attr('text-anchor', d => d.type === 'error' ? 'end' : 'start')
    .text(d => d.id.replace(/_/g, ' '))
    .style('font-size', '12px');

// Add effectiveness indicators for solutions
node.filter(d => d.type === 'solution')
    .append('text')
    .attr('x', sankey.nodeWidth() + 6)
    .attr('y', d => (d.y1 - d.y0) / 2 + 15)
    .attr('text-anchor', 'start')
    .text(d => \`\${(d.effectiveness * 100).toFixed(0)}% effective\`)
    .style('font-size', '10px')
    .style('fill', '#666');

// Tooltips
const tooltip = d3.select('.tooltip');

link.on('mouseover', function(event, d) {
    tooltip.transition().duration(200).style('opacity', .9);
    tooltip.html(\`\${d.source.id} → \${d.target.id}<br>Count: \${d.value}\`)
        .style('left', (event.pageX + 10) + 'px')
        .style('top', (event.pageY - 28) + 'px');
})
.on('mouseout', () => tooltip.transition().duration(500).style('opacity', 0));

// Title
svg.append('text')
    .attr('x', width / 2 + margin.left)
    .attr('y', 20)
    .attr('text-anchor', 'middle')
    .style('font-size', '18px')
    .style('font-weight', 'bold')
    .text('Error to Solution Flow Analysis');
`;
```

## Step 4: Agent Calls chart_render

```python
# Agent renders the visualization
render_result = await mcp__d3_intelligence__chart_render({
    "d3_code": d3_code,
    "title": "Error Resolution Effectiveness",
    "container_id": "chart"
})

# Result:
{
    "success": true,
    "filepath": "/tmp/agent_visualizations/viz_20250718_143022_a3f7b9c2.html",
    "url": "file:///tmp/agent_visualizations/viz_20250718_143022_a3f7b9c2.html",
    "filename": "viz_20250718_143022_a3f7b9c2.html",
    "puppeteer_ready": true
}
```

## Step 5: Agent Uses Puppeteer to Verify

```python
# Agent uses the Puppeteer MCP tool to verify
verification_result = await mcp__puppeteer__puppeteer_navigate({
    "url": render_result["url"]
})

# Take screenshot
screenshot = await mcp__puppeteer__puppeteer_screenshot({
    "name": "sankey_verification",
    "selector": "#chart"
})

# Test interactivity - hover over a flow
await mcp__puppeteer__puppeteer_evaluate({
    "script": """
    // Hover over first link to trigger tooltip
    const firstLink = document.querySelector('.link');
    const event = new MouseEvent('mouseover', {
        bubbles: true,
        cancelable: true,
        view: window
    });
    firstLink.dispatchEvent(event);
    
    // Check if tooltip appeared
    const tooltip = document.querySelector('.tooltip');
    const isVisible = tooltip && parseFloat(window.getComputedStyle(tooltip).opacity) > 0;
    
    return {
        tooltipVisible: isVisible,
        tooltipContent: tooltip ? tooltip.textContent : null,
        linkCount: document.querySelectorAll('.link').length,
        nodeCount: document.querySelectorAll('.node').length
    };
    """
})

# Result confirms:
{
    "tooltipVisible": true,
    "tooltipContent": "timeout_error → retry_solution\nCount: 35",
    "linkCount": 4,
    "nodeCount": 6
}
```

## Step 6: Agent Reports Success

> "I've successfully created a Sankey diagram showing the flow from errors to solutions. The visualization clearly shows:
> 
> 1. **Retry solution** handles most timeout and connection errors (55 total)
> 2. **Cache solution** is 92% effective but only used for 10 timeout errors
> 3. **Refresh token** perfectly handles all auth errors (95% effectiveness)
> 
> The width of the flows represents the count of errors handled by each solution. Hovering over any flow shows the exact count.
> 
> Screenshot saved as 'sankey_verification.png' confirming the chart rendered correctly with all interactive features working."

## Key Benefits of This Workflow

1. **Data-Driven Decisions**: The agent doesn't guess - it analyzes the data structure first
2. **Intelligent Recommendations**: Based on actual patterns, not preconceived notions
3. **Custom Code Generation**: The agent writes D3 code specifically for this data
4. **Verification**: Automated testing ensures the visualization actually works
5. **Full Creative Control**: Agent can create ANY visualization, not limited to templates

## Alternative Decisions the Agent Might Make

Based on different data characteristics:

- **If nodes > 1000**: "The intelligence report warns about too many nodes. I'll create an aggregated summary table instead with sparklines showing trends."

- **If density > 0.5**: "This network is too dense for a node-link diagram. I'll create an adjacency matrix with color intensity showing connection strength."

- **If temporal pattern detected**: "Since the data has timestamps, I'll create an animated timeline showing how error-solution relationships evolve over time."

- **If no patterns detected**: "The data doesn't show clear patterns. I'll create an interactive data table with search and sort capabilities for exploration."

This workflow ensures agents make informed visualization decisions based on data characteristics rather than defaulting to generic templates.