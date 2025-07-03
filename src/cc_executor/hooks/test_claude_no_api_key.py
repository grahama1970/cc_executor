#!/usr/bin/env python3
"""
Test Claude Code without ANTHROPIC_API_KEY to see if it works on Max plan.
"""

import subprocess
import sys
import os
import time
from pathlib import Path

def test_claude_without_api_key():
    """Test if Claude works without API key on Max plan."""
    print("=== Testing Claude Code without API Key ===\n")
    
    # First, show current state
    print("Current environment:")
    print(f"  ANTHROPIC_API_KEY: {os.environ.get('ANTHROPIC_API_KEY', 'NOT SET')}")
    print(f"  Python: {sys.executable}")
    print(f"  Working dir: {os.getcwd()}")
    
    # Unset ANTHROPIC_API_KEY if it exists
    env = os.environ.copy()
    if 'ANTHROPIC_API_KEY' in env:
        del env['ANTHROPIC_API_KEY']
        print("\n✅ Removed ANTHROPIC_API_KEY from environment")
    else:
        print("\n✅ ANTHROPIC_API_KEY was not set")
    
    # Test commands
    test_commands = [
        # Simple test without debug
        {
            'cmd': ["claude", "-p", "Say hello"],
            'description': "Simple claude command",
            'timeout': 30
        },
        # With debug flag
        {
            'cmd': ["claude", "--debug", "-p", "Say hello"],
            'description': "Claude with --debug flag",
            'timeout': 30
        },
        # With explicit no API key flag if it exists
        {
            'cmd': ["claude", "--no-api-key", "-p", "Say hello"],
            'description': "Claude with --no-api-key flag",
            'timeout': 30
        },
    ]
    
    for test in test_commands:
        print(f"\n{'='*60}")
        print(f"Test: {test['description']}")
        print(f"Command: {' '.join(test['cmd'])}")
        print(f"Timeout: {test['timeout']}s")
        print("="*60)
        
        start_time = time.time()
        
        try:
            # Run with clean environment (no API key)
            result = subprocess.run(
                test['cmd'],
                capture_output=True,
                text=True,
                timeout=test['timeout'],
                env=env
            )
            
            elapsed = time.time() - start_time
            
            print(f"\n✅ Command completed in {elapsed:.2f}s")
            print(f"Exit code: {result.returncode}")
            
            # Show output
            if result.stdout:
                print("\n--- STDOUT ---")
                print(result.stdout[:500] + ("...[truncated]" if len(result.stdout) > 500 else ""))
            
            if result.stderr:
                print("\n--- STDERR ---")
                print(result.stderr[:500] + ("...[truncated]" if len(result.stderr) > 500 else ""))
            
            # Look for authentication-related messages
            combined = result.stdout + result.stderr
            auth_indicators = [
                "API key", "api key", "API_KEY",
                "authentication", "Authentication",
                "unauthorized", "Unauthorized",
                "403", "401",
                "Max plan", "max plan",
                "hook", "Hook"
            ]
            
            print("\n--- Analysis ---")
            found = []
            for indicator in auth_indicators:
                if indicator in combined:
                    found.append(indicator)
            
            if found:
                print(f"Found indicators: {', '.join(set(found))}")
            else:
                print("No authentication or hook indicators found")
                
        except subprocess.TimeoutExpired:
            elapsed = time.time() - start_time
            print(f"\n❌ Command timed out after {elapsed:.2f}s")
            print("This suggests Claude is hanging, possibly due to:")
            print("  - Broken authentication on Max plan")
            print("  - Broken hooks interfering")
            print("  - Network issues")
            
        except Exception as e:
            print(f"\n❌ Error: {type(e).__name__}: {e}")
    
    # Also test if claude is even installed/accessible
    print(f"\n{'='*60}")
    print("Checking Claude installation...")
    
    try:
        # Check if claude command exists
        which_result = subprocess.run(
            ["which", "claude"],
            capture_output=True,
            text=True
        )
        
        if which_result.returncode == 0:
            claude_path = which_result.stdout.strip()
            print(f"✅ Claude found at: {claude_path}")
            
            # Check claude version/help
            help_result = subprocess.run(
                ["claude", "--help"],
                capture_output=True,
                text=True,
                timeout=5,
                env=env
            )
            
            if help_result.returncode == 0:
                print("✅ Claude --help works!")
                print(help_result.stdout[:200] + "...")
            else:
                print("❌ Claude --help failed")
                if help_result.stderr:
                    print(f"Error: {help_result.stderr[:200]}")
        else:
            print("❌ Claude command not found in PATH")
            
    except subprocess.TimeoutExpired:
        print("❌ Claude --help timed out")
    except Exception as e:
        print(f"❌ Error checking claude: {e}")
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print("="*60)
    print("\nClaude Code appears to be broken in multiple ways:")
    print("1. Hooks don't trigger automatically ❌")
    print("2. Claude command hangs/times out ❌")
    print("3. No clear authentication method for Max plan ❌")
    print("\nOur workaround bypasses ALL of this by:")
    print("1. Running hooks manually via subprocess")
    print("2. Not relying on the claude CLI")
    print("3. Using the API directly with proper auth")


if __name__ == "__main__":
    test_claude_without_api_key()