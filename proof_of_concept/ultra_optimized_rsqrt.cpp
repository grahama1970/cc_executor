#include <iostream>
#include <chrono>
#include <cmath>
#include <immintrin.h>
#include <vector>
#include <iomanip>
#include <cstring>
#include <array>

// Original fast inverse square root for comparison
float Q_rsqrt(float number) {
    long i;
    float x2, y;
    const float threehalfs = 1.5F;
    x2 = number * 0.5F;
    y  = number;
    i  = * ( long * ) &y;
    i  = 0x5f3759df - ( i >> 1 );
    y  = * ( float * ) &i;
    y  = y * ( threehalfs - ( x2 * y * y ) );
    return y;
}

// Standard library version
float std_rsqrt(float number) {
    return 1.0f / std::sqrt(number);
}

// ============================================================================
// ULTRA-OPTIMIZED HYBRID INVERSE SQUARE ROOT ALGORITHM
// ============================================================================
// This algorithm achieves superior performance through:
// 1. Hardware intrinsic rsqrt approximation (14-bit precision)
// 2. Single Newton-Raphson iteration for 23-bit precision
// 3. Vectorized processing with AVX2/FMA
// 4. Branch-free design
// 5. Optimal instruction scheduling

// Single precision using hardware intrinsics
inline float ultra_rsqrt(float x) {
    #ifdef __SSE__
    // Use hardware rsqrt approximation
    __m128 xmm = _mm_set_ss(x);
    __m128 rsqrt = _mm_rsqrt_ss(xmm);
    
    // One Newton-Raphson iteration for full precision
    // rsqrt = rsqrt * (1.5 - 0.5 * x * rsqrt * rsqrt)
    const __m128 half = _mm_set_ss(0.5f);
    const __m128 three_halves = _mm_set_ss(1.5f);
    
    __m128 x_half = _mm_mul_ss(xmm, half);
    __m128 rsqrt_sq = _mm_mul_ss(rsqrt, rsqrt);
    __m128 tmp = _mm_mul_ss(x_half, rsqrt_sq);
    tmp = _mm_sub_ss(three_halves, tmp);
    rsqrt = _mm_mul_ss(rsqrt, tmp);
    
    return _mm_cvtss_f32(rsqrt);
    #else
    // Fallback to optimized bit manipulation
    union { float f; uint32_t i; } conv = { .f = x };
    conv.i = 0x5f375a86 - (conv.i >> 1);
    float y = conv.f;
    
    // Two iterations for accuracy
    y = y * (1.5f - 0.5f * x * y * y);
    y = y * (1.5f - 0.5f * x * y * y);
    return y;
    #endif
}

// Vectorized version processing 8 floats at once
void ultra_rsqrt_avx2(const float* input, float* output, size_t count) {
    const __m256 half = _mm256_set1_ps(0.5f);
    const __m256 three_halves = _mm256_set1_ps(1.5f);
    
    size_t simd_count = count & ~7;
    
    for (size_t i = 0; i < simd_count; i += 8) {
        // Load 8 values
        __m256 x = _mm256_loadu_ps(&input[i]);
        
        // Hardware rsqrt approximation (14-bit precision)
        __m256 rsqrt = _mm256_rsqrt_ps(x);
        
        // Newton-Raphson iteration with FMA
        #ifdef __FMA__
        // rsqrt = rsqrt * (1.5 - 0.5 * x * rsqrt^2)
        __m256 x_half = _mm256_mul_ps(x, half);
        __m256 tmp = _mm256_fnmadd_ps(_mm256_mul_ps(x_half, rsqrt), rsqrt, three_halves);
        rsqrt = _mm256_mul_ps(rsqrt, tmp);
        #else
        // Without FMA
        __m256 x_half = _mm256_mul_ps(x, half);
        __m256 rsqrt_sq = _mm256_mul_ps(rsqrt, rsqrt);
        __m256 tmp = _mm256_mul_ps(x_half, rsqrt_sq);
        tmp = _mm256_sub_ps(three_halves, tmp);
        rsqrt = _mm256_mul_ps(rsqrt, tmp);
        #endif
        
        // Store result
        _mm256_storeu_ps(&output[i], rsqrt);
    }
    
    // Handle remaining elements
    for (size_t i = simd_count; i < count; i++) {
        output[i] = ultra_rsqrt(input[i]);
    }
}

// Even more optimized: Process 16 floats with AVX-512 (if available)
#ifdef __AVX512F__
void ultra_rsqrt_avx512(const float* input, float* output, size_t count) {
    const __m512 half = _mm512_set1_ps(0.5f);
    const __m512 three_halves = _mm512_set1_ps(1.5f);
    
    size_t simd_count = count & ~15;
    
    for (size_t i = 0; i < simd_count; i += 16) {
        __m512 x = _mm512_loadu_ps(&input[i]);
        __m512 rsqrt = _mm512_rsqrt14_ps(x);
        
        // Newton-Raphson with FMA
        __m512 x_half = _mm512_mul_ps(x, half);
        __m512 tmp = _mm512_fnmadd_ps(_mm512_mul_ps(x_half, rsqrt), rsqrt, three_halves);
        rsqrt = _mm512_mul_ps(rsqrt, tmp);
        
        _mm512_storeu_ps(&output[i], rsqrt);
    }
    
    // Handle remaining with AVX2
    ultra_rsqrt_avx2(&input[simd_count], &output[simd_count], count - simd_count);
}
#endif

// Benchmark functions
template<typename Func>
double benchmark_single(Func func, const std::vector<float>& data, int iterations) {
    auto start = std::chrono::high_resolution_clock::now();
    
    float sum = 0.0f;
    for (int i = 0; i < iterations; i++) {
        for (float val : data) {
            sum += func(val);
        }
    }
    
    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double, std::milli> duration = end - start;
    
    if (sum == 0.0f) std::cout << "Prevented optimization\n";
    
    return duration.count();
}

double benchmark_simd(const std::vector<float>& data, int iterations, bool use_avx512 = false) {
    size_t aligned_size = (data.size() + 15) & ~15;
    std::vector<float> aligned_input(aligned_size);
    std::vector<float> aligned_output(aligned_size);
    
    std::copy(data.begin(), data.end(), aligned_input.begin());
    
    auto start = std::chrono::high_resolution_clock::now();
    
    for (int i = 0; i < iterations; i++) {
        #ifdef __AVX512F__
        if (use_avx512) {
            ultra_rsqrt_avx512(aligned_input.data(), aligned_output.data(), aligned_input.size());
        } else
        #endif
        {
            ultra_rsqrt_avx2(aligned_input.data(), aligned_output.data(), aligned_input.size());
        }
    }
    
    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double, std::milli> duration = end - start;
    
    float sum = 0.0f;
    for (size_t i = 0; i < data.size(); i++) sum += aligned_output[i];
    if (sum == 0.0f) std::cout << "Prevented optimization\n";
    
    return duration.count();
}

// Game engine demonstrations
namespace GameEngine {
    // Fast vector normalization for physics
    struct Vec3 {
        float x, y, z;
        
        void normalize() {
            float len_sq = x*x + y*y + z*z;
            float inv_len = ultra_rsqrt(len_sq);
            x *= inv_len;
            y *= inv_len;
            z *= inv_len;
        }
    };
    
    // Batch normalize for particle systems
    void normalize_particle_velocities(Vec3* particles, size_t count) {
        // Extract magnitudes
        std::vector<float> magnitudes(count);
        for (size_t i = 0; i < count; i++) {
            magnitudes[i] = particles[i].x * particles[i].x + 
                          particles[i].y * particles[i].y + 
                          particles[i].z * particles[i].z;
        }
        
        // Batch compute inverse magnitudes
        std::vector<float> inv_magnitudes(count);
        ultra_rsqrt_avx2(magnitudes.data(), inv_magnitudes.data(), count);
        
        // Apply normalization
        for (size_t i = 0; i < count; i++) {
            particles[i].x *= inv_magnitudes[i];
            particles[i].y *= inv_magnitudes[i];
            particles[i].z *= inv_magnitudes[i];
        }
    }
    
    // Distance calculations for AI/physics
    float fast_distance(const Vec3& a, const Vec3& b) {
        float dx = a.x - b.x;
        float dy = a.y - b.y;
        float dz = a.z - b.z;
        float dist_sq = dx*dx + dy*dy + dz*dz;
        return 1.0f / ultra_rsqrt(dist_sq);
    }
}

int main() {
    std::cout << "Ultra-Optimized Hybrid Inverse Square Root Algorithm\n";
    std::cout << "===================================================\n\n";
    
    // Detect CPU features
    std::cout << "CPU Feature Detection:\n";
    std::cout << "SSE:     " << ((__builtin_cpu_supports("sse") ? "Yes" : "No")) << "\n";
    std::cout << "AVX2:    " << ((__builtin_cpu_supports("avx2") ? "Yes" : "No")) << "\n";
    std::cout << "FMA:     " << ((__builtin_cpu_supports("fma") ? "Yes" : "No")) << "\n";
    #ifdef __AVX512F__
    std::cout << "AVX-512: Yes\n";
    #else
    std::cout << "AVX-512: No\n";
    #endif
    std::cout << "\n";
    
    // Test correctness
    float test_values[] = {0.25f, 0.5f, 1.0f, 2.0f, 4.0f, 16.0f, 25.0f, 100.0f, 1000.0f};
    
    std::cout << "Correctness Test:\n";
    std::cout << std::setw(12) << "Input" 
              << std::setw(18) << "Q_rsqrt" 
              << std::setw(18) << "ultra_rsqrt"
              << std::setw(18) << "std_rsqrt" 
              << std::setw(18) << "Error %\n";
    
    for (float val : test_values) {
        float q_result = Q_rsqrt(val);
        float u_result = ultra_rsqrt(val);
        float std_result = std_rsqrt(val);
        float error = std::abs((u_result - std_result) / std_result) * 100.0f;
        
        std::cout << std::setw(12) << val 
                  << std::setw(18) << q_result 
                  << std::setw(18) << u_result
                  << std::setw(18) << std_result 
                  << std::setw(17) << error << "%\n";
    }
    
    // Performance benchmark
    std::cout << "\nPerformance Benchmark (10M elements, 100 iterations):\n";
    
    // Generate test data
    std::vector<float> test_data;
    test_data.reserve(10000000);
    
    // Mix of ranges common in games
    for (int i = 0; i < 10000000; i++) {
        int base = (i % 4);
        switch (base) {
            case 0: test_data.push_back(0.1f + (i % 100) * 0.01f); break;   // Small
            case 1: test_data.push_back(1.0f + (i % 100) * 0.1f); break;    // Medium
            case 2: test_data.push_back(10.0f + (i % 100) * 1.0f); break;   // Large
            case 3: test_data.push_back(100.0f + (i % 100) * 10.0f); break; // Very large
        }
    }
    
    const int iterations = 100;
    
    double q_time = benchmark_single(Q_rsqrt, test_data, iterations);
    double u_time = benchmark_single(ultra_rsqrt, test_data, iterations);
    double std_time = benchmark_single(std_rsqrt, test_data, iterations);
    double avx2_time = benchmark_simd(test_data, iterations, false);
    
    #ifdef __AVX512F__
    double avx512_time = benchmark_simd(test_data, iterations, true);
    #endif
    
    std::cout << "\nTiming Results:\n";
    std::cout << "Q_rsqrt:        " << q_time << " ms\n";
    std::cout << "ultra_rsqrt:    " << u_time << " ms\n";
    std::cout << "std_rsqrt:      " << std_time << " ms\n";
    std::cout << "ultra AVX2:     " << avx2_time << " ms\n";
    #ifdef __AVX512F__
    std::cout << "ultra AVX-512:  " << avx512_time << " ms\n";
    #endif
    
    std::cout << "\nSpeedup Analysis:\n";
    std::cout << "ultra_rsqrt vs Q_rsqrt:    " << q_time / u_time << "x\n";
    std::cout << "ultra_rsqrt vs std_rsqrt:  " << std_time / u_time << "x\n";
    std::cout << "ultra AVX2 vs Q_rsqrt:     " << q_time / avx2_time << "x\n";
    std::cout << "ultra AVX2 vs std_rsqrt:   " << std_time / avx2_time << "x\n";
    #ifdef __AVX512F__
    std::cout << "ultra AVX-512 vs Q_rsqrt:  " << q_time / avx512_time << "x\n";
    std::cout << "ultra AVX-512 vs std:      " << std_time / avx512_time << "x\n";
    #endif
    
    // Game engine demonstrations
    std::cout << "\nGame Engine Use Cases:\n\n";
    
    // 1. Single vector normalization
    std::cout << "1. Vector Normalization (Physics):\n";
    GameEngine::Vec3 velocity = {3.0f, 4.0f, 0.0f};
    std::cout << "   Original: (" << velocity.x << ", " << velocity.y << ", " << velocity.z << ")\n";
    velocity.normalize();
    std::cout << "   Normalized: (" << velocity.x << ", " << velocity.y << ", " << velocity.z << ")\n";
    float mag = std::sqrt(velocity.x*velocity.x + velocity.y*velocity.y + velocity.z*velocity.z);
    std::cout << "   Magnitude: " << mag << " (should be ~1.0)\n\n";
    
    // 2. Batch particle normalization
    std::cout << "2. Particle System (1000 particles):\n";
    std::vector<GameEngine::Vec3> particles(1000);
    for (int i = 0; i < 1000; i++) {
        particles[i] = {(float)(i % 10), (float)(i % 7), (float)(i % 13)};
    }
    
    auto start = std::chrono::high_resolution_clock::now();
    GameEngine::normalize_particle_velocities(particles.data(), particles.size());
    auto end = std::chrono::high_resolution_clock::now();
    
    std::chrono::duration<double, std::micro> duration = end - start;
    std::cout << "   Batch normalized 1000 particles in " << duration.count() << " microseconds\n";
    std::cout << "   Sample particle[500] magnitude: " 
              << std::sqrt(particles[500].x*particles[500].x + 
                          particles[500].y*particles[500].y + 
                          particles[500].z*particles[500].z) << "\n\n";
    
    // 3. Distance calculation
    std::cout << "3. Fast Distance Calculation (AI/Physics):\n";
    GameEngine::Vec3 player = {10.0f, 0.0f, 5.0f};
    GameEngine::Vec3 enemy = {15.0f, 0.0f, 8.0f};
    float dist = GameEngine::fast_distance(player, enemy);
    std::cout << "   Distance between player and enemy: " << dist << "\n";
    std::cout << "   Standard calculation: " 
              << std::sqrt((15-10)*(15-10) + 0*0 + (8-5)*(8-5)) << "\n";
    
    std::cout << "\nMathematical Basis:\n";
    std::cout << "The algorithm uses hardware rsqrt approximation followed by\n";
    std::cout << "Newton-Raphson iteration: y = y * (1.5 - 0.5 * x * y²)\n";
    std::cout << "This converges quadratically to 1/√x with each iteration.\n";
    
    return 0;
}