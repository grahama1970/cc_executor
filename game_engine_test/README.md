# Fast Inverse Square Root Implementation

This directory contains a Python implementation of the famous fast inverse square root algorithm, originally used in Quake III Arena.

## Files

- `fast_inv_sqrt.py` - Complete implementation with multiple versions and benchmarks
- `fast_inv_sqrt_comparison.png` - Visual comparison of accuracy and performance

## Implementations

1. **Classic (Quake III)**: Uses the magic number 0x5f3759df with one Newton-Raphson iteration
2. **Optimized**: Uses improved magic number 0x5f375a86 with two iterations for better accuracy
3. **Lookup Table**: Modern approach using pre-calculated values with interpolation

## Running

```bash
python game_engine_test/fast_inv_sqrt.py
```

## Key Findings

- The classic algorithm achieves ~0.12% average error with just one iteration
- The optimized version reduces error to ~0.0003% with two iterations
- Lookup tables provide excellent accuracy (~0.0005% error) with consistent performance
- In Python, the overhead of struct pack/unpack makes the bit-manipulation versions slower than standard methods
- The algorithm's true power is in C/C++ where direct memory access is available

## Algorithm Explanation

The fast inverse square root exploits the IEEE 754 floating-point representation:
1. Treats the float's bit pattern as an integer
2. Uses bit shifting to approximate log₂(x)/2
3. Applies a magic constant to correct for format quirks
4. Refines with Newton-Raphson iteration(s)

The genius is in the magic number, which was discovered through a combination of mathematical analysis and empirical optimization.