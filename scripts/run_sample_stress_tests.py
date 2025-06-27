#!/usr/bin/env python3
"""Run a sample of stress tests from each category"""

import subprocess
import json
import time

# Define test samples - one from each category
test_samples = [
    ("simple", "simple_3"),      # Quick math
    ("parallel", "parallel_1"),   # Ten functions
    ("rapid_fire", "rapid_1"),    # Hundred questions (but will timeout)
    ("complex_orchestration", "complex_2"),  # Code review chain
]

results = {}
start_time = time.time()

print("Running sample stress tests from each category...")
print("=" * 60)

for category, test_id in test_samples:
    print(f"\nRunning {test_id} from {category} category...")
    
    cmd = f"python src/cc_executor/prompts/unified_stress_test_executor.py --test {test_id}"
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        
        # Parse success/failure from output
        if "✅ SUCCESS" in result.stdout:
            results[test_id] = "SUCCESS"
            print(f"✅ {test_id}: SUCCESS")
        else:
            results[test_id] = "FAILURE"
            print(f"❌ {test_id}: FAILURE")
            
    except subprocess.TimeoutExpired:
        results[test_id] = "TIMEOUT"
        print(f"⏱️ {test_id}: TIMEOUT (>2 minutes)")

# Summary
print("\n" + "=" * 60)
print("SAMPLE TEST SUMMARY")
print("=" * 60)

success_count = sum(1 for r in results.values() if r == "SUCCESS")
total_count = len(results)

print(f"Total tests run: {total_count}")
print(f"Success: {success_count}")
print(f"Failure: {total_count - success_count}")
print(f"Success rate: {success_count/total_count*100:.1f}%")
print(f"Total time: {time.time() - start_time:.1f}s")

print("\nDetailed results:")
for test_id, result in results.items():
    print(f"  {test_id}: {result}")

# Save results
with open("sample_stress_test_results.json", "w") as f:
    json.dump({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": results,
        "summary": {
            "total": total_count,
            "success": success_count,
            "failure": total_count - success_count,
            "success_rate": success_count/total_count*100
        }
    }, f, indent=2)

print("\nResults saved to sample_stress_test_results.json")