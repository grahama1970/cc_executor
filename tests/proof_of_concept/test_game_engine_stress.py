#!/usr/bin/env python3
"""
Stress test for cc_execute with complex orchestration.

Tests:
- Task tool usage for spawning multiple Claude instances
- Concurrent algorithm development with different parameters
- MCP tool usage (perplexity-ask) for evaluation
- JSON schema enforcement
- Complex result aggregation
"""
import asyncio
import time
from executor import cc_execute, CCExecutorConfig

async def run_game_engine_competition():
    """Run the game engine algorithm competition stress test."""
    print("🎮 CC_EXECUTE STRESS TEST: Game Engine Algorithm Competition")
    print("="*80)
    print("This test will:")
    print("1. Use Task tool to spawn 4 concurrent Claude instances")
    print("2. Each creates a different algorithm with varying parameters")
    print("3. Use perplexity-ask to evaluate and pick winner")
    print("4. Return structured JSON with all results")
    print("="*80)
    
    # The complex orchestration task
    competition_task = """Use your Task tool to spawn 4 concurrent Claude instances to create game engine algorithms more efficient than the fast inverse square root algorithm.

REQUIREMENTS:
1. First, run 'which gcc' and 'gcc --version' to check the C compiler environment

2. Each instance should create a DIFFERENT algorithm approach
3. Each instance uses different parameters:
   - Instance 1: Conservative (--max-turns 1, low creativity)
   - Instance 2: Balanced (--max-turns 2, medium creativity)  
   - Instance 3: Creative (--max-turns 3, high creativity)
   - Instance 4: Experimental (--max-turns 3, maximum creativity)

4. Each algorithm must include:
   - The algorithm implementation in C/C++
   - COMPILE and RUN the code to verify it works
   - Performance benchmarks vs original (with actual timing measurements)
   - Use case in game engines
   - Mathematical explanation
   - Include any compilation errors/warnings and fix them

5. After all 4 complete, use the perplexity-ask MCP tool to evaluate all algorithms and pick the best one with detailed rationale.

6. Return a JSON response with this exact schema:
{
  "algorithms": [
    {
      "instance": 1,
      "name": "Algorithm name",
      "code": "C/C++ implementation",
      "compilation_output": "gcc output or errors",
      "test_results": "Execution results showing it works",
      "performance_gain": "X% faster (with actual measurements)",
      "benchmark_data": "Timing comparisons with original",
      "use_case": "Description",
      "explanation": "Mathematical basis"
    },
    // ... for all 4 instances
  ],
  "perplexity_evaluation": {
    "winner": 1,  // instance number
    "rationale": "Detailed explanation of why this algorithm won",
    "comparison": "How algorithms compare to each other"
  },
  "summary": "Overall summary of the competition",
  "execution_uuid": "Will be provided"
}

Execute this complex orchestration task now."""
    
    start_time = time.time()
    
    try:
        # Execute with extended timeout
        result = await cc_execute(
            competition_task,
            config=CCExecutorConfig(
                timeout=1200,  # 20 minutes for very complex orchestration
                stream_output=True,
                save_transcript=True
            ),
            stream=True,
            return_json=True
        )
        
        elapsed = time.time() - start_time
        
        print(f"\n{'='*80}")
        print(f"✅ COMPETITION COMPLETE in {elapsed:.1f}s")
        print(f"{'='*80}")
        
        if isinstance(result, dict):
            # Display results
            algorithms = result.get('algorithms', [])
            print(f"\n📊 ALGORITHMS CREATED: {len(algorithms)}")
            
            for i, algo in enumerate(algorithms):
                print(f"\n{'='*60}")
                print(f"ALGORITHM {i+1}: {algo.get('name', 'Unknown')}")
                print(f"Instance: {algo.get('instance')}")
                print(f"Performance: {algo.get('performance_gain', 'N/A')}")
                print(f"Use case: {algo.get('use_case', 'N/A')[:200]}...")
                print(f"\nCode preview:")
                code = algo.get('code', 'No code')
                print(code[:500] + "..." if len(code) > 500 else code)
                print(f"\nExplanation: {algo.get('explanation', 'N/A')[:300]}...")
            
            # Show evaluation results
            print(f"\n{'='*80}")
            print("🔍 PERPLEXITY EVALUATION")
            print("="*80)
            
            eval_data = result.get('perplexity_evaluation', {})
            winner = eval_data.get('winner', 'Unknown')
            print(f"\n🏆 WINNER: Algorithm from Instance {winner}")
            print(f"\nRationale: {eval_data.get('rationale', 'N/A')}")
            print(f"\nComparison: {eval_data.get('comparison', 'N/A')}")
            
            # Summary
            print(f"\n{'='*80}")
            print("📋 SUMMARY")
            print("="*80)
            print(result.get('summary', 'No summary available'))
            
            # UUID verification
            print(f"\n{'='*80}")
            if result.get('execution_uuid'):
                print(f"✅ Execution UUID verified: {result['execution_uuid']}")
            else:
                print("⚠️  WARNING: No execution UUID found!")
                
            # Save detailed results
            import json
            from pathlib import Path
            
            results_dir = Path(__file__).parent / "stress_test_results"
            results_dir.mkdir(exist_ok=True)
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            results_file = results_dir / f"game_engine_competition_{timestamp}.json"
            
            with open(results_file, 'w') as f:
                json.dump({
                    "test": "game_engine_algorithm_competition",
                    "duration_seconds": elapsed,
                    "result": result,
                    "timestamp": timestamp
                }, f, indent=2)
            
            print(f"\n💾 Detailed results saved to: {results_file}")
            
        else:
            print(f"\n⚠️  Unexpected result type: {type(result)}")
            print(f"Result: {str(result)[:1000]}...")
            
    except TimeoutError as e:
        elapsed = time.time() - start_time
        print(f"\n⏱️  TIMEOUT after {elapsed:.1f}s: {e}")
        print("Consider increasing timeout for this complex task")
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n❌ FAILED after {elapsed:.1f}s: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting CC_EXECUTE stress test...")
    print("This will test complex orchestration capabilities")
    print("Expected duration: 10-20 minutes")
    print("")
    
    asyncio.run(run_game_engine_competition())