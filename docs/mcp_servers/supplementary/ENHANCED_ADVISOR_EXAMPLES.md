# Enhanced D3 Visualization Advisor Examples

This document shows how the enhanced visualization advisor analyzes different data types using pandas and provides specific recommendations.

## Example 1: ArangoDB Edge Collection

```python
# Agent receives data from ArangoDB query
arango_edges = [
    {"_from": "users/123", "_to": "posts/456", "action": "liked", "timestamp": "2024-01-15T10:30:00Z"},
    {"_from": "users/124", "_to": "posts/456", "action": "commented", "timestamp": "2024-01-15T11:00:00Z"},
    {"_from": "users/123", "_to": "posts/457", "action": "shared", "timestamp": "2024-01-15T12:00:00Z"},
    {"_from": "users/125", "_to": "posts/456", "action": "liked", "timestamp": "2024-01-15T12:30:00Z"}
]

# Agent calls the advisor
result = await analyze_and_recommend_visualization(
    json.dumps(arango_edges),
    "Show user interactions with posts"
)
```

### Advisor Response:

```markdown
# D3.js Visualization Recommendation Guide

## Your Data Analysis

**Data Shape**: network
**Key Metrics**: {"density": 0.25}
**Detected Patterns**: arangodb_graph
**Potential Issues**: None

## Network Visualization Recommendations

### 🔷 ArangoDB Graph Data Detected!

Your data appears to be from an ArangoDB edge collection with `_from` and `_to` fields.

**Data Format**: ArangoDB Edge Collection
**Detected**: 4 edges connecting 5 unique nodes

### ✅ RECOMMENDED: Bipartite Layout
**Why**: Your data has two distinct node types (users and posts) with interactions between them.

**D3 Implementation**:
```javascript
// Separate nodes by type
const users = nodes.filter(n => n.id.startsWith('users'));
const posts = nodes.filter(n => n.id.startsWith('posts'));

// Position in two columns
const xScale = d3.scaleOrdinal()
    .domain(['user', 'post'])
    .range([100, width - 100]);
```

### ✅ ALTERNATIVE: Temporal Network
**Why**: Your edges have timestamps - show interactions over time.
```

## Example 2: Time Series with Data Quality Issues

```python
# Sales data with outliers and missing values
sales_data = [
    {"date": "2024-01-01", "sales": 1000, "returns": 50, "profit_margin": 0.15},
    {"date": "2024-01-02", "sales": 1200, "returns": None, "profit_margin": 0.18},  # Missing
    {"date": "2024-01-03", "sales": 950, "returns": 30, "profit_margin": 0.12},
    {"date": "2024-01-04", "sales": 15000, "returns": 100, "profit_margin": 0.45},  # Outlier
    {"date": "2024-01-05", "sales": 1100, "returns": 45, "profit_margin": 0.16}
]

result = await analyze_and_recommend_visualization(
    json.dumps(sales_data),
    "Analyze sales performance and identify issues"
)
```

### Advisor Response with Pandas Analysis:

```markdown
# D3.js Visualization Recommendation Guide

## Your Data Analysis

**Data Shape**: tabular
**Detected Patterns**: time_series, regular_time_series_daily
**Potential Issues**: None

## Detailed Pandas Analysis

### Data Overview
- **Rows**: 5
- **Columns**: 4
- **Memory Usage**: 0.00 MB

### Column Types
- **Numeric**: sales, returns, profit_margin
- **Temporal**: date

### ⚠️ Missing Values
- **returns**: 1 missing (20.0%)

### 📊 Outliers Detected
- **sales**: 1 outliers (20.0%)
  - Normal range: [-1187.50, 3337.50]
  - Examples: [15000]

### 💡 Key Insights
- Column 'profit_margin' might be proportions (0-1 range)

### 📅 Temporal Data
- **date**: daily frequency, spanning 4 days

## Tabular Data Visualization Recommendations

### ✅ RECOMMENDED: Line Chart with Annotations
**Why**: Time series with outliers needs clear marking.

```javascript
// Highlight outliers
const outlierThreshold = 3337.50;

// Add annotation for outlier
const annotations = data
    .filter(d => d.sales > outlierThreshold)
    .map(d => ({
        note: { label: "Outlier: " + d.sales },
        x: x(parseTime(d.date)),
        y: y(d.sales),
        dy: -30,
        dx: 30
    }));
```

### Data Cleaning Recommendations:
1. **Handle missing returns**: Use interpolation or forward-fill
2. **Investigate outlier**: Is 15,000 a data entry error?
3. **Verify profit margins**: Unusually high on outlier day
```

## Example 3: Highly Correlated Multivariate Data

```python
# Environmental monitoring data
env_data = [
    {"temperature_c": 20, "humidity_pct": 65, "air_quality_index": 45, "location": "Station A"},
    {"temperature_c": 22, "humidity_pct": 60, "air_quality_index": 50, "location": "Station A"},
    {"temperature_c": 25, "humidity_pct": 55, "air_quality_index": 58, "location": "Station B"},
    {"temperature_c": 28, "humidity_pct": 48, "air_quality_index": 65, "location": "Station B"},
    {"temperature_c": 30, "humidity_pct": 42, "air_quality_index": 72, "location": "Station C"},
    {"temperature_c": 32, "humidity_pct": 38, "air_quality_index": 78, "location": "Station C"}
]
```

### Advisor Response:

```markdown
## Detailed Pandas Analysis

### 🔗 Strong Correlations
- **temperature_c** ↔ **humidity_pct**: -0.99
- **temperature_c** ↔ **air_quality_index**: 0.98

### 📈 Distribution Insights
- All numeric columns show strong linear relationships

## Visualization Recommendations

### ✅ RECOMMENDED: Scatter Plot Matrix
**Why**: Perfect for showing multiple correlations at once.

```javascript
// Create scatter plot matrix
const variables = ['temperature_c', 'humidity_pct', 'air_quality_index'];
const size = 200;
const padding = 20;

// Create scales for each variable
const scales = {};
variables.forEach(v => {
    scales[v] = d3.scaleLinear()
        .domain(d3.extent(data, d => d[v]))
        .range([0, size]);
});

// Create cell for each pair
variables.forEach((v1, i) => {
    variables.forEach((v2, j) => {
        const cell = svg.append('g')
            .attr('transform', `translate(${i * (size + padding)}, ${j * (size + padding)})`);
        
        if (i !== j) {
            // Scatter plot
            cell.selectAll('circle')
                .data(data)
                .join('circle')
                .attr('cx', d => scales[v1](d[v1]))
                .attr('cy', d => scales[v2](d[v2]))
                .attr('r', 3)
                .attr('fill', d => colorScale(d.location));
        } else {
            // Diagonal: variable name
            cell.append('text')
                .attr('x', size / 2)
                .attr('y', size / 2)
                .attr('text-anchor', 'middle')
                .text(v1);
        }
    });
});
```

### ✅ ALTERNATIVE: Parallel Coordinates
**Why**: Shows patterns across all dimensions simultaneously.
```

## Example 4: Part-of-Whole Data (Percentages)

```python
# Market share data that sums to 100%
market_data = [
    {"quarter": "Q1", "product_a": 35, "product_b": 40, "product_c": 25},
    {"quarter": "Q2", "product_a": 30, "product_b": 45, "product_c": 25},
    {"quarter": "Q3", "product_a": 28, "product_b": 42, "product_c": 30},
    {"quarter": "Q4", "product_a": 32, "product_b": 38, "product_c": 30}
]
```

### Advisor Detects:

```markdown
### 💡 Key Insights
- Numeric columns sum to 100 (percentages detected)
- Part-of-whole relationship identified

### ✅ RECOMMENDED: Stacked Area Chart
**Why**: Shows how composition changes over time.

```javascript
// Stack the data
const stack = d3.stack()
    .keys(['product_a', 'product_b', 'product_c'])
    .offset(d3.stackOffsetNone);

const series = stack(data);

// Area generator
const area = d3.area()
    .x(d => x(d.data.quarter))
    .y0(d => y(d[0]))
    .y1(d => y(d[1]))
    .curve(d3.curveMonotoneX);

// Draw areas
svg.selectAll('.area')
    .data(series)
    .join('path')
    .attr('class', 'area')
    .attr('d', area)
    .attr('fill', d => colorScale(d.key));
```
```

## Example 5: Geographic Data Detection

```python
# Store locations with coordinates
store_data = [
    {"store_id": "S001", "city": "New York", "latitude": 40.7128, "longitude": -74.0060, 
     "revenue": 1500000, "customers": 5000},
    {"store_id": "S002", "city": "Chicago", "latitude": 41.8781, "longitude": -87.6298,
     "revenue": 1200000, "customers": 4000},
    {"store_id": "S003", "city": "Los Angeles", "latitude": 34.0522, "longitude": -118.2437,
     "revenue": 1800000, "customers": 6000}
]
```

### Advisor Geographic Detection:

```markdown
**Detected Patterns**: geographic

### 💡 Key Insights
- Geographic coordinates detected (latitude/longitude)
- Additional metrics available for bubble sizing

### ✅ RECOMMENDED: Map Visualization
**Why**: Natural way to show geographic data.

**Options**:
1. **Bubble Map**: Size bubbles by revenue
2. **Choropleth**: If aggregating by region
3. **Connection Map**: If showing flows between locations

```javascript
// Using D3 with geographic projection
const projection = d3.geoAlbersUsa()
    .scale(1000)
    .translate([width / 2, height / 2]);

// Size scale for bubbles
const sizeScale = d3.scaleSqrt()
    .domain([0, d3.max(data, d => d.revenue)])
    .range([5, 50]);

// Plot cities
svg.selectAll('circle')
    .data(data)
    .join('circle')
    .attr('cx', d => projection([d.longitude, d.latitude])[0])
    .attr('cy', d => projection([d.longitude, d.latitude])[1])
    .attr('r', d => sizeScale(d.revenue))
    .attr('fill', 'steelblue')
    .attr('opacity', 0.7);
```
```

## Key Benefits of Enhanced Analysis

1. **Pandas-Powered Insights**:
   - Automatic dtype detection
   - Statistical summaries (mean, std, quartiles)
   - Correlation analysis
   - Outlier detection using IQR method
   - Missing value analysis
   - Whitespace and data quality checks

2. **ArangoDB Awareness**:
   - Recognizes `_from`/`_to` edge format
   - Handles graph traversal results
   - Converts to D3-compatible format

3. **Pattern Detection**:
   - Time series with frequency detection
   - Geographic data recognition
   - Part-of-whole relationships
   - Skewed distributions
   - High correlations

4. **Smart Recommendations**:
   - Specific thresholds (>500 nodes → table)
   - Data cleaning suggestions
   - Alternative visualizations
   - Performance optimizations

5. **Code Generation**:
   - Working D3.js snippets
   - Adaptive parameters based on data
   - Best practices built-in

The advisor now provides comprehensive guidance that helps agents make informed decisions about visualization, ensuring the most appropriate chart type is selected based on deep data analysis.