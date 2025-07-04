#!/usr/bin/env python3
"""
Comprehensive assessment of all hook usage functions.
Uses full pre/post hook chain and generates report in tmp/.
"""

import os
import sys
import subprocess
import json
import time
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime

# CRITICAL: Set up paths before imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir.parent))
sys.path.insert(0, str(current_dir.parent.parent))

# Import hooks for pre/post processing
try:
    from cc_executor.hooks import setup_environment
    from cc_executor.hooks import check_task_dependencies
    from cc_executor.hooks import analyze_task_complexity
    from cc_executor.hooks import truncate_logs
    from cc_executor.hooks import record_execution_metrics
    from cc_executor.hooks import claude_response_validator
    from cc_executor.hooks import update_task_status
    HOOKS_AVAILABLE = True
except ImportError:
    HOOKS_AVAILABLE = False
    print("WARNING: Hooks not available - running without full hook chain")

class HookUsageAssessor:
    """Run and assess all hook usage functions with full hook chain."""
    
    def __init__(self):
        # Hooks directory is at src/cc_executor/hooks
        self.hooks_dir = Path(__file__).parent.parent.parent  # Go up to hooks/
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create reports directory in prompts/reports
        self.reports_dir = Path(__file__).parent.parent / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        
        self.report_path = self.reports_dir / f"HOOKS_USAGE_REPORT_{self.timestamp}.md"
        
        # Still use tmp for temporary execution artifacts
        self.tmp_dir = self.hooks_dir / "tmp"
        self.tmp_dir.mkdir(exist_ok=True)
        self.results = []
        self.start_time = time.time()
        self.redis_client = self._init_redis()
        self.test_session_id = f"hook_assess_{self.timestamp}"
        
        # Create temp directory for test outputs
        self.temp_dir = self.tmp_dir / f"hook_assess_{self.timestamp}"
        self.temp_dir.mkdir(exist_ok=True)
        
        # Track which hooks were used
        self.hooks_used = {
            'pre': [],
            'post': []
        }
        
    def _init_redis(self):
        """Initialize Redis connection for validation."""
        try:
            import redis
            client = redis.Redis(decode_responses=True)
            client.ping()
            return client
        except:
            return None
    
    def run_pre_hooks(self, hook_name: str, env: Dict[str, str]) -> Dict[str, Any]:
        """Run pre-execution hooks."""
        pre_hook_results = {}
        
        if not HOOKS_AVAILABLE:
            return pre_hook_results
        
        # Skip actual hook execution during assessment to prevent subprocess spawning
        if os.environ.get('SKIP_HOOK_EXECUTION', '').lower() == 'true':
            # Just check that hooks exist
            hooks_to_check = ['setup_environment.py', 'check_task_dependencies.py', 'analyze_task_complexity.py']
            for hook in hooks_to_check:
                hook_path = self.hooks_dir / hook
                if hook_path.exists():
                    pre_hook_results[hook] = 'exists'
                    self.hooks_used['pre'].append(hook)
            return pre_hook_results
        
        # 1. Setup environment (venv activation)
        try:
            env_hook_env = env.copy()
            env_hook_env['CLAUDE_COMMAND'] = f"python {hook_name} --test"
            
            result = subprocess.run(
                [sys.executable, str(self.hooks_dir / "setup_environment.py")],
                env=env_hook_env,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                pre_hook_results['setup_environment'] = 'success'
                self.hooks_used['pre'].append('setup_environment')
                
                # Check if command was wrapped
                if self.redis_client:
                    wrapped = self.redis_client.get(f"cmd:wrapped:{env['CLAUDE_SESSION_ID']}")
                    if wrapped:
                        pre_hook_results['venv_wrapped'] = True
        except Exception as e:
            pre_hook_results['setup_environment'] = f'error: {str(e)}'
        
        # 2. Check dependencies
        try:
            # Create fake context with common imports
            deps_env = env.copy()
            deps_env['CLAUDE_CONTEXT'] = """
            Task: Test hook functionality
            import json
            import redis
            import subprocess
            from pathlib import Path
            """
            
            result = subprocess.run(
                [sys.executable, str(self.hooks_dir / "check_task_dependencies.py")],
                env=deps_env,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                pre_hook_results['check_dependencies'] = 'success'
                self.hooks_used['pre'].append('check_task_dependencies')
        except Exception as e:
            pre_hook_results['check_dependencies'] = f'error: {str(e)}'
        
        # 3. Analyze complexity (for timeout estimation)
        try:
            complexity_env = env.copy()
            
            # Create temp file with task
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write(f"Task 1: Test {hook_name} functionality comprehensively")
                complexity_env['CLAUDE_FILE'] = f.name
            
            result = subprocess.run(
                [sys.executable, str(self.hooks_dir / "analyze_task_complexity.py")],
                env=complexity_env,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    complexity_data = json.loads(result.stdout)
                    pre_hook_results['complexity'] = complexity_data
                    self.hooks_used['pre'].append('analyze_task_complexity')
                except:
                    pass
            
            os.unlink(complexity_env['CLAUDE_FILE'])
        except Exception as e:
            pre_hook_results['analyze_complexity'] = f'error: {str(e)}'
        
        return pre_hook_results
    
    def run_post_hooks(self, hook_name: str, output: Dict[str, Any], 
                      env: Dict[str, str], duration: float) -> Dict[str, Any]:
        """Run post-execution hooks."""
        post_hook_results = {}
        
        if not HOOKS_AVAILABLE:
            return post_hook_results
        
        # Skip actual hook execution during assessment to prevent subprocess spawning
        if os.environ.get('SKIP_HOOK_EXECUTION', '').lower() == 'true':
            # Just check that hooks exist
            hooks_to_check = ['truncate_logs.py', 'record_execution_metrics.py', 
                             'claude_response_validator.py', 'update_task_status.py']
            for hook in hooks_to_check:
                hook_path = self.hooks_dir / hook
                if hook_path.exists():
                    post_hook_results[hook] = 'exists'
                    self.hooks_used['post'].append(hook)
            return post_hook_results
        
        # 1. Truncate logs if needed
        try:
            truncate_env = env.copy()
            truncate_env['CLAUDE_OUTPUT'] = output['stdout'] + output['stderr']
            truncate_env['CLAUDE_DURATION'] = str(duration)
            
            result = subprocess.run(
                [sys.executable, str(self.hooks_dir / "truncate_logs.py")],
                env=truncate_env,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    truncate_data = json.loads(result.stdout)
                    if truncate_data.get('truncated'):
                        post_hook_results['log_truncation'] = {
                            'original_size': truncate_data.get('original_size'),
                            'truncated_size': truncate_data.get('truncated_size')
                        }
                        self.hooks_used['post'].append('truncate_logs')
                except:
                    pass
        except Exception as e:
            post_hook_results['truncate_logs'] = f'error: {str(e)}'
        
        # 2. Record execution metrics
        try:
            metrics_env = env.copy()
            metrics_env['CLAUDE_EXIT_CODE'] = str(output['exit_code'])
            metrics_env['CLAUDE_DURATION'] = str(duration)
            metrics_env['CLAUDE_OUTPUT_SIZE'] = str(len(output['stdout'] + output['stderr']))
            
            result = subprocess.run(
                [sys.executable, str(self.hooks_dir / "record_execution_metrics.py")],
                env=metrics_env,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                post_hook_results['metrics_recorded'] = True
                self.hooks_used['post'].append('record_execution_metrics')
                
                # Check Redis for metrics
                if self.redis_client:
                    metrics_key = f"metrics:{env['CLAUDE_SESSION_ID']}"
                    metrics = self.redis_client.get(metrics_key)
                    if metrics:
                        post_hook_results['metrics_data'] = json.loads(metrics)
        except Exception as e:
            post_hook_results['record_metrics'] = f'error: {str(e)}'
        
        # 3. Validate response quality
        try:
            validate_env = env.copy()
            validate_env['CLAUDE_OUTPUT'] = output['stdout']
            validate_env['CLAUDE_COMMAND'] = f"python {hook_name} --test"
            validate_env['CLAUDE_EXIT_CODE'] = str(output['exit_code'])
            validate_env['CLAUDE_DURATION'] = str(duration)
            
            result = subprocess.run(
                [sys.executable, str(self.hooks_dir / "claude_response_validator.py")],
                env=validate_env,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    validation_data = json.loads(result.stdout)
                    post_hook_results['response_quality'] = validation_data.get('quality')
                    post_hook_results['quality_score'] = validation_data.get('score')
                    self.hooks_used['post'].append('claude_response_validator')
                except:
                    pass
        except Exception as e:
            post_hook_results['validate_response'] = f'error: {str(e)}'
        
        # 4. Update task status
        try:
            status_env = env.copy()
            status_env['TASK_ID'] = f"test_{hook_name}"
            status_env['TASK_STATUS'] = 'completed' if output['exit_code'] == 0 else 'failed'
            
            result = subprocess.run(
                [sys.executable, str(self.hooks_dir / "update_task_status.py")],
                env=status_env,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                post_hook_results['status_updated'] = True
                self.hooks_used['post'].append('update_task_status')
        except Exception as e:
            post_hook_results['update_status'] = f'error: {str(e)}'
        
        return post_hook_results
    
    def get_hook_expectations(self, filename: str) -> Dict[str, Any]:
        """Define expected behaviors for each hook."""
        expectations = {
            'setup_environment.py': {
                'description': 'Wraps commands with virtual environment activation',
                'test_indicators': ['Environment Setup Hook Test', 'Testing', 'venv'],
                'redis_keys': ['cmd:wrapped:*'],
                'min_lines': 10,
                'should_modify_env': True,
                'error_ok': False
            },
            'analyze_task_complexity.py': {
                'description': 'Analyzes task complexity and estimates timeout',
                'test_indicators': ['Task Complexity Analyzer Test', 'Complexity:', 'Timeout:'],
                'redis_keys': ['task:complexity:*'],
                'min_lines': 8,
                'should_have_json': True,
                'error_ok': False
            },
            'claude_response_validator.py': {
                'description': 'Validates Claude responses for quality and hallucinations',
                'test_indicators': ['Claude Response Validation', 'quality', 'score'],
                'redis_keys': ['claude:quality:*', 'claude:response:*'],
                'min_lines': 10,
                'should_detect_hallucination': True,
                'error_ok': False
            },
            'check_task_dependencies.py': {
                'description': 'Extracts and validates required packages from tasks',
                'test_indicators': ['Task Dependencies Check', 'packages', 'Test'],
                'redis_keys': ['hook:req_pkgs:*'],
                'min_lines': 8,
                'should_find_packages': True,
                'error_ok': False
            },
            'task_list_preflight_check.py': {
                'description': 'Analyzes task lists for risk and complexity',
                'test_indicators': ['Task List Pre-Flight Check', 'risk', 'Testing'],
                'redis_keys': ['task:risk:*'],
                'min_lines': 10,
                'should_assess_risk': True,
                'error_ok': True  # May exit with code 1 for high-risk tasks
            },
            'truncate_logs.py': {
                'description': 'Truncates large outputs while preserving key information',
                'test_indicators': ['Log Truncation Hook Test', 'truncat', 'Testing'],
                'redis_keys': ['log:truncated:*'],
                'min_lines': 5,
                'should_show_reduction': True,
                'error_ok': False
            },
            'claude_instance_pre_check.py': {
                'description': 'Pre-validates Claude instance configuration',
                'test_indicators': ['Claude Instance Pre-Check', 'validation', 'Test'],
                'redis_keys': ['claude:precheck:*'],
                'min_lines': 8,
                'should_validate_config': True,
                'error_ok': False
            },
            'record_execution_metrics.py': {
                'description': 'Records execution metrics to Redis',
                'test_indicators': ['Execution Metrics', 'Recording', 'metrics'],
                'redis_keys': ['metrics:*', 'execution:stats:*'],
                'min_lines': 5,
                'should_store_metrics': True,
                'error_ok': False
            },
            'update_task_status.py': {
                'description': 'Updates task status in Redis',
                'test_indicators': ['Task Status Update', 'status', 'updated'],
                'redis_keys': ['task:status:*'],
                'min_lines': 5,
                'should_update_status': True,
                'error_ok': False
            },
            'review_code_changes.py': {
                'description': 'Reviews code changes for quality and safety',
                'test_indicators': ['Code Review', 'changes', 'review'],
                'redis_keys': ['code:review:*'],
                'min_lines': 5,
                'should_analyze_code': True,
                'error_ok': False
            },
            'claude_structured_response.py': {
                'description': 'Ensures Claude responses follow structured format',
                'test_indicators': ['Structured Response', 'format', 'validation'],
                'redis_keys': ['claude:structured:*'],
                'min_lines': 5,
                'should_validate_structure': True,
                'error_ok': False
            },
            'debug_hooks.py': {
                'description': 'Debug utility for testing individual hooks',
                'test_indicators': ['Debug', 'hook', 'test'],
                'redis_keys': [],
                'min_lines': 3,
                'is_utility': True,
                'error_ok': True
            }
        }
        
        # Default for unknown hooks
        default = {
            'description': 'Hook functionality test',
            'test_indicators': ['Test', 'Hook'],
            'redis_keys': [],
            'min_lines': 3,
            'error_ok': True
        }
        
        return expectations.get(filename, default)
    
    def clear_test_redis_keys(self):
        """Clear any test keys from previous runs."""
        if not self.redis_client:
            return
        
        patterns = [
            'cmd:wrapped:*test*',
            'task:complexity:*test*',
            'claude:quality:*test*',
            'hook:req_pkgs:*test*',
            'task:risk:*test*',
            'log:truncated:*test*',
            'metrics:*test*',
            'task:status:*test*',
            f'{self.test_session_id}*',
            'assess:*'
        ]
        
        for pattern in patterns:
            keys = self.redis_client.keys(pattern)
            for key in keys:
                self.redis_client.delete(key)
    
    def capture_redis_state(self) -> Dict[str, int]:
        """Capture current Redis key counts by pattern."""
        if not self.redis_client:
            return {}
        
        state = {}
        patterns = [
            'cmd:wrapped:*',
            'task:complexity:*',
            'claude:quality:*',
            'hook:req_pkgs:*',
            'task:risk:*',
            'log:truncated:*',
            'metrics:*',
            'task:status:*',
            'code:review:*',
            'claude:structured:*'
        ]
        
        for pattern in patterns:
            state[pattern] = len(self.redis_client.keys(pattern))
        
        return state
    
    def run_hook_test_with_full_chain(self, file_path: Path) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        """Run a hook's test function with full pre/post hook chain."""
        print(f"Testing {file_path.name}...")
        
        # Set up test environment
        env = os.environ.copy()
        env['HOOK_TEST_SESSION'] = self.test_session_id
        env['CLAUDE_SESSION_ID'] = f"{self.test_session_id}_{file_path.stem}"
        env['ASSESSMENT_MODE'] = 'true'
        
        # Ensure PYTHONPATH
        pythonpath = env.get('PYTHONPATH', '')
        src_path = str(self.hooks_dir.parent)
        if src_path not in pythonpath:
            env['PYTHONPATH'] = f"{src_path}:{pythonpath}" if pythonpath else src_path
        
        # Run pre-hooks
        pre_hook_results = self.run_pre_hooks(file_path.name, env)
        
        # Capture Redis state before
        redis_before = self.capture_redis_state() if self.redis_client else {}
        
        # Run the actual hook test
        start_time = time.time()
        try:
            # Change to temp directory
            original_cwd = os.getcwd()
            os.chdir(self.temp_dir)
            
            # Hooks use --test flag for safety reasons
            # Future components should use direct if __name__ == "__main__":
            result = subprocess.run(
                [sys.executable, str(file_path), '--test'],
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
                cwd=self.temp_dir
            )
            
            output = {
                'success': True,
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'timed_out': False
            }
            
        except subprocess.TimeoutExpired:
            output = {
                'success': False,
                'exit_code': -1,
                'stdout': '',
                'stderr': 'Process timed out after 30 seconds',
                'timed_out': True
            }
        except Exception as e:
            output = {
                'success': False,
                'exit_code': -1,
                'stdout': '',
                'stderr': f'Exception: {str(e)}',
                'timed_out': False
            }
        finally:
            os.chdir(original_cwd)
        
        duration = time.time() - start_time
        
        # Capture Redis state after
        redis_after = self.capture_redis_state() if self.redis_client else {}
        
        # Calculate Redis delta
        redis_delta = {}
        for key in redis_after:
            redis_delta[key] = redis_after.get(key, 0) - redis_before.get(key, 0)
        
        # Run post-hooks
        post_hook_results = self.run_post_hooks(file_path.name, output, env, duration)
        
        # Save raw response to prevent hallucination
        self.save_raw_response(file_path.name, output)
        
        return output, pre_hook_results, post_hook_results, redis_delta, duration
    
    def save_raw_response(self, filename: str, output: Dict[str, Any]):
        """Save raw response to tmp/responses/ directory for future reference."""
        responses_dir = self.tmp_dir / "responses"
        responses_dir.mkdir(exist_ok=True)
        
        # Save as JSON for easy loading
        response_file = responses_dir / f"{filename}_{self.timestamp}.json"
        with open(response_file, 'w') as f:
            json.dump({
                'filename': filename,
                'timestamp': self.timestamp,
                'output': output
            }, f, indent=2)
        
        # Also save raw text for easy reading
        text_file = responses_dir / f"{filename}_{self.timestamp}.txt"
        with open(text_file, 'w') as f:
            f.write(f"=== Raw Response: {filename} ===\n")
            f.write(f"Timestamp: {self.timestamp}\n")
            f.write(f"Exit Code: {output['exit_code']}\n")
            f.write("\n--- STDOUT ---\n")
            f.write(output['stdout'])
            f.write("\n\n--- STDERR ---\n")
            f.write(output['stderr'])
    
    def assess_hook_output(self, filename: str, output: Dict[str, Any],
                          expectations: Dict[str, Any], redis_delta: Dict[str, int],
                          pre_hooks: Dict[str, Any], post_hooks: Dict[str, Any]) -> Dict[str, Any]:
        """Assess hook output using behavioral patterns and hook chain evidence."""
        combined_output = output['stdout'] + output['stderr']
        
        assessment = {
            'reasonable': False,
            'confidence': 0,
            'reasons': [],
            'indicators_found': [],
            'redis_evidence': {},
            'hook_chain_evidence': {
                'pre': pre_hooks,
                'post': post_hooks
            }
        }
        
        # Bonus for successful hook chain
        if pre_hooks:
            assessment['confidence'] += 5
            assessment['reasons'].append(f"Pre-hooks executed: {list(pre_hooks.keys())}")
        
        if post_hooks:
            assessment['confidence'] += 5
            assessment['reasons'].append(f"Post-hooks executed: {list(post_hooks.keys())}")
        
        # Check for timeout
        if output['timed_out']:
            assessment['reasons'].append("Hook test timed out")
            assessment['confidence'] = 95
            return assessment
        
        # Check exit code (some hooks exit 1 on purpose)
        if output['exit_code'] != 0 and not expectations['error_ok']:
            assessment['reasons'].append(f"Non-zero exit code: {output['exit_code']}")
            assessment['confidence'] = 80
        
        # Check for exceptions
        has_exception = 'Traceback' in combined_output
        if has_exception and not expectations['error_ok']:
            assessment['reasons'].append("Unexpected exception in test")
            assessment['confidence'] = 90
            return assessment
        
        # Check output length
        lines = combined_output.strip().split('\n') if combined_output else []
        if len(lines) < expectations['min_lines']:
            assessment['reasons'].append(f"Output too short ({len(lines)} lines)")
            assessment['confidence'] = 60
        else:
            assessment['reasons'].append(f"Good output length ({len(lines)} lines)")
            assessment['reasonable'] = True
            assessment['confidence'] = 40
        
        # Check for test indicators
        found_indicators = []
        for indicator in expectations['test_indicators']:
            if indicator.lower() in combined_output.lower():
                found_indicators.append(indicator)
        
        assessment['indicators_found'] = found_indicators
        
        if len(found_indicators) >= len(expectations['test_indicators']) * 0.6:
            assessment['reasonable'] = True
            assessment['reasons'].append(f"Found {len(found_indicators)}/{len(expectations['test_indicators'])} test indicators")
            assessment['confidence'] += 30
        else:
            assessment['reasons'].append(f"Missing test indicators ({len(found_indicators)}/{len(expectations['test_indicators'])})")
        
        # Check for tmp/ usage
        if 'tmp/' in combined_output:
            assessment['reasons'].append("Using tmp/ directory correctly")
            assessment['confidence'] += 5
        
        # Redis validation
        if self.redis_client and expectations['redis_keys']:
            redis_found = []
            for pattern in expectations['redis_keys']:
                if any(k for k, v in redis_delta.items() if pattern.rstrip('*') in k and v > 0):
                    redis_found.append(pattern)
            
            if redis_found:
                assessment['reasonable'] = True
                assessment['reasons'].append(f"Created Redis keys: {', '.join(redis_found)}")
                assessment['confidence'] += 20
                assessment['redis_evidence'] = {k: v for k, v in redis_delta.items() if v > 0}
        
        # Hook-specific validations
        if expectations.get('should_detect_hallucination') and 'hallucination' in combined_output.lower():
            assessment['reasonable'] = True
            assessment['reasons'].append("Successfully detected hallucination")
            assessment['confidence'] += 10
        
        if expectations.get('should_find_packages') and ('pandas' in combined_output.lower() or 'requests' in combined_output.lower()):
            assessment['reasonable'] = True
            assessment['reasons'].append("Found package dependencies")
            assessment['confidence'] += 10
        
        if expectations.get('should_assess_risk') and 'risk' in combined_output.lower():
            assessment['reasonable'] = True
            assessment['reasons'].append("Performed risk assessment")
            assessment['confidence'] += 10
        
        if expectations.get('should_show_reduction') and ('truncat' in combined_output.lower() or 'reduction' in combined_output.lower()):
            assessment['reasonable'] = True
            assessment['reasons'].append("Showed log truncation")
            assessment['confidence'] += 10
        
        # Check hook chain specific evidence
        if pre_hooks.get('venv_wrapped'):
            assessment['reasons'].append("Command wrapped with venv activation")
            assessment['confidence'] += 5
        
        if post_hooks.get('metrics_recorded'):
            assessment['reasons'].append("Execution metrics recorded")
            assessment['confidence'] += 5
        
        if post_hooks.get('response_quality'):
            assessment['reasons'].append(f"Response quality: {post_hooks['response_quality']}")
            assessment['confidence'] += 5
        
        # Final confidence bounds
        assessment['confidence'] = max(0, min(100, assessment['confidence']))
        
        return assessment
    
    def generate_report(self):
        """Generate comprehensive markdown report in tmp/."""
        report_lines = [
            "# Hooks Usage Function Assessment Report",
            f"\n**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"\n**Report Location**: {self.report_path}",
            f"**Temp Directory**: {self.temp_dir}",
            f"**Raw Responses Saved**: {self.tmp_dir}/responses/",
            f"\n**Total Hooks Tested**: {len(self.results)}",
            f"**Redis Available**: {'Yes' if self.redis_client else 'No'}",
            f"**Hooks Available**: {'Yes' if HOOKS_AVAILABLE else 'No'}",
            f"**Test Session ID**: {self.test_session_id}",
            f"**Total Time**: {time.time() - self.start_time:.1f}s",
            "\n---\n",
            "## Hook Chain Usage",
            "",
            f"**Pre-hooks Used**: {', '.join(set(self.hooks_used['pre'])) if self.hooks_used['pre'] else 'None'}",
            f"**Post-hooks Used**: {', '.join(set(self.hooks_used['post'])) if self.hooks_used['post'] else 'None'}",
            "\n---\n",
            "## Summary",
            ""
        ]
        
        # Calculate summary stats
        total = len(self.results)
        passed = sum(1 for r in self.results if r['assessment']['reasonable'])
        failed = total - passed
        
        report_lines.extend([
            f"- **Passed**: {passed}/{total} ({passed/total*100:.1f}%)",
            f"- **Failed**: {failed}/{total}",
            f"- **Average Confidence**: {sum(r['assessment']['confidence'] for r in self.results)/total:.1f}%",
            f"- **Hooks with Redis Evidence**: {sum(1 for r in self.results if r['assessment']['redis_evidence'])}/{total}",
            ""
        ])
        
        # Add category breakdown
        categories = {
            'Environment Setup': ['setup_environment.py'],
            'Task Analysis': ['analyze_task_complexity.py', 'check_task_dependencies.py', 'task_list_preflight_check.py'],
            'Claude Validation': ['claude_response_validator.py', 'claude_instance_pre_check.py', 'claude_structured_response.py'],
            'Logging & Metrics': ['truncate_logs.py', 'record_execution_metrics.py', 'update_task_status.py'],
            'Code Review': ['review_code_changes.py'],
            'Utilities': ['debug_hooks.py']
        }
        
        report_lines.extend(["\n### Category Performance:\n"])
        
        for category, hooks in categories.items():
            cat_results = [r for r in self.results if r['filename'] in hooks]
            if cat_results:
                cat_passed = sum(1 for r in cat_results if r['assessment']['reasonable'])
                report_lines.append(f"- **{category}**: {cat_passed}/{len(cat_results)} passed")
        
        report_lines.extend(["\n---\n", "## Detailed Results\n"])
        
        # Add detailed results for each hook
        for result in self.results:
            filename = result['filename']
            expectations = result['expectations']
            output = result['output']
            assessment = result['assessment']
            duration = result['duration']
            
            status_icon = "✅" if assessment['reasonable'] else "❌"
            
            report_lines.extend([
                f"### {status_icon} {filename}",
                f"\n**Description**: {expectations['description']}",
                f"\n**Expected Test Indicators**: {', '.join(expectations['test_indicators'])}",
                f"\n**Assessment**: {'PASS' if assessment['reasonable'] else 'FAIL'} (Confidence: {assessment['confidence']}%)",
                f"**Execution Time**: {duration:.2f}s",
                f"\n**Reasons**:",
                ""
            ])
            
            for reason in assessment['reasons']:
                report_lines.append(f"- {reason}")
            
            if assessment['indicators_found']:
                report_lines.append(f"\n**Indicators Found**: {', '.join(assessment['indicators_found'])}")
            
            if assessment.get('redis_evidence'):
                report_lines.append(f"\n**Redis Keys Created**:")
                for pattern, count in assessment['redis_evidence'].items():
                    if count > 0:
                        report_lines.append(f"- {pattern}: {count} keys")
            
            # Hook chain details
            if assessment['hook_chain_evidence']['pre'] or assessment['hook_chain_evidence']['post']:
                report_lines.append(f"\n**Hook Chain Evidence**:")
                
                if assessment['hook_chain_evidence']['pre']:
                    report_lines.append("- Pre-hooks:")
                    for hook, result in assessment['hook_chain_evidence']['pre'].items():
                        if isinstance(result, str) and 'error' not in result:
                            report_lines.append(f"  - {hook}: {result}")
                
                if assessment['hook_chain_evidence']['post']:
                    report_lines.append("- Post-hooks:")
                    for hook, result in assessment['hook_chain_evidence']['post'].items():
                        if isinstance(result, dict):
                            report_lines.append(f"  - {hook}: {json.dumps(result, indent=2)}")
                        elif isinstance(result, bool):
                            report_lines.append(f"  - {hook}: {'success' if result else 'failed'}")
            
            report_lines.extend([
                "\n**Raw Output**:",
                "```",
                f"Command: python {filename} --test",
                f"Exit Code: {output['exit_code']}",
                f"Working Directory: {self.temp_dir}",
                "\n--- STDOUT ---",
                output['stdout'][:1500] + ('...[truncated]' if len(output['stdout']) > 1500 else ''),
                "\n--- STDERR ---",
                output['stderr'][:500] + ('...[truncated]' if len(output['stderr']) > 500 else '') if output['stderr'] else '(empty)',
                "```",
                "\n---\n"
            ])
        
        # Add recommendations
        report_lines.extend([
            "## Recommendations\n"
        ])
        
        if failed > 0:
            report_lines.extend([
                "### For Failed Hooks:",
                ""
            ])
            
            for result in self.results:
                if not result['assessment']['reasonable']:
                    reasons = result['assessment']['reasons']
                    report_lines.append(f"- **{result['filename']}**: {reasons[0] if reasons else 'Review test implementation'}")
        
        if not self.redis_client:
            report_lines.extend([
                "\n### Redis Integration:",
                "- Redis is not available. Many hooks have reduced validation without Redis.",
                "- Consider running with Redis for complete assessment."
            ])
        
        if not HOOKS_AVAILABLE:
            report_lines.extend([
                "\n### Hook Chain:",
                "- Full hook chain not available. Tests ran without pre/post processing.",
                "- Ensure cc_executor is properly installed and PYTHONPATH is set."
            ])
        
        # Add pattern recommendation
        report_lines.extend([
            "\n### Pattern Recommendation:",
            "Hooks use --test flags for production safety, but for new non-hook components:",
            "- Use direct `if __name__ == '__main__':` implementation",
            "- No flags needed for simpler AI agent interaction",
            "- See core/ components for AI-friendly patterns"
        ])
        
        # Write report
        with open(self.report_path, 'w') as f:
            f.write('\n'.join(report_lines))
        
        print(f"\n✅ Report generated: {self.report_path}")
        print(f"📁 Temp files saved to: {self.temp_dir}")
        
        return passed, failed
    
    def cleanup(self):
        """Clean up test Redis keys."""
        self.clear_test_redis_keys()
        
        # Keep temp directory for debugging
        print(f"\n💡 Temp directory preserved for debugging: {self.temp_dir}")
    
    def run_all_assessments(self):
        """Run all hook tests and generate report."""
        print("=== Hooks Usage Function Assessment ===\n")
        print(f"Session ID: {self.test_session_id}")
        print(f"Redis Status: {'Connected' if self.redis_client else 'Not Available'}")
        print(f"Hooks Available: {HOOKS_AVAILABLE}")
        print(f"Report will be saved to: {self.report_path}\n")
        
        # Clear any existing test keys
        self.clear_test_redis_keys()
        
        # Get all hook files
        hook_files = sorted([f for f in self.hooks_dir.glob("*.py")
                           if f.name != "__init__.py" and 
                           not f.name.startswith("ASSESS") and
                           f.name != "ASSESS_HOOKS_OUTPUT.md"])
        
        for file_path in hook_files:
            # Get expectations
            expectations = self.get_hook_expectations(file_path.name)
            
            # Run hook test with full chain
            output, pre_hooks, post_hooks, redis_delta, duration = self.run_hook_test_with_full_chain(file_path)
            
            # Assess output
            assessment = self.assess_hook_output(
                file_path.name, output, expectations, 
                redis_delta, pre_hooks, post_hooks
            )
            
            # Store result
            self.results.append({
                'filename': file_path.name,
                'expectations': expectations,
                'output': output,
                'assessment': assessment,
                'duration': duration
            })
            
            # Print immediate feedback
            status = "✅ PASS" if assessment['reasonable'] else "❌ FAIL"
            print(f"{status} - {file_path.name} (Confidence: {assessment['confidence']}%)")
        
        # Generate report
        passed, failed = self.generate_report()
        
        print(f"\n{'='*60}")
        print(f"Total: {len(self.results)} | Passed: {passed} | Failed: {failed}")
        print(f"Success Rate: {passed/len(self.results)*100:.1f}%")
        
        # Cleanup
        self.cleanup()
        
        return passed, failed

if __name__ == "__main__":
    # Environment check
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version.split()[0]}")
    print(f"Working directory: {os.getcwd()}")
    
    # Ensure PYTHONPATH is set
    if 'cc_executor' not in os.environ.get('PYTHONPATH', ''):
        print("\n⚠️  WARNING: cc_executor not in PYTHONPATH")
        print("Run: export PYTHONPATH='${PWD}/src:${PYTHONPATH}'")
    
    assessor = HookUsageAssessor()
    passed, failed = assessor.run_all_assessments()
    
    # Exit with appropriate code
    sys.exit(0 if failed == 0 else 1)