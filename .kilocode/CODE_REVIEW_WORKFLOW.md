Excellent. You are exactly right. We have the individual components, and now we need to wire them together. The two missing pieces are:

1.  **Registering the MCP Tool:** Telling Claude Code's MCP system how to launch your `mcp_kilocode_review.py` script.
2.  **The Master Prompt:** Crafting the instructions that teach the AI agent *how* and *when* to use this new two-step tool to create a self-correction loop.

Here is the complete solution to finalize your workflow.

---

### 1. Registering the MCP Tool in `~/.claude/claude_code/.mcp.json`

You need to add a new entry to the `mcpServers` object in your `.mcp.json` file. This tells the system how to run your Python script when the agent calls for the `kilocode-review` tool.

Based on your existing configuration, especially the `arango-tools` entry, here is the block you should add.

**Action:** Add the following JSON block inside the `mcpServers` object in your `~/.claude/claude_code/.mcp.json` file. Remember to add a comma after the preceding entry.

```json
    "kilocode-review": {
      "command": "uv",
      "args": [
        "--directory",
        "/home/graham/workspace/experiments/cc_executor",
        "run",
        "--script",
        "src/cc_executor/servers/mcp_kilocode_review.py"
      ],
      "env": {
        "PYTHONPATH": "/home/graham/workspace/experiments/cc_executor/src",
        "UV_PROJECT_ROOT": "/home/graham/workspace/experiments/cc_executor"
      }
    }
```

**Why this works:**
*   **`"kilocode-review"`:** The key matches the `mcp = FastMCP("kilocode-review")` line in your Python script. This is how the system maps the tool name to the command.
*   **`command: "uv"` and `args`:** This correctly uses `uv` to run your script, specifying the project directory and using the `--script` flag because your file has a `/// script` header for dependency management.
*   **`env`:** We add `PYTHONPATH` and `UV_PROJECT_ROOT` for robustness, ensuring that any local imports (like `from utils.mcp_logger...`) will resolve correctly, just like in your other tool definitions.

---

### 2. The Master Prompt: Orchestrating the Full Workflow

This is the most crucial piece. You need to give the AI agent a clear, unambiguous "Standard Operating Procedure" (SOP) to follow. This prompt should be included in your main task request, likely at the end.

Here is a master prompt designed specifically for the two-step, asynchronous nature of your new tool.

> **Final Instructions: Mandatory Self-Correction and Verification**
>
> Once you believe you have completed the primary coding task, you MUST perform a final quality check using the `kilocode-review` tool. This is a non-negotiable step to ensure your work adheres to all project constraints.
>
> Follow this procedure exactly:
>
> 1.  **Identify Changed Files:** Use your file system tools to identify all file paths you have created or modified.
>
> 2.  **Initiate Review:** Call the `kilocode-review.start_review` tool. Pass the file paths as a single space-separated string to the `files` argument.
>     *   The tool will immediately return a JSON object containing a `review_id`. This ID is the path to the results directory.
>
> 3.  **Wait for Completion:** The review process is **asynchronous** and can take several minutes to run.
>     *   You must wait patiently. A good strategy is to wait for 2-3 minutes before checking the results.
>
> 4.  **Retrieve and Analyze Results:** After waiting, call the `kilocode-review.get_review_results` tool, passing the `review_id` you received in step 2.
>     *   This will return a JSON object containing the full review.
>     *   Carefully examine the content of the `results.actionable_fixes` field. This contains fixes that are pre-validated and safe to apply.
>     *   Also, review `results.incompatible_suggestions` to learn what standard fixes are incorrect for this project's context.
>
> 5.  **Perform Self-Correction:**
>     *   If `actionable_fixes` contains any suggestions, you are **REQUIRED** to open the relevant files and apply the changes exactly as described.
>     *   If `actionable_fixes` is empty or null, no corrections are needed.
>
> 6.  **Conclude Task:** After applying all required fixes, you may consider the task complete. In your final message, state that you have finished the work and confirm that it has passed the automated contextual review.

---

### Putting It All Together: A Simulated Agent Workflow

This is how an agent would execute your complete, end-to-end workflow:

1.  **Agent Finishes Coding:** The agent writes code to `src/new_feature.py` and `src/utils/helpers.py`.

2.  **Agent Follows Prompt (Step 1-2):** "My coding is done. Now I must start the review."
    ```xml
    <execute_command>
      <tool_name>kilocode-review</tool_name>
      <function_name>start_review</function_name>
      <args>
        <files>src/new_feature.py src/utils/helpers.py</files>
      </args>
    </execute_command>
    ```

3.  **Agent Receives `review_id`:** The tool returns:
    ```json
    {
      "success": true,
      "review_id": "docs/code_review/20231028110000_c4d9a...",
      "message": "Review started successfully. Use get_review_results with the review_id to fetch the summary."
    }
    ```

4.  **Agent Waits (Step 3):** "The review has started. The `review_id` is `docs/code_review/20231028110000_c4d9a...`. I will now wait for 3 minutes before checking the results."

5.  **Agent Retrieves Results (Step 4):** After waiting, the agent calls:
    ```xml
    <execute_command>
      <tool_name>kilocode-review</tool_name>
      <function_name>get_review_results</function_name>
      <args>
        <review_id>docs/code_review/20231028110000_c4d9a...</review_id>
      </args>
    </execute_command>
    ```

6.  **Agent Analyzes Results:** The tool returns a large JSON. The agent parses it and finds content in `results.actionable_fixes`:
    `"### 1. Missing JSON Serialization\n**File:** src/new_feature.py:52\n**Current:**\n`return data`\n**Fixed:**\n`return json.dumps(data)`\n**Rationale:** FastMCP requires JSON string outputs."`

7.  **Agent Self-Corrects (Step 5):** "The review found a critical issue. I must apply the fix." The agent opens `src/new_feature.py`, navigates to line 52, and changes `return data` to `return json.dumps(data)`.

8.  **Agent Concludes (Step 6):** "I have completed the task. I wrote the new feature and performed the mandatory self-review. The review identified one issue related to FastMCP compatibility, which I have now corrected. The code is complete and has passed the automated contextual review."

You now have a complete, robust, and fully automated quality assurance loop.