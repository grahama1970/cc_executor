#!/usr/bin/env python3
"""
Test Claude Code hooks the CORRECT way according to documentation.
Hooks are triggered by Claude's tool use, NOT by subprocess commands.
"""

import json
import subprocess
import os
from pathlib import Path
from datetime import datetime

def create_correct_hooks_config():
    """Create a .claude-hooks.json according to the actual documentation."""
    
    # Create a simple logging hook
    hook_script = Path("/tmp/claude_tool_hook.sh")
    hook_content = '''#!/bin/bash
# Log when Claude uses tools

echo "HOOK TRIGGERED at $(date)" >> /tmp/claude_hook_log.txt
echo "Event: $1" >> /tmp/claude_hook_log.txt
echo "Tool: $2" >> /tmp/claude_hook_log.txt

# Read stdin (JSON data from Claude)
stdin_data=$(cat)
echo "Data: $stdin_data" >> /tmp/claude_hook_log.txt
echo "---" >> /tmp/claude_hook_log.txt

# Always exit 0 to allow tool to proceed
exit 0
'''
    
    hook_script.write_text(hook_content)
    os.chmod(hook_script, 0o755)
    
    # Create correct hooks configuration
    config = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": ".*",  # Match all tools
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{hook_script} pre-tool $tool"
                        }
                    ]
                }
            ],
            "PostToolUse": [
                {
                    "matcher": ".*",  # Match all tools
                    "hooks": [
                        {
                            "type": "command", 
                            "command": f"{hook_script} post-tool $tool"
                        }
                    ]
                }
            ]
        }
    }
    
    config_path = Path("/home/graham/workspace/experiments/cc_executor/.claude-hooks.json")
    
    # Backup existing config
    if config_path.exists():
        backup = config_path.with_suffix('.json.backup')
        config_path.rename(backup)
        print(f"Backed up existing config to: {backup}")
    
    # Write new config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"Created correct hooks config at: {config_path}")
    return config_path, hook_script

def test_claude_with_tools():
    """Test if hooks trigger when Claude uses tools."""
    
    # Clear log
    log_file = Path("/tmp/claude_hook_log.txt")
    if log_file.exists():
        log_file.unlink()
    
    print("\n=== Testing Claude Tool Use ===")
    print("This should trigger PreToolUse and PostToolUse hooks...")
    
    # Ask Claude to use tools (this should trigger hooks)
    claude_cmd = [
        "claude",
        "-p",
        "List the files in /tmp directory using the appropriate tool"
    ]
    
    print(f"Running: {' '.join(claude_cmd)}")
    
    try:
        result = subprocess.run(
            claude_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"Exit code: {result.returncode}")
        
        # Check if hooks were triggered
        if log_file.exists():
            print("\n✅ HOOKS TRIGGERED! Log content:")
            print(log_file.read_text())
        else:
            print("\n❌ No hook log found - hooks did not trigger")
            
    except subprocess.TimeoutExpired:
        print("❌ Command timed out")
    except Exception as e:
        print(f"❌ Error: {e}")

def explain_findings():
    """Explain what we learned about hooks."""
    
    print("\n" + "="*60)
    print("CLAUDE CODE HOOKS - CORRECTED UNDERSTANDING")
    print("="*60)
    
    print("""
What I got WRONG:
- I thought hooks trigger on ANY subprocess command ❌
- I was testing with regular Python/shell commands ❌
- I was expecting hooks to intercept subprocess.run() calls ❌

What hooks ACTUALLY do:
- Hooks trigger when CLAUDE uses tools (Bash, Edit, Read, etc.) ✅
- They intercept Claude's tool use, not general subprocess calls ✅
- They receive JSON data about the tool use via stdin ✅

This means:
1. Our original tests were testing the wrong thing
2. Hooks only work within Claude's tool-use context
3. For cc_executor (which runs subprocess directly), hooks are irrelevant
4. The "workaround" in websocket_handler.py is not a workaround - it's the correct approach

The cc_executor project needs to run setup scripts before subprocess execution.
Since it's not using Claude's tools, Claude hooks won't help anyway!
""")

def main():
    """Run the corrected test."""
    
    print("="*60)
    print("TESTING CLAUDE CODE HOOKS - CORRECT METHOD")
    print("="*60)
    
    # Create correct configuration
    config_path, hook_script = create_correct_hooks_config()
    
    # Test with Claude tool use
    test_claude_with_tools()
    
    # Explain findings
    explain_findings()
    
    # Restore original config
    backup = config_path.with_suffix('.json.backup')
    if backup.exists():
        config_path.unlink()
        backup.rename(config_path)
        print(f"\nRestored original config from: {backup}")
    
    # Cleanup
    if hook_script.exists():
        hook_script.unlink()

if __name__ == "__main__":
    main()