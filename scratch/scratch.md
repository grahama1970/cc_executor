and do any docs in /home/graham/workspace/experiments/cc_executor/docs need to be deprecated, amended, or reorganized 



you need to use uv venv --python=3.10.11 .venv and uv pip install -e .


create a new code review request
following @docs/templates/CODE_REVIEW_REQUEST_TEMPLATE.md
the code review request needs to thoroughly check the MCP endpoint
(/home/graham/workspace/experiments/cc_executor/src/cc_executor/servers/mcp_cc_execute.py)
and the python endpoint
(/home/graham/workspace/experiments/cc_executor/src/cc_executor/client/cc_execute.py)

also assess 
- the shared claude code instance call
is create_subprocess_shell this the most optimal reliable and shared way to call claude code from the MCP and directly from python?
@src/cc_executor/core/process_manager.py
with stdbuf_check = await
asyncio.create_subprocess_shell(
"which stdbuf",
stdout=asyncio.subprocess.PIPE,
stderr=asyncio.subprocess.DEVNULL
)
- assess the effectiveness of hook integration in the MCP and in cc_execute.py
- assess what code in /home/graham/workspace/experiments/cc_executor/src/cc_executor is no longer needed (not referenced) and should be archived/depreacted
- access if cc_executor is ready to deploy and use as an MCP for the agent and cc_execute.py within code
- access what (if anything) is missing from cc_executor project that would directly benefit the user when calling a claude instance with as little friction/complexity as possible





Also, should we be implementing:
/home/graham/workspace/experiments/cc_executor/repos/fastmcp
FastMCP offers several advanced features for handling long-running processes beyond basic progress reporting. These features are designed to improve user experience, enable richer interactions, and provide robust server-client communication:

Progress Reporting: Continuously update the client on the status of long-running operations using ctx.report_progress().

Streaming Output: Send data to the client incrementally as it is generated, supporting use cases like progressive text, image, or media generation.

Advanced Logging: Send debug, info, warning, and error messages back to the client in real time, providing transparency and easier troubleshooting for ongoing tasks.

User Elicitation (Interactive Input): Pause execution to request structured input from the client during a running operation, enabling interactive and adaptive workflows (e.g., asking the user for additional information mid-process).

Resource Access: Dynamically read from or write to server-side resources within a long-running process, allowing complex, multi-step operations that depend on external data.

HTTP Streaming & SSE Compatibility: Support for HTTP streaming and Server-Sent Events (SSE) enables real-time updates and output delivery for long-running tasks.

Resumability: Some implementations support resuming interrupted long-running operations, allowing clients to reconnect and continue without loss of progress.

Configurable Ping Behavior: Maintain connection health during lengthy operations by sending periodic pings, with customizable intervals and logging.

Typed Server Events: Emit structured, typed events to the client, which can be used for custom progress, status updates, or other notifications during execution.

Prompt Argument Auto-Completion: For interactive tools, provide real-time suggestions or completions for user input, streamlining complex workflows.

These features, accessible via the context object (ctx), make FastMCP well-suited for building robust, user-friendly servers that handle complex, long-running tasks with interactive and real-time capabilities.
 
 
 
 remember calling the @src/cc_executor/prompts/cc_execute.md prompt does NOT access the MCP tools or fastmcp. These are two completely different approaches




you should mention using the source installation method (uv and pyproject.toml) in /home/graham/workspace/experiments/cc_executor/docs/templates/DOCKER_DEPLOYMENT_TEMPLATE.md  So you don't make the same mistake again  

Also, you have many problems becuase you dont force rebuild the container when you are debugging. Because of this, code is not updated in the container



re claude authentication, you did not share the docker volume

then ensure that /home/graham/workspace/experiments/cc_executor/deployment/docker_setup.md complies with the template. Then continue with debugging the docker and testing all the endpoints


you do not need a coded/automated wizard. just ask clarifyig questions when confused 

why are you echoing python code int he markdown file. Just ask the huamn clarofying questions (if relevant) in the prompt. Be flexible. It should have been obvious to ask of websockets and fastapi should be 1 or two containers or to ask what the name of the container should be


these are confgurations that you should ask your human. Do you understand. The prompt needs to ask the human clarifying questions. This should be part of the prompt and prompt template design--especially if the project code/docs are not clear




when you are done submit a code review       │
│   request prepdned with 018_ (in /home/graham  │
│   /workspace/experiments/cc_executor/src/cc_e  │
│   xecutor/tasks/orchestrator/incoming)  that   │
│   asks for a review of cc_execute.md as the    │
│   entry point and websocket_handler.py and     │
│   all the helper files. Explain what the code  │
│   should do and oto request for iterative      │
│   helpful changes  that do not add britteness  │
│   or needless complexity 