#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"  
# dependencies = [
#     "networkx",
#     "tree-sitter",
#     "tree-sitter-language-pack",
#     "loguru",
#     "python-arango",
# ]
# ///
"""
assess_complexity_v2.py - Enhanced complexity assessment with logger integration

This version integrates with the Logger Agent to:
1. Search for similar errors and their resolutions
2. Log assessment results for future reference
3. Track successful fixes
4. Build a knowledge base of error patterns

=== AGENT INSTRUCTIONS FOR THIS FILE ===
Run this script directly to test functionality:
  python assess_complexity_v2.py          # Runs working_usage() - stable, known to work
  python assess_complexity_v2.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug_function() instead!
The working_usage() function MUST pass all assertions to verify the script works.
===
"""

import json
import sys
import os
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
import networkx as nx
import ast
from loguru import logger
from datetime import datetime
import asyncio

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")


# Import logger agent components
try:
    from agent_log_manager import get_log_manager
    LOGGER_AVAILABLE = True
except ImportError:
    logger.warning("Logger agent not available - running in standalone mode")
    LOGGER_AVAILABLE = False

# Import tree_sitter_utils
from cc_executor.utils.tree_sitter_utils import parse_python_code


# Error-specific analysis strategies
ERROR_STRATEGIES = {
    'ModuleNotFoundError': {
        'focus': ['import_paths', 'project_structure', 'available_modules'],
        'skip': ['call_graph', 'coupling_metrics'],
        'analyzer': 'analyze_import_error'
    },
    'TypeError': {
        'focus': ['variable_types', 'method_signatures', 'type_conversions'],
        'skip': ['import_analysis'],
        'analyzer': 'analyze_type_error'
    },
    'AttributeError': {
        'focus': ['class_definitions', 'method_availability', 'inheritance'],
        'skip': ['import_analysis'],
        'analyzer': 'analyze_attribute_error'
    },
    'NameError': {
        'focus': ['variable_scope', 'definition_order', 'imports'],
        'skip': ['call_graph'],
        'analyzer': 'analyze_name_error'
    },
    'SyntaxError': {
        'focus': ['line_context', 'indentation', 'brackets'],
        'skip': ['call_graph', 'import_analysis'],
        'analyzer': 'analyze_syntax_error'
    }
}


async def search_similar_errors(
    error_type: str,
    error_message: str,
    file_path: str,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """Search for similar errors in the logger database."""
    if not LOGGER_AVAILABLE:
        return []
    
    try:
        manager = await get_log_manager()
        
        # Search for similar errors
        search_query = f"{error_type} {error_message}"
        results = await manager.search.search_agent_activity(
            query=search_query,
            filters={
                "event_types": ["error", "fix", "resolution"],
                "time_range": "30d"  # Look back 30 days
            },
            limit=limit
        )
        
        # Also search for specific error patterns
        error_patterns = await manager.search.find_error_patterns(
            time_range="30d",
            min_occurrences=1
        )
        
        # Filter for relevant patterns
        relevant_patterns = [
            p for p in error_patterns 
            if p.get('error_type') == error_type or error_message in p.get('pattern', '')
        ]
        
        return {
            "similar_errors": results,
            "error_patterns": relevant_patterns
        }
        
    except Exception as e:
        logger.error(f"Failed to search similar errors: {e}")
        return {"similar_errors": [], "error_patterns": []}


async def log_assessment_result(
    error_type: str,
    error_message: str,
    file_path: str,
    assessment_result: Dict[str, Any],
    execution_id: str
) -> Optional[str]:
    """Log the assessment result for future reference."""
    if not LOGGER_AVAILABLE:
        return None
    
    try:
        manager = await get_log_manager()
        
        # Log the assessment
        log_result = await manager.log_event(
            level="INFO",
            message=f"Assessed {error_type}: {error_message}",
            script_name="assess_complexity",
            execution_id=execution_id,
            extra_data={
                "assessment_type": "error_analysis",
                "error_type": error_type,
                "error_message": error_message,
                "file_path": file_path,
                "complexity_indicators": assessment_result.get("complexity_indicators", []),
                "confidence": assessment_result.get("confidence", "MEDIUM"),
                "recommended_tools": assessment_result.get("recommended_tools", [])
            },
            tags=["assessment", "error-analysis", error_type.lower()]
        )
        
        # Store as a memory for learning
        memory_result = await manager.memory.add_memory(
            content=f"Analyzed {error_type} in {Path(file_path).name}: {assessment_result.get('summary', '')}",
            memory_type="error_pattern",
            metadata={
                "error_type": error_type,
                "file_path": file_path,
                "complexity": assessment_result.get("complexity_indicators", []),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        return log_result.get("_id")
        
    except Exception as e:
        logger.error(f"Failed to log assessment: {e}")
        return None


async def log_successful_fix(
    error_type: str,
    error_message: str,
    file_path: str,
    fix_description: str,
    execution_id: str,
    original_assessment_id: Optional[str] = None
) -> Optional[str]:
    """Log a successful fix for future reference."""
    if not LOGGER_AVAILABLE:
        return None
    
    try:
        manager = await get_log_manager()
        
        # Log the successful fix
        fix_result = await manager.log_event(
            level="SUCCESS",
            message=f"Fixed {error_type}: {fix_description}",
            script_name="assess_complexity",
            execution_id=execution_id,
            extra_data={
                "fix_type": "error_resolution",
                "error_type": error_type,
                "original_error": error_message,
                "file_path": file_path,
                "fix_description": fix_description,
                "original_assessment_id": original_assessment_id
            },
            tags=["fix", "resolution", error_type.lower(), "success"]
        )
        
        # Store as a learning
        learning_result = await manager.memory.add_memory(
            content=f"Fix for {error_type}: {fix_description}",
            memory_type="learning",
            metadata={
                "error_type": error_type,
                "fix_description": fix_description,
                "file_path": file_path,
                "confidence": 0.9,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Create relationship between error and fix if we have the original assessment
        if original_assessment_id:
            await manager.relationships.extract_relationships(
                text1=f"Error: {error_message}",
                text2=f"Fix: {fix_description}",
                context={
                    "error_id": original_assessment_id,
                    "fix_id": fix_result.get("_id"),
                    "execution_id": execution_id
                }
            )
        
        return fix_result.get("_id")
        
    except Exception as e:
        logger.error(f"Failed to log successful fix: {e}")
        return None


async def analyze_with_tree_sitter(file_content: str, file_path: str) -> Dict[str, Any]:
    """Analyze code structure using tree-sitter."""
    try:
        analysis = parse_python_code(file_content)
        
        # Extract relevant metrics
        return {
            "function_count": len(analysis.get("functions", [])),
            "class_count": len(analysis.get("classes", [])),
            "import_count": len(analysis.get("imports", [])),
            "imports": analysis.get("imports", []),
            "functions": [f["name"] for f in analysis.get("functions", [])],
            "classes": [c["name"] for c in analysis.get("classes", [])],
            "has_main_block": analysis.get("has_main_block", False),
            "docstring": analysis.get("docstring", None),
            "circular_imports": False  # Would need multi-file analysis
        }
    except Exception as e:
        logger.error(f"Tree-sitter analysis failed: {e}")
        return {
            "error": str(e),
            "function_count": 0,
            "class_count": 0,
            "import_count": 0
        }


async def assess_complexity(
    error_type: str,
    error_message: str, 
    file_path: str,
    stack_trace: Optional[str] = None,
    previous_attempts: int = 0
) -> str:
    """
    Generate a comprehensive prompt analyzing the error with context-specific strategies.
    Now includes logger integration for finding similar errors and logging results.
    """
    execution_id = f"assess_{datetime.utcnow().timestamp()}"
    
    # Search for similar errors and resolutions
    similar_errors = await search_similar_errors(
        error_type, error_message, file_path
    )
    
    # Read file content
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
    except Exception as e:
        file_content = f"[Unable to read file: {e}]"
    
    # Get error-specific strategy
    strategy = ERROR_STRATEGIES.get(error_type, {
        'focus': ['general_analysis'],
        'skip': [],
        'analyzer': None
    })
    
    # Build the assessment
    assessment_result = {
        "complexity_indicators": [],
        "confidence": "MEDIUM",
        "recommended_tools": [],
        "summary": ""
    }
    
    # Start building the prompt
    prompt = f"""# Error Complexity Assessment

## Error Details
- **Type**: {error_type}
- **Message**: {error_message}
- **File**: {file_path}
- **Previous Attempts**: {previous_attempts}
"""
    
    # Add similar errors section if found
    if similar_errors.get("similar_errors"):
        prompt += "\n## 🔍 Similar Errors Found in History\n"
        for i, err in enumerate(similar_errors["similar_errors"][:3], 1):
            doc = err.get("doc", {})
            prompt += f"\n### {i}. {doc.get('message', 'No message')}\n"
            if doc.get('extra_data', {}).get('fix_description'):
                prompt += f"- **Fix**: {doc['extra_data']['fix_description']}\n"
            prompt += f"- **Score**: {err.get('score', 0):.2f}\n"
    
    # Add error patterns if found
    if similar_errors.get("error_patterns"):
        prompt += "\n## 📊 Error Patterns Detected\n"
        for pattern in similar_errors["error_patterns"][:2]:
            prompt += f"\n### Pattern: {pattern.get('pattern', 'Unknown')}\n"
            prompt += f"- **Count**: {pattern.get('count', 0)} occurrences\n"
            if pattern.get('resolutions'):
                prompt += f"- **Common Fix**: {pattern['resolutions'][0].get('description', 'N/A')}\n"
    
    # Add stack trace
    if stack_trace:
        prompt += f"\n## Stack Trace\n```\n{stack_trace}\n```\n"
    
    # Tree-sitter analysis
    tree_analysis = await analyze_with_tree_sitter(file_content, file_path)
    
    # Error-specific analysis
    if strategy['analyzer'] == 'analyze_import_error':
        error_analysis = await analyze_import_error(
            Path(file_path), error_message, Path(file_path).parent
        )
        prompt += "\n## Import Error Analysis\n"
        prompt += f"- **Missing Module**: {error_analysis.get('missing_module', 'Unknown')}\n"
        if error_analysis.get('available_modules'):
            prompt += f"- **Available Modules**: {', '.join(error_analysis['available_modules'][:10])}\n"
        if error_analysis.get('possible_fixes'):
            prompt += "\n### Suggested Fixes:\n"
            for fix in error_analysis['possible_fixes']:
                prompt += f"- {fix}\n"
    
    # Add tree-sitter metrics
    prompt += "\n## Code Structure Analysis\n"
    prompt += f"- **Functions**: {tree_analysis.get('function_count', 0)}\n"
    prompt += f"- **Classes**: {tree_analysis.get('class_count', 0)}\n"
    prompt += f"- **Imports**: {tree_analysis.get('import_count', 0)}\n"
    
    # Complexity assessment
    if tree_analysis.get('function_count', 0) > 20:
        assessment_result["complexity_indicators"].append("large_file")
    
    if tree_analysis.get('circular_imports'):
        assessment_result["complexity_indicators"].append("circular_deps")
    
    # Confidence assessment
    if similar_errors.get("similar_errors") and len(similar_errors["similar_errors"]) > 0:
        assessment_result["confidence"] = "HIGH"
        prompt += "\n## ✅ High Confidence - Similar errors have been fixed before\n"
    elif error_type == "SyntaxError":
        assessment_result["confidence"] = "HIGH"
    elif "circular" in str(assessment_result["complexity_indicators"]):
        assessment_result["confidence"] = "LOW"
    
    # Tool recommendations
    prompt += "\n## Recommended Approach\n"
    
    if assessment_result["confidence"] == "HIGH" and similar_errors.get("similar_errors"):
        prompt += "- **Self-fix** with reference to previous solutions\n"
        assessment_result["recommended_tools"].append("self-fix")
    elif assessment_result["complexity_indicators"]:
        prompt += "- **send_to_gemini** for architectural analysis\n"
        assessment_result["recommended_tools"].append("send_to_gemini")
    else:
        prompt += "- **perplexity-ask** for best practices\n"
        assessment_result["recommended_tools"].append("perplexity-ask")
    
    # Log the assessment
    assessment_id = await log_assessment_result(
        error_type, error_message, file_path, 
        assessment_result, execution_id
    )
    
    if assessment_id:
        prompt += f"\n## Assessment ID: {assessment_id}\n"
        prompt += "Use this ID when logging the fix to create a knowledge link.\n"
    
    return prompt


async def analyze_import_error(
    file_path: Path, 
    error_message: str,
    project_root: Path
) -> Dict[str, Any]:
    """Specialized analysis for import errors."""
    missing_module = "unknown"
    
    # Extract module name from error
    if "No module named" in error_message:
        parts = error_message.split("'")
        if len(parts) >= 2:
            missing_module = parts[1]
    
    # Check available modules
    available_modules = []
    
    # Check standard library
    import sys
    stdlib_modules = set(sys.stdlib_module_names) if hasattr(sys, 'stdlib_module_names') else set()
    
    # Check installed packages
    try:
        import pkg_resources
        installed_packages = [d.project_name for d in pkg_resources.working_set]
        available_modules.extend(installed_packages)
    except:
        pass
    
    # Suggest fixes
    possible_fixes = []
    
    if missing_module in stdlib_modules:
        possible_fixes.append(f"'{missing_module}' is in stdlib - check Python version")
    elif missing_module in available_modules:
        possible_fixes.append(f"'{missing_module}' is installed - check sys.path")
    else:
        possible_fixes.append(f"Install '{missing_module}' with: uv add {missing_module}")
    
    # Check if it's a local module
    local_modules = []
    for py_file in project_root.rglob("*.py"):
        if "__pycache__" not in str(py_file):
            module_name = py_file.stem
            if module_name == missing_module:
                relative_path = py_file.relative_to(project_root)
                possible_fixes.append(f"Found '{module_name}' at {relative_path} - add parent to sys.path")
    
    return {
        "missing_module": missing_module,
        "available_modules": available_modules[:20],  # Limit output
        "possible_fixes": possible_fixes,
        "local_modules": local_modules
    }


# Example usage functions
async def working_usage():
    """
    Demonstrate the enhanced assess_complexity with logger integration.
    
    This example shows:
    1. Searching for similar errors
    2. Logging assessment results
    3. Logging successful fixes
    4. Building a searchable knowledge base
    """
    logger.info("=== Testing Enhanced Assess Complexity ===")
    
    # Create a test file with an error
    test_file = Path("/tmp/test_error.py")
    test_file.write_text("""
import non_existent_module
from utils import helper

def main():
    print("This will fail")
""")
    
    # Test 1: Assess an import error
    logger.info("\nTest 1: Assessing import error...")
    
    result = await assess_complexity(
        error_type="ModuleNotFoundError",
        error_message="No module named 'non_existent_module'",
        file_path=str(test_file),
        stack_trace="File test_error.py, line 2, in <module>\n    import non_existent_module"
    )
    
    logger.info("Assessment generated successfully")
    logger.info(f"Result preview: {result[:200]}...")
    
    # Extract assessment ID if available
    assessment_id = None
    if "Assessment ID:" in result:
        assessment_id = result.split("Assessment ID:")[1].split("\n")[0].strip()
        logger.info(f"Assessment logged with ID: {assessment_id}")
    
    # Test 2: Log a successful fix
    logger.info("\nTest 2: Logging successful fix...")
    
    fix_id = await log_successful_fix(
        error_type="ModuleNotFoundError",
        error_message="No module named 'non_existent_module'",
        file_path=str(test_file),
        fix_description="Removed unused import 'non_existent_module'",
        execution_id=f"test_{datetime.utcnow().timestamp()}",
        original_assessment_id=assessment_id
    )
    
    if fix_id:
        logger.success(f"✓ Fix logged with ID: {fix_id}")
    
    # Test 3: Search for the logged fix
    logger.info("\nTest 3: Searching for logged fixes...")
    
    if LOGGER_AVAILABLE:
        similar = await search_similar_errors(
            "ModuleNotFoundError",
            "non_existent_module",
            str(test_file)
        )
        
        if similar.get("similar_errors"):
            logger.info(f"Found {len(similar['similar_errors'])} similar errors")
    
    # Clean up
    test_file.unlink()
    
    logger.success("\n✅ All tests completed!")
    return True


async def debug_function():
    """
    Debug function for testing logger integration edge cases.
    """
    logger.info("=== Debug Mode: Testing Edge Cases ===")
    
    # Test with various error types
    error_types = [
        ("TypeError", "unsupported operand type(s) for +: 'int' and 'str'"),
        ("AttributeError", "'NoneType' object has no attribute 'split'"),
        ("NameError", "name 'undefined_var' is not defined"),
        ("SyntaxError", "invalid syntax")
    ]
    
    test_file = Path("/tmp/debug_test.py")
    test_file.write_text("# Debug test file")
    
    for error_type, error_msg in error_types:
        logger.info(f"\nTesting {error_type}...")
        
        result = await assess_complexity(
            error_type=error_type,
            error_message=error_msg,
            file_path=str(test_file),
            previous_attempts=1
        )
        
        # Check if similar errors were found
        if "Similar Errors Found" in result:
            logger.info("✓ Found similar errors in history")
        
        # Check if patterns were detected
        if "Error Patterns Detected" in result:
            logger.info("✓ Detected error patterns")
    
    test_file.unlink()
    return True


if __name__ == "__main__":
    """
    AGENT INSTRUCTIONS:
    - DEFAULT: Runs working_usage() - stable example that works
    - DEBUG: Run with 'debug' argument to test new ideas
    - DO NOT create external test files - use debug_function() instead!
    """
    import sys
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    if mode == "debug":
        asyncio.run(debug_function())
    else:
        asyncio.run(working_usage())