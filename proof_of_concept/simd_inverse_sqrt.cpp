#include <iostream>
#include <chrono>
#include <cmath>
#include <immintrin.h>
#include <cstring>
#include <iomanip>

// Original Quake III fast inverse square root for comparison
float fastInvSqrt(float number) {
    union {
        float f;
        uint32_t i;
    } conv;
    
    float x2 = number * 0.5f;
    conv.f = number;
    conv.i = 0x5f3759df - (conv.i >> 1);
    conv.f = conv.f * (1.5f - (x2 * conv.f * conv.f));
    return conv.f;
}

// Novel SIMD-based inverse square root with cache prefetching
// Processes 8 floats at once using AVX2 with improved Newton-Raphson
class SimdInverseSqrt {
private:
    static constexpr float MAGIC_CONSTANT = 0x5f375a86;  // Optimized magic number
    
public:
    // Process 8 floats in parallel using AVX2
    static void inverseSqrt8(const float* input, float* output) {
        __m256 x = _mm256_load_ps(input);
        __m256 xhalf = _mm256_mul_ps(x, _mm256_set1_ps(0.5f));
        
        // Convert float to int for bit manipulation
        __m256i i = _mm256_castps_si256(x);
        
        // Apply magic constant and shift
        i = _mm256_sub_epi32(_mm256_set1_epi32(0x5f375a86), 
                             _mm256_srli_epi32(i, 1));
        
        // Convert back to float
        x = _mm256_castsi256_ps(i);
        
        // Two iterations of Newton-Raphson for higher accuracy
        __m256 three_halves = _mm256_set1_ps(1.5f);
        x = _mm256_mul_ps(x, _mm256_sub_ps(three_halves, 
                          _mm256_mul_ps(xhalf, _mm256_mul_ps(x, x))));
        
        // Second iteration for game engine precision requirements
        x = _mm256_mul_ps(x, _mm256_sub_ps(three_halves, 
                          _mm256_mul_ps(xhalf, _mm256_mul_ps(x, x))));
        
        _mm256_store_ps(output, x);
    }
    
    // Process arrays with cache prefetching for large datasets
    static void inverseSqrtArray(const float* input, float* output, size_t count) {
        size_t i = 0;
        
        // Process 8 elements at a time
        for (; i + 7 < count; i += 8) {
            // Prefetch next cache line
            if (i + 16 < count) {
                _mm_prefetch((const char*)(input + i + 16), _MM_HINT_T0);
            }
            
            inverseSqrt8(input + i, output + i);
        }
        
        // Handle remaining elements
        for (; i < count; i++) {
            output[i] = fastInvSqrt(input[i]);
        }
    }
};

// Experimental bit-twiddling approach with lookup table acceleration
class BitTwiddleInvSqrt {
private:
    static constexpr size_t LUT_SIZE = 256;
    static float lut[LUT_SIZE];
    static bool lut_initialized;
    
    static void initLUT() {
        if (!lut_initialized) {
            for (size_t i = 0; i < LUT_SIZE; i++) {
                float x = 1.0f + (float)i / LUT_SIZE;
                lut[i] = 1.0f / sqrt(x);
            }
            lut_initialized = true;
        }
    }
    
public:
    static float inverseSqrt(float x) {
        initLUT();
        
        union {
            float f;
            uint32_t i;
        } conv;
        
        // Extract exponent and mantissa
        conv.f = x;
        uint32_t exp = (conv.i >> 23) & 0xFF;
        uint32_t mantissa = conv.i & 0x7FFFFF;
        
        // Compute approximate result using exponent manipulation
        uint32_t result_exp = ((0x7F + 127) - exp) >> 1;
        
        // Use lookup table for mantissa approximation
        uint32_t lut_index = mantissa >> 15;  // Use top 8 bits
        float mantissa_approx = lut[lut_index & 0xFF];
        
        // Combine results
        conv.i = (result_exp << 23) | (mantissa >> 1);
        float result = conv.f;
        
        // Single Newton-Raphson iteration
        result = result * (1.5f - 0.5f * x * result * result);
        
        return result * mantissa_approx;
    }
};

float BitTwiddleInvSqrt::lut[BitTwiddleInvSqrt::LUT_SIZE];
bool BitTwiddleInvSqrt::lut_initialized = false;

// Benchmark function
template<typename Func>
double benchmark(Func func, const std::string& name, int iterations = 10000000) {
    float test_values[] = {4.0f, 16.0f, 25.0f, 100.0f, 0.25f, 0.5f, 2.0f, 9.0f};
    float results[8];
    
    auto start = std::chrono::high_resolution_clock::now();
    
    for (int i = 0; i < iterations; i++) {
        for (int j = 0; j < 8; j++) {
            results[j] = func(test_values[j]);
        }
    }
    
    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
    
    std::cout << name << " time: " << duration.count() / 1000.0 << " ms" << std::endl;
    
    // Verify accuracy
    std::cout << "Sample results for " << name << ":" << std::endl;
    for (int i = 0; i < 4; i++) {
        float actual = 1.0f / sqrt(test_values[i]);
        float computed = func(test_values[i]);
        float error = std::abs(actual - computed) / actual * 100;
        std::cout << "  1/sqrt(" << test_values[i] << ") = " << computed 
                  << " (actual: " << actual << ", error: " << error << "%)" << std::endl;
    }
    
    return duration.count() / 1000.0;
}

// Game engine use case: Normal vector normalization for lighting
struct Vec3 {
    float x, y, z;
};

void normalizeVectors(Vec3* vectors, size_t count) {
    alignas(32) float magnitudes[8];
    alignas(32) float inv_magnitudes[8];
    
    for (size_t i = 0; i < count; i += 8) {
        // Calculate magnitudes squared
        for (size_t j = 0; j < 8 && i + j < count; j++) {
            magnitudes[j] = vectors[i+j].x * vectors[i+j].x + 
                           vectors[i+j].y * vectors[i+j].y + 
                           vectors[i+j].z * vectors[i+j].z;
        }
        
        // Compute inverse square roots in parallel
        SimdInverseSqrt::inverseSqrt8(magnitudes, inv_magnitudes);
        
        // Apply to vectors
        for (size_t j = 0; j < 8 && i + j < count; j++) {
            vectors[i+j].x *= inv_magnitudes[j];
            vectors[i+j].y *= inv_magnitudes[j];
            vectors[i+j].z *= inv_magnitudes[j];
        }
    }
}

int main() {
    std::cout << "=== Advanced Game Engine Inverse Square Root Algorithms ===" << std::endl;
    std::cout << std::endl;
    
    // Standard library baseline
    auto std_time = benchmark([](float x) { return 1.0f / sqrt(x); }, "std::sqrt");
    
    // Original fast inverse square root
    auto fast_time = benchmark(fastInvSqrt, "Fast InvSqrt (Quake III)");
    
    // Bit-twiddling with LUT
    auto bit_time = benchmark(BitTwiddleInvSqrt::inverseSqrt, "BitTwiddle + LUT");
    
    // SIMD benchmark
    std::cout << "\nSIMD Parallel Processing (8 floats at once):" << std::endl;
    const size_t array_size = 80000000;  // 80 million floats
    alignas(32) float* input = new alignas(32) float[array_size];
    alignas(32) float* output = new alignas(32) float[array_size];
    
    // Initialize test data
    for (size_t i = 0; i < array_size; i++) {
        input[i] = 1.0f + (i % 1000) * 0.1f;
    }
    
    // SIMD benchmark
    auto simd_start = std::chrono::high_resolution_clock::now();
    SimdInverseSqrt::inverseSqrtArray(input, output, array_size);
    auto simd_end = std::chrono::high_resolution_clock::now();
    auto simd_duration = std::chrono::duration_cast<std::chrono::microseconds>(simd_end - simd_start);
    
    std::cout << "SIMD processed " << array_size << " floats in " 
              << simd_duration.count() / 1000.0 << " ms" << std::endl;
    std::cout << "Throughput: " << (array_size / (simd_duration.count() / 1000000.0)) / 1000000.0 
              << " million operations/second" << std::endl;
    
    // Traditional approach for comparison
    auto trad_start = std::chrono::high_resolution_clock::now();
    for (size_t i = 0; i < array_size; i++) {
        output[i] = fastInvSqrt(input[i]);
    }
    auto trad_end = std::chrono::high_resolution_clock::now();
    auto trad_duration = std::chrono::duration_cast<std::chrono::microseconds>(trad_end - trad_start);
    
    std::cout << "Traditional fast inverse sqrt: " << trad_duration.count() / 1000.0 << " ms" << std::endl;
    std::cout << "SIMD Speedup: " << (float)trad_duration.count() / simd_duration.count() << "x" << std::endl;
    
    // Game engine use case demonstration
    std::cout << "\n=== Game Engine Use Case: Normal Vector Normalization ===" << std::endl;
    const size_t vector_count = 1000000;
    Vec3* normals = new Vec3[vector_count];
    
    // Initialize with random vectors
    for (size_t i = 0; i < vector_count; i++) {
        normals[i] = {(float)(i % 100) - 50.0f, 
                      (float)((i * 3) % 100) - 50.0f, 
                      (float)((i * 7) % 100) - 50.0f};
    }
    
    auto norm_start = std::chrono::high_resolution_clock::now();
    normalizeVectors(normals, vector_count);
    auto norm_end = std::chrono::high_resolution_clock::now();
    auto norm_duration = std::chrono::duration_cast<std::chrono::microseconds>(norm_end - norm_start);
    
    std::cout << "Normalized " << vector_count << " vectors in " 
              << norm_duration.count() / 1000.0 << " ms" << std::endl;
    
    // Verify normalization
    float total_magnitude = 0;
    for (size_t i = 0; i < 10; i++) {
        float mag = sqrt(normals[i].x * normals[i].x + 
                        normals[i].y * normals[i].y + 
                        normals[i].z * normals[i].z);
        total_magnitude += mag;
    }
    std::cout << "Average magnitude of first 10 normalized vectors: " 
              << total_magnitude / 10.0f << " (should be ~1.0)" << std::endl;
    
    delete[] input;
    delete[] output;
    delete[] normals;
    
    std::cout << "\n=== Performance Summary ===" << std::endl;
    std::cout << "Standard library: " << std_time << " ms (baseline)" << std::endl;
    std::cout << "Fast InvSqrt: " << fast_time << " ms (" 
              << std_time / fast_time << "x speedup)" << std::endl;
    std::cout << "BitTwiddle + LUT: " << bit_time << " ms (" 
              << std_time / bit_time << "x speedup)" << std::endl;
    std::cout << "SIMD (array): " << (float)trad_duration.count() / simd_duration.count() 
              << "x speedup over scalar" << std::endl;
    
    return 0;
}