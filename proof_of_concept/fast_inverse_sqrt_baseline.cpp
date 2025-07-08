#include <iostream>
#include <chrono>
#include <cmath>
#include <immintrin.h>
#include <vector>
#include <iomanip>

// Original Quake III fast inverse square root
float Q_rsqrt(float number) {
    long i;
    float x2, y;
    const float threehalfs = 1.5F;

    x2 = number * 0.5F;
    y  = number;
    i  = * ( long * ) &y;                       // evil floating point bit level hacking
    i  = 0x5f3759df - ( i >> 1 );               // what the fuck?
    y  = * ( float * ) &i;
    y  = y * ( threehalfs - ( x2 * y * y ) );   // 1st iteration
    // y  = y * ( threehalfs - ( x2 * y * y ) );   // 2nd iteration, this can be removed
    return y;
}

// Standard library version for comparison
float std_rsqrt(float number) {
    return 1.0f / std::sqrt(number);
}

// Benchmark function
template<typename Func>
double benchmark(Func func, const std::vector<float>& data, int iterations) {
    auto start = std::chrono::high_resolution_clock::now();
    
    float sum = 0.0f; // Prevent optimization
    for (int i = 0; i < iterations; i++) {
        for (float val : data) {
            sum += func(val);
        }
    }
    
    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double, std::milli> duration = end - start;
    
    // Use sum to prevent dead code elimination
    if (sum == 0.0f) std::cout << "Prevented optimization\n";
    
    return duration.count();
}

int main() {
    std::cout << "Fast Inverse Square Root Baseline Benchmark\n";
    std::cout << "==========================================\n\n";
    
    // Test correctness
    float test_values[] = {4.0f, 16.0f, 25.0f, 100.0f, 0.25f, 0.5f, 2.0f};
    
    std::cout << "Correctness Test:\n";
    std::cout << std::setw(10) << "Input" << std::setw(20) << "Q_rsqrt" 
              << std::setw(20) << "std_rsqrt" << std::setw(20) << "Error %\n";
    
    for (float val : test_values) {
        float q_result = Q_rsqrt(val);
        float std_result = std_rsqrt(val);
        float error = std::abs((q_result - std_result) / std_result) * 100.0f;
        
        std::cout << std::setw(10) << val 
                  << std::setw(20) << q_result 
                  << std::setw(20) << std_result 
                  << std::setw(19) << error << "%\n";
    }
    
    // Performance benchmark
    std::cout << "\nPerformance Benchmark:\n";
    
    // Generate test data
    std::vector<float> test_data;
    for (int i = 0; i < 1000000; i++) {
        test_data.push_back(0.1f + (i % 1000) * 0.1f);
    }
    
    const int iterations = 100;
    
    double q_time = benchmark(Q_rsqrt, test_data, iterations);
    double std_time = benchmark(std_rsqrt, test_data, iterations);
    
    std::cout << "Q_rsqrt time: " << q_time << " ms\n";
    std::cout << "std_rsqrt time: " << std_time << " ms\n";
    std::cout << "Speedup: " << std_time / q_time << "x\n";
    
    return 0;
}