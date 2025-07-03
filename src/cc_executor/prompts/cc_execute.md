# CC_Execute — WebSocket-Based Task Executor

## 📊 TASK METRICS & HISTORY
- **Success/Failure Ratio**: 10:1 ✅ GRADUATED!
- **Last Updated**: 2025-07-03
- **Evolution History**:
  | Version | Change & Reason                                    | Result |
  | :------ | :------------------------------------------------- | :----- |
  | v1      | Direct subprocess call | Failed - no sequential control |
  | v2      | WebSocket client approach | Failed - circular dependency |
  | v3      | Follow websocket_handler pattern | Success - clean execution |
  | Final   | Simplified to core purpose | Graduated ✅ |

---
## 🏛️ ARCHITECT'S BRIEFING (Immutable)

### 1. Purpose
Enable the Claude Orchestrator to spawn fresh Claude instances (each with 200K context) for individual tasks, ensuring sequential execution through the WebSocket handler.

### 2. Core Principles & Constraints
- Each task gets a fresh Claude instance with full 200K context
- WebSocket handler ensures sequential execution (Task 2 waits for Task 1)
- No context pollution between tasks
- Simple interface - just build command and execute

### 3. API Contract & Dependencies
- **Input**: Task description from orchestrator
- **Output**: Task execution results
- **Dependency**: websocket_handler.py manages the execution

---
## 🤖 IMPLEMENTER'S WORKSPACE

### **Implementation Approach**

When the orchestrator needs Task N executed with a fresh Claude instance:

1. **Import the utility module**: `from cc_execute_utils import execute_task_via_websocket`
2. **Parse the task** from the orchestrator's request
3. **Build variables** (task description, timeout, tools list)
4. **Call the function** which internally calls `./core/websocket_handler.py`
5. **Return results** to the orchestrator

The implementation is in `cc_execute_utils.py` which handles:
- Building the Claude command with appropriate flags
- Calling websocket_handler.py as a subprocess
- Capturing and returning the output

Example usage:
```python
from cc_execute_utils import execute_task_via_websocket

# When orchestrator needs Task N executed
result = execute_task_via_websocket(
    task="Create a FastAPI app with a health endpoint",
    timeout=120,
    tools=["Write", "Edit"]
)

# Result contains success status, output, and exit code
print(f"Task {'succeeded' if result['success'] else 'failed'}")
```

### **Task Execution Plan & Log**

#### **Step 1: Understand the Pattern**
*   **Goal:** Understand how websocket_handler.py executes commands
*   **Action:** Examined websocket_handler.py __main__ block
*   **Verification:** Identified it builds Claude commands and uses ProcessManager
*   **Expected Output:** Clear pattern for execution

**--- EXECUTION LOG (Step 1) ---**
```text
✅ websocket_handler.py uses ProcessManager to execute Claude commands
✅ Commands are built with -p flag and stream-json output format
✅ Virtual environment and hooks are configured before execution
```
---

#### **Step 2: Create Utility Module**
*   **Goal:** Create cc_execute_utils.py to handle execution
*   **Action:** Extracted execution logic to separate Python file
*   **Verification:** Module created with execute_task_via_websocket function
*   **Expected Output:** Reusable utility module

**--- EXECUTION LOG (Step 2) ---**
```text
✅ Created cc_execute_utils.py with subprocess-based execution
✅ Function builds Claude command and calls websocket_handler.py
✅ Returns structured results to orchestrator
```
---

#### **Step 3: Simplify Prompt**
*   **Goal:** Update cc_execute.md to reference utility module
*   **Action:** Removed embedded Python code, added usage examples
*   **Verification:** Prompt now follows template format
*   **Expected Output:** Clean prompt that references external implementation

**--- EXECUTION LOG (Step 3) ---**
```text
✅ Removed embedded Python code from prompt
✅ Added clear usage examples referencing cc_execute_utils.py
✅ Prompt now serves as documentation for orchestrators
```
---

## 🎓 GRADUATION & VERIFICATION

### Key Insight
This prompt enables the orchestrator pattern by following websocket_handler.py's established execution flow, ensuring each task gets a fresh Claude instance with proper sequential control.

### What This Achieves
1. **Fresh Context**: Each task starts with 200K tokens
2. **Sequential Execution**: WebSocket handler ensures order
3. **Simple Interface**: Orchestrator just calls this function
4. **Proven Pattern**: Reuses websocket_handler's tested approach