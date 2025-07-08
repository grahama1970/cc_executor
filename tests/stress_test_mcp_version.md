# Stress Test: Game Engine Algorithm - MCP TOOL VERSION

This version uses mcp__cc-execute__execute for complex tasks that need fresh context.

## Task Execution List

### Task 1: Historical Research
**Direct execution**: 
```python
await mcp__perplexity-ask__perplexity_ask({
    "messages": [{
        "role": "user", 
        "content": "Research Fast Inverse Square Root (0x5f3759df), modern CPU sqrt implementations, and 2023-2025 advances in approximation algorithms"
    }]
})
# Save findings to research/fast_inverse_sqrt_history.md
```

### Task 2: Mathematical Foundation Research
**Direct execution**:
```python
await mcp__perplexity-ask__perplexity_ask({
    "messages": [{
        "role": "user",
        "content": "Research Newton-Raphson optimizations, lookup table approaches, bit manipulation for floats, recent approximation algorithm papers"
    }]
})
# Save to research/mathematical_approaches.md
```

### Task 3: Algorithm Design Document
**MCP Tool execution**:
```python
await mcp__cc-execute__execute(
    task="Based on research files, design comprehensive algorithm spec for new fast inverse square root using modern CPU features (AVX, FMA), multiple precision levels, theoretical performance analysis, and mathematical derivation. Save as design/new_algorithm_spec.md with detailed pseudocode.",
    timeout=300
)
```

### Task 4: Baseline Implementation
**MCP Tool execution**:
```python
await mcp__cc-execute__execute(
    task="Implement classic Fast Inverse Square Root in Python with original algorithm, comprehensive comments, test cases, and timing utilities. Save as src/baseline_fast_inverse_sqrt.py",
    timeout=180
)
```

### Task 5: Performance Profiling Setup
**Direct execution**: Install packages and create profiling utilities
```bash
pip install numpy numba line_profiler memory_profiler py-spy
# Create benchmarks/profiling_setup.py with timing/memory/cache utilities
```

### Task 6: Novel Algorithm Implementation V1
**MCP Tool execution**:
```python
await mcp__cc-execute__execute(
    task="Implement first version of new algorithm with lookup tables, adaptive precision, SIMD-friendly layouts, and extensive mathematical documentation. Create 200+ lines of optimized code in src/fast_inverse_sqrt_v1.py",
    timeout=600
)
```

### Task 7: Benchmark Suite Creation
**MCP Tool execution**:
```python
await mcp__cc-execute__execute(
    task="Create comprehensive benchmarks testing accuracy (0.001-1000000), single/batch performance, numpy/math/baseline comparison, matplotlib visualizations, edge cases. Save as benchmarks/comprehensive_benchmark.py",
    timeout=480
)
```

### Task 8: Performance Analysis Round 1
**Direct execution**:
```bash
python benchmarks/comprehensive_benchmark.py --iterations 1000000
# Generate reports/performance_analysis_v1.md
```

### Task 9: Algorithm Consultation
**Direct execution**:
```python
await mcp__perplexity-ask__perplexity_ask({
    "messages": [{
        "role": "user",
        "content": f"Given these performance results: {results}, research why certain ranges perform poorly, modern CPU optimizations, game engine optimizations (Unreal/Unity), hardware-specific optimizations"
    }]
})
# Save to research/optimization_insights.md
```

### Task 10: Mathematical Optimization
**MCP Tool execution**:
```python
await mcp__cc-execute__execute(
    task="Create optimized version with polynomial approximation, cache-friendly patterns, CPU-specific paths, auto-vectorization hints, Halley's method error correction. Include theoretical proofs in src/fast_inverse_sqrt_v2.py",
    timeout=600
)
```

### Task 11: JIT Compilation Integration
**MCP Tool execution**:
```python
await mcp__cc-execute__execute(
    task="Create Numba-optimized version with @njit decorators, parallel batch processing, custom LLVM intrinsics, CUDA kernels, and fallbacks. Save as src/fast_inverse_sqrt_jit.py",
    timeout=600
)
```

### Task 12: Game Engine Integration Test
**MCP Tool execution**:
```python
await mcp__cc-execute__execute(
    task="Create realistic game scenario: 3D vector normalization, 10000 object physics, lighting calculations, frame rate comparisons, power consumption estimates. Save as game_engine_test/physics_simulation.py with pygame visualization.",
    timeout=900
)
```

### Task 13: External Review
**Direct execution**:
```python
# Use LiteLLM/Gemini for review
# Review for correctness, stability, optimization opportunities
# Save to reviews/expert_review.md
```

### Task 14: Final Optimization
**MCP Tool execution**:
```python
await mcp__cc-execute__execute(
    task="Implement final version with all optimizations, runtime algorithm selection, thread-safe batch processing, C extension module, error handling, 500+ lines of code. Save as src/fast_inverse_sqrt_final.py and src/fast_inverse_sqrt.c",
    timeout=1200
)
```

### Task 15: Publication Package
**MCP Tool execution**:
```python
await mcp__cc-execute__execute(
    task="Create complete package: documentation, mathematical proofs, benchmark results, visualizations, blog post, academic paper draft, open source guidelines. Save in publication/ directory.",
    timeout=900
)
```