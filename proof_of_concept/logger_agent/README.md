Okay, this is a very important step to make this complex logging and introspection system understandable and usable for both human developers and the autonomous agent.

Here is the comprehensive `README.md` for this effort, meticulously designed to cover all aspects of the ArangoDB-backed agent logging system.

---

# ArangoDB-Backed Agent Logging System

This project implements a sophisticated, centralized logging and introspection system for autonomous AI agents, leveraging ArangoDB's multi-model capabilities. Designed to enhance debugging, learning, and self-recovery, this system transforms raw log data into a structured, queryable, and graph-ready knowledge base.

It replaces traditional flat-file logging with a unified ArangoDB backend, providing agents with "CRUD-like" access to their own execution history, errors, outputs, and learned insights.

## Table of Contents

1.  [Introduction](#1-introduction)
2.  [Features](#2-features)
3.  [Architecture Overview](#3-architecture-overview)
    *   [Data Flow](#data-flow)
    *   [Core Components](#core-components)
    *   [ArangoDB Schema](#arangodb-schema)
4.  [Setup & Initialization](#4-setup--initialization)
    *   [Prerequisites](#prerequisites)
    *   [Python Package Installation](#python-package-installation)
    *   [ArangoDB Configuration](#arangodb-configuration)
    *   [Database & Schema Initialization](#database--schema-initialization)
5.  [Usage Guidelines for Agents (and Humans)](#5-usage-guidelines-for-agents-and-humans)
    *   [Integrating into a Python Script](#integrating-into-a-python-script)
    *   [Agent-Specific Log Interaction](#agent-specific-log-interaction)
6.  [Agent Interaction & Learning Strategy](#6-agent-interaction--learning-strategy)
7.  [Prompts Directory (`prompts/`)](#7-prompts-directory-prompts)
8.  [Code Structure Overview](#8-code-structure-overview)
9.  [Troubleshooting](#9-troubleshooting)
10. [License](#10-license)

---

## 1. Introduction

Traditional logging often falls short for autonomous AI agents. Cryptic error messages, scattered log files, and a lack of structured history make self-diagnosis and learning a significant challenge. This project addresses these limitations by introducing an **ArangoDB-backed logging system** designed specifically for agent introspection.

By centralizing all execution data into a flexible multi-model database, agents can now:
*   **Query their own past actions:** Understand "what happened when."
*   **Search for patterns:** Find recurring errors or successful resolutions.
*   **Recall learned facts:** Access a self-maintained knowledge base of debugging insights.
*   **Build causal graphs:** Infer relationships between errors, attempts, and solutions for deeper reasoning.

This system aims to empower agents to create self-contained scripts, recover from errors more effectively, and continuously improve their performance through self-reflection.

## 2. Features

*   **Unified Log Storage:** All log messages (DEBUG, INFO, WARNING, ERROR, CRITICAL), script outputs, and agent-specific learnings are stored in a single `log_events` collection in ArangoDB.
*   **Structured Logging:** Log records are stored as rich JSON documents, preserving context, file/function/line information, and `extra` data.
*   **Asynchronous Writes:** A non-blocking `loguru` sink pushes logs to an `asyncio.Queue`, with a background thread/task writing to ArangoDB, ensuring minimal performance impact on the main script.
*   **Traceable Script Runs:** Each script execution is assigned a unique `execution_id`, recorded in the `script_runs` collection, and bound to all logs for that run. This enables end-to-end traceability of script lifecycles.
*   **Agent-Centric API (`AgentLogManager`):** Provides a simplified, "CRUD-like" interface on the `logger` object for agents:
    *   `logger.query_logs(aql_query)`: Execute custom AQL for precise data retrieval.
    *   `logger.search_bm25_logs(text_query)`: Perform powerful full-text search (BM25-like relevance) on log messages, exceptions, and outputs.
    *   `logger.prune_logs(...)`: Efficiently delete old logs based on time, category, or execution ID.
    *   `logger.get_latest_response(script_name, execution_id)`: Retrieve the structured JSON output of a specific script run.
    *   `logger.log_agent_learning(message, function_name)`: Explicitly record debugging insights and lessons learned.
    *   `logger.start_run(...)` / `logger.end_run(...)`: Mark the lifecycle of a script execution.
*   **Graph-Ready Data:** Log documents include fields (`execution_id`, `function`, `file`, `line`) that enable the agent to build complex graph relationships (e.g., `(ErrorLog)-[CAUSED_BY]->(AgentLearning)`) using separate graph utilities for advanced reasoning.
*   **Verbose Error Reporting:** Loguru's `diagnose=True` provides detailed tracebacks and local variable states for errors directly within the database.
*   **Helper Prompts:** A `prompts/` directory provides pre-written guides and AQL examples for common complex agent tasks.

## 3. Architecture Overview

### Data Flow

```mermaid
graph TD
    A[Python Script] -- Loguru.info/error/debug --> B(Loguru Logger)
    B -- Configured Sink (Non-blocking) --> C(Asyncio.Queue)
    C -- Background Writer Thread/Task --> D[ArangoDB]
    D -- Structured Log Events (log_events collection)
    D -- Script Run Metadata (script_runs collection)
    E[Agent / Human] -- AgentLogManager API --> D
```

### Core Components

*   **Loguru:** The chosen logging library for its flexibility, structured logging capabilities, and sink management.
*   **`src/arangodb/core/utils/arango_log_sink.py`:**
    *   A custom `loguru` sink function.
    *   Receives log records, extracts relevant fields, and pushes them into an `asyncio.Queue`.
    *   Runs in a background thread to prevent blocking the main application.
    *   Handles batching of log writes to ArangoDB for efficiency.
*   **`src/arangodb/core/utils/agent_log_manager.py`:**
    *   The **singleton** class that orchestrates the entire logging system.
    *   Initializes `loguru` with the `arango_log_sink`.
    *   Manages the ArangoDB connection for the background writer.
    *   Exposes the unified `logger` API (e.g., `logger.query_logs`, `logger.start_run`).
*   **`src/arangodb/core/utils/arango_init.py`:**
    *   A standalone script to be run *once* for initial ArangoDB database and schema setup.
    *   Creates the log database, collections, and ArangoSearch View.
*   **ArangoDB:**
    *   **`script_logs` database:** A dedicated database for all logging data, isolating it from other project data.
    *   **`script_runs` collection:** Stores high-level metadata for each script execution (start/end time, script name, mode, final status).
    *   **`log_events` collection:** Stores individual log messages as rich documents. Contains `timestamp`, `level`, `message`, `file`, `function`, `line`, `exception`, `extra` (where `execution_id`, `log_category`, and `payload` for outputs reside).
    *   **`log_events_view`:** An ArangoSearch View over `log_events` configured for full-text search (BM25-like) on fields like `message`, `exception.value`, `extra.payload`, and `log_category`.
*   **`prompts/` directory:** Contains Markdown files with detailed instructions and AQL examples for complex agent tasks, serving as "recipes."

### ArangoDB Schema

**Database:** `script_logs` (or custom name via `ARANGO_DB` env var)

**Collections:**

*   `script_runs` (Document Collection)
    *   `_key` (same as `execution_id`)
    *   `script_name` (e.g., `my_script`)
    *   `start_time` (ISO 8601 string)
    *   `end_time` (ISO 8601 string, or `null`)
    *   `mode` (e.g., "working", "debug")
    *   `status` ("running", "completed", "failed")
    *   `pid` (process ID)
    *   `thread_id` (thread ID)
    *   `messages_logged` (count of log messages for this run)

*   `log_events` (Document Collection)
    *   `timestamp` (ISO 8601 string, `record["time"].isoformat()`)
    *   `level` (e.g., "INFO", "ERROR")
    *   `message` (the log string)
    *   `file` (`{"name": "...", "path": "..."}`)
    *   `function` (function name)
    *   `line` (line number)
    *   `elapsed` (seconds since logger start)
    *   `process` (`{"id": ..., "name": "..."}`)
    *   `thread` (`{"id": ..., "name": "..."}`)
    *   `exception` (`{"type": "...", "value": "...", "traceback": "..."}`, if error)
    *   `log_category` (e.g., "INFO", "ERROR", "AGENT_LEARNING", "SCRIPT_FINAL_RESPONSE")
    *   `extra` (dict containing all bound variables, e.g., `{"execution_id": "...", "payload": {...}}`)

**ArangoSearch Views:**

*   `log_events_view`
    *   Linked to `log_events` collection.
    *   Indexed fields for full-text search using `text_en` analyzer:
        *   `message`
        *   `level`
        *   `function`
        *   `file`
        *   `extra.payload` (for searching within script outputs)
        *   `exception.value` (for searching within error messages)
        *   `log_category`

## 4. Setup & Initialization

### Prerequisites

*   **Docker:** For running ArangoDB.
*   **Python 3.8+**
*   **`uv`:** (Recommended package installer) or `pip`.

### Python Package Installation

Install required Python packages using `uv` (recommended for speed and dependency resolution):

```bash
uv pip install python-arango loguru uvloop tqdm rapidfuzz sentence-transformers rich colorama redis litellm
```

### ArangoDB Configuration

The logging system connects to ArangoDB using environment variables. Set these in your shell's profile (`~/.bashrc`, `~/.zshrc`) or explicitly before running scripts.

*   `ARANGO_HOST`: Your ArangoDB instance URL (e.g., `http://localhost:8529`).
*   `ARANGO_DB`: The name of the *new* database dedicated to logs (e.g., `script_logs`).
*   `ARANGO_USER`: Username for ArangoDB access (default: `root`).
*   `ARANGO_PASSWORD`: Password for ArangoDB access (default: `openSesame`).

**Example:**

```bash
export ARANGO_HOST="http://localhost:8529"
export ARANGO_DB="script_logs"
export ARANGO_USER="root"
export ARANGO_PASSWORD="openSesame"
```

### Database & Schema Initialization

You must run a one-time script to create the necessary ArangoDB database, collections, and ArangoSearch view.

**AGENT_INSTRUCTIONS:**

1.  **Ensure ArangoDB is Running:**
    ```bash
    docker run -p 8529:8529 -e ARANGO_ROOT_PASSWORD=openSesame --name arangodb-agent-logs -d arangodb/arangodb:3.12.4
    ```
2.  **Ensure Environment Variables are Set:** (As described above).
3.  **Run the Initialization Script ONCE:**
    ```bash
    python -m src.arangodb.core.utils.arango_init
    ```
    *Expected Output:* Success messages confirming database, collection, and view creation. This script is idempotent and can be run multiple times without issues.

## 5. Usage Guidelines for Agents (and Humans)

### Integrating into a Python Script

When creating a new Python script, follow the template guidance in `docs/05_development/PYTHON_SCRIPT_TEMPLATE.md`. The core changes for logging are:

**1. Imports:**
Replace `from loguru import logger` with:

```python
from src.arangodb.core.utils.agent_log_manager import logger, log_agent_learning, start_run, end_run, query_logs, search_bm25_logs, prune_logs, get_latest_response
```

**2. Logging a Script's Final Primary Output:**
Rename your `save_results` function to `log_final_response` and modify it as follows. This logs your script's main JSON output directly into ArangoDB for later retrieval.

```python
def log_final_response(results: Dict[str, Any]) -> None:
    """
    AGENT: Logs the primary JSON response of the script to ArangoDB.
    The agent can retrieve this using `logger.get_latest_response()`.
    
    Args:
        results: The final results dictionary to log.
    """
    # CRITICAL: Log the final structured output to ArangoDB.
    # The 'payload' in extra will be stored as a subfield for later querying.
    logger.info("SCRIPT_FINAL_RESPONSE_PAYLOAD", payload=results, log_category="SCRIPT_FINAL_RESPONSE", file=__file__)
    logger.success("Primary script response has been logged to ArangoDB.")
```
*(Note: `file=__file__` is automatically added by loguru, but explicitly showing it here emphasizes its importance for `get_latest_response` to identify the correct script.)*

**3. The `if __name__ == "__main__":` Block:**
This block manages the lifecycle of your script's run in the log database.

```python
if __name__ == "__main__":
    """
    Script entry point with TWO usage functions.
    ...
    AGENT: All script executions are now logged to ArangoDB.
    The 'execution_id' links all messages from this run.
    """
    import asyncio
    import sys
    from pathlib import Path
    
    # Choose which function to run
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    # AGENT: Start a new script run in ArangoDB logs
    script_name = Path(__file__).stem
    execution_id = start_run(script_name, mode)
    # AGENT: CRITICAL: Bind the execution ID to ALL subsequent log messages in this run
    logger = logger.bind(execution_id=execution_id) # Re-bind logger with execution_id
    
    logger.info(f"Script '{script_name}' starting in '{mode.upper()}' mode. Execution ID: {execution_id}")
    log_agent_learning(f"Script initiated in '{mode}' mode.", function_name="__main__")

    success = False
    try:
        if mode == "debug":
            success = asyncio.run(debug_function())
        else:
            success = asyncio.run(working_usage())
    except Exception as e:
        logger.critical(f"An unhandled critical error occurred during script execution in '{mode}' mode: {e}", exc_info=True)
        log_agent_learning(f"CRITICAL: Unhandled exception in main execution block for '{mode}' mode: {e}.", function_name="__main__")

    # Exit with appropriate code
    exit_code = 0 if success else 1
    logger.info(f"Script finished with exit code {exit_code}.")
    log_agent_learning(f"Script execution completed with exit code {exit_code}.", function_name="__main__")
    # AGENT: End the script run record in ArangoDB
    end_run(execution_id, success)
    exit(exit_code)
```

### Agent-Specific Log Interaction

Beyond basic logging, the agent can use powerful methods provided by `AgentLogManager`:

*   **Log Agent Learnings (`logger.log_agent_learning`):**
    *   **Purpose:** To explicitly record debugging steps, insights, or learned facts for future self-reflection and knowledge retrieval.
    *   **Example:**
        ```python
        # In debug_function() after fixing an issue:
        logger.log_agent_learning(
            "Found that 'params' was sometimes None; added explicit check for dict type. This resolved ValueError.",
            function_name="validate_input"
        )
        ```

*   **Querying Logs with AQL (`logger.query_logs`):**
    *   **Purpose:** For advanced, precise data retrieval using ArangoDB's native AQL query language.
    *   **Example (Find all ERROR logs from a specific function):**
        ```python
        from src.arangodb.core.utils.agent_log_manager import logger
        
        aql_query = """
        FOR l IN log_events
        FILTER l.level == 'ERROR' AND l.function == 'process_task'
        SORT l.timestamp DESC
        RETURN { timestamp: l.timestamp, message: l.message, execution_id: l.extra.execution_id }
        """
        errors = logger.query_logs(aql_query)
        # Agent can now process 'errors' list
        ```

*   **Full-Text Search (BM25) (`logger.search_bm25_logs`):**
    *   **Purpose:** To find relevant log entries by keywords or phrases, leveraging ArangoDB's ArangoSearch view for relevance ranking.
    *   **Example (Find logs about Redis connection issues):**
        ```python
        from src.arangodb.core.utils.agent_log_manager import logger
        
        search_results = logger.search_bm25_logs("Redis connection refused", limit=5)
        # Results contain 'doc' (the log event) and 'score' (relevance)
        for res in search_results:
            logger.info(f"Relevant log (Score: {res['score']:.2f}): {res['doc']['message']}")
        ```

*   **Retrieve Latest Script Output (`logger.get_latest_response`):**
    *   **Purpose:** To programmatically get the structured JSON output of a script's last execution (or a specific one).
    *   **Example:**
        ```python
        from src.arangodb.core.utils.agent_log_manager import logger
        from pathlib import Path
        
        script_name_to_check = "my_data_analysis_script" # Or Path(__file__).stem for current script
        latest_output = logger.get_latest_response(script_name_to_check)
        
        if latest_output:
            logger.info(f"Latest output of {script_name_to_check}: {latest_output['status']}")
            # Agent can now parse and transform latest_output['results']
        else:
            logger.warning(f"No latest response found for {script_name_to_check}.")
        ```

*   **Pruning Logs (`logger.prune_logs`):**
    *   **Purpose:** To manage the size of the log database by deleting old or less critical log entries.
    *   **Example (Delete all logs older than 30 days):**
        ```python
        from src.arangodb.core.utils.agent_log_manager import logger
        
        deleted_count = logger.prune_logs(days_to_keep=30)
        logger.info(f"Cleaned up {deleted_count} old log entries.")
        
        # Example (Delete DEBUG logs older than 7 days):
        deleted_debugs = logger.prune_logs(days_to_keep=7, log_category="DEBUG")
        logger.info(f"Cleaned up {deleted_debugs} old DEBUG entries.")
        ```

## 6. Agent Interaction & Learning Strategy

This logging system is more than just storage; it's a foundation for agent intelligence and self-improvement.

*   **Proactive Debugging:** The agent should `search_bm25_logs` for new `ERROR` or `CRITICAL` logs after a task failure.
*   **Root Cause Analysis:** Using `query_logs` with `execution_id` (obtained from `script_runs` collection), the agent can retrieve the full sequence of events and variable states (from `diagnose=True` logs) that led to an error.
*   **Knowledge Graph Building:** The structured log data provides rich nodes (`log_events`, `script_runs`). The agent can use graph utilities (`src/arangodb/core/graph/`) to infer and explicitly create relationships:
    *   `(_log_event_A_Error_)-[CAUSED_BY]->(_log_event_B_Warning_)`
    *   `(_log_event_Error_)-[RESOLVED_BY]->(AGENT_LEARNING_log_entry_)`
    *   `(_script_run_X_)-[EXECUTED_FUNCTION]->(log_event_function_call_)`
    *   This allows multi-hop graph traversal queries (`graph_traverse`) to understand the causal chain of events and solutions.
*   **Reflective Learning:** `logger.log_agent_learning()` serves as the agent's self-documenting journal. By consistently using it, the agent builds a searchable knowledge base of its own experiences. This knowledge can be queried to inform future problem-solving.
*   **Feedback Loop:** Script execution -> Logged results -> Agent assessment (via `get_latest_response` and `query_logs`) -> Learning (`log_agent_learning`) -> Improved script.

## 7. Prompts Directory (`prompts/`)

The `prompts/` directory at the project root contains helper prompts and structured guides for common complex tasks an agent might perform. These serve as pre-written "recipes" that the agent can execute or adapt.

*   **`prompts/AGENT_LOGGING_GUIDE.md`**: This document provides a detailed, agent-focused guide on how to utilize all features of the new logging system.
*   **`prompts/create_edge_relationship.md`**: An example prompt demonstrating how the agent can manually create graph edges between log events (or other entities) using `logger.query_logs` to find IDs and `src/arangodb/core/graph/enhanced_relationships.py` to create the edge. This showcases the multi-module interaction for advanced graph reasoning.

Agents are encouraged to browse this directory when facing new challenges or to find examples of complex operations.

## 8. Code Structure Overview

This section briefly outlines the relevant files and their roles in the logging system.

```
project_root/
├── prompts/                                     # New: Agent-specific helper prompts and guides
│   ├── AGENT_LOGGING_GUIDE.md
│   └── create_edge_relationship.md              # Example for graph relations between logs
│
├── src/
│   └── arangodb/
│       └── core/
│           ├── graph/                           # Existing: Graph operations (entity resolution, etc.)
│           │   ├── __init__.py                  # AGENT_INSTRUCTIONS: Package overview
│           │   ├── enhanced_relationships.py    # AGENT_INSTRUCTIONS: Create temporal edges
│           │   └── ... (other graph modules)
│           │
│           ├── memory/                          # Existing: Memory agent (conversations, compaction)
│           │   ├── __init__.py                  # AGENT_INSTRUCTIONS: Package overview
│           │   ├── memory_agent.py              # AGENT_INSTRUCTIONS: Store/retrieve conversations
│           │   └── ... (other memory modules)
│           │
│           ├── search/                          # Existing: Search capabilities (BM25, semantic, hybrid)
│           │   ├── __init__.py                  # AGENT_INSTRUCTIONS: Package overview
│           │   ├── bm25_search.py               # (Used by logger.search_bm25_logs internally)
│           │   └── ... (other search modules)
│           │
│           └── utils/                           # New & Modified: Core Logging System Utilities
│               ├── arango_constants.py          # New: Defines ArangoDB connection/schema constants
│               ├── arango_init.py               # New: AGENT_INSTRUCTIONS: Database/schema initialization script
│               ├── arango_log_sink.py           # New: Internal: Loguru custom sink for async ArangoDB writes
│               ├── agent_log_manager.py         # New: AGENT_INSTRUCTIONS: Singleton logger, exposes API (logger.query_logs, etc.)
│               ├── dependency_checker.py        # Modified: Ensures uvloop for async performance
│               ├── ... (other existing utilities)
│
└── docs/
    └── 05_development/
        └── PYTHON_SCRIPT_TEMPLATE.md            # Modified: Core template for agent scripts (integrates new logger)
```

## 9. Troubleshooting

*   **`ConnectionAbortedError: Can't connect to host(s) within limit`:**
    *   **Cause:** ArangoDB container is not running or accessible from your Python environment.
    *   **Solution:** Verify Docker container status (`docker ps`), check port mapping (`-p 8529:8529`), ensure `ARANGO_HOST` environment variable is correct.
*   **`CollectionNotFound: Collection 'log_events' not found`:**
    *   **Cause:** The ArangoDB database schema for logging has not been initialized.
    *   **Solution:** Run `python -m src.arangodb.core.utils.arango_init` (see [Database & Schema Initialization](#database--schema-initialization)).
*   **`ViewCreateError: Failed to create ArangoSearch View`:**
    *   **Cause:** Often an issue with ArangoDB versions or permissions.
    *   **Solution:** Ensure you are running ArangoDB 3.12.4. Verify `ARANGO_USER` and `ARANGO_PASSWORD` have sufficient permissions to create views.
*   **Log messages not appearing in ArangoDB, but showing in console:**
    *   **Cause:** The background log writer thread might have failed to start or connect to ArangoDB.
    *   **Solution:** Check the console output for `AgentLogManager: Failed to connect to ArangoDB` errors during startup. Ensure `arango_init.py` was run successfully.

## 10. Gemini Integration for Automated Issue Resolution

### Overview
This project includes templates for automated integration with Google's Gemini Flash model via Vertex AI. When Claude Code encounters complex issues, it can automatically generate standardized issue reports for Gemini to solve.

### Key Integration Points

1. **Issue Detection**: Claude Code detects blocking errors and generates formatted reports
2. **Gemini Solutions**: Gemini provides complete code fixes in standardized format
3. **Automated Extraction**: Extract and apply fixes without manual intervention
4. **Validation**: All fixes are tested with isolated test databases

### Templates Location
- **Main Template**: `docs/integration/GEMINI_CLAUDE_CODE_INTEGRATION_TEMPLATE.md`
- **Markdown Format**: `docs/issues/002_markdown_format_requirements.md`
- **Extraction Script**: `scripts/extract_code_from_markdown.py`

### Quick Start for Integration

```python
# 1. Generate issue report
from pathlib import Path
issue_report = generate_gemini_issue_report(error, context)
Path("issues/for_gemini.md").write_text(issue_report)

# 2. Get solution from Gemini (future Vertex AI)
solution = await get_gemini_solution(issue_report)

# 3. Extract and apply fixes
os.system(f"python scripts/extract_code_from_markdown.py {solution_file} src/")

# 4. Validate fixes
os.system("python src/working_usage_verification.py")
```

### Critical Format Requirements

Gemini MUST use these exact markers for code:
```markdown
<!-- CODE_FILE_START: src/path/to/file.py -->
```python
# Complete file content here
```
<!-- CODE_FILE_END: src/path/to/file.py -->
```

### Test Database Pattern

All database operations MUST use test isolation:
```python
from utils.test_db_utils import setup_test_database, teardown_test_database

test_db, test_db_name, test_db_config = await setup_test_database()
try:
    # Database operations here
finally:
    await teardown_test_database(test_db_name)
```

For complete integration details, see `docs/integration/GEMINI_CLAUDE_CODE_INTEGRATION_TEMPLATE.md`.

## 11. License

[MIT License](LICENSE) (or your project's chosen license).

---

**(End of README.md)**