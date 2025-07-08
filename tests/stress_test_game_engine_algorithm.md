# Stress Test: Game Engine Fast Inverse Square Root Alternative

## Objective
Create a Python-based algorithm that outperforms the famous Fast Inverse Square Root (Q_rsqrt) algorithm from Quake III. This requires deep research, mathematical innovation, benchmarking, and iterative optimization.

## Test Configuration
- **Total Tasks**: 15
- **Mixed Execution**: Some use cc_execute, others use direct MCP tools
- **Expected Duration**: 45-90 minutes
- **Complexity**: Very High (mathematical research, algorithm development, benchmarking)

## Task List

### Task 1: Historical Research (Direct - perplexity-ask)
**Execution**: Direct MCP tool
**Command**: Use perplexity-ask to research:
- The original Fast Inverse Square Root algorithm (0x5f3759df magic number)
- Modern CPU architectures and their sqrt implementations
- Recent (2023-2025) advances in approximation algorithms
- SIMD instructions for square root operations
Save findings to `research/fast_inverse_sqrt_history.md`

### Task 2: Mathematical Foundation Research (Direct - perplexity-ask)
**Execution**: Direct MCP tool  
**Command**: Use perplexity-ask to research:
- Newton-Raphson method optimizations
- Lookup table approaches for sqrt
- Bit manipulation techniques for floating point
- Recent papers on fast approximation algorithms
Save findings to `research/mathematical_approaches.md`

### Task 3: Algorithm Design Document (cc_execute)
**Execution**: Using cc_execute.md
**Command**: Based on the research in tasks 1-2, design a comprehensive algorithm specification for a new fast inverse square root that:
- Uses modern CPU features (AVX, FMA instructions)
- Implements multiple precision levels (game vs scientific)
- Includes theoretical performance analysis
- Documents the mathematical derivation
Save as `design/new_algorithm_spec.md` with detailed pseudocode and complexity analysis.

### Task 4: Baseline Implementation (cc_execute)
**Execution**: Using cc_execute.md
**Command**: Implement the classic Fast Inverse Square Root in Python with:
- Original algorithm with magic constant
- Comprehensive comments explaining bit manipulation
- Multiple test cases with known values
- Timing utilities for benchmarking
Save as `src/baseline_fast_inverse_sqrt.py`

### Task 5: Performance Profiling Setup (Direct)
**Execution**: Direct
**Command**: Install performance profiling tools:
```bash
pip install numpy numba line_profiler memory_profiler py-spy
```
Create `benchmarks/profiling_setup.py` with utilities for measuring:
- Execution time at nanosecond precision
- Memory usage patterns
- CPU cache performance
- Vectorization opportunities

### Task 6: Novel Algorithm Implementation V1 (cc_execute)
**Execution**: Using cc_execute.md
**Command**: Implement the first version of our new algorithm based on the design doc:
- Use lookup tables for initial approximation
- Implement adaptive precision based on input range
- Add SIMD-friendly data layouts
- Include extensive documentation of the mathematical approach
Save as `src/fast_inverse_sqrt_v1.py` with at least 200 lines of optimized code.

### Task 7: Benchmark Suite Creation (cc_execute)
**Execution**: Using cc_execute.md
**Command**: Create a comprehensive benchmark suite that:
- Tests accuracy across different ranges (0.001 to 1000000)
- Measures performance for single values and batches
- Compares against numpy.sqrt, math.sqrt, and baseline
- Generates visualization plots of error vs performance
- Tests edge cases (denormalized floats, special values)
Save as `benchmarks/comprehensive_benchmark.py` with matplotlib visualizations.

### Task 8: Performance Analysis Round 1 (Direct)
**Execution**: Direct
**Command**: Run the benchmark suite and analyze results:
```bash
python benchmarks/comprehensive_benchmark.py --iterations 1000000
```
Generate performance report at `reports/performance_analysis_v1.md`

### Task 9: Algorithm Consultation (Direct - perplexity-ask)
**Execution**: Direct MCP tool
**Command**: Use perplexity-ask with the performance results to research:
- Why certain input ranges perform poorly
- Modern CPU optimization techniques we missed
- Successful optimizations from game engines (Unreal, Unity)
- Hardware-specific optimizations for AMD/Intel/ARM
Save insights to `research/optimization_insights.md`

### Task 10: Mathematical Optimization (cc_execute)
**Execution**: Using cc_execute.md
**Command**: Based on consultation insights, create an optimized version that:
- Uses polynomial approximation for initial guess
- Implements cache-friendly memory access patterns
- Adds CPU-specific code paths using feature detection
- Includes auto-vectorization hints for compilers
- Implements error correction using Halley's method
Save as `src/fast_inverse_sqrt_v2.py` with theoretical proofs in comments.

### Task 11: JIT Compilation Integration (cc_execute)
**Execution**: Using cc_execute.md
**Command**: Create a Numba-optimized version that:
- Uses @njit decorators for critical paths
- Implements parallel processing for batch operations
- Adds custom LLVM intrinsics for sqrt operations
- Creates GPU kernel for CUDA-capable systems
- Includes fallback for systems without Numba
Save as `src/fast_inverse_sqrt_jit.py` with performance comparisons.

### Task 12: Game Engine Integration Test (cc_execute)
**Execution**: Using cc_execute.md
**Command**: Create a realistic game engine scenario that:
- Implements 3D vector normalization using our algorithm
- Simulates physics calculations (10000 objects)
- Includes lighting calculations requiring sqrt
- Compares frame rates using different sqrt implementations
- Measures power consumption estimates
Save as `game_engine_test/physics_simulation.py` with visual output using pygame.

### Task 13: External Review (Direct - LiteLLM)
**Execution**: Direct MCP tool
**Command**: Use LiteLLM with gemini-2.0-flash-exp to review our implementation:
- Mathematical correctness of approximations
- Potential numerical stability issues
- Optimization opportunities we missed
- Comparison with state-of-the-art implementations
Request specific code improvements and save to `reviews/expert_review.md`

### Task 14: Final Optimization (cc_execute)
**Execution**: Using cc_execute.md
**Command**: Implement the final version incorporating all feedback:
- Apply all optimization suggestions from review
- Add runtime algorithm selection based on input
- Implement thread-safe batch processing
- Create C extension module for critical paths
- Add comprehensive error handling and logging
- Include 500+ lines of highly optimized code
Save as `src/fast_inverse_sqrt_final.py` and `src/fast_inverse_sqrt.c`

### Task 15: Publication Package (cc_execute)
**Execution**: Using cc_execute.md
**Command**: Create a complete package for publication:
- Comprehensive documentation with mathematical proofs
- Benchmark results comparing all versions
- Visualization of accuracy/performance tradeoffs
- Blog post explaining the algorithm for developers
- Academic paper draft with related work section
- Open source license and contribution guidelines
Save in `publication/` directory with README, charts, and LaTeX paper.

## Success Criteria
1. **Algorithm Performance**: At least 20% faster than numpy.sqrt for game engine use cases
2. **Accuracy**: Maximum error < 0.1% for typical game calculations
3. **Robustness**: Handle all edge cases without crashes
4. **Documentation**: Full mathematical derivation and proofs
5. **Integration**: Working game engine demonstration
6. **Research**: Utilize perplexity-ask effectively for cutting-edge insights

## Stress Points
- **Long-running tasks**: Algorithm implementation and benchmarking (5-10 min each)
- **Complex dependencies**: Later tasks depend on earlier research
- **External tool integration**: Multiple MCP tools (perplexity-ask, LiteLLM)
- **Heavy computation**: Benchmarking millions of operations
- **Large file generation**: 500+ line implementations, extensive documentation

## Expected Failures
This stress test is designed to potentially fail at:
- Task 6/10/14: Complex algorithm implementation might timeout
- Task 7: Comprehensive benchmarking might exceed memory limits
- Task 12: Game engine simulation might hit resource constraints
- Task 15: Documentation generation might hit token limits

The goal is to identify where cc_execute breaks down under real-world complexity.