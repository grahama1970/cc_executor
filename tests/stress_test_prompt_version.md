# Stress Test: Game Engine Algorithm - PROMPT REFERENCE VERSION

This version uses "Using cc_execute.md:" for complex tasks that need fresh context.

## Task Execution List

### Task 1: Historical Research
**Direct execution**: Use mcp__perplexity-ask__perplexity_ask to research the Fast Inverse Square Root algorithm, modern CPU architectures, and recent advances in approximation algorithms. Save findings to research/fast_inverse_sqrt_history.md

### Task 2: Mathematical Foundation Research  
**Direct execution**: Use mcp__perplexity-ask__perplexity_ask to research Newton-Raphson optimizations, lookup tables, bit manipulation, and recent papers. Save to research/mathematical_approaches.md

### Task 3: Algorithm Design Document
**Using cc_execute.md**: Based on the research files, design a comprehensive algorithm specification for a new fast inverse square root that uses modern CPU features (AVX, FMA), implements multiple precision levels, includes theoretical performance analysis, and documents the mathematical derivation. Save as design/new_algorithm_spec.md with detailed pseudocode.

### Task 4: Baseline Implementation
**Using cc_execute.md**: Implement the classic Fast Inverse Square Root in Python with the original algorithm, comprehensive comments, test cases, and timing utilities. Save as src/baseline_fast_inverse_sqrt.py

### Task 5: Performance Profiling Setup
**Direct execution**: Install numpy numba line_profiler memory_profiler py-spy. Create benchmarks/profiling_setup.py with nanosecond timing, memory profiling, and cache analysis utilities.

### Task 6: Novel Algorithm Implementation V1
**Using cc_execute.md**: Implement the first version of our new algorithm with lookup tables, adaptive precision, SIMD-friendly layouts, and extensive mathematical documentation. Create at least 200 lines of optimized code in src/fast_inverse_sqrt_v1.py

### Task 7: Benchmark Suite Creation
**Using cc_execute.md**: Create comprehensive benchmarks testing accuracy across ranges 0.001-1000000, measuring single/batch performance, comparing against numpy/math/baseline, generating matplotlib visualizations, and testing edge cases. Save as benchmarks/comprehensive_benchmark.py

### Task 8: Performance Analysis Round 1
**Direct execution**: Run python benchmarks/comprehensive_benchmark.py --iterations 1000000 and generate reports/performance_analysis_v1.md

### Task 9: Algorithm Consultation
**Direct execution**: Use mcp__perplexity-ask__perplexity_ask with performance results to research optimization opportunities. Save to research/optimization_insights.md

### Task 10: Mathematical Optimization
**Using cc_execute.md**: Create optimized version with polynomial approximation, cache-friendly patterns, CPU-specific paths, auto-vectorization hints, and Halley's method error correction. Include theoretical proofs in src/fast_inverse_sqrt_v2.py

### Task 11: JIT Compilation Integration
**Using cc_execute.md**: Create Numba-optimized version with @njit decorators, parallel batch processing, custom LLVM intrinsics, CUDA kernels, and fallbacks. Save as src/fast_inverse_sqrt_jit.py

### Task 12: Game Engine Integration Test
**Using cc_execute.md**: Create realistic game scenario with 3D vector normalization, 10000 object physics simulation, lighting calculations, frame rate comparisons, and power consumption estimates. Save as game_engine_test/physics_simulation.py with pygame visualization.

### Task 13: External Review
**Direct execution**: Use LiteLLM/Gemini to review implementation for correctness, stability, and optimization opportunities. Save to reviews/expert_review.md

### Task 14: Final Optimization
**Using cc_execute.md**: Implement final version with all optimizations, runtime algorithm selection, thread-safe batch processing, C extension module, error handling, and 500+ lines of optimized code. Save as src/fast_inverse_sqrt_final.py and src/fast_inverse_sqrt.c

### Task 15: Publication Package
**Using cc_execute.md**: Create complete package with documentation, mathematical proofs, benchmark results, visualizations, blog post, academic paper draft, and open source guidelines. Save in publication/ directory.