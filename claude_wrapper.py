#!/usr/bin/env python3
"""
Claude Code wrapper that enforces hook execution at all lifecycle points.
Runs Claude in a subprocess and monitors its execution.
"""
import os
import sys
import subprocess
import signal
import time
import json
from pathlib import Path
from datetime import datetime
import atexit

project_root = Path(__file__).parent
hooks_dir = project_root / "src" / "cc_executor" / "hooks"
claude_process = None

def run_hook(hook_name: str, context: dict = None):
    """Run a hook with context."""
    hook_path = hooks_dir / f"{hook_name}.py"
    if not hook_path.exists():
        return True
    
    env = os.environ.copy()
    if context:
        env['HOOK_CONTEXT'] = json.dumps(context)
    
    result = subprocess.run(
        [sys.executable, str(hook_path)],
        env=env,
        capture_output=True,
        text=True
    )
    return result.returncode == 0

def cleanup():
    """Run post-execution hooks."""
    print("\n🪝 Running cleanup hooks...")
    run_hook("record_execution_metrics")
    run_hook("truncate_logs")
    if claude_process and claude_process.poll() is None:
        claude_process.terminate()

def signal_handler(signum, frame):
    """Handle signals to ensure cleanup."""
    cleanup()
    sys.exit(0)

def main():
    global claude_process
    
    # Register cleanup
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("🚀 Claude Wrapper Starting...")
    
    # Pre-execution hooks
    if not run_hook("setup_environment"):
        print("❌ Environment setup failed")
        return 1
        
    if not run_hook("claude_instance_pre_check"):
        print("❌ Claude pre-check failed")
        return 1
    
    # Launch Claude with monitoring
    print("\n📟 Launching Claude Code...")
    
    # Start Claude in a subprocess so we can monitor it
    claude_cmd = ["claude", "code"]  # Add your Claude command here
    
    try:
        claude_process = subprocess.Popen(
            claude_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Monitor output and inject hooks at key points
        while True:
            output = claude_process.stdout.readline()
            if output == '' and claude_process.poll() is not None:
                break
            if output:
                print(output.strip())
                
                # Detect operations and run hooks
                if "Executing command" in output:
                    run_hook("analyze_task_complexity")
                elif "Error" in output:
                    run_hook("debug_hooks")
                    
        return_code = claude_process.poll()
        
    except Exception as e:
        print(f"❌ Error running Claude: {e}")
        return 1
    finally:
        cleanup()
    
    return return_code

if __name__ == "__main__":
    sys.exit(main())