#!/usr/bin/env python3
"""
Solution for handling Claude's "thinking freeze" in cc_executor.

Based on observations:
1. Claude can take 30s-3min to respond to complex prompts
2. First system output comes quickly (~1s) but content can take much longer
3. Users perceive this as "frozen" when there's no feedback

This module provides strategies to mitigate the perception of freezing.
"""

import asyncio
import time
from typing import Optional, Callable, Dict, Any


class ThinkingIndicatorHandler:
    """Handles thinking indicators for long-running Claude tasks."""
    
    def __init__(self, 
                 thinking_threshold: float = 5.0,
                 update_interval: float = 10.0):
        """
        Initialize thinking indicator handler.
        
        Args:
            thinking_threshold: Seconds to wait before showing thinking indicator
            update_interval: Seconds between thinking status updates
        """
        self.thinking_threshold = thinking_threshold
        self.update_interval = update_interval
        self.start_time = None
        self.first_content_time = None
        self.thinking_task = None
        
    async def start_monitoring(self, progress_callback: Optional[Callable] = None):
        """Start monitoring for thinking indicators."""
        self.start_time = time.time()
        
        if progress_callback:
            self.thinking_task = asyncio.create_task(
                self._thinking_monitor(progress_callback)
            )
    
    async def _thinking_monitor(self, callback: Callable):
        """Monitor and provide thinking updates."""
        await asyncio.sleep(self.thinking_threshold)
        
        # If no content yet, start showing thinking indicators
        if self.first_content_time is None:
            elapsed = time.time() - self.start_time
            await callback(f"Claude is thinking... ({elapsed:.0f}s)")
            
            # Continue updates
            while self.first_content_time is None:
                await asyncio.sleep(self.update_interval)
                elapsed = time.time() - self.start_time
                
                # Provide contextual messages based on elapsed time
                if elapsed < 30:
                    message = f"Claude is analyzing the request... ({elapsed:.0f}s)"
                elif elapsed < 60:
                    message = f"Claude is working on a complex response... ({elapsed:.0f}s)"
                elif elapsed < 120:
                    message = f"This is taking longer than usual. Claude is still processing... ({elapsed:.0f}s)"
                else:
                    message = f"Complex task in progress. Please wait... ({elapsed:.0f}s)"
                
                await callback(message)
    
    def record_first_content(self):
        """Record when first actual content is received."""
        if self.first_content_time is None:
            self.first_content_time = time.time()
            if self.thinking_task and not self.thinking_task.done():
                self.thinking_task.cancel()
    
    async def cleanup(self):
        """Clean up any running tasks."""
        if self.thinking_task and not self.thinking_task.done():
            self.thinking_task.cancel()
            try:
                await self.thinking_task
            except asyncio.CancelledError:
                pass


def enhance_prompt_for_early_response(prompt: str, complexity_score: int = 0) -> str:
    """
    Enhance a prompt to encourage early acknowledgment from Claude.
    
    Args:
        prompt: Original prompt
        complexity_score: Estimated complexity (0-10)
        
    Returns:
        Enhanced prompt that may get earlier response
    """
    if complexity_score >= 7:
        # For very complex prompts, add explicit acknowledgment request
        return f"""Please briefly acknowledge this request first by saying "Working on this complex task..." 

{prompt}"""
    elif complexity_score >= 5:
        # For moderately complex, add a softer request
        return f"""Task: {prompt}

(Please indicate you're working on this if it will take more than a few seconds)"""
    else:
        # For simple prompts, don't modify
        return prompt


def estimate_complexity(prompt: str) -> int:
    """
    Estimate prompt complexity to set expectations.
    
    Returns:
        Complexity score 0-10
    """
    # Simple heuristics
    score = 0
    
    # Length-based scoring
    if len(prompt) > 1000:
        score += 3
    elif len(prompt) > 500:
        score += 2
    elif len(prompt) > 200:
        score += 1
    
    # Keyword-based scoring
    complex_keywords = [
        'comprehensive', 'production-ready', 'implement', 'create',
        'design', 'architecture', 'analyze', 'optimize', 'refactor',
        'test', 'documentation', 'error handling', 'type hints'
    ]
    
    prompt_lower = prompt.lower()
    keyword_count = sum(1 for keyword in complex_keywords if keyword in prompt_lower)
    score += min(keyword_count, 4)
    
    # Multi-step indicators
    if any(indicator in prompt for indicator in ['step', 'first', 'then', 'finally']):
        score += 2
    
    # Code generation indicators
    if any(word in prompt_lower for word in ['function', 'class', 'module', 'api']):
        score += 1
    
    return min(score, 10)


# Integration with cc_execute
async def cc_execute_with_thinking_indicator(
    prompt: str,
    progress_callback: Optional[Callable] = None,
    enhance_prompt: bool = True,
    **kwargs
) -> Dict[str, Any]:
    """
    Execute Claude command with thinking indicators.
    
    This is a wrapper around cc_execute that adds thinking indication.
    """
    from cc_executor.client.cc_execute import cc_execute
    
    # Estimate complexity
    complexity = estimate_complexity(prompt)
    
    # Enhance prompt if requested and complexity is high
    if enhance_prompt and complexity >= 5:
        prompt = enhance_prompt_for_early_response(prompt, complexity)
    
    # Create thinking handler
    handler = ThinkingIndicatorHandler(
        thinking_threshold=5.0 if complexity < 7 else 3.0
    )
    
    # Start monitoring
    await handler.start_monitoring(progress_callback)
    
    try:
        # Execute with streaming to detect first content
        async def stream_callback(chunk):
            # Detect first real content
            if chunk and not chunk.startswith('[') and len(chunk) > 10:
                handler.record_first_content()
        
        result = await cc_execute(
            prompt,
            stream_callback=stream_callback if 'stream_callback' not in kwargs else kwargs.get('stream_callback'),
            **kwargs
        )
        
        return result
        
    finally:
        await handler.cleanup()


# Example usage
async def example_usage():
    """Example of using thinking indicators."""
    
    async def progress_handler(message: str):
        print(f"\r{message}", end='', flush=True)
    
    # Complex prompt that will likely take time
    prompt = """Create a comprehensive Python implementation of a Red-Black Tree with:
    - All standard operations (insert, delete, search)
    - Tree balancing with proper rotations
    - Validation methods
    - Visualization using ASCII art
    - Full type hints and docstrings
    - Unit tests for all methods"""
    
    print("Executing complex task with thinking indicators...")
    result = await cc_execute_with_thinking_indicator(
        prompt,
        progress_callback=progress_handler,
        enhance_prompt=True
    )
    
    print(f"\n\nResult: {result[:200]}...")


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())