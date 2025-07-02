#!/usr/bin/env python3
"""
Pre-execution hook to help AI agents understand CLI entry points and proper invocation.
This solves the major problem of agents not knowing how to call CLI commands properly.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import tomli
except ImportError:
    tomli = None


def read_pyproject_toml(project_root: Path) -> Optional[Dict]:
    """Read and parse pyproject.toml file."""
    pyproject_path = project_root / "pyproject.toml"
    
    if not pyproject_path.exists():
        return None
    
    try:
        if tomli:
            with open(pyproject_path, 'rb') as f:
                return tomli.load(f)
        else:
            # Fallback: basic parsing for entry points
            with open(pyproject_path) as f:
                content = f.read()
                
            # Extract scripts section
            scripts = {}
            in_scripts = False
            for line in content.split('\n'):
                if '[project.scripts]' in line:
                    in_scripts = True
                    continue
                elif in_scripts and line.startswith('['):
                    break
                elif in_scripts and '=' in line:
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        name = parts[0].strip()
                        entry = parts[1].strip().strip('"')
                        scripts[name] = entry
            
            return {'project': {'scripts': scripts}} if scripts else None
    except Exception as e:
        return None


def get_cli_invocation_info(command: str) -> Dict[str, any]:
    """
    Analyze a command and provide proper CLI invocation information.
    """
    result = {
        'original_command': command,
        'entry_points': {},
        'recommended_invocation': None,
        'environment_setup': [],
        'warnings': []
    }
    
    # Find project root (where pyproject.toml is)
    current_path = Path.cwd()
    project_root = None
    
    # Search up the directory tree
    search_path = current_path
    for _ in range(10):  # Limit search depth
        if (search_path / "pyproject.toml").exists():
            project_root = search_path
            break
        if search_path.parent == search_path:
            break
        search_path = search_path.parent
    
    if not project_root:
        result['warnings'].append("Could not find pyproject.toml - are you in the project directory?")
        return result
    
    # Read pyproject.toml
    pyproject_data = read_pyproject_toml(project_root)
    if not pyproject_data:
        result['warnings'].append("Could not parse pyproject.toml")
        return result
    
    # Extract entry points
    scripts = pyproject_data.get('project', {}).get('scripts', {})
    result['entry_points'] = scripts
    
    # Check if command matches any entry point
    command_parts = command.strip().split()
    if not command_parts:
        return result
    
    cmd_name = command_parts[0]
    
    # Direct entry point match
    if cmd_name in scripts:
        result['recommended_invocation'] = command
        result['environment_setup'] = [
            f"cd {project_root}",
            "source .venv/bin/activate",
            f"export PYTHONPATH=\"{project_root}/src:$PYTHONPATH\""
        ]
        return result
    
    # Check for common mistakes
    if cmd_name == "cc_executor" and "cc-executor" in scripts:
        result['warnings'].append("Use 'cc-executor' (with hyphen) not 'cc_executor'")
        result['recommended_invocation'] = command.replace("cc_executor", "cc-executor", 1)
    
    elif cmd_name == "python" and len(command_parts) > 1:
        # Check if trying to run a module that has an entry point
        module_path = command_parts[1]
        for entry_name, entry_point in scripts.items():
            if entry_point.split(':')[0].replace('.', '/') in module_path:
                result['warnings'].append(f"This module has a CLI entry point: {entry_name}")
                result['recommended_invocation'] = entry_name + ' ' + ' '.join(command_parts[2:])
    
    # Set up environment regardless
    result['environment_setup'] = [
        f"cd {project_root}",
        "source .venv/bin/activate",
        f"export PYTHONPATH=\"{project_root}/src:$PYTHONPATH\""
    ]
    
    return result


def check_venv_active() -> bool:
    """Check if virtual environment is active."""
    return hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)


def main():
    """Hook entry point."""
    # Get command from environment
    command = os.environ.get('CLAUDE_COMMAND', '')
    session_id = os.environ.get('CLAUDE_SESSION_ID', 'unknown')
    
    if not command:
        return
    
    # Check if this looks like a CLI command
    cli_indicators = ['cc-executor', 'cc_executor', 'check-file-rules', 'transcript-helper']
    is_cli_command = any(indicator in command for indicator in cli_indicators)
    
    if not is_cli_command and not ('python' in command and 'main.py' in command):
        return  # Not a CLI command, skip
    
    # Analyze the command
    info = get_cli_invocation_info(command)
    
    # Store analysis in Redis if available
    try:
        import redis
        r = redis.Redis(decode_responses=True)
        r.ping()
        
        # Store CLI guidance
        key = f"cli:guidance:{session_id}"
        r.setex(key, 300, json.dumps(info))
        
        # Store entry points for reference
        if info['entry_points']:
            r.setex(f"cli:entry_points:{session_id}", 300, json.dumps(info['entry_points']))
    except:
        pass
    
    # Output guidance to stderr so agent sees it
    if info['warnings'] or info['recommended_invocation']:
        print("\n=== CLI INVOCATION GUIDANCE ===", file=sys.stderr)
        
        if info['warnings']:
            for warning in info['warnings']:
                print(f"⚠️  {warning}", file=sys.stderr)
        
        if info['entry_points']:
            print("\nAvailable CLI commands:", file=sys.stderr)
            for name, entry in info['entry_points'].items():
                print(f"  - {name} → {entry}", file=sys.stderr)
        
        if info['recommended_invocation']:
            print(f"\n✅ Recommended: {info['recommended_invocation']}", file=sys.stderr)
        
        if info['environment_setup']:
            print("\nRequired setup:", file=sys.stderr)
            for step in info['environment_setup']:
                print(f"  {step}", file=sys.stderr)
        
        # Check current environment
        if not check_venv_active():
            print("\n❌ Virtual environment is NOT active!", file=sys.stderr)
        else:
            print("\n✅ Virtual environment is active", file=sys.stderr)
        
        print("==============================\n", file=sys.stderr)
    
    # Modify command if needed
    if info['recommended_invocation'] and info['recommended_invocation'] != command:
        os.environ['CLAUDE_COMMAND'] = info['recommended_invocation']


if __name__ == "__main__":
    # Test mode
    print("=== CLI Entry Point Checker Hook Test ===\n")
    
    # Test various commands
    test_commands = [
        "cc_executor server start",  # Wrong name
        "cc-executor",  # Correct
        "python src/cc_executor/core/main.py",  # Direct module
        "check-file-rules --help",
        "python -m cc_executor.core.main"
    ]
    
    for cmd in test_commands:
        print(f"Testing: {cmd}")
        os.environ['CLAUDE_COMMAND'] = cmd
        os.environ['CLAUDE_SESSION_ID'] = 'test'
        
        info = get_cli_invocation_info(cmd)
        print(f"  Warnings: {info['warnings']}")
        print(f"  Recommended: {info['recommended_invocation']}")
        print()
    
    # Show full analysis
    print("\nFull analysis for 'cc_executor':")
    full_info = get_cli_invocation_info("cc_executor")
    print(json.dumps(full_info, indent=2))
    
    print("\n✅ CLI entry point check completed")