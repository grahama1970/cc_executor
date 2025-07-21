# MCP Tools Comparison: Test Scenarios vs Current Implementation

## Current MCP Tools Available (as of Jan 21, 2025)

### Basic MCP-exposed tools (via @mcp.tool decorator):
1. **schema()** - Get database schema
2. **query(aql, bind_vars)** - Execute AQL queries  
3. **insert(...)** - Insert log events
4. **edge(...)** - Create graph edges
5. **upsert(...)** - Update or insert documents

### Internal ArangoTools class methods (not exposed as MCP tools):
- `english_to_aql_patterns()` - Natural language to AQL conversion
- `add_glossary_term()` - Add glossary entries
- `link_glossary_terms()` - Link glossary terms
- `research_database_issue()` - Research database problems
- `extract_lesson()` - Extract lessons from solutions
- Various CRUD operations

## Tools Expected by Test Scenarios (Not Found)

### Advanced Analytics Tools:
1. **build_similarity_graph()** - Build FAISS similarity graphs
2. **find_similar_documents()** - Find semantically similar documents
3. **detect_communities()** - Detect communities in graph
4. **detect_anomalies()** - Find anomalous patterns
5. **analyze_pattern_evolution()** - Track patterns over time

### Pattern Analysis Tools:
6. **find_patterns()** - Find solution patterns
7. **natural_language_to_aql()** - Convert NL to AQL (exists but not exposed)

## Key Findings

### 1. Missing MCP Decorators
Some functionality exists in the ArangoTools class but isn't exposed as MCP tools:
- `english_to_aql_patterns()` exists but isn't decorated with `@mcp.tool()`
- Pattern finding logic exists within methods but not as standalone tools

### 2. Removed Features
The test scenarios reference advanced ML features that appear to have been removed:
- FAISS integration for similarity search
- Embedding-based semantic search
- Advanced graph analytics (community detection, anomaly detection)

### 3. Simplified Implementation
The current implementation focuses on:
- Basic CRUD operations
- Simple graph relationships
- Direct AQL query execution
- Glossary management
- Basic research capabilities

## Recommendations

### Immediate Actions:

1. **Expose Existing Functionality**
   Add MCP decorators to useful internal methods:
   ```python
   @mcp.tool()
   async def natural_language_to_aql(query: str, context: Optional[str] = None) -> str:
       # Wrapper around english_to_aql_patterns
   ```

2. **Update Test Scenarios**
   Rewrite scenarios to test what actually exists:
   - Test AQL query generation
   - Test glossary functionality
   - Test research capabilities
   - Remove references to ML/analytics features

3. **Document Current Capabilities**
   Update documentation to reflect actual functionality:
   - Basic graph operations
   - Query capabilities
   - Glossary management
   - Research features

### Future Considerations:

1. **Implement Core Missing Features**
   If advanced analytics are needed:
   - Add similarity search using ArangoDB's built-in features
   - Implement basic pattern detection using AQL
   - Add simple anomaly detection based on statistics

2. **Create New Test Scenarios**
   Design scenarios that test:
   - Complex AQL queries
   - Graph traversals
   - Glossary relationships
   - Research workflow

## Test Scenario Remapping

### Scenarios That Can Work (with modifications):
- **Scenario 1-5**: Basic operations using insert/query/edge
- **NEW Scenarios**: Test glossary, research, and NL-to-AQL features

### Scenarios That Cannot Work:
- **Scenario 6-20**: All require non-existent ML/analytics tools

## Conclusion

The test scenarios were written for a much more ambitious version of the tool that included advanced ML and analytics features. The current implementation is simpler and focuses on basic database operations, glossary management, and research capabilities. The test scenarios need a complete rewrite to match the actual implementation.