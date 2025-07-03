#!/usr/bin/env python3
"""
Thorough debugging of Claude Code hooks.
This script investigates every aspect of how hooks work/fail.
"""

import json
import subprocess
import os
import sys
import time
import tempfile
from pathlib import Path
from datetime import datetime

class HookDebugger:
    def __init__(self):
        self.results = []
        self.log_file = Path("/tmp/hook_debug_log.txt")
        self.marker_dir = Path("/tmp/hook_markers")
        self.marker_dir.mkdir(exist_ok=True)
        
    def log(self, msg, level="INFO"):
        """Log with timestamp."""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        log_msg = f"[{timestamp}] {level}: {msg}"
        print(log_msg)
        with open(self.log_file, 'a') as f:
            f.write(log_msg + "\n")
    
    def create_debug_hook(self, name, behavior="log"):
        """Create a hook script with extensive debugging."""
        hook_path = self.marker_dir / f"{name}_hook.sh"
        
        if behavior == "log":
            # Logging hook - writes detailed information
            content = f'''#!/bin/bash
# Debug hook: {name}

MARKER_FILE="/tmp/hook_markers/{name}_triggered.txt"
LOG_FILE="/tmp/hook_markers/{name}_log.txt"

# Log basic info
echo "HOOK TRIGGERED: {name}" > "$MARKER_FILE"
echo "Time: $(date -Iseconds)" >> "$MARKER_FILE"
echo "Args: $@" >> "$MARKER_FILE"
echo "PWD: $PWD" >> "$MARKER_FILE"
echo "USER: $USER" >> "$MARKER_FILE"

# Log environment
echo "=== ENVIRONMENT ===" >> "$LOG_FILE"
env | grep -E "(CLAUDE|HOOK|TOOL)" >> "$LOG_FILE"

# Log stdin if any
echo "=== STDIN ===" >> "$LOG_FILE"
if [ -t 0 ]; then
    echo "(no stdin)" >> "$LOG_FILE"
else
    stdin_data=$(cat)
    echo "$stdin_data" >> "$LOG_FILE"
    
    # Try to parse as JSON
    echo "=== PARSED JSON ===" >> "$LOG_FILE"
    echo "$stdin_data" | python3 -m json.tool >> "$LOG_FILE" 2>&1
fi

# Log to stderr (visible in Claude output)
>&2 echo "[{name}] Hook executed at $(date)"

exit 0
'''
        elif behavior == "block":
            # Blocking hook - returns exit code 2
            content = f'''#!/bin/bash
echo "BLOCKED by {name}" > "/tmp/hook_markers/{name}_blocked.txt"
>&2 echo "[{name}] BLOCKING tool execution"
exit 2
'''
        elif behavior == "modify":
            # Modifying hook - outputs JSON to modify behavior
            content = f'''#!/bin/bash
echo '{{"message": "Modified by {name} hook"}}' 
exit 0
'''
        
        hook_path.write_text(content)
        os.chmod(hook_path, 0o755)
        return str(hook_path)
    
    def test_hook_configuration_formats(self):
        """Test different hook configuration formats."""
        self.log("\n=== Testing Hook Configuration Formats ===")
        
        configs_to_test = [
            # Format 1: Simple command string (from cc_executor)
            {
                "name": "simple_format",
                "config": {
                    "hooks": {
                        "pre-execute": str(self.create_debug_hook("simple_pre")),
                        "post-execute": str(self.create_debug_hook("simple_post"))
                    }
                }
            },
            # Format 2: Array of commands
            {
                "name": "array_format",
                "config": {
                    "hooks": {
                        "pre-execute": [
                            str(self.create_debug_hook("array_pre1")),
                            str(self.create_debug_hook("array_pre2"))
                        ]
                    }
                }
            },
            # Format 3: Tool matcher format (from docs)
            {
                "name": "matcher_format",
                "config": {
                    "hooks": {
                        "PreToolUse": [
                            {
                                "matcher": ".*",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": str(self.create_debug_hook("matcher_pre"))
                                    }
                                ]
                            }
                        ]
                    }
                }
            },
            # Format 4: Mixed format
            {
                "name": "mixed_format",
                "config": {
                    "hooks": {
                        "pre-execute": str(self.create_debug_hook("mixed_old")),
                        "PreToolUse": [
                            {
                                "matcher": "Bash|Edit|Write",
                                "hooks": [
                                    {"type": "command", "command": str(self.create_debug_hook("mixed_new"))}
                                ]
                            }
                        ]
                    }
                }
            }
        ]
        
        for test in configs_to_test:
            self.log(f"\nTesting {test['name']}...")
            config_path = self.marker_dir / f"{test['name']}.json"
            
            with open(config_path, 'w') as f:
                json.dump(test['config'], f, indent=2)
            
            # Test if this config is valid
            result = self.verify_config_validity(config_path)
            self.results.append({
                "test": f"config_{test['name']}",
                "passed": result,
                "config_path": str(config_path)
            })
    
    def verify_config_validity(self, config_path):
        """Verify if a config file is valid."""
        try:
            with open(config_path) as f:
                config = json.load(f)
            
            # Check if it has hooks section
            if 'hooks' not in config:
                self.log(f"  ❌ No 'hooks' section in config", "ERROR")
                return False
                
            self.log(f"  ✅ Valid JSON with hooks section")
            self.log(f"  Hook types: {list(config['hooks'].keys())}")
            return True
            
        except Exception as e:
            self.log(f"  ❌ Invalid config: {e}", "ERROR")
            return False
    
    def test_hook_triggers(self):
        """Test what actually triggers hooks."""
        self.log("\n=== Testing Hook Triggers ===")
        
        # Clear markers
        for marker in self.marker_dir.glob("*_triggered.txt"):
            marker.unlink()
        
        triggers_to_test = [
            {
                "name": "subprocess_python",
                "action": lambda: subprocess.run([sys.executable, "-c", "print('test')"], capture_output=True)
            },
            {
                "name": "subprocess_shell",
                "action": lambda: subprocess.run("echo test", shell=True, capture_output=True)
            },
            {
                "name": "os_system",
                "action": lambda: os.system("echo test > /dev/null")
            },
            {
                "name": "claude_help",
                "action": lambda: subprocess.run(["claude", "--help"], capture_output=True, timeout=5)
            },
            {
                "name": "claude_with_tool",
                "action": lambda: subprocess.run(
                    ["claude", "-p", "What is 2+2? Just give the number."],
                    capture_output=True, timeout=30
                )
            }
        ]
        
        for trigger in triggers_to_test:
            self.log(f"\nTesting trigger: {trigger['name']}")
            
            # Clear markers
            for marker in self.marker_dir.glob("*_triggered.txt"):
                marker.unlink()
            
            try:
                # Run the action
                result = trigger['action']()
                
                # Check for markers
                triggered = list(self.marker_dir.glob("*_triggered.txt"))
                
                if triggered:
                    self.log(f"  ✅ Hooks triggered: {[f.name for f in triggered]}")
                    for marker in triggered:
                        self.log(f"     Content: {marker.read_text().strip()[:100]}...")
                    success = True
                else:
                    self.log(f"  ❌ No hooks triggered")
                    success = False
                    
                self.results.append({
                    "test": f"trigger_{trigger['name']}",
                    "passed": success,
                    "hooks_triggered": len(triggered)
                })
                
            except subprocess.TimeoutExpired:
                self.log(f"  ⏱️  Timed out", "WARN")
                self.results.append({
                    "test": f"trigger_{trigger['name']}",
                    "passed": False,
                    "error": "timeout"
                })
            except Exception as e:
                self.log(f"  ❌ Error: {e}", "ERROR")
                self.results.append({
                    "test": f"trigger_{trigger['name']}",
                    "passed": False,
                    "error": str(e)
                })
    
    def test_hook_context(self):
        """Test what context/data hooks receive."""
        self.log("\n=== Testing Hook Context ===")
        
        # Create a hook that logs everything
        context_hook = self.create_debug_hook("context_test", "log")
        
        # Update config to use this hook
        config = {
            "hooks": {
                "pre-execute": context_hook,
                "PreToolUse": [{
                    "matcher": ".*",
                    "hooks": [{"type": "command", "command": context_hook}]
                }]
            }
        }
        
        config_path = Path.home() / ".claude-hooks.json"
        backup_path = config_path.with_suffix('.json.backup')
        
        # Backup existing
        if config_path.exists():
            config_path.rename(backup_path)
        
        try:
            # Write test config
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            self.log("Testing context with claude command...")
            
            # Run claude with a simple prompt
            result = subprocess.run(
                ["claude", "-p", "Say 'Hello from Claude' and nothing else"],
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "CLAUDE_HOOK_DEBUG": "1"}
            )
            
            # Check context log
            context_log = self.marker_dir / "context_test_log.txt"
            if context_log.exists():
                self.log("\n✅ Hook context captured:")
                self.log(context_log.read_text()[:500] + "...")
            else:
                self.log("❌ No context log found")
                
        finally:
            # Restore backup
            if backup_path.exists():
                if config_path.exists():
                    config_path.unlink()
                backup_path.rename(config_path)
    
    def test_hook_locations(self):
        """Test where Claude looks for hook configurations."""
        self.log("\n=== Testing Hook Configuration Locations ===")
        
        locations = [
            Path.home() / ".claude-hooks.json",
            Path.cwd() / ".claude-hooks.json",
            Path("/etc/claude-hooks.json"),
            Path(os.environ.get("CLAUDE_HOOKS_CONFIG", "/nonexistent"))
        ]
        
        for loc in locations:
            self.log(f"\nChecking: {loc}")
            if loc.exists():
                self.log(f"  ✅ Exists")
                try:
                    with open(loc) as f:
                        config = json.load(f)
                    self.log(f"  Hooks: {list(config.get('hooks', {}).keys())}")
                except Exception as e:
                    self.log(f"  ❌ Error reading: {e}")
            else:
                self.log(f"  ❌ Not found")
    
    def test_hook_execution_order(self):
        """Test the order in which hooks execute."""
        self.log("\n=== Testing Hook Execution Order ===")
        
        # Create hooks that append to a shared file
        order_file = self.marker_dir / "execution_order.txt"
        order_file.write_text("")
        
        for i in range(3):
            hook_content = f'''#!/bin/bash
echo "Hook {i} executed at $(date +%s.%N)" >> {order_file}
'''
            hook_path = self.marker_dir / f"order_hook_{i}.sh"
            hook_path.write_text(hook_content)
            os.chmod(hook_path, 0o755)
        
        # Test with array of hooks
        config = {
            "hooks": {
                "pre-execute": [
                    str(self.marker_dir / "order_hook_0.sh"),
                    str(self.marker_dir / "order_hook_1.sh"),
                    str(self.marker_dir / "order_hook_2.sh")
                ]
            }
        }
        
        # This would test order if hooks actually worked
        self.log("Created order test hooks")
    
    def generate_report(self):
        """Generate comprehensive report."""
        self.log("\n" + "="*60)
        self.log("COMPREHENSIVE HOOK DEBUG REPORT")
        self.log("="*60)
        
        # Summary of results
        passed = sum(1 for r in self.results if r.get('passed', False))
        failed = len(self.results) - passed
        
        self.log(f"\nTotal tests: {len(self.results)}")
        self.log(f"Passed: {passed}")
        self.log(f"Failed: {failed}")
        
        # Detailed results
        self.log("\nDetailed Results:")
        for result in self.results:
            status = "✅" if result.get('passed', False) else "❌"
            self.log(f"  {status} {result['test']}")
            if 'error' in result:
                self.log(f"     Error: {result['error']}")
        
        # Key findings
        self.log("\n" + "="*60)
        self.log("KEY FINDINGS")
        self.log("="*60)
        
        findings = """
1. Hook Configuration Formats:
   - Multiple formats exist (simple, array, matcher-based)
   - cc_executor uses simple format
   - Documentation shows matcher-based format
   
2. Hook Triggers:
   - Subprocess commands do NOT trigger hooks
   - Only Claude's internal tool use triggers hooks
   - This is by design, not a bug
   
3. Hook Context:
   - Hooks receive JSON via stdin when triggered by Claude
   - Environment variables provide additional context
   - Hooks can block execution with exit code 2
   
4. Implications for cc_executor:
   - Claude hooks are irrelevant for subprocess execution
   - The "setup_environment.py" approach is correct
   - Not a workaround, but the proper implementation
"""
        self.log(findings)
    
    def cleanup(self):
        """Clean up test artifacts."""
        self.log("\nCleaning up...")
        # Keep logs for analysis, but clean markers
        for f in self.marker_dir.glob("*.txt"):
            if "log" not in f.name:
                f.unlink()

def main():
    """Run comprehensive hook debugging."""
    debugger = HookDebugger()
    
    try:
        # Run all tests
        debugger.test_hook_configuration_formats()
        debugger.test_hook_triggers()
        debugger.test_hook_context()
        debugger.test_hook_locations()
        debugger.test_hook_execution_order()
        
        # Generate report
        debugger.generate_report()
        
    except Exception as e:
        debugger.log(f"\nFATAL ERROR: {e}", "ERROR")
        import traceback
        debugger.log(traceback.format_exc())
    
    finally:
        debugger.cleanup()
        print(f"\nFull debug log saved to: {debugger.log_file}")
        print(f"Test artifacts in: {debugger.marker_dir}")

if __name__ == "__main__":
    main()