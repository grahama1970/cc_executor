"""
Claude CLI Tool Limitations - Workaround Examples

This file demonstrates how to work around the fact that Claude CLI
instances don't have access to Task, Todo, or other web-only tools.
"""

import asyncio
from cc_executor.client.cc_execute import cc_execute


async def task_tool_workaround():
    """Shows how to work around missing Task tool."""
    
    # ❌ WRONG - This will fail (Task tool not available)
    # result = await cc_execute(
    #     "Use the Task tool to break down building a web scraper",
    #     json_mode=True
    # )
    
    # ✅ CORRECT - Ask for the breakdown directly
    result = await cc_execute(
        "What are the implementation steps for building a web scraper? "
        "Return JSON with 'steps' array containing task descriptions.",
        json_mode=True
    )
    
    print("Task breakdown:")
    for i, step in enumerate(result.get('steps', []), 1):
        print(f"{i}. {step}")
    
    return result


async def todo_tool_workaround():
    """Shows how to work around missing TodoRead/TodoWrite tools."""
    
    # ❌ WRONG - These will fail
    # await cc_execute("Add 'implement auth' to the todo list")
    # await cc_execute("Read my todo list")
    
    # ✅ CORRECT - Manage todos externally
    todos = []  # Orchestrator manages the list
    
    # Get tasks from Claude
    result = await cc_execute(
        "What are the todos for implementing a REST API? "
        "Return JSON with 'todos' array.",
        json_mode=True
    )
    
    # Orchestrator manages the todo list
    todos.extend(result.get('todos', []))
    print(f"Todo list now has {len(todos)} items")
    
    return todos


async def interactive_workaround():
    """Shows how to handle lack of interactive features."""
    
    # ❌ WRONG - Assumes interactive capability
    # await cc_execute("Guide me through setting up Docker")
    
    # ✅ CORRECT - Get complete information upfront
    result = await cc_execute(
        "What is a complete Docker setup guide for a Python web app? "
        "Include all steps, commands, and configuration files.",
        json_mode=True
    )
    
    print("Docker Setup Guide:")
    print(result.get('result', 'No guide generated'))
    
    return result


async def image_analysis_workaround():
    """Shows how to handle lack of image upload."""
    
    # ❌ WRONG - Can't upload images via CLI
    # await cc_execute("Analyze this screenshot: [drag & drop]")
    
    # ✅ CORRECT - Describe what you need analyzed
    result = await cc_execute(
        "What should I look for when reviewing a web app's mobile responsiveness? "
        "Provide a checklist.",
        json_mode=True
    )
    
    # Or, if you have an image locally, describe it
    result2 = await cc_execute(
        "Given a web page with a navigation bar at top (logo left, menu right), "
        "content area with 3 columns on desktop, and footer with 4 sections, "
        "what responsive design improvements would you suggest?",
        json_mode=True
    )
    
    return result2


async def command_vs_question_pattern():
    """Critical pattern: Always use questions, not commands."""
    
    # ❌ Commands that timeout or fail
    bad_examples = [
        "Write a Python function to calculate factorial",
        "Create a web scraper",
        "Implement a sorting algorithm",
        "Build a REST API"
    ]
    
    # ✅ Questions that work reliably
    good_examples = [
        "What is a Python function that calculates factorial?",
        "What is a Python web scraper example?",
        "What is a sorting algorithm implementation?",
        "What is a REST API architecture?"
    ]
    
    # Demonstrate the difference
    print("Testing question format (reliable)...")
    result = await cc_execute(
        "What is a Python function that validates email addresses?",
        json_mode=True
    )
    print(f"✅ Success: Got {len(result.get('result', ''))} chars")
    
    return result


async def mcp_tools_available():
    """Shows that MCP tools ARE available in Claude CLI."""
    
    # ✅ MCP tools work fine - cc_executor auto-configures them
    print("Testing MCP tool availability...")
    
    # Example 1: Using perplexity-ask for research
    result1 = await cc_execute(
        "Use perplexity-ask to research: What are the best practices for Redis caching in 2024? "
        "Return a summary of the findings.",
        json_mode=True
    )
    print("✅ perplexity-ask worked")
    
    # Example 2: Using ripgrep for code search
    result2 = await cc_execute(
        "Use ripgrep to find all Python files containing 'async def' in this project. "
        "What are the main async functions?",
        json_mode=True
    )
    print("✅ ripgrep worked")
    
    # Example 3: GitHub operations
    result3 = await cc_execute(
        "Use the github MCP tool to search for repositories about 'fastapi redis cache'. "
        "What are the top 3 most starred repos?",
        json_mode=True  
    )
    print("✅ github tool worked")
    
    return {
        "perplexity_result": result1,
        "ripgrep_result": result2,
        "github_result": result3
    }


# Summary of workarounds
WORKAROUND_GUIDE = """
CLAUDE CLI LIMITATIONS - QUICK REFERENCE

Missing Tool -> Workaround:

1. Task tool -> Ask "What are the steps to..."
2. TodoRead/Write -> Manage list in orchestrator
3. Interactive guides -> Ask for complete guide upfront  
4. Image upload -> Describe the image content
5. File download UI -> Use file operations directly
6. Rich formatting -> Work with raw text
7. Session management -> Each call is independent

BUT YOU DO HAVE MCP TOOLS:
- perplexity-ask -> Web search and research
- github -> GitHub operations
- ripgrep -> Fast file search
- brave-search -> Web and local search
- puppeteer -> Web automation
- Any custom MCP tools in .mcp.json

GOLDEN RULES:
- Always phrase as questions, not commands
- Don't assume any web UI tools exist
- Manage state in the orchestrator, not Claude
- MCP tools ARE available (cc_executor auto-configures)
- Test prompts with: timeout 180 claude -p "prompt"
"""


if __name__ == "__main__":
    print(WORKAROUND_GUIDE)
    
    # Run examples
    asyncio.run(task_tool_workaround())