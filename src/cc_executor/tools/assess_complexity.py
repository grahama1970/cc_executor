#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "networkx",
#     "tree-sitter",
#     "tree-sitter-language-pack",
#     "loguru",
# ]
# ///
"""
assess_complexity.py - Error-aware complexity assessment tool with static analysis

Analyzes Python errors with context-specific strategies:
- ModuleNotFoundError: Shows import paths, project structure, available modules
- TypeError: Displays variable types, method signatures, type conversions
- AttributeError: Lists available attributes, similar names, class hierarchy
- General errors: Performs call graph analysis and complexity metrics

Returns a prompt with targeted analysis to guide debugging decisions.
Follows Python script template standards from docs/reference/PYTHON_SCRIPT_TEMPLATE.md

Example Input:
    {
        "error_type": "ModuleNotFoundError",
        "error_message": "No module named 'utils'",
        "file_path": "/path/to/file.py",
        "stack_trace": "File file.py, line 10, in <module>\\n    from utils import helper"
    }

Expected Output:
    A prompt with error-specific analysis and tool recommendations
"""

import json
import sys
import os
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
import networkx as nx
import ast
from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")

# Import tree_sitter_utils module directly to avoid circular imports
tree_sitter_utils_path = Path(__file__).parent.parent / "utils" / "tree_sitter_utils.py"
spec = __import__('importlib.util', fromlist=['spec_from_file_location', 'module_from_spec']).spec_from_file_location("tree_sitter_utils", tree_sitter_utils_path)
tree_sitter_utils = __import__('importlib.util', fromlist=['module_from_spec']).module_from_spec(spec)
spec.loader.exec_module(tree_sitter_utils)


# ============================================
# ERROR-SPECIFIC ANALYSIS STRATEGIES
# ============================================

ERROR_STRATEGIES = {
    'ModuleNotFoundError': {
        'focus': ['import_paths', 'project_structure', 'available_modules'],
        'skip': ['call_graph', 'coupling_metrics'],
        'analyzer': 'analyze_import_error'
    },
    'ImportError': {
        'focus': ['import_paths', 'circular_imports', 'module_availability'],
        'skip': ['call_graph'],
        'analyzer': 'analyze_import_error'
    },
    'TypeError': {
        'focus': ['variable_types', 'method_signatures', 'type_conversions'],
        'skip': ['import_analysis'],
        'analyzer': 'analyze_type_error'
    },
    'AttributeError': {
        'focus': ['object_attributes', 'class_hierarchy', 'similar_names'],
        'skip': ['general_metrics'],
        'analyzer': 'analyze_attribute_error'
    },
    'NameError': {
        'focus': ['variable_scope', 'available_names', 'import_status'],
        'skip': ['call_graph'],
        'analyzer': 'analyze_name_error'
    },
    'SyntaxError': {
        'focus': ['syntax_context', 'common_patterns'],
        'skip': ['call_graph', 'import_analysis'],
        'analyzer': 'analyze_syntax_error'
    }
}


def analyze_import_error(
    error_type: str,
    error_message: str,
    file_path: str,
    stack_trace: Optional[str] = None
) -> Dict[str, Any]:
    """Analyze import-related errors with focus on paths and structure."""
    
    analysis = {
        "error_specific": {},
        "suggestions": []
    }
    
    # Extract the missing module name
    import_name = None
    if "No module named" in error_message:
        # Handle both quoted and unquoted module names
        parts = error_message.split("'")
        if len(parts) >= 2:
            import_name = parts[1]
        else:
            # Try double quotes
            parts = error_message.split('"')
            if len(parts) >= 2:
                import_name = parts[1]
            else:
                # Fallback: extract word after "named"
                words = error_message.split()
                try:
                    idx = words.index("named")
                    if idx + 1 < len(words):
                        import_name = words[idx + 1].strip("'\"")
                except ValueError:
                    pass
    elif "cannot import name" in error_message:
        parts = error_message.split("'")
        if len(parts) >= 4:
            import_name = parts[3]
            analysis["error_specific"]["importing_from"] = parts[1]
        else:
            # Try double quotes
            parts = error_message.split('"')
            if len(parts) >= 4:
                import_name = parts[3]
                analysis["error_specific"]["importing_from"] = parts[1]
    
    if not import_name:
        return analysis
    
    # Analyze file location and project structure
    file_path_obj = Path(file_path)
    if file_path_obj.exists():
        # Get relative path components
        src_index = -1
        parts = file_path_obj.parts
        for i, part in enumerate(parts):
            if part in ['src', 'lib', 'app']:
                src_index = i
                break
        
        if src_index >= 0:
            relative_parts = parts[src_index:]
            analysis["error_specific"]["file_location"] = "/".join(relative_parts)
        
        # Check for available modules at various levels
        current_dir = file_path_obj.parent
        available_modules = []
        
        # Check current directory
        for item in current_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                available_modules.append(f"./{item.name}")
        
        # Check parent directories
        parent = current_dir.parent
        parent_modules = []
        for item in parent.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                parent_modules.append(f"../{item.name}")
        
        analysis["error_specific"]["available_at_current_level"] = available_modules[:5]
        analysis["error_specific"]["available_at_parent_level"] = parent_modules[:5]
        
        # Look for the specific module
        project_root = file_path_obj
        while project_root.parent != project_root:
            if (project_root / import_name).exists():
                rel_path = os.path.relpath(project_root / import_name, file_path_obj.parent)
                analysis["suggestions"].append(f"Found '{import_name}' at: {rel_path}")
                break
            if (project_root / '.git').exists() or (project_root / 'pyproject.toml').exists():
                break
            project_root = project_root.parent
    
    # Extract import statement from stack trace
    if stack_trace and "import" in stack_trace:
        lines = stack_trace.split('\n')
        for line in lines:
            if "from" in line or "import" in line:
                analysis["error_specific"]["import_statement"] = line.strip()
    
    # Check if file runs as script (has if __name__ == "__main__")
    if file_path_obj.exists():
        try:
            content = file_path_obj.read_text()
            if 'if __name__ == "__main__"' in content:
                # Calculate correct relative path to src directory
                src_index = -1
                parts = file_path_obj.parts
                for i, part in enumerate(parts):
                    if part == 'src':
                        src_index = i
                        break
                
                # Suggest using find_dotenv for more robust project root detection
                analysis["suggestions"].append("Add sys.path manipulation at module level before imports")
                analysis["suggestions"].append("Option 1 (Recommended): Use python-dotenv for robust path finding:")
                analysis["suggestions"].append("  from pathlib import Path")
                analysis["suggestions"].append("  from dotenv import find_dotenv")
                analysis["suggestions"].append("  import sys")
                analysis["suggestions"].append("  project_root = Path(find_dotenv()).parent if find_dotenv() else Path(__file__).parent")
                analysis["suggestions"].append("  sys.path.insert(0, str(project_root / 'src'))")
                
                # Also provide the brittle parent counting as fallback
                if src_index >= 0:
                    levels_up = len(parts) - src_index - 1
                    parent_refs = '.parent' * levels_up
                    analysis["suggestions"].append(f"Option 2 (Fallback): sys.path.insert(0, str(Path(__file__){parent_refs}))")
        except:
            pass
    
    return analysis


def analyze_type_error(
    error_type: str,
    error_message: str,
    file_path: str,
    stack_trace: Optional[str] = None
) -> Dict[str, Any]:
    """Analyze type-related errors with focus on type mismatches."""
    
    analysis = {
        "error_specific": {},
        "suggestions": []
    }
    
    # Common TypeError patterns
    if "not JSON serializable" in error_message:
        # Extract type name more reliably
        import re
        type_match = re.search(r"type\s+(\w+)", error_message)
        if type_match:
            type_name = type_match.group(1)
        else:
            # Safely extract type name from quotes
            parts = error_message.split("'")
            type_name = parts[1] if len(parts) > 1 else "unknown"
        
        analysis["error_specific"]["problematic_type"] = type_name
        analysis["suggestions"].append(f"Convert {type_name} to JSON-compatible type")
        
        if type_name == "datetime":
            analysis["suggestions"].append("Use .isoformat() for datetime objects")
        elif type_name == "set":
            analysis["suggestions"].append("Convert set to list: list(my_set)")
        elif type_name == "bytes":
            analysis["suggestions"].append("Decode bytes: my_bytes.decode('utf-8')")
    
    elif "must be str, not" in error_message:
        analysis["error_specific"]["expected"] = "str"
        # Safely extract actual type
        parts = error_message.split("not ")
        actual = parts[1] if len(parts) > 1 else "unknown"
        analysis["error_specific"]["actual"] = actual
        analysis["suggestions"].append(f"Convert to string: str(value)")
    
    elif "unsupported operand type" in error_message:
        analysis["error_specific"]["operation_error"] = True
        analysis["suggestions"].append("Check variable types before operation")
        analysis["suggestions"].append("Add type validation or conversion")
    
    return analysis


def analyze_attribute_error(
    error_type: str,
    error_message: str,
    file_path: str,
    stack_trace: Optional[str] = None
) -> Dict[str, Any]:
    """Analyze attribute-related errors."""
    
    analysis = {
        "error_specific": {},
        "suggestions": []
    }
    
    # Extract object and attribute names
    if "has no attribute" in error_message:
        parts = error_message.split("'")
        if len(parts) >= 4:
            obj_type = parts[1]
            attr_name = parts[3]
            analysis["error_specific"]["object_type"] = obj_type
            analysis["error_specific"]["missing_attribute"] = attr_name
        else:
            # Try double quotes
            parts = error_message.split('"')
            if len(parts) >= 4:
                obj_type = parts[1]
                attr_name = parts[3]
                analysis["error_specific"]["object_type"] = obj_type
                analysis["error_specific"]["missing_attribute"] = attr_name
            
            # Suggest similar attributes for common types
            if obj_type == "dict":
                analysis["suggestions"].append("For dict, use ['key'] not .key")
            elif obj_type == "list":
                analysis["suggestions"].append("Lists don't have attributes, use methods like .append()")
    
    return analysis


def analyze_name_error(
    error_type: str,
    error_message: str,
    file_path: str,
    stack_trace: Optional[str] = None
) -> Dict[str, Any]:
    """Analyze name/variable errors."""
    
    analysis = {
        "error_specific": {},
        "suggestions": []
    }
    
    if "is not defined" in error_message:
        # Safely extract name from quotes
        parts = error_message.split("'")
        if len(parts) > 1:
            name = parts[1]
        else:
            parts = error_message.split('"')
            name = parts[1] if len(parts) > 1 else "unknown"
        
        analysis["error_specific"]["undefined_name"] = name
        analysis["suggestions"].append(f"Check if '{name}' is imported or defined")
        analysis["suggestions"].append(f"Common fix: import {name} or define it")
    
    return analysis


def analyze_syntax_error(
    error_type: str,
    error_message: str,
    file_path: str,
    stack_trace: Optional[str] = None
) -> Dict[str, Any]:
    """Analyze syntax errors."""
    
    analysis = {
        "error_specific": {},
        "suggestions": []
    }
    
    if "invalid syntax" in error_message:
        analysis["suggestions"].append("Check for missing colons, parentheses, or quotes")
        analysis["suggestions"].append("Verify indentation is consistent")
    
    return analysis


def get_error_specific_analysis(
    error_type: str,
    error_message: str,
    file_path: str,
    stack_trace: Optional[str] = None
) -> Dict[str, Any]:
    """Route to appropriate error-specific analyzer."""
    
    strategy = ERROR_STRATEGIES.get(error_type, {})
    analyzer_name = strategy.get('analyzer')
    
    if analyzer_name and analyzer_name in globals():
        analyzer = globals()[analyzer_name]
        return analyzer(error_type, error_message, file_path, stack_trace)
    
    return {"error_specific": {}, "suggestions": []}


def build_call_graph(code: str, language: str) -> nx.DiGraph:
    """Build a function call graph from code using tree-sitter."""
    metadata = tree_sitter_utils.extract_code_metadata(code, language)
    
    if not metadata.get("tree_sitter_success"):
        return nx.DiGraph()
    
    graph = nx.DiGraph()
    
    # Add all functions as nodes
    for func in metadata.get("functions", []):
        graph.add_node(func["name"], type="function", data=func)
    
    # Parse function bodies to find calls
    for func in metadata.get("functions", []):
        func_code = func.get("code", "")
        for other_func in metadata.get("functions", []):
            if other_func["name"] != func["name"] and f"{other_func['name']}(" in func_code:
                graph.add_edge(func["name"], other_func["name"])
    
    return graph


def analyze_file_structure(file_path: str, error_type: str) -> Dict[str, Any]:
    """Analyze file structure using appropriate strategy for error type."""
    
    analysis = {
        "exists": False,
        "tree_sitter_analysis": None,
        "call_graph": None,
        "ast_metrics": None,
        "error": None
    }
    
    # Check what to skip based on error type
    strategy = ERROR_STRATEGIES.get(error_type, {})
    skip_items = strategy.get('skip', [])
    
    try:
        if not Path(file_path).exists():
            return analysis
            
        analysis["exists"] = True
        code = Path(file_path).read_text()
        
        # Basic metrics (always include)
        lines = code.splitlines()
        analysis["basic_metrics"] = {
            "size_bytes": len(code),
            "line_count": len(lines),
            "non_empty_lines": len([l for l in lines if l.strip()])
        }
        
        # Determine language
        language = tree_sitter_utils.get_language_by_extension(file_path) or "python"
        
        # Tree-sitter analysis (unless skipped)
        if 'tree_sitter' not in skip_items:
            ts_metadata = tree_sitter_utils.extract_code_metadata(code, language)
            if ts_metadata.get("tree_sitter_success"):
                analysis["tree_sitter_analysis"] = {
                    "functions": len(ts_metadata.get("functions", [])),
                    "classes": len(ts_metadata.get("classes", [])),
                    "function_names": [f["name"] for f in ts_metadata.get("functions", [])],
                    "class_names": [c["name"] for c in ts_metadata.get("classes", [])]
                }
                
                # Build call graph (unless skipped)
                if 'call_graph' not in skip_items:
                    graph = build_call_graph(code, language)
                    if graph.nodes:
                        analysis["call_graph"] = {
                            "nodes": list(graph.nodes),
                            "edges": list(graph.edges),
                            "is_cyclic": not nx.is_directed_acyclic_graph(graph),
                            "in_degrees": dict(graph.in_degree()),
                            "out_degrees": dict(graph.out_degree())
                        }
        
        # Python AST analysis for imports (unless skipped)
        if language == "python" and 'import_analysis' not in skip_items:
            try:
                tree = ast.parse(code)
                imports = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        imports.extend(alias.name for alias in node.names)
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ''
                        imports.extend(f"{module}.{alias.name}" for alias in node.names)
                
                analysis["ast_metrics"] = {
                    "imports": imports,
                    "import_count": len(imports)
                }
            except:
                pass
                
    except Exception as e:
        analysis["error"] = str(e)
    
    return analysis


def check_project_patterns(file_path: str) -> Dict[str, Any]:
    """Check for project-specific patterns and conventions."""
    
    patterns = {
        "import_style": "unknown",
        "test_pattern": "unknown",
        "has_requirements": False,
        "has_pyproject": False
    }
    
    file_path_obj = Path(file_path)
    project_root = file_path_obj
    
    # Find project root - check for .env, .git, or pyproject.toml
    while project_root.parent != project_root:
        if any((project_root / marker).exists() for marker in ['.env', '.git', 'pyproject.toml']):
            break
        project_root = project_root.parent
    
    # Try to use python-dotenv if available
    try:
        from dotenv import find_dotenv
        dotenv_path = find_dotenv(str(file_path_obj))
        if dotenv_path:
            project_root = Path(dotenv_path).parent
    except ImportError:
        pass
    
    # Check for requirements files
    patterns["has_requirements"] = (project_root / "requirements.txt").exists()
    patterns["has_pyproject"] = (project_root / "pyproject.toml").exists()
    
    # Detect import style from nearby files
    try:
        py_files = list(file_path_obj.parent.glob("*.py"))[:5]
        relative_imports = 0
        absolute_imports = 0
        sys_path_found = False
        
        for py_file in py_files:
            try:
                content = py_file.read_text()
                if "from ." in content:
                    relative_imports += 1
                if "from src" in content or "from app" in content or "from utils" in content:
                    absolute_imports += 1
                if "sys.path.insert" in content or "sys.path.append" in content:
                    sys_path_found = True
            except:
                pass
        
        if relative_imports > absolute_imports:
            patterns["import_style"] = "relative"
        elif absolute_imports > relative_imports:
            patterns["import_style"] = "absolute"
            
        patterns["uses_sys_path"] = sys_path_found
    except:
        pass
    
    return patterns


def generate_assessment_prompt(
    error_type: str,
    error_message: str,
    file_path: str,
    stack_trace: Optional[str] = None,
    previous_attempts: int = 0
) -> str:
    """Generate a prompt with error-aware analysis for assessing complexity."""
    
    # Get error-specific analysis
    error_analysis = get_error_specific_analysis(error_type, error_message, file_path, stack_trace)
    
    # Perform general file analysis with error-aware strategy
    file_analysis = analyze_file_structure(file_path, error_type)
    
    # Check project patterns
    project_patterns = check_project_patterns(file_path)
    
    # Build key issues summary
    key_issues = []
    complexity_indicators = []
    
    if not file_analysis["exists"]:
        key_issues.append(f"⚠️ File not found: {file_path}")
    else:
        # Add error-specific issues
        if error_type == "ModuleNotFoundError" and error_analysis.get("error_specific"):
            if "importing_from" in error_analysis["error_specific"]:
                key_issues.append(f"❌ Cannot import from '{error_analysis['error_specific']['importing_from']}'")
        
        # Add complexity issues only if relevant to error type
        strategy = ERROR_STRATEGIES.get(error_type, {})
        if 'call_graph' not in strategy.get('skip', []):
            if file_analysis.get("call_graph", {}).get("is_cyclic"):
                key_issues.append("🔄 **Circular dependencies detected**")
                complexity_indicators.append("circular_deps")
            
            cg = file_analysis.get("call_graph", {})
            max_out = max(cg.get("out_degrees", {}).values(), default=0)
            if max_out > 5:
                funcs = [n for n, d in cg["out_degrees"].items() if d == max_out]
                key_issues.append(f"🔥 **High coupling**: {', '.join(funcs)} ({max_out} dependencies)")
                complexity_indicators.append("high_coupling")
        
        # Check for previous attempts
        if previous_attempts > 2:
            key_issues.append(f"⚠️ **Multiple attempts**: {previous_attempts} previous failures")
            complexity_indicators.append("multiple_failures")
        
        # Check for performance-related errors
        if any(indicator in error_message.lower() for indicator in ["memory", "overflow", "timeout", "deadlock", "performance"]):
            key_issues.append("🚨 **Performance/Resource issue detected**")
            complexity_indicators.append("performance_issue")
    
    # Build the prompt with key issues first
    prompt = f"""## 🎯 Key Issues Identified
{chr(10).join('- ' + issue for issue in key_issues) if key_issues else '- No critical issues detected'}

## Error Summary
- **Type**: {error_type}
- **Message**: {error_message}
- **File**: {file_path}
- **Attempts**: {previous_attempts}

## Stack Trace
```
{stack_trace if stack_trace else "No stack trace provided"}
```
"""
    
    # Add error-specific analysis section
    if error_analysis.get("error_specific"):
        prompt += "\n## Error-Specific Analysis\n"
        
        for key, value in error_analysis["error_specific"].items():
            if isinstance(value, list):
                prompt += f"- **{key.replace('_', ' ').title()}**: {', '.join(value[:3])}"
                if len(value) > 3:
                    prompt += f" (+{len(value)-3} more)"
                prompt += "\n"
            else:
                prompt += f"- **{key.replace('_', ' ').title()}**: {value}\n"
        
        if error_analysis.get("suggestions"):
            prompt += "\n### Quick Fix Suggestions\n"
            for suggestion in error_analysis["suggestions"]:
                prompt += f"- {suggestion}\n"
    
    # Add project context
    prompt += "\n## Project Context\n"
    prompt += f"- **Import style**: {project_patterns['import_style']}\n"
    prompt += f"- **Has requirements.txt**: {'Yes' if project_patterns['has_requirements'] else 'No'}\n"
    prompt += f"- **Has pyproject.toml**: {'Yes' if project_patterns['has_pyproject'] else 'No'}\n"
    if project_patterns.get('uses_sys_path'):
        prompt += f"- **Uses sys.path manipulation**: Yes (check for sys.path.insert at module level)\n"
    
    # Add relevant metrics based on error type
    if file_analysis["exists"]:
        strategy = ERROR_STRATEGIES.get(error_type, {})
        focus_items = strategy.get('focus', [])
        
        prompt += "\n## Relevant Analysis\n"
        
        # Always show tree-sitter analysis if available
        if file_analysis.get("tree_sitter_analysis"):
            ts = file_analysis["tree_sitter_analysis"]
            prompt += f"- **Functions in file**: {ts['functions']} total"
            if ts['function_names']:
                prompt += f" ({', '.join(ts['function_names'][:5])}"
                if len(ts['function_names']) > 5:
                    prompt += f" +{len(ts['function_names'])-5} more"
                prompt += ")"
            prompt += "\n"
            
            if ts['classes']:
                prompt += f"- **Classes in file**: {ts['classes']} total ({', '.join(ts['class_names'][:3])})\n"
        
        # Show metrics relevant to the error
        if 'import_paths' in focus_items and file_analysis.get("ast_metrics"):
            ast_m = file_analysis["ast_metrics"]
            if ast_m.get("imports"):
                prompt += f"- **Current imports**: {', '.join(ast_m['imports'][:5])}\n"
        
        # Show call graph details when not skipped
        if 'call_graph' not in strategy.get('skip', []) and file_analysis.get("call_graph"):
            cg = file_analysis["call_graph"]
            if cg.get("is_cyclic"):
                prompt += "- **⚠️ Circular dependencies detected**\n"
            
            # Show high coupling functions with details
            high_coupling = [(n, d) for n, d in cg.get("out_degrees", {}).items() if d > 3]
            if high_coupling:
                prompt += "- **Call graph analysis**:\n"
                for func, deps in sorted(high_coupling, key=lambda x: x[1], reverse=True)[:3]:
                    prompt += f"  - `{func}()` calls {deps} functions\n"
                    
            # Show most called functions
            high_in_degree = [(n, d) for n, d in cg.get("in_degrees", {}).items() if d > 2]
            if high_in_degree:
                prompt += "- **Most called functions**:\n"
                for func, calls in sorted(high_in_degree, key=lambda x: x[1], reverse=True)[:3]:
                    prompt += f"  - `{func}()` called by {calls} functions\n"
    
    # Add complexity assessment section if indicators present
    if complexity_indicators:
        prompt += "\n## 🚨 Complexity Assessment\n"
        if "circular_deps" in complexity_indicators:
            prompt += "- **TOO COMPLEX FOR SELF-FIX**: Circular dependencies require architectural analysis\n"
        if "high_coupling" in complexity_indicators:
            prompt += "- **TOO COMPLEX FOR SELF-FIX**: High coupling indicates structural issues\n"
        if "multiple_failures" in complexity_indicators:
            prompt += "- **STOP ATTEMPTING**: Multiple failures suggest fundamental misunderstanding\n"
        if "performance_issue" in complexity_indicators:
            prompt += "- **TOO COMPLEX FOR SELF-FIX**: Performance issues require profiling and analysis\n"
        prompt += "\n**Recommendation**: Do NOT attempt to fix this yourself. Use appropriate tools below.\n"
    
    prompt += f"""
## Compliance Check
- Review against: `/home/graham/workspace/experiments/cc_executor/docs/reference/PYTHON_SCRIPT_TEMPLATE.md`
- Ensure proper import organization, error handling, and documentation

## Assessment Criteria
1. **Error clarity**: Is the error message specific and actionable?
2. **Fix confidence**: Can you identify the exact fix from the analysis?
3. **Scope**: Is this localized or does it affect multiple components?
4. **Pattern match**: Does this match common patterns in the project?

## Approach Recommendations

Choose your approach based on the analysis:

1. **Self-fix** (High confidence): You understand the exact fix
   - Direct implementation using Edit/Write tools
   - Example: "datetime not JSON serializable" → use .isoformat()
   - ✅ USE WHEN: Clear path like "Found 'utils' at: ../../../utils"

2. **Documentation lookup** (Library-specific): Need official library documentation
   - Tool: `mcp__context7__get-library-docs` (after `mcp__context7__resolve-library-id`)
   - ✅ USE WHEN: Need specific API docs, method signatures, or examples

3. **Research best practices** (General questions): Need patterns or best practices
   - Tool: `mcp__perplexity-ask__perplexity_ask`
   - ✅ USE WHEN: General questions, error explanations, or current best practices

4. **Fresh context** (Stuck/confused): Need new perspective after multiple attempts
   - Tool: `mcp__cc-execute__execute_task` 
   - ⚠️ USE WHEN: Tunnel vision, repeated failures, or need fresh approach

5. **Comprehensive analysis** (Complex): Architectural or multi-file issues
   - Tool: `mcp__logger-tools__send_to_gemini`
   - 🚨 USE WHEN: Circular dependencies, high coupling, performance issues
   - 🚨 MANDATORY FOR: Any issue marked "TOO COMPLEX FOR SELF-FIX" above

Based on the above analysis, which approach and tool is most appropriate?"""
    
    return prompt


def main(
    error_type: str,
    error_message: str,
    file_path: str,
    stack_trace: Optional[str] = None,
    previous_attempts: int = 0,
    **kwargs  # Ignore extra parameters for compatibility
) -> str:
    """Entry point that returns the assessment prompt."""
    
    prompt = generate_assessment_prompt(
        error_type=error_type,
        error_message=error_message,
        file_path=file_path,
        stack_trace=stack_trace,
        previous_attempts=previous_attempts
    )
    
    # Return the prompt directly as a string
    return prompt


async def working_usage():
    """Stable working examples demonstrating the tool's functionality."""
    logger.info("=== Error-Aware Complexity Assessment Tool ===\n")
    
    # Example 1: ModuleNotFoundError
    logger.info("Example 1: ModuleNotFoundError Analysis")
    prompt1 = main(
        error_type="ModuleNotFoundError",
        error_message="No module named 'utils'",
        file_path="/home/graham/workspace/experiments/cc_executor/proof_of_concept/logger_agent/src/agent_graph_builder.py",
        stack_trace="File agent_graph_builder.py, line 10\n    from utils.test_db import setup"
    )
    logger.info("Generated prompt focuses on import paths and project structure")
    
    # Example 2: TypeError
    logger.info("\nExample 2: TypeError Analysis")
    prompt2 = main(
        error_type="TypeError",
        error_message="Object of type datetime is not JSON serializable",
        file_path="/home/graham/workspace/experiments/cc_executor/src/arango_log_sink.py",
        stack_trace="File arango_log_sink.py, line 124\n    json.dumps(log_doc)"
    )
    logger.info("Generated prompt focuses on type conversion and serialization")
    
    return True


async def debug_function():
    """Debug function for testing new error types and edge cases."""
    logger.info("=== Debug Mode - Testing Error Analysis ===")
    
    # Test with a complex circular import scenario
    test_case = {
        "error_type": "ImportError",
        "error_message": "cannot import name 'GraphBuilder' from partially initialized module 'graph'",
        "file_path": "/test/path/graph/__init__.py",
        "stack_trace": "Circular import detected",
        "previous_attempts": 3
    }
    
    prompt = main(**test_case)
    print("\n--- Generated Prompt ---")
    print(prompt[:500] + "...")
    
    return True


if __name__ == "__main__":
    """
    Script entry point following PYTHON_SCRIPT_TEMPLATE.md standards.
    
    Usage:
        python assess_complexity.py              # Runs working_usage()
        python assess_complexity.py debug        # Runs debug_function()
        python assess_complexity.py '{"error_type": "TypeError", ...}'  # Direct JSON input
    """
    import asyncio
    
    mode = "working"
    
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "debug":
            mode = "debug"
        elif arg.startswith('{'):
            # Direct JSON input mode
            input_data = json.loads(arg)
            result = main(**input_data)
            print(result)
            exit(0)
    
    async def run_mode():
        if mode == "debug":
            logger.info("Running in DEBUG mode...")
            return await debug_function()
        else:
            logger.info("Running in WORKING mode...")
            return await working_usage()
    
    # Single asyncio.run() call
    success = asyncio.run(run_mode())
    exit(0 if success else 1)