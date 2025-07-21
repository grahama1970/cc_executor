# MCP Servers: An AI Agent's Retrievable Memory System

This README consolidates and supersedes the previous `README_short.md` and the original `README.md`.
It has been audited against the current source code (see list at the end of this file)
and should be treated as the single source of truth for how the MCP servers work.

----

## 1 Conceptual Foundations

### 1.1 Memory as a Knowledge Graph
Traditional AI agents are stateless and solve each problem from scratch.
The MCP system changes that paradigm by persisting every action, error, outcome,
and tool call in an **ArangoDB** graph database; edges capture semantic relations
so the agent can perform associative recall and learn from experience.

### 1.2 The Core Learning Loop

```text
┌──────────────────────────┐      1. start_journey      ┌─────────────────────────┐
│        AI Agent          ├───────────────────────────►│   mcp_tool_journey      │
│      (Claude Code)       │                            │ (select first tool)     │
└───────────┬──────────────┘                            └────────────┬────────────┘
            │                                                       │ 2. execute
            │ 6. complete_journey                                   │   tool
            │  (reward back-prop)                                   │
            │                                                       ▼
┌───────────┴──────────────┐                           ┌──────────────────────────┐
│ mcp_tool_journey         │◄──────────────────────────┤  *any MCP tool*          │
│ (update Q-values)        │    5. reward              │  (e.g. mcp_cc_execute)   │
└───────────┬──────────────┘                           └────────────┬─────────────┘
            ▲                                                       │ 3. record_tool_step
            │                                                       │    & get next tool
┌───────────┴──────────────┐                           ┌───────────▼─────────────┐
│ mcp_outcome_adjudicator  ├───────────────────────────┤   mcp_tool_journey      │
│ (determine success)      │     4. adjudicate         │   (choose next tool)    │
└──────────────────────────┘                           └─────────────────────────┘
```

Reinforcement-learning parameters (Q-learning + Thompson sampling) are updated
step-by-step, allowing the agent to converge on optimal tool sequences.

----

## 2 System Architecture

```text
AI Agent  ⇆  MCP Servers  ⇆  ArangoDB + FAISS  ⇆  External CLIs / LLMs
```

Servers are grouped by responsibility:

- **Orchestrators**: high-level workflows (`mcp_debugging_assistant.py`).
- **Learning Engine**: realtime RL (`mcp_tool_journey.py`).
- **Outcome Oracle**: reward calculation (`mcp_outcome_adjudicator.py`).
- **Offline Optimiser**: analyse history (`mcp_tool_sequence_optimizer.py`).
- **Code Intelligence**: AST analysis (`mcp_code_analyzer.py`), Multi-tool review (`mcp_code_review.py`).
- **Content Processing**: Document extraction (`mcp_crawler.py`), Response validation (`mcp_response_validator.py`).
- **Domain Tools**: DB (`mcp_arango_tools.py`), Visualisation (`mcp_d3_visualizer.py`, `mcp_d3_visualization_advisor.py`),
  LLM access (`mcp_llm_instance.py`, `mcp_litellm_request.py`, `mcp_litellm_batch.py`,
  `mcp_universal_llm_executor.py`), Task delegation (`mcp_cc_execute.py`).

### 2.1 Database Collections
- `log_events`, `errors_and_failures`, `tool_journey_edges`, `q_values`, `thompson_params`,
  `pattern_similarity` and others are created automatically on first use.

----

## 3 Server Catalogue

| # | File | Purpose | Key MCP tools / resources |
|---|------|---------|---------------------------|
| 1 | `mcp_arango_tools.py` | Graph-DB interface, pattern analysis, FAISS similarity search | `query`, `insert`, `edge`, `build_similarity_graph`, `find_similar_documents`, `detect_communities`, `detect_anomalies`, `analyze_pattern_evolution` |
| 2 | `mcp_tool_journey.py` | Journey & realtime RL | `start_journey`, `record_tool_step`, `complete_journey`, `query_similar_journeys` |
| 3 | `mcp_outcome_adjudicator.py` | Truth oracle, reward calc | `adjudicate_outcome` |
| 4 | `mcp_tool_sequence_optimizer.py` | Offline sequence mining | `optimize_tool_sequence`, `find_successful_sequences`, `analyze_sequence_performance` |
| 5 | `mcp_debugging_assistant.py` | Pre-made debugging workflows | `resolve_error_workflow`, `analyze_error_cascade`, `suggest_preventive_measures`, `create_debugging_report`, `compare_debugging_approaches` |
| 6 | `mcp_cc_execute.py` | Spawn Claude-Code subprocesses & verify filesystem side-effects | `execute_task`, `execute_task_list`, `verify_execution` |
| 7 | `mcp_llm_instance.py` | Unified CLI interface for Claude / GPT / Gemini etc | `execute_llm`, `stream_llm`, `estimate_tokens`, `configure_llm` |
| 8 | `mcp_litellm_request.py` | Single LiteLLM call with retries | `process_single_request` |
| 9 | `mcp_litellm_batch.py` | Parallel LiteLLM batch | `process_batch_requests` |
|10| `mcp_universal_llm_executor.py` | Generic subprocess wrapper around arbitrary LLM CLIs | `execute_llm`, `concatenate_files`, `estimate_tokens`, `parse_llm_output` |
|11| `mcp_d3_visualization_advisor.py` | Decide best D3 layout for given data | `analyze_and_recommend_visualization` |
|12| `mcp_d3_visualizer.py` | Generate interactive HTML visualisations | `generate_graph_visualization`, `generate_intelligent_visualization`, `visualize_arango_graph` |
|13| `mcp_crawler.py` | Extract & process HTML, RST, Markdown, and other document formats | `crawl_url`, `extract_content`, `parse_structured_data` |
|14| `mcp_code_analyzer.py` | AST-based code analysis using tree-sitter for 40+ languages | `analyze_code`, `extract_ast`, `find_patterns`, `analyze_dependencies` |
|15| `mcp_code_review.py` | Multi-tool code review with security & quality checks | `start_review`, `get_review_results`, `list_available_tools` |
|16| `mcp_response_validator.py` | Validate & transform API responses to ensure consistency | `validate_response`, `transform_response`, `check_schema_compliance` |
|17| *(archived)* | *KiloCode integration moved to slash commands* | *See /docs/code_review/SIMPLE_KILOCODE_WORKFLOW.md* |

----

## 4 Learning Use-Cases

### 4.1 Error → Solution
1. `start_journey` with task description and context.  
2. `mcp_arango_tools.find_similar_documents` to recall past fixes.  
3. Execute a candidate fix, e.g. `mcp_cc_execute.execute_task("uv pip install pandas")`.  
4. `adjudicate_outcome` verifies success (hard evidence preferred).  
5. `complete_journey` back-propagates reward.

### 4.2 Tool Sequence Optimisation
`tool_journey_edges` edges store success statistics; offline optimiser
periodically boosts high-performing sequences to solve the cold-start problem.

### 4.3 Graph-Based Pattern Discovery
FAISS + ArangoDB enables semantic clustering of errors, solutions and tool journeys;
graph algorithms (Louvain, HNSW etc.) surface non-obvious patterns.

### 4.4 KiloCode Integration - Simple Slash Command Workflow

KiloCode integration is now handled through simple slash commands and file exchange:

1. **Claude Code**: Human runs `/code-review` → generates review request file
2. **KiloCode**: Human runs `/review-contextual` → saves results file  
3. **Claude Code**: Human runs `/implement-fixes` → reads results and implements changes

**Benefits**:
- Uses both tools' native slash commands
- Uses KiloCode's own LLM (no external API calls)
- Simple file exchange in `/docs/code_review/reviewer/incoming/`
- Follows orchestrator guide naming conventions
- Human-friendly at each step

See `/docs/code_review/SIMPLE_KILOCODE_WORKFLOW.md` for complete documentation.

### 4.5 Enhanced Problem-Solving with New MCP Servers

The addition of specialized MCP servers significantly enhances the agent's ability to solve complex problems:

#### **Code Intelligence** (`mcp_code_analyzer.py`, `mcp_code_review.py`)
- **AST-Based Understanding**: Using tree-sitter, the agent can analyze code structure across 40+ languages, understanding function calls, dependencies, and patterns without executing code
- **Security & Quality Checks**: Multi-tool code review catches SQL injection risks, hardcoded secrets, and style violations before they become problems
- **Pattern Learning**: AST analysis results are stored in ArangoDB, allowing the agent to learn common code patterns and anti-patterns over time

#### **Content Processing** (`mcp_crawler.py`, `mcp_response_validator.py`)
- **Multi-Format Document Handling**: Extract structured content from HTML, Markdown, RST, and other formats, enabling the agent to learn from documentation and web resources
- **Response Consistency**: Validate and transform API responses to ensure all MCP servers return data in a consistent format, reducing integration errors
- **Schema Compliance**: Automatic validation against expected schemas prevents downstream processing failures

#### **Synergistic Benefits**
1. **Error Prevention**: Code review + AST analysis catch issues before execution
2. **Documentation Learning**: Crawler extracts technical docs → Agent learns best practices → Code analyzer applies them
3. **Reliable Integration**: Response validator ensures all tools speak the same "language" in the graph database
4. **Pattern Discovery**: AST patterns + Graph algorithms reveal non-obvious code relationships

These servers transform the agent from reactive (fixing errors after they occur) to proactive (preventing errors through analysis and validation).

----

## 5 Why FAISS?
- ArangoDB lacks native vector search.
- FAISS provides logarithmic nearest-neighbour search and supports millions of vectors.
- Similarity edges are written back to the graph so regular AQL traversals work.

----

## 6 Two-Level Code Review System
If enabled, a post-task hook triggers a fast Haiku/mini-model review (Level 1)
followed by a deeper Gemini/Opus review (Level 2). Results are stored in ArangoDB
so the agent learns code quality patterns over time.

----

## 7 Configuration
Create a `.env` file or export environment variables:

```bash
ARANGO_HOST=localhost
ARANGO_PORT=8529
ARANGO_DATABASE=logger_agent
ARANGO_USERNAME=root
ARANGO_PASSWORD=changeme

# LLM API Keys
ANTHROPIC_API_KEY=...
GOOGLE_AI_API_KEY=...
OPENAI_API_KEY=...
```

----

## 8 File Inventory (auto-generated)
```text
mcp_arango_tools.py
mcp_tool_journey.py
mcp_outcome_adjudicator.py
mcp_tool_sequence_optimizer.py
mcp_debugging_assistant.py
mcp_cc_execute.py
mcp_llm_instance.py
mcp_litellm_request.py
mcp_litellm_batch.py
mcp_universal_llm_executor.py
mcp_d3_visualizer.py
mcp_d3_visualization_advisor.py
mcp_crawler.py
mcp_code_analyzer.py
mcp_code_review.py
mcp_response_validator.py
mcp_kilocode_review.py
mcp_kilocode_workflow.py
```

----

## 9 Future Roadmap
- Federated learning of Q-values without sharing sensitive data.
- Causal analysis of successful tool sequences.
- Predictive failure analysis.
- Automatic bootstrapping from git history.

----

## 10 Changelog
- 2025-07-19: First unified README produced by `kilocode` agent.

_End of document_