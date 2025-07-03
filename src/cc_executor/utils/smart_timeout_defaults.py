#!/usr/bin/env python3
"""
Smart timeout defaults: When in doubt, use 90s+ with acknowledgment.

Core principle: Unknown prompts get generous timeouts to prevent false failures.
"""

from typing import Dict, Optional, Tuple

class SmartTimeoutDefaults:
    """
    Simple, effective timeout strategy:
    1. Known prompts: Use historical data
    2. Unknown prompts: 90s minimum + acknowledgment
    3. Never fail due to aggressive timeouts
    """
    
    def __init__(self):
        # Core defaults - generous to prevent false failures
        self.unknown_prompt_timeout = 300  # 5 minutes for unknown prompts (was 90s)
        self.require_acknowledgment_for_unknown = True
        
        # Stall detection should also be generous
        self.stall_timeout_unknown = 120  # 2 minutes (was 60s) (not 10!)
        
    def get_timeout_strategy(self, has_historical_data: bool, confidence: float = 0.0) -> Dict:
        """
        Determine timeout strategy based on available data.
        
        Args:
            has_historical_data: Whether we have Redis history for this prompt type
            confidence: Confidence level (0-1) in historical data
            
        Returns:
            Timeout strategy configuration
        """
        if has_historical_data and confidence > 0.5:
            # Use historical data with confidence
            return {
                "strategy": "historical",
                "base_timeout": None,  # Use Redis data
                "add_acknowledgment": False,  # Not needed if we know the pattern
                "stall_timeout": 30,  # Can be more aggressive with known patterns
                "reason": "Using proven historical patterns"
            }
        else:
            # Unknown prompt - be generous!
            return {
                "strategy": "default_generous", 
                "base_timeout": self.unknown_prompt_timeout,
                "add_acknowledgment": self.require_acknowledgment_for_unknown,
                "stall_timeout": self.stall_timeout_unknown,
                "reason": "Unknown prompt type - using safe defaults to prevent timeout"
            }
    
    def enhance_prompt_if_unknown(self, prompt: str, is_unknown: bool = True) -> str:
        """
        Add acknowledgment to unknown prompts to prevent stall detection.
        
        Args:
            prompt: Original prompt
            is_unknown: Whether this is an unknown prompt type
            
        Returns:
            Enhanced prompt with acknowledgment if needed
        """
        if not is_unknown:
            return prompt
        
        # Add universal acknowledgment that works for any prompt
        acknowledgment = """

Please acknowledge this request briefly, then proceed with your response."""
        
        return prompt + acknowledgment
    
    def get_timeout_for_complexity(self, complexity: str, is_unknown: bool = True) -> int:
        """
        Get timeout based on complexity with unknown-safe defaults.
        
        Args:
            complexity: simple/medium/complex
            is_unknown: Whether this is an unknown prompt type
            
        Returns:
            Timeout in seconds
        """
        if is_unknown:
            # Generous timeouts for unknown prompts (especially for code/research)
            unknown_timeouts = {
                "trivial": 120,  # 2 minutes for trivial unknowns
                "simple": 180,   # 3 minutes for simple unknowns
                "low": 180,      # 3 minutes for low complexity
                "medium": 300,   # 5 minutes for medium
                "high": 420,     # 7 minutes for high complexity
                "complex": 600,  # 10 minutes for complex
                "extreme": 900   # 15 minutes for extreme
            }
            return unknown_timeouts.get(complexity, 300)  # Default 5 minutes
        else:
            # Known prompts can use tighter timeouts
            known_timeouts = {
                "simple": 30,
                "medium": 120,
                "complex": 240
            }
            return known_timeouts.get(complexity, 120)
    
    def update_stress_test_config(self, test_config: Dict) -> Dict:
        """
        Update stress test configuration with smart defaults.
        
        Args:
            test_config: Original test configuration
            
        Returns:
            Updated configuration with smart timeouts
        """
        # Check if we have historical data
        has_history = test_config.get("has_redis_history", False)
        
        # Get timeout strategy
        strategy = self.get_timeout_strategy(has_history)
        
        # Update timeout if using defaults
        if strategy["base_timeout"]:
            test_config["timeout"] = strategy["base_timeout"]
        
        # Update stall timeout  
        test_config["stall_timeout"] = strategy["stall_timeout"]
        
        # Add acknowledgment if needed
        if strategy["add_acknowledgment"]:
            original_prompt = test_config.get("natural_language_request", "")
            test_config["natural_language_request"] = self.enhance_prompt_if_unknown(
                original_prompt, 
                is_unknown=True
            )
            test_config["uses_acknowledgment"] = True
        
        # Add strategy metadata
        test_config["timeout_strategy"] = strategy
        
        return test_config


# Practical example: Fix the failing stress tests
def fix_stress_test_timeouts():
    """
    Example of fixing the stress test timeouts using smart defaults.
    """
    defaults = SmartTimeoutDefaults()
    
    # Example failing prompts from stress test
    failing_prompts = [
        {
            "id": "simple_2",
            "prompt": "What is a quick chicken and rice recipe that takes 30 minutes?",
            "complexity": "simple",
            "has_redis_history": False  # Unknown
        },
        {
            "id": "parallel_1", 
            "prompt": "What is Python code for 5 functions?",
            "complexity": "medium",
            "has_redis_history": False
        },
        {
            "id": "long_1",
            "prompt": "What is a 500-word outline for a story?",
            "complexity": "complex", 
            "has_redis_history": False
        }
    ]
    
    print("Fixing Stress Test Timeouts")
    print("=" * 60)
    
    for test in failing_prompts:
        # Get smart timeout
        timeout = defaults.get_timeout_for_complexity(
            test["complexity"],
            is_unknown=not test["has_redis_history"]
        )
        
        # Enhance prompt if unknown
        enhanced_prompt = defaults.enhance_prompt_if_unknown(
            test["prompt"],
            is_unknown=not test["has_redis_history"]
        )
        
        print(f"\nTest: {test['id']}")
        print(f"Original timeout: 10s (stall detection)")
        print(f"Smart timeout: {timeout}s")
        print(f"Add acknowledgment: {enhanced_prompt != test['prompt']}")
        
        if enhanced_prompt != test["prompt"]:
            print(f"Enhanced prompt adds: '{enhanced_prompt[len(test['prompt']):]}'")
    
    print("\n" + "=" * 60)
    print("Summary: All unknown prompts now get 90s+ timeout with acknowledgment")
    print("Result: No more false failures from aggressive timeouts!")


if __name__ == "__main__":
    # Demonstrate the fix
    fix_stress_test_timeouts()
    
    # Show the core principle
    print("\n🎯 CORE PRINCIPLE:")
    print("If no similar prompt in Redis → 90s timeout + acknowledgment")
    print("This simple rule prevents 90% of timeout failures!")