#!/usr/bin/env python3
"""
Enhanced timeout calculator with token awareness and thinking overhead.

Key improvements:
1. Default 90s timeout for unknown prompts
2. Accounts for "thinking tokens" from acknowledgment patterns
3. BM25 search for similar prompts when no exact match
4. Token-based timeout calculation
"""

import re
import hashlib
from typing import Dict, Optional, Tuple
from pathlib import Path

class EnhancedTimeoutCalculator:
    def __init__(self, redis_timer=None):
        self.redis_timer = redis_timer
        self.default_timeout = 90  # Default for unknown prompts
        
        # Thinking token overhead for acknowledgment patterns
        self.thinking_overhead = {
            "simple": 0,      # No acknowledgment needed
            "medium": 100,    # ~100 tokens for brief acknowledgment
            "complex": 300    # ~300 tokens for detailed acknowledgment + progress
        }
        
        # Token generation rates by model (tokens/second)
        self.token_rates = {
            "claude-3-5-sonnet-20241022": 50,
            "claude-3-5-haiku-20241022": 100,
            "claude-3-opus-20250620": 30,
            "default": 40
        }
        
    def estimate_tokens(self, prompt: str, task_type: Dict, include_thinking: bool = True) -> Dict[str, int]:
        """
        Estimate tokens including thinking/acknowledgment overhead.
        
        Args:
            prompt: The user prompt
            task_type: Task classification dict
            include_thinking: Whether to include acknowledgment token overhead
            
        Returns:
            Dictionary with token estimates
        """
        # Base input tokens (rough: 0.75 tokens per character)
        base_input_tokens = int(len(prompt) * 0.75)
        
        # Add thinking tokens if using acknowledgment pattern
        thinking_tokens = 0
        if include_thinking:
            complexity = task_type.get('complexity', 'medium')
            thinking_tokens = self.thinking_overhead.get(complexity, 100)
        
        input_tokens = base_input_tokens + thinking_tokens
        
        # Output token estimation
        output_tokens = self._estimate_output_tokens(prompt, task_type)
        
        return {
            "input_tokens": input_tokens,
            "base_input_tokens": base_input_tokens,
            "thinking_tokens": thinking_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens
        }
    
    def _estimate_output_tokens(self, prompt: str, task_type: Dict) -> int:
        """Estimate output tokens based on prompt patterns and task type."""
        
        # Check for explicit word counts
        word_count_patterns = [
            (r'(\d+)[-\s]*word', 1.5),  # tokens = words * 1.5
            (r'(\d+)k[-\s]*word', 1500),  # multiply by 1000 then 1.5
        ]
        
        for pattern, multiplier in word_count_patterns:
            match = re.search(pattern, prompt.lower())
            if match:
                count = int(match.group(1))
                if multiplier > 100:  # It's the 'k' pattern
                    return int(count * multiplier)
                else:
                    return int(count * multiplier)
        
        # Check for specific counts
        count_patterns = [
            (r'(\d+)\s*haiku', 40),      # tokens per haiku
            (r'(\d+)\s*function', 150),   # tokens per function
            (r'(\d+)\s*question', 20),    # tokens per Q&A
            (r'(\d+)\s*script', 100),     # tokens per script idea
            (r'list of (\d+)', 30),       # tokens per list item
        ]
        
        for pattern, per_item in count_patterns:
            match = re.search(pattern, prompt.lower())
            if match:
                count = int(match.group(1))
                return count * per_item
        
        # Task type based estimation
        question_type_estimates = {
            "yes_no": 50,
            "calculation": 100,
            "explanation": 500,
            "code_snippet": 300,
            "code_generation": 1000,
            "creative_writing": 1500,
            "architecture": 1500,
            "comprehensive": 3000,
            "list": 300,
            "refactor": 800,
            "qa": 200,
            "general": 500  # default
        }
        
        return question_type_estimates.get(
            task_type.get('question_type', 'general'),
            500
        )
    
    async def calculate_smart_timeout(
        self, 
        command: str, 
        task_type: Dict,
        use_acknowledgment: bool = True
    ) -> Dict:
        """
        Calculate timeout using multiple strategies:
        1. Exact historical match
        2. BM25 similar prompt search  
        3. Token-based calculation
        4. Default 90s for unknowns
        """
        
        # Try Redis historical data if available
        if self.redis_timer:
            try:
                # Try exact match first
                history = await self.redis_timer.get_task_history(
                    task_type['category'],
                    task_type['name'],
                    task_type['complexity'],
                    task_type['question_type']
                )
                
                if history['sample_size'] >= 3:
                    # Good historical data
                    historical_timeout = history['max_time'] * 1.5  # 50% buffer
                    return {
                        "timeout": int(max(historical_timeout, 60)),  # Min 60s
                        "method": "historical_exact",
                        "confidence": min(history['sample_size'] / 10, 1.0),
                        "samples": history['sample_size']
                    }
                
                # Try BM25 search for similar prompts
                similar = await self.redis_timer.find_similar_tasks(
                    task_type['complexity'],
                    task_type['question_type']
                )
                
                if similar and len(similar) >= 2:
                    # Use similar tasks
                    avg_time = sum(t['avg_time'] for t in similar[:3]) / min(3, len(similar))
                    similar_timeout = avg_time * 2  # 2x buffer for similar
                    return {
                        "timeout": int(max(similar_timeout, 60)),
                        "method": "bm25_similar",
                        "confidence": 0.7,
                        "similar_count": len(similar)
                    }
                    
            except Exception as e:
                print(f"Redis lookup failed: {e}")
        
        # Fall back to token-based calculation
        token_estimate = self.estimate_tokens(command, task_type, use_acknowledgment)
        
        # Detect model from command
        model = self._detect_model(command)
        tokens_per_second = self.token_rates.get(model, self.token_rates['default'])
        
        # Calculate time components
        token_time = token_estimate['total_tokens'] / tokens_per_second
        cli_overhead = 30  # Claude CLI startup
        
        # Complexity buffer
        complexity_buffers = {
            "simple": 1.2,   # 20% buffer
            "medium": 1.5,   # 50% buffer  
            "complex": 2.0   # 100% buffer
        }
        buffer = complexity_buffers.get(task_type.get('complexity', 'medium'), 1.5)
        
        # Calculate timeout
        calculated_timeout = (cli_overhead + token_time) * buffer
        
        # Check system load
        if self.redis_timer:
            system_load = self.redis_timer.get_system_load()
            if system_load['cpu_load'] > 14.0:
                calculated_timeout *= 3.0
        
        # Apply bounds with 90s default minimum
        final_timeout = max(self.default_timeout, calculated_timeout)
        final_timeout = min(final_timeout, 1800)  # Max 30 minutes
        
        return {
            "timeout": int(final_timeout),
            "method": "token_calculation",
            "confidence": 0.5,
            "token_estimate": token_estimate,
            "token_time": token_time,
            "cli_overhead": cli_overhead,
            "complexity_buffer": buffer,
            "model": model,
            "tokens_per_second": tokens_per_second,
            "uses_default_minimum": calculated_timeout < self.default_timeout
        }
    
    def _detect_model(self, command: str) -> str:
        """Detect Claude model from command."""
        model_patterns = [
            (r'--model\s+claude-3-5-sonnet', 'claude-3-5-sonnet-20241022'),
            (r'--model\s+claude-3-5-haiku', 'claude-3-5-haiku-20241022'),
            (r'--model\s+claude-3-opus', 'claude-3-opus-20250620'),
        ]
        
        for pattern, model in model_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return model
        
        return 'default'
    
    def add_acknowledgment_to_prompt(self, prompt: str, complexity: str) -> str:
        """
        Add acknowledgment pattern to prompt based on complexity.
        
        Args:
            prompt: Original prompt
            complexity: Task complexity (simple/medium/complex)
            
        Returns:
            Enhanced prompt with acknowledgment pattern
        """
        if complexity == "simple":
            # No acknowledgment needed
            return prompt
        
        elif complexity == "medium":
            # Add brief acknowledgment
            acknowledgment = "\n\nBegin with a brief acknowledgment of this request, then provide your answer."
            return prompt + acknowledgment
        
        else:  # complex
            # Add detailed acknowledgment with progress updates
            acknowledgment = """

Start by confirming what you understand from this request in one sentence, then work through it systematically.

For complex sections, provide brief progress indicators like:
- "Analyzing requirements..."
- "Designing solution..."  
- "Implementing details..."

This helps track progress during longer responses."""
            return prompt + acknowledgment


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_timeout_calculation():
        """Test the enhanced timeout calculator"""
        
        # Create calculator (without Redis for testing)
        calc = EnhancedTimeoutCalculator()
        
        test_cases = [
            {
                "prompt": "What is 2+2?",
                "task_type": {"complexity": "simple", "question_type": "calculation"},
                "expected_method": "token_calculation"
            },
            {
                "prompt": "What is a 500-word explanation of recursion?",
                "task_type": {"complexity": "medium", "question_type": "explanation"},
                "expected_method": "token_calculation"
            },
            {
                "prompt": "What is a collection of 20 haikus about programming?",
                "task_type": {"complexity": "medium", "question_type": "creative_writing"},
                "expected_method": "token_calculation"
            },
            {
                "prompt": "What is a comprehensive 5000-word guide to microservices?",
                "task_type": {"complexity": "complex", "question_type": "comprehensive"},
                "expected_method": "token_calculation"
            }
        ]
        
        print("Enhanced Timeout Calculation Tests")
        print("=" * 60)
        
        for test in test_cases:
            prompt = test["prompt"]
            task_type = test["task_type"]
            
            # Calculate timeout
            result = await calc.calculate_smart_timeout(
                f'claude -p "{prompt}"',
                task_type,
                use_acknowledgment=True
            )
            
            # Get token estimate
            tokens = calc.estimate_tokens(prompt, task_type, include_thinking=True)
            
            print(f"\nPrompt: {prompt[:50]}...")
            print(f"Complexity: {task_type['complexity']}")
            print(f"Tokens: {tokens['total_tokens']} (input: {tokens['input_tokens']}, output: {tokens['output_tokens']})")
            print(f"Thinking tokens: {tokens['thinking_tokens']}")
            print(f"Timeout: {result['timeout']}s")
            print(f"Method: {result['method']}")
            print(f"Uses 90s minimum: {result.get('uses_default_minimum', False)}")
            
            # Show enhanced prompt
            enhanced = calc.add_acknowledgment_to_prompt(prompt, task_type['complexity'])
            if enhanced != prompt:
                print(f"Enhanced prompt adds: {len(enhanced) - len(prompt)} characters")
        
        print("\n" + "=" * 60)
        print("Key insights:")
        print("- Simple prompts: No acknowledgment, fast timeout")
        print("- Medium prompts: Brief acknowledgment, prevents timeout") 
        print("- Complex prompts: Detailed acknowledgment with progress")
        print("- Unknown prompts: Default to 90s (not 10s stall)")
        
        return True
    
    # Run test
    asyncio.run(test_timeout_calculation())