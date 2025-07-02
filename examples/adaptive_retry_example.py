#!/usr/bin/env python3
"""
Example of how an agent can handle token limit notifications and retry with adaptive prompts.
"""

import asyncio
import json
import websockets
import uuid

class AdaptiveClaudeAgent:
    """An agent that adapts its prompts when hitting token limits."""
    
    def __init__(self, ws_url="ws://localhost:8005/ws"):
        self.ws_url = ws_url
        self.websocket = None
        self.session_id = None
        
    async def connect(self):
        """Connect to the WebSocket handler."""
        self.websocket = await websockets.connect(self.ws_url, ping_timeout=None)
        msg = await self.websocket.recv()
        data = json.loads(msg)
        self.session_id = data['params']['session_id']
        print(f"✅ Connected: Session {self.session_id}")
        
    async def execute_with_retry(self, prompt, max_retries=3):
        """Execute a prompt with automatic retry on token limits."""
        
        original_prompt = prompt
        attempt = 0
        
        while attempt <= max_retries:
            print(f"\n📝 Attempt {attempt + 1}/{max_retries + 1}")
            print(f"   Prompt: {prompt[:100]}...")
            
            # Send command
            command = {
                "jsonrpc": "2.0",
                "method": "execute",
                "params": {
                    "command": f'claude -p "{prompt}" --output-format stream-json --dangerously-skip-permissions --allowedTools none --verbose'
                },
                "id": str(uuid.uuid4())
            }
            
            await self.websocket.send(json.dumps(command))
            
            # Monitor execution
            success = await self._monitor_execution()
            
            if success:
                print("✅ Execution successful!")
                return True
                
            # Adapt prompt for retry
            if attempt < max_retries:
                prompt = self._adapt_prompt(original_prompt, prompt, attempt + 1)
                attempt += 1
            else:
                print("❌ Max retries reached")
                return False
                
    async def _monitor_execution(self):
        """Monitor execution for completion or errors."""
        
        while True:
            try:
                msg = await asyncio.wait_for(self.websocket.recv(), timeout=300.0)
                data = json.loads(msg)
                
                method = data.get("method", "")
                
                if method == "error.token_limit_exceeded":
                    params = data["params"]
                    print(f"\n🚨 Token limit exceeded: {params.get('limit'):,} tokens")
                    print(f"   Suggestion: {params.get('suggestion')}")
                    return False
                    
                elif method == "error.rate_limit_exceeded":
                    params = data["params"]
                    print(f"\n🚨 Rate limit exceeded: {params.get('message')}")
                    return False
                    
                elif method == "process.completed":
                    params = data["params"]
                    exit_code = params.get('exit_code', -1)
                    if exit_code == 0:
                        return True
                    else:
                        print(f"\n❌ Process failed with exit code: {exit_code}")
                        return False
                        
                elif method == "heartbeat":
                    print("💓", end="", flush=True)
                    
            except asyncio.TimeoutError:
                print("\n⏱️ Execution timeout")
                return False
                
    def _adapt_prompt(self, original_prompt, current_prompt, attempt):
        """Adapt the prompt based on retry attempt."""
        
        if attempt == 1:
            # First retry: Add conciseness instruction
            print("\n🔄 Retry strategy: Adding conciseness instruction")
            return f"{current_prompt} Please be concise and limit your response to essential information only."
            
        elif attempt == 2:
            # Second retry: Specify word limit
            print("\n🔄 Retry strategy: Specifying word limit")
            return f"{original_prompt} Please limit your response to approximately 1000 words."
            
        elif attempt == 3:
            # Third retry: Request outline only
            print("\n🔄 Retry strategy: Requesting outline only")
            if "guide" in original_prompt.lower():
                return f"Create a detailed outline (not full content) for: {original_prompt}"
            else:
                return f"Provide a brief summary of: {original_prompt}"
                
        return current_prompt
        
    async def close(self):
        """Close the WebSocket connection."""
        if self.websocket:
            await self.websocket.close()


async def main():
    """Demonstrate adaptive retry on token limits."""
    
    print("Adaptive Claude Agent Example")
    print("=" * 60)
    
    agent = AdaptiveClaudeAgent()
    
    try:
        # Connect to WebSocket handler
        await agent.connect()
        
        # Test with a prompt that might exceed token limits
        long_prompt = (
            "Write a comprehensive 8000 word technical guide on Python async/await. "
            "Cover event loops, coroutines, tasks, futures, synchronization, "
            "subprocess management, network programming, error handling, and "
            "performance optimization. Include extensive code examples."
        )
        
        print(f"\nOriginal request: {long_prompt[:100]}...")
        
        # Execute with automatic retry
        success = await agent.execute_with_retry(long_prompt)
        
        print("\n" + "=" * 60)
        print("FINAL RESULT")
        print("=" * 60)
        if success:
            print("✅ Successfully completed the request")
            print("   The adaptive retry strategy worked!")
        else:
            print("❌ Failed to complete the request")
            print("   Even with retries, the request couldn't be fulfilled")
            
    finally:
        await agent.close()


if __name__ == "__main__":
    print("Make sure the WebSocket handler is running on port 8005")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nExample interrupted")