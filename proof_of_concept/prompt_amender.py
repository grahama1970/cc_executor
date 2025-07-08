#!/usr/bin/env python3
"""
Prompt Amendment Module for cc_execute

Transforms potentially problematic prompts into reliable question format
following CLAUDE_CLI_PROMPT_BEST_PRACTICES.md guidelines.
"""
import asyncio
import json
from pathlib import Path
from typing import Tuple, Optional

async def amend_prompt(original_prompt: str, cc_execute_func) -> Tuple[str, str]:
    """
    Use Claude to amend a prompt for better reliability.
    
    Returns:
        Tuple of (amended_prompt, amendment_explanation)
    """
    amendment_task = f"""Analyze this prompt and amend it for Claude CLI reliability:

ORIGINAL PROMPT:
{original_prompt}

AMENDMENT RULES:
1. Convert imperative commands to questions ("Write X" → "What is X?")
2. Decompose multi-task prompts into atomic tasks
3. Remove interactive patterns ("Guide me", "Help me")
4. Clarify execution vs explanation needs
5. Add structure for complex requests

DECOMPOSITION RULES:
- If prompt contains "and", "then", "also", "plus" → likely multiple tasks
- If prompt has "first", "second", "finally" → sequential tasks to split
- Each task should have ONE clear objective
- Tasks should complete in under 60 seconds

If the prompt contains multiple tasks, return ONLY the first atomic task.
If the prompt is already well-formed and atomic, return it unchanged.

Return JSON with this schema:
{{
  "original_prompt": "the original prompt",
  "amended_prompt": "the improved prompt (or original if no changes needed)",
  "changes_made": ["list of changes applied"],
  "risk_assessment": "low|medium|high risk of timeout/failure",
  "explanation": "why these changes improve reliability",
  "is_ambiguous": true/false,
  "ambiguity_reason": "explanation if ambiguous (null otherwise)",
  "decomposed_tasks": ["list of atomic tasks if multi-task prompt"]
}}

AMBIGUITY DETECTION:
Mark as ambiguous if:
- No clear objective ("do something with this")
- Missing context ("fix the bug", "explain this")
- Vague requirements ("make it better", "optimize it")
- Unclear scope ("create an app", "build a system")

If ambiguous, set amended_prompt to null and explain why."""

    # Use cc_execute to amend the prompt
    result = await cc_execute_func(
        amendment_task,
        return_json=True,
        stream=False,  # No need to stream amendment
        config=None  # Use default timeout
    )
    
    if isinstance(result, dict):
        # Check for ambiguity
        if result.get('is_ambiguous', False):
            raise ValueError(f"Ambiguous prompt detected: {result.get('ambiguity_reason', 'Unknown reason')}")
        
        # Check if multi-task decomposition happened
        decomposed = result.get('decomposed_tasks', [])
        if len(decomposed) > 1:
            explanation = f"{result.get('explanation', '')} (Task 1 of {len(decomposed)})"
        else:
            explanation = result.get('explanation', 'No explanation provided')
        
        return (
            result.get('amended_prompt', original_prompt),
            explanation
        )
    else:
        # Fallback if JSON parsing fails
        return (original_prompt, "Amendment failed, using original")


def apply_basic_rules(prompt: str) -> str:
    """
    Apply basic transformation rules without calling Claude.
    Faster but less sophisticated.
    """
    # Check for obvious ambiguity first
    ambiguous_patterns = [
        ("fix the bug", "No code or context provided"),
        ("explain this", "No subject specified"),
        ("make it better", "No target or criteria specified"),
        ("optimize it", "No code or target specified"),
        ("do something with", "Vague objective"),
        ("help me", "Interactive pattern detected"),
        ("guide me", "Interactive pattern detected"),
    ]
    
    prompt_lower = prompt.lower().strip()
    for pattern, reason in ambiguous_patterns:
        if pattern in prompt_lower and len(prompt) < 50:
            raise ValueError(f"Ambiguous prompt: {reason}")
    
    # Check for too vague
    if len(prompt.split()) < 3:
        raise ValueError("Prompt too vague - needs more context")
    
    # Command verb transformations
    transformations = {
        "Write ": "What is ",
        "Create ": "What is a ",
        "Generate ": "What are ",
        "Build ": "What is the architecture for ",
        "Implement ": "What is an implementation of ",
        "Make ": "What is a way to make ",
        "Design ": "What is a design for ",
        "Develop ": "What is a development approach for ",
    }
    
    amended = prompt
    for cmd, question in transformations.items():
        if amended.startswith(cmd):
            amended = question + amended[len(cmd):] + "?"
            break
    
    # Add clarifications for common ambiguities
    if "example" in amended.lower() and "code" in amended.lower():
        if "(not code execution)" not in amended:
            amended += " (provide explanation, not code execution)"
    
    return amended


class SmartPromptAmender:
    """
    Intelligent prompt amendment with caching and fallback.
    """
    def __init__(self, cc_execute_func=None):
        self.cc_execute = cc_execute_func
        self.cache = {}
        self.stats = {
            "total_amendments": 0,
            "claude_amendments": 0,
            "basic_amendments": 0,
            "cache_hits": 0
        }
    
    async def amend(self, prompt: str, use_claude: bool = True) -> Tuple[str, str]:
        """
        Amend a prompt with intelligent routing.
        
        Args:
            prompt: Original prompt
            use_claude: Whether to use Claude for sophisticated analysis
            
        Returns:
            Tuple of (amended_prompt, explanation)
        """
        self.stats["total_amendments"] += 1
        
        # Check cache first
        if prompt in self.cache:
            self.stats["cache_hits"] += 1
            return self.cache[prompt]
        
        # Decide amendment strategy
        if use_claude and self.cc_execute and len(prompt) > 50:
            # Complex prompts benefit from Claude analysis
            try:
                self.stats["claude_amendments"] += 1
                amended, explanation = await amend_prompt(prompt, self.cc_execute)
            except Exception as e:
                # Fallback to basic rules
                print(f"⚠️  Claude amendment failed: {e}, using basic rules")
                amended = apply_basic_rules(prompt)
                explanation = "Basic rule transformation applied"
        else:
            # Simple prompts use basic rules
            self.stats["basic_amendments"] += 1
            amended = apply_basic_rules(prompt)
            explanation = "Basic rule transformation applied"
        
        # Cache the result
        self.cache[prompt] = (amended, explanation)
        
        return amended, explanation
    
    def get_stats(self) -> dict:
        """Get amendment statistics."""
        return self.stats.copy()


# Example usage patterns
if __name__ == "__main__":
    # Test basic transformations
    test_prompts = [
        "Write a Python function to calculate factorial",
        "Create a web scraper in Python",
        "Generate 20 haikus about programming",
        "What is the meaning of life?",  # Already good
        "Build a REST API with authentication",
        "First do X, then Y, then Z",  # Multi-step
        "Help me write a sorting algorithm",  # Interactive
    ]
    
    print("Basic Rule Transformations:")
    print("=" * 60)
    for prompt in test_prompts:
        try:
            amended = apply_basic_rules(prompt)
            if amended != prompt:
                print(f"❌ {prompt}")
                print(f"✅ {amended}")
            else:
                print(f"✓  {prompt} (no change needed)")
        except ValueError as e:
            print(f"🚫 {prompt}")
            print(f"   → Rejected: {e}")
        print()
    
    # Async example with Claude
    async def test_claude_amendment():
        print("\nClaude-Powered Amendment:")
        print("=" * 60)
        
        # Mock cc_execute for testing
        async def mock_cc_execute(task, **kwargs):
            return {
                "amended_prompt": "What is a Python function that calculates factorial?",
                "changes_made": ["Converted 'Write' to 'What is'", "Added question mark"],
                "risk_assessment": "low",
                "explanation": "Question format prevents execution mode hanging"
            }
        
        prompt = "Write a Python function to calculate factorial"
        amended, explanation = await amend_prompt(prompt, mock_cc_execute)
        
        print(f"Original: {prompt}")
        print(f"Amended:  {amended}")
        print(f"Reason:   {explanation}")
    
    # Run async test
    # asyncio.run(test_claude_amendment())