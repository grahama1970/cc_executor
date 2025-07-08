"""
Original Quake III Fast Inverse Square Root Algorithm
=====================================================

This is a reference implementation of the famous fast inverse square root
algorithm from Quake III Arena, adapted to Python.

The algorithm computes 1/sqrt(x) using bit manipulation and Newton-Raphson
iterations, avoiding the expensive sqrt() operation.
"""

import struct
import numpy as np


def original_fast_inverse_sqrt(number: float) -> float:
    """
    Original Quake III fast inverse square root algorithm.
    
    This algorithm uses the famous "magic constant" 0x5f3759df
    and performs bit manipulation to approximate 1/sqrt(x).
    
    Args:
        number: The input number to compute 1/sqrt(x) for
        
    Returns:
        Approximation of 1/sqrt(number)
    """
    # Convert float to raw bits
    i = struct.unpack('>l', struct.pack('>f', number))[0]
    
    # Magic bit hack - the famous constant
    i = 0x5f3759df - (i >> 1)
    
    # Convert back to float
    y = struct.unpack('>f', struct.pack('>l', i))[0]
    
    # Newton-Raphson iteration (once is usually enough)
    y = y * (1.5 - (number * 0.5 * y * y))
    
    return y


def original_fast_inverse_sqrt_improved(number: float) -> float:
    """
    Improved version with better magic constant and double iteration.
    
    Uses Chris Lomont's improved magic constant 0x5f375a86
    which provides slightly better accuracy.
    
    Args:
        number: The input number to compute 1/sqrt(x) for
        
    Returns:
        More accurate approximation of 1/sqrt(number)
    """
    # Convert float to raw bits
    i = struct.unpack('>l', struct.pack('>f', number))[0]
    
    # Improved magic constant
    i = 0x5f375a86 - (i >> 1)
    
    # Convert back to float
    y = struct.unpack('>f', struct.pack('>l', i))[0]
    
    # Two Newton-Raphson iterations for better accuracy
    y = y * (1.5 - (number * 0.5 * y * y))
    y = y * (1.5 - (number * 0.5 * y * y))
    
    return y


if __name__ == "__main__":
    # Test the algorithms
    test_values = [4.0, 16.0, 25.0, 100.0, 0.25, 0.5, 2.0]
    
    print("Original Quake III Fast Inverse Square Root Tests")
    print("=" * 50)
    
    for x in test_values:
        original = original_fast_inverse_sqrt(x)
        improved = original_fast_inverse_sqrt_improved(x)
        actual = 1.0 / np.sqrt(x)
        
        print(f"\nInput: {x}")
        print(f"Original: {original:.6f}")
        print(f"Improved: {improved:.6f}")
        print(f"Actual:   {actual:.6f}")
        print(f"Original Error: {abs(original - actual):.6f} ({abs(original - actual)/actual*100:.2f}%)")
        print(f"Improved Error: {abs(improved - actual):.6f} ({abs(improved - actual)/actual*100:.2f}%)")