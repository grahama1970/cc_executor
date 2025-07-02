#!/usr/bin/env python3
"""
Analyze Claude instance execution data to understand the relationship
between prompt complexity, execution time, and failure rates.
"""

import json
import redis
import statistics
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import numpy as np

def analyze_complexity_failure_correlation():
    """Analyze the correlation between complexity and failure rates."""
    r = redis.Redis(decode_responses=True)
    
    print("=== Claude Complexity vs Failure Rate Analysis ===\n")
    
    # Get data for each complexity bucket
    complexity_data = {}
    
    for bucket in range(6):  # 0-5 complexity buckets
        bucket_data = r.hgetall(f"claude:complexity:{bucket}")
        
        if bucket_data:
            total = sum(int(v) for v in bucket_data.values())
            
            # Count by quality type
            quality_breakdown = {
                'complete': int(bucket_data.get('complete', 0)),
                'partial': int(bucket_data.get('partial', 0)),
                'acknowledged': int(bucket_data.get('acknowledged', 0)),
                'hallucinated': int(bucket_data.get('hallucinated', 0)),
                'error': int(bucket_data.get('error', 0))
            }
            
            # Calculate failure rate (anything not complete)
            failures = total - quality_breakdown['complete']
            failure_rate = (failures / total * 100) if total > 0 else 0
            
            complexity_data[bucket] = {
                'total': total,
                'failure_rate': failure_rate,
                'breakdown': quality_breakdown
            }
            
    # Display results
    print("Complexity | Total | Success | Failure Rate | Breakdown")
    print("-" * 70)
    
    for bucket, data in sorted(complexity_data.items()):
        if data['total'] > 0:
            success = data['breakdown']['complete']
            print(f"    {bucket}      | {data['total']:5d} | {success:7d} | {data['failure_rate']:11.1f}% | ", end="")
            
            # Show breakdown
            breakdown_str = []
            for quality, count in data['breakdown'].items():
                if count > 0 and quality != 'complete':
                    pct = count / data['total'] * 100
                    breakdown_str.append(f"{quality[:3]}:{pct:.0f}%")
            print(", ".join(breakdown_str))
            
    return complexity_data


def analyze_execution_times():
    """Analyze execution times by complexity level."""
    r = redis.Redis(decode_responses=True)
    
    print("\n\n=== Execution Time by Complexity ===\n")
    
    time_data = {}
    
    for bucket in range(6):
        times_str = r.lrange(f"claude:exec_time:complexity:{bucket}", 0, -1)
        
        if times_str:
            times = [float(t) for t in times_str]
            
            time_data[bucket] = {
                'count': len(times),
                'mean': statistics.mean(times),
                'median': statistics.median(times),
                'min': min(times),
                'max': max(times),
                'stdev': statistics.stdev(times) if len(times) > 1 else 0
            }
            
    print("Complexity | Count |  Mean  | Median |  Min  |  Max  | StdDev")
    print("-" * 65)
    
    for bucket, data in sorted(time_data.items()):
        print(f"    {bucket}      | {data['count']:5d} | {data['mean']:6.1f}s | "
              f"{data['median']:6.1f}s | {data['min']:5.1f}s | {data['max']:5.1f}s | "
              f"{data['stdev']:6.1f}s")
              
    return time_data


def analyze_recent_failures():
    """Analyze recent failed executions to identify patterns."""
    r = redis.Redis(decode_responses=True)
    
    print("\n\n=== Recent Failure Analysis ===\n")
    
    # Get recent failures
    failures = r.lrange("claude:failed_executions", 0, 19)  # Last 20
    
    if not failures:
        print("No recent failures found.")
        return
        
    # Analyze failure patterns
    failure_types = {}
    complexity_failures = {}
    
    for failure_json in failures:
        failure = json.loads(failure_json)
        
        # Count by quality type
        quality = failure['quality']
        failure_types[quality] = failure_types.get(quality, 0) + 1
        
        # Count by complexity
        complexity = int(failure['complexity_score'])
        complexity_failures[complexity] = complexity_failures.get(complexity, 0) + 1
        
    print("Failure Type Distribution:")
    for ftype, count in sorted(failure_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {ftype:15s}: {count:3d} ({count/len(failures)*100:.1f}%)")
        
    print("\nFailures by Complexity:")
    for complexity, count in sorted(complexity_failures.items()):
        print(f"  Complexity {complexity}: {count:3d} ({count/len(failures)*100:.1f}%)")
        
    # Show example failures
    print("\nExample Failed Commands (last 5):")
    for i, failure_json in enumerate(failures[:5]):
        failure = json.loads(failure_json)
        print(f"\n{i+1}. Command: {failure['command'][:80]}...")
        print(f"   Quality: {failure['quality']}")
        print(f"   Complexity: {failure['complexity_score']:.2f}")
        print(f"   Duration: {failure['duration']:.1f}s")
        print(f"   Hallucination Score: {failure['hallucination_score']:.2f}")


def analyze_hallucination_patterns():
    """Analyze hallucination patterns by complexity."""
    r = redis.Redis(decode_responses=True)
    
    print("\n\n=== Hallucination Pattern Analysis ===\n")
    
    hallucinations = r.lrange("claude:hallucination_examples", 0, -1)
    
    if not hallucinations:
        print("No hallucination examples found.")
        return
        
    # Group by complexity
    by_complexity = {}
    
    for hall_json in hallucinations:
        hall = json.loads(hall_json)
        complexity = int(hall.get('complexity_score', 0))
        
        if complexity not in by_complexity:
            by_complexity[complexity] = []
        by_complexity[complexity].append(hall)
        
    print("Hallucinations by Complexity Level:")
    for complexity in sorted(by_complexity.keys()):
        examples = by_complexity[complexity]
        print(f"\nComplexity {complexity}: {len(examples)} hallucinations")
        
        # Show common patterns
        if examples:
            # Extract command keywords
            keywords = {}
            for ex in examples:
                cmd_words = ex['command'].lower().split()
                for word in ['create', 'implement', 'function', 'endpoint', 'api']:
                    if word in cmd_words:
                        keywords[word] = keywords.get(word, 0) + 1
                        
            if keywords:
                print("  Common keywords:")
                for kw, count in sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:3]:
                    print(f"    - {kw}: {count}")


def generate_complexity_report():
    """Generate a comprehensive complexity analysis report."""
    r = redis.Redis(decode_responses=True)
    
    print("\n\n=== COMPLEXITY ANALYSIS SUMMARY ===\n")
    
    # Get overall statistics
    total_executions = r.llen("claude:execution_history")
    successful = r.llen("claude:successful_executions")
    failed = r.llen("claude:failed_executions")
    
    overall_success_rate = (successful / total_executions * 100) if total_executions > 0 else 0
    
    print(f"Total Claude Executions: {total_executions}")
    print(f"Overall Success Rate: {overall_success_rate:.1f}%")
    print(f"Successful: {successful} | Failed: {failed}")
    
    # Key insights
    print("\n📊 Key Insights:")
    
    # Find complexity threshold
    complexity_data = analyze_complexity_failure_correlation()
    
    for bucket, data in sorted(complexity_data.items()):
        if data.get('failure_rate', 0) > 50:
            print(f"\n⚠️  Complexity {bucket}+ has >50% failure rate!")
            print(f"   Consider breaking down tasks with complexity score >{bucket}")
            break
            
    # Average times
    time_data = analyze_execution_times()
    
    if time_data:
        avg_times = [(b, d['mean']) for b, d in time_data.items()]
        if len(avg_times) > 1:
            # Check for exponential growth
            first_bucket_time = avg_times[0][1]
            last_bucket_time = avg_times[-1][1]
            
            if last_bucket_time > first_bucket_time * 3:
                print(f"\n⏱️  Execution time increases {last_bucket_time/first_bucket_time:.1f}x "
                      f"from complexity 0 to {avg_times[-1][0]}")
                
    # Recommendations
    print("\n💡 Recommendations:")
    
    # Based on data, suggest complexity limits
    safe_complexity = 0
    for bucket, data in sorted(complexity_data.items()):
        if data.get('failure_rate', 100) < 20:  # Less than 20% failure
            safe_complexity = bucket
        else:
            break
            
    print(f"1. Keep prompt complexity below {safe_complexity + 1} for reliable execution")
    print("2. Use structured response format for all complexity levels")
    print("3. Enable retry mechanism for complexity 2+ tasks")
    print("4. Consider task decomposition for multi-step requests")
    
    # Create visualization if matplotlib available
    try:
        create_complexity_visualization(complexity_data, time_data)
        print("\n📈 Visualization saved to: claude_complexity_analysis.png")
    except ImportError:
        print("\n(Install matplotlib for visualizations)")


def create_complexity_visualization(complexity_data: Dict, time_data: Dict):
    """Create visualization of complexity analysis."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Failure rate by complexity
    buckets = sorted(complexity_data.keys())
    failure_rates = [complexity_data[b].get('failure_rate', 0) for b in buckets]
    
    ax1.bar(buckets, failure_rates, color='red', alpha=0.7)
    ax1.set_xlabel('Complexity Score')
    ax1.set_ylabel('Failure Rate (%)')
    ax1.set_title('Failure Rate by Prompt Complexity')
    ax1.grid(axis='y', alpha=0.3)
    
    # Execution time by complexity
    time_buckets = sorted(time_data.keys())
    mean_times = [time_data[b]['mean'] for b in time_buckets]
    
    ax2.plot(time_buckets, mean_times, 'b-o', linewidth=2, markersize=8)
    ax2.set_xlabel('Complexity Score')
    ax2.set_ylabel('Mean Execution Time (seconds)')
    ax2.set_title('Execution Time by Prompt Complexity')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('claude_complexity_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()


if __name__ == "__main__":
    # Run all analyses
    complexity_data = analyze_complexity_failure_correlation()
    time_data = analyze_execution_times()
    analyze_recent_failures()
    analyze_hallucination_patterns()
    generate_complexity_report()
    
    print("\n✅ Analysis complete!")