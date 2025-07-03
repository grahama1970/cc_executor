#!/usr/bin/env python3
"""
Hook Enforcement Workaround - Since Claude Code hooks don't work,
we implement them directly in Python code.
"""
import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Callable
import json
from datetime import datetime

class HookEnforcer:
    """Enforces hooks programmatically since Claude Code won't."""
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.hooks_dir = self.project_root / "src" / "cc_executor" / "hooks"
        self.log_dir = Path("/tmp")
        self.venv_path = self.project_root / ".venv"
        
    def pre_execution_hook(self, func_name: str, *args, **kwargs):
        """Run before any function execution."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = self.log_dir / f"hook_pre_execution_{timestamp}.log"
        
        # Check virtual environment
        if not self._check_venv():
            self._activate_venv()
            
        # Log execution
        log_data = {
            "timestamp": timestamp,
            "function": func_name,
            "args": str(args)[:200],  # Truncate for safety
            "kwargs": str(kwargs)[:200],
            "venv_active": self._check_venv(),
            "cwd": str(Path.cwd())
        }
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
            
        print(f"🪝 PRE-EXECUTION HOOK: {func_name}")
        
    def post_execution_hook(self, func_name: str, result: Any, error: Optional[Exception] = None):
        """Run after any function execution."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = self.log_dir / f"hook_post_execution_{timestamp}.log"
        
        log_data = {
            "timestamp": timestamp,
            "function": func_name,
            "success": error is None,
            "error": str(error) if error else None,
            "result_type": type(result).__name__
        }
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
            
        status = "✅" if error is None else "❌"
        print(f"🪝 POST-EXECUTION HOOK: {func_name} {status}")
        
    def _check_venv(self) -> bool:
        """Check if virtual environment is active."""
        return hasattr(sys, 'real_prefix') or (
            hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
        )
        
    def _activate_venv(self):
        """Activate virtual environment."""
        if self.venv_path.exists():
            activate_script = self.venv_path / "bin" / "activate_this.py"
            if activate_script.exists():
                exec(open(activate_script).read(), {'__file__': str(activate_script)})
            else:
                # Fallback: modify sys.path
                site_packages = self.venv_path / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
                if site_packages.exists():
                    sys.path.insert(0, str(site_packages))
                    
    def enforce_hook(self, hook_type: str, *args, **kwargs):
        """Run a specific hook from the hooks directory."""
        hook_script = self.hooks_dir / f"{hook_type}.py"
        if hook_script.exists():
            # Import and run the hook
            spec = __import__('importlib.util').util.spec_from_file_location(hook_type, hook_script)
            hook_module = __import__('importlib.util').util.module_from_spec(spec)
            spec.loader.exec_module(hook_module)
            
            if hasattr(hook_module, 'run_hook'):
                return hook_module.run_hook(*args, **kwargs)
                
        return True  # Default to allowing operation

def with_hooks(enforcer: HookEnforcer):
    """Decorator to wrap functions with hook enforcement."""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            # Pre-execution hook
            enforcer.pre_execution_hook(func.__name__, *args, **kwargs)
            
            # Execute function
            error = None
            result = None
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                error = e
                
            # Post-execution hook
            enforcer.post_execution_hook(func.__name__, result, error)
            
            # Re-raise error if occurred
            if error:
                raise error
                
            return result
        return wrapper
    return decorator

# Global enforcer instance
hook_enforcer = HookEnforcer()

if __name__ == "__main__":
    # Usage demonstration
    print("=== Hook Enforcement Workaround ===")
    
    @with_hooks(hook_enforcer)
    def test_function(x: int, y: int) -> int:
        """Test function to demonstrate hooks."""
        return x + y
    
    # Test the hooks
    result = test_function(5, 3)
    print(f"Result: {result}")
    
    # Check logs created
    import glob
    logs = glob.glob("/tmp/hook_*.log")
    print(f"\n✅ Created {len(logs)} hook logs")
    
    # Save demonstration output
    output_dir = Path(__file__).parent / "tmp" / "responses"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f"hook_enforcement_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "hooks_executed": len(logs),
            "result": result,
            "venv_active": hook_enforcer._check_venv()
        }, f, indent=2)
        
    print(f"\n💾 Response saved to: {output_file.relative_to(Path.cwd())}")