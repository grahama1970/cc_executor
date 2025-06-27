#!/usr/bin/env python3
"""
Unified Stress Test Executor V2 - With Dynamic Timeout Management
Executes stress test tasks against cc-executor with intelligent timeout handling
"""

import json
import time
import requests
import argparse
import concurrent.futures
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import re
import threading
from execution_time_tracker import ExecutionTimeTracker

class UnifiedStressTestExecutorV2:
    def __init__(self, base_url: str = "http://localhost:8002", max_concurrent: int = 10):
        self.base_url = base_url
        self.stream_endpoint = f"{base_url}/execute/stream"
        self.json_stream_endpoint = f"{base_url}/execute/json-stream"
        self.transcript_search_url = "http://localhost:8002/transcript/search"
        self.max_concurrent = max_concurrent
        self.results = []
        self.time_tracker = ExecutionTimeTracker()
        
    def estimate_task_complexity(self, task: Dict[str, Any]) -> Dict[str, int]:
        """Estimate task complexity and return appropriate timeouts"""
        request = task['natural_language_request'].lower()
        
        # Base timeout for MCP - MUCH longer than web!
        base_timeout = 300  # 5 minutes minimum!
        
        # Complexity factors
        complexity_score = 0
        
        # Word count factor
        word_count = len(request.split())
        complexity_score += word_count // 50  # Every 50 words adds to complexity
        
        # Specific complexity indicators
        complexity_keywords = {
            'comprehensive': 10,
            'detailed': 5,
            'complete': 5,
            'full': 5,
            'entire': 5,
            'all': 3,
            'multiple': 3,
            'compare': 5,
            'analyze': 5,
            'research': 10,
            'guide': 10,
            'tutorial': 8,
            'explain': 3,
            'story': 15,  # Stories take time
            'essay': 10,
            'report': 8,
            'documentation': 8,
            '10000 word': 30,
            '5000 word': 20,
            '1000 word': 10,
            '100': 10,  # 100 of anything is a lot
            '20': 5,
            '10': 3,
        }
        
        for keyword, score in complexity_keywords.items():
            if keyword in request:
                complexity_score += score
        
        # Task-specific adjustments
        if 'recipe' in request:
            complexity_score += 5  # Recipes need detailed steps
        if 'build' in request and 'app' in request:
            complexity_score += 20  # Building apps is complex
        if 'fibonacci' in request:
            complexity_score += 5  # Math calculations
        if 'llm' in request or 'model' in request:
            complexity_score += 10  # External API calls take time
        
        # Get historical timeout data
        task_id = task.get('id', 'unknown')
        category = task.get('category', 'unknown')
        
        # Calculate base timeout with complexity
        calculated_timeout = base_timeout + (complexity_score * 30)  # 30s per complexity point
        
        # Check Redis for historical timeout data
        import subprocess
        try:
            result = subprocess.run(
                ['/home/graham/.claude/commands/check-task-timeout', category, task_id, str(calculated_timeout)],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Extract timeout from output
                for line in result.stdout.split('\n'):
                    if line.startswith('TIMEOUT='):
                        redis_timeout = float(line.split('=')[1])
                        task_timeout = redis_timeout
                        print(f"Using Redis historical timeout: {task_timeout:.0f}s")
                        break
                else:
                    task_timeout = calculated_timeout
                    print(f"Using calculated timeout: {task_timeout:.0f}s (no Redis data)")
            else:
                task_timeout = calculated_timeout
                print(f"Using calculated timeout: {task_timeout:.0f}s (Redis check failed)")
        except:
            task_timeout = calculated_timeout
            print(f"Using calculated timeout: {task_timeout:.0f}s (Redis unavailable)")
        
        # MCP connections should be VERY patient
        connection_timeout = max(task_timeout * 2, 1800)  # At least 30 minutes!
        heartbeat_interval = 30  # Heartbeat every 30 seconds
        
        # Use task's specified timeout if it's larger
        if 'verification' in task and 'timeout' in task['verification']:
            # For MCP, multiply any hardcoded timeouts by 3
            verification_timeout = task['verification']['timeout'] * 3
            task_timeout = max(task_timeout, verification_timeout)
        
        return {
            'task_timeout': task_timeout,
            'connection_timeout': connection_timeout,
            'heartbeat_interval': heartbeat_interval,
            'complexity_score': complexity_score
        }
    
    def execute_task_with_heartbeat(self, task: Dict[str, Any], category: str) -> Dict[str, Any]:
        """Execute a single task with heartbeat monitoring"""
        marker = f"MARKER_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{task['id']}"
        
        # Estimate complexity and timeouts
        timeouts = self.estimate_task_complexity(task)
        
        print(f"\n{'='*80}")
        print(f"Executing Task: {task['name']} (ID: {task['id']}) from category: {category}")
        print(f"Complexity Score: {timeouts['complexity_score']}")
        print(f"Task Timeout: {timeouts['task_timeout']}s")
        print(f"Marker: {marker}")
        print(f"Request: {task['natural_language_request'][:100]}...")
        
        # Add marker to request
        payload = task['json_payload'].copy()
        payload['question'] = f"{task['natural_language_request']}\n\nIMPORTANT: Include this marker in your response: {marker}"
        
        start_time = time.time()
        full_response = ""
        task_completed = False
        last_activity = time.time()
        
        def heartbeat_monitor():
            """Monitor for activity and print heartbeat"""
            nonlocal last_activity, task_completed
            while not task_completed:
                time.sleep(timeouts['heartbeat_interval'])
                if not task_completed:
                    elapsed = time.time() - last_activity
                    total_elapsed = time.time() - start_time
                    if elapsed > timeouts['heartbeat_interval']:
                        print(f"\n💓 Heartbeat: Task still running... ({total_elapsed:.0f}s elapsed)")
                    if total_elapsed > timeouts['task_timeout']:
                        print(f"\n⏰ Task exceeded timeout of {timeouts['task_timeout']}s")
                        break
        
        # Start heartbeat thread
        heartbeat_thread = threading.Thread(target=heartbeat_monitor, daemon=True)
        heartbeat_thread.start()
        
        try:
            # Send request to /execute/json-stream endpoint
            response = requests.post(
                self.json_stream_endpoint,
                json=payload,
                headers={'Content-Type': 'application/json'},
                stream=True,
                timeout=timeouts['connection_timeout']
            )
            
            # Collect streamed response with activity tracking
            dots_printed = 0
            for line in response.iter_lines():
                if line:
                    last_activity = time.time()  # Update activity timestamp
                    try:
                        chunk = json.loads(line.decode('utf-8'))
                        # Handle json-stream format
                        if chunk.get('type') == 'output':
                            full_response += chunk.get('line', '') + '\n'
                            dots_printed += 1
                            if dots_printed % 10 == 0:
                                print('.', end='', flush=True)
                        elif chunk.get('type') == 'complete':
                            print(f" [{chunk.get('status', 'unknown')}]", end='')
                            task_completed = True
                    except json.JSONDecodeError:
                        # If not JSON, treat as plain text
                        full_response += line.decode('utf-8') + '\n'
                
                # Check if we've exceeded task timeout
                if time.time() - start_time > timeouts['task_timeout']:
                    print(f"\n⏱️ Task timeout reached ({timeouts['task_timeout']}s)")
                    break
            
            task_completed = True
            print()  # New line after dots
            
            # Wait a bit for transcript to update
            time.sleep(2)
            
            # Verify in transcript
            verified = self.verify_execution(marker, task, full_response)
            
            duration = time.time() - start_time
            
            result = {
                'task_id': task['id'],
                'task_name': task['name'],
                'category': category,
                'marker': marker,
                'verified': verified,
                'duration': duration,
                'response_length': len(full_response),
                'complexity_score': timeouts['complexity_score'],
                'timestamp': datetime.now().isoformat()
            }
            
            # Track execution time in Redis for future predictions
            try:
                subprocess.run([
                    '/home/graham/.claude/commands/record-task-time',
                    category,
                    task['id'],
                    str(timeouts['task_timeout']),
                    str(duration),
                    'true' if verified else 'false'
                ], capture_output=True, timeout=5)
            except:
                pass  # Don't fail if Redis recording fails
            
            if verified:
                print(f"✅ Task {task['id']} completed successfully in {duration:.2f}s")
            else:
                print(f"❌ Task {task['id']} verification failed!")
                
            return result
            
        except requests.exceptions.Timeout:
            task_completed = True
            duration = time.time() - start_time
            print(f"\n⏱️ Task {task['id']} connection timeout after {duration:.0f}s")
            
            # Track the timeout in Redis
            try:
                subprocess.run([
                    '/home/graham/.claude/commands/record-task-time',
                    category,
                    task['id'],
                    str(timeouts['task_timeout']),
                    str(duration),
                    'false'
                ], capture_output=True, timeout=5)
            except:
                pass
            
            return {
                'task_id': task['id'],
                'task_name': task['name'],
                'category': category,
                'marker': marker,
                'verified': False,
                'error': 'connection_timeout',
                'duration': duration,
                'complexity_score': timeouts['complexity_score'],
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            task_completed = True
            print(f"\n❌ Task {task['id']} failed with error: {str(e)}")
            return {
                'task_id': task['id'],
                'task_name': task['name'],
                'category': category,
                'marker': marker,
                'verified': False,
                'error': str(e),
                'duration': time.time() - start_time,
                'complexity_score': timeouts['complexity_score'],
                'timestamp': datetime.now().isoformat()
            }
    
    def verify_execution(self, marker: str, task: Dict[str, Any], response: str) -> bool:
        """Verify task execution in transcript"""
        # First check if marker appears in response
        if marker not in response:
            print(f"  ⚠️ Marker not found in response")
            return False
        
        # Then verify in transcript
        try:
            search_response = requests.post(
                self.transcript_search_url,
                params={'query': marker, 'max_results': 10},
                timeout=10
            )
            
            if search_response.status_code == 200:
                transcript_data = search_response.text
                if marker in transcript_data:
                    print(f"  ✓ Marker verified in transcript")
                    
                    # Check for expected patterns
                    for pattern in task['verification'].get('expected_patterns', []):
                        if pattern.lower() in response.lower():
                            print(f"  ✓ Found expected pattern: {pattern}")
                        else:
                            print(f"  ⚠️ Missing expected pattern: {pattern}")
                    
                    return True
                else:
                    print(f"  ⚠️ Marker not found in transcript")
                    return False
            else:
                print(f"  ⚠️ Transcript search failed: {search_response.status_code}")
                return False
                
        except Exception as e:
            print(f"  ⚠️ Transcript verification error: {str(e)}")
            return False
    
    def run_category(self, category_name: str, category_data: Dict[str, Any]):
        """Run all tests in a category"""
        print(f"\n{'#'*80}")
        print(f"# Running Category: {category_name}")
        print(f"# Description: {category_data['description']}")
        print(f"# Tasks: {len(category_data['tasks'])}")
        print(f"{'#'*80}")
        
        category_results = []
        
        # Determine if we should run in parallel based on category
        parallel_categories = ['parallel', 'rapid_fire', 'extreme_stress']
        
        if category_name in parallel_categories and self.max_concurrent > 1:
            # Run tasks in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
                future_to_task = {
                    executor.submit(self.execute_task_with_heartbeat, task, category_name): task 
                    for task in category_data['tasks']
                }
                
                for future in concurrent.futures.as_completed(future_to_task):
                    result = future.result()
                    category_results.append(result)
                    self.results.append(result)
        else:
            # Run tasks sequentially
            for task in category_data['tasks']:
                result = self.execute_task_with_heartbeat(task, category_name)
                category_results.append(result)
                self.results.append(result)
                
                # Small delay between sequential tasks
                time.sleep(2)
        
        return category_results
    
    def run_all_tests(self, task_list_path: str, categories: List[str] = None):
        """Run all tests from the task list"""
        # Load task list
        with open(task_list_path, 'r') as f:
            task_list = json.load(f)
        
        print(f"Loaded task list: {task_list['task_list_id']}")
        print(f"Description: {task_list['description']}")
        
        # If specific categories specified, filter
        if categories:
            categories_to_run = {k: v for k, v in task_list['categories'].items() if k in categories}
        else:
            categories_to_run = task_list['categories']
        
        # Run each category
        for category_name, category_data in categories_to_run.items():
            self.run_category(category_name, category_data)
    
    def generate_report(self, output_file: str = None):
        """Generate execution report"""
        if not self.results:
            print("No results to report")
            return
        
        # Calculate statistics
        total_tasks = len(self.results)
        successful_tasks = len([r for r in self.results if r.get('verified', False)])
        failed_tasks = total_tasks - successful_tasks
        
        # Group by category
        categories = {}
        for result in self.results:
            cat = result['category']
            if cat not in categories:
                categories[cat] = {'total': 0, 'success': 0, 'failed': 0}
            categories[cat]['total'] += 1
            if result.get('verified', False):
                categories[cat]['success'] += 1
            else:
                categories[cat]['failed'] += 1
        
        # Generate report
        report = {
            'summary': {
                'start_time': min(r['timestamp'] for r in self.results),
                'end_time': max(r['timestamp'] for r in self.results),
                'total_tasks': total_tasks,
                'successful_tasks': successful_tasks,
                'failed_tasks': failed_tasks,
                'success_rate': (successful_tasks / total_tasks * 100) if total_tasks > 0 else 0
            },
            'categories': categories,
            'detailed_results': self.results
        }
        
        # Print summary
        print(f"\n{'='*80}")
        print("EXECUTION SUMMARY REPORT")
        print(f"{'='*80}")
        print(f"Start Time: {report['summary']['start_time']}")
        print(f"End Time: {report['summary']['end_time']}")
        
        # Calculate duration
        start = datetime.fromisoformat(report['summary']['start_time'])
        end = datetime.fromisoformat(report['summary']['end_time'])
        duration = (end - start).total_seconds()
        print(f"Total Duration: {duration:.2f}s")
        
        print(f"\nTotal Tasks: {total_tasks}")
        print(f"Successful: {successful_tasks}")
        print(f"Failed: {failed_tasks}")
        print(f"Success Rate: {report['summary']['success_rate']:.1f}%")
        
        print(f"\n{'Category':<20} {'Total':<10} {'Success':<10} {'Failed':<10} {'Rate':<10}")
        print("-" * 60)
        for cat_name, cat_stats in categories.items():
            rate = (cat_stats['success'] / cat_stats['total'] * 100) if cat_stats['total'] > 0 else 0
            print(f"{cat_name:<20} {cat_stats['total']:<10} {cat_stats['success']:<10} {cat_stats['failed']:<10} {rate:<10.1f}%")
        
        # Show failed tasks
        failed_results = [r for r in self.results if not r.get('verified', False)]
        if failed_results:
            print(f"\n{'='*80}")
            print("FAILED TASKS DETAILS:")
            print(f"{'='*80}")
            for result in failed_results:
                print(f"\nTask: {result['task_id']} ({result['task_name']})")
                print(f"Category: {result['category']}")
                print(f"Error: {result.get('error', 'Verification failed')}")
                print(f"Marker: {result['marker']}")
                print(f"Complexity Score: {result.get('complexity_score', 'N/A')}")
        
        # Save detailed report
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\n📄 Detailed report saved to: {output_file}")
        
        return report

def main():
    parser = argparse.ArgumentParser(description='Run unified stress tests against cc-executor')
    parser.add_argument('--base-url', default='http://localhost:8002', help='Base URL for cc-executor')
    parser.add_argument('--categories', nargs='+', help='Specific categories to run')
    parser.add_argument('--max-concurrent', type=int, default=10, help='Max concurrent tasks')
    parser.add_argument('--task-list', default='../../tasks/unified_stress_test_tasks.json', 
                       help='Path to task list JSON file')
    parser.add_argument('--report', default=f'stress_test_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
                       help='Output report file')
    
    args = parser.parse_args()
    
    try:
        executor = UnifiedStressTestExecutorV2(
            base_url=args.base_url,
            max_concurrent=args.max_concurrent
        )
        
        executor.run_all_tests(
            task_list_path=args.task_list,
            categories=args.categories
        )
        
        executor.generate_report(output_file=args.report)
        
    except FileNotFoundError as e:
        print(f"❌ Task list not found: {e}")
        print("Make sure you're running from the correct directory or provide --task-list path")
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()