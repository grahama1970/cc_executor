#!/usr/bin/env python3
"""Redis-based task timing and complexity estimation"""

import asyncio
import json
import time
import statistics
import subprocess
import hashlib
import re
import os
import psutil
import sys
from typing import Dict, List, Optional, Tuple

from cc_executor.utils.enhanced_prompt_classifier import EnhancedPromptClassifier

class RedisTaskTimer:
    def __init__(self, redis_prefix="cc_executor:times"):
        self.redis_prefix = redis_prefix
        self.load_multiplier_threshold = 14.0  # CPU load threshold for 3x timeout
        self.enhanced_classifier = EnhancedPromptClassifier()  # Use enhanced classifier
        
    async def execute_redis(self, command: str) -> str:
        """Execute redis-cli command and return output"""
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise Exception(f"Redis error: {stderr.decode()}")
        return stdout.decode().strip()
    
    def classify_command(self, command: str) -> Dict[str, str]:
        """Classify command using enhanced classifier and metatags"""
        # Check for inline metatags first
        metatag_pattern = r'\[(\w+):(\w+)\]'
        tags = dict(re.findall(metatag_pattern, command))
        
        if tags:
            # Use provided tags
            return {
                "category": tags.get("category", "unknown"),
                "name": tags.get("task", "unknown"),
                "complexity": tags.get("complexity", "medium"),
                "question_type": tags.get("type", "general")
            }
        
        # Use enhanced classifier for better categorization
        enhanced_result = self.enhanced_classifier.classify(command)
        
        # Start with enhanced classifier results
        result = {
            "category": enhanced_result["category"],
            "name": enhanced_result["sub_type"],
            "complexity": enhanced_result["complexity"],
            "question_type": enhanced_result["category"]
        }
        
        # Special case overrides for specific tools
        # Redis operations
        if 'redis-cli' in command:
            result["category"] = "redis"
            if any(op in command.upper() for op in ['GET', 'SET', 'HGET', 'HSET']):
                result.update({"name": "simple_op", "complexity": "simple", "question_type": "lookup"})
            elif any(op in command.upper() for op in ['SCAN', 'KEYS', 'ZRANGE']):
                result.update({"name": "scan_op", "complexity": "medium", "question_type": "search"})
            elif 'FT.SEARCH' in command.upper():
                result.update({"name": "bm25_search", "complexity": "complex", "question_type": "search"})
        
        # Claude operations - only override if explicitly using claude command
        elif 'claude' in command and ('--print' in command or '-p' in command):
            result["category"] = "claude"
            
            # Haiku generation
            if 'haiku' in command.lower():
                # Try numeric match first - allow words between number and haiku
                match = re.search(r'(\d+)\s*\w*\s*haiku', command.lower())
                if match:
                    count = int(match.group(1))
                else:
                    # Word to number mapping
                    word_numbers = {
                        'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
                        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
                        'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14,
                        'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18,
                        'nineteen': 19, 'twenty': 20, 'thirty': 30, 'forty': 40,
                        'fifty': 50, 'hundred': 100
                    }
                    # Search for word numbers
                    count = 1  # default
                    for word, num in word_numbers.items():
                        if word in command.lower():
                            count = num
                            break
                            
                result["name"] = f"haiku_{count}"
                result["question_type"] = "creative_writing"
                # Complexity based on count
                if count <= 5:
                    result["complexity"] = "simple"
                elif count <= 20:
                    result["complexity"] = "medium"
                else:
                    result["complexity"] = "complex"
            
            # Code operations
            elif 'refactor' in command.lower():
                result.update({"name": "refactor", "complexity": "complex", "question_type": "code_refactor"})
            elif 'analyze' in command.lower():
                result.update({"name": "analyze", "complexity": "medium", "question_type": "code_analysis"})
            elif 'debug' in command.lower():
                result.update({"name": "debug", "complexity": "complex", "question_type": "debugging"})
            elif 'explain' in command.lower():
                result.update({"name": "explain", "complexity": "medium", "question_type": "explanation"})
            elif 'test' in command.lower() or 'unittest' in command.lower():
                result.update({"name": "testing", "complexity": "medium", "question_type": "testing"})
            elif 'implement' in command.lower() or 'create' in command.lower():
                result.update({"name": "implement", "complexity": "complex", "question_type": "implementation"})
            
            # Long content generation detection
            elif any(x in command.lower() for x in ['5000 word', '10000 word', '10,000 word', 'comprehensive guide', 'epic story']):
                result.update({"name": "long_content", "complexity": "complex", "question_type": "content_generation"})
            elif '100 different' in command.lower() or 'ultimate stress' in command.lower():
                result.update({"name": "extreme_generation", "complexity": "complex", "question_type": "code_generation"})
            elif 'research' in command.lower() and 'topics' in command.lower():
                result.update({"name": "research_multi", "complexity": "complex", "question_type": "research"})
            elif 'improve it 10 times' in command.lower():
                result.update({"name": "iterative_improvement", "complexity": "complex", "question_type": "code_generation"})
            
            else:
                # Keep enhanced classifier results for generic tasks
                pass
        
        # System commands - only override if command starts with these
        elif command.strip().split()[0] in ['ls', 'pwd', 'echo', 'cat'] if command.strip() else False:
            result.update({
                "category": "system", 
                "name": "simple_cmd", 
                "complexity": "simple",
                "question_type": "filesystem"
            })
        elif command.strip().split()[0] in ['grep', 'find', 'awk', 'sed'] if command.strip() else False:
            result.update({
                "category": "system",
                "name": "search_cmd",
                "complexity": "medium", 
                "question_type": "search"
            })
        
        # Python/testing operations - only override if running python scripts
        elif command.strip().startswith('python') and ('test' in command or 'pytest' in command):
            result.update({
                "category": "testing",
                "name": "pytest",
                "complexity": "medium",
                "question_type": "testing"
            })
        
        # If still unknown, try to infer from keywords
        if result["name"] == "unknown":
            cmd_hash = hashlib.md5(command.encode()).hexdigest()[:8]
            result["name"] = cmd_hash
        
        return result
    
    async def _get_ratio_async(self, ratio_key: str, default_ratio: float) -> float:
        """Async helper to get ratio from Redis"""
        try:
            ratio_data = await self.execute_redis(f"redis-cli GET {ratio_key}")
            if ratio_data and ratio_data != "(nil)":
                return float(ratio_data)
        except Exception:
            pass
        return default_ratio
    
    def _calculate_stall_timeout(self, avg_time: float, task_type: Dict) -> int:
        """Calculate stall timeout based on historical data and task characteristics"""
        # Use environment variable for ratio if set
        default_ratio = float(os.environ.get('STALL_TIMEOUT_RATIO', '0.5'))
        
        # Get ratio from Redis if available
        ratio_key = f"{self.redis_prefix}:stall_ratios:{task_type['question_type']}:{task_type['complexity']}"
        
        # Check if we're in an async context
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context but can't await in sync method
            # Use default ratio to avoid nested event loop
            ratio = default_ratio
        except RuntimeError:
            # No event loop running, safe to create one
            try:
                ratio = asyncio.run(self._get_ratio_async(ratio_key, default_ratio))
            except Exception:
                ratio = default_ratio
            
        # Calculate based on ratio
        stall_timeout = int(avg_time * ratio)
        
        # Use environment variables for bounds
        min_stall = int(os.environ.get('MIN_STALL_TIMEOUT', '30'))
        max_stall = int(os.environ.get('MAX_STALL_TIMEOUT', '600'))
        
        # Apply bounds
        stall_timeout = max(min_stall, min(max_stall, stall_timeout))
            
        return stall_timeout
    
    async def get_task_history(self, category: str, task: str, complexity: str = None, question_type: str = None) -> Dict:
        """Get historical execution times from Redis, optionally filtered by complexity and type"""
        # Base keys
        history_key = f"{self.redis_prefix}:{category}:{task}:history"
        stats_key = f"{self.redis_prefix}:{category}:{task}:stats"
        
        # If complexity/type specified, use more specific keys
        if complexity and question_type:
            history_key = f"{self.redis_prefix}:{category}:{task}:{complexity}:{question_type}:history"
            stats_key = f"{self.redis_prefix}:{category}:{task}:{complexity}:{question_type}:stats"
        
        # Get recent executions
        history_data = await self.execute_redis(
            f"redis-cli zrange {history_key} -10 -1"
        )
        
        times = []
        if history_data:
            for line in history_data.split('\n'):
                if line.strip():
                    try:
                        entry = json.loads(line)
                        if entry.get('success'):
                            times.append(entry['actual'])
                    except json.JSONDecodeError:
                        continue
        
        # Get stats
        stats_data = await self.execute_redis(f"redis-cli hgetall {stats_key}")
        stats = {}
        if stats_data:
            lines = stats_data.split('\n')
            for i in range(0, len(lines), 2):
                if i + 1 < len(lines):
                    stats[lines[i]] = int(lines[i + 1])
        
        success_rate = 0
        if stats.get('total_runs', 0) > 0:
            success_rate = stats.get('successes', 0) / stats['total_runs']
        
        # Calculate percentile-based average to avoid outlier influence
        avg_time = None
        if times:
            try:
                if len(times) >= 5:
                    # Use 90th percentile for better outlier resistance
                    sorted_times = sorted(times)
                    p90_index = int(len(sorted_times) * 0.9)
                    avg_time = sorted_times[p90_index]
                else:
                    # Fall back to mean for small samples
                    avg_time = statistics.mean(times)
            except statistics.StatisticsError:
                avg_time = times[0] if times else None
        
        return {
            "times": times,
            "avg_time": avg_time,
            "max_time": max(times) if times else None,
            "min_time": min(times) if times else None,
            "success_rate": success_rate,
            "sample_size": len(times)
        }
    
    async def find_similar_tasks(self, complexity: str, question_type: str, limit: int = 10) -> List[Dict]:
        """Find similar tasks by complexity and question type using Redis pattern matching"""
        # Search for all keys matching the pattern
        pattern = f"{self.redis_prefix}:*:*:{complexity}:{question_type}:history"
        
        # Use SCAN to find matching keys (more efficient than KEYS)
        keys_data = await self.execute_redis(f"redis-cli --scan --pattern '{pattern}'")
        
        similar_tasks = []
        if keys_data:
            keys = keys_data.strip().split('\n')
            for key in keys[:limit]:  # Limit results
                if key:
                    # Extract category and task from key
                    parts = key.split(':')
                    if len(parts) >= 6:
                        category = parts[2]
                        task = parts[3]
                        
                        # Get the history for this task
                        history = await self.get_task_history(category, task, complexity, question_type)
                        if history['avg_time']:
                            similar_tasks.append({
                                "category": category,
                                "task": task,
                                "complexity": complexity,
                                "question_type": question_type,
                                "avg_time": history['avg_time'],
                                "success_rate": history['success_rate'],
                                "sample_size": history['sample_size']
                            })
        
        # Sort by sample size (more data = more reliable)
        similar_tasks.sort(key=lambda x: x['sample_size'], reverse=True)
        return similar_tasks
    
    async def get_average_execution_time(self, prompt: str, limit: int = 10) -> Optional[float]:
        """Get average execution time from Redis for similar prompts"""
        # Classify the prompt
        task_type = self.classify_command(prompt)
        
        # First try exact match
        history = await self.get_task_history(
            task_type['category'],
            task_type['name'],
            task_type['complexity'],
            task_type['question_type']
        )
        
        if history['sample_size'] >= 3 and history['avg_time']:
            return history['avg_time']
        
        # Try to find similar tasks
        similar_tasks = await self.find_similar_tasks(
            task_type['complexity'],
            task_type['question_type'],
            limit=limit
        )
        
        if similar_tasks:
            # Calculate weighted average based on sample size
            total_weight = sum(task['sample_size'] for task in similar_tasks)
            if total_weight > 0:
                weighted_avg = sum(
                    task['avg_time'] * task['sample_size'] 
                    for task in similar_tasks
                ) / total_weight
                return weighted_avg
        
        return None
    
    async def search_similar_prompts(self, prompt: str, search_criteria: Dict[str, any] = None) -> List[Dict]:
        """Search for similar prompts by token count, complexity, and keywords"""
        # Classify the prompt
        task_type = self.classify_command(prompt)
        
        # Default search criteria
        if search_criteria is None:
            search_criteria = {}
        
        # Extract search parameters
        complexity = search_criteria.get('complexity', task_type['complexity'])
        category = search_criteria.get('category', task_type['category'])
        max_token_diff = search_criteria.get('max_token_diff', 50)
        keywords = search_criteria.get('keywords', [])
        
        # Estimate token count (rough approximation)
        prompt_tokens = len(prompt.split()) * 1.3  # Rough token estimate
        
        # Search pattern for similar complexity and category
        pattern = f"{self.redis_prefix}:{category}:*:{complexity}:*:history"
        
        # Use SCAN to find matching keys
        keys_data = await self.execute_redis(f"redis-cli --scan --pattern '{pattern}'")
        
        similar_prompts = []
        if keys_data:
            keys = keys_data.strip().split('\n')
            for key in keys[:20]:  # Limit to 20 keys for performance
                if key:
                    # Extract task info from key
                    parts = key.split(':')
                    if len(parts) >= 6:
                        task_category = parts[2]
                        task_name = parts[3]
                        task_complexity = parts[4]
                        task_type = parts[5]
                        
                        # Get recent executions for this task
                        history_data = await self.execute_redis(
                            f"redis-cli zrange {key} -5 -1"
                        )
                        
                        if history_data:
                            for line in history_data.split('\n'):
                                if line.strip():
                                    try:
                                        entry = json.loads(line)
                                        
                                        # Check if this entry matches our criteria
                                        if 'prompt' in entry:  # If we stored the prompt
                                            entry_tokens = len(entry['prompt'].split()) * 1.3
                                            token_diff = abs(entry_tokens - prompt_tokens)
                                            
                                            # Check token difference
                                            if token_diff <= max_token_diff:
                                                # Check keywords if provided
                                                if keywords:
                                                    if not any(kw.lower() in entry['prompt'].lower() for kw in keywords):
                                                        continue
                                                
                                                similar_prompts.append({
                                                    "category": task_category,
                                                    "task": task_name,
                                                    "complexity": task_complexity,
                                                    "question_type": task_type,
                                                    "execution_time": entry['actual'],
                                                    "success": entry.get('success', True),
                                                    "token_diff": token_diff,
                                                    "timestamp": entry['timestamp']
                                                })
                                    except json.JSONDecodeError:
                                        continue
        
        # Sort by token difference (most similar first)
        similar_prompts.sort(key=lambda x: x['token_diff'])
        
        return similar_prompts
    
    def get_system_load(self) -> Dict[str, float]:
        """Get current system load metrics"""
        try:
            # Get CPU load average (1 minute)
            load_avg = os.getloadavg()[0]  # 1-minute load average
            
            # Get GPU memory if nvidia-smi is available
            gpu_memory_gb = 0.0
            try:
                result = subprocess.run(
                    ['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'],
                    capture_output=True, text=True, timeout=2
                )
                if result.returncode == 0:
                    gpu_memory_mb = float(result.stdout.strip().split('\n')[0])
                    gpu_memory_gb = gpu_memory_mb / 1024.0
            except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
                pass
            
            return {
                "cpu_load": load_avg,
                "gpu_memory_gb": gpu_memory_gb
            }
        except Exception as e:
            print(f"[Redis] Warning: Could not get system load: {e}")
            return {"cpu_load": 0.0, "gpu_memory_gb": 0.0}
    
    async def estimate_complexity(self, command: str) -> Dict:
        """Estimate task complexity based on history or patterns"""
        task_type = self.classify_command(command)
        
        # Check if this is an unknown prompt type
        is_unknown = (task_type['category'] == 'unknown' or 
                     task_type['name'] == 'unknown' or 
                     task_type['category'] == 'general')
        
        # Get system load for timeout adjustment
        system_load = self.get_system_load()
        load_multiplier = 1.0
        if system_load['cpu_load'] > self.load_multiplier_threshold:
            load_multiplier = 3.0
            print(f"⚠️ High system load detected: {system_load['cpu_load']:.1f} (applying 3x timeout multiplier)")
        
        try:
            # First try exact match with complexity and type
            history = await self.get_task_history(
                task_type['category'], 
                task_type['name'],
                task_type['complexity'],
                task_type['question_type']
            )
        except Exception as e:
            print(f"[Redis] Warning: Could not fetch history: {e}")
            history = {'sample_size': 0}
        
        # If we have good history, use it
        if history['sample_size'] >= 3:
            return {
                "category": task_type['category'],
                "task": task_type['name'],
                "complexity": task_type['complexity'],
                "question_type": task_type['question_type'],
                "expected_time": history['avg_time'] * 1.2 * load_multiplier,  # 20% buffer + load adjustment
                "max_time": history['max_time'] * 2 * load_multiplier,         # 2x worst case + load adjustment
                "stall_timeout": self._calculate_stall_timeout(history['avg_time'], task_type),
                "confidence": min(history['sample_size'] / 10, 1.0),
                "based_on": "exact_history",
                "system_load": system_load,
                "load_multiplier": load_multiplier
            }
        
        # Try to find similar tasks
        try:
            similar = await self.find_similar_tasks(task_type['complexity'], task_type['question_type'])
        except Exception as e:
            print(f"[Redis] Warning: Could not find similar tasks: {e}")
            similar = []
            
        if similar and len(similar) >= 2:
            # Average the top similar tasks
            avg_time = statistics.mean([t['avg_time'] for t in similar[:3]])
            max_time = max([t['avg_time'] for t in similar[:3]]) * 1.5
            
            return {
                "category": task_type['category'],
                "task": task_type['name'], 
                "complexity": task_type['complexity'],
                "question_type": task_type['question_type'],
                "expected_time": avg_time * 1.3 * load_multiplier,  # 30% buffer + load adjustment
                "max_time": max_time * 2 * load_multiplier,
                "stall_timeout": self._calculate_stall_timeout(avg_time, task_type),
                "confidence": 0.7,
                "based_on": "similar_tasks",
                "similar_tasks_used": len(similar),
                "system_load": system_load,
                "load_multiplier": load_multiplier
            }
        
        # Try similarity search for unknown prompts
        if is_unknown:
            try:
                similar_prompts = await self.search_similar_prompts(command, {
                    'max_token_diff': 100,
                    'complexity': task_type['complexity']
                })
                
                if similar_prompts and len(similar_prompts) >= 2:
                    # Use average of similar prompts
                    avg_time = statistics.mean([p['execution_time'] for p in similar_prompts[:5]])
                    max_time = max([p['execution_time'] for p in similar_prompts[:5]]) * 1.5
                    
                    # Ensure minimum 600s (10 minutes) for unknown prompts
                    avg_time = max(avg_time, 600.0)
                    max_time = max(max_time, 600.0)
                    
                    return {
                        "category": task_type['category'],
                        "task": task_type['name'],
                        "complexity": task_type['complexity'],
                        "question_type": task_type['question_type'],
                        "expected_time": avg_time * 1.2 * load_multiplier,
                        "max_time": max_time * 2 * load_multiplier,
                        "stall_timeout": self._calculate_stall_timeout(avg_time, task_type),
                        "confidence": 0.6,
                        "based_on": "similarity_search",
                        "similar_prompts_found": len(similar_prompts),
                        "system_load": system_load,
                        "load_multiplier": load_multiplier,
                        "unknown_prompt_acknowledged": True
                    }
            except Exception as e:
                print(f"[Redis] Warning: Similarity search failed: {e}")
        
        # Fall back to heuristics from environment or defaults
        heuristic_key = f"{task_type['category']}:{task_type['name']}"
        heuristic_env = os.environ.get(f"HEURISTIC_{heuristic_key.upper().replace(':', '_').replace('-', '_')}")
        
        if heuristic_env:
            # Parse from environment: "expected:max" format
            try:
                expected, max_time = map(float, heuristic_env.split(':'))
                
                # Ensure minimum 600s (10 minutes) for unknown prompts
                if is_unknown:
                    expected = max(expected, 600.0)
                    max_time = max(max_time, 600.0)
                
                return {
                    "category": task_type['category'],
                    "task": task_type['name'],
                    "complexity": task_type['complexity'],
                    "question_type": task_type['question_type'],
                    "expected_time": expected * load_multiplier,
                    "max_time": max_time * load_multiplier,
                    "stall_timeout": self._calculate_stall_timeout(expected, task_type),
                    "confidence": 0.5,
                    "based_on": "environment_heuristic",
                    "system_load": system_load,
                    "load_multiplier": load_multiplier,
                    "unknown_prompt_acknowledged": is_unknown
                }
            except:
                pass
        
        # Unknown task - conservative defaults based on complexity
        # Get defaults from environment or use built-in values
        # IMPORTANT: Apply 3x baseline multiplier for Claude CLI long-running processes
        baseline_multiplier = 3.0  # Claude CLI needs longer timeouts
        
        # For unknown prompts, ensure minimum 10 minute (600s) timeout
        if is_unknown:
            print(f"⚠️ Unknown prompt type detected. Using minimum 10 minute (600s) timeout with acknowledgment.")
            print(f"  Category: {task_type['category']}, Task: {task_type['name']}")
        
        default_times = {
            "trivial": {
                "expected": float(os.environ.get('DEFAULT_TRIVIAL_EXPECTED', '5')) * baseline_multiplier,
                "max": float(os.environ.get('DEFAULT_TRIVIAL_MAX', '15')) * baseline_multiplier
            },
            "low": {
                "expected": float(os.environ.get('DEFAULT_LOW_EXPECTED', '20')) * baseline_multiplier,
                "max": float(os.environ.get('DEFAULT_LOW_MAX', '60')) * baseline_multiplier
            },
            "simple": {
                "expected": float(os.environ.get('DEFAULT_SIMPLE_EXPECTED', '10')) * baseline_multiplier,
                "max": float(os.environ.get('DEFAULT_SIMPLE_MAX', '30')) * baseline_multiplier
            },
            "medium": {
                "expected": float(os.environ.get('DEFAULT_MEDIUM_EXPECTED', '60')) * baseline_multiplier,
                "max": float(os.environ.get('DEFAULT_MEDIUM_MAX', '180')) * baseline_multiplier
            },
            "high": {
                "expected": float(os.environ.get('DEFAULT_HIGH_EXPECTED', '120')) * baseline_multiplier,
                "max": float(os.environ.get('DEFAULT_HIGH_MAX', '360')) * baseline_multiplier
            },
            "complex": {
                "expected": float(os.environ.get('DEFAULT_COMPLEX_EXPECTED', '180')) * baseline_multiplier,
                "max": float(os.environ.get('DEFAULT_COMPLEX_MAX', '600')) * baseline_multiplier
            },
            "extreme": {
                "expected": float(os.environ.get('DEFAULT_EXTREME_EXPECTED', '300')) * baseline_multiplier,
                "max": float(os.environ.get('DEFAULT_EXTREME_MAX', '900')) * baseline_multiplier
            }
        }
        
        times = default_times.get(task_type['complexity'], default_times['medium'])
        
        # Ensure minimum 600s (10 minutes) for unknown prompts
        if is_unknown:
            times['expected'] = max(times['expected'], 600.0)
            times['max'] = max(times['max'], 600.0)
        
        result = {
            "category": task_type['category'],
            "task": task_type['name'],
            "complexity": task_type['complexity'],
            "question_type": task_type['question_type'],
            "expected_time": times['expected'] * load_multiplier,
            "max_time": times['max'] * load_multiplier,
            "stall_timeout": self._calculate_stall_timeout(times['expected'], task_type),
            "confidence": 0.1,
            "based_on": "default_with_3x_baseline",
            "baseline_multiplier": baseline_multiplier,
            "system_load": system_load,
            "load_multiplier": load_multiplier,
            "unknown_prompt_acknowledged": is_unknown
        }
        
        return result
    
    async def update_history(self, task_type: Dict, elapsed: float, 
                           success: bool, expected: float) -> None:
        """Update Redis with execution results"""
        timestamp = int(time.time())
        
        # Get system load at completion
        system_load = self.get_system_load()
        
        # Prepare record with all metadata including load info
        record = {
            "timestamp": timestamp,
            "expected": expected,
            "actual": elapsed,
            "success": success,
            "variance": (elapsed - expected) / expected if expected > 0 else 0,
            "complexity": task_type.get('complexity', 'medium'),
            "question_type": task_type.get('question_type', 'general'),
            "cpu_load": system_load['cpu_load'],
            "gpu_memory_gb": system_load['gpu_memory_gb']
        }
        
        # Update both general and specific history
        # General history (backward compatible)
        history_key = f"{self.redis_prefix}:{task_type['category']}:{task_type['name']}:history"
        await self.execute_redis(
            f"redis-cli zadd {history_key} {timestamp} '{json.dumps(record)}'"
        )
        
        # Specific history with complexity and type
        specific_key = f"{self.redis_prefix}:{task_type['category']}:{task_type['name']}:{task_type.get('complexity', 'medium')}:{task_type.get('question_type', 'general')}:history"
        await self.execute_redis(
            f"redis-cli zadd {specific_key} {timestamp} '{json.dumps(record)}'"
        )
        
        # Update stats for both keys
        stats_key = f"{self.redis_prefix}:{task_type['category']}:{task_type['name']}:stats"
        specific_stats_key = f"{self.redis_prefix}:{task_type['category']}:{task_type['name']}:{task_type.get('complexity', 'medium')}:{task_type.get('question_type', 'general')}:stats"
        await self.execute_redis(f"redis-cli hincrby {stats_key} total_runs 1")
        await self.execute_redis(f"redis-cli hincrby {specific_stats_key} total_runs 1")
        
        if success:
            await self.execute_redis(f"redis-cli hincrby {stats_key} successes 1")
            await self.execute_redis(f"redis-cli hincrby {specific_stats_key} successes 1")
        else:
            await self.execute_redis(f"redis-cli hincrby {stats_key} failures 1")
            await self.execute_redis(f"redis-cli hincrby {specific_stats_key} failures 1")
        
        # Set TTL if not already set
        history_ttl = int(os.environ.get('HISTORY_TTL', '604800'))  # Default 7 days
        
        # Check and set TTL for history key
        try:
            ttl_check = await self.execute_redis(f"redis-cli TTL {history_key}")
            if int(ttl_check) < 0:  # -1 means no TTL, -2 means key doesn't exist
                await self.execute_redis(f"redis-cli EXPIRE {history_key} {history_ttl}")
        except:
            pass  # Ignore TTL errors
            
        # Check and set TTL for specific key
        try:
            ttl_check = await self.execute_redis(f"redis-cli TTL {specific_key}")
            if int(ttl_check) < 0:
                await self.execute_redis(f"redis-cli EXPIRE {specific_key} {history_ttl}")
        except:
            pass
            
        # Check and set TTL for stats keys
        try:
            ttl_check = await self.execute_redis(f"redis-cli TTL {stats_key}")
            if int(ttl_check) < 0:
                await self.execute_redis(f"redis-cli EXPIRE {stats_key} {history_ttl}")
        except:
            pass
            
        try:
            ttl_check = await self.execute_redis(f"redis-cli TTL {specific_stats_key}")
            if int(ttl_check) < 0:
                await self.execute_redis(f"redis-cli EXPIRE {specific_stats_key} {history_ttl}")
        except:
            pass
        
        # Maintain history size (keep last 100)
        await self.execute_redis(f"redis-cli zremrangebyrank {history_key} 0 -101")
        await self.execute_redis(f"redis-cli zremrangebyrank {specific_key} 0 -101")
        
        print(f"[Redis] Updated {task_type['category']}:{task_type['name']} "
              f"({task_type.get('complexity', 'medium')}/{task_type.get('question_type', 'general')}) - "
              f"Actual: {elapsed:.1f}s, Expected: {expected:.1f}s, "
              f"Variance: {record['variance']:.1%}")
    
    async def validate_timeout(self, command: str, proposed_timeout: int) -> Dict:
        """
        Validate a proposed timeout against Redis historical data.
        
        Args:
            command: The command to validate timeout for
            proposed_timeout: The proposed timeout in seconds
            
        Returns:
            Dictionary with validation results
        """
        # Get complexity estimation
        estimation = await self.estimate_complexity(command)
        
        # Calculate validation metrics
        suggested_timeout = int(estimation['max_time'])
        diff_percentage = abs(suggested_timeout - proposed_timeout) / proposed_timeout * 100
        
        # Determine if timeout is reasonable
        is_valid = True
        adjustment_reason = None
        
        if suggested_timeout > proposed_timeout * 2:
            # Proposed timeout is way too short
            is_valid = False
            adjustment_reason = "Proposed timeout is too short based on historical data"
        elif suggested_timeout < proposed_timeout * 0.5:
            # Proposed timeout is unnecessarily long
            is_valid = True  # Still valid but wasteful
            adjustment_reason = "Proposed timeout is longer than necessary"
        
        return {
            "is_valid": is_valid,
            "proposed_timeout": proposed_timeout,
            "suggested_timeout": suggested_timeout,
            "difference_percentage": diff_percentage,
            "confidence": estimation['confidence'],
            "based_on": estimation['based_on'],
            "adjustment_reason": adjustment_reason,
            "task_classification": {
                "category": estimation['category'],
                "task": estimation['task'],
                "complexity": estimation['complexity'],
                "question_type": estimation['question_type']
            }
        }


# Self-verification
if __name__ == "__main__":
    async def test_redis_timing():
        timer = RedisTaskTimer()
        
        # Test 1: Redis connection
        try:
            result = await timer.execute_redis("redis-cli ping")
            assert result == "PONG", f"Redis not responding: {result}"
            print("✓ Redis connection OK")
        except Exception as e:
            print(f"✗ Redis connection failed: {e}")
            return False
        
        # Test 2: Command classification with enhanced classifier
        test_cases = [
            ("redis-cli GET user:123", {
                "category": "redis", "name": "simple_op", 
                "complexity": "simple", "question_type": "lookup"
            }),
            ("What is code to add two numbers?", {
                "category": "code",
                "complexity": "trivial"
            }),
            ("What is a Python function to calculate factorial?", {
                "category": "code",
                "complexity": "low"
            }),
            ("ls -la", {
                "category": "system", "name": "simple_cmd",
                "complexity": "simple", "question_type": "filesystem"
            }),
        ]
        
        for cmd, expected in test_cases:
            result = timer.classify_command(cmd)
            # Check key fields match (allow some flexibility for enhanced classifier)
            for key in ['category', 'complexity']:
                if key in expected:
                    assert result[key] == expected[key], f"Classification failed for {key}: {cmd} → {result}"
        print("✓ Command classification OK")
        
        # Test 3: Complexity estimation
        estimate = await timer.estimate_complexity("redis-cli GET test")
        assert estimate['expected_time'] > 0
        assert estimate['max_time'] > estimate['expected_time']
        print(f"✓ Complexity estimation OK: {estimate}")
        
        # Test 4: History update and retrieval
        test_task = {
            "category": "test", 
            "name": "verification",
            "complexity": "medium",
            "question_type": "testing"
        }
        await timer.update_history(test_task, elapsed=5.2, success=True, expected=5.0)
        
        history = await timer.get_task_history("test", "verification", "medium", "testing")
        assert history['sample_size'] > 0
        assert 5.2 in history['times']
        print(f"✓ History storage OK: {history}")
        
        # Test 5: Find similar tasks
        # Add another test task
        test_task2 = {
            "category": "test2",
            "name": "another_test", 
            "complexity": "medium",
            "question_type": "testing"
        }
        await timer.update_history(test_task2, elapsed=6.1, success=True, expected=6.0)
        
        similar = await timer.find_similar_tasks("medium", "testing")
        assert len(similar) >= 2, f"Expected at least 2 similar tasks, got {len(similar)}"
        print(f"✓ Find similar tasks OK: Found {len(similar)} similar tasks")
        
        # Test 6: Timeout validation
        validation = await timer.validate_timeout("echo test", 90)
        assert validation['is_valid'], "Timeout validation failed"
        assert 'suggested_timeout' in validation
        print(f"✓ Timeout validation OK: {validation}")
        
        # Test 7: Test unknown prompt handling  
        # Test with a prompt that should default to 'general' category
        unknown_estimate = await timer.estimate_complexity("Please do something completely random and undefined")
        print(f"Unknown prompt estimate: {unknown_estimate}")
        # General category gets medium complexity which is 60s * 3 = 180s expected
        assert unknown_estimate['expected_time'] >= 600.0, f"Unknown prompt should have minimum 600s (10 min) timeout, got {unknown_estimate['expected_time']}"
        print(f"✓ Unknown prompt handling OK: min timeout {unknown_estimate['expected_time']}s")
        
        # Test 8: Get average execution time
        avg_time = await timer.get_average_execution_time("redis-cli GET test")
        print(f"✓ Average execution time retrieval OK: {avg_time}s" if avg_time else "✓ No average time available (expected)")
        
        # Test 9: Search similar prompts
        similar = await timer.search_similar_prompts("What is a function to add numbers?", {
            'complexity': 'trivial',
            'keywords': ['function', 'add']
        })
        print(f"✓ Similar prompt search OK: Found {len(similar)} similar prompts")
        
        # Test 10: Recovery test - Redis failure simulation
        print("\n--- Recovery Tests ---")
        
        # Save original method
        original_execute = timer.execute_redis
        
        # Simulate Redis failure
        async def mock_redis_fail(cmd):
            raise Exception("Redis connection failed")
        
        timer.execute_redis = mock_redis_fail
        
        # Test that estimation still works with fallback
        try:
            fallback_estimate = await timer.estimate_complexity("echo fallback test")
            assert fallback_estimate['based_on'] == 'default_with_3x_baseline', "Should fall back to defaults"
            print("✓ Recovery OK: Falls back to defaults when Redis fails")
        except Exception as e:
            print(f"✗ Recovery failed: {e}")
            return False
        
        # Test timeout validation with Redis down
        try:
            fallback_validation = await timer.validate_timeout("echo test", 90)
            assert fallback_validation['based_on'] == 'default_with_3x_baseline'
            print("✓ Timeout validation OK with Redis down")
        except Exception as e:
            print(f"✗ Timeout validation failed during recovery: {e}")
            return False
        
        # Restore Redis connection
        timer.execute_redis = original_execute
        
        # Cleanup
        await timer.execute_redis("redis-cli del cc_executor:times:test:verification:history")
        await timer.execute_redis("redis-cli del cc_executor:times:test:verification:stats")
        await timer.execute_redis("redis-cli del cc_executor:times:test:verification:medium:testing:history")
        await timer.execute_redis("redis-cli del cc_executor:times:test:verification:medium:testing:stats")
        await timer.execute_redis("redis-cli del cc_executor:times:test2:another_test:history")
        await timer.execute_redis("redis-cli del cc_executor:times:test2:another_test:stats")
        await timer.execute_redis("redis-cli del cc_executor:times:test2:another_test:medium:testing:history")
        await timer.execute_redis("redis-cli del cc_executor:times:test2:another_test:medium:testing:stats")
        
        print("\n✓ All tests passed including recovery!")
        return True
    
    # Run verification
    success = asyncio.run(test_redis_timing())
    assert success, "Redis timing verification failed"
