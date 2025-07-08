#include <iostream>
#include <chrono>
#include <cmath>
#include <immintrin.h>
#include <cstring>
#include <iomanip>
#include <vector>
#include <algorithm>

// Original Quake III fast inverse square root
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

// Enhanced fast inverse square root with better magic constant
float enhancedInvSqrt(float number) {
    union {
        float f;
        uint32_t i;
    } conv;
    
    float x2 = number * 0.5f;
    conv.f = number;
    // Improved magic constant based on numerical analysis
    conv.i = 0x5f375a86 - (conv.i >> 1);
    
    // Two Newton-Raphson iterations for better accuracy
    conv.f = conv.f * (1.5f - (x2 * conv.f * conv.f));
    conv.f = conv.f * (1.5f - (x2 * conv.f * conv.f));
    
    return conv.f;
}

// SIMD-optimized inverse square root using AVX2
class SimdInverseSqrt {
public:
    // Process 8 floats in parallel
    static void inverseSqrt8(const float* input, float* output) {
        __m256 x = _mm256_loadu_ps(input);
        __m256 xhalf = _mm256_mul_ps(x, _mm256_set1_ps(0.5f));
        
        // Convert to integer for bit manipulation
        __m256i i = _mm256_castps_si256(x);
        
        // Apply enhanced magic constant
        i = _mm256_sub_epi32(_mm256_set1_epi32(0x5f375a86), 
                             _mm256_srli_epi32(i, 1));
        
        // Convert back to float
        x = _mm256_castsi256_ps(i);
        
        // Two Newton-Raphson iterations
        __m256 three_halves = _mm256_set1_ps(1.5f);
        x = _mm256_mul_ps(x, _mm256_sub_ps(three_halves, 
                          _mm256_mul_ps(xhalf, _mm256_mul_ps(x, x))));
        x = _mm256_mul_ps(x, _mm256_sub_ps(three_halves, 
                          _mm256_mul_ps(xhalf, _mm256_mul_ps(x, x))));
        
        _mm256_storeu_ps(output, x);
    }
    
    // Process large arrays with cache optimization
    static void processArray(const float* input, float* output, size_t count) {
        const size_t CACHE_LINE = 64;
        const size_t FLOATS_PER_CACHE_LINE = CACHE_LINE / sizeof(float);
        
        size_t i = 0;
        
        // Process in chunks of 8 with prefetching
        for (; i + 7 < count; i += 8) {
            // Prefetch next cache line
            if (i + FLOATS_PER_CACHE_LINE < count) {
                _mm_prefetch((const char*)(input + i + FLOATS_PER_CACHE_LINE), _MM_HINT_T0);
            }
            
            inverseSqrt8(input + i, output + i);
        }
        
        // Handle remaining elements
        for (; i < count; i++) {
            output[i] = enhancedInvSqrt(input[i]);
        }
    }
};

// Experimental: Lookup table with polynomial approximation
class HybridInvSqrt {
private:
    static constexpr size_t LUT_BITS = 8;
    static constexpr size_t LUT_SIZE = 1 << LUT_BITS;
    static float lut[LUT_SIZE];
    static float slope_lut[LUT_SIZE];
    static bool initialized;
    
public:
    static void initialize() {
        if (initialized) return;
        
        // Precompute lookup tables for range [1, 2)
        for (size_t i = 0; i < LUT_SIZE; i++) {
            float x = 1.0f + (float)i / LUT_SIZE;
            float x_next = 1.0f + (float)(i + 1) / LUT_SIZE;
            
            lut[i] = 1.0f / sqrt(x);
            // Precompute slope for linear interpolation
            slope_lut[i] = (1.0f / sqrt(x_next) - lut[i]) * LUT_SIZE;
        }
        
        initialized = true;
    }
    
    static float inverseSqrt(float x) {
        initialize();
        
        union {
            float f;
            uint32_t i;
        } conv;
        
        conv.f = x;
        
        // Extract exponent and mantissa
        int exp = ((conv.i >> 23) & 0xFF) - 127;
        conv.i = (conv.i & 0x007FFFFF) | 0x3F800000;  // Normalize to [1, 2)
        
        // Get LUT index and fractional part
        float normalized = conv.f;
        float index_f = (normalized - 1.0f) * LUT_SIZE;
        int index = (int)index_f;
        float frac = index_f - index;
        
        // Linear interpolation from lookup table
        float result = lut[index] + slope_lut[index] * frac;
        
        // Adjust for exponent
        int result_exp = -(exp >> 1);
        if (exp & 1) {
            result *= 0.70710678118f;  // 1/sqrt(2)
            result_exp--;
        }
        
        // Apply exponent
        conv.f = result;
        conv.i += (result_exp << 23);
        
        return conv.f;
    }
};

float HybridInvSqrt::lut[HybridInvSqrt::LUT_SIZE];
float HybridInvSqrt::slope_lut[HybridInvSqrt::LUT_SIZE];
bool HybridInvSqrt::initialized = false;

// Benchmark utilities
template<typename Func>
void benchmarkScalar(Func func, const std::string& name, float* test_data, size_t count) {
    std::vector<float> results(count);
    
    auto start = std::chrono::high_resolution_clock::now();
    
    for (size_t i = 0; i < count; i++) {
        results[i] = func(test_data[i]);
    }
    
    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
    
    std::cout << name << ": " << duration.count() / 1000.0 << " ms";
    std::cout << " (" << (count / (duration.count() / 1000000.0)) / 1000000.0 
              << " Mops/sec)" << std::endl;
    
    // Check accuracy on sample values
    double total_error = 0;
    for (size_t i = 0; i < std::min(size_t(10), count); i++) {
        float expected = 1.0f / sqrt(test_data[i]);
        float error = std::abs(results[i] - expected) / expected;
        total_error += error;
    }
    std::cout << "  Average error: " << (total_error / 10 * 100) << "%" << std::endl;
}

// Game engine demonstration: Particle system physics
struct Particle {
    float x, y, z;
    float vx, vy, vz;
    float mass;
};

void updateParticleForces(Particle* particles, size_t count) {
    alignas(32) float distances_sq[8];
    alignas(32) float inv_distances[8];
    
    const float G = 6.674e-11f;  // Gravitational constant
    
    for (size_t i = 0; i < count; i++) {
        float fx = 0, fy = 0, fz = 0;
        
        // Calculate forces from nearby particles
        for (size_t j = i + 1; j < std::min(i + 9, count); j += 8) {
            size_t batch_size = std::min(size_t(8), count - j);
            
            // Calculate squared distances
            for (size_t k = 0; k < batch_size; k++) {
                float dx = particles[j + k].x - particles[i].x;
                float dy = particles[j + k].y - particles[i].y;
                float dz = particles[j + k].z - particles[i].z;
                distances_sq[k] = dx * dx + dy * dy + dz * dz + 0.001f;  // Softening
            }
            
            // Compute inverse distances using SIMD
            SimdInverseSqrt::inverseSqrt8(distances_sq, inv_distances);
            
            // Apply forces
            for (size_t k = 0; k < batch_size; k++) {
                float inv_d3 = inv_distances[k] * inv_distances[k] * inv_distances[k];
                float force = G * particles[i].mass * particles[j + k].mass * inv_d3;
                
                fx += force * (particles[j + k].x - particles[i].x);
                fy += force * (particles[j + k].y - particles[i].y);
                fz += force * (particles[j + k].z - particles[i].z);
            }
        }
        
        // Update velocities (simplified)
        particles[i].vx += fx * 0.01f;
        particles[i].vy += fy * 0.01f;
        particles[i].vz += fz * 0.01f;
    }
}

int main() {
    std::cout << "=== Advanced Game Engine Inverse Square Root Performance Analysis ===" << std::endl;
    std::cout << std::endl;
    
    // Generate test data
    const size_t TEST_SIZE = 10000000;
    float* test_data = new float[TEST_SIZE];
    float* output = new float[TEST_SIZE];
    
    // Mix of typical game engine values
    for (size_t i = 0; i < TEST_SIZE; i++) {
        // Values from different ranges game engines encounter
        switch (i % 4) {
            case 0: test_data[i] = 0.1f + (i % 100) * 0.01f; break;      // Small values
            case 1: test_data[i] = 1.0f + (i % 1000) * 0.001f; break;    // Around 1.0
            case 2: test_data[i] = 10.0f + (i % 100) * 0.1f; break;      // Medium values
            case 3: test_data[i] = 100.0f + (i % 1000) * 0.1f; break;    // Large values
        }
    }
    
    std::cout << "Testing with " << TEST_SIZE << " values..." << std::endl;
    std::cout << std::endl;
    
    // Scalar benchmarks
    benchmarkScalar([](float x) { return 1.0f / sqrt(x); }, 
                    "Standard library (1/sqrt)", test_data, TEST_SIZE);
    
    benchmarkScalar(fastInvSqrt, 
                    "Fast InvSqrt (Quake III)", test_data, TEST_SIZE);
    
    benchmarkScalar(enhancedInvSqrt, 
                    "Enhanced InvSqrt", test_data, TEST_SIZE);
    
    benchmarkScalar(HybridInvSqrt::inverseSqrt, 
                    "Hybrid LUT+Interpolation", test_data, TEST_SIZE);
    
    // SIMD benchmark
    std::cout << std::endl;
    auto simd_start = std::chrono::high_resolution_clock::now();
    SimdInverseSqrt::processArray(test_data, output, TEST_SIZE);
    auto simd_end = std::chrono::high_resolution_clock::now();
    auto simd_duration = std::chrono::duration_cast<std::chrono::microseconds>(simd_end - simd_start);
    
    std::cout << "SIMD AVX2 (8x parallel): " << simd_duration.count() / 1000.0 << " ms";
    std::cout << " (" << (TEST_SIZE / (simd_duration.count() / 1000000.0)) / 1000000.0 
              << " Mops/sec)" << std::endl;
    
    // Verify SIMD accuracy
    double simd_error = 0;
    for (size_t i = 0; i < 10; i++) {
        float expected = 1.0f / sqrt(test_data[i]);
        float error = std::abs(output[i] - expected) / expected;
        simd_error += error;
    }
    std::cout << "  Average error: " << (simd_error / 10 * 100) << "%" << std::endl;
    
    // Game engine use case: Particle system
    std::cout << std::endl;
    std::cout << "=== Game Engine Use Case: N-Body Particle Physics ===" << std::endl;
    
    const size_t PARTICLE_COUNT = 10000;
    Particle* particles = new Particle[PARTICLE_COUNT];
    
    // Initialize particles
    for (size_t i = 0; i < PARTICLE_COUNT; i++) {
        particles[i] = {
            (float)(i % 100), (float)((i * 3) % 100), (float)((i * 7) % 100),
            0.0f, 0.0f, 0.0f,
            1.0f + (i % 10) * 0.1f
        };
    }
    
    auto physics_start = std::chrono::high_resolution_clock::now();
    
    // Simulate 100 physics steps
    for (int step = 0; step < 100; step++) {
        updateParticleForces(particles, PARTICLE_COUNT);
    }
    
    auto physics_end = std::chrono::high_resolution_clock::now();
    auto physics_duration = std::chrono::duration_cast<std::chrono::microseconds>(physics_end - physics_start);
    
    std::cout << "Simulated 100 physics steps for " << PARTICLE_COUNT 
              << " particles in " << physics_duration.count() / 1000.0 << " ms" << std::endl;
    std::cout << "Average per frame: " << physics_duration.count() / 100000.0 << " ms" << std::endl;
    
    // Mathematical explanation
    std::cout << std::endl;
    std::cout << "=== Mathematical Basis ===" << std::endl;
    std::cout << "The fast inverse square root exploits IEEE 754 float representation:" << std::endl;
    std::cout << "1. Float as integer: sign(1) + exponent(8) + mantissa(23)" << std::endl;
    std::cout << "2. log2(x) ≈ (float_as_int(x) - bias) / 2^23" << std::endl;
    std::cout << "3. 1/sqrt(x) = x^(-0.5) = 2^(-0.5 * log2(x))" << std::endl;
    std::cout << "4. Magic constant 0x5f3759df approximates this transformation" << std::endl;
    std::cout << "5. Newton-Raphson iteration: y = y * (1.5 - 0.5 * x * y * y)" << std::endl;
    std::cout << std::endl;
    std::cout << "Our optimizations:" << std::endl;
    std::cout << "- Enhanced magic constant 0x5f375a86 (better initial approximation)" << std::endl;
    std::cout << "- AVX2 SIMD: 8 operations in parallel" << std::endl;
    std::cout << "- Cache prefetching for large arrays" << std::endl;
    std::cout << "- Hybrid LUT: Combines lookup table with linear interpolation" << std::endl;
    
    delete[] test_data;
    delete[] output;
    delete[] particles;
    
    return 0;
}