#!/usr/bin/env python3
"""
Run all stress tests using standalone WebSocket client.
This runner uses the existing server and doesn't restart it.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Any, Tuple

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../src'))

from cc_executor.core.client import WebSocketClient
from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>", level="INFO")


class AllStressTestRunner:
    """Run all stress tests from unified configuration"""
    
    def __init__(self, config_path: str = None):
        # Default to all_stress_tests.json
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'configs', 'all_stress_tests.json'
            )
        
        with open(config_path, 'r') as f:
            self.config = json.load(f)
            
        self.client = WebSocketClient()
        self.results = []
        self.start_time = None
        
    def verify_test(self, test: Dict[str, Any], output: str) -> Tuple[bool, List[str], List[str]]:
        """Verify test output matches expected patterns"""
        patterns = test.get('expected_patterns', [])
        found = []
        missing = []
        
        for pattern in patterns:
            if pattern.lower() in output.lower():
                found.append(pattern)
            else:
                missing.append(pattern)
                
        success = len(missing) == 0
        return success, found, missing
        
    async def run_test(self, test: Dict[str, Any], category_timeout: int) -> Dict[str, Any]:
        """Run a single test"""
        test_id = test['id']
        test_name = test['name']
        command = test['command']
        
        logger.info(f"[{test_id}] Running: {test_name}")
        
        start = time.time()
        
        try:
            # Let Redis determine timeout by not specifying it
            result = await self.client.execute_command(command)
            
            if result['success']:
                output = '\n'.join(result['output_data'])
                success, found, missing = self.verify_test(test, output)
                
                duration = time.time() - start
                
                if success:
                    logger.info(f"✅ PASSED in {duration:.1f}s")
                    return {
                        'test_id': test_id,
                        'name': test_name,
                        'status': 'passed',
                        'duration': duration,
                        'patterns_found': found,
                        'output_preview': output[:200] + '...' if len(output) > 200 else output
                    }
                else:
                    logger.error(f"❌ FAILED: Pattern mismatch - missing {missing}")
                    return {
                        'test_id': test_id,
                        'name': test_name,
                        'status': 'failed',
                        'duration': duration,
                        'error': f'Pattern mismatch: missing {missing}',
                        'patterns_found': found,
                        'patterns_missing': missing,
                        'output_preview': output[:200] + '...' if len(output) > 200 else output
                    }
            else:
                duration = time.time() - start
                logger.error(f"❌ FAILED: {result.get('error', 'Unknown error')}")
                return {
                    'test_id': test_id,
                    'name': test_name,
                    'status': 'failed',
                    'duration': duration,
                    'error': result.get('error', 'Unknown error')
                }
                
        except Exception as e:
            duration = time.time() - start
            logger.error(f"❌ FAILED: Unexpected error: {e}")
            return {
                'test_id': test_id,
                'name': test_name,
                'status': 'failed',
                'duration': duration,
                'error': f'Unexpected error: {str(e)}'
            }
            
    async def run_category(self, category_name: str, category_config: Dict[str, Any]) -> Dict[str, Any]:
        """Run all tests in a category"""
        logger.info(f"\n{'='*70}")
        logger.info(f"CATEGORY: {category_name.upper()}")
        logger.info(f"{'='*70}")
        logger.info(f"Description: {category_config['description']}")
        logger.info(f"Tests: {len(category_config['tests'])}")
        logger.info(f"Timeout: {category_config['timeout']}s\n")
        
        category_results = []
        category_start = time.time()
        
        for test in category_config['tests']:
            result = await self.run_test(test, category_config['timeout'])
            category_results.append(result)
            
        category_duration = time.time() - category_start
        passed = sum(1 for r in category_results if r['status'] == 'passed')
        
        logger.info(f"\nCategory Summary: {passed}/{len(category_results)} passed ({passed/len(category_results)*100:.1f}%)")
        logger.info(f"Category Duration: {category_duration:.1f}s")
        
        return {
            'category': category_name,
            'description': category_config['description'],
            'total_tests': len(category_results),
            'passed': passed,
            'failed': len(category_results) - passed,
            'success_rate': passed / len(category_results) * 100,
            'duration': category_duration,
            'results': category_results
        }
        
    async def run_all_tests(self):
        """Run all test categories"""
        logger.info("🔍 Running self-verification...")
        
        # Verify configuration
        if not self.config.get('categories'):
            logger.error("❌ No categories found in configuration")
            return
            
        logger.info(f"✅ Configuration valid")
        logger.info(f"📋 Found {len(self.config['categories'])} categories")
        
        # Count total tests
        total_tests = sum(
            len(cat['tests']) 
            for cat in self.config['categories'].values()
        )
        logger.info(f"📋 Total tests: {total_tests}")
        
        execution_id = f"ALL_STRESS_TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"🚀 Starting All Stress Tests - {execution_id}")
        
        self.start_time = time.time()
        
        # Run all categories
        for category_name, category_config in self.config['categories'].items():
            category_result = await self.run_category(category_name, category_config)
            self.results.append(category_result)
            
        # Generate summary
        total_duration = time.time() - self.start_time
        total_passed = sum(r['passed'] for r in self.results)
        total_failed = sum(r['failed'] for r in self.results)
        overall_success_rate = (total_passed / (total_passed + total_failed) * 100) if (total_passed + total_failed) > 0 else 0
        
        # Generate report
        report_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'reports', 'all_stress_tests_report.md'
        )
        
        self.generate_report(execution_id, total_duration, overall_success_rate, report_path)
        
        logger.info(f"\n📄 Report written to: {report_path}")
        logger.info(f"📊 Overall Success Rate: {overall_success_rate:.1f}% ({total_passed}/{total_passed + total_failed})")
        logger.info(f"⏱️  Total Duration: {total_duration:.1f}s")
        
    def generate_report(self, execution_id: str, total_duration: float, overall_success_rate: float, report_path: str):
        """Generate markdown report"""
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        with open(report_path, 'w') as f:
            f.write(f"# All Stress Tests Report\n\n")
            f.write(f"**Generated**: {datetime.now().isoformat()}  \n")
            f.write(f"**Execution ID**: {execution_id}  \n")
            f.write(f"**Total Duration**: {total_duration:.2f} seconds  \n")
            f.write(f"**Configuration**: {self.config.get('task_list_id', 'Unknown')}\n\n")
            
            # Overall summary
            total_tests = sum(r['total_tests'] for r in self.results)
            total_passed = sum(r['passed'] for r in self.results)
            total_failed = sum(r['failed'] for r in self.results)
            
            f.write(f"## Overall Summary\n\n")
            f.write(f"- **Total Categories**: {len(self.results)}\n")
            f.write(f"- **Total Tests**: {total_tests}\n")
            f.write(f"- **Passed**: {total_passed} ✅\n")
            f.write(f"- **Failed**: {total_failed} ❌\n")
            f.write(f"- **Success Rate**: {overall_success_rate:.1f}%\n\n")
            
            # Category summaries
            f.write(f"## Category Summaries\n\n")
            
            for category_result in self.results:
                f.write(f"### {category_result['category'].upper()}\n\n")
                f.write(f"- **Description**: {category_result['description']}\n")
                f.write(f"- **Tests**: {category_result['total_tests']}\n")
                f.write(f"- **Passed**: {category_result['passed']} ({category_result['success_rate']:.1f}%)\n")
                f.write(f"- **Duration**: {category_result['duration']:.1f}s\n\n")
            
            # Detailed results by category
            f.write(f"## Detailed Results\n\n")
            
            for category_result in self.results:
                f.write(f"### {category_result['category'].upper()} Tests\n\n")
                
                for test_result in category_result['results']:
                    status_icon = "✅" if test_result['status'] == 'passed' else "❌"
                    f.write(f"#### {test_result['name']} - {status_icon} {test_result['status'].upper()}\n\n")
                    f.write(f"- **ID**: `{test_result['test_id']}`\n")
                    f.write(f"- **Duration**: {test_result['duration']:.2f}s\n")
                    
                    if test_result['status'] == 'failed':
                        f.write(f"- **Error**: {test_result.get('error', 'Unknown error')}\n")
                        
                    if 'patterns_found' in test_result:
                        f.write(f"- **Patterns Found**: {len(test_result['patterns_found'])}\n")
                        
                    if 'patterns_missing' in test_result:
                        f.write(f"- **Patterns Missing**: {test_result['patterns_missing']}\n")
                        
                    if 'output_preview' in test_result:
                        f.write(f"- **Output Preview**: `{test_result['output_preview']}`\n")
                        
                    f.write("\n")
            
            # Redis timeout analysis
            f.write(f"## Redis Timeout Analysis\n\n")
            f.write(f"Tests were run without specifying timeouts, allowing Redis to estimate based on:\n")
            f.write(f"- Historical execution data\n")
            f.write(f"- Task complexity classification\n")
            f.write(f"- System load monitoring\n\n")
            f.write(f"This adaptive timeout system prevents false failures due to hardcoded limits.\n")

async def main():
    """Main entry point"""
    runner = AllStressTestRunner()
    await runner.run_all_tests()
    await runner.client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())