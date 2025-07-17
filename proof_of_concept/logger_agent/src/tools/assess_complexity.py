#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "loguru",
#     "litellm",
#     "redis",
#     "google-auth",
#     "python-dotenv",
# ]
# ///
"""
assess_complexity.py - Analyze error complexity and recommend fix strategy

=== AGENT INSTRUCTIONS: HOW TO USE THIS TOOL ===

When you encounter an error during code execution:

1. Call AssessComplexity with the error details:
   AssessComplexity(
       error_type="ImportError",
       error_message="No module named 'pandas'", 
       file_path="src/data_processor.py",
       stack_trace="<full stack trace if available>",
       previous_attempts=0  # Increment if you've tried before
   )

2. The tool will return:
   {
       "complexity": "low",  # low/medium/high/critical
       "strategy": "self_fix",  # What to do next
       "action_summary": "Try fixing it yourself - this is a simple error",
       "specific_hints": ["Check import statements", ...],
       "example_query": "How to fix ImportError..."  # For research tools
   }

3. Follow the recommended strategy:
   - "self_fix" → Fix it yourself using Edit/Write tools
   - "perplexity_research" → Use mcp__perplexity-ask__perplexity_ask
   - "fresh_claude_cc_execute" → Use cc_execute for clean context
   - "gemini_flash" → Use litellm with Gemini for comprehensive fix
   - "human_review" → Ask the user for architectural guidance

4. If the fix fails, call AssessComplexity again with previous_attempts+=1
   The tool will escalate to more powerful strategies.

IMPORTANT: Always use this tool BEFORE attempting fixes to avoid wasting time!

=== TESTING (for development only) ===
  python assess_complexity.py          # Runs working_usage()
  python assess_complexity.py debug    # Tests various error patterns
"""

import json
import sys
from typing import Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, asdict


class Complexity(Enum):
    """Error complexity levels"""
    LOW = "low"          # Import/syntax errors
    MEDIUM = "medium"    # Logic errors, async issues
    HIGH = "high"        # Multi-file, complex dependencies
    CRITICAL = "critical"  # Architectural, design flaws


class FixStrategy(Enum):
    """Recommended fix strategies"""
    SELF_FIX = "self_fix"
    PERPLEXITY_RESEARCH = "perplexity_research"
    FRESH_CLAUDE = "fresh_claude_cc_execute"
    GEMINI_FLASH = "gemini_flash"
    HUMAN_REVIEW = "human_review"


@dataclass
class ComplexityAssessment:
    """Result of complexity assessment"""
    complexity: Complexity
    strategy: FixStrategy
    confidence: float  # 0.0 to 1.0
    reasoning: str
    specific_hints: list[str]
    example_query: Optional[str] = None


def assess_error_complexity(
    error_type: str,
    error_message: str,
    file_path: str,
    stack_trace: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> ComplexityAssessment:
    """
    Assess the complexity of an error and recommend a fix strategy.
    
    Args:
        error_type: Type of error (ImportError, SyntaxError, etc.)
        error_message: The error message
        file_path: Path to the file with the error
        stack_trace: Optional full stack trace
        context: Optional additional context (dependencies, related files, etc.)
    
    Returns:
        ComplexityAssessment with recommendation
    """
    
    error_lower = error_message.lower()
    error_type_lower = error_type.lower()
    
    # Low complexity patterns
    if any(pattern in error_type_lower for pattern in ["import", "module", "syntax", "indent", "name"]):
        return ComplexityAssessment(
            complexity=Complexity.LOW,
            strategy=FixStrategy.SELF_FIX,
            confidence=0.9,
            reasoning="Simple import or syntax error - can be fixed directly",
            specific_hints=[
                "Check import statements",
                "Verify module is installed",
                "Check for typos in variable/function names"
            ]
        )
    
    # Medium complexity patterns - need research
    if any(pattern in error_lower for pattern in ["async", "await", "coroutine", "timeout", "connection"]):
        return ComplexityAssessment(
            complexity=Complexity.MEDIUM,
            strategy=FixStrategy.PERPLEXITY_RESEARCH,
            confidence=0.8,
            reasoning="Async/await or connection issue - research best practices",
            specific_hints=[
                "Search for Python async patterns",
                "Check for missing await keywords",
                "Look for timeout configuration options"
            ],
            example_query=f"Python best practice fix for: {error_message[:100]}"
        )
    
    # High complexity - multi-file or deep stack trace
    if stack_trace and stack_trace.count('\n') > 10:
        # Deep stack trace suggests complex issue
        return ComplexityAssessment(
            complexity=Complexity.HIGH,
            strategy=FixStrategy.FRESH_CLAUDE,
            confidence=0.7,
            reasoning="Deep stack trace indicates complex issue - fresh context needed",
            specific_hints=[
                "Use cc_execute for clean context",
                "Include all related files in context",
                "Focus on the root cause, not symptoms"
            ],
            example_query=f"Fix complex Python error in {file_path}"
        )
    
    # Critical - architectural issues
    if any(pattern in error_lower for pattern in ["circular", "dependency", "architecture", "design"]):
        return ComplexityAssessment(
            complexity=Complexity.CRITICAL,
            strategy=FixStrategy.GEMINI_FLASH,
            confidence=0.6,
            reasoning="Architectural issue requires comprehensive analysis",
            specific_hints=[
                "Use Gemini with full project context",
                "Consider refactoring approach",
                "May need human review for design decisions"
            ]
        )
    
    # Runtime errors that might need Gemini
    if any(pattern in error_type_lower for pattern in ["runtime", "type", "attribute", "key"]):
        if context and context.get("previous_attempts", 0) > 1:
            # Multiple failed attempts, escalate to Gemini
            return ComplexityAssessment(
                complexity=Complexity.HIGH,
                strategy=FixStrategy.GEMINI_FLASH,
                confidence=0.7,
                reasoning="Multiple attempts failed - need comprehensive fix",
                specific_hints=[
                    "Include all previous attempts in context",
                    "Ask for complete solution with error handling",
                    "Request explanation of root cause"
                ]
            )
        else:
            # First attempt, try fresh Claude
            return ComplexityAssessment(
                complexity=Complexity.MEDIUM,
                strategy=FixStrategy.FRESH_CLAUDE,
                confidence=0.8,
                reasoning="Runtime error - try fresh perspective first",
                specific_hints=[
                    "Use cc_execute for clean analysis",
                    "Focus on the specific error line",
                    "Check data types and None values"
                ]
            )
    
    # Default case - when unsure
    return ComplexityAssessment(
        complexity=Complexity.MEDIUM,
        strategy=FixStrategy.PERPLEXITY_RESEARCH,
        confidence=0.5,
        reasoning="Unknown error pattern - research for best approach",
        specific_hints=[
            "Search for similar error patterns",
            "Check documentation for the library/framework",
            "Look for community solutions"
        ],
        example_query=f"How to fix: {error_type} - {error_message[:100]}"
    )


def tool(name=None, description=None):
    """Decorator for tool registration"""
    def decorator(func):
        func._tool_name = name or func.__name__
        func._tool_description = description
        return func
    return decorator


@tool(
    name="AssessComplexity",
    description="Analyze error complexity and get fix strategy recommendation"
)
def main(
    error_type: str,
    error_message: str,
    file_path: str,
    stack_trace: Optional[str] = None,
    previous_attempts: int = 0,
    related_files: Optional[list[str]] = None
) -> Dict[str, Any]:
    """
    Main entry point when called as a tool.
    
    Returns a JSON response with:
    - complexity: low/medium/high/critical
    - strategy: self_fix/perplexity_research/fresh_claude_cc_execute/gemini_flash
    - confidence: 0.0-1.0
    - reasoning: Why this strategy was chosen
    - specific_hints: Actionable steps for the agent
    - example_query: Example query for research tools (if applicable)
    """
    
    context = {
        "previous_attempts": previous_attempts,
        "related_files": related_files or []
    }
    
    assessment = assess_error_complexity(
        error_type=error_type,
        error_message=error_message,
        file_path=file_path,
        stack_trace=stack_trace,
        context=context
    )
    
    return {
        "complexity": assessment.complexity.value,
        "strategy": assessment.strategy.value,
        "confidence": assessment.confidence,
        "reasoning": assessment.reasoning,
        "specific_hints": assessment.specific_hints,
        "example_query": assessment.example_query,
        "action_summary": _get_action_summary(assessment)
    }


def _get_action_summary(assessment: ComplexityAssessment) -> str:
    """Get a one-line action summary for the agent"""
    summaries = {
        FixStrategy.SELF_FIX: "Try fixing it yourself - this is a simple error",
        FixStrategy.PERPLEXITY_RESEARCH: "Use perplexity-ask to research the solution",
        FixStrategy.FRESH_CLAUDE: "Use cc_execute for a fresh Claude perspective",
        FixStrategy.GEMINI_FLASH: "Use Gemini Flash with full context for comprehensive fix",
        FixStrategy.HUMAN_REVIEW: "This requires human review and architectural decisions"
    }
    return summaries.get(assessment.strategy, "Unknown strategy")


async def working_usage():
    """Demonstrate proper usage of the complexity assessment tool"""
    print("=== Testing Complexity Assessment Tool ===\n")
    
    # Test case: Import error (LOW complexity)
    result = main(
        error_type="ImportError",
        error_message="No module named 'requests'",
        file_path="src/utils/api_client.py"
    )
    
    print("Test Case: Import Error")
    print(f"Complexity: {result['complexity']}")
    print(f"Strategy: {result['strategy']}")
    print(f"Action: {result['action_summary']}")
    print(f"Confidence: {result['confidence']}")
    print()
    
    return True


async def debug_function():
    """Test various error patterns and edge cases"""
    print("=== Debug Mode: Testing Various Error Patterns ===\n")
    
    test_cases = [
        {
            "name": "Simple Import Error",
            "error_type": "ImportError",
            "error_message": "No module named 'pandas'",
            "file_path": "data_processor.py"
        },
        {
            "name": "Async Timeout Issue",
            "error_type": "asyncio.TimeoutError",
            "error_message": "Timeout context manager should be used inside a task",
            "file_path": "async_handler.py",
            "stack_trace": "File async_handler.py line 45\n  await something()"
        },
        {
            "name": "Complex Multi-file Error",
            "error_type": "RuntimeError",
            "error_message": "Circular dependency detected",
            "file_path": "core/engine.py",
            "stack_trace": "\n".join([f"File {i}.py line {i*10}" for i in range(15)]),
            "previous_attempts": 2
        },
        {
            "name": "After Multiple Attempts",
            "error_type": "AttributeError",
            "error_message": "'NoneType' object has no attribute 'process'",
            "file_path": "processor.py",
            "previous_attempts": 3
        }
    ]
    
    for test in test_cases:
        name = test.pop("name")
        print(f"{'='*60}")
        print(f"Test: {name}")
        print(f"{'='*60}")
        
        result = main(**test)
        
        print(f"Complexity: {result['complexity'].upper()}")
        print(f"Strategy: {result['strategy']}")
        print(f"Action: {result['action_summary']}")
        print(f"Reasoning: {result['reasoning']}")
        print(f"Confidence: {result['confidence']:.1%}")
        
        if result.get('example_query'):
            print(f"Example Query: {result['example_query']}")
        
        print("\nHints:")
        for hint in result['specific_hints']:
            print(f"  - {hint}")
        print()
    
    return True


if __name__ == "__main__":
    import asyncio
    
    # Check if called with JSON input (as a tool)
    if len(sys.argv) > 1 and sys.argv[1].startswith('{'):
        input_data = json.loads(sys.argv[1])
        result = main(**input_data)
        print(json.dumps(result, indent=2))
    else:
        # Run test modes
        mode = sys.argv[1] if len(sys.argv) > 1 else "working"
        
        if mode == "debug":
            print("Running in DEBUG mode...")
            asyncio.run(debug_function())
        else:
            print("Running in WORKING mode...")
            asyncio.run(working_usage())