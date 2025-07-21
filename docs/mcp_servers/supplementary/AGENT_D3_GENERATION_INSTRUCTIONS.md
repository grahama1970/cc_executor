# Agent Instructions for D3.js Visualization Generation

## Overview
You are generating custom D3.js visualizations based on data analysis. You have COMPLETE CREATIVE FREEDOM to generate any visualization code, inspired by modern libraries like Nivo but not limited to their chart types.

## CRITICAL: When NOT to Visualize

**Always consider if a table or text summary is better than a chart:**

### Use a TABLE when:
- Data has >10 columns of attributes to compare
- Showing exact values is more important than patterns
- Data is primarily categorical with no clear relationships
- User needs to sort/filter/search the data
- There are >500 data points without clear groupings
- Data density >0.5 (too many connections to visualize clearly)

### Use TEXT SUMMARY when:
- Data has <5 items
- Simple statistics tell the whole story
- The "visualization" would just be labeled numbers
- Showing a trend that can be stated in one sentence

### Use HYBRID (Table + Mini Visualizations) when:
- Need both exact values and visual patterns
- Sparklines or mini-charts per row would help
- Overview + detail is required

## Visualization Inspiration from Nivo

Nivo (https://nivo.rocks) demonstrates modern, interactive visualizations. Here's what you can create:

### 1. Bar Charts (When to use)
```javascript
// Use for comparing discrete categories
// Good for: top 10 lists, category comparisons, time-based counts
// Avoid when: >20 categories, continuous data, no clear order

// Example: Error counts by type
const margin = {top: 40, right: 80, bottom: 40, left: 80};
const width = 800 - margin.left - margin.right;
const height = 400 - margin.top - margin.bottom;

const x = d3.scaleBand()
    .domain(data.map(d => d.category))
    .range([0, width])
    .padding(0.1);

const y = d3.scaleLinear()
    .domain([0, d3.max(data, d => d.value)])
    .range([height, 0]);

// Animated bars with hover effects
svg.selectAll(".bar")
    .data(data)
    .enter().append("rect")
    .attr("class", "bar")
    .attr("x", d => x(d.category))
    .attr("width", x.bandwidth())
    .attr("y", height)
    .attr("height", 0)
    .transition()
    .duration(800)
    .attr("y", d => y(d.value))
    .attr("height", d => height - y(d.value));
```

### 2. Line Charts (When to use)
```javascript
// Use for continuous data over time, trends, multiple series
// Good for: time series, performance metrics, comparative trends
// Avoid when: <3 data points, discrete categories, no time element

// Multi-line with hover tooltip
const line = d3.line()
    .x(d => x(d.date))
    .y(d => y(d.value))
    .curve(d3.curveMonotoneX); // Smooth curves

// Add gradient fill under line
const gradient = svg.append("defs")
    .append("linearGradient")
    .attr("id", "line-gradient")
    .attr("gradientUnits", "userSpaceOnUse")
    .attr("x1", 0).attr("y1", y(0))
    .attr("x2", 0).attr("y2", y(maxValue));
```

### 3. Pie/Donut Charts (When to use)
```javascript
// Use for part-to-whole relationships, max 5-7 categories
// Good for: distribution, composition, percentages
// Avoid when: >7 slices, similar values, need exact comparisons

const pie = d3.pie()
    .value(d => d.value)
    .sort(null);

const arc = d3.arc()
    .innerRadius(radius * 0.6) // Donut hole
    .outerRadius(radius);

// Animated entrance
arcs.append("path")
    .attr("d", arc)
    .attr("fill", d => colorScale(d.data.category))
    .transition()
    .duration(1000)
    .attrTween("d", function(d) {
        const interpolate = d3.interpolate({startAngle: 0, endAngle: 0}, d);
        return t => arc(interpolate(t));
    });
```

### 4. Scatter Plots (When to use)
```javascript
// Use for correlation, clusters, outliers, 2-3 variables
// Good for: regression, groupings, anomaly detection
// Avoid when: >1000 points without zoom, overlapping points

// With size and color encoding
circles.enter().append("circle")
    .attr("cx", d => x(d.xValue))
    .attr("cy", d => y(d.yValue))
    .attr("r", d => radiusScale(d.size))
    .attr("fill", d => colorScale(d.category))
    .attr("opacity", 0.7)
    .on("mouseover", showTooltip)
    .on("mouseout", hideTooltip);

// Add zoom behavior for large datasets
const zoom = d3.zoom()
    .scaleExtent([1, 10])
    .on("zoom", zoomed);
```

### 5. Heatmaps (When to use)
```javascript
// Use for correlation matrices, time vs category, density
// Good for: patterns in 2D data, calendars, confusion matrices
// Avoid when: sparse data, need exact values, <3x3 grid

const colorScale = d3.scaleSequential()
    .interpolator(d3.interpolateViridis)
    .domain([minValue, maxValue]);

cells.enter().append("rect")
    .attr("x", d => x(d.column))
    .attr("y", d => y(d.row))
    .attr("width", x.bandwidth())
    .attr("height", y.bandwidth())
    .attr("fill", d => colorScale(d.value))
    .on("mouseover", function(event, d) {
        // Show value on hover
        tooltip.html(`${d.row} × ${d.column}: ${d.value}`)
            .style("opacity", 1);
    });
```

### 6. Network Graphs (When to use)
```javascript
// Use for relationships, flows, hierarchies, <200 nodes
// Good for: dependencies, social networks, knowledge graphs
// Avoid when: >200 nodes (use matrix), no meaningful layout

// Force-directed with clustering
const simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).distance(50))
    .force("charge", d3.forceManyBody().strength(-100))
    .force("cluster", forceCluster()) // Custom clustering
    .force("collision", d3.forceCollide().radius(15));

// Add convex hulls for clusters
const hulls = svg.append("g")
    .selectAll("path")
    .data(clusters)
    .enter().append("path")
    .attr("class", "hull")
    .style("fill", d => d.color)
    .style("opacity", 0.2);
```

### 7. Sankey Diagrams (When to use)
```javascript
// Use for flows, multi-stage processes, energy/material flow
// Good for: conversion funnels, budget flow, process analysis
// Avoid when: no clear flow direction, circular dependencies

const sankey = d3.sankey()
    .nodeWidth(15)
    .nodePadding(10)
    .extent([[1, 1], [width - 1, height - 6]]);

// Gradient links showing flow
link.append("linearGradient")
    .attr("id", d => `gradient-${d.index}`)
    .attr("gradientUnits", "userSpaceOnUse")
    .attr("x1", d => d.source.x1)
    .attr("x2", d => d.target.x0);
```

### 8. Treemaps (When to use)
```javascript
// Use for hierarchical data with size metric
// Good for: file systems, budgets, nested categories
// Avoid when: deep hierarchy (>4 levels), similar sizes

const treemap = d3.treemap()
    .size([width, height])
    .padding(2)
    .round(true);

cells.append("rect")
    .attr("x", d => d.x0)
    .attr("y", d => d.y0)
    .attr("width", d => d.x1 - d.x0)
    .attr("height", d => d.y1 - d.y0)
    .attr("fill", d => colorScale(d.parent.data.name));
```

### 9. Radar/Spider Charts (When to use)
```javascript
// Use for multivariate comparisons, 3-8 dimensions
// Good for: skill assessments, product comparisons, balance
// Avoid when: >8 axes, very different scales, single item

const angleSlice = Math.PI * 2 / axes.length;
const radarLine = d3.lineRadial()
    .radius(d => rScale(d.value))
    .angle((d, i) => i * angleSlice)
    .curve(d3.curveLinearClosed);
```

### 10. Stream Graphs (When to use)
```javascript
// Use for time-based composition changes
// Good for: topic evolution, market share over time
// Avoid when: exact values needed, volatile data

const stack = d3.stack()
    .keys(categories)
    .offset(d3.stackOffsetWiggle);

const area = d3.area()
    .x(d => x(d.data.date))
    .y0(d => y(d[0]))
    .y1(d => y(d[1]))
    .curve(d3.curveCardinal);
```

## Advanced Techniques

### 1. Responsive Design
```javascript
// Always make visualizations responsive
function resize() {
    const newWidth = container.clientWidth;
    const newHeight = container.clientHeight;
    
    svg.attr("width", newWidth)
       .attr("height", newHeight);
    
    // Update scales and redraw
    x.range([0, newWidth]);
    y.range([newHeight, 0]);
    
    // Update elements
    updateVisualization();
}

window.addEventListener("resize", resize);
```

### 2. Smooth Transitions
```javascript
// Animate changes for better UX
selection.transition()
    .duration(750)
    .ease(d3.easeCubicInOut)
    .attr("transform", d => `translate(${x(d)},${y(d)})`);
```

### 3. Interactive Features
```javascript
// Brushing for selection
const brush = d3.brush()
    .extent([[0, 0], [width, height]])
    .on("end", brushended);

// Zoom and pan
const zoom = d3.zoom()
    .scaleExtent([1, 10])
    .translateExtent([[0, 0], [width, height]]);

// Hover effects
.on("mouseover", function(event, d) {
    d3.select(this)
        .transition()
        .duration(100)
        .attr("r", r * 1.5);
})
```

### 4. Annotations
```javascript
// Add context with annotations
const annotations = [{
    note: { label: "Peak error rate" },
    x: x(peakDate),
    y: y(peakValue),
    dy: -30,
    dx: 30
}];

const makeAnnotations = d3.annotation()
    .annotations(annotations);

svg.append("g")
    .call(makeAnnotations);
```

### 5. Dark Mode Support
```javascript
// Check for dark mode preference
const isDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;

const theme = {
    background: isDarkMode ? '#1a1a1a' : '#ffffff',
    text: isDarkMode ? '#e0e0e0' : '#333333',
    gridLines: isDarkMode ? '#333333' : '#e0e0e0'
};
```

## Decision Framework

```javascript
function selectVisualization(data, purpose) {
    // 1. Check if visualization is appropriate
    if (data.length < 3) return "text_summary";
    if (data.length > 1000 && !data.clusters) return "aggregated_table";
    
    // 2. Identify data characteristics
    const characteristics = analyzeData(data);
    
    // 3. Match to visualization type
    if (characteristics.isTemporal && characteristics.hasMultipleSeries) {
        return "multi_line_chart";
    } else if (characteristics.isHierarchical && characteristics.hasSize) {
        return "treemap";
    } else if (characteristics.isNetwork && characteristics.nodeCount < 200) {
        return "force_directed_graph";
    } else if (characteristics.isPartToWhole && characteristics.categories <= 7) {
        return "donut_chart";
    } else if (characteristics.needsCorrelation) {
        return "scatter_plot";
    } else if (characteristics.isFlow) {
        return "sankey_diagram";
    } else if (characteristics.isDense2D) {
        return "heatmap";
    } else {
        return "smart_table"; // With inline sparklines
    }
}
```

## Code Generation Template

```javascript
// Your generated D3 code should follow this structure:

// 1. Setup
const margin = {top: 20, right: 20, bottom: 40, left: 50};
const width = containerWidth - margin.left - margin.right;
const height = containerHeight - margin.top - margin.bottom;

// 2. Scales (adapt to data)
const xScale = /* appropriate scale based on data type */;
const yScale = /* appropriate scale based on data type */;
const colorScale = /* categorical, sequential, or diverging */;

// 3. SVG setup with proper structure
const svg = d3.select(container)
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom);

const g = svg.append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);

// 4. Axes (if applicable)
const xAxis = d3.axisBottom(xScale);
const yAxis = d3.axisLeft(yScale);

// 5. Main visualization elements
// ... your creative code here ...

// 6. Interactions (hover, click, zoom, brush)
// ... interaction handlers ...

// 7. Legend (if needed)
// ... legend code ...

// 8. Responsive behavior
// ... resize handlers ...
```

## Remember

1. **Less is often more** - A clean table might be better than a cluttered chart
2. **Consider your audience** - Scientists might want different viz than business users
3. **Performance matters** - Canvas for >1000 points, aggregation for >10000
4. **Accessibility** - Include ARIA labels, keyboard navigation, color-blind friendly palettes
5. **Test your output** - Ensure the generated code actually runs without errors

You have complete freedom to innovate beyond these examples. The goal is to create the most effective representation for the specific data and use case.