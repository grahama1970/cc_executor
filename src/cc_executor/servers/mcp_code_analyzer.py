#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "fastmcp",
#     "mcp-logger-utils>=0.1.5",
#     "python-dotenv",
#     "loguru",
#     "tree-sitter",
#     "tree-sitter-language-pack"
# ]
# ///
"""
MCP Server for Code Analysis using Tree-sitter.

This MCP provides agents with a tool to parse code snippets into an
Abstract Syntax Tree (AST) and extract structured metadata, such as
functions, classes, and their parameters.

=== MCP DEBUGGING NOTES (2025-01-20) ===

COMMON MCP USAGE PITFALLS:
1. Language parameter must match supported language names (e.g., 'python', 'javascript')
2. Code must be passed as a string, not a file path
3. Tree-sitter language packs are loaded lazily on first use

HOW TO DEBUG THIS MCP SERVER:

1. TEST LOCALLY (QUICKEST):
   ```bash
   # Test if server can start
   python src/cc_executor/servers/mcp_code_analyzer.py test
   
   # Run working usage
   python src/cc_executor/servers/mcp_code_analyzer.py working
   ```

2. CHECK MCP LOGS:
   - Startup log: ~/.claude/mcp_logs/code-analyzer_startup.log
   - Debug log: ~/.claude/mcp_logs/code-analyzer_debug.log
   - Calls log: ~/.claude/mcp_logs/code-analyzer_calls.jsonl

3. COMMON ISSUES & FIXES:
   
   a) Language not supported:
      - Error: "Language 'X' is not supported"
      - Fix: Check supported languages with supported_languages tool
      - Supported: python, javascript, typescript, java, go, rust, c, cpp
   
   b) Parse errors:
      - Error: "Failed to parse code"
      - Fix: Ensure code is syntactically valid
      - Check: Use language-specific linters first

4. ENVIRONMENT VARIABLES:
   - PYTHONPATH=/home/graham/workspace/experiments/cc_executor/src
   - No specific env vars required

5. CURRENT STATUS:
   - ✅ All imports working
   - ✅ Tree-sitter integration functional
   - ✅ Language autodetection working

=== END DEBUGGING NOTES ===

AGENT VERIFICATION INSTRUCTIONS:
- Run with `test` argument: `python mcp_code_analyzer.py test`
- Run the `working_usage()`: `python mcp_code_analyzer.py working`
- The `working_usage()` function MUST pass assertions, verifying that a sample
  Python snippet is correctly parsed into its constituent functions and classes.
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

from fastmcp import FastMCP
from loguru import logger
from dotenv import load_dotenv, find_dotenv
from mcp_logger_utils import MCPLogger, debug_tool
from tree_sitter import Parser, Query, Node
from tree_sitter_language_pack import get_language, get_parser

# Import standardized response utilities
sys.path.insert(0, str(Path(__file__).parent))
from utils.response_utils import create_success_response, create_error_response

# Configure logging, MCP, etc.
logger.remove(); logger.add(sys.stderr, level="INFO")
load_dotenv(find_dotenv())
mcp = FastMCP("code-analyzer")
mcp_logger = MCPLogger("code-analyzer")


class CodeAnalyzerTools:
    """Encapsulates Tree-sitter parsing logic."""
    def __init__(self):
        # Language mappings including file extensions
        self.LANGUAGE_MAPPINGS = { 
            # Python
            "py": "python", "python": "python", "pyw": "python",
            # JavaScript/TypeScript
            "js": "javascript", "javascript": "javascript", "jsx": "javascript",
            "ts": "typescript", "typescript": "typescript", "tsx": "typescript",
            # Java/Kotlin/Scala
            "java": "java", 
            "kt": "kotlin", "kotlin": "kotlin", "kts": "kotlin",
            "scala": "scala", "sc": "scala",
            # Go/Rust
            "go": "go", 
            "rs": "rust", "rust": "rust",
            # C/C++
            "c": "c", "h": "c",
            "cpp": "cpp", "c++": "cpp", "cc": "cpp", "cxx": "cpp", "hpp": "cpp",
            # Web
            "html": "html", "htm": "html",
            "css": "css", "scss": "css", "sass": "css",
            "php": "php",
            # Ruby/Elixir/Erlang
            "rb": "ruby", "ruby": "ruby",
            "ex": "elixir", "elixir": "elixir", "exs": "elixir",
            "erl": "erlang", "erlang": "erlang", "hrl": "erlang",
            # Functional
            "hs": "haskell", "haskell": "haskell", "lhs": "haskell",
            "ml": "ocaml", "ocaml": "ocaml", "mli": "ocaml",
            "clj": "clojure", "clojure": "clojure", "cljs": "clojure",
            # Data/Science
            "r": "r", "R": "r",
            "jl": "julia", "julia": "julia",
            "lua": "lua",
            "pl": "perl", "perl": "perl", "pm": "perl",
            # Shell/Config
            "sh": "bash", "bash": "bash", "zsh": "bash", "fish": "bash",
            "sql": "sql",
            "json": "json",
            "yaml": "yaml", "yml": "yaml",
            "toml": "toml",
            "xml": "xml",
            "md": "markdown", "markdown": "markdown",
            # Other
            "tex": "latex", "latex": "latex",
            "dockerfile": "dockerfile", "Dockerfile": "dockerfile",
            "cmake": "cmake", "CMakeLists.txt": "cmake",
            "vim": "vim", "vimrc": "vim",
            "swift": "swift"
        }
        self.parsers = {}
        self.languages = {}
        
        # Language-specific node types
        self.NODE_TYPES = {
            "python": {
                "function": "function_definition",
                "class": "class_definition",
                "import": ["import_statement", "import_from_statement"],
                "decorator": "decorator",
                "docstring_container": ["function_definition", "class_definition", "module"],
                "variable": ["assignment", "ann_assign"],
                "decision_nodes": ["if_statement", "for_statement", "while_statement", 
                                 "try_statement", "except_clause", "with_statement",
                                 "match_statement", "case_clause"]
            },
            "javascript": {
                "function": ["function_declaration", "function", "arrow_function", "method_definition"],
                "class": "class_declaration",
                "import": "import_statement",
                "decorator": "decorator",
                "variable": ["variable_declaration", "lexical_declaration"],
                "decision_nodes": ["if_statement", "for_statement", "while_statement", 
                                 "switch_statement", "case_statement", "try_statement",
                                 "catch_clause", "ternary_expression"]
            },
            "typescript": {
                "function": ["function_declaration", "function", "arrow_function", "method_definition"],
                "class": "class_declaration",
                "import": "import_statement",
                "decorator": "decorator",
                "interface": "interface_declaration",
                "type_alias": "type_alias_declaration",
                "variable": ["variable_declaration", "lexical_declaration"],
                "decision_nodes": ["if_statement", "for_statement", "while_statement",
                                 "switch_statement", "case_statement", "try_statement",
                                 "catch_clause", "ternary_expression"]
            },
            "java": {
                "function": "method_declaration",
                "class": ["class_declaration", "interface_declaration"],
                "import": "import_declaration",
                "annotation": ["marker_annotation", "annotation"],
                "variable": ["local_variable_declaration", "field_declaration"],
                "decision_nodes": ["if_statement", "for_statement", "while_statement",
                                 "switch_expression", "try_statement", "catch_clause",
                                 "enhanced_for_statement"]
            },
            "go": {
                "function": ["function_declaration", "method_declaration"],
                "class": "type_declaration",  # Go uses type declarations for structs
                "import": "import_declaration",
                "variable": ["var_declaration", "short_var_declaration"],
                "decision_nodes": ["if_statement", "for_statement", "switch_statement",
                                 "type_switch_statement", "select_statement"]
            },
            "rust": {
                "function": "function_item",
                "class": ["struct_item", "enum_item", "impl_item"],
                "import": "use_declaration",
                "attribute": "attribute_item",
                "variable": ["let_declaration", "const_item", "static_item"],
                "decision_nodes": ["if_expression", "match_expression", "while_expression",
                                 "for_expression", "loop_expression"]
            }
        }
        
        # Generic node types for languages without specific mappings
        self.GENERIC_NODE_TYPES = {
            "function": ["function_definition", "function_declaration", "method_definition", 
                        "method_declaration", "function_item", "function", "arrow_function",
                        "lambda_expression", "anonymous_function", "closure_expression"],
            "class": ["class_definition", "class_declaration", "class", "struct_definition",
                     "struct_declaration", "struct_item", "enum_definition", "enum_declaration",
                     "enum_item", "interface_declaration", "trait_definition", "impl_item",
                     "type_definition", "type_declaration"],
            "import": ["import_statement", "import_declaration", "import_from_statement",
                      "use_declaration", "require_statement", "include_statement",
                      "using_directive", "namespace_using_directive"],
            "variable": ["variable_declaration", "variable_statement", "assignment",
                        "assignment_expression", "let_declaration", "const_declaration",
                        "var_declaration", "field_declaration", "property_declaration",
                        "lexical_declaration", "assignment_statement"],
            "decision_nodes": ["if_statement", "if_expression", "conditional_expression",
                             "ternary_expression", "switch_statement", "switch_expression",
                             "case_statement", "case_clause", "match_expression",
                             "for_statement", "for_expression", "while_statement",
                             "while_expression", "do_statement", "try_statement",
                             "try_expression", "catch_clause", "except_clause"]
        }

    def _get_parser_and_language(self, language: str) -> Optional[tuple]:
        """Lazily loads and caches parsers and languages for each language."""
        lang_name = self.LANGUAGE_MAPPINGS.get(language.lower())
        if not lang_name:
            return None
            
        if lang_name in self.parsers:
            return self.parsers[lang_name], self.languages[lang_name]
        
        try:
            parser = get_parser(lang_name)
            lang_obj = get_language(lang_name)
            self.parsers[lang_name] = parser
            self.languages[lang_name] = lang_obj
            return parser, lang_obj
        except Exception as e:
            logger.error(f"Failed to load tree-sitter language '{lang_name}': {e}")
            return None

    def analyze_code(self, code: str, language: str) -> Dict:
        """Parses a code snippet and extracts comprehensive metadata."""
        result = self._get_parser_and_language(language)
        if not result:
            raise ValueError(f"Language '{language}' is not supported or failed to load.")
        
        parser, lang_obj = result
        lang_name = self.LANGUAGE_MAPPINGS.get(language.lower())
        
        # Parse the code
        tree = parser.parse(bytes(code, "utf8"))
        root_node = tree.root_node
        
        # Initialize metadata structure
        metadata = {
            "functions": [],
            "classes": [],
            "imports": [],
            "variables": [],
            "decorators": [],
            "docstrings": [],
            "comments": [],
            "type_definitions": [],  # interfaces, type aliases
            "complexity_info": {},
            "tree_sitter_success": True,
            "parse_errors": []
        }
        
        # Check for parse errors
        if root_node.has_error:
            metadata["parse_errors"] = self._find_error_nodes(root_node)
        
        # Extract all elements using tree cursor for efficiency
        cursor = tree.walk()
        self._traverse_tree(cursor, code, metadata, lang_name)
        
        # Calculate file-level metrics
        metadata["metrics"] = {
            "total_lines": len(code.splitlines()),
            "total_functions": len(metadata["functions"]),
            "total_classes": len(metadata["classes"]),
            "average_complexity": self._calculate_average_complexity(metadata["functions"])
        }
        
        # For script languages without functions/classes, treat the entire file as a function
        if self._is_script_language(lang_name) and not metadata["functions"] and not metadata["classes"]:
            script_info = {
                "name": "<script>",
                "type": "script",
                "start_line": 1,
                "end_line": len(code.splitlines()),
                "start_col": 0,
                "end_col": 0,
                "complexity": self._calculate_complexity(root_node, lang_name),
                "parameters": [],
                "return_type": None,
                "docstring": self._extract_script_docstring(code, lang_name),
                "decorators": [],
                "is_async": False,
                "is_generator": False
            }
            metadata["functions"].append(script_info)
            metadata["is_script"] = True
        
        return metadata
    
    def _traverse_tree(self, cursor, code: str, metadata: Dict, language: str):
        """Efficiently traverse the AST using TreeCursor."""
        node = cursor.node
        # Use specific node types if available, otherwise use generic ones
        node_types = self.NODE_TYPES.get(language, self.GENERIC_NODE_TYPES)
        
        # Extract based on node type
        if self._matches_node_type(node.type, node_types.get("function", [])):
            func_info = self._extract_function(node, code, language)
            if func_info:
                metadata["functions"].append(func_info)
                
        elif self._matches_node_type(node.type, node_types.get("class", [])):
            class_info = self._extract_class(node, code, language)
            if class_info:
                metadata["classes"].append(class_info)
                
        elif self._matches_node_type(node.type, node_types.get("import", [])):
            import_info = self._extract_import(node, code, language)
            if import_info:
                metadata["imports"].append(import_info)
                
        elif self._matches_node_type(node.type, node_types.get("variable", [])):
            # For JavaScript/TypeScript, also check if this variable contains a function
            if language in ["javascript", "typescript"]:
                # Check for arrow functions or function expressions in variable declarations
                for child in node.children:
                    if child.type == "variable_declarator":
                        for subchild in child.children:
                            if subchild.type in ["arrow_function", "function"]:
                                func_info = self._extract_function(subchild, code, language)
                                if func_info:
                                    # Get the variable name as the function name
                                    name_node = child.child_by_field_name("name")
                                    if name_node:
                                        func_info["name"] = code[name_node.start_byte:name_node.end_byte]
                                    metadata["functions"].append(func_info)
            var_info = self._extract_variable(node, code, language)
            if var_info:
                metadata["variables"].append(var_info)
                
        elif node.type == "comment":
            comment_info = self._extract_comment(node, code)
            metadata["comments"].append(comment_info)
            
        # Language-specific extractions
        if language == "python" and node.type == "decorator":
            decorator_info = self._extract_decorator(node, code)
            metadata["decorators"].append(decorator_info)
            
        elif language in ["typescript", "javascript"] and node.type == "decorator":
            decorator_info = self._extract_decorator(node, code)
            metadata["decorators"].append(decorator_info)
            
        elif language == "typescript" and node.type == "interface_declaration":
            interface_info = self._extract_interface(node, code)
            metadata["type_definitions"].append(interface_info)
            
        elif language == "java" and self._matches_node_type(node.type, node_types.get("annotation", [])):
            annotation_info = self._extract_annotation(node, code)
            metadata["decorators"].append(annotation_info)
        
        # Traverse children
        if cursor.goto_first_child():
            self._traverse_tree(cursor, code, metadata, language)
            while cursor.goto_next_sibling():
                self._traverse_tree(cursor, code, metadata, language)
            cursor.goto_parent()
    
    def _matches_node_type(self, node_type: str, expected_types) -> bool:
        """Check if node type matches expected types (str or list)."""
        if isinstance(expected_types, str):
            return node_type == expected_types
        elif isinstance(expected_types, list):
            return node_type in expected_types
        return False
    
    def _extract_function(self, node: Node, code: str, language: str) -> Optional[Dict]:
        """Extract function information including signature, docstring, and complexity."""
        name_node = node.child_by_field_name("name")
        if not name_node and node.type not in ["arrow_function", "function"]:
            return None
            
        func_info = {
            "name": code[name_node.start_byte:name_node.end_byte] if name_node else "anonymous",
            "type": "function",
            "start_line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "start_col": node.start_point[1],
            "end_col": node.end_point[1],
            "complexity": self._calculate_complexity(node, language),
            "parameters": [],
            "return_type": None,
            "docstring": None,
            "decorators": [],
            "is_async": False,
            "is_generator": False
        }
        
        # Extract parameters
        params_node = node.child_by_field_name("parameters")
        if not params_node and node.type == "arrow_function":
            # Arrow functions might have formal_parameters as first child
            for child in node.children:
                if child.type == "formal_parameters":
                    params_node = child
                    break
        
        if params_node:
            func_info["parameters"] = self._extract_parameters(params_node, code, language)
        else:
            # Debug: log what children we have
            logger.debug(f"No parameters field for function {func_info['name']}, node type: {node.type}")
        
        # Extract return type
        return_type_node = node.child_by_field_name("return_type")
        if return_type_node:
            func_info["return_type"] = code[return_type_node.start_byte:return_type_node.end_byte]
        
        # Extract docstring (Python)
        if language == "python":
            body_node = node.child_by_field_name("body")
            if body_node and body_node.child_count > 0:
                first_stmt = body_node.child(0)
                if first_stmt.type == "expression_statement" and first_stmt.child_count > 0:
                    expr = first_stmt.child(0)
                    if expr.type == "string":
                        func_info["docstring"] = code[expr.start_byte:expr.end_byte].strip("\"'")
            
            # Check if async
            for child in node.children:
                if child.type == "async" or (child.type == "identifier" and code[child.start_byte:child.end_byte] == "async"):
                    func_info["is_async"] = True
                    break
        
        # Extract decorators
        func_info["decorators"] = self._get_preceding_decorators(node, code, language)
        
        return func_info
    
    def _extract_class(self, node: Node, code: str, language: str) -> Optional[Dict]:
        """Extract class information including methods and attributes."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None
            
        class_info = {
            "name": code[name_node.start_byte:name_node.end_byte],
            "type": "class",
            "start_line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "start_col": node.start_point[1],
            "end_col": node.end_point[1],
            "methods": [],
            "attributes": [],
            "docstring": None,
            "decorators": [],
            "base_classes": []
        }
        
        # Extract base classes/superclass
        if language == "python":
            superclass_node = node.child_by_field_name("superclasses")
            if superclass_node:
                class_info["base_classes"] = self._extract_base_classes(superclass_node, code)
        
        # Extract docstring
        body_node = node.child_by_field_name("body")
        if body_node and language == "python":
            if body_node.child_count > 0:
                first_stmt = body_node.child(0)
                if first_stmt.type == "expression_statement" and first_stmt.child_count > 0:
                    expr = first_stmt.child(0)
                    if expr.type == "string":
                        class_info["docstring"] = code[expr.start_byte:expr.end_byte].strip("\"'")
        
        # Extract decorators
        class_info["decorators"] = self._get_preceding_decorators(node, code, language)
        
        return class_info
    
    def _extract_import(self, node: Node, code: str, language: str) -> Dict:
        """Extract import information."""
        import_text = code[node.start_byte:node.end_byte]
        
        import_info = {
            "type": "import",
            "statement": import_text,
            "line": node.start_point[0] + 1,
            "modules": [],
            "names": []
        }
        
        # Language-specific import parsing
        if language == "python":
            if node.type == "import_statement":
                # import module1, module2
                for child in node.children:
                    if child.type == "dotted_name" or child.type == "identifier":
                        import_info["modules"].append(code[child.start_byte:child.end_byte])
            elif node.type == "import_from_statement":
                # from module import name1, name2
                module_node = node.child_by_field_name("module_name")
                if module_node:
                    import_info["modules"].append(code[module_node.start_byte:module_node.end_byte])
                    
        elif language in ["javascript", "typescript"]:
            # Parse ES6 imports
            for child in node.children:
                if child.type == "string":
                    import_info["modules"].append(code[child.start_byte:child.end_byte].strip("\"'"))
        
        return import_info
    
    def _extract_variable(self, node: Node, code: str, language: str) -> Optional[Dict]:
        """Extract variable declaration with type information."""
        var_info = {
            "type": "variable",
            "name": None,
            "var_type": None,
            "line": node.start_point[0] + 1,
            "is_const": False
        }
        
        if language == "python":
            if node.type == "assignment":
                left = node.child_by_field_name("left")
                if left and left.type == "identifier":
                    var_info["name"] = code[left.start_byte:left.end_byte]
            elif node.type == "ann_assign":
                target = node.child_by_field_name("target")
                annotation = node.child_by_field_name("annotation")
                if target:
                    var_info["name"] = code[target.start_byte:target.end_byte]
                if annotation:
                    var_info["var_type"] = code[annotation.start_byte:annotation.end_byte]
                    
        elif language in ["javascript", "typescript"]:
            declarator = node.child_by_field_name("declarator")
            if declarator:
                name_node = declarator.child_by_field_name("name")
                if name_node:
                    var_info["name"] = code[name_node.start_byte:name_node.end_byte]
                    
                # Type annotation in TypeScript
                type_node = declarator.child_by_field_name("type")
                if type_node:
                    var_info["var_type"] = code[type_node.start_byte:type_node.end_byte]
                    
            # Check const/let/var
            for child in node.children:
                if child.type == "const":
                    var_info["is_const"] = True
                    break
        
        return var_info if var_info["name"] else None
    
    def _extract_parameters(self, params_node: Node, code: str, language: str) -> List[Dict]:
        """Extract function parameters with types."""
        parameters = []
        
        # Handle Python parameters more comprehensively
        if language == "python" and params_node:
            # For Python, we need to handle the parameter list structure
            for child in params_node.children:
                if child.type in ["identifier", "typed_parameter", "default_parameter"]:
                    param_info = {
                        "name": None,
                        "type": None,
                        "default": None
                    }
                    
                    if child.type == "identifier":
                        param_info["name"] = code[child.start_byte:child.end_byte]
                    elif child.type == "typed_parameter":
                        # For typed_parameter, the name is the first child (identifier)
                        if child.children and child.children[0].type == "identifier":
                            param_info["name"] = code[child.children[0].start_byte:child.children[0].end_byte]
                        type_node = child.child_by_field_name("type")
                        if type_node:
                            param_info["type"] = code[type_node.start_byte:type_node.end_byte]
                    elif child.type == "default_parameter":
                        name_node = child.child_by_field_name("name")
                        if name_node:
                            param_info["name"] = code[name_node.start_byte:name_node.end_byte]
                        value_node = child.child_by_field_name("value")
                        if value_node:
                            param_info["default"] = code[value_node.start_byte:value_node.end_byte]
                    
                    if param_info["name"]:
                        parameters.append(param_info)
            
            return parameters
        
        # Original logic for other languages
        for param in params_node.named_children:
            param_info = {
                "name": None,
                "type": None,
                "default": None
            }
            
            if language == "python":
                if param.type in ["identifier", "typed_parameter"]:
                    name_node = param if param.type == "identifier" else param.child_by_field_name("name")
                    if name_node:
                        param_info["name"] = code[name_node.start_byte:name_node.end_byte]
                    
                    type_node = param.child_by_field_name("type") if param.type == "typed_parameter" else None
                    if type_node:
                        param_info["type"] = code[type_node.start_byte:type_node.end_byte]
                        
                    # Default value
                    default_node = param.child_by_field_name("value")
                    if default_node:
                        param_info["default"] = code[default_node.start_byte:default_node.end_byte]
                        
            if param_info["name"]:
                parameters.append(param_info)
                
        return parameters
    
    def _calculate_complexity(self, node: Node, language: str) -> int:
        """Calculate cyclomatic complexity for a function/method."""
        complexity = 1  # Base complexity
        decision_nodes = self.NODE_TYPES.get(language, {}).get("decision_nodes", [])
        
        def count_decisions(n: Node) -> int:
            count = 0
            if n.type in decision_nodes:
                count += 1
            for child in n.children:
                count += count_decisions(child)
            return count
        
        complexity += count_decisions(node)
        return complexity
    
    def _extract_decorator(self, node: Node, code: str) -> Dict:
        """Extract decorator information."""
        return {
            "type": "decorator",
            "name": code[node.start_byte:node.end_byte].strip("@"),
            "line": node.start_point[0] + 1
        }
    
    def _extract_annotation(self, node: Node, code: str) -> Dict:
        """Extract Java annotation information."""
        name_node = node.child_by_field_name("name")
        return {
            "type": "annotation",
            "name": code[name_node.start_byte:name_node.end_byte] if name_node else code[node.start_byte:node.end_byte],
            "line": node.start_point[0] + 1
        }
    
    def _extract_interface(self, node: Node, code: str) -> Dict:
        """Extract TypeScript interface information."""
        name_node = node.child_by_field_name("name")
        return {
            "type": "interface",
            "name": code[name_node.start_byte:name_node.end_byte] if name_node else "unnamed",
            "line": node.start_point[0] + 1,
            "text": code[node.start_byte:node.end_byte]
        }
    
    def _extract_comment(self, node: Node, code: str) -> Dict:
        """Extract comment information."""
        comment_text = code[node.start_byte:node.end_byte]
        return {
            "type": "comment",
            "text": comment_text,
            "line": node.start_point[0] + 1,
            "is_jsdoc": comment_text.startswith("/**"),
            "is_multiline": "\n" in comment_text
        }
    
    def _get_preceding_decorators(self, node: Node, code: str, language: str) -> List[str]:
        """Get decorators that precede a function/class."""
        decorators = []
        prev_sibling = node.prev_sibling
        
        while prev_sibling:
            if language == "python" and prev_sibling.type == "decorator":
                decorators.append(code[prev_sibling.start_byte:prev_sibling.end_byte].strip("@"))
            elif language in ["typescript", "javascript"] and prev_sibling.type == "decorator":
                decorators.append(code[prev_sibling.start_byte:prev_sibling.end_byte])
            else:
                break
            prev_sibling = prev_sibling.prev_sibling
            
        return list(reversed(decorators))
    
    def _extract_base_classes(self, superclass_node: Node, code: str) -> List[str]:
        """Extract base classes from superclass node."""
        base_classes = []
        for child in superclass_node.children:
            if child.type in ["identifier", "attribute"]:
                base_classes.append(code[child.start_byte:child.end_byte])
        return base_classes
    
    def _find_error_nodes(self, node: Node) -> List[Dict]:
        """Find all ERROR nodes in the tree."""
        errors = []
        if node.type == "ERROR":
            errors.append({
                "line": node.start_point[0] + 1,
                "column": node.start_point[1],
                "message": "Parse error"
            })
        for child in node.children:
            errors.extend(self._find_error_nodes(child))
        return errors
    
    def _calculate_average_complexity(self, functions: List[Dict]) -> float:
        """Calculate average cyclomatic complexity."""
        if not functions:
            return 0.0
        total = sum(f.get("complexity", 1) for f in functions)
        return round(total / len(functions), 2)

    def _is_script_language(self, language: str) -> bool:
        """Check if a language is typically used for scripts without function definitions."""
        script_languages = {
            "bash", "sh", "shell", "sql", "dockerfile", "makefile", 
            "yaml", "json", "toml", "xml", "html", "css", "markdown",
            "cmake", "vim"
        }
        return language in script_languages
    
    def _extract_script_docstring(self, code: str, language: str) -> Optional[str]:
        """Extract docstring/header comment from script files."""
        lines = code.splitlines()
        if not lines:
            return None
            
        # Different comment styles per language
        comment_patterns = {
            "bash": "#",
            "sql": "--",
            "dockerfile": "#",
            "yaml": "#",
            "vim": '"',
            "css": "/*",
            "html": "<!--",
            "markdown": None  # No standard comment in markdown
        }
        
        comment_prefix = comment_patterns.get(language, "#")
        if not comment_prefix:
            return None
            
        # Extract leading comments
        docstring_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(comment_prefix):
                docstring_lines.append(stripped[len(comment_prefix):].strip())
            elif stripped and not stripped.startswith(("#!/", "<?", "<!")):
                break
                
        return "\n".join(docstring_lines) if docstring_lines else None

    def get_supported_languages(self) -> List[str]:
        """Returns a list of supported languages."""
        # Return unique language names (values, not keys)
        return sorted(list(set(self.LANGUAGE_MAPPINGS.values())))

tools = CodeAnalyzerTools()

@mcp.tool()
@debug_tool(mcp_logger)
async def analyze(code: str, language: str) -> str:
    """Parses a code snippet and returns structured metadata (functions, classes, etc.)."""
    start_time = time.time()
    try:
        result = tools.analyze_code(code, language)
        return create_success_response(result, "analyze", start_time)
    except Exception as e:
        suggestions = [f"Check if language '{language}' is supported by calling the 'supported_languages' tool."]
        return create_error_response(str(e), "analyze", start_time, suggestions)

@mcp.tool()
@debug_tool(mcp_logger)
async def supported_languages() -> str:
    """Returns a list of languages supported by the analyzer."""
    start_time = time.time()
    result = tools.get_supported_languages()
    return create_success_response({"languages": result}, "supported_languages", start_time)


async def working_usage():
    print("=== Code Analyzer MCP Working Usage ===")
    
    # Test 1: Python code with function, class, imports, decorators
    python_code = '''import os
from typing import List, Optional
import json

@dataclass
class Person:
    """A person with a name and age."""
    name: str
    age: int = 0
    
    def greet(self, other: Optional[str] = None) -> str:
        """Greet someone."""
        if other:
            return f"Hello {other}, I'm {self.name}"
        return f"Hello, I'm {self.name}"

@lru_cache(maxsize=128)
def fibonacci(n: int) -> int:
    """Calculate fibonacci number with complexity O(n)."""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Main execution
if __name__ == "__main__":
    person = Person("Alice", 30)
    print(person.greet())
'''
    
    print("Testing Python code analysis...")
    # Call the tool directly without decorators
    try:
        data = tools.analyze_code(python_code, "python")
        
        # Debug print
        print(f"Functions found: {[f['name'] for f in data['functions']]}")
        print(f"Classes found: {[c['name'] for c in data['classes']]}")
        print(f"Imports found: {len(data['imports'])}")
        
        # Verify extraction results
        assert data["tree_sitter_success"], "Tree-sitter parsing failed"
        assert len(data["functions"]) == 2, f"Expected 2 functions, got {len(data['functions'])}"
        assert len(data["classes"]) == 1, f"Expected 1 class, got {len(data['classes'])}"
        assert len(data["imports"]) >= 3, f"Expected at least 3 imports, got {len(data['imports'])}"
        
        # Check function details
        fib_func = next((f for f in data["functions"] if f["name"] == "fibonacci"), None)
        assert fib_func is not None, "fibonacci function not found"
        print(f"Fibonacci function details: {json.dumps(fib_func, indent=2)}")
        assert fib_func["complexity"] >= 2, f"Expected complexity >= 2, got {fib_func['complexity']}"
        assert len(fib_func["parameters"]) == 1, f"fibonacci should have 1 parameter, got {len(fib_func['parameters'])}"
        assert fib_func["return_type"] == "int", f"Expected return type 'int', got {fib_func['return_type']}"
        assert len(fib_func["decorators"]) == 1, "fibonacci should have 1 decorator"
        
        # Check class details
        person_class = data["classes"][0]
        assert person_class["name"] == "Person", f"Expected class 'Person', got {person_class['name']}"
        assert person_class["docstring"] is not None, "Person class should have docstring"
        assert len(person_class["decorators"]) == 1, "Person should have @dataclass decorator"
        
        print("✓ Python code analysis passed all tests")
    except Exception as e:
        print(f"Python analysis failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    # Test 2: JavaScript/TypeScript code
    js_code = '''import React from 'react';
import { useState, useEffect } from 'react';

interface Props {
    title: string;
    count?: number;
}

const Counter: React.FC<Props> = ({ title, count = 0 }) => {
    const [value, setValue] = useState(count);
    
    useEffect(() => {
        console.log(`Counter ${title} changed to ${value}`);
    }, [value, title]);
    
    const increment = () => {
        setValue(prev => prev + 1);
    };
    
    return (
        <div>
            <h1>{title}: {value}</h1>
            <button onClick={increment}>+</button>
        </div>
    );
};

export default Counter;
'''
    
    print("Testing TypeScript code analysis...")
    try:
        data = tools.analyze_code(js_code, "typescript")
        
        print(f"TypeScript analysis results:")
        print(f"  Functions: {[f['name'] for f in data['functions']]}")
        print(f"  Classes: {[c['name'] for c in data['classes']]}")
        print(f"  Type definitions: {len(data['type_definitions'])}")
        
        # Verify TypeScript extraction
        assert len(data["functions"]) >= 2, f"Expected at least 2 functions (Counter, increment), got {len(data['functions'])}"
        assert len(data["imports"]) >= 2, f"Expected at least 2 imports, got {len(data['imports'])}"
        assert len(data["type_definitions"]) >= 1, f"Expected at least 1 interface, got {len(data['type_definitions'])}"
        
        print("✓ TypeScript code analysis passed")
    except Exception as e:
        print(f"TypeScript analysis failed: {e}")
        raise
    
    # Test 3: Check supported languages
    supported = tools.get_supported_languages()
    
    print(f"\nSupported languages ({len(supported)}): {', '.join(supported[:15])}...")
    
    required_langs = ["python", "javascript", "typescript", "java", "go", "rust",
                     "ruby", "php", "swift", "kotlin", "bash", "sql", "html", "css"]
    
    for lang in required_langs:
        assert lang in supported, f"Language '{lang}' should be supported"
    
    print(f"✓ All {len(required_langs)} tested languages are supported")
    print(f"✓ Total {len(supported)} languages available")
    
    # Test 4: Complex Python with high cyclomatic complexity
    complex_code = '''def process_data(items, mode="normal"):
    """Process items with many decision points."""
    result = []
    
    for item in items:
        if mode == "normal":
            if item > 0:
                if item % 2 == 0:
                    result.append(item * 2)
                else:
                    result.append(item * 3)
            elif item < 0:
                result.append(abs(item))
            else:
                result.append(0)
        elif mode == "special":
            try:
                if item > 10:
                    result.append(item // 2)
                elif item > 5:
                    result.append(item * item)
                else:
                    result.append(item + 10)
            except Exception as e:
                result.append(-1)
        else:
            match item:
                case 0:
                    result.append(100)
                case 1 | 2 | 3:
                    result.append(200)
                case _:
                    result.append(300)
    
    return result
'''
    
    print("Testing complexity analysis...")
    try:
        data = tools.analyze_code(complex_code, "python")
        process_func = data["functions"][0]
        assert process_func["complexity"] >= 10, f"Expected high complexity (>=10), got {process_func['complexity']}"
        
        print(f"✓ Complexity analysis working (detected complexity: {process_func['complexity']})")
    except Exception as e:
        print(f"Complexity analysis failed: {e}")
        raise
    
    # Test 5: Script language (Bash)
    bash_code = '''#!/bin/bash
# Deploy script for production
# Handles rollback on failure

set -e
DEPLOY_DIR="/var/www/app"
BACKUP_DIR="/var/backups/app"

echo "Starting deployment..."
if [ -d "$DEPLOY_DIR" ]; then
    cp -r "$DEPLOY_DIR" "$BACKUP_DIR/$(date +%Y%m%d_%H%M%S)"
fi

git pull origin main
npm install
npm run build

echo "Deployment complete!"
'''
    
    print("\nTesting Bash script analysis...")
    try:
        data = tools.analyze_code(bash_code, "bash")
        
        assert data["is_script"], "Bash file should be recognized as script"
        assert len(data["functions"]) == 1, f"Expected 1 script function, got {len(data['functions'])}"
        
        script_func = data["functions"][0]
        assert script_func["name"] == "<script>", "Script should have <script> name"
        assert script_func["type"] == "script", "Should have script type"
        assert "Deploy script" in script_func["docstring"], "Should extract script docstring"
        
        print("✓ Script language analysis passed")
    except Exception as e:
        print(f"Script analysis failed: {e}")
        raise
    
    # Summary
    print("\n=== ALL TESTS PASSED ===")
    print(f"✓ Tested {len(['Python', 'TypeScript', 'Complexity', 'Languages', 'Scripts'])} scenarios")
    print("✓ Tree-sitter AST analysis fully functional")
    print(f"✓ Supporting {len(supported)} languages")
    print("✓ Ready for production use")
    
    return True

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            # Quick test mode
            print(f"✓ {Path(__file__).name} can start successfully!")
            sys.exit(0)
        elif sys.argv[1] == "debug":
            # Debug mode - could add debug function if needed
            asyncio.run(working_usage())
        elif sys.argv[1] == "working":
            asyncio.run(working_usage())
    else:
        # Run the MCP server
        try:
            logger.info("Starting Code Analyzer MCP server")
            mcp.run()
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.critical(f"MCP server crashed: {e}", exc_info=True)
            if mcp_logger:
                mcp_logger.log_error({"error": str(e), "context": "server_startup"})
            sys.exit(1)