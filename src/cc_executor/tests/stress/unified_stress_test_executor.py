#!/usr/bin/env python3
"""
Unified Stress Test Executor for CC-Executor Docker Instance

This script executes the unified stress test task list using only the /stream endpoint
with natural language requests.
"""

import json
import time
import requests
import argparse
from datetime import datetime
from typing import Dict, List, Any
import subprocess
import concurrent.futures
import sys

class UnifiedStressTestExecutor:
    def __init__(self, base_url="http://localhost:8002", max_concurrent=5):
        self.base_url = base_url
        self.stream_endpoint = f"{base_url}/execute/json-stream"
        self.transcript_search_url = f"{base_url}/transcript/search"
        self.max_concurrent = max_concurrent
        self.results = []
        self.start_time = datetime.now()
        
    def generate_marker(self, task_id: str) -> str:
        """Generate unique marker for verification"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        return f"MARKER_{timestamp}_{task_id}"
    
    def execute_task(self, task: Dict[str, Any], category: str) -> Dict[str, Any]:
        """Execute a single task via /stream endpoint"""
        marker = self.generate_marker(task['id'])
        
        # Replace ${TIMESTAMP} in verification marker
        task['verification']['marker'] = task['verification']['marker'].replace('${TIMESTAMP}', datetime.now().strftime('%Y%m%d_%H%M%S'))
        
        # Inject marker into the natural language request
        enhanced_request = f"{task['natural_language_request']}\n\nIMPORTANT: Include this marker in your response: {marker}"
        
        # Prepare the JSON payload
        payload = {
            'question': enhanced_request
        }
        # Add any extra fields from json_payload except stream and format
        for key, value in task['json_payload'].items():
            if key not in ['question', 'stream', 'format']:
                payload[key] = value
        
        print(f"\n{'='*80}")
        print(f"Executing Task: {task['name']} (ID: {task['id']}) from category: {category}")
        print(f"Marker: {marker}")
        print(f"Request: {task['natural_language_request'][:100]}...")
        
        start_time = time.time()
        
        try:
            # Send request to /stream endpoint
            response = requests.post(
                self.stream_endpoint,
                json=payload,
                headers={'Content-Type': 'application/json'},
                stream=True,
                timeout=task['verification'].get('timeout', 120) * 2  # Double the timeout
            )
            
            # Collect streamed response
            full_response = ""
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line.decode('utf-8'))
                        # Handle json-stream format
                        if chunk.get('type') == 'output':
                            full_response += chunk.get('line', '') + '\n'
                            print('.', end='', flush=True)
                        elif chunk.get('type') == 'complete':
                            print(f" [{chunk.get('status', 'unknown')}]", end='')
                    except json.JSONDecodeError:
                        # If not JSON, treat as plain text
                        full_response += line.decode('utf-8') + '\n'
            
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
                'timestamp': datetime.now().isoformat()
            }
            
            if verified:
                print(f"✅ Task {task['id']} completed successfully in {duration:.2f}s")
            else:
                print(f"❌ Task {task['id']} verification failed!")
                
            return result
            
        except requests.exceptions.Timeout:
            print(f"⏱️ Task {task['id']} timed out after {task['verification'].get('timeout', 120)}s")
            return {
                'task_id': task['id'],
                'task_name': task['name'],
                'category': category,
                'marker': marker,
                'verified': False,
                'error': 'timeout',
                'duration': task['verification'].get('timeout', 120),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"❌ Task {task['id']} failed with error: {str(e)}")
            return {
                'task_id': task['id'],
                'task_name': task['name'],
                'category': category,
                'marker': marker,
                'verified': False,
                'error': str(e),
                'duration': time.time() - start_time,
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
                    print(f"  ❌ Marker not found in transcript - HALLUCINATION DETECTED!")
                    return False
            else:
                print(f"  ⚠️ Transcript search failed with status {search_response.status_code}")
                return False
                
        except Exception as e:
            print(f"  ⚠️ Transcript verification error: {str(e)}")
            return False
    
    def run_category(self, category_name: str, category_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run all tasks in a category"""
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
                    executor.submit(self.execute_task, task, category_name): task 
                    for task in category_data['tasks']
                }
                
                for future in concurrent.futures.as_completed(future_to_task):
                    result = future.result()
                    category_results.append(result)
                    self.results.append(result)
        else:
            # Run tasks sequentially
            for task in category_data['tasks']:
                result = self.execute_task(task, category_name)
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
        
        # Generate summary report
        self.generate_report()
    
    def generate_report(self):
        """Generate execution summary report"""
        total_duration = (datetime.now() - self.start_time).total_seconds()
        
        print(f"\n{'='*80}")
        print(f"EXECUTION SUMMARY REPORT")
        print(f"{'='*80}")
        print(f"Start Time: {self.start_time}")
        print(f"End Time: {datetime.now()}")
        print(f"Total Duration: {total_duration:.2f}s")
        print(f"\nTotal Tasks: {len(self.results)}")
        
        # Calculate success metrics
        successful = sum(1 for r in self.results if r.get('verified', False))
        failed = len(self.results) - successful
        success_rate = (successful / len(self.results) * 100) if self.results else 0
        
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        # Category breakdown
        print(f"\n{'Category':<20} {'Total':<10} {'Success':<10} {'Failed':<10} {'Rate':<10}")
        print(f"{'-'*60}")
        
        categories = {}
        for result in self.results:
            cat = result.get('category', 'unknown')
            if cat not in categories:
                categories[cat] = {'total': 0, 'success': 0, 'failed': 0}
            categories[cat]['total'] += 1
            if result.get('verified', False):
                categories[cat]['success'] += 1
            else:
                categories[cat]['failed'] += 1
        
        for cat, stats in categories.items():
            rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"{cat:<20} {stats['total']:<10} {stats['success']:<10} {stats['failed']:<10} {rate:<10.1f}%")
        
        # Failed tasks details
        if failed > 0:
            print(f"\n{'='*80}")
            print("FAILED TASKS DETAILS:")
            print(f"{'='*80}")
            for result in self.results:
                if not result.get('verified', False):
                    print(f"\nTask: {result['task_id']} ({result['task_name']})")
                    print(f"Category: {result['category']}")
                    print(f"Error: {result.get('error', 'Verification failed')}")
                    print(f"Marker: {result['marker']}")
        
        # Save detailed results
        report_path = f"stress_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump({
                'summary': {
                    'start_time': self.start_time.isoformat(),
                    'end_time': datetime.now().isoformat(),
                    'total_duration': total_duration,
                    'total_tasks': len(self.results),
                    'successful': successful,
                    'failed': failed,
                    'success_rate': success_rate
                },
                'categories': categories,
                'detailed_results': self.results
            }, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_path}")

def main():
    parser = argparse.ArgumentParser(description='Run unified stress tests')
    parser.add_argument('--categories', nargs='+', help='Specific categories to run')
    parser.add_argument('--max-concurrent', type=int, default=5, help='Max concurrent tasks')
    parser.add_argument('--base-url', default='http://localhost:8002', help='Base URL for Docker Claude')
    parser.add_argument('--task-list', default='../../tasks/unified_stress_test_tasks.json', help='Path to task list')
    
    args = parser.parse_args()
    
    executor = UnifiedStressTestExecutor(
        base_url=args.base_url,
        max_concurrent=args.max_concurrent
    )
    
    try:
        executor.run_all_tests(args.task_list, args.categories)
    except KeyboardInterrupt:
        print("\n\n⚠️ Test execution interrupted by user")
        executor.generate_report()
    except Exception as e:
        print(f"\n❌ Test execution failed: {str(e)}")
        executor.generate_report()

if __name__ == "__main__":
    main()