# Matrix Multiplication Performance Analysis Report

## 1. Overview

This report details the findings of a multi-turn conversational research process to determine the fastest and most optimized method for multiplying two matrices in Python. The process involved an initial research phase using the `perplexity-ask` tool, followed by the creation and execution of a benchmark script to empirically validate the findings.

## 2. Turn 1: Initial Concurrent Research

The initial prompt instructed a `claude` instance to concurrently research the question using both `perplexity-ask` and `gemini-cli`. The `claude` instance correctly identified that `gemini-cli` was not available and proceeded with `perplexity-ask` and its own web search capabilities.

### 2.1. Synthesized Research from Claude

The primary finding was that for most use cases, **NumPy** is the standard and most optimized method due to its reliance on underlying compiled libraries (BLAS/LAPACK). The research also correctly identified that specialized libraries like **SciPy** should be used for sparse matrices and that advanced algorithms like **Strassen's** are only relevant for very large integer matrices.

### 2.2. Raw JSON Response from the `claude` instance

```json
{
    "type": "result",
    "subtype": "success",
    "is_error": false,
    "duration_ms": 48635,
    "duration_api_ms": 16846,
    "num_turns": 4,
    "result": "**NumPy's `@` operator or `numpy.matmul`** is the fastest method for matrix multiplication in Python, offering ~1,200x speedup over naive Python loops.\n\n```python\nimport numpy as np\nC = A @ B  # or np.matmul(A, B)\n```\n\nFor very large integer-only matrices, specialized Strassen algorithms can be 8-30x faster than NumPy, but NumPy remains optimal for general use with floating-point data.",
    "session_id": "af7d2169-5236-4f7f-976a-5a5de8054bfe",
    "total_cost_usd": 0.6332553000000001,
    "usage": {
        "input_tokens": 11,
        "cache_creation_input_tokens": 30396,
        "cache_read_input_tokens": 27297,
        "output_tokens": 245,
        "server_tool_use": {
            "web_search_requests": 0
        }
    }
}
```

## 3. Turn 2: Benchmark Execution and Feedback

Based on the research, a benchmark script was created and executed. The script compared the performance of NumPy, SciPy (for sparse matrices), and a pure Python implementation.

### 3.1. Benchmark Code (`/tmp/benchmark_matmul.py`)

```python
import numpy as np
import scipy.sparse as sp
import time

def multiply_pure_python(A, B):
    """Multiplies two dense matrices using pure Python loops."""
    rows_A, cols_A = len(A), len(A[0])
    rows_B, cols_B = len(B), len(B[0])
    if cols_A != rows_B:
        raise ValueError("Incompatible dimensions")
    C = [[0 for _ in range(cols_B)] for _ in range(rows_A)]
    for i in range(rows_A):
        for j in range(cols_B):
            for k in range(cols_A):
                C[i][j] += A[i][k] * B[k][j]
    return C

if __name__ == "__main__":
    size = 512
    density = 0.01
    print(f"--- Matrix Multiplication Benchmark ({size}x{size}) ---\n")

    # --- 1. Dense Matrix Benchmark (NumPy vs. Pure Python) ---
    print(f"1. DENSE MATRIX (size={size}x{size})")
    A_dense = np.random.rand(size, size)
    B_dense = np.random.rand(size, size)

    # NumPy
    start_time = time.time()
    C_numpy = A_dense @ B_dense
    duration_np = time.time() - start_time
    print(f"   - NumPy (@ operator):      {duration_np:.6f} seconds")

    # Pure Python
    A_py = A_dense.tolist()
    B_py = B_dense.tolist()
    start_time = time.time()
    C_python = multiply_pure_python(A_py, B_py)
    duration_py = time.time() - start_time
    print(f"   - Pure Python (loops):     {duration_py:.6f} seconds")
    
    # Verification
    assert np.allclose(C_numpy, C_python)
    print(f"   - Verification:            OK")
    print(f"   - NumPy Speedup:           {duration_py / duration_np:.2f}x")

    # --- 2. Sparse Matrix Benchmark (SciPy vs. NumPy) ---
    print(f"\n2. SPARSE MATRIX (size={size}x{size}, density={density*100}%)")
    A_sparse = sp.random(size, size, density=density, format='csr')
    B_sparse = sp.random(size, size, density=density, format='csr')

    # SciPy Sparse
    start_time = time.time()
    C_scipy = A_sparse @ B_sparse
    duration_sp = time.time() - start_time
    print(f"   - SciPy (sparse @):        {duration_sp:.6f} seconds")

    # Convert to dense for NumPy comparison
    A_dense_from_sparse = A_sparse.toarray()
    B_dense_from_sparse = B_sparse.toarray()
    
    # NumPy on dense equivalent
    start_time = time.time()
    C_numpy_from_sparse = A_dense_from_sparse @ B_dense_from_sparse
    duration_np_from_sparse = time.time() - start_time
    print(f"   - NumPy (on dense array):  {duration_np_from_sparse:.6f} seconds")

    # Verification
    assert np.allclose(C_scipy.toarray(), C_numpy_from_sparse)
    print(f"   - Verification:            OK")
    if duration_sp > 0:
        print(f"   - SciPy vs NumPy Speedup:  {duration_np_from_sparse / duration_sp:.2f}x")

    print("\n--- Benchmark Complete ---")
```

### 3.2. Benchmark Results (Feedback)

```
--- Matrix Multiplication Benchmark (512x512) ---

1. DENSE MATRIX (size=512x512)
   - NumPy (@ operator):      0.035088 seconds
   - Pure Python (loops):     14.033222 seconds
   - Verification:            OK
   - NumPy Speedup:           399.95x

2. SPARSE MATRIX (size=512x512, density=1.0%)
   - SciPy (sparse @):        0.000229 seconds
   - NumPy (on dense array):  0.006449 seconds
   - Verification:            OK
   - SciPy vs NumPy Speedup:  28.15x

--- Benchmark Complete ---
```

## 4. Final Conclusion for Researchers

The conversational research process has definitively answered the question. The optimal method for matrix multiplication in Python is context-dependent:

- **For dense matrices, use NumPy.** It provides a speedup of several orders of magnitude over pure Python (~400x in our test).
- **For sparse matrices, use SciPy's sparse modules.** They are significantly more performant than using NumPy on a dense representation of the same data (~28x faster in our test).

This concludes the research and feedback cycle.

```