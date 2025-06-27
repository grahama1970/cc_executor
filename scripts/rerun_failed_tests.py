#!/usr/bin/env python3
"""Rerun only the failed stress tests with improved stall timeouts"""

import subprocess
import json
import time

# The 6 tests that failed due to stall timeout
failed_tests = [
    ("parallel", "parallel_2"),     # twenty_haikus
    ("long_running", "long_1"),     # epic_story  
    ("long_running", "long_2"),     # comprehensive_guide
    ("extreme_stress", "extreme_1"), # research_explosion
    ("extreme_stress", "extreme_2"), # infinite_improvement
    ("extreme_stress", "extreme_3"), # ultimate_stress
]

results = {}
start_time = time.time()

print("Re-running failed stress tests with improved stall timeouts...")
print("=" * 60)
print("Stall timeouts updated:")
print("  - Long/Extreme tests: 180s (was 60s)")
print("  - Twenty haikus: 120s (was 60s)")
print("=" * 60)

for category, test_id in failed_tests:
    print(f"\nRunning {test_id} from {category} category...")
    
    cmd = f"python src/cc_executor/prompts/unified_stress_test_executor.py --test {test_id}"
    
    try:
        # Give extreme tests more time
        timeout = 720 if test_id.startswith("extreme_") else 360
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        
        # Parse success/failure from output
        if "✅ SUCCESS" in result.stdout:
            results[test_id] = "SUCCESS"
            print(f"✅ {test_id}: SUCCESS")
        else:
            results[test_id] = "FAILURE"
            print(f"❌ {test_id}: FAILURE")
            # Show failure reason
            if "STALLED" in result.stdout:
                print(f"   Still stalled despite increased timeout")
            elif "TIMEOUT" in result.stdout:
                print(f"   Test timeout exceeded")
                
    except subprocess.TimeoutExpired:
        results[test_id] = "TIMEOUT"
        print(f"⏱️ {test_id}: TIMEOUT (subprocess timeout)")

# Summary
print("\n" + "=" * 60)
print("FAILED TESTS RE-RUN SUMMARY")
print("=" * 60)

success_count = sum(1 for r in results.values() if r == "SUCCESS")
total_count = len(results)

print(f"Total tests re-run: {total_count}")
print(f"Success: {success_count}")
print(f"Still failing: {total_count - success_count}")
print(f"Success rate: {success_count/total_count*100:.1f}%")
print(f"Total time: {time.time() - start_time:.1f}s")

print("\nDetailed results:")
for test_id, result in results.items():
    print(f"  {test_id}: {result}")

# Save results
with open("failed_tests_rerun_results.json", "w") as f:
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

print("\nResults saved to failed_tests_rerun_results.json")

# Overall assessment
if success_count == total_count:
    print("\n🎉 All previously failed tests now pass!")
    print("The system is ready for Docker containerization.")
else:
    print(f"\n⚠️ {total_count - success_count} tests still failing.")
    print("Further investigation needed before Docker migration.")