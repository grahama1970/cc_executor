#!/usr/bin/env python3
"""
Advanced CC_Execute example - Tool Integration & External Verification.

This demonstrates the advanced patterns from README.md:
- Direct MCP tool usage (no cc_execute)
- cc_execute for complex generation tasks
- External model verification
- Mixed execution patterns
"""
import sys
from pathlib import Path
import json
from datetime import datetime
import time

# Add project to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from cc_executor.prompts.cc_execute_utils import execute_task_via_websocket

def execute_direct_task(task_desc: str, timeout: int = 60) -> dict:
    """
    Execute a task directly without cc_execute.
    This is for simple tasks that don't need fresh context.
    """
    # For this example, we simulate direct execution
    # In real usage, this would call Claude directly without cc_execute
    print("📡 Executing directly (no cc_execute needed)...")
    
    # Simulate MCP tool call - in reality this would be:
    # result = await mcp_perplexity_ask(task_desc)
    
    return {
        'success': True,
        'output_lines': [
            "Simulated MCP perplexity-ask response:",
            "Recent quantum entanglement breakthroughs include...",
            "- 2024: Google's Willow chip achieved 100+ qubit entanglement",
            "- 2025: MIT demonstrated room-temperature entanglement stability",
            "Note: In real usage, this would be actual perplexity-ask results"
        ],
        'direct_execution': True
    }

def main():
    """Execute advanced task list with mixed patterns."""
    print("="*80)
    print("CC Executor - Advanced Usage Example")
    print("Tool Integration & External Verification Pattern")
    print("="*80)
    print("\nThis example demonstrates:")
    print("- Direct MCP tool usage (Task 1)")
    print("- cc_execute for complex tasks (Tasks 2-4)")
    print("- External model verification (Task 3)")
    print("- Sequential dependencies")
    print("- Automatic UUID4 verification when using cc_execute")
    
    # Define tasks with mixed execution patterns
    tasks = [
        {
            'num': 1,
            'name': 'Research Quantum Entanglement',
            'execution': 'direct',  # No cc_execute needed
            'desc': '''Use the perplexity-ask MCP tool to research quantum entanglement breakthroughs from 2024-2025. Save the research findings to quantum_research.md with:
- Recent experimental breakthroughs
- New theoretical developments
- Practical applications emerging
- Key researchers and institutions''',
            'timeout': 60,
            'expected_file': 'quantum_research.md'
        },
        {
            'num': 2,
            'name': 'Create Tutorial',
            'execution': 'cc_execute',  # Needs fresh context
            'desc': '''Using cc_execute.md: Based on the research in quantum_research.md, create a beginner-friendly tutorial on quantum entanglement. Save as quantum_tutorial.md with:
- Introduction for non-physicists
- Core concepts explained simply
- Python code examples using qiskit
- Visual diagrams (as ASCII art or mermaid)
- Real-world applications
- Further learning resources''',
            'timeout': 300,  # 5 minutes
            'expected_file': 'quantum_tutorial.md'
        },
        {
            'num': 3,
            'name': 'External Review',
            'execution': 'cc_execute',  # Fresh context for unbiased review
            'desc': '''Using cc_execute.md: Review the tutorial from quantum_tutorial.md using the ask-litellm.md prompt with gemini-2.0-flash-exp model. Create review_feedback.md with:
- Technical accuracy assessment
- Pedagogical effectiveness
- Code quality review
- Suggestions for improvement
- Missing concepts to add''',
            'timeout': 180,  # 3 minutes
            'expected_file': 'review_feedback.md'
        },
        {
            'num': 4,
            'name': 'Interactive Exercises',
            'execution': 'cc_execute',  # Complex generation needs isolation
            'desc': '''Using cc_execute.md: Based on the tutorial and review feedback, create interactive Jupyter notebook exercises. Save as quantum_exercises.ipynb with:
- Exercise 1: Basic quantum states
- Exercise 2: Creating entangled states
- Exercise 3: Measuring quantum correlations
- Exercise 4: Simulating Bell's inequality
- Solutions with explanations''',
            'timeout': 300,  # 5 minutes
            'expected_file': 'quantum_exercises.ipynb'
        }
    ]
    
    # Track execution
    results = []
    start_time = time.time()
    
    # Execute each task with appropriate method
    for task in tasks:
        print(f"\n{'='*80}")
        print(f"Task {task['num']}: {task['name']}")
        print(f"Execution Mode: {task['execution'].upper()}")
        print(f"{'='*80}")
        print(f"Timeout: {task['timeout']}s")
        print(f"\nTask description:")
        print(task['desc'][:200] + "..." if len(task['desc']) > 200 else task['desc'])
        
        task_start = time.time()
        
        # Choose execution method
        if task['execution'] == 'direct':
            # Direct execution (no cc_execute)
            print(f"\n🚀 Executing directly (simple task, no fresh context needed)...")
            result = execute_direct_task(task['desc'], task['timeout'])
        else:
            # Use cc_execute for complex tasks
            print(f"\n🔄 Executing via cc_execute (complex task, needs fresh context)...")
            result = execute_task_via_websocket(
                task=task['desc'],
                timeout=task['timeout'],
                tools=["Read", "Write", "Edit", "mcp__perplexity-ask__perplexity_ask"]
            )
        
        task_duration = time.time() - task_start
        
        # Save result
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path("tmp/responses")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"task_{task['num']}_{timestamp}.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        # Extract status
        success = result.get('success', False)
        status = 'success' if success else 'failed'
        
        # Check for UUID verification (only for cc_execute tasks)
        verification_status = "N/A"
        if task['execution'] == 'cc_execute' and 'hook_verification' in result:
            verification_passed = result['hook_verification'].get('verification_passed', False)
            verification_status = "🔐 VERIFIED" if verification_passed else "⚠️ NOT VERIFIED"
            
            # Show verification details
            print(f"\nUUID Verification: {verification_status}")
            if result['hook_verification'].get('messages'):
                for msg in result['hook_verification']['messages']:
                    print(f"  {msg}")
        
        # Check if expected file would be created
        file_status = "Would create" if success else "Not created"
        
        results.append({
            'task': task['name'],
            'execution': task['execution'],
            'status': status,
            'success': success,
            'verification': verification_status,
            'duration': task_duration,
            'expected_file': task['expected_file'],
            'file_status': file_status
        })
        
        # Task summary
        print(f"\n{'✅' if success else '❌'} Task Result:")
        print(f"  Status: {status}")
        print(f"  Duration: {task_duration:.1f}s")
        print(f"  Expected output: {task['expected_file']} ({file_status})")
        if task['execution'] == 'cc_execute':
            print(f"  UUID Verification: {verification_status}")
        print(f"  Output saved: {output_file}")
        
        if not success:
            print(f"\n❌ Task failed. Stopping execution.")
            break
    
    # Overall summary
    total_duration = time.time() - start_time
    print(f"\n{'='*80}")
    print("EXECUTION SUMMARY")
    print(f"{'='*80}")
    print(f"Total execution time: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
    print(f"\nTask Results:")
    
    for i, r in enumerate(results, 1):
        status_icon = "✅" if r['success'] else "❌"
        exec_type = "📡 Direct" if r['execution'] == 'direct' else "🔄 cc_execute"
        
        print(f"\n{status_icon} Task {i}: {r['task']}")
        print(f"   Execution: {exec_type}")
        print(f"   Duration: {r['duration']:.1f}s")
        print(f"   Output: {r['expected_file']}")
        if r['execution'] == 'cc_execute':
            print(f"   Verification: {r['verification']}")
    
    # Pattern demonstration
    print(f"\n{'='*80}")
    print("PATTERNS DEMONSTRATED")
    print(f"{'='*80}")
    
    direct_tasks = sum(1 for r in results if r['execution'] == 'direct')
    cc_execute_tasks = sum(1 for r in results if r['execution'] == 'cc_execute')
    
    print(f"📡 Direct execution: {direct_tasks} task(s)")
    print("   - Used for simple MCP tool calls")
    print("   - No fresh context needed")
    print("   - No UUID verification")
    
    print(f"\n🔄 cc_execute pattern: {cc_execute_tasks} task(s)")
    print("   - Used for complex generation")
    print("   - Fresh 200K context per task")
    print("   - Automatic UUID4 verification")
    print("   - WebSocket keeps long tasks alive")
    
    # Key insights
    print(f"\n{'='*80}")
    print("KEY INSIGHTS")
    print(f"{'='*80}")
    print("1. Not every task needs cc_execute - use it when you need:")
    print("   - Fresh context isolation")
    print("   - Long-running execution (>1 minute)")
    print("   - Complex generation tasks")
    
    print("\n2. Direct execution is fine for:")
    print("   - Simple tool calls (perplexity-ask, etc.)")
    print("   - Quick queries")
    print("   - Tasks that don't need isolation")
    
    print("\n3. cc_execute provides automatic features:")
    print("   - UUID4 anti-hallucination verification")
    print("   - Error recovery with retries")
    print("   - WebSocket for reliability")
    
    if all(r['success'] for r in results):
        print(f"\n🎉 All tasks completed successfully!")
        print("\nThis workflow demonstrated:")
        print("- Research → Tutorial → Review → Exercises")
        print("- Each task built on previous outputs")
        print("- Mixed execution patterns for efficiency")

if __name__ == "__main__":
    main()