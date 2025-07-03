#!/usr/bin/env python3
"""
Test if Anthropic hooks work when Claude uses its own tools.
This tests actual Claude tool usage, not subprocess commands.
"""

import os
from pathlib import Path
from datetime import datetime

# Create a simple pre/post hook that logs when it's called
def create_logging_hook():
    """Create a hook that logs all calls."""
    hook_content = '''#!/usr/bin/env python3
import sys
import json
from datetime import datetime

# Log that hook was called
log_file = "/tmp/claude_hook_log.txt"
with open(log_file, "a") as f:
    f.write(f"\\n{'='*60}\\n")
    f.write(f"HOOK CALLED: {sys.argv[0]}\\n")
    f.write(f"Time: {datetime.now().isoformat()}\\n")
    f.write(f"Args: {sys.argv[1:]}\\n")
    
    # Read stdin if available
    try:
        stdin_data = sys.stdin.read()
        if stdin_data:
            f.write(f"STDIN data received:\\n")
            data = json.loads(stdin_data)
            f.write(json.dumps(data, indent=2)[:500] + "\\n")
    except:
        f.write("No stdin data\\n")

print("Hook executed successfully")
'''
    
    hook_path = Path("/tmp/test_claude_hook.py")
    hook_path.write_text(hook_content)
    os.chmod(hook_path, 0o755)
    return hook_path

# Create test configuration
def create_test_config():
    """Create a hooks config that should catch all Claude tool usage."""
    hook_path = create_logging_hook()
    
    config = {
        "hooks": {
            # Old-style hooks
            "pre-execute": str(hook_path),
            "post-execute": str(hook_path),
            "pre-tool": str(hook_path),
            "post-tool": str(hook_path),
            
            # New-style hooks from docs
            "PreToolUse": [{
                "matcher": ".*",  # Match ALL tools
                "hooks": [{
                    "type": "command",
                    "command": f"{hook_path} PreToolUse"
                }]
            }],
            "PostToolUse": [{
                "matcher": ".*",
                "hooks": [{
                    "type": "command",
                    "command": f"{hook_path} PostToolUse"
                }]
            }],
            "Notification": [{
                "matcher": ".*",
                "hooks": [{
                    "type": "command",
                    "command": f"{hook_path} Notification"
                }]
            }]
        }
    }
    
    return config

if __name__ == "__main__":
    print("Creating test hook configuration...")
    config = create_test_config()
    
    print("\nTest configuration:")
    import json
    print(json.dumps(config, indent=2))
    
    print("\nTo test:")
    print("1. Save this config to ~/.claude-hooks.json")
    print("2. Have Claude use various tools (Bash, Write, Edit, etc.)")
    print("3. Check /tmp/claude_hook_log.txt to see if hooks were called")
    print("\nLog file will be at: /tmp/claude_hook_log.txt")