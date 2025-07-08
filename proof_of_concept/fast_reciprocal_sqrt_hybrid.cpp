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

// Our hybrid fast reciprocal square root algorithm
// Combines bit manipulation with lookup table and SIMD optimization
class FastRecipSqrt {
private:
    // Precomputed lookup table for initial approximation refinement
    static constexpr int LUT_SIZE = 256;
    float lut[LUT_SIZE];
    
    // Magic constants optimized through mathematical analysis
    static constexpr uint32_t MAGIC_CONSTANT = 0x5f375a86;  // Refined magic number
    static constexpr float ITERATION_CONSTANT = 1.5008908f;  // Slightly adjusted for better convergence
    
public:
    FastRecipSqrt() {
        // Initialize lookup table with correction factors
        for (int i = 0; i < LUT_SIZE; i++) {
            float mantissa = 1.0f + (float)i / LUT_SIZE;
            float exact = 1.0f / sqrtf(mantissa);
            float approx = 1.0f / sqrtf(1.5f);  // Base approximation
            lut[i] = exact / approx;  // Correction factor
        }
    }
    
    // Single precision version with lookup table refinement
    float compute(float x) {
        union {
            float f;
            uint32_t i;
        } conv;
        
        conv.f = x;
        uint32_t mantissa_bits = (conv.i & 0x007FFFFF) >> 15;  // Extract mantissa bits
        uint32_t lut_index = mantissa_bits >> 3;  // Use top bits for LUT
        
        // Apply the bit manipulation with our refined magic constant
        conv.i = MAGIC_CONSTANT - (conv.i >> 1);
        
        // Apply lookup table correction
        float y = conv.f * lut[lut_index & (LUT_SIZE - 1)];
        
        // Single Newton-Raphson iteration with adjusted constant
        float x2 = x * 0.5f;
        y = y * (ITERATION_CONSTANT - x2 * y * y);
        
        return y;
    }
    
    // SIMD version for processing 4 floats at once
    __m128 compute_simd(__m128 x) {
        // Extract integer representation
        __m128i xi = _mm_castps_si128(x);
        
        // Apply bit manipulation
        __m128i magic = _mm_set1_epi32(MAGIC_CONSTANT);
        xi = _mm_srli_epi32(xi, 1);
        xi = _mm_sub_epi32(magic, xi);
        
        // Convert back to float
        __m128 y = _mm_castsi128_ps(xi);
        
        // Newton-Raphson iteration
        __m128 half_x = _mm_mul_ps(x, _mm_set1_ps(0.5f));
        __m128 three_halfs = _mm_set1_ps(ITERATION_CONSTANT);
        __m128 y_squared = _mm_mul_ps(y, y);
        __m128 correction = _mm_sub_ps(three_halfs, _mm_mul_ps(half_x, y_squared));
        y = _mm_mul_ps(y, correction);
        
        return y;
    }
    
    // Optimized version for normalized vectors (common in game engines)
    void normalize_vector(float* vec3) {
        float norm_sq = vec3[0]*vec3[0] + vec3[1]*vec3[1] + vec3[2]*vec3[2];
        float inv_norm = compute(norm_sq);
        vec3[0] *= inv_norm;
        vec3[1] *= inv_norm;
        vec3[2] *= inv_norm;
    }
};

// Standard library version for accuracy comparison
float std_rsqrt(float x) {
    return 1.0f / sqrtf(x);
}

// Benchmark function
void benchmark() {
    const int NUM_TESTS = 10000000;
    float* test_values = (float*)aligned_alloc(16, NUM_TESTS * sizeof(float));
    float* results = (float*)aligned_alloc(16, NUM_TESTS * sizeof(float));
    
    // Generate test values
    srand(42);
    for (int i = 0; i < NUM_TESTS; i++) {
        test_values[i] = (float)rand() / RAND_MAX * 100.0f + 0.1f;
    }
    
    FastRecipSqrt frs;
    clock_t start, end;
    double cpu_time_used;
    
    // Benchmark standard library
    start = clock();
    for (int i = 0; i < NUM_TESTS; i++) {
        results[i] = std_rsqrt(test_values[i]);
    }
    end = clock();
    cpu_time_used = ((double)(end - start)) / CLOCKS_PER_SEC;
    printf("Standard library rsqrt: %.3f seconds\n", cpu_time_used);
    
    // Benchmark Quake III algorithm
    start = clock();
    for (int i = 0; i < NUM_TESTS; i++) {
        results[i] = Q_rsqrt(test_values[i]);
    }
    end = clock();
    cpu_time_used = ((double)(end - start)) / CLOCKS_PER_SEC;
    printf("Quake III fast inverse sqrt: %.3f seconds\n", cpu_time_used);
    
    // Benchmark our hybrid algorithm
    start = clock();
    for (int i = 0; i < NUM_TESTS; i++) {
        results[i] = frs.compute(test_values[i]);
    }
    end = clock();
    cpu_time_used = ((double)(end - start)) / CLOCKS_PER_SEC;
    printf("Hybrid fast reciprocal sqrt: %.3f seconds\n", cpu_time_used);
    
    // Benchmark SIMD version
    start = clock();
    for (int i = 0; i < NUM_TESTS; i += 4) {
        __m128 vals = _mm_load_ps(&test_values[i]);
        __m128 res = frs.compute_simd(vals);
        _mm_store_ps(&results[i], res);
    }
    end = clock();
    cpu_time_used = ((double)(end - start)) / CLOCKS_PER_SEC;
    printf("SIMD hybrid reciprocal sqrt: %.3f seconds\n", cpu_time_used);
    
    free(test_values);
    free(results);
}

// Accuracy test
void accuracy_test() {
    FastRecipSqrt frs;
    float test_values[] = {0.25f, 1.0f, 2.0f, 4.0f, 9.0f, 16.0f, 25.0f, 100.0f};
    
    printf("\nAccuracy Test:\n");
    printf("Value\tStandard\tQuake III\tHybrid\t\tError(Q3)\tError(Hybrid)\n");
    
    for (float val : test_values) {
        float std_result = std_rsqrt(val);
        float q3_result = Q_rsqrt(val);
        float hybrid_result = frs.compute(val);
        
        float q3_error = fabsf(q3_result - std_result) / std_result * 100.0f;
        float hybrid_error = fabsf(hybrid_result - std_result) / std_result * 100.0f;
        
        printf("%.2f\t%.6f\t%.6f\t%.6f\t%.2f%%\t\t%.2f%%\n",
               val, std_result, q3_result, hybrid_result, q3_error, hybrid_error);
    }
}

// Game engine use case: Lighting calculation
void lighting_demo() {
    FastRecipSqrt frs;
    
    printf("\nGame Engine Use Case - Phong Lighting:\n");
    
    // Light position and surface normal (typical game scenario)
    float light_pos[3] = {10.0f, 15.0f, 5.0f};
    float surface_point[3] = {0.0f, 0.0f, 0.0f};
    float surface_normal[3] = {0.0f, 1.0f, 0.0f};
    
    // Calculate light direction
    float light_dir[3];
    light_dir[0] = light_pos[0] - surface_point[0];
    light_dir[1] = light_pos[1] - surface_point[1];
    light_dir[2] = light_pos[2] - surface_point[2];
    
    // Normalize using our algorithm
    clock_t start = clock();
    for (int i = 0; i < 1000000; i++) {
        frs.normalize_vector(light_dir);
    }
    clock_t end = clock();
    
    double time_used = ((double)(end - start)) / CLOCKS_PER_SEC;
    printf("1M vector normalizations: %.3f seconds\n", time_used);
    
    // Calculate dot product for lighting
    float dot = light_dir[0] * surface_normal[0] + 
                light_dir[1] * surface_normal[1] + 
                light_dir[2] * surface_normal[2];
    
    printf("Normalized light direction: (%.3f, %.3f, %.3f)\n", 
           light_dir[0], light_dir[1], light_dir[2]);
    printf("Lighting intensity: %.3f\n", fmaxf(0.0f, dot));
}

int main() {
    printf("=== Fast Reciprocal Square Root Hybrid Algorithm ===\n");
    printf("Combining bit manipulation, lookup tables, and SIMD\n\n");
    
    benchmark();
    accuracy_test();
    lighting_demo();
    
    printf("\n=== Mathematical Explanation ===\n");
    printf("1. Bit manipulation provides initial approximation (like Quake III)\n");
    printf("2. Lookup table refines based on mantissa patterns\n");
    printf("3. Adjusted Newton-Raphson iteration for final precision\n");
    printf("4. SIMD version processes 4 values simultaneously\n");
    printf("5. Optimized for game engine vector normalization\n");
    
    return 0;
}