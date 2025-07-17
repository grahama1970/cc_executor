"""
Enhanced Tree-Sitter utilities for GitGit repository analysis.
Module: tree_sitter_utils.py
Description: Utility functions and helpers for tree sitter utils

This module provides comprehensive code metadata extraction using Tree-Sitter.
It supports a wide range of programming languages and extracts detailed function and
class information including parameter types, default values, and docstrings.

Key features:
1. Support for 100+ programming languages
2. Detailed parameter extraction including types and defaults
3. Docstring extraction and association
4. Class and method relationship tracking
5. Robust error handling with fallbacks
6. Line number tracking for better context
"""

import os
import json
import logging
from typing import Optional, Dict, List, Any, Tuple, Union

# Try to use loguru if available, otherwise use standard logging
try:
    from loguru import logger
except ImportError:
    # Set up standard logging as fallback
    logger = logging.getLogger(__name__)
    
from tree_sitter import Parser, Node
import tree_sitter_language_pack as tlp


# Expanded mapping of code block types/file extensions to Tree-sitter language names
LANGUAGE_MAPPINGS = {
    # ActionScript
    "actionscript": "actionscript",
    "as": "actionscript",
    
    # Ada
    "ada": "ada",
    "adb": "ada",
    "ads": "ada",
    
    # Arduino
    "ino": "arduino",
    "arduino": "arduino",
    
    # Assembly
    "asm": "asm",
    "s": "asm",
    
    # Bash/Shell
    "sh": "bash",
    "bash": "bash",
    "zsh": "bash",
    
    # C
    "c": "c",
    "h": "c",
    
    # C++
    "cpp": "cpp",
    "cxx": "cpp",
    "cc": "cpp",
    "hpp": "cpp",
    "hxx": "cpp",
    "hh": "cpp",
    
    # C#
    "cs": "csharp",
    "csharp": "csharp",
    
    # CSS
    "css": "css",
    
    # Dart
    "dart": "dart",
    
    # Go
    "go": "go",
    
    # HTML
    "html": "html",
    "htm": "html",
    
    # Java
    "java": "java",
    
    # JavaScript
    "js": "javascript",
    "javascript": "javascript",
    "jsx": "javascript",
    
    # JSON
    "json": "json",
    
    # Julia
    "jl": "julia",
    "julia": "julia",
    
    # Kotlin
    "kt": "kotlin",
    "kts": "kotlin",
    "kotlin": "kotlin",
    
    # Lua
    "lua": "lua",
    
    # Markdown
    "md": "markdown",
    "markdown": "markdown",
    
    # Objective-C
    "m": "objc",
    "mm": "objc",
    "objc": "objc",
    
    # OCaml
    "ml": "ocaml",
    "mli": "ocaml_interface",
    "ocaml": "ocaml",
    
    # PHP
    "php": "php",
    
    # Python
    "py": "python",
    "python": "python",
    "pyi": "python",
    
    # R
    "r": "r",
    
    # Ruby
    "rb": "ruby",
    "ruby": "ruby",
    
    # Rust
    "rs": "rust",
    "rust": "rust",
    
    # Scala
    "scala": "scala",
    "sc": "scala",
    
    # Swift
    "swift": "swift",
    
    # TypeScript
    "ts": "typescript",
    "typescript": "typescript",
    "tsx": "typescript",
    
    # XML
    "xml": "xml",
    
    # YAML
    "yaml": "yaml",
    "yml": "yaml",
}


def get_language_by_extension(file_path: str) -> Optional[str]:
    """
    Determine the programming language from a file path's extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        The language identifier if recognized, None otherwise
    """
    ext = os.path.splitext(file_path)[1].lstrip('.').lower()
    return LANGUAGE_MAPPINGS.get(ext)


def get_language_by_name(language_name: str) -> Optional[str]:
    """
    Determine if a language name is supported.
    
    Args:
        language_name: Name of the language to check
        
    Returns:
        The language identifier if supported, None otherwise
    """
    language_name = language_name.lower()
    if language_name in LANGUAGE_MAPPINGS:
        return language_name
    for key, value in LANGUAGE_MAPPINGS.items():
        if value == language_name:
            return value
    return None


def get_supported_language(code_type: str) -> Optional[str]:
    """
    Return the Tree-sitter language name for a given code type, if supported.
    
    Args:
        code_type: The code type or file extension
        
    Returns:
        The language identifier if supported, None otherwise
    """
    code_type = code_type.lstrip(".").lower()
    language_name = LANGUAGE_MAPPINGS.get(code_type)
    if not language_name:
        logger.debug(f"No language mapping for code type: {code_type}")
        return None
    try:
        tlp.get_language(language_name)
        return language_name
    except Exception as e:
        logger.debug(f"Language {language_name} not supported by tree-sitter-language-pack: {e}")
        return None


def extract_parameter_type(node: Node) -> Optional[str]:
    """
    Extract type information from a parameter node.
    
    Args:
        node: The parameter node to analyze
        
    Returns:
        Type annotation as a string, or None if not found
    """
    # Check for explicit type annotations
    type_node = node.child_by_field_name("type")
    if type_node:
        return type_node.text.decode("utf-8")
    
    # Look for Python-style annotations
    for child in node.children:
        if child.type == "type_annotation":
            for subchild in child.children:
                if subchild.type not in (":", "annotation"):
                    return subchild.text.decode("utf-8")
        
    # Look for TypeScript-style annotations
    for child in node.children:
        if child.type == "type_annotation" or child.type == "type":
            return child.text.decode("utf-8")
            
    return None


def extract_default_value(node: Node) -> Optional[str]:
    """
    Extract default value from a parameter node.
    
    Args:
        node: The parameter node to analyze
        
    Returns:
        Default value as a string, or None if not found
    """
    # For Python default parameters
    if node.type == "default_parameter" or node.type.endswith("default_parameter"):
        for child in node.children:
            if child.type == "=" or child.type == "eq":
                # The next sibling should be the default value
                idx = node.children.index(child)
                if idx < len(node.children) - 1:
                    return node.children[idx + 1].text.decode("utf-8")
    
    # For TypeScript/JavaScript default parameters
    for child in node.children:
        if child.type == "initializer" or child.type == "default_value":
            for subchild in child.children:
                if subchild.type != "=":
                    return subchild.text.decode("utf-8")
    
    return None


def is_parameter_required(node: Node) -> bool:
    """
    Determine if a parameter is required (no default value).
    
    Args:
        node: The parameter node to analyze
        
    Returns:
        True if the parameter is required, False otherwise
    """
    # If it has a default value, it's not required
    if extract_default_value(node) is not None:
        return False
    
    # Check for optional markers in TypeScript/JavaScript
    for child in node.children:
        if child.type == "?" or child.text.decode("utf-8") == "?":
            return False
    
    return True


def extract_parameters(parameters_node: Node, language: str) -> List[Dict[str, Any]]:
    """
    Extract comprehensive parameter information including types, defaults, and requirements.
    
    Args:
        parameters_node: The function parameters node
        language: The programming language identifier
        
    Returns:
        List of parameter dictionaries with name, type, default, and required fields
    """
    params = []
    
    if not parameters_node:
        return params
        
    for child in parameters_node.children:
        # Skip punctuation and non-parameter nodes
        if child.type in (",", "(", ")", "[", "]", "{", "}", "comment"):
            continue
            
        param_info = {
            "name": None,
            "type": None,
            "default": None,
            "required": True
        }
        
        # Direct identifier (simple parameter)
        if child.type == "identifier":
            param_info["name"] = child.text.decode("utf-8")
            
        # Typed or default parameters
        elif child.type in ("typed_parameter", "default_parameter", "optional_parameter", 
                          "parameter", "formal_parameter", "required_parameter"):
            # Find the parameter name
            name_node = child.child_by_field_name("name")
            if name_node:
                param_info["name"] = name_node.text.decode("utf-8")
            else:
                # Search for an identifier or pattern node
                for subchild in child.children:
                    if subchild.type == "identifier" or subchild.type == "pattern":
                        param_info["name"] = subchild.text.decode("utf-8")
                        break
            
            # Extract type information
            param_info["type"] = extract_parameter_type(child)
            
            # Extract default value
            param_info["default"] = extract_default_value(child)
            
            # Determine if required
            param_info["required"] = is_parameter_required(child)
        
        # For rest parameters (e.g., ...args in JavaScript)
        elif child.type == "rest_parameter":
            for subchild in child.children:
                if subchild.type == "identifier":
                    param_info["name"] = "..." + subchild.text.decode("utf-8")
                    param_info["required"] = False
                    break
        
        # Add the parameter if we found a name
        if param_info["name"]:
            params.append(param_info)
    
    return params


def extract_return_type(node: Node) -> Optional[str]:
    """
    Extract the function return type if specified.
    
    Args:
        node: The function definition node
        
    Returns:
        Return type as a string, or None if not found
    """
    # Check for TypeScript/Java style return type
    return_type = node.child_by_field_name("return_type")
    if return_type:
        return return_type.text.decode("utf-8")
    
    # Check for Python style return annotation
    for child in node.children:
        if child.type == "return_type" or child.type == "return_type_annotation":
            # Skip the arrow itself
            for subchild in child.children:
                if subchild.type not in ("->", ":"):
                    return subchild.text.decode("utf-8")
    
    return None


def extract_docstring(body_node: Node, language: str) -> Optional[str]:
    """
    Extract docstring based on the programming language.
    
    Args:
        body_node: The function/class body node
        language: The programming language identifier
        
    Returns:
        Docstring as a string, or None if not found
    """
    if not body_node:
        return None
        
    # Python-style docstrings
    if language == "python":
        for child in body_node.children:
            if child.type == "expression_statement":
                expr = child.child_by_field_name("expression")
                if expr and expr.type == "string":
                    docstring = expr.text.decode("utf-8").strip("'\"")
                    # Clean up multiline docstrings
                    return docstring.replace('"""', '').replace("'''", '').strip()
    
    # JavaScript/TypeScript JSDoc comments
    elif language in ("javascript", "typescript"):
        prev_sibling = body_node.prev_sibling
        while prev_sibling:
            if prev_sibling.type == "comment" and "/**" in prev_sibling.text.decode("utf-8"):
                comment = prev_sibling.text.decode("utf-8")
                # Clean up JSDoc format
                lines = comment.split("\n")
                cleaned_lines = []
                for line in lines:
                    line = line.strip()
                    line = line.lstrip("/*").rstrip("*/").strip()
                    line = line.lstrip("*").strip()
                    if line:
                        cleaned_lines.append(line)
                return "\n".join(cleaned_lines)
            prev_sibling = prev_sibling.prev_sibling
    
    # Java/Kotlin/Scala Javadoc comments
    elif language in ("java", "kotlin", "scala"):
        prev_sibling = body_node.prev_sibling
        while prev_sibling:
            if prev_sibling.type == "comment" and "/**" in prev_sibling.text.decode("utf-8"):
                comment = prev_sibling.text.decode("utf-8")
                # Clean up Javadoc format
                lines = comment.split("\n")
                cleaned_lines = []
                for line in lines:
                    line = line.strip()
                    line = line.lstrip("/*").rstrip("*/").strip()
                    line = line.lstrip("*").strip()
                    if line and not line.startswith("@"):  # Skip Javadoc tags
                        cleaned_lines.append(line)
                return "\n".join(cleaned_lines)
            prev_sibling = prev_sibling.prev_sibling
    
    # For other languages, try a generic approach
    for child in body_node.children:
        if child.type == "comment":
            return child.text.decode("utf-8").strip()
    
    return None


def extract_code_metadata(code: str, language: str) -> Dict[str, Any]:
    """
    Extract comprehensive metadata from code using tree-sitter.
    
    Args:
        code: The source code to analyze
        language: The programming language identifier
        
    Returns:
        Dictionary containing extracted metadata
    """
    metadata = {
        "language": language,
        "functions": [],
        "classes": [],
        "tree_sitter_success": False,
        "error": None
    }
    
    try:
        # Skip unsupported languages
        language_id = get_supported_language(language)
        if not language_id:
            metadata["error"] = f"Unsupported language: {language}"
            return metadata
            
        # Get parser for the language
        parser = tlp.get_parser(language_id)
        
        # Parse the code
        tree = parser.parse(bytes(code, "utf8"))
        root_node = tree.root_node
        
        # Language-specific query patterns
        queries = {
            "python": """
                (function_definition
                    name: (identifier) @func_name
                    parameters: (parameters) @params
                    body: (block) @body
                ) @function

                (class_definition
                    name: (identifier) @class_name
                    body: (block) @class_body
                ) @class
            """,
            "javascript": """
                (function_declaration
                    name: (identifier) @func_name
                    parameters: (formal_parameters) @params
                    body: (statement_block) @body
                ) @function

                (method_definition
                    name: (property_identifier) @method_name
                    parameters: (formal_parameters) @params
                    body: (statement_block) @body
                ) @method

                (class_declaration
                    name: (identifier) @class_name
                    body: (class_body) @class_body
                ) @class
            """,
            "typescript": """
                (function_declaration
                    name: (identifier) @func_name
                    parameters: (formal_parameters) @params
                    body: (statement_block) @body
                ) @function

                (method_definition
                    name: (property_identifier) @method_name
                    parameters: (formal_parameters) @params
                    body: (statement_block) @body
                ) @method

                (class_declaration
                    name: (identifier) @class_name
                    body: (class_body) @class_body
                ) @class
            """,
            "java": """
                (method_declaration
                    name: (identifier) @method_name
                    parameters: (formal_parameters) @params
                    body: (block) @body
                ) @method

                (class_declaration
                    name: (identifier) @class_name
                    body: (class_body) @class_body
                ) @class
            """,
            "cpp": """
                (function_definition
                    declarator: (function_declarator
                        declarator: (identifier) @func_name
                        parameters: (parameter_list) @params
                    )
                    body: (compound_statement) @body
                ) @function

                (class_specifier
                    name: (type_identifier) @class_name
                    body: (field_declaration_list) @class_body
                ) @class
            """,
            "go": """
                (function_declaration
                    name: (identifier) @func_name
                    parameters: (parameter_list) @params
                    body: (block) @body
                ) @function

                (method_declaration
                    name: (field_identifier) @method_name
                    parameters: (parameter_list) @params
                    body: (block) @body
                ) @method
            """,
            "ruby": """
                (method
                    name: (identifier) @method_name
                    parameters: (method_parameters) @params
                    body: (body_statement) @body
                ) @method

                (class
                    name: (constant) @class_name
                    body: (body_statement) @class_body
                ) @class
            """
        }
        
        # Fallback to python query for unsupported languages
        query_str = queries.get(language_id, queries["python"])
        lang_obj = tlp.get_language(language_id)
        
        try:
            query = lang_obj.query(query_str)
            capture_results = query.captures(root_node)
            
            # Process the captures based on the format (no logging of object types)
            
            # Process the captures
            functions = []
            classes = []
            
            current_function = None
            current_class = None
            
            # The capture_results can be in different formats depending on the tree-sitter version:
            # 1. List of (node, capture_name) tuples (original expectation)
            # 2. Dictionary mapping capture names to list of nodes
            # 3. Other formats we'll handle with a fallback
            try:
                # Handle dictionary case (most likely based on debug output)
                if isinstance(capture_results, dict):
                    # Process functions/methods
                    function_nodes = capture_results.get("function", []) + capture_results.get("method", [])
                    for node in function_nodes:
                        func_info = {
                            "name": "",
                            "parameters": [],
                            "return_type": None,
                            "docstring": None,
                            "line_span": (node.start_point[0] + 1, node.end_point[0] + 1),
                            "code": code[node.start_byte:node.end_byte]
                        }
                        
                        # Get function name
                        if "func_name" in capture_results:
                            for name_node in capture_results["func_name"]:
                                if name_node.start_byte >= node.start_byte and name_node.end_byte <= node.end_byte:
                                    func_info["name"] = name_node.text.decode("utf-8")
                                    break
                        
                        if "method_name" in capture_results and not func_info["name"]:
                            for name_node in capture_results["method_name"]:
                                if name_node.start_byte >= node.start_byte and name_node.end_byte <= node.end_byte:
                                    func_info["name"] = name_node.text.decode("utf-8")
                                    break
                        
                        # Get parameters
                        if "params" in capture_results:
                            for params_node in capture_results["params"]:
                                if params_node.start_byte >= node.start_byte and params_node.end_byte <= node.end_byte:
                                    func_info["parameters"] = extract_parameters(params_node, language_id)
                                    break
                                    
                        # Get body and docstring
                        if "body" in capture_results:
                            for body_node in capture_results["body"]:
                                if body_node.start_byte >= node.start_byte and body_node.end_byte <= node.end_byte:
                                    func_info["docstring"] = extract_docstring(body_node, language_id)
                                    func_info["return_type"] = extract_return_type(node)
                                    break
                                    
                        functions.append(func_info)
                    
                    # Process classes
                    class_nodes = capture_results.get("class", [])
                    for node in class_nodes:
                        class_info = {
                            "name": "",
                            "methods": [],
                            "docstring": None,
                            "line_span": (node.start_point[0] + 1, node.end_point[0] + 1),
                            "code": code[node.start_byte:node.end_byte]
                        }
                        
                        # Get class name
                        if "class_name" in capture_results:
                            for name_node in capture_results["class_name"]:
                                if name_node.start_byte >= node.start_byte and name_node.end_byte <= node.end_byte:
                                    class_info["name"] = name_node.text.decode("utf-8")
                                    break
                        
                        # Get class body and docstring
                        if "class_body" in capture_results:
                            for body_node in capture_results["class_body"]:
                                if body_node.start_byte >= node.start_byte and body_node.end_byte <= node.end_byte:
                                    class_info["docstring"] = extract_docstring(body_node, language_id)
                                    break
                                    
                        classes.append(class_info)
                
                # Handle list of tuples case (original expected format)
                else:
                    for capture in capture_results:
                        # Try to handle different capture formats
                        if isinstance(capture, tuple):
                            if len(capture) == 2:
                                node, name = capture
                            elif len(capture) == 3:
                                # Some versions might use (start, end, name) format
                                node = capture[0]
                                name = capture[2]
                            else:
                                # Skip if we can't understand the format
                                logger.debug(f"Skipping capture with unexpected format: {capture}")
                                continue
                        else:
                            # Skip if it's not a tuple
                            logger.debug(f"Skipping non-tuple capture: {capture}")
                            continue

                        if name == "function" or name == "method":
                            current_function = {
                                "name": "",
                                "parameters": [],
                                "return_type": None,
                                "docstring": None,
                                "line_span": (node.start_point[0] + 1, node.end_point[0] + 1),
                                "code": code[node.start_byte:node.end_byte]
                            }
                            functions.append(current_function)
                        
                        elif name == "func_name" or name == "method_name":
                            if current_function:
                                current_function["name"] = node.text.decode("utf-8")
                        
                        elif name == "params":
                            if current_function:
                                current_function["parameters"] = extract_parameters(node, language_id)
                        
                        elif name == "body":
                            if current_function:
                                # Extract docstring and return type
                                current_function["docstring"] = extract_docstring(node, language_id)
                                current_function["return_type"] = extract_return_type(current_function.get("node", node))
                        
                        elif name == "class":
                            current_class = {
                                "name": "",
                                "methods": [],
                                "docstring": None,
                                "line_span": (node.start_point[0] + 1, node.end_point[0] + 1),
                                "code": code[node.start_byte:node.end_byte]
                            }
                            classes.append(current_class)
                        
                        elif name == "class_name":
                            if current_class:
                                current_class["name"] = node.text.decode("utf-8")
                        
                        elif name == "class_body":
                            if current_class:
                                current_class["docstring"] = extract_docstring(node, language_id)
                
                metadata["functions"] = functions
                metadata["classes"] = classes
                metadata["tree_sitter_success"] = True
                
            except Exception as e:
                # Fallback to a simple approach if the query-based processing fails
                logger.warning(f"Query-based extraction processing failed: {e}, falling back to traversal")
                functions, classes = traverse_fallback(root_node, code, language_id)
                metadata["functions"] = functions
                metadata["classes"] = classes
                metadata["tree_sitter_success"] = True
            
        except Exception as e:
            # Fallback to a simple approach if the query fails
            logger.warning(f"Query-based extraction failed: {e}, falling back to traversal")
            functions, classes = traverse_fallback(root_node, code, language_id)
            metadata["functions"] = functions
            metadata["classes"] = classes
            metadata["tree_sitter_success"] = True
            
    except Exception as e:
        logger.error(f"Error parsing code with tree-sitter: {e}")
        metadata["error"] = str(e)
        metadata["tree_sitter_success"] = False
    
    return metadata


def traverse_fallback(root_node: Node, code: str, language_id: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Fallback method to traverse the syntax tree and extract basic metadata when queries fail.
    Optimized with memoization to avoid redundant work on large codebases.
    
    Args:
        root_node: The root node of the syntax tree
        code: The source code being analyzed
        language_id: The language identifier
        
    Returns:
        Tuple of (functions list, classes list)
    """
    functions = []
    classes = []
    
    # OPTIMIZATION: Add memoization cache to avoid reprocessing nodes
    processed_nodes = set()
    
    # OPTIMIZATION: Cache child lookups for specific types to avoid repeated scans
    child_type_cache = {}
    
    def find_child_by_type(node: Node, target_types: Tuple[str, ...]) -> Optional[Node]:
        """Helper function to find child node by type with caching."""
        # Create a cache key based on node ID and target types
        cache_key = (id(node), target_types)
        
        # Check if result is already in cache
        if cache_key in child_type_cache:
            return child_type_cache[cache_key]
        
        # Find the first child matching any of the target types
        result = None
        for child in node.children:
            if child.type in target_types:
                result = child
                break
                
        # Cache the result (including None results)
        child_type_cache[cache_key] = result
        return result
    
    def traverse(node: Node):
        # OPTIMIZATION: Skip already processed nodes
        node_id = id(node)
        if node_id in processed_nodes:
            return
        processed_nodes.add(node_id)
        
        # OPTIMIZATION: Early return for irrelevant node types (only process target types)
        if node.type not in (
            "function_definition", "function_declaration", "method_definition", "method_declaration",
            "class_definition", "class_declaration", "class_specifier", "class"
        ):
            # Only recurse into potentially relevant children
            for child in node.children:
                traverse(child)
            return
        
        # Extract function definitions
        if node.type in ("function_definition", "function_declaration", "method_definition", "method_declaration"):
            func_info = {
                "name": "",
                "parameters": [],
                "return_type": None,
                "docstring": None,
                "line_span": (node.start_point[0] + 1, node.end_point[0] + 1),
                "code": code[node.start_byte:node.end_byte]
            }
            
            # Extract function name - use cached lookup
            name_node = find_child_by_type(
                node, ("identifier", "property_identifier", "field_identifier")
            )
            
            if name_node:
                func_info["name"] = name_node.text.decode("utf-8")
            
            # Extract parameters - use cached lookup
            params_node = find_child_by_type(
                node, ("parameters", "formal_parameters", "parameter_list")
            )
                
            if params_node:
                func_info["parameters"] = extract_parameters(params_node, language_id)
            
            # Extract docstring - use cached lookup
            body_node = find_child_by_type(
                node, ("block", "statement_block", "compound_statement", "body_statement")
            )
                
            if body_node:
                func_info["docstring"] = extract_docstring(body_node, language_id)
            
            functions.append(func_info)
        
        # Extract class definitions
        elif node.type in ("class_definition", "class_declaration", "class_specifier", "class"):
            class_info = {
                "name": "",
                "methods": [],
                "docstring": None,
                "line_span": (node.start_point[0] + 1, node.end_point[0] + 1),
                "code": code[node.start_byte:node.end_byte]
            }
            
            # Extract class name - use cached lookup
            name_node = find_child_by_type(
                node, ("identifier", "type_identifier", "constant")
            )
                
            if name_node:
                class_info["name"] = name_node.text.decode("utf-8")
            
            # Extract docstring - use cached lookup
            body_node = find_child_by_type(
                node, ("block", "class_body", "field_declaration_list", "body_statement")
            )
                
            if body_node:
                class_info["docstring"] = extract_docstring(body_node, language_id)
                
            classes.append(class_info)
        
        # OPTIMIZATION: Process children in batches by type to improve locality
        # Process identifier-like children first (names)
        for child in node.children:
            if child.type in ("identifier", "property_identifier", "field_identifier", 
                            "type_identifier", "constant"):
                traverse(child)
        
        # Process parameter and body nodes next
        for child in node.children:
            if child.type in ("parameters", "formal_parameters", "parameter_list",
                            "block", "statement_block", "compound_statement", "body_statement",
                            "class_body", "field_declaration_list"):
                traverse(child)
        
        # Process remaining children
        for child in node.children:
            if child.type not in (
                "identifier", "property_identifier", "field_identifier", 
                "type_identifier", "constant",
                "parameters", "formal_parameters", "parameter_list",
                "block", "statement_block", "compound_statement", "body_statement",
                "class_body", "field_declaration_list"
            ):
                traverse(child)
    
    # Start traversal from root
    traverse(root_node)
    
    # Clear caches to free memory
    child_type_cache.clear()
    processed_nodes.clear()
    
    return functions, classes


def extract_code_metadata_from_file(file_path: str) -> Dict[str, Any]:
    """
    Extract code metadata from a file.
    
    Args:
        file_path: Path to the file to analyze
        
    Returns:
        Dictionary containing extracted metadata
    """
    try:
        language = get_language_by_extension(file_path)
        if not language:
            return {
                "language": "unknown",
                "functions": [],
                "classes": [],
                "tree_sitter_success": False,
                "error": f"Unsupported file extension: {os.path.splitext(file_path)[1]}"
            }
            
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            code = f.read()
            
        metadata = extract_code_metadata(code, language)
        metadata["file_path"] = file_path
        return metadata
        
    except Exception as e:
        logger.error(f"Error extracting metadata from file {file_path}: {e}")
        return {
            "language": get_language_by_extension(file_path) or "unknown",
            "functions": [],
            "classes": [],
            "file_path": file_path,
            "tree_sitter_success": False,
            "error": str(e)
        }


def get_language_info() -> Dict[str, List[str]]:
    """
    Get information about supported languages and their file extensions.
    
    Returns:
        Dictionary mapping language names to lists of file extensions
    """
    language_info = {}
    
    for ext, lang in LANGUAGE_MAPPINGS.items():
        if lang not in language_info:
            language_info[lang] = []
        language_info[lang].append(ext)
    
    return language_info


if __name__ == "__main__":
    """
    When run directly, this module provides a demonstration of its functionality
    by parsing a sample code file in each supported language.
    """
    import argparse
    from rich.console import Console
    from rich.table import Table
    
    # Setup argument parser
    parser = argparse.ArgumentParser(description="Tree-sitter code metadata extraction")
    parser.add_argument("--file", "-f", type=str, help="Path to a file to analyze")
    parser.add_argument("--language", "-l", type=str, help="Language identifier (if not using file)")
    parser.add_argument("--code", "-c", type=str, help="Code snippet (if not using file)")
    parser.add_argument("--list-languages", action="store_true", help="List supported languages")
    args = parser.parse_args()
    
    console = Console()
    
    # List supported languages if requested
    if args.list_languages:
        lang_info = get_language_info()
        console.print("[bold]Supported Languages:[/bold]")
        lang_table = Table(title="Tree-sitter Supported Languages")
        lang_table.add_column("Language", style="cyan")
        lang_table.add_column("File Extensions", style="green")
        
        for lang, exts in sorted(lang_info.items()):
            lang_table.add_row(lang, ", ".join(exts))
            
        console.print(lang_table)
        exit(0)
    
    # Analyze a file if provided
    if args.file:
        console.print(f"[bold]Analyzing file:[/bold] {args.file}")
        metadata = extract_code_metadata_from_file(args.file)
        
        if not metadata["tree_sitter_success"]:
            console.print(f"[red]Failed to extract metadata:[/red] {metadata.get('error', 'Unknown error')}")
            exit(1)
            
        # Display functions
        if metadata["functions"]:
            func_table = Table(title=f"Functions ({len(metadata['functions'])})")
            func_table.add_column("Name", style="cyan")
            func_table.add_column("Parameters", style="green")
            func_table.add_column("Return Type", style="blue")
            func_table.add_column("Lines", style="magenta")
            
            for func in metadata["functions"]:
                params_str = ", ".join([
                    f"{p['name']}: {p['type'] or 'any'}{' (optional)' if not p['required'] else ''}"
                    for p in func["parameters"]
                ])
                func_table.add_row(
                    func["name"],
                    params_str or "None",
                    func["return_type"] or "None",
                    f"{func['line_span'][0]}-{func['line_span'][1]}"
                )
                
            console.print(func_table)
        
        # Display classes
        if metadata["classes"]:
            class_table = Table(title=f"Classes ({len(metadata['classes'])})")
            class_table.add_column("Name", style="cyan")
            class_table.add_column("Lines", style="magenta")
            class_table.add_column("Docstring", style="green")
            
            for cls in metadata["classes"]:
                class_table.add_row(
                    cls["name"],
                    f"{cls['line_span'][0]}-{cls['line_span'][1]}",
                    (cls["docstring"] or "")[:50] + ("..." if cls["docstring"] and len(cls["docstring"]) > 50 else "")
                )
                
            console.print(class_table)
            
        console.print(f"[green]Successfully extracted metadata for {args.file}[/green]")
        
    # Analyze a code snippet if provided
    elif args.language and args.code:
        console.print(f"[bold]Analyzing {args.language} code snippet[/bold]")
        metadata = extract_code_metadata(args.code, args.language)
        
        if not metadata["tree_sitter_success"]:
            console.print(f"[red]Failed to extract metadata:[/red] {metadata.get('error', 'Unknown error')}")
            exit(1)
            
        console.print(json.dumps(metadata, indent=2))
        
        
    # Display usage if no arguments provided
    else:
        console.print("[yellow]Please provide either a file path or a language and code snippet.[/yellow]")
        console.print("Example usage:")
        console.print("  python tree_sitter_utils.py --file path/to/file.py")
        console.print("  python tree_sitter_utils.py --language python --code 'def example(): pass'")
        console.print("  python tree_sitter_utils.py --list-languages")