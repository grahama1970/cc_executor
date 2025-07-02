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
import re
from typing import Optional, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

# Configure logging for production use
# Remove default logger to avoid duplicate logs
logger.remove()

# Console logging (INFO and above)
logger.add(sys.stderr, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>", level="INFO")

# File logging (DEBUG and above) with rotation
# Navigate from websocket_handler.py -> core -> cc_executor -> src -> experiments -> cc_executor root
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
log_dir = os.path.join(project_root, "logs")
os.makedirs(log_dir, exist_ok=True)  # Ensure log directory exists
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
    from .resource_monitor import adjust_timeout
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
    from resource_monitor import adjust_timeout


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
        
        # Initialize Redis task timer for intelligent timeout estimation
        try:
            # Lazy import to avoid circular import issues
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from prompts.redis_task_timing import RedisTaskTimer
            self.redis_timer = RedisTaskTimer()
            logger.info("Redis task timer initialized for intelligent timeout estimation")
        except Exception as e:
            logger.warning(f"Could not initialize Redis task timer: {e}. Using fallback timeouts.")
            self.redis_timer = None
            
        # Initialize hook integration
        try:
            from .hook_integration import HookIntegration
            self.hooks = HookIntegration()
            if self.hooks.enabled:
                logger.info(f"Hook integration enabled with {len(self.hooks.config.get('hooks', {}))} hooks configured")
        except Exception as e:
            logger.warning(f"Could not initialize hook integration: {e}")
            self.hooks = None
        
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
                ).model_dump()
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
            elif method == "hook_status":
                await self._handle_hook_status(session_id, params, msg_id)
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
            
            # F6: Remove logging of sensitive data - don't log API key information
            # Check environment silently without logging sensitive info
            
            # Execute pre-execution hook if available
            if self.hooks and self.hooks.enabled:
                try:
                    # First try hook-based complexity analysis
                    hook_complexity = await self.hooks.analyze_command_complexity(req.command)
                    if hook_complexity and req.timeout is None:
                        req.timeout = hook_complexity.get('estimated_timeout', 120)
                        logger.info(f"[HOOK TIMEOUT] Estimated timeout: {req.timeout}s "
                                  f"(complexity: {hook_complexity.get('complexity')}, "
                                  f"confidence: {hook_complexity.get('confidence', 0):.2f})")
                        
                    # Execute pre-execution validation hook
                    pre_result = await self.hooks.pre_execution_hook(req.command, session_id)
                    if pre_result:
                        # Check if environment was setup
                        if 'pre-execute' in pre_result and pre_result['pre-execute'].get('success'):
                            logger.info("[HOOK ENV] Environment setup hook executed successfully")
                            
                            # Check if we need to modify environment
                            try:
                                # F7: Graceful Redis fallback
                                import redis
                                r = redis.Redis(decode_responses=True)
                                env_key = f"hook:env_setup:{session_id}"
                                env_data = r.get(env_key)
                                
                                if env_data:
                                    env_info = json.loads(env_data)
                                    if 'wrapped_command' in env_info:
                                        original_cmd = req.command
                                        req.command = env_info['wrapped_command']
                                        logger.info(f"[HOOK ENV] Command wrapped for venv: {req.command[:100]}...")
                            except Exception as e:
                                logger.debug(f"Could not check environment updates: {e}")
                                
                        # N2: Improve error propagation - surface pre-execute failures as warnings
                        for hook_name, result in pre_result.items():
                            if not result.get('success'):
                                error_msg = result.get('error', 'Unknown error')
                                stderr = result.get('stderr', '')
                                
                                # Create detailed warning message
                                warning_details = f"Pre-execution hook '{hook_name}' failed: {error_msg}"
                                if stderr:
                                    warning_details += f"\nStderr: {stderr[:500]}"  # Truncate long stderr
                                
                                logger.warning(warning_details)
                                
                                # Send warning notification to client
                                await self._send_notification(
                                    session.websocket,
                                    "hook.warning",
                                    {
                                        "hook_type": hook_name,
                                        "error": error_msg,
                                        "stderr": stderr[:500] if stderr else None,
                                        "message": f"Hook '{hook_name}' failed but execution will continue",
                                        "severity": "warning"
                                    }
                                )
                                
                                # Special handling for invalid command errors
                                if "invalid command" in error_msg.lower() or "command not found" in error_msg.lower():
                                    # Still execute but with prominent warning
                                    await self._send_notification(
                                        session.websocket,
                                        "command.validation_warning",
                                        {
                                            "command": req.command[:100],
                                            "warning": "Command may be invalid or not found",
                                            "suggestion": "Check command syntax and availability"
                                        }
                                    )
                except Exception as e:
                    logger.error(f"Hook execution error: {e}")
                    
            # If no timeout provided, use Redis to estimate based on historical data
            if req.timeout is None and self.redis_timer:
                try:
                    estimation = await self.redis_timer.estimate_complexity(req.command)
                    req.timeout = int(estimation['max_time'])  # Use max_time for safety
                    logger.info(f"[REDIS TIMEOUT] Estimated timeout: {req.timeout}s based on {estimation['based_on']} "
                              f"(category: {estimation['category']}, complexity: {estimation['complexity']})")
                except Exception as e:
                    logger.warning(f"[REDIS TIMEOUT] Could not estimate timeout: {e}")
                    # Fall back to default timeout logic
                
            # Record start time for metrics
            start_time = time.time()
            
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
                ).model_dump()
            )
            
            # Start streaming task with optional timeout from request
            stream_task = asyncio.create_task(
                self._stream_process_output(session_id, process, req.command, req.timeout)
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
                ).model_dump()
            )
            
            # Handle cancellation
            if req.type == "CANCEL":
                if session.task and not session.task.done():
                    session.task.cancel()
                    # Wait a moment for cancellation to propagate
                    try:
                        await asyncio.wait_for(session.task, timeout=2.0)
                    except (asyncio.CancelledError, asyncio.TimeoutError):
                        pass
                
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
            
    async def _handle_hook_status(
        self,
        session_id: str,
        params: Dict[str, Any],
        msg_id: Optional[Any]
    ) -> None:
        """
        Handle hook status query request.
        
        Args:
            session_id: Session identifier
            params: Request parameters (unused)
            msg_id: Request ID for response correlation
        """
        session = await self.sessions.get_session(session_id)
        if not session:
            return
            
        try:
            # Get hook status
            if self.hooks:
                status = self.hooks.get_hook_status()
                
                # Add Redis metrics if available
                if self.redis_timer:
                    try:
                        import redis
                        r = redis.Redis(decode_responses=True)
                        
                        # Get recent hook executions
                        recent_hooks = r.lrange("hook:executions", 0, 9)
                        status['recent_executions'] = [
                            json.loads(h) for h in recent_hooks
                        ] if recent_hooks else []
                        
                        # Get hook statistics
                        stats = r.hgetall("hook:stats")
                        status['statistics'] = stats if stats else {}
                        
                    except Exception as e:
                        logger.debug(f"Could not get hook metrics: {e}")
                        
            else:
                status = {
                    'enabled': False,
                    'message': 'Hook integration not initialized'
                }
                
            # Send response
            await self._send_response(
                session.websocket,
                status,
                msg_id
            )
            
        except Exception as e:
            logger.error(f"Error getting hook status: {e}")
            await self._send_error(
                session.websocket,
                ERROR_INTERNAL_ERROR,
                str(e),
                msg_id
            )
            
    async def _stream_process_output(self, session_id: str, process: Any, command: str, timeout: Optional[int] = None) -> None:
        """
        Stream process output to WebSocket.
        
        Args:
            session_id: Session identifier
            process: Process to stream from
            command: The command being executed
            timeout: Optional timeout in seconds for the command
        """
        session = await self.sessions.get_session(session_id)
        if not session:
            return
            
        # Track execution start time for Redis history
        execution_start = time.time()
        
        # Collect output for post-execution hook
        collected_output = []
            
        async def send_output(stream_type: str, data: str):
            """Send output line to client, chunking if necessary."""
            # Collect output for hooks (limit to prevent memory issues)
            if stream_type == "stdout" and len(collected_output) < 100:
                collected_output.append(data[:1000])  # Limit each line
                
            # Check for token limit errors in the output
            if stream_type == "stdout":
                # Token limit detection patterns
                if "Claude's response exceeded the" in data and "output token maximum" in data:
                    # Extract token limit if possible
                    limit_match = re.search(r'exceeded the (\d+) output token', data)
                    token_limit = int(limit_match.group(1)) if limit_match else 32000
                    
                    logger.warning(f"[TOKEN LIMIT EXCEEDED] Detected token limit error: {token_limit} tokens")
                    
                    # Send special notification for token limit
                    await self._send_notification(
                        session.websocket,
                        "error.token_limit_exceeded",
                        {
                            "session_id": session_id,
                            "error_type": "token_limit",
                            "limit": token_limit,
                            "message": f"Claude's output exceeded {token_limit} token limit",
                            "suggestion": "Retry with a more concise prompt or specify word/token limits",
                            "error_text": data.strip(),
                            "recoverable": True
                        }
                    )
                
                # Rate limit detection patterns
                elif "Claude AI usage limit reached" in data:
                    logger.warning("[RATE LIMIT] Detected usage limit error")
                    
                    # Extract reset time if available
                    reset_match = re.search(r'resets at (\d+)', data)
                    reset_timestamp = int(reset_match.group(1)) if reset_match else None
                    
                    await self._send_notification(
                        session.websocket,
                        "error.rate_limit_exceeded",
                        {
                            "session_id": session_id,
                            "error_type": "usage_limit",
                            "message": "Claude AI usage limit reached",
                            "reset_timestamp": reset_timestamp,
                            "error_text": data.strip(),
                            "recoverable": False
                        }
                    )
                
                # HTTP 429 rate limit
                elif "429" in data and ("rate limit" in data.lower() or "too many requests" in data.lower()):
                    logger.warning("[RATE LIMIT] Detected HTTP 429 error")
                    
                    await self._send_notification(
                        session.websocket,
                        "error.rate_limit_exceeded",
                        {
                            "session_id": session_id,
                            "error_type": "rate_limit_429",
                            "message": "HTTP 429 Too Many Requests",
                            "error_text": data.strip(),
                            "recoverable": True,
                            "retry_after": 60  # Default retry after 60 seconds
                        }
                    )
            
            # Chunk large messages to avoid WebSocket frame size limits
            # Increased from 4KB to 64KB for better handling of large outputs like essays
            MAX_CHUNK_SIZE = 65536  # 64KB chunks
            
            if len(data) <= MAX_CHUNK_SIZE:
                # Small message, send as-is
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
                    ).model_dump()
                )
            else:
                # Large message, send in chunks
                logger.info(f"[CHUNKED OUTPUT] {stream_type} sending {len(data):,} chars in {(len(data) + MAX_CHUNK_SIZE - 1) // MAX_CHUNK_SIZE} chunks")
                
                for i in range(0, len(data), MAX_CHUNK_SIZE):
                    chunk = data[i:i + MAX_CHUNK_SIZE]
                    is_last_chunk = (i + MAX_CHUNK_SIZE) >= len(data)
                    
                    await self._send_notification(
                        session.websocket,
                        "process.output",
                        StreamOutput(
                            type=stream_type,
                            data=chunk,
                            truncated=not is_last_chunk or data.endswith("...\n"),
                            chunk_index=i // MAX_CHUNK_SIZE,
                            total_chunks=(len(data) + MAX_CHUNK_SIZE - 1) // MAX_CHUNK_SIZE
                        ).model_dump()
                    )
            
        try:
            # Stream output with dynamic timeout adjustment based on system load
            # The WebSocket ping/pong keeps the connection alive
            
            # Check if we should apply a timeout
            # Use the timeout from the request if provided
            if timeout:
                stream_timeout = timeout
                logger.info(f"Using requested timeout: {stream_timeout}s")
            elif 'claude' in command:
                # Default timeout for Claude commands if not specified
                # Complex tasks should specify their own timeout
                stream_timeout = 120  # 2 minutes default for Claude
                logger.info(f"Using default Claude timeout: {stream_timeout}s")
            elif os.environ.get('ENABLE_STREAM_TIMEOUT', 'false').lower() == 'true':
                # Use STREAM_TIMEOUT from config with dynamic adjustment
                base_timeout = STREAM_TIMEOUT
                stream_timeout = adjust_timeout(base_timeout)
                logger.info(f"Streaming output with {stream_timeout}s timeout (base: {base_timeout}s)")
            else:
                stream_timeout = None
                logger.info(f"Streaming output (no timeout - process will complete naturally)")
            
            # FIX: Handle streaming with timeout gracefully
            try:
                await self.streamer.multiplex_streams(
                    process.stdout,
                    process.stderr,
                    send_output,
                    timeout=stream_timeout
                )
            except asyncio.TimeoutError:
                logger.warning(f"Stream timeout after {stream_timeout}s - likely Claude gave short response")
                # Continue to process completion
            
            # Wait for process completion with timeout
            try:
                exit_code = await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Process wait timeout - checking exit code")
                exit_code = process.returncode if process.returncode is not None else 0
            
            # Log completion details
            completion_status = "completed" if exit_code == 0 else "failed"
            execution_time = time.time() - execution_start
            logger.info(f"[PROCESS COMPLETED] PID: {process.pid}, Exit code: {exit_code}, "
                       f"Status: {completion_status}, Duration: {execution_time:.1f}s")
            
            # Update Redis history with execution results
            if self.redis_timer and exit_code == 0:  # Only record successful executions
                try:
                    task_type = self.redis_timer.classify_command(command)
                    expected_time = timeout if timeout else execution_time
                    await self.redis_timer.update_history(
                        task_type=task_type,
                        elapsed=execution_time,
                        success=True,
                        expected=expected_time
                    )
                    logger.info(f"[REDIS HISTORY] Updated history for {task_type['category']}:{task_type['name']}")
                except Exception as e:
                    logger.warning(f"[REDIS HISTORY] Could not update history: {e}")
                    
            # Execute post-execution hook if available
            if self.hooks and self.hooks.enabled:
                try:
                    # Join collected output
                    full_output = '\n'.join(collected_output)
                    
                    hook_results = await self.hooks.post_execution_hook(
                        command=command,
                        exit_code=exit_code,
                        duration=execution_time,
                        output=full_output
                    )
                    
                    if hook_results:
                        logger.info(f"[HOOK POST-EXEC] Executed post-execution hooks: "
                                  f"{list(hook_results.keys())}")
                        
                        # Check if any hooks suggested improvements
                        for hook_name, result in hook_results.items():
                            if result and result.get('stdout'):
                                logger.debug(f"[HOOK {hook_name}] {result['stdout'][:200]}")
                                
                except Exception as e:
                    logger.error(f"Post-execution hook error: {e}")
            
            # Notify completion
            await self._send_notification(
                session.websocket,
                "process.completed",
                StatusUpdate(
                    status=completion_status,
                    pid=process.pid,
                    pgid=session.pgid,
                    exit_code=exit_code
                ).model_dump()

            )
            
        except asyncio.CancelledError:
            logger.info(f"Streaming cancelled for {session_id}")
            # CRITICAL: Properly terminate the process when task is cancelled
            if process.returncode is None:
                logger.info(f"Terminating process {process.pid} due to cancellation")
                await self.processes.terminate_process(process, session.pgid)
            raise  # Always re-raise CancelledError
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
            ).model_dump(),
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
    print('  claude -p --mcp-config .mcp.json \\')
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
        # CRITICAL: Include --output-format stream-json for proper handling of large outputs
        base_cmd = 'claude -p --output-format stream-json'
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
            'claude -p --output-format stream-json "What is 2+2?" --dangerously-skip-permissions',
            "Minimal tool-free test"
        )
        tests["--no-tools-long"] = (
            'claude -p --output-format stream-json "Write a 5000 word science fiction story about a programmer who discovers their code is sentient" --dangerously-skip-permissions',
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

