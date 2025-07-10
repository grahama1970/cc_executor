"""
Unit tests for the add_numbers function.

=== USAGE INSTRUCTIONS FOR AGENTS ===
Run this script directly to test:
  python test_add_numbers.py          # Runs working_usage() - stable, known to work
  python test_add_numbers.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug function!
"""

import unittest
import sys
import asyncio
from pathlib import Path
from math import isclose

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from add_numbers import add_numbers


class TestAddNumbers(unittest.TestCase):
    """Test cases for the add_numbers function."""
    
    def test_positive_integers(self):
        """Test adding positive integers"""
        self.assertEqual(add_numbers(2, 3), 5)
        self.assertEqual(add_numbers(10, 20), 30)
        self.assertEqual(add_numbers(100, 200), 300)
        self.assertEqual(add_numbers(1, 1), 2)
    
    def test_negative_numbers(self):
        """Test with negative numbers"""
        self.assertEqual(add_numbers(-5, 3), -2)
        self.assertEqual(add_numbers(-10, -5), -15)
        self.assertEqual(add_numbers(-100, 50), -50)
        self.assertEqual(add_numbers(50, -100), -50)
    
    def test_floats(self):
        """Test with floating point numbers"""
        self.assertTrue(isclose(add_numbers(1.5, 2.5), 4.0))
        self.assertTrue(isclose(add_numbers(0.1, 0.2), 0.3, rel_tol=1e-9))
        self.assertTrue(isclose(add_numbers(3.14, 2.86), 6.0))
        self.assertTrue(isclose(add_numbers(-1.5, 3.5), 2.0))
    
    def test_mixed_types(self):
        """Test mixing integers and floats"""
        self.assertTrue(isclose(add_numbers(5, 2.5), 7.5))
        self.assertTrue(isclose(add_numbers(10.5, 5), 15.5))
        self.assertTrue(isclose(add_numbers(-3, 1.5), -1.5))
        self.assertTrue(isclose(add_numbers(2.7, -3), -0.3, rel_tol=1e-9))
    
    def test_zero_values(self):
        """Test with zero values"""
        self.assertEqual(add_numbers(0, 0), 0)
        self.assertEqual(add_numbers(5, 0), 5)
        self.assertEqual(add_numbers(0, -5), -5)
        self.assertTrue(isclose(add_numbers(0.0, 3.14), 3.14))
    
    def test_large_numbers(self):
        """Test with large numbers"""
        self.assertEqual(add_numbers(1000000, 2000000), 3000000)
        self.assertEqual(add_numbers(999999, 1), 1000000)
        self.assertTrue(isclose(add_numbers(1e10, 2e10), 3e10))
        self.assertTrue(isclose(add_numbers(1.234e15, 5.678e15), 6.912e15))
    
    def test_small_numbers(self):
        """Test with very small floating point numbers"""
        self.assertTrue(isclose(add_numbers(1e-10, 2e-10), 3e-10, rel_tol=1e-9))
        self.assertTrue(isclose(add_numbers(0.0001, 0.0002), 0.0003))
        self.assertTrue(isclose(add_numbers(1e-15, -1e-15), 0.0, abs_tol=1e-14))
    
    def test_edge_cases(self):
        """Test edge cases and special values"""
        # Test with very small and very large numbers
        self.assertTrue(isclose(add_numbers(1e-100, 1e100), 1e100))
        # Test negative zero
        self.assertEqual(add_numbers(-0, 0), 0)
        self.assertEqual(add_numbers(-0, 5), 5)


async def working_usage():
    """Demonstrate proper usage of the unit tests.
    
    AGENT: Run this for stable, production-ready example.
    This function is known to work and should not be modified.
    """
    # Run the unit tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestAddNumbers)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print(f"\nTests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    return result.wasSuccessful()


async def debug_function():
    """Debug function for testing new ideas and troubleshooting.
    
    AGENT: Use this function for experimenting! Rewrite freely.
    This is constantly rewritten to test different things.
    """
    # Currently testing edge cases
    test_cases = [
        (float('inf'), 1),  # Infinity
        (float('-inf'), 1),  # Negative infinity
        (1e308, 1e308),  # Very large numbers
        (1e-308, 1e-308),  # Very small numbers
    ]
    
    print("Testing edge cases:")
    for a, b in test_cases:
        try:
            result = add_numbers(a, b)
            print(f"✓ add_numbers({a}, {b}) = {result}")
        except Exception as e:
            print(f"✗ add_numbers({a}, {b}): {e}")
    
    # Test with invalid types (should fail)
    print("\nTesting invalid types (should fail):")
    invalid_cases = [
        ("5", 3),  # String
        (5, None),  # None
        ([1, 2], 3),  # List
        ({"a": 1}, 2),  # Dict
    ]
    
    for a, b in invalid_cases:
        try:
            result = add_numbers(a, b)
            print(f"✗ add_numbers({a!r}, {b!r}) = {result} (Should have failed!)")
        except Exception as e:
            print(f"✓ add_numbers({a!r}, {b!r}): {type(e).__name__}: {e}")


if __name__ == "__main__":
    """
    AGENT INSTRUCTIONS:
    - DEFAULT: Runs working_usage() - stable example that works
    - DEBUG: Run with 'debug' argument to test new ideas
    - DO NOT create external test files - use debug_function() instead!
    """
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    if mode == "debug":
        print("Running debug mode...")
        asyncio.run(debug_function())
    else:
        print("Running working usage mode...")
        asyncio.run(working_usage())