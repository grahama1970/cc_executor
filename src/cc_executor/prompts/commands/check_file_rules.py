#!/usr/bin/env python3
"""
check_file_rules.py - Verify Python files follow documentation and usage rules.

This script checks that Python files in the project follow the required rules:
1. Max 500 lines per file
2. Documentation header with third-party links
3. Example input and expected output
4. Usage function with real data validation

Third-party Documentation:
- Python AST module: https://docs.python.org/3/library/ast.html
- File I/O: https://docs.python.org/3/tutorial/inputoutput.html#reading-and-writing-files

Example Input:
    python check_file_rules.py /path/to/module.py

Expected Output:
    ✅ /path/to/module.py - All checks passed
    - Lines: 245/500 ✓
    - Documentation header: ✓
    - Third-party links: 3 found ✓
    - Example input section: ✓
    - Expected output section: ✓
    - Usage function: ✓
"""

import os
import sys
import ast
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class FileRuleChecker:
    """Check Python files against documentation and usage rules."""
    
    def __init__(self):
        self.max_lines = 500
        self.required_sections = [
            "Third-party Documentation:",
            "Example Input:",
            "Expected Output:"
        ]
        
    def check_file(self, filepath: str) -> Dict[str, any]:
        """
        Check a single Python file against all rules.
        
        Returns dict with check results.
        """
        results = {
            "filepath": filepath,
            "exists": False,
            "line_count": 0,
            "under_500_lines": False,
            "has_docstring": False,
            "has_third_party_links": False,
            "third_party_count": 0,
            "has_example_input": False,
            "has_expected_output": False,
            "has_usage_function": False,
            "errors": []
        }
        
        if not os.path.exists(filepath):
            results["errors"].append("File does not exist")
            return results
            
        results["exists"] = True
        
        try:
            with open(filepath, 'r') as f:
                content = f.read()
                lines = content.splitlines()
                
            # Check line count
            results["line_count"] = len(lines)
            results["under_500_lines"] = len(lines) <= self.max_lines
            
            # Parse AST
            tree = ast.parse(content)
            
            # Check for module docstring
            docstring = ast.get_docstring(tree)
            if docstring:
                results["has_docstring"] = True
                
                # Check for required sections
                results["has_third_party_links"] = "Third-party Documentation:" in docstring
                results["has_example_input"] = "Example Input:" in docstring
                results["has_expected_output"] = "Expected Output:" in docstring
                
                # Count third-party links
                link_pattern = r'https?://[^\s]+'
                links = re.findall(link_pattern, docstring)
                results["third_party_count"] = len(links)
                
            # Check for usage function (if __name__ == "__main__":)
            for node in ast.walk(tree):
                if isinstance(node, ast.If):
                    if (isinstance(node.test, ast.Compare) and
                        len(node.test.ops) == 1 and
                        isinstance(node.test.ops[0], ast.Eq) and
                        isinstance(node.test.left, ast.Name) and
                        node.test.left.id == "__name__" and
                        len(node.test.comparators) == 1 and
                        isinstance(node.test.comparators[0], ast.Constant) and
                        node.test.comparators[0].value == "__main__"):
                        results["has_usage_function"] = True
                        break
                        
        except Exception as e:
            results["errors"].append(f"Error parsing file: {e}")
            
        return results
        
    def check_directory(self, directory: str) -> List[Dict[str, any]]:
        """Check all Python files in a directory."""
        results = []
        
        for filepath in Path(directory).rglob("*.py"):
            # Skip __pycache__ and other generated files
            if "__pycache__" in str(filepath):
                continue
            if str(filepath).endswith(".pyc"):
                continue
                
            result = self.check_file(str(filepath))
            results.append(result)
            
        return results
        
    def print_results(self, results: Dict[str, any]) -> bool:
        """
        Print check results for a file.
        
        Returns True if all checks passed.
        """
        filepath = results["filepath"]
        all_passed = True
        
        if not results["exists"]:
            print(f"❌ {filepath} - File does not exist")
            return False
            
        # Check each rule
        checks = []
        
        # Line count
        if results["under_500_lines"]:
            checks.append(f"Lines: {results['line_count']}/500 ✓")
        else:
            checks.append(f"Lines: {results['line_count']}/500 ✗")
            all_passed = False
            
        # Documentation
        if results["has_docstring"]:
            checks.append("Documentation header: ✓")
        else:
            checks.append("Documentation header: ✗")
            all_passed = False
            
        # Third-party links
        if results["has_third_party_links"] and results["third_party_count"] > 0:
            checks.append(f"Third-party links: {results['third_party_count']} found ✓")
        else:
            checks.append("Third-party links: ✗")
            all_passed = False
            
        # Example sections
        if results["has_example_input"]:
            checks.append("Example input section: ✓")
        else:
            checks.append("Example input section: ✗")
            all_passed = False
            
        if results["has_expected_output"]:
            checks.append("Expected output section: ✓")
        else:
            checks.append("Expected output section: ✗")
            all_passed = False
            
        # Usage function
        if results["has_usage_function"]:
            checks.append("Usage function: ✓")
        else:
            checks.append("Usage function: ✗")
            all_passed = False
            
        # Print summary
        if all_passed:
            print(f"✅ {filepath} - All checks passed")
        else:
            print(f"❌ {filepath} - Some checks failed")
            
        for check in checks:
            print(f"  - {check}")
            
        if results["errors"]:
            print("  Errors:")
            for error in results["errors"]:
                print(f"    - {error}")
                
        return all_passed


def main():
    """Check file rules for Python files."""
    checker = FileRuleChecker()
    
    if len(sys.argv) < 2:
        # Default to checking core directory
        directory = "/home/graham/workspace/experiments/cc_executor/src/cc_executor/core"
        print(f"Checking all Python files in: {directory}\n")
        
        results = checker.check_directory(directory)
        all_passed = True
        
        for result in results:
            passed = checker.print_results(result)
            if not passed:
                all_passed = False
            print()
            
        # Summary
        total = len(results)
        passed = sum(1 for r in results if all([
            r["under_500_lines"], r["has_docstring"], 
            r["has_third_party_links"], r["has_example_input"],
            r["has_expected_output"], r["has_usage_function"]
        ]))
        
        print(f"\nSummary: {passed}/{total} files pass all checks")
        return 0 if all_passed else 1
        
    else:
        # Check specific file
        filepath = sys.argv[1]
        result = checker.check_file(filepath)
        passed = checker.print_results(result)
        return 0 if passed else 1


if __name__ == "__main__":
    """Usage example: Check rules for this file and core modules."""
    
    print("=== Self-Test: Checking this file ===")
    checker = FileRuleChecker()
    
    # Check this file
    this_file = __file__
    result = checker.check_file(this_file)
    passed = checker.print_results(result)
    
    print(f"\nSelf-test result: {'PASSED' if passed else 'FAILED'}")
    
    # Also run main if called directly
    print("\n=== Checking Core Modules ===")
    sys.exit(main())