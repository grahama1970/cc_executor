#!/usr/bin/env python3
"""
Comprehensive MCP Server Debugging Framework

This tool systematically tests all MCP servers and captures ALL errors,
including import failures that don't make it to the MCP logs.
"""

import json
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import time

# Colors for output
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

class MCPDebugger:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.mcp_config_path = Path.home() / ".claude" / "claude_code" / ".mcp.json"
        self.debug_report_path = self.project_root / "tmp" / "mcp_debug_report.json"
        self.debug_log_path = self.project_root / "tmp" / "mcp_debug.log"
        
        # Ensure tmp directory exists
        (self.project_root / "tmp").mkdir(exist_ok=True)
        
    def load_mcp_config(self) -> Dict:
        """Load the MCP configuration."""
        with open(self.mcp_config_path) as f:
            return json.load(f)
    
    def extract_cc_executor_servers(self, config: Dict) -> List[Tuple[str, Dict]]:
        """Extract only cc_executor MCP servers from config."""
        servers = []
        for name, server_config in config.get("mcpServers", {}).items():
            # Check if it's a cc_executor server
            args = server_config.get("args", [])
            if any("cc_executor" in str(arg) for arg in args):
                servers.append((name, server_config))
        return servers
    
    def test_import_chain(self, server_path: str, pythonpath: str) -> Dict:
        """Test the import chain for a Python file."""
        test_script = f'''
import sys
import json
import traceback

# Set PYTHONPATH
sys.path.insert(0, "{pythonpath}")

results = {{
    "imports_tested": [],
    "import_errors": [],
    "warnings": []
}}

# Try to execute the file and capture all imports
try:
    with open("{server_path}", "r") as f:
        content = f.read()
    
    # Extract imports
    import ast
    tree = ast.parse(content)
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name
                try:
                    __import__(module_name)
                    results["imports_tested"].append({{
                        "module": module_name,
                        "status": "success"
                    }})
                except Exception as e:
                    results["imports_tested"].append({{
                        "module": module_name,
                        "status": "failed",
                        "error": str(e)
                    }})
                    results["import_errors"].append({{
                        "module": module_name,
                        "error": str(e),
                        "type": type(e).__name__
                    }})
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            try:
                if module_name:
                    __import__(module_name)
                    results["imports_tested"].append({{
                        "module": module_name,
                        "status": "success"
                    }})
            except Exception as e:
                results["imports_tested"].append({{
                    "module": module_name,
                    "status": "failed",
                    "error": str(e)
                }})
                results["import_errors"].append({{
                    "module": module_name,
                    "error": str(e),
                    "type": type(e).__name__
                }})

    # Now try to run the file in test mode
    import importlib.util
    spec = importlib.util.spec_from_file_location("mcp_server", "{server_path}")
    module = importlib.util.module_from_spec(spec)
    
    # Inject test mode
    original_argv = sys.argv
    sys.argv = ["{server_path}", "test"]
    
    try:
        spec.loader.exec_module(module)
        results["execution"] = "success"
    except SystemExit as e:
        # Normal exit in test mode
        results["execution"] = "success"
    except Exception as e:
        results["execution"] = "failed"
        results["execution_error"] = {{
            "error": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc()
        }}
    finally:
        sys.argv = original_argv
        
except Exception as e:
    results["parse_error"] = {{
        "error": str(e),
        "type": type(e).__name__,
        "traceback": traceback.format_exc()
    }}

print(json.dumps(results))
'''
        
        # Run the test script
        env = os.environ.copy()
        env["PYTHONPATH"] = pythonpath
        
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            capture_output=True,
            text=True,
            env=env,
            timeout=10
        )
        
        if result.returncode == 0:
            try:
                return json.loads(result.stdout)
            except:
                return {
                    "error": "Failed to parse test output",
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
        else:
            return {
                "error": "Test script failed",
                "stderr": result.stderr,
                "stdout": result.stdout
            }
    
    def run_server_test(self, name: str, config: Dict) -> Dict:
        """Run comprehensive test on a single MCP server."""
        result = {
            "name": name,
            "timestamp": datetime.now().isoformat(),
            "config": config,
            "tests": {}
        }
        
        # Extract server details
        command = config.get("command", "")
        args = config.get("args", [])
        env = config.get("env", {})
        
        # Find the Python file
        python_file = None
        for arg in args:
            if arg.endswith(".py"):
                if "cc_executor" in arg:
                    # Construct full path
                    python_file = self.project_root / arg.replace("src/cc_executor/", "src/cc_executor/")
                break
        
        if not python_file or not python_file.exists():
            result["tests"]["file_exists"] = {
                "status": "failed",
                "error": f"Python file not found: {python_file}"
            }
            return result
        
        result["tests"]["file_exists"] = {"status": "success", "path": str(python_file)}
        
        # Test 1: Import chain analysis
        pythonpath = env.get("PYTHONPATH", str(self.project_root / "src"))
        if not pythonpath.startswith("/"):
            pythonpath = str(self.project_root / pythonpath)
            
        print(f"\n{BLUE}Testing import chain for {name}...{RESET}")
        import_result = self.test_import_chain(str(python_file), pythonpath)
        result["tests"]["imports"] = import_result
        
        # Test 2: Direct execution test
        print(f"{BLUE}Testing direct execution...{RESET}")
        env_copy = os.environ.copy()
        env_copy.update(env)
        env_copy["PYTHONPATH"] = pythonpath
        
        # Run with test flag
        cmd = [sys.executable, str(python_file), "test"]
        exec_result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env_copy,
            timeout=10
        )
        
        result["tests"]["direct_execution"] = {
            "command": " ".join(cmd),
            "returncode": exec_result.returncode,
            "stdout": exec_result.stdout,
            "stderr": exec_result.stderr,
            "success": exec_result.returncode == 0 and "ready" in exec_result.stdout.lower()
        }
        
        # Test 3: Check MCP logs
        log_dir = Path.home() / ".claude" / "mcp_logs"
        startup_log = log_dir / f"{name}_startup.log"
        debug_log = log_dir / f"{name}_debug.log"
        
        result["tests"]["mcp_logs"] = {
            "startup_log_exists": startup_log.exists(),
            "debug_log_exists": debug_log.exists()
        }
        
        if startup_log.exists():
            # Get last few entries
            with open(startup_log) as f:
                lines = f.readlines()
                result["tests"]["mcp_logs"]["last_startup_entry"] = lines[-50:] if len(lines) > 50 else lines
        
        # Test 4: Check for common issues
        issues = []
        
        # Check stderr for common problems
        stderr = exec_result.stderr
        if "ModuleNotFoundError" in stderr:
            # Extract module name
            import re
            match = re.search(r"No module named '([^']+)'", stderr)
            if match:
                issues.append({
                    "type": "missing_module",
                    "module": match.group(1),
                    "fix": f"uv add {match.group(1)}"
                })
        
        if "IndentationError" in stderr:
            issues.append({
                "type": "indentation_error",
                "error": stderr.split('\n')[0]
            })
            
        if "ImportError" in stderr:
            issues.append({
                "type": "import_error", 
                "error": stderr
            })
            
        result["tests"]["common_issues"] = issues
        
        # Generate status
        if exec_result.returncode == 0 and "ready" in exec_result.stdout.lower():
            result["status"] = "working"
        elif import_result.get("import_errors"):
            result["status"] = "import_failures"
        elif issues:
            result["status"] = "has_issues"
        else:
            result["status"] = "unknown"
            
        return result
    
    def debug_all_servers(self):
        """Debug all cc_executor MCP servers."""
        print(f"{BOLD}MCP Server Debugging Framework{RESET}")
        print(f"{'='*60}\n")
        
        # Load config
        config = self.load_mcp_config()
        servers = self.extract_cc_executor_servers(config)
        
        print(f"Found {len(servers)} cc_executor MCP servers to test\n")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "servers": {}
        }
        
        # Test each server
        for name, server_config in servers:
            print(f"{BOLD}Testing: {name}{RESET}")
            result = self.run_server_test(name, server_config)
            results["servers"][name] = result
            
            # Print summary
            status = result.get("status", "unknown")
            if status == "working":
                print(f"{GREEN}✅ {name} - Working{RESET}")
            elif status == "import_failures":
                print(f"{RED}❌ {name} - Import failures{RESET}")
                for err in result["tests"]["imports"].get("import_errors", []):
                    print(f"   - Missing: {err['module']}")
            elif status == "has_issues":
                print(f"{YELLOW}⚠️  {name} - Has issues{RESET}")
                for issue in result["tests"]["common_issues"]:
                    print(f"   - {issue['type']}: {issue.get('module', issue.get('error', ''))}")
            else:
                print(f"{RED}❓ {name} - Unknown status{RESET}")
            print()
        
        # Save detailed report
        with open(self.debug_report_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Generate summary
        print(f"\n{BOLD}Summary:{RESET}")
        print(f"{'='*60}")
        
        working = sum(1 for r in results["servers"].values() if r.get("status") == "working")
        total = len(results["servers"])
        
        print(f"Working: {working}/{total}")
        print(f"\nDetailed report saved to: {self.debug_report_path}")
        
        # Generate fix script
        self.generate_fix_script(results)
        
    def generate_fix_script(self, results: Dict):
        """Generate a script to fix common issues."""
        fix_script_path = self.project_root / "tmp" / "fix_mcp_issues.sh"
        
        fixes = []
        fixes.append("#!/bin/bash")
        fixes.append("# Auto-generated MCP fix script")
        fixes.append(f"# Generated: {datetime.now()}")
        fixes.append("")
        
        # Collect all missing modules
        missing_modules = set()
        for server_name, server_result in results["servers"].items():
            for issue in server_result.get("tests", {}).get("common_issues", []):
                if issue["type"] == "missing_module":
                    missing_modules.add(issue["module"])
        
        if missing_modules:
            fixes.append("# Install missing modules")
            for module in missing_modules:
                fixes.append(f"uv add {module}")
            fixes.append("")
        
        # Save fix script
        with open(fix_script_path, 'w') as f:
            f.write('\n'.join(fixes))
        
        os.chmod(fix_script_path, 0o755)
        print(f"\nFix script generated: {fix_script_path}")

if __name__ == "__main__":
    debugger = MCPDebugger()
    
    # Add todo tracking
    print("\n📋 TODO: Marking MCP debugging framework as in progress...")
    
    debugger.debug_all_servers()
    
    print("\n✅ MCP debugging framework created!")
    print("\nNext steps:")
    print("1. Review the debug report in tmp/mcp_debug_report.json")
    print("2. Run tmp/fix_mcp_issues.sh if there are missing modules")
    print("3. Check individual server issues in the report")