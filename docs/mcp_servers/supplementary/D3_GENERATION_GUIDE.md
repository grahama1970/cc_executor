# D3.js Intelligent Visualization Generation Guide

## Decision Framework for AI Agents

### 1. Data Analysis Phase

Before generating any visualization, analyze these characteristics:

```javascript
const dataAnalysis = {
  // Size metrics
  nodeCount: nodes.length,
  linkCount: links.length,
  density: linkCount / (nodeCount * (nodeCount - 1)),
  avgDegree: (2 * linkCount) / nodeCount,
  
  // Data characteristics
  hasTimestamp: nodes.some(n => n.timestamp),
  hasHierarchy: nodes.some(n => n.parent),
  hasCategories: new Set(nodes.map(n => n.type || n.category)).size,
  hasWeights: links.some(l => l.weight || l.value),
  
  // Complexity assessment
  visualComplexity: calculateComplexity(nodeCount, density),
  readabilityScore: estimateReadability(nodeCount, linkCount)
};
```

### 2. Visualization Decision Matrix

| Condition | Recommended Visualization | Fallback Options |
|-----------|--------------------------|------------------|
| **nodes > 500 OR density > 0.5** | `table`, `summary_stats` | Paginated table, aggregated view |
| **nodes < 50 AND density < 0.1** | `force-directed` | `force-clustered` if categories > 2 |
| **nodes 50-200 AND density < 0.2** | `force-clustered` | `hierarchical` if tree-like |
| **density > 0.3 OR (nodes > 100 AND density > 0.2)** | `adjacency_matrix` | `heatmap`, `chord_diagram` |
| **hasTimestamp AND timePoints > 3** | `timeline_network` | `alluvial` if categorical flow |
| **hasHierarchy AND maxDepth < 6** | `tree`, `dendrogram` | `treemap` if size matters |
| **isBipartite(nodes, links)** | `bipartite_layout` | `sankey` if flow data |
| **links have source→target→value** | `sankey_diagram` | `chord` if circular relationships |

### 3. Code Generation Patterns

#### Base Structure (All Visualizations)
```javascript
class IntelligentVisualization {
  constructor(data, config) {
    this.data = this.validateData(data);
    this.config = this.mergeConfig(config);
    this.analysis = this.analyzeData();
    this.vizType = this.selectVisualization();
  }
  
  validateData(data) {
    // Handle edge cases
    if (!data || !data.nodes || data.nodes.length === 0) {
      return { nodes: [], links: [], isEmpty: true };
    }
    // Ensure consistent structure
    return {
      nodes: data.nodes.map((n, i) => ({ id: i, ...n })),
      links: data.links.filter(l => 
        this.nodeExists(l.source) && this.nodeExists(l.target)
      )
    };
  }
  
  selectVisualization() {
    const { nodeCount, density, complexity } = this.analysis;
    
    // NO VISUALIZATION cases
    if (complexity === 'excessive') {
      return 'tabular_summary';
    }
    
    // Specific pattern detection
    if (this.detectBipartite()) return 'bipartite';
    if (this.detectTimeSeries()) return 'timeline';
    if (this.detectHierarchy()) return 'tree';
    if (this.detectFlow()) return 'sankey';
    
    // Density-based selection
    if (density > 0.3) return 'matrix';
    if (nodeCount < 50) return 'force';
    return 'force_clustered';
  }
}
```

#### Force-Directed with Clustering
```javascript
generateClusteredForce() {
  // Auto-detect clusters
  const clusters = d3.group(this.data.nodes, d => d.type || d.category);
  
  // Custom force for clustering
  const clusterForce = alpha => {
    for (const [key, nodes of clusters]) {
      const centroid = d3.mean(nodes, d => d.x);
      nodes.forEach(node => {
        node.vx += (centroid.x - node.x) * alpha * 0.1;
      });
    }
  };
  
  // Adaptive parameters based on data
  const simulation = d3.forceSimulation()
    .force('link', d3.forceLink()
      .distance(d => this.adaptiveLinkDistance(d)))
    .force('charge', d3.forceManyBody()
      .strength(d => this.adaptiveChargeStrength(d)))
    .force('cluster', clusterForce)
    .force('collision', d3.forceCollide()
      .radius(d => this.adaptiveNodeRadius(d)));
}
```

#### Adjacency Matrix for Dense Graphs
```javascript
generateMatrix() {
  // Order nodes for pattern visibility
  const nodeOrder = this.computeOptimalOrder();
  
  // Create matrix
  const matrix = [];
  nodeOrder.forEach((source, i) => {
    nodeOrder.forEach((target, j) => {
      const link = this.findLink(source, target);
      matrix.push({
        x: i,
        y: j,
        value: link ? link.value : 0,
        source: source,
        target: target
      });
    });
  });
  
  // Color scale for values
  const colorScale = d3.scaleSequential()
    .domain([0, d3.max(matrix, d => d.value)])
    .interpolator(d3.interpolateViridis);
}
```

#### Hybrid Visualizations
```javascript
generateHybrid() {
  // Example: Overview + Detail
  const overview = this.generateMinimap();
  const detail = this.generateMainView();
  
  // Link interactions
  overview.on('brush', extent => {
    detail.zoomTo(extent);
  });
  
  // Example: Matrix + Network overlay
  const matrix = this.generateMatrix();
  const selectedCells = matrix.filter(d => d.value > threshold);
  const overlayNetwork = this.generatePartialNetwork(selectedCells);
}
```

### 4. Edge Case Handlers

```javascript
const edgeCaseHandlers = {
  emptyData: () => ({
    type: 'message',
    content: 'No data to visualize',
    icon: 'info'
  }),
  
  singleNode: (node) => ({
    type: 'centered_node',
    layout: { x: width/2, y: height/2 },
    message: 'Single node visualization'
  }),
  
  noLinks: (nodes) => ({
    type: 'grid_layout',
    positions: d3.range(nodes.length).map(i => ({
      x: (i % cols) * spacing,
      y: Math.floor(i / cols) * spacing
    }))
  }),
  
  tooManyNodes: (data) => ({
    type: 'aggregated_view',
    clusters: this.computeClusters(data),
    summary: this.computeSummaryStats(data)
  })
};
```

### 5. Adaptive Parameters

```javascript
const adaptiveParams = {
  nodeRadius: (node, analysis) => {
    const base = 5;
    const scaleFactor = Math.max(1, 50 / analysis.nodeCount);
    const importance = node.degree || 1;
    return base * scaleFactor * Math.sqrt(importance);
  },
  
  linkDistance: (link, analysis) => {
    const base = 30;
    const densityFactor = 1 + (1 - analysis.density) * 2;
    return base * densityFactor;
  },
  
  chargeStrength: (node, analysis) => {
    const base = -30;
    const sparsityFactor = 1 / (analysis.density + 0.1);
    return base * sparsityFactor;
  }
};
```

### 6. Responsive Design

```javascript
const responsiveFeatures = {
  // Dynamic sizing
  dimensions: () => {
    const container = d3.select('#viz-container').node();
    return {
      width: container.clientWidth,
      height: container.clientHeight,
      margin: { top: 20, right: 20, bottom: 40, left: 40 }
    };
  },
  
  // Breakpoint adjustments
  adjustForViewport: (width) => {
    if (width < 600) {
      return {
        showLabels: false,
        simplifyAxes: true,
        reduceTicks: true
      };
    }
    return { showLabels: true };
  },
  
  // Zoom/Pan for large visualizations
  enableZoom: () => {
    const zoom = d3.zoom()
      .scaleExtent([0.1, 10])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });
    svg.call(zoom);
  }
};
```

### 7. Performance Optimizations

```javascript
const performanceOptimizations = {
  // Canvas for large datasets
  useCanvas: (nodeCount) => nodeCount > 1000,
  
  // Progressive rendering
  progressiveRender: (nodes, chunkSize = 100) => {
    let index = 0;
    const renderChunk = () => {
      const chunk = nodes.slice(index, index + chunkSize);
      // Render chunk
      index += chunkSize;
      if (index < nodes.length) {
        requestAnimationFrame(renderChunk);
      }
    };
    renderChunk();
  },
  
  // Level of detail
  levelOfDetail: (zoomLevel) => ({
    showLabels: zoomLevel > 0.5,
    showDetails: zoomLevel > 1,
    showMiniatures: zoomLevel < 0.3
  })
};
```

## Decision Logic Summary

1. **Analyze first**: Never jump to visualization without understanding the data
2. **Respect limits**: Tables and summaries are valid "visualizations" for complex data
3. **Match patterns**: Use specialized layouts for detected patterns (temporal, hierarchical, flow)
4. **Handle edges**: Always have fallbacks for empty, single, or excessive data
5. **Stay adaptive**: Parameters should scale with data characteristics
6. **Think hybrid**: Combine techniques when single approach isn't sufficient
7. **Ensure responsive**: Generated code must work across viewports

This guide ensures AI agents generate appropriate, performant, and insightful D3.js visualizations tailored to the specific characteristics of each dataset.