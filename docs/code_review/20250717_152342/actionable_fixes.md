## Critical: Hard-coded fallback credentials in ArangoTools
**File:** `src/cc_executor/servers/mcp_arango_crud.py`
**Problem:** The file contains hard-coded default credentials, posing a security risk.
**Suggested Fix:** Externalize credentials using environment variables or a dedicated secrets management service.

## High: Monolithic ArangoTools class violates SRP
**File:** `src/cc_executor/servers/mcp_arango_crud.py`
**Problem:** The `ArangoTools` class has too many responsibilities (CRUD, graph ops, admin), making it difficult to maintain.
**Suggested Fix:** Refactor the class into smaller, more focused modules based on responsibility (e.g., `NodeManager`, `EdgeManager`, `GraphAdmin`).

## Medium: Duplicated tool-sequence optimization logic
**File:** `src/cc_executor/servers/mcp_tool_sequence_optimizer.py` and `src/cc_executor/servers/mcp_tool_journey_advanced.py`
**Problem:** The core optimization algorithm is duplicated across two files, leading to code redundancy.
**Suggested Fix:** Consolidate the duplicated logic into a single, reusable function or utility module and import it where needed.

## High: Inefficient subprocess execution in logger server
**File:** `src/cc_executor/servers/mcp_logger_tools.py`
**Problem:** The `run_tool` function invokes `uv run` in a new subprocess for every request, causing significant performance overhead.
**Suggested Fix:** Replace the per-call subprocess with a more efficient approach, such as a long-running worker pool or by importing and calling the tool's function directly within the async event loop.

## Medium: Embedded HTML templates in Python code
**File:** `src/cc_executor/servers/mcp_d3_visualizer.py`
**Problem:** Large blocks of HTML are embedded as strings within Python functions, mixing presentation with logic.
**Suggested Fix:** Separate concerns by moving HTML to external template files and using a templating engine like Jinja2 to render them.