#!/usr/bin/env python3
"""
Comprehensive pre-execution check for Claude Code instances.
Ensures environment is fully configured before spawning Claude.

This hook prevents common failures by validating:
1. Working directory
2. Virtual environment activation  
3. MCP configuration
4. Python path setup
5. Dependencies installation
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Tuple
from loguru import logger

class EnvironmentValidator:
    """Validates and prepares environment for Claude execution."""
    
    def __init__(self):
        self.checks_passed = []
        self.checks_failed = []
        self.fixes_applied = []
        self.project_root = self._find_project_root()
        
    def _find_project_root(self) -> Path:
        """Find project root by looking for pyproject.toml or .git."""
        current = Path.cwd()
        
        for parent in [current] + list(current.parents):
            if (parent / 'pyproject.toml').exists() or (parent / '.git').exists():
                return parent
                
        return current
        
    def check_working_directory(self) -> Tuple[bool, str]:
        """Verify we're in the correct working directory."""
        cwd = Path.cwd()
        
        # Check if we're in a reasonable project directory
        indicators = ['pyproject.toml', 'setup.py', 'requirements.txt', '.git', 'src']
        has_indicators = any((cwd / ind).exists() for ind in indicators)
        
        if has_indicators:
            self.checks_passed.append(f"Working directory: {cwd}")
            return True, str(cwd)
        else:
            self.checks_failed.append(f"No project indicators in {cwd}")
            return False, str(cwd)
            
    def check_venv_activation(self) -> Tuple[bool, str]:
        """Check if virtual environment is activated."""
        venv_path = None
        
        # Check VIRTUAL_ENV
        if 'VIRTUAL_ENV' in os.environ:
            venv_path = os.environ['VIRTUAL_ENV']
            
        # Check for .venv in project
        project_venv = self.project_root / '.venv'
        if project_venv.exists():
            if venv_path and Path(venv_path) == project_venv:
                self.checks_passed.append(f"Venv active: {venv_path}")
                return True, str(venv_path)
            else:
                self.checks_failed.append(f"Wrong venv active: {venv_path}")
                self.fixes_applied.append(f"Should activate: {project_venv}")
                return False, str(project_venv)
        
        self.checks_failed.append("No virtual environment found")
        return False, ""
        
    def check_mcp_config(self) -> Tuple[bool, str]:
        """Verify .mcp.json exists and is valid."""
        mcp_path = self.project_root / '.mcp.json'
        
        if not mcp_path.exists():
            # Try to create a minimal MCP config
            minimal_config = {
                "mcpServers": {},
                "tools": {
                    "perplexity-ask": {
                        "command": "mcp-server-perplexity-ask"
                    }
                }
            }
            
            try:
                mcp_path.write_text(json.dumps(minimal_config, indent=2))
                self.fixes_applied.append("Created minimal .mcp.json")
                return True, str(mcp_path)
            except Exception as e:
                self.checks_failed.append(f"Cannot create .mcp.json: {e}")
                return False, ""
                
        # Validate existing config
        try:
            with open(mcp_path) as f:
                config = json.load(f)
                
            if isinstance(config, dict):
                self.checks_passed.append(f"Valid .mcp.json at {mcp_path}")
                return True, str(mcp_path)
            else:
                self.checks_failed.append("Invalid .mcp.json format")
                return False, str(mcp_path)
                
        except Exception as e:
            self.checks_failed.append(f"Cannot read .mcp.json: {e}")
            return False, str(mcp_path)
            
    def check_python_path(self) -> Tuple[bool, List[str]]:
        """Verify PYTHONPATH configuration."""
        issues = []
        paths_needed = []
        
        # Check .env file
        env_file = self.project_root / '.env'
        env_pythonpath = None
        
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    if line.startswith('PYTHONPATH='):
                        env_pythonpath = line.strip().split('=', 1)[1]
                        break
                        
        # Check pyproject.toml
        pyproject = self.project_root / 'pyproject.toml'
        expected_paths = ['./src', str(self.project_root / 'src')]
        
        # Verify PYTHONPATH includes src
        current_pythonpath = os.environ.get('PYTHONPATH', '')
        
        if 'src' in current_pythonpath or any(p in current_pythonpath for p in expected_paths):
            self.checks_passed.append(f"PYTHONPATH includes src: {current_pythonpath}")
        else:
            self.checks_failed.append("PYTHONPATH missing src directory")
            paths_needed.append('./src')
            
            # Try to fix
            os.environ['PYTHONPATH'] = f"./src:{current_pythonpath}".rstrip(':')
            self.fixes_applied.append("Added ./src to PYTHONPATH")
            
        return len(issues) == 0, paths_needed
        
    def check_dependencies(self) -> Tuple[bool, str]:
        """Verify dependencies are installed."""
        venv_path = os.environ.get('VIRTUAL_ENV')
        
        if not venv_path:
            self.checks_failed.append("Cannot check dependencies without venv")
            return False, ""
            
        # Check if key packages are installed
        key_packages = ['fastapi', 'websockets', 'redis', 'loguru']
        missing = []
        
        for pkg in key_packages:
            check = subprocess.run(
                [f"{venv_path}/bin/python", "-c", f"import {pkg}"],
                capture_output=True
            )
            if check.returncode != 0:
                missing.append(pkg)
                
        if missing:
            self.checks_failed.append(f"Missing packages: {missing}")
            
            # Try to install with uv
            if (Path(venv_path) / 'bin' / 'uv').exists():
                logger.info("Running uv pip install -e . to fix dependencies")
                install_cmd = f"cd {self.project_root} && {venv_path}/bin/uv pip install -e ."
                
                try:
                    result = subprocess.run(
                        install_cmd,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.returncode == 0:
                        self.fixes_applied.append("Installed dependencies with uv")
                        return True, "Dependencies installed"
                    else:
                        logger.error(f"uv install failed: {result.stderr}")
                        
                except Exception as e:
                    logger.error(f"Could not run uv install: {e}")
                    
            return False, f"Missing: {missing}"
        else:
            self.checks_passed.append("All key dependencies installed")
            return True, "All dependencies present"
            
    def generate_init_commands(self) -> List[str]:
        """Generate initialization commands for Claude."""
        commands = []
        
        # Always start with pwd
        commands.append("pwd")
        
        # Activate venv if needed
        venv_path = self.project_root / '.venv'
        if venv_path.exists():
            commands.append(f"source {venv_path}/bin/activate")
            
        # Set PYTHONPATH
        commands.append("export PYTHONPATH=./src:$PYTHONPATH")
        
        # Verify environment
        commands.append("which python")
        commands.append("echo $PYTHONPATH")
        
        return commands
        
    def create_validation_record(self) -> Dict:
        """Create a comprehensive validation record."""
        return {
            "timestamp": time.time(),
            "project_root": str(self.project_root),
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "fixes_applied": self.fixes_applied,
            "init_commands": self.generate_init_commands(),
            "ready": len(self.checks_failed) == 0
        }


def main():
    """Main hook entry point."""
    command = os.environ.get('CLAUDE_COMMAND', '')
    session_id = os.environ.get('CLAUDE_SESSION_ID', 'default')
    
    # Only run for Claude instances
    if 'claude' not in command.lower():
        logger.info("Not a Claude command, skipping pre-check")
        sys.exit(0)
        
    logger.info("=== Claude Instance Pre-Check ===")
    
    validator = EnvironmentValidator()
    
    # Run all checks
    cwd_ok, cwd = validator.check_working_directory()
    venv_ok, venv = validator.check_venv_activation()
    mcp_ok, mcp = validator.check_mcp_config()
    path_ok, paths = validator.check_python_path()
    deps_ok, deps = validator.check_dependencies()

    # --- Additional required package verification (session-specific) ---
    missing_pkgs = []
    try:
        import redis
        r = redis.Redis(decode_responses=True)
        req_key = f"hook:req_pkgs:{session_id}"
        req_pkgs_json = r.get(req_key)
        if req_pkgs_json:
            required_pkgs = json.loads(req_pkgs_json)
            # Get installed packages via uv (fast JSON)
            try:
                pkg_list_json = subprocess.check_output(["uv", "pip", "list", "--format", "json"], text=True, timeout=10)
                installed_names = {pkg['name'].lower() for pkg in json.loads(pkg_list_json)}
                missing_pkgs = [p for p in required_pkgs if p.lower() not in installed_names]
            except Exception as e:
                logger.warning(f"Could not obtain installed package list: {e}")
    except Exception as e:
        logger.debug(f"Redis unavailable for required package check: {e}")

    if missing_pkgs:
        auto_install = os.environ.get('AUTO_INSTALL_MISSING_PKGS', 'false').lower() == 'true'
        logger.warning(f"Missing session-required packages: {missing_pkgs}")
        if auto_install:
            try:
                install_cmd = ["uv", "pip", "install", "--quiet", *missing_pkgs]
                logger.info(f"Auto-installing via uv: {' '.join(missing_pkgs)}")
                res = subprocess.run(install_cmd, capture_output=True, text=True, timeout=120)
                if res.returncode != 0:
                    logger.error(f"uv install failed: {res.stderr[:200]}")
                else:
                    validator.fixes_applied.append(f"Installed missing pkgs: {missing_pkgs}")
                    missing_pkgs = []
            except Exception as e:
                logger.error(f"Auto-install encountered error: {e}")
        else:
            # Abort early so orchestrator can handle installation
            logger.error("Aborting due to missing packages. Set AUTO_INSTALL_MISSING_PKGS=true to auto-install.")
            sys.exit(1)
    
    # Create validation record
    validation = validator.create_validation_record()
    
    # Store in Redis for post-hook
    try:
        import redis
        r = redis.Redis(decode_responses=True)
        
        key = f"hook:claude_validation:{session_id}"
        r.setex(key, 600, json.dumps(validation))  # 10 minute TTL
        
        logger.info(f"Stored validation record for session {session_id}")
        
    except Exception as e:
        logger.error(f"Could not store validation: {e}")
        
    # Log summary
    logger.info(f"Checks passed: {len(validator.checks_passed)}")
    logger.info(f"Checks failed: {len(validator.checks_failed)}")
    logger.info(f"Fixes applied: {len(validator.fixes_applied)}")
    
    if validator.checks_failed:
        logger.warning("Environment issues detected:")
        for issue in validator.checks_failed:
            logger.warning(f"  - {issue}")
            
    if validator.fixes_applied:
        logger.info("Fixes applied:")
        for fix in validator.fixes_applied:
            logger.info(f"  + {fix}")
            
    # Modify command to include init steps
    if validation['ready'] and 'claude -p' in command:
        init_steps = ' && '.join(validation['init_commands'])
        
        # Prepend initialization to the prompt
        if '--dangerously-skip-permissions' in command:
            # Extract the prompt (last part after flags)
            parts = command.split('"')
            if len(parts) >= 2:
                original_prompt = parts[-2]
                
                # Create enhanced prompt with init verification
                enhanced_prompt = f"""First, verify the environment by running these commands and showing the output:
{chr(10).join(f'- {cmd}' for cmd in validation['init_commands'])}

Then, {original_prompt}"""
                
                # Reconstruct command
                parts[-2] = enhanced_prompt
                new_command = '"'.join(parts)
                
                # Store for WebSocket handler
                r.hset(f"hook:claude_validation:{session_id}", "enhanced_command", new_command)
                logger.info("Enhanced Claude prompt with environment verification")
                
    # Exit successfully - don't block execution
    sys.exit(0)


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{message}")
    
    # Usage example for testing
    if "--test" in sys.argv:
        print("\n=== Claude Instance Pre-Check Test ===\n")
        
        # Test environment validation
        validator = EnvironmentValidator()
        
        print("1. Running all environment checks:\n")
        
        # Working directory check
        cwd_ok, cwd = validator.check_working_directory()
        print(f"✓ Working Directory: {cwd_ok} - {cwd}")
        
        # Virtual environment check
        venv_ok, venv = validator.check_venv_activation()
        print(f"{'✓' if venv_ok else '✗'} Virtual Environment: {venv_ok} - {venv}")
        
        # MCP config check
        mcp_ok, mcp = validator.check_mcp_config()
        print(f"{'✓' if mcp_ok else '✗'} MCP Config: {mcp_ok} - {mcp}")
        
        # Python path check
        path_ok, paths = validator.check_python_path()
        print(f"{'✓' if path_ok else '✗'} Python Path: {path_ok} - {paths}")
        
        # Dependencies check
        deps_ok, deps = validator.check_dependencies()
        print(f"{'✓' if deps_ok else '✗'} Dependencies: {deps_ok} - {deps}")
        
        print("\n2. Summary:")
        print(f"  Checks passed: {len(validator.checks_passed)}")
        print(f"  Checks failed: {len(validator.checks_failed)}")
        print(f"  Fixes applied: {len(validator.fixes_applied)}")
        
        if validator.checks_passed:
            print("\n✓ Passed checks:")
            for check in validator.checks_passed:
                print(f"  - {check}")
                
        if validator.checks_failed:
            print("\n✗ Failed checks:")
            for check in validator.checks_failed:
                print(f"  - {check}")
                
        if validator.fixes_applied:
            print("\n⚡ Fixes applied:")
            for fix in validator.fixes_applied:
                print(f"  - {fix}")
        
        # Generate init commands
        print("\n3. Generated initialization commands:")
        init_commands = validator.generate_init_commands()
        for cmd in init_commands:
            print(f"  $ {cmd}")
            
        # Create validation record
        validation = validator.create_validation_record()
        print(f"\n4. Validation record ready: {validation['ready']}")
        
        # Test command enhancement
        print("\n5. Testing command enhancement:")
        test_command = 'claude -p "What is 2+2?" --dangerously-skip-permissions'
        print(f"Original: {test_command}")
        
        # Simulate enhancement
        if validation['ready']:
            enhanced_prompt = f"""First, verify the environment by running these commands and showing the output:
{chr(10).join(f'- {cmd}' for cmd in validation['init_commands'])}

Then, What is 2+2?"""
            print(f"\nEnhanced prompt:")
            print("---")
            print(enhanced_prompt)
            print("---")
        
        # Test Redis storage (if available)
        print("\n6. Testing Redis storage:")
        try:
            import redis
            r = redis.Redis(decode_responses=True)
            r.ping()
            
            test_session = "test_session_123"
            key = f"hook:claude_validation:{test_session}"
            r.setex(key, 60, json.dumps(validation))
            
            # Verify storage
            stored = r.get(key)
            if stored:
                print(f"✓ Successfully stored validation for session {test_session}")
                stored_data = json.loads(stored)
                print(f"  Project root: {stored_data['project_root']}")
                print(f"  Ready: {stored_data['ready']}")
            
            # Cleanup
            r.delete(key)
            
        except Exception as e:
            print(f"✗ Redis not available: {e}")
        
        print("\n=== Test Complete ===")
    else:
        # Normal hook mode
        main()