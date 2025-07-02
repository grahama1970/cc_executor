#!/usr/bin/env python3
"""
Timeout Recovery Manager - Last line of defense for prompt execution

Implements progressive recovery strategies when prompts timeout or fail.
"""

import asyncio
import time
import re
from typing import Dict, Optional, List, Tuple
from loguru import logger

class TimeoutRecoveryManager:
    """
    Manages timeout recovery and re-prompting strategies.
    
    This is the last line of defense when Claude instances timeout or 
    produce incomplete responses.
    """
    
    def __init__(self):
        self.recovery_attempts = {}
        self.recovery_strategies = [
            self._immediate_acknowledgment_strategy,
            self._progressive_simplification_strategy,
            self._checkpoint_based_strategy,
            self._bare_minimum_strategy
        ]
        
    async def execute_with_recovery(
        self, 
        original_prompt: str,
        prompt_id: str,
        execute_fn,
        max_attempts: int = 3,
        base_timeout: int = 90
    ) -> Dict:
        """
        Execute prompt with automatic recovery on timeout.
        
        Args:
            original_prompt: The original prompt text
            prompt_id: Unique identifier for this prompt
            execute_fn: Async function to execute the prompt
            max_attempts: Maximum recovery attempts
            base_timeout: Base timeout in seconds
            
        Returns:
            Execution result with recovery metadata
        """
        self.recovery_attempts[prompt_id] = []
        
        for attempt in range(1, max_attempts + 1):
            try:
                # Select recovery strategy based on attempt
                strategy_fn = self.recovery_strategies[min(attempt - 1, 3)]
                
                # Modify prompt with recovery strategy
                recovery_prompt = strategy_fn(original_prompt, attempt)
                
                # Increase timeout with each attempt
                timeout = base_timeout * (1.5 ** (attempt - 1))
                
                logger.info(f"Attempt {attempt}/{max_attempts} for {prompt_id}")
                logger.debug(f"Using strategy: {strategy_fn.__name__}")
                logger.debug(f"Timeout: {timeout}s")
                
                # Execute with recovery-aware prompt
                start_time = time.time()
                result = await execute_fn(recovery_prompt, timeout=timeout)
                elapsed = time.time() - start_time
                
                # Record attempt
                self.recovery_attempts[prompt_id].append({
                    'attempt': attempt,
                    'strategy': strategy_fn.__name__,
                    'success': result.get('success', False),
                    'elapsed': elapsed,
                    'timeout': timeout
                })
                
                if result.get('success'):
                    result['recovery_metadata'] = {
                        'attempts': attempt,
                        'final_strategy': strategy_fn.__name__,
                        'recovery_needed': attempt > 1
                    }
                    return result
                    
                # Check if response indicates timeout
                if self._is_timeout_response(result):
                    logger.warning(f"Timeout detected in attempt {attempt}")
                    continue
                    
            except asyncio.TimeoutError:
                logger.error(f"Attempt {attempt} timed out after {timeout}s")
                continue
            except Exception as e:
                logger.error(f"Attempt {attempt} failed: {e}")
                continue
        
        # All attempts failed
        return {
            'success': False,
            'error': 'All recovery attempts exhausted',
            'recovery_metadata': {
                'attempts': max_attempts,
                'all_attempts': self.recovery_attempts[prompt_id]
            }
        }
    
    def _immediate_acknowledgment_strategy(self, prompt: str, attempt: int) -> str:
        """
        Strategy 1: Add immediate acknowledgment requirement.
        """
        return f"""IMPORTANT: Start your response with "ACKNOWLEDGED: Processing request..." within 2 seconds.

{prompt}

Response Protocol:
1. First line: "ACKNOWLEDGED: Processing request..."
2. Provide your response with clear section markers
3. If running long, use "CONTINUING..." markers every 20 seconds
4. Prioritize core information first"""
    
    def _progressive_simplification_strategy(self, prompt: str, attempt: int) -> str:
        """
        Strategy 2: Progressively simplify the request.
        """
        # Extract the core question
        lines = prompt.split('\n')
        question_lines = [l for l in lines if '?' in l]
        core_request = question_lines[0] if question_lines else lines[0]
        
        return f"""SIMPLIFIED REQUEST (Attempt {attempt}):

Core Question: {core_request}

REQUIREMENTS:
- Acknowledge immediately: "WORKING..."
- Answer in under 200 words
- Focus only on the essential answer
- Skip examples unless critical
- Use bullet points for clarity

Begin response NOW."""
    
    def _checkpoint_based_strategy(self, prompt: str, attempt: int) -> str:
        """
        Strategy 3: Checkpoint-based response structure.
        """
        # Extract first 200 chars as summary
        prompt_summary = prompt[:200].strip() + "..."
        
        return f"""TIME-CRITICAL REQUEST:

{prompt_summary}

CHECKPOINT RESPONSE STRUCTURE:
[0-5s] Output: "CHECKPOINT 1: Understanding request..."
[5-15s] Output: "CHECKPOINT 2: Core answer: [provide main point]"
[15-30s] Output: "CHECKPOINT 3: Key details: [add important details]"
[30s+] Output: "CHECKPOINT 4: [optional examples/elaboration]"

If sensing timeout, immediately output: "[PARTIAL] [summary of what you have]"

Start with CHECKPOINT 1 immediately."""
    
    def _bare_minimum_strategy(self, prompt: str, attempt: int) -> str:
        """
        Strategy 4: Absolute bare minimum response.
        """
        # Extract just key words
        words = re.findall(r'\b\w+\b', prompt)
        key_words = [w for w in words if len(w) > 4][:10]
        
        return f"""CRITICAL - MINIMAL RESPONSE REQUIRED:

Keywords: {' '.join(key_words)}

Reply with:
1. "ACK" (immediately)
2. One sentence answer
3. Nothing else

GO!"""
    
    def _is_timeout_response(self, result: Dict) -> bool:
        """
        Check if response indicates a timeout occurred.
        """
        if not result.get('output'):
            return True
            
        timeout_indicators = [
            'timeout',
            'timed out',
            'taking too long',
            'connection lost',
            'no response'
        ]
        
        output_lower = str(result.get('output', '')).lower()
        return any(indicator in output_lower for indicator in timeout_indicators)
    
    def get_recovery_stats(self, prompt_id: str) -> Dict:
        """
        Get recovery statistics for a specific prompt.
        """
        attempts = self.recovery_attempts.get(prompt_id, [])
        if not attempts:
            return {}
            
        successful = [a for a in attempts if a['success']]
        
        return {
            'total_attempts': len(attempts),
            'successful_attempts': len(successful),
            'recovery_rate': len(successful) / len(attempts) if attempts else 0,
            'strategies_used': [a['strategy'] for a in attempts],
            'total_time': sum(a['elapsed'] for a in attempts),
            'final_success': attempts[-1]['success'] if attempts else False
        }
    
    def generate_recovery_report(self) -> str:
        """
        Generate a report of all recovery attempts.
        """
        report_lines = ["Timeout Recovery Report", "=" * 50]
        
        total_prompts = len(self.recovery_attempts)
        if not total_prompts:
            return "No recovery attempts recorded."
        
        # Calculate overall stats
        total_attempts = sum(len(attempts) for attempts in self.recovery_attempts.values())
        recovered = sum(
            1 for attempts in self.recovery_attempts.values()
            if any(a['success'] for a in attempts[1:])  # Successful after first attempt
        )
        
        report_lines.extend([
            f"Total prompts with recovery: {total_prompts}",
            f"Total recovery attempts: {total_attempts}",
            f"Successfully recovered: {recovered}",
            f"Recovery rate: {recovered/total_prompts*100:.1f}%",
            "",
            "Per-Prompt Details:",
            "-" * 50
        ])
        
        for prompt_id, attempts in self.recovery_attempts.items():
            stats = self.get_recovery_stats(prompt_id)
            report_lines.extend([
                f"\nPrompt: {prompt_id}",
                f"  Attempts: {stats['total_attempts']}",
                f"  Success: {'Yes' if stats['final_success'] else 'No'}",
                f"  Total time: {stats['total_time']:.1f}s",
                f"  Strategies: {', '.join(set(stats['strategies_used']))}"
            ])
        
        return '\n'.join(report_lines)


# Example integration with process manager
async def execute_with_recovery_example():
    """
    Example of using the recovery manager with a process executor.
    """
    recovery_manager = TimeoutRecoveryManager()
    
    # Mock execute function
    async def mock_execute(prompt, timeout):
        # Simulate execution
        await asyncio.sleep(2)
        
        # Simulate different outcomes
        if "ACKNOWLEDGED" in prompt:
            return {'success': True, 'output': 'ACKNOWLEDGED: Processing...'}
        elif "CHECKPOINT" in prompt:
            return {'success': True, 'output': 'CHECKPOINT 1: Done'}
        elif "ACK" in prompt:
            return {'success': True, 'output': 'ACK. Answer: Yes.'}
        else:
            # Simulate timeout
            raise asyncio.TimeoutError()
    
    # Test recovery
    result = await recovery_manager.execute_with_recovery(
        original_prompt="What is a complex algorithm for sorting?",
        prompt_id="test_sort_001",
        execute_fn=mock_execute,
        max_attempts=4,
        base_timeout=30
    )
    
    print("Result:", result)
    print("\nRecovery Report:")
    print(recovery_manager.generate_recovery_report())


if __name__ == "__main__":
    # Run example
    asyncio.run(execute_with_recovery_example())