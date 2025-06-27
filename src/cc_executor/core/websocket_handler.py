"""
WebSocket handler module for CC Executor MCP WebSocket Service.

DEBUGGING GUIDE (truncated):
- Enable verbose logs by setting `LOGURU_LEVEL=DEBUG` when running the service.
- Heartbeat: look for "Heartbeat sent" every `heartbeat_interval` seconds; absence means the task died.
- Connection lifecycle events are logged at INFO.
- Use the example Claude commands in the docstring to reproduce long-running cases without the WebSocket.

This module manages WebSocket connections, routes JSON-RPC messages,
and coordinates between sessions, processes, and streaming. It implements
the Model Context Protocol (MCP) over WebSocket.

Third-party Documentation:
- JSON-RPC 2.0 Specification: https://www.jsonrpc.org/specification
- FastAPI WebSockets: https://fastapi.tiangolo.com/advanced/websockets/
- WebSocket Protocol: https://datatracker.ietf.org/doc/html/rfc6455
- Model Context Protocol: https://modelcontextprotocol.io/docs

Example Input:
    Execute: {"jsonrpc":"2.0","method":"execute","params":{"command":"ls -la"},"id":1}
    Control: {"jsonrpc":"2.0","method":"control","params":{"type":"PAUSE"},"id":2}
    Invalid: {"jsonrpc":"2.0","method":"unknown","id":3}

Expected Output:
    Execute: {"jsonrpc":"2.0","result":{"status":"started","pid":12345},"id":1}
    Control: {"jsonrpc":"2.0","result":{"status":"paused"},"id":2}
    Error: {"jsonrpc":"2.0","error":{"code":-32601,"message":"Unknown method"},"id":3}
    Stream: {"jsonrpc":"2.0","method":"process.output","params":{"type":"stdout","data":"output"}}

Example Claude Code Instances:
    
    Simple (quick test):
    claude -p --output-format stream-json --verbose --mcp-config .mcp.json \
      --allowedTools "mcp__perplexity-ask mcp__brave-search mcp__github mcp__ripgrep mcp__puppeteer" \
      --dangerously-skip-permissions "What is 2+2?"
    
    Medium (should complete in ~30s):
    claude -p --output-format stream-json --verbose --mcp-config .mcp.json \
      --allowedTools "mcp__perplexity-ask mcp__brave-search mcp__github mcp__ripgrep mcp__puppeteer" \
      --dangerously-skip-permissions "Write 5 haikus about AI" | gnomon
    
    Long-running (3-5 minutes):
    claude -p --output-format stream-json --verbose --mcp-config .mcp.json \
      --allowedTools "mcp__perplexity-ask mcp__brave-search mcp__github mcp__ripgrep mcp__puppeteer" \
      --dangerously-skip-permissions "Write a 5000 word science fiction story about a programmer who discovers their code is sentient. Include dialogue, plot twists, and a surprising ending. Stream the entire story." | gnomon
    
    Note: Use these direct terminal commands to debug when WebSocket tests fail.
    The heartbeat mechanism keeps connections alive during Claude's thinking period.
"""

import json
import asyncio
import uuid
import time
import os
import sys
from typing import Optional, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

# Configure logging for production use
# Remove default logger to avoid duplicate logs
logger.remove()

# Console logging (INFO and above)
logger.add(sys.stderr, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>", level="INFO")

# File logging (DEBUG and above) with rotation
log_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))) + "/logs"
logger.add(
    f"{log_dir}/websocket_handler_{{time}}.log",
    level="DEBUG",
    rotation="10 MB",
    retention=5,  # Keep 5 rotated files
    enqueue=True,  # Make logging non-blocking
    backtrace=True,
    diagnose=True
)

try:
    from .config import (
        ALLOWED_COMMANDS, JSONRPC_VERSION,
        ERROR_METHOD_NOT_FOUND, ERROR_INVALID_PARAMS,
        ERROR_SESSION_LIMIT, ERROR_COMMAND_NOT_ALLOWED,
        ERROR_PROCESS_NOT_FOUND, ERROR_INTERNAL_ERROR,
        STREAM_TIMEOUT
    )
    from .models import (
        JSONRPCRequest, JSONRPCResponse, JSONRPCError,
        ExecuteRequest, ControlRequest, StatusUpdate,
        StreamOutput, ConnectionInfo, validate_command
    )
    from .session_manager import SessionManager
    from .process_manager import ProcessManager, ProcessNotFoundError
    from .stream_handler import StreamHandler
except ImportError:
    # For standalone execution
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from config import (
        ALLOWED_COMMANDS, JSONRPC_VERSION,
        ERROR_METHOD_NOT_FOUND, ERROR_INVALID_PARAMS,
        ERROR_SESSION_LIMIT, ERROR_COMMAND_NOT_ALLOWED,
        ERROR_PROCESS_NOT_FOUND, ERROR_INTERNAL_ERROR,
        STREAM_TIMEOUT
    )
    from models import (
        JSONRPCRequest, JSONRPCResponse, JSONRPCError,
        ExecuteRequest, ControlRequest, StatusUpdate,
        StreamOutput, ConnectionInfo, validate_command
    )
    from session_manager import SessionManager
    from process_manager import ProcessManager, ProcessNotFoundError
    from stream_handler import StreamHandler


DEFAULT_HEARTBEAT_INTERVAL = 20  # seconds


class WebSocketHandler:
    """
    Handles WebSocket connections and message routing.
    
    This class coordinates:
    - WebSocket lifecycle management
    - JSON-RPC message parsing and routing
    - Command execution and process control
    - Output streaming to clients
    - Error handling and session cleanup
    """
    
    def __init__(
        self,
        session_manager: SessionManager,
        process_manager: ProcessManager,
        stream_handler: StreamHandler,
        heartbeat_interval: Optional[int] = None
    ):
        """
        Initialize the WebSocket handler.
        
        Args:
            session_manager: Session manager instance
            process_manager: Process manager instance
            stream_handler: Stream handler instance
            heartbeat_interval: Heartbeat interval in seconds (defaults to WEBSOCKET_HEARTBEAT_INTERVAL env var or 30)
        """
        self.sessions = session_manager
        self.processes = process_manager
        self.streamer = stream_handler
        # Use environment variable if not explicitly provided
        self.heartbeat_interval = heartbeat_interval or int(os.environ.get('WEBSOCKET_HEARTBEAT_INTERVAL', '30'))
        
    async def handle_connection(self, websocket: WebSocket, session_id: str) -> None:
        """
        Main WebSocket connection handler.
        
        Args:
            websocket: FastAPI WebSocket instance
            session_id: Unique session identifier
        """
        # Accept the connection
        logger.info(f"Accepting WebSocket connection from {websocket.client} as session {session_id}")
        await websocket.accept()
        
        # Log connection details
        logger.info(f"WebSocket state: {websocket.application_state}")
        logger.info(f"Client state: {websocket.client_state}")
        
        # Try to create session
        if not await self.sessions.create_session(session_id, websocket):
            await self._send_error(
                websocket, ERROR_SESSION_LIMIT,
                "Session limit exceeded", None
            )
            await websocket.close(code=1008, reason="Session limit exceeded")
            return
            
        try:
            # No heartbeat needed - Uvicorn handles WebSocket ping/pong

            # Send connection confirmation
            await self._send_notification(
                websocket, "connected",
                ConnectionInfo(
                    session_id=session_id,
                    version="1.0.0",
                    capabilities=["execute", "control", "stream"]
                ).dict()
            )
            
            # Message loop
            message_count = 0
            
            while True:
                try:
                    # Wait indefinitely for messages - connection health is managed by Uvicorn's ping/pong
                    data = await websocket.receive_text()
                    message_count += 1
                    
                    logger.debug(f"Received message {message_count} from {session_id}")
                    await self._handle_message(session_id, data)
                    
                except WebSocketDisconnect as e:
                    logger.info(f"WebSocket disconnected: {session_id} (code: {e.code}, reason: {e.reason})")
                    break
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from {session_id}: {e}")
                    await self._send_error(
                        websocket, -32700,
                        "Parse error", None
                    )
                    
        except Exception as e:
            logger.error(f"WebSocket error for {session_id}: {e}")
            
        finally:
            await self._cleanup_session(session_id)
            

    async def _handle_message(self, session_id: str, data: str) -> None:
        """
        Handle incoming JSON-RPC message.
        
        Args:
            session_id: Session identifier
            data: Raw message data
        """
        session = await self.sessions.get_session(session_id)
        if not session:
            logger.error(f"Session not found: {session_id}")
            return
            
        try:
            # Parse JSON-RPC request
            request = json.loads(data)
            method = request.get("method")
            params = request.get("params", {})
            msg_id = request.get("id")
            
            logger.debug(f"Received {method} from {session_id}")
            
            # Route to appropriate handler
            if method == "execute":
                await self._handle_execute(session_id, params, msg_id)
            elif method == "control":
                await self._handle_control(session_id, params, msg_id)
            else:
                await self._send_error(
                    session.websocket,
                    ERROR_METHOD_NOT_FOUND,
                    f"Unknown method: {method}",
                    msg_id
                )
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self._send_error(
                session.websocket,
                ERROR_INTERNAL_ERROR,
                str(e),
                request.get("id") if 'request' in locals() else None
            )
            
    async def _handle_execute(
        self,
        session_id: str,
        params: Dict[str, Any],
        msg_id: Optional[Any]
    ) -> None:
        """
        Handle command execution request.
        
        Args:
            session_id: Session identifier
            params: Request parameters
            msg_id: Request ID for response correlation
        """
        session = await self.sessions.get_session(session_id)
        if not session:
            return
            
        try:
            # Validate request
            req = ExecuteRequest(**params)
            
            # Validate command security
            is_valid, error_msg = validate_command(req.command, ALLOWED_COMMANDS)
            if not is_valid:
                await self._send_error(
                    session.websocket,
                    ERROR_COMMAND_NOT_ALLOWED,
                    error_msg,
                    msg_id
                )
                return
                
            # Check if already running a process
            if session.process and self.processes.is_process_alive(session.process):
                await self._send_error(
                    session.websocket,
                    ERROR_INVALID_PARAMS,
                    "A process is already running",
                    msg_id
                )
                return
                
            # Execute command with proper working directory
            # __file__ is websocket_handler.py, we need to go up 4 levels to project root
            # websocket_handler.py -> core -> cc_executor -> src -> [project root]
            cwd = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            
            # Log critical execution details that affect command success
            logger.info(f"[EXECUTE] Command: {req.command[:100]}...")
            logger.info(f"[EXECUTE] Working directory: {cwd}")
            logger.info(f"[EXECUTE] MCP config exists: {os.path.exists(os.path.join(cwd, '.mcp.json'))}")
            
            # Check environment - log if ANTHROPIC_API_KEY will be removed
            if 'ANTHROPIC_API_KEY' in os.environ:
                logger.info("[EXECUTE] ANTHROPIC_API_KEY will be removed (using Claude Max)")
            else:
                logger.info("[EXECUTE] ANTHROPIC_API_KEY not present in environment")
                
            process = await self.processes.execute_command(req.command, cwd=cwd)
            pgid = self.processes.get_process_group_id(process)
            
            # Update session
            await self.sessions.update_session(
                session_id,
                process=process,
                pgid=pgid
            )
            
            # Send success response
            await self._send_response(
                session.websocket,
                {"status": "started", "pid": process.pid, "pgid": pgid},
                msg_id
            )
            
            # Notify process started
            await self._send_notification(
                session.websocket,
                "process.started",
                StatusUpdate(
                    status="started",
                    pid=process.pid,
                    pgid=pgid
                ).dict()
            )
            
            # Start streaming task - no timeout, let process complete naturally
            stream_task = asyncio.create_task(
                self._stream_process_output(session_id, process)
            )
            await self.sessions.update_session(session_id, task=stream_task)
            
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            await self._send_error(
                session.websocket,
                ERROR_INTERNAL_ERROR,
                str(e),
                msg_id
            )
            
    async def _handle_control(
        self,
        session_id: str,
        params: Dict[str, Any],
        msg_id: Optional[Any]
    ) -> None:
        """
        Handle process control request.
        
        Args:
            session_id: Session identifier
            params: Request parameters
            msg_id: Request ID for response correlation
        """
        session = await self.sessions.get_session(session_id)
        if not session:
            return
            
        try:
            # Validate request
            req = ControlRequest(**params)
            
            # Check if process exists
            if not session.process or not session.pgid:
                await self._send_error(
                    session.websocket,
                    ERROR_PROCESS_NOT_FOUND,
                    "No process is running",
                    msg_id
                )
                return
                
            # Apply control
            self.processes.control_process(session.pgid, req.type)
            
            # Send success response
            status_map = {
                "PAUSE": "paused",
                "RESUME": "resumed",
                "CANCEL": "canceled"
            }
            await self._send_response(
                session.websocket,
                {"status": status_map[req.type]},
                msg_id
            )
            
            # Notify status change
            await self._send_notification(
                session.websocket,
                f"process.{status_map[req.type]}",
                StatusUpdate(
                    status=status_map[req.type],
                    pid=session.process.pid,
                    pgid=session.pgid
                ).dict()
            )
            
            # Handle cancellation
            if req.type == "CANCEL" and session.task:
                session.task.cancel()
                
        except ProcessNotFoundError as e:
            await self._send_error(
                session.websocket,
                ERROR_PROCESS_NOT_FOUND,
                str(e),
                msg_id
            )
        except Exception as e:
            logger.error(f"Error controlling process: {e}")
            await self._send_error(
                session.websocket,
                ERROR_INTERNAL_ERROR,
                str(e),
                msg_id
            )
            
    async def _stream_process_output(self, session_id: str, process: Any) -> None:
        """
        Stream process output to WebSocket.
        
        Args:
            session_id: Session identifier
            process: Process to stream from
        """
        session = await self.sessions.get_session(session_id)
        if not session:
            return
            
        async def send_output(stream_type: str, data: str):
            """Send output line to client."""
            # Log large outputs for debugging (but not every line)
            if len(data) > 10000:
                logger.info(f"[LARGE OUTPUT] {stream_type} sending {len(data):,} chars")
            elif logger._core.min_level <= 10:  # DEBUG level
                logger.debug(f"[OUTPUT] {stream_type} ({len(data)} chars): {data[:100]}...")
            
            await self._send_notification(
                session.websocket,
                "process.output",
                StreamOutput(
                    type=stream_type,
                    data=data,
                    truncated=data.endswith("...\n")
                ).dict()
            )
            
        try:
            # Stream output without timeout - let process complete naturally
            # The WebSocket ping/pong keeps the connection alive
            logger.info(f"Streaming output (no timeout - process will complete naturally)")
            
            await self.streamer.multiplex_streams(
                process.stdout,
                process.stderr,
                send_output
                # No timeout - wait indefinitely for process to complete
            )
            
            # Wait for process completion
            exit_code = await process.wait()
            
            # Log completion details
            completion_status = "completed" if exit_code == 0 else "failed"
            logger.info(f"[PROCESS COMPLETED] PID: {process.pid}, Exit code: {exit_code}, "
                       f"Status: {completion_status}")
            
            # Notify completion
            await self._send_notification(
                session.websocket,
                "process.completed",
                StatusUpdate(
                    status=completion_status,
                    pid=process.pid,
                    pgid=session.pgid,
                    exit_code=exit_code
                ).dict()

            )
            
        except asyncio.CancelledError:
            logger.info(f"Streaming cancelled for {session_id}")
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            await self._send_notification(
                session.websocket,
                "process.error",
                {"error": str(e)}
            )
            
    async def _cleanup_session(self, session_id: str) -> None:
        """
        Clean up session and associated resources.
        
        Args:
            session_id: Session identifier
        """
        session = await self.sessions.remove_session(session_id)
        if not session:
            return
            
        # Cancel streaming task
        if session.task and not session.task.done():
            session.task.cancel()
            
        # Cleanup process
        if session.process:
            await self.processes.cleanup_process(session.process, session.pgid)
            
    # JSON-RPC helpers
    
    async def _send_response(
        self,
        websocket: WebSocket,
        result: Any,
        msg_id: Optional[Any]
    ) -> None:
        """Send JSON-RPC response."""
        response = JSONRPCResponse(
            jsonrpc=JSONRPC_VERSION,
            result=result,
            id=msg_id
        )
        await websocket.send_json(response.dict(exclude_none=True))
        
    async def _send_error(
        self,
        websocket: WebSocket,
        code: int,
        message: str,
        msg_id: Optional[Any],
        data: Any = None
    ) -> None:
        """Send JSON-RPC error."""
        response = JSONRPCResponse(
            jsonrpc=JSONRPC_VERSION,
            error=JSONRPCError(
                code=code,
                message=message,
                data=data
            ).dict(),
            id=msg_id
        )
        await websocket.send_json(response.dict(exclude_none=True))
        
    async def _send_notification(
        self,
        websocket: WebSocket,
        method: str,
        params: Any
    ) -> None:
        """Send JSON-RPC notification (no ID)."""
        notification = {
            "jsonrpc": JSONRPC_VERSION,
            "method": method,
            "params": params
        }
        await websocket.send_json(notification)


if __name__ == "__main__":
    """
    Direct debug entry point for VSCode.
    
    VSCode Debug:
        1. Set breakpoints anywhere in this file
        2. Press F5 (or Run > Start Debugging)
        3. The server will start on ws://localhost:8004/ws
    """
    from fastapi import FastAPI
    import uvicorn
    
    print("=" * 60)
    print("WebSocket Handler Server")
    print("=" * 60)
    print("Starting server on ws://localhost:8004/ws")
    print()
    print("Test with Claude commands (MCP tools will be loaded if available):")
    print('  claude -p --output-format stream-json --verbose --mcp-config .mcp.json \\')
    print('    --allowedTools "mcp__perplexity-ask mcp__brave-search mcp__github mcp__ripgrep mcp__puppeteer" \\')
    print('    --dangerously-skip-permissions "What is 2+2?"')
    print()
    print("Or run with --simple, --medium, or --long to test Claude directly")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    # Create FastAPI app
    app = FastAPI()
    
    # Initialize components
    session_manager = SessionManager(10)
    process_manager = ProcessManager()
    stream_handler = StreamHandler()
    handler = WebSocketHandler(session_manager, process_manager, stream_handler)
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        session_id = str(uuid.uuid4())
        print(f"\n[NEW CONNECTION] Session: {session_id}")
        await handler.handle_connection(websocket, session_id)
        print(f"[DISCONNECTED] Session: {session_id}\n")
    
    # Build Claude test commands
    def build_claude_tests():
        """Build Claude test commands with MCP configuration."""
        # Load MCP servers from config
        mcp_servers = []
        mcp_config_path = '.mcp.json'
        
        if os.path.exists(mcp_config_path):
            try:
                with open(mcp_config_path, 'r') as f:
                    mcp_config = json.load(f)
                    # Get server names for allowedTools
                    mcp_servers = list(mcp_config.get('mcpServers', {}).keys())
            except Exception as e:
                print(f"Warning: Could not load MCP config: {e}")
        
        # Build base command with MCP config
        base_cmd = 'claude -p --output-format stream-json --verbose'
        if mcp_servers:
            # Add MCP config and allowed tools
            allowed_tools = ' '.join([f'mcp__{server}' for server in mcp_servers])
            base_cmd += f' --mcp-config {mcp_config_path} --allowedTools "{allowed_tools}" --dangerously-skip-permissions'
        
        # Build test commands
        tests = {
            "--simple": (base_cmd + ' "What is 2+2?"', "Simple math question"),
            "--medium": (base_cmd + ' "Write 5 haikus about coding"', "Stream 5 haikus"),
            "--long": (base_cmd + ' "Write a 5000 word science fiction story about a programmer who discovers their code is sentient"', "Long story generation"),
        }
        
        # Add tool-free tests for diagnostics
        tests["--no-tools"] = (
            'claude -p "What is 2+2?" --output-format stream-json --verbose',
            "Minimal tool-free test"
        )
        tests["--no-tools-long"] = (
            'claude -p "Write a 5000 word science fiction story about a programmer who discovers their code is sentient" --output-format stream-json --verbose',
            "Long story without tools"
        )
        
        return tests
    
    CLAUDE_TESTS = build_claude_tests()
    
    # Check which test to run
    import sys
    test_to_run = None
    for arg in sys.argv[1:]:
        if arg in CLAUDE_TESTS:
            test_to_run = arg
            break
    
    # Define test function if needed
    if test_to_run:
        test_process_manager = ProcessManager()
        test_stream_handler = StreamHandler()
        
        async def run_claude_test():
            """Run a Claude test to verify everything works."""
            command, description = CLAUDE_TESTS[test_to_run]
            
            print("\n" + "=" * 60)
            print(f"Running Claude Test: {description}")
            print("=" * 60)
            print(f"Command: {command}")
            print()
            
            start_time = time.time()
            # Execute from the correct directory to find .mcp.json
            # __file__ is websocket_handler.py, we need to go up 4 levels to project root
            # websocket_handler.py -> core -> cc_executor -> src -> [project root]
            cwd = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            print(f"Working directory: {cwd}")
            print(f".mcp.json exists: {os.path.exists(os.path.join(cwd, '.mcp.json'))}")
            process = await test_process_manager.execute_command(command, cwd=cwd)
            
            # Collect output
            output_lines = []
            total_bytes = 0
            
            async def collect_output(stream_type: str, data: str):
                nonlocal total_bytes
                if data.strip():
                    output_lines.append(data.strip())
                    total_bytes += len(data)
                    # Show progress for long outputs
                    if len(output_lines) % 10 == 0:
                        elapsed = time.time() - start_time
                        print(f"  [{elapsed:.1f}s] {len(output_lines)} lines, {total_bytes:,} bytes...")
            
            # Use a longer timeout for Claude story generation
            await test_stream_handler.multiplex_streams(
                process.stdout,
                process.stderr,
                collect_output,
                timeout=600.0  # 10 minute timeout for long story generation
            )
            
            exit_code = await process.wait()
            elapsed = time.time() - start_time
            
            print(f"\nCompleted in {elapsed:.1f}s")
            print(f"Exit code: {exit_code}")
            print(f"Output: {len(output_lines)} lines, {total_bytes:,} bytes")
            
            if output_lines:
                print("\nClaude's response:")
                # Try to parse JSON and extract the actual message - NO TRUNCATION
                for line in output_lines:
                    try:
                        if line.startswith('{'):
                            data = json.loads(line)
                            if data.get('type') == 'assistant' and 'content' in data.get('message', {}):
                                for content in data['message']['content']:
                                    if content.get('type') == 'text':
                                        # SHOW THE FULL TEXT - NO TRUNCATION
                                        print("-" * 60)
                                        print(content['text'])
                                        print("-" * 60)
                                        word_count = len(content['text'].split())
                                        print(f"Total words: {word_count:,}")
                                    elif content.get('type') == 'tool_use':
                                        # Handle tool use (like Write tool with story content)
                                        tool_input = content.get('input', {})
                                        if 'content' in tool_input:
                                            print("-" * 60)
                                            print("[Tool Use Content - e.g., story being written to file]")
                                            print(tool_input['content'])  # Show FULL content, no truncation
                                            print("-" * 60)
                                            word_count = len(tool_input.get('content', '').split())
                                            print(f"Total words in tool use: {word_count:,}")
                            elif data.get('type') == 'result':
                                print(f"Duration: {data.get('duration_ms', 0)/1000:.1f}s (API: {data.get('duration_api_ms', 0)/1000:.1f}s)")
                    except json.JSONDecodeError:
                        pass
                
                # Also show raw JSON lines for debugging
                print("\nRaw JSON output:")
                for i, line in enumerate(output_lines):
                    print(f"Line {i+1} ({len(line)} bytes): {line}")
            
            # Save test output to test_outputs directory
            test_output_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))) + "/test_outputs"
            os.makedirs(test_output_dir, exist_ok=True)
            test_output_file = f"{test_output_dir}/claude_test_{test_to_run}_{time.strftime('%Y%m%d_%H%M%S')}.txt"
            
            with open(test_output_file, 'w') as f:
                f.write(f"Test: {description}\n")
                f.write(f"Command: {command}\n")
                f.write(f"Duration: {elapsed:.1f}s\n")
                f.write(f"Exit code: {exit_code}\n")
                f.write(f"Total output: {len(output_lines)} lines, {total_bytes:,} bytes\n")
                f.write("=" * 60 + "\n")
                f.write("\n".join(output_lines))
            
            print(f"\nTest output saved to: {test_output_file}")
            print("=" * 60)
    
    # Run the server - using asyncio.run() to manage the event loop
    async def main():
        # Run test if requested
        if test_to_run:
            await run_claude_test()
            if "--no-server" in sys.argv:
                print("\nTest completed. Exiting without starting server.")
                return
            print("\nNow starting WebSocket server...\n")
        
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=8004,
            log_level=os.environ.get('LOG_LEVEL', 'info').lower(),
            ws_ping_interval=20,
            ws_ping_timeout=20,
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    asyncio.run(main())

