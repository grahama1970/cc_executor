#!/usr/bin/env python3
"""WebSocket Orchestrator for Self-Improving Prompts"""

import asyncio
import json
import websockets
import time
import sys
import os
from pathlib import Path
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

# Import Redis task timer if available
try:
    sys.path.append(str(Path(__file__).parent))
    from redis_task_timing import RedisTaskTimer
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("[Warning] Redis task timing not available, using defaults")

class WebSocketOrchestrator:
    """Orchestrates self-improving prompt execution via WebSocket MCP"""
    
    def __init__(self, websocket_uri="ws://localhost:8003/ws/mcp"):
        self.websocket_uri = websocket_uri
        self.current_iteration = 0
        self.success_count = 0
        self.failure_count = 0
        self.output_buffer = ""
        self.learned_patterns = {}
        self.redis_timer = RedisTaskTimer() if REDIS_AVAILABLE else None
    
    def add_metatags(self, command, category="unknown", task="unknown", 
                     complexity="medium", question_type="general"):
        """Add classification metatags to a command"""
        metatags = f"[category:{category}][task:{task}][complexity:{complexity}][type:{question_type}]"
        
        # If command already has metatags, don't add more
        if '[category:' in command:
            return command
            
        # Insert metatags after the quote for claude commands
        if 'claude --print' in command:
            return command.replace("--print '", f"--print '{metatags} ").replace('--print "', f'--print "{metatags} ')
        else:
            # For other commands, prepend metatags
            return f"{metatags} {command}"
        
    async def execute_with_monitoring(self, command, expected_patterns=None, timeout=None):
        """Execute command and monitor for patterns"""
        
        marker = f"MARKER_{int(time.time())}_{self.current_iteration}"
        print(f"\n{marker}")
        
        # Get complexity estimate from Redis if available
        if self.redis_timer and not timeout:
            try:
                estimate = await self.redis_timer.estimate_complexity(command)
                timeout = estimate['max_time']
                stall_timeout = estimate['stall_timeout']
                print(f"[Redis] Using estimated timeouts - Max: {timeout}s, Stall: {stall_timeout}s")
                print(f"[Redis] Based on: {estimate['based_on']} (confidence: {estimate['confidence']:.1%})")
                
                # Store classification for later update
                self.current_task_type = {
                    "category": estimate['category'],
                    "name": estimate['task'],
                    "complexity": estimate['complexity'],
                    "question_type": estimate['question_type']
                }
                self.expected_time = estimate['expected_time']
            except Exception as e:
                print(f"[Redis] Error getting estimate: {e}")
                # Use environment variables for defaults
                default_timeout = int(os.environ.get('DEFAULT_TASK_TIMEOUT', '300'))
                default_stall_timeout = int(os.environ.get('DEFAULT_STALL_TIMEOUT', '120'))
                timeout = timeout or default_timeout
                stall_timeout = default_stall_timeout
                self.current_task_type = None
        else:
            # Use environment variables for defaults
            default_timeout = int(os.environ.get('DEFAULT_TASK_TIMEOUT', '300'))
            default_stall_timeout = int(os.environ.get('DEFAULT_STALL_TIMEOUT', '120'))
            timeout = timeout or default_timeout
            stall_timeout = default_stall_timeout
            self.current_task_type = None
        
        line_buffer = ""  # Buffer for partial JSON lines
        start_time = time.time()
        
        try:
            async with websockets.connect(self.websocket_uri) as ws:
                # Wait for connection confirmation
                conn_msg = await ws.recv()
                print(f"[Connected: {json.loads(conn_msg)['params']['session_id']}]")
                
                # Execute command
                await ws.send(json.dumps({
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "execute",
                    "params": {"command": command}
                }))
                
                # Monitor execution
                last_output_time = time.time()
                self.output_buffer = ""
                success = False
                json_objects_received = []
                
                while True:
                    try:
                        # Check timeouts
                        elapsed = time.time() - start_time
                        if elapsed > timeout:
                            await self._cancel_execution(ws, f"Timeout exceeded ({elapsed:.1f}s > {timeout}s)")
                            break
                        
                        if time.time() - last_output_time > stall_timeout:
                            await self._cancel_execution(ws, f"No output for {stall_timeout}s")
                            break
                        
                        # Receive with timeout
                        msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        data = json.loads(msg)
                    
                        if data.get('method') == 'process.output':
                            chunk = data['params']['data']
                            self.output_buffer += chunk
                            last_output_time = time.time()
                            
                            # Handle JSON streaming (for --output-format stream-json)
                            line_buffer += chunk
                            lines = line_buffer.splitlines(keepends=True)
                            line_buffer = ""
                            
                            for i, line in enumerate(lines):
                                # If line doesn't end with newline, it's incomplete
                                if i == len(lines) - 1 and not line.endswith('\n'):
                                    line_buffer = line
                                    break
                                    
                                line = line.strip()
                                if line:
                                    try:
                                        json_obj = json.loads(line)
                                        json_objects_received.append(json_obj)
                                        # Process Claude's JSON events
                                        if json_obj.get('type') == 'assistant':
                                            # Extract text content from assistant messages
                                            content = json_obj.get('message', {}).get('content', [])
                                            for item in content:
                                                if item.get('type') == 'text':
                                                    print(item['text'], end='', flush=True)
                                    except json.JSONDecodeError:
                                        # Not JSON, just print as regular output
                                        print(line)
                            
                            # Check for patterns in accumulated output
                            if expected_patterns:
                                for pattern in expected_patterns:
                                    if pattern in self.output_buffer:
                                        self.learned_patterns[pattern] = True
                            
                            # Detect errors
                            if self._detect_error(chunk):
                                await self._cancel_execution(ws, "Error detected")
                                break
                        
                        elif data.get('method') == 'process.completed':
                            exit_code = data['params']['exit_code']
                            success = (exit_code == 0)
                            
                            # Verify expected patterns if provided
                            if success and expected_patterns:
                                found_patterns = [p for p in expected_patterns if p in self.output_buffer]
                                # Success if we found at least some nature patterns
                                success = len(found_patterns) > 0
                                print(f"\n[Found patterns: {found_patterns}]")
                            
                            print(f"\n[Exit code: {exit_code}]")
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                    except (ConnectionClosedError, ConnectionClosedOK) as e:
                        print(f"\n[Connection closed: {e}]")
                        break
                    except json.JSONDecodeError as e:
                        print(f"\n[Invalid JSON received: {e}]")
                        continue
            
            # Update metrics
            elapsed_time = time.time() - start_time
            
            if success:
                self.success_count += 1
                print(f"\n✓ SUCCESS (Total: {self.success_count})")
            else:
                self.failure_count += 1
                print(f"\n✗ FAILURE (Total: {self.failure_count})")
            
            # Update Redis with execution results
            if self.redis_timer and self.current_task_type:
                try:
                    await self.redis_timer.update_history(
                        task_type=self.current_task_type,
                        elapsed=elapsed_time,
                        success=success,
                        expected=self.expected_time
                    )
                except Exception as e:
                    print(f"[Redis] Error updating history: {e}")
            
            return {
                "success": success,
                "output": self.output_buffer,
                "marker": marker,
                "patterns_found": list(self.learned_patterns.keys()),
                "elapsed_time": elapsed_time
            }
        
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"\n[Connection error: {e}]")
            self.failure_count += 1
            
            # Update Redis even on failure
            if self.redis_timer and self.current_task_type:
                try:
                    await self.redis_timer.update_history(
                        task_type=self.current_task_type,
                        elapsed=elapsed_time,
                        success=False,
                        expected=self.expected_time
                    )
                except Exception as redis_e:
                    print(f"[Redis] Error updating history: {redis_e}")
            
            return {
                "success": False,
                "output": self.output_buffer,
                "marker": marker,
                "patterns_found": [],
                "error": str(e),
                "elapsed_time": elapsed_time
            }
    
    async def _cancel_execution(self, ws, reason):
        """Cancel running execution"""
        print(f"\n[Cancelling: {reason}]")
        
        await ws.send(json.dumps({
            "jsonrpc": "2.0",
            "id": 99,
            "method": "control",
            "params": {"type": "CANCEL"}
        }))
        
        # Wait for completion
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            if data.get('method') == 'process.completed':
                break
    
    def _detect_error(self, output):
        """Detect error patterns"""
        error_patterns = [
            "Traceback", "Error:", "FAILED", "AssertionError",
            "ModuleNotFoundError", "command not found",
            "Connection refused", "No such file"
        ]
        return any(pattern in output for pattern in error_patterns)
    
    def get_success_ratio(self):
        """Get current success ratio"""
        total = self.success_count + self.failure_count
        if total == 0:
            return "0:0"
        return f"{self.success_count}:{self.failure_count}"
    
    def should_graduate(self):
        """Check if 10:1 ratio achieved"""
        return self.success_count >= 10 and self.failure_count <= 1


# Utility functions for common patterns
async def execute_claude_haiku(orchestrator, num_haikus=5):
    """Execute Claude to generate haikus"""
    
    # Determine complexity based on quantity
    if num_haikus <= 5:
        complexity = "simple"
    elif num_haikus <= 20:
        complexity = "medium"
    else:
        complexity = "complex"
    
    # Build command with metatags
    metatags = f"[category:claude][task:haiku_{num_haikus}][complexity:{complexity}][type:creative]"
    command = f'''bash -c "PATH=/home/graham/.nvm/versions/node/v22.15.0/bin:$PATH claude --print '{metatags} Write {num_haikus} haikus about nature in traditional 5-7-5 syllable format, each on a new line. No code blocks.' --output-format stream-json --verbose"'''
    
    expected_patterns = [
        "haiku",  # Should mention haiku
        "nature", # Should be about nature
        "tree", "wind", "water", "sky", "mountain"  # Nature words
    ]
    
    result = await orchestrator.execute_with_monitoring(
        command=command,
        expected_patterns=expected_patterns,
        timeout=None  # Will use Redis estimate or environment default
    )
    
    # Count haikus in output
    if result and 'output' in result:
        # Look for double newlines between haikus or count individual haikus
        haiku_count = result['output'].count('\n\n') + 1 if '\n\n' in result['output'] else 0
        
        # Also check if we got the full haikus by looking for specific patterns
        if "Morning dew" in result['output'] or "haiku" in result['output'].lower():
            # Count blocks separated by double newlines
            blocks = [b.strip() for b in result['output'].split('\n\n') if b.strip()]
            haiku_count = len(blocks)
        
        print(f"\n[Generated {haiku_count} haikus]")
    
    return result


async def verify_transcript(marker):
    """Verify execution in transcript"""
    
    cmd = f'''rg "{marker}" ~/.claude/projects/-home-graham-workspace-experiments-cc-executor/*.jsonl | wc -l'''
    
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await proc.communicate()
    
    try:
        count = int(stdout.decode().strip())
        if count > 0:
            print(f"\n[Transcript verified: {marker} found {count} times]")
            return True
    except:
        pass
    
    print(f"\n[WARNING: {marker} not found in transcript]")
    return False


# Main execution
async def main():
    """Run the orchestrator with the provided task"""
    
    if len(sys.argv) < 2:
        print("Usage: python websocket_orchestrator.py <task>")
        print("Tasks: haiku5, haiku20, stress_test")
        sys.exit(1)
    
    task = sys.argv[1]
    orchestrator = WebSocketOrchestrator()
    
    if task == "haiku5":
        result = await execute_claude_haiku(orchestrator, 5)
        
    elif task == "haiku20":
        result = await execute_claude_haiku(orchestrator, 20)
        
    elif task == "stress_test":
        command = '''python src/cc_executor/tests/stress/unified_stress_test_executor_v3.py src/cc_executor/tasks/haiku_single_task.json'''
        result = await orchestrator.execute_with_monitoring(command)
    
    else:
        print(f"Unknown task: {task}")
        sys.exit(1)
    
    # Verify in transcript
    if result and 'marker' in result:
        await verify_transcript(result['marker'])
    
    # Show final metrics
    print(f"\n=== Final Metrics ===")
    print(f"Success Ratio: {orchestrator.get_success_ratio()}")
    print(f"Should Graduate: {orchestrator.should_graduate()}")


if __name__ == "__main__":
    asyncio.run(main())