#!/usr/bin/env python3
"""
Demo: Timeout Recovery Integration

Shows how to integrate timeout recovery with process manager for 
robust prompt execution.
"""

import asyncio
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / 'src'))

from cc_executor.core.timeout_recovery_manager import TimeoutRecoveryManager
from cc_executor.core.process_manager import ProcessManager
from cc_executor.core.websocket_handler import websocket_handler
from loguru import logger

class RecoveryEnabledExecutor:
    """
    Executor with built-in timeout recovery capabilities.
    """
    
    def __init__(self, ws_url="ws://localhost:8004/ws"):
        self.ws_url = ws_url
        self.recovery_manager = TimeoutRecoveryManager()
        self.process_manager = ProcessManager()
        
    async def execute_prompt_with_recovery(
        self, 
        prompt: str, 
        prompt_id: str,
        base_timeout: int = 90,
        max_attempts: int = 3
    ):
        """
        Execute a prompt with automatic timeout recovery.
        """
        
        # Define the execution function
        async def execute_fn(modified_prompt, timeout):
            # Build Claude command
            command = f'claude -p "{modified_prompt}" --dangerously-skip-permissions --allowedTools none'
            
            # Execute via process manager
            result = await self.process_manager.execute_command(
                command=command,
                timeout=timeout,
                session_id=prompt_id
            )
            
            return {
                'success': result.get('exit_code', 1) == 0,
                'output': result.get('output', ''),
                'error': result.get('error', ''),
                'duration': result.get('duration', 0)
            }
        
        # Execute with recovery
        return await self.recovery_manager.execute_with_recovery(
            original_prompt=prompt,
            prompt_id=prompt_id,
            execute_fn=execute_fn,
            max_attempts=max_attempts,
            base_timeout=base_timeout
        )

async def demo_recovery_scenarios():
    """
    Demonstrate various recovery scenarios.
    """
    executor = RecoveryEnabledExecutor()
    
    # Test scenarios
    test_prompts = [
        {
            'id': 'simple_test',
            'prompt': 'What is 2+2? Provide just the number.',
            'timeout': 30,
            'attempts': 2
        },
        {
            'id': 'complex_test',
            'prompt': '''What is a comprehensive implementation of a web scraper in Python?
            
Include:
1. Error handling
2. Rate limiting
3. Proxy support
4. Data extraction
5. Storage options

Please provide complete, production-ready code.''',
            'timeout': 60,
            'attempts': 3
        },
        {
            'id': 'timeout_prone',
            'prompt': '''Create a detailed 1000-word essay on the history of computing, 
            including all major milestones, key figures, and technological breakthroughs 
            from 1940 to present day.''',
            'timeout': 45,  # Intentionally short
            'attempts': 4
        }
    ]
    
    print("=" * 60)
    print("Timeout Recovery Demo")
    print("=" * 60)
    
    for test in test_prompts:
        print(f"\nTesting: {test['id']}")
        print("-" * 40)
        
        result = await executor.execute_prompt_with_recovery(
            prompt=test['prompt'],
            prompt_id=test['id'],
            base_timeout=test['timeout'],
            max_attempts=test['attempts']
        )
        
        # Display results
        if result['success']:
            print(f"✅ Success after {result['recovery_metadata']['attempts']} attempt(s)")
            print(f"Strategy: {result['recovery_metadata']['final_strategy']}")
            if result['recovery_metadata']['recovery_needed']:
                print("🔄 Recovery was needed")
            
            # Show output preview
            output = result.get('output', '')
            if output:
                preview = output[:200] + "..." if len(output) > 200 else output
                print(f"Output: {preview}")
        else:
            print(f"❌ Failed after all attempts")
            print(f"Error: {result.get('error', 'Unknown')}")
        
        # Show recovery stats
        stats = executor.recovery_manager.get_recovery_stats(test['id'])
        if stats:
            print(f"\nRecovery Stats:")
            print(f"  Total attempts: {stats['total_attempts']}")
            print(f"  Total time: {stats['total_time']:.1f}s")
            print(f"  Strategies: {', '.join(set(stats['strategies_used']))}")
    
    # Final report
    print("\n" + "=" * 60)
    print(executor.recovery_manager.generate_recovery_report())

async def demo_stress_test_integration():
    """
    Show how to integrate recovery with stress tests.
    """
    print("\n" + "=" * 60)
    print("Stress Test Recovery Integration")
    print("=" * 60)
    
    # Example of updating a stress test prompt
    original_stress_prompt = """What is the architecture for a distributed system?

Include:
1. Microservices design
2. Message queuing
3. Load balancing
4. Data consistency
5. Monitoring"""
    
    # Create recovery-aware version
    recovery_aware_prompt = """What is the architecture for a distributed system?

TIMEOUT PREVENTION PROTOCOL:
- [0-5s] Output: "DESIGNING: Starting distributed system architecture..."
- [5-20s] List core components with brief descriptions
- [20-40s] Add implementation details for each component
- [40s+] Include advanced patterns and best practices

If approaching time limit, output "[CONTINUING...]" and summarize what's complete.

Include:
1. Microservices design
2. Message queuing  
3. Load balancing
4. Data consistency
5. Monitoring

Begin immediately with the first checkpoint."""
    
    print("Original prompt:")
    print(original_stress_prompt[:100] + "...")
    print("\nRecovery-aware prompt:")
    print(recovery_aware_prompt[:200] + "...")
    
    # Show how it prevents timeouts
    print("\nBenefits of recovery-aware prompts:")
    print("✓ Immediate acknowledgment prevents early timeout")
    print("✓ Checkpoints ensure partial results on timeout")
    print("✓ Progressive detail allows graceful degradation")
    print("✓ Clear markers enable parsing incomplete responses")

if __name__ == "__main__":
    # Create necessary directories
    Path("logs").mkdir(exist_ok=True)
    
    # Configure logging
    logger.add("logs/timeout_recovery_demo.log", rotation="10 MB")
    
    print("Timeout Recovery Demo")
    print("This demonstrates the 'last line of defense' for handling timeouts")
    print()
    
    # Check environment
    if 'ANTHROPIC_API_KEY' in os.environ:
        print("⚠️  Removing ANTHROPIC_API_KEY for Claude CLI")
        del os.environ['ANTHROPIC_API_KEY']
    
    # Run demos
    asyncio.run(demo_recovery_scenarios())
    asyncio.run(demo_stress_test_integration())