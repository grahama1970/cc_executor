#!/usr/bin/env python3
"""Test prompt amendment features."""
import asyncio
from executor import cc_execute, CCExecutorConfig

async def test_amendment_examples():
    """Test various prompt amendment scenarios."""
    
    test_cases = [
        # Ambiguous prompts (should fail)
        ("fix the bug", True, "Should detect as ambiguous"),
        ("make it better", True, "Should detect vague requirements"),
        ("explain this", True, "Should detect missing context"),
        
        # Command transformations (should amend)
        ("Write a Python function to calculate factorial", False, "Should convert to question"),
        ("Create a web scraper for news sites", False, "Should convert to question"),
        ("Generate 10 random passwords", False, "Should convert to question"),
        
        # Multi-task decomposition (should extract first task)
        ("Create a web scraper that fetches articles and stores them in a database", False, "Should decompose"),
        ("Build a REST API with authentication and write tests for it", False, "Should decompose"),
        
        # Already good prompts (no change)
        ("What is the capital of France?", False, "Already in question format"),
        ("What is a Python function that sorts a list?", False, "Already well-formed"),
    ]
    
    print("PROMPT AMENDMENT TEST")
    print("="*80)
    
    for prompt, expect_error, description in test_cases:
        print(f"\nTesting: {prompt[:60]}...")
        print(f"Expectation: {description}")
        
        try:
            # Use cc_execute with amendment
            result = await cc_execute(
                prompt,
                config=CCExecutorConfig(timeout=60),
                stream=False,
                amend_prompt=True,  # Enable amendment
                return_json=False
            )
            
            if expect_error:
                print("❌ ERROR: Expected ambiguity detection but succeeded!")
            else:
                print("✅ SUCCESS: Prompt was amended/executed successfully")
                print(f"   Result preview: {result[:100]}...")
                
        except ValueError as e:
            if expect_error and "Ambiguous prompt" in str(e):
                print(f"✅ SUCCESS: Correctly detected ambiguity - {e}")
            else:
                print(f"❌ ERROR: Unexpected error - {e}")
        except Exception as e:
            print(f"❌ ERROR: Unexpected exception - {type(e).__name__}: {e}")

async def test_manual_amendment():
    """Test the amendment process directly."""
    from prompt_amender import apply_basic_rules, amend_prompt
    
    print("\n\nMANUAL AMENDMENT TEST")
    print("="*80)
    
    # Test basic rules
    print("\n1. Testing basic rule application:")
    test_prompts = [
        "Write a sorting algorithm",
        "Create a TODO app",
        "What is machine learning?",
        "fix the bug",  # Should raise error
    ]
    
    for prompt in test_prompts:
        try:
            amended = apply_basic_rules(prompt)
            print(f"✅ '{prompt}' → '{amended}'")
        except ValueError as e:
            print(f"🚫 '{prompt}' → Rejected: {e}")
    
    # Test Claude-powered amendment
    print("\n2. Testing Claude-powered amendment:")
    complex_prompt = "Build a web application with user authentication, database integration, and email notifications"
    
    # Mock cc_execute for testing
    async def mock_cc_execute(task, **kwargs):
        # Simulate Claude's response
        return {
            "original_prompt": complex_prompt,
            "amended_prompt": "What is the architecture for a web application with user authentication?",
            "changes_made": [
                "Converted 'Build' to 'What is the architecture for'",
                "Decomposed multi-task prompt",
                "Extracted first atomic task (authentication)"
            ],
            "risk_assessment": "low",
            "explanation": "Focused on single architectural component to avoid timeout",
            "is_ambiguous": False,
            "decomposed_tasks": [
                "What is the architecture for a web application with user authentication?",
                "What is a database schema for user management?",
                "What is a Python implementation for email notifications?"
            ]
        }
    
    try:
        amended, explanation = await amend_prompt(complex_prompt, mock_cc_execute)
        print(f"✅ Original: {complex_prompt}")
        print(f"   Amended: {amended}")
        print(f"   Reason: {explanation}")
    except Exception as e:
        print(f"❌ Amendment failed: {e}")

if __name__ == "__main__":
    print("Testing CC_EXECUTE Prompt Amendment Features")
    print("This demonstrates ambiguity detection and prompt transformation")
    print("")
    
    # Run tests
    asyncio.run(test_amendment_examples())
    asyncio.run(test_manual_amendment())