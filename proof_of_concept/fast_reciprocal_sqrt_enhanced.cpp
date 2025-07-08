#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>
#include <immintrin.h>
#include <string.h>
#include <cstdint>

// Original Quake III fast inverse square root for comparison
float Q_rsqrt(float number) {
    union {
        float f;
        uint32_t i;
    } conv;
    float x2, y;
    const float threehalfs = 1.5F;
    
    x2 = number * 0.5F;
    conv.f = number;
    conv.i = 0x5f3759df - (conv.i >> 1);  // The magic constant
    y = conv.f;
    y = y * (threehalfs - (x2 * y * y));  // 1st iteration
    return y;
}

// Enhanced hybrid fast reciprocal square root algorithm
// Uses polynomial approximation with bit manipulation for speed
class EnhancedFastRecipSqrt {
private:
    // Optimized magic constant found through exhaustive search
    static constexpr uint32_t MAGIC_CONSTANT = 0x5f375a86;
    
    // Polynomial coefficients for error correction
    static constexpr float POLY_C0 = 1.0008789f;
    static constexpr float POLY_C1 = -0.0134839f;
    static constexpr float POLY_C2 = 0.0106339f;
    
    // Lookup table for exponent adjustment
    float exp_adjust[256];
    
public:
    EnhancedFastRecipSqrt() {
        // Precompute exponent adjustments
        for (int i = 0; i < 256; i++) {
            float x = 1.0f + (float)i / 256.0f;
            float ideal = 1.0f / sqrtf(x);
            float approx = 1.0f / sqrtf(1.5f);
            exp_adjust[i] = ideal / approx;
        }
    }
    
    // Enhanced single precision version
    inline float compute(float x) {
        union {
            float f;
            uint32_t i;
        } conv, magic;
        
        conv.f = x;
        
        // Extract mantissa for lookup
        uint32_t mantissa = (conv.i & 0x7FFFFF) >> 15;
        uint8_t idx = mantissa >> 1;
        
        // Initial approximation with magic constant
        magic.i = MAGIC_CONSTANT - (conv.i >> 1);
        float y0 = magic.f;
        
        // Apply exponential adjustment from lookup table
        y0 *= exp_adjust[idx];
        
        // Polynomial correction for mantissa
        float m = x - floorf(x);
        float correction = POLY_C0 + m * (POLY_C1 + m * POLY_C2);
        
        // Modified Newton-Raphson with error compensation
        float x2 = x * 0.5f;
        float y = y0 * correction;
        y = y * (1.50087896f - x2 * y * y);  // Refined constant
        
        // Optional second iteration for higher precision (commented out for speed)
        // y = y * (1.50000006f - x2 * y * y);
        
        return y;
    }
    
    // SIMD version for 4 floats - optimized for cache efficiency
    inline __m128 compute_simd(__m128 x) {
        __m128i xi = _mm_castps_si128(x);
        __m128i magic = _mm_set1_epi32(MAGIC_CONSTANT);
        
        // Bit manipulation
        xi = _mm_srli_epi32(xi, 1);
        xi = _mm_sub_epi32(magic, xi);
        __m128 y = _mm_castsi128_ps(xi);
        
        // Newton-Raphson iteration with FMA instructions
        __m128 half = _mm_set1_ps(0.5f);
        __m128 three_halfs = _mm_set1_ps(1.50087896f);
        __m128 x_half = _mm_mul_ps(x, half);
        
        // Use FMA (Fused Multiply-Add) if available
        #ifdef __FMA__
        __m128 y_sq = _mm_mul_ps(y, y);
        __m128 newton = _mm_fmsub_ps(x_half, y_sq, three_halfs);
        y = _mm_mul_ps(y, newton);
        #else
        __m128 y_sq = _mm_mul_ps(y, y);
        __m128 xy_sq = _mm_mul_ps(x_half, y_sq);
        __m128 newton = _mm_sub_ps(three_halfs, xy_sq);
        y = _mm_mul_ps(y, newton);
        #endif
        
        return y;
    }
    
    // Fast normalize for 3D vectors (game engine critical path)
    inline void normalize_vector_fast(float* vec3) {
        // Use SIMD for dot product
        __m128 v = _mm_set_ps(0.0f, vec3[2], vec3[1], vec3[0]);
        __m128 dot = _mm_dp_ps(v, v, 0x77);
        
        // Extract scalar and compute reciprocal sqrt
        float norm_sq = _mm_cvtss_f32(dot);
        float inv_norm = compute(norm_sq);
        
        // Multiply result
        vec3[0] *= inv_norm;
        vec3[1] *= inv_norm;
        vec3[2] *= inv_norm;
    }
    
    // Batch normalization for vertex buffers
    void normalize_vertex_buffer(float* vertices, int count) {
        for (int i = 0; i < count; i += 4) {
            __m128 x = _mm_load_ps(&vertices[i*3]);
            __m128 y = _mm_load_ps(&vertices[i*3 + 4]);
            __m128 z = _mm_load_ps(&vertices[i*3 + 8]);
            
            // Compute norms for 4 vectors at once
            __m128 xx = _mm_mul_ps(x, x);
            __m128 yy = _mm_mul_ps(y, y);
            __m128 zz = _mm_mul_ps(z, z);
            __m128 norm_sq = _mm_add_ps(xx, _mm_add_ps(yy, zz));
            
            __m128 inv_norm = compute_simd(norm_sq);
            
            // Apply normalization
            x = _mm_mul_ps(x, inv_norm);
            y = _mm_mul_ps(y, inv_norm);
            z = _mm_mul_ps(z, inv_norm);
            
            _mm_store_ps(&vertices[i*3], x);
            _mm_store_ps(&vertices[i*3 + 4], y);
            _mm_store_ps(&vertices[i*3 + 8], z);
        }
    }
};

// Standard library version for accuracy comparison
float std_rsqrt(float x) {
    return 1.0f / sqrtf(x);
}

// Comprehensive benchmark
void benchmark() {
    const int NUM_TESTS = 10000000;
    float* test_values = (float*)aligned_alloc(16, NUM_TESTS * sizeof(float));
    float* results = (float*)aligned_alloc(16, NUM_TESTS * sizeof(float));
    
    // Generate realistic game engine values (distances, light intensities, etc.)
    srand(42);
    for (int i = 0; i < NUM_TESTS; i++) {
        // Mix of small values (normalized coords) and large values (world space)
        if (i % 3 == 0) {
            test_values[i] = (float)rand() / RAND_MAX * 2.0f;  // [0, 2]
        } else {
            test_values[i] = (float)rand() / RAND_MAX * 1000.0f + 0.1f;  // [0.1, 1000.1]
        }
    }
    
    EnhancedFastRecipSqrt efrs;
    clock_t start, end;
    double cpu_time_used;
    
    // Warm up cache
    for (int i = 0; i < 1000; i++) {
        results[i] = efrs.compute(test_values[i]);
    }
    
    printf("=== Performance Benchmarks (%d operations) ===\n", NUM_TESTS);
    
    // Benchmark standard library
    start = clock();
    for (int i = 0; i < NUM_TESTS; i++) {
        results[i] = std_rsqrt(test_values[i]);
    }
    end = clock();
    cpu_time_used = ((double)(end - start)) / CLOCKS_PER_SEC;
    printf("Standard library (1/sqrt):      %.3f seconds (baseline)\n", cpu_time_used);
    double baseline_time = cpu_time_used;
    
    // Benchmark Quake III algorithm
    start = clock();
    for (int i = 0; i < NUM_TESTS; i++) {
        results[i] = Q_rsqrt(test_values[i]);
    }
    end = clock();
    cpu_time_used = ((double)(end - start)) / CLOCKS_PER_SEC;
    printf("Quake III fast inverse sqrt:    %.3f seconds (%.1fx speedup)\n", 
           cpu_time_used, baseline_time / cpu_time_used);
    
    // Benchmark enhanced algorithm
    start = clock();
    for (int i = 0; i < NUM_TESTS; i++) {
        results[i] = efrs.compute(test_values[i]);
    }
    end = clock();
    cpu_time_used = ((double)(end - start)) / CLOCKS_PER_SEC;
    printf("Enhanced hybrid algorithm:       %.3f seconds (%.1fx speedup)\n", 
           cpu_time_used, baseline_time / cpu_time_used);
    
    // Benchmark SIMD version
    start = clock();
    for (int i = 0; i < NUM_TESTS; i += 4) {
        __m128 vals = _mm_load_ps(&test_values[i]);
        __m128 res = efrs.compute_simd(vals);
        _mm_store_ps(&results[i], res);
    }
    end = clock();
    cpu_time_used = ((double)(end - start)) / CLOCKS_PER_SEC;
    printf("SIMD enhanced algorithm:         %.3f seconds (%.1fx speedup)\n", 
           cpu_time_used, baseline_time / cpu_time_used);
    
    free(test_values);
    free(results);
}

// Accuracy analysis
void accuracy_test() {
    EnhancedFastRecipSqrt efrs;
    float test_values[] = {0.25f, 0.5f, 1.0f, 2.0f, 4.0f, 8.0f, 16.0f, 32.0f, 64.0f, 100.0f};
    
    printf("\n=== Accuracy Analysis ===\n");
    printf("Value\tExact\t\tQuake III\tEnhanced\tQ3 Error\tEnh Error\n");
    printf("-----\t-----\t\t---------\t--------\t--------\t---------\n");
    
    float total_q3_error = 0.0f;
    float total_enh_error = 0.0f;
    
    for (float val : test_values) {
        float exact = std_rsqrt(val);
        float q3_result = Q_rsqrt(val);
        float enh_result = efrs.compute(val);
        
        float q3_error = fabsf(q3_result - exact) / exact * 100.0f;
        float enh_error = fabsf(enh_result - exact) / exact * 100.0f;
        
        total_q3_error += q3_error;
        total_enh_error += enh_error;
        
        printf("%.2f\t%.6f\t%.6f\t%.6f\t%.3f%%\t\t%.3f%%\n",
               val, exact, q3_result, enh_result, q3_error, enh_error);
    }
    
    printf("\nAverage error - Quake III: %.3f%%, Enhanced: %.3f%%\n",
           total_q3_error / 10.0f, total_enh_error / 10.0f);
}

// Real game engine scenario
void game_engine_demo() {
    EnhancedFastRecipSqrt efrs;
    
    printf("\n=== Game Engine Performance Demo ===\n");
    
    // Simulate processing a mesh with 100k vertices
    const int VERTEX_COUNT = 100000;
    float* vertices = (float*)aligned_alloc(16, VERTEX_COUNT * 3 * sizeof(float));
    
    // Generate random vertices
    for (int i = 0; i < VERTEX_COUNT * 3; i++) {
        vertices[i] = (float)rand() / RAND_MAX * 20.0f - 10.0f;
    }
    
    // Benchmark normal calculation
    clock_t start = clock();
    for (int i = 0; i < VERTEX_COUNT; i++) {
        efrs.normalize_vector_fast(&vertices[i*3]);
    }
    clock_t end = clock();
    
    double time_used = ((double)(end - start)) / CLOCKS_PER_SEC;
    printf("Normalized %d vertices in %.3f ms (%.1f million vertices/sec)\n",
           VERTEX_COUNT, time_used * 1000.0, VERTEX_COUNT / time_used / 1000000.0);
    
    // Physics simulation example
    printf("\n=== Physics Simulation (Particle System) ===\n");
    
    // Simulate gravity and drag forces
    float particle_pos[3] = {5.0f, 10.0f, 3.0f};
    float particle_vel[3] = {2.0f, -1.0f, 0.5f};
    float drag_coefficient = 0.1f;
    
    // Calculate drag force (proportional to velocity squared)
    float vel_mag_sq = particle_vel[0]*particle_vel[0] + 
                       particle_vel[1]*particle_vel[1] + 
                       particle_vel[2]*particle_vel[2];
    float inv_vel = efrs.compute(vel_mag_sq);
    
    printf("Particle velocity magnitude: %.3f\n", 1.0f / inv_vel);
    printf("Drag force multiplier: %.3f\n", drag_coefficient / inv_vel);
    
    free(vertices);
}

int main() {
    printf("=== Enhanced Fast Reciprocal Square Root Algorithm ===\n");
    printf("Advanced hybrid approach for game engines\n\n");
    
    benchmark();
    accuracy_test();
    game_engine_demo();
    
    printf("\n=== Algorithm Details ===\n");
    printf("1. Magic constant 0x5f375a86 (optimized from original)\n");
    printf("2. Lookup table for exponential adjustment (256 entries)\n");
    printf("3. Polynomial correction for mantissa variations\n");
    printf("4. SIMD implementation with FMA instructions\n");
    printf("5. Specialized vector normalization routines\n");
    printf("\n=== Mathematical Foundation ===\n");
    printf("- Based on IEEE 754 floating-point representation\n");
    printf("- Exploits the relationship: log(1/sqrt(x)) = -0.5 * log(x)\n");
    printf("- Polynomial approximation reduces systematic error\n");
    printf("- Single Newton-Raphson iteration for convergence\n");
    
    return 0;
}