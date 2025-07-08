# Optimization Insights for Fast Inverse Square Root

## 1. Why Certain Input Ranges Perform Poorly with Lookup Tables

Lookup table–based approximations for fast inverse square root often quantize some bits of the floating-point input (usually the exponent and/or high bits of the mantissa) to address the range and then use a precomputed value as a starting guess. Issues arise for input ranges where the table resolution is too coarse or doesn't capture sufficient input detail:

### Key Problems:
- **Coarse Quantization**: If the table is small (to save memory), then wide input intervals map to the same table entry, meaning the approximation can be much less accurate for inputs not closely matching the representative value.
- **Underrepresented Ranges**: Low magnitude or subnormal values, or values near exponent boundaries, may be underrepresented or experience aliasing, resulting in higher relative error for those ranges.
- **Non-Uniform Error Distribution**: Many lookup table methods, especially with ~256KB tables, trade memory for accuracy but cannot deliver uniform error across all exponents and mantissas—some input intervals will be 'hot spots' for higher error.
- **Edge Cases**: Floating-point numbers are not uniformly distributed in raw bit space, so edge cases or denormals are especially problematic, since they're less frequently addressed in table construction and can overflow or underflow during the approximation steps.

## 2. Modern CPU Optimization Techniques

Modern CPUs (2024–2025) offer several ways to accelerate inverse square root calculations:

### Hardware Acceleration:
- **Vector Instructions**: Many CPUs have fast, native instructions like `RSQRTPS`/`VRSQRTPS` (for single-precision) and their AVX/AVX-512 variants, enabling simultaneous processing of 4–16 floats per call. These are much faster and can be followed by one Newton-Raphson step for improved precision if needed.

### SIMD Optimization:
- **Batch Processing**: Arranging data so that batch processing with SIMD instructions can be used efficiently (e.g., processing 8 floats at once in AVX2, 16 at once in AVX-512).

### Memory Optimization:
- **Cache Locality**: Optimize lookup tables for cache friendliness; 256KB can fit in L2/L3 cache on many CPUs, but ensuring hot-data stays in L1D/L2 is preferable.
- **Software Pipelining and Prefetching**: Overlap table lookup, arithmetic, and Newton steps when possible.

### Computational Optimization:
- **FMA (Fused Multiply-Add)**: FMA instructions can reduce rounding errors and improve both throughput and accuracy for the Newton-Raphson step.
- **Mixed Precision and Adaptive Refinement**: Start with a fast, low-precision estimate and refine only for those inputs where the error threshold is exceeded, based on a quick test.

## 3. Game Engine Optimizations (2024-2025)

Modern game engines prioritize hardware-accelerated, SIMD-based vector math for operations like normalization and inverse square root:

### Current Best Practices:
- **Hardware rsqrt**: Most engines now delegate to platform-provided vector math libraries or use direct CPU intrinsics (`_mm_rsqrt_ps`, `_mm256_rsqrt_ps`, etc.), sometimes wrapped in cross-platform abstraction layers to maximize portability and performance.
- **Selective Refinement**: Engines often perform a single Newton-Raphson iteration after the hardware rsqrt for higher accuracy only where needed, such as in physically based rendering or physics, and skip it for less-critical code paths.
- **SIMD-Friendly Data Layouts**: Structure-of-arrays (SoA) layouts are used to maximize SIMD efficiency—vectors to be normalized are packed for batch rsqrt.
- **Adaptive Paths**: Some engines dynamically select between hardware rsqrt and table-based approximations, based on detected CPU features, data alignment, and target accuracy.
- **GPU Offloading**: For workloads heavily using normalization (e.g., shaders), the operation is usually moved to the GPU, using native GPU rsqrt instructions, which are faster and more parallel.
- **Deprecated Table-Based Approaches**: Generally deprecated except on platforms with no fast hardware support or very stringent determinism requirements; when used, table size is tuned to fit cache, and secondary steps address out-of-table or high-error ranges.

## Technical Recommendations for Algorithm Improvement

### 1. Exploit SIMD
Restructure your algorithm to operate on batches of values at once, leveraging AVX2/AVX-512 or ARM NEON on target platforms.

### 2. Use Hardware rsqrt + 1 NR Step
This combination is, on modern CPUs, both more accurate and much faster than manual bit-hack or table-based approaches.

### 3. Profile and Tune Table Size
If using a table, profile actual input distributions, and possibly use non-uniform quantization (denser near 1, sparser elsewhere) to minimize max error for real-world data.

### 4. Implement Hybrid Method
For platforms where hardware is not best, combine a small, high-accuracy table for the most common exponent ranges with a fast NR refinement to keep error low everywhere.

### 5. Guard Outlier Cases
Explicitly check for subnormals, zeros, and infinities to avoid catastrophic errors, especially if table-approximation is used.

## Conclusion

Modern best practice for inverse square root is to prefer hardware SIMD instructions supplemented by a single Newton-Raphson iteration, using table-based methods only in legacy or highly specialized cases. Fine-tune memory/cache trade-offs and always validate error distributions across the full input space.

The performance results showing higher error in FAST mode despite being slower than expected suggest that the lookup table approach may be hitting cache miss penalties or suffering from poor quantization for certain input ranges. The recommendation is to move toward hardware-accelerated approaches with adaptive refinement based on accuracy requirements.

## References
- [Fast inverse square root - Wikipedia](https://en.wikipedia.org/wiki/Fast_inverse_square_root)
- [RSQRT Performance Analysis](https://hllmn.net/blog/2023-04-20_rsqrt/)
- [Square root algorithms](https://en.wikipedia.org/wiki/Square_root_algorithms)

Optimization insights saved to research/optimization_insights.md