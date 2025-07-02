#!/usr/bin/env python3
"""
Test runner for security enhancement tests.
Runs the unit tests for hook integration and websocket error propagation.
"""

import subprocess
import sys
import os

def run_tests():
    """Run the security unit tests."""
    print("=" * 60)
    print("Running Security Enhancement Unit Tests")
    print("=" * 60)
    
    # Change to tests directory
    test_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(test_dir)
    
    tests = [
        ("Hook Integration Security", "test_hook_integration_security.py"),
        ("WebSocket Error Propagation", "test_websocket_error_propagation.py")
    ]
    
    all_passed = True
    
    for test_name, test_file in tests:
        print(f"\n### Running {test_name} ###")
        print("-" * 40)
        
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"],
            capture_output=True,
            text=True
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
            
        if result.returncode != 0:
            all_passed = False
            print(f"❌ {test_name} FAILED")
        else:
            print(f"✅ {test_name} PASSED")
            
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All security tests PASSED!")
    else:
        print("❌ Some tests FAILED!")
        sys.exit(1)
        
    return all_passed


if __name__ == "__main__":
    run_tests()