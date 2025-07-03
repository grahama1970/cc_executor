#!/usr/bin/env python3
"""
Redis-based similarity search for finding similar prompts and averaging execution times.

Uses RediSearch for:
1. Token count similarity (numeric range)
2. Complexity matching (tag)
3. BM25 keyword search
4. Expected vs actual comparison

Returns average actual execution time from similar prompts.
"""

import json
import asyncio
import statistics
from typing import List, Dict, Optional, Tuple
import hashlib
import re

class RedisSimilaritySearch:
    def __init__(self, redis_prefix="cc_executor:prompts"):
        self.redis_prefix = redis_prefix
        self.index_name = f"{redis_prefix}:idx"
        
    async def execute_redis(self, command: str) -> str:
        """Execute redis-cli command"""
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise Exception(f"Redis error: {stderr.decode()}")
        return stdout.decode().strip()
    
    async def create_search_index(self):
        """
        Create RediSearch index for similarity matching.
        
        Schema includes:
        - prompt_text: Full text search (BM25)
        - keywords: Extracted keywords for better matching
        - token_count: Numeric for range queries
        - complexity: Tag field (simple/medium/complex)
        - expected_time: Numeric
        - actual_time: Numeric  
        - execution_variance: Numeric (actual/expected ratio)
        """
        schema = """
        FT.CREATE {idx}
        ON HASH PREFIX 1 {prefix}:
        SCHEMA
            prompt_text TEXT WEIGHT 2.0
            keywords TEXT WEIGHT 3.0
            token_count NUMERIC SORTABLE
            complexity TAG SORTABLE
            expected_time NUMERIC SORTABLE
            actual_time NUMERIC SORTABLE
            execution_variance NUMERIC SORTABLE
            success TAG
            timestamp NUMERIC SORTABLE
        """.format(idx=self.index_name, prefix=self.redis_prefix)
        
        try:
            await self.execute_redis(f"redis-cli {schema}")
            print(f"✓ Created RediSearch index: {self.index_name}")
        except Exception as e:
            if "Index already exists" in str(e):
                print(f"✓ RediSearch index exists: {self.index_name}")
            else:
                print(f"⚠️ Could not create index: {e}")
    
    def extract_keywords(self, prompt: str) -> List[str]:
        """Extract important keywords from prompt for better matching."""
        # Remove common words
        stop_words = {
            'what', 'is', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on',
            'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'it', 'that',
            'this', 'these', 'those', 'be', 'been', 'being', 'have', 'has',
            'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could',
            'may', 'might', 'must', 'can', 'please', 'brief', 'briefly'
        }
        
        # Extract meaningful words
        words = re.findall(r'\b\w+\b', prompt.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        # Extract numbers and special patterns
        numbers = re.findall(r'\b\d+\b', prompt)
        keywords.extend(numbers)
        
        # Extract specific patterns
        patterns = [
            (r'(\d+)[-\s]*word', 'word_count'),
            (r'(\d+)\s*haiku', 'haiku_count'),
            (r'(\d+)\s*function', 'function_count'),
            (r'python|javascript|java|code', 'programming'),
            (r'recipe|cooking|food', 'culinary'),
            (r'story|narrative|plot', 'creative_writing'),
            (r'architecture|design|system', 'technical_design'),
        ]
        
        for pattern, keyword in patterns:
            if re.search(pattern, prompt.lower()):
                keywords.append(keyword)
        
        return list(set(keywords))  # Unique keywords
    
    async def index_prompt_execution(
        self, 
        prompt: str,
        token_count: int,
        complexity: str,
        expected_time: float,
        actual_time: float,
        success: bool = True
    ) -> str:
        """
        Index a prompt execution for future similarity searches.
        
        Returns:
            Document ID for the indexed prompt
        """
        # Generate document ID
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:12]
        doc_id = f"{self.redis_prefix}:{prompt_hash}:{int(actual_time)}"
        
        # Extract keywords
        keywords = self.extract_keywords(prompt)
        
        # Calculate execution variance
        variance = actual_time / expected_time if expected_time > 0 else 1.0
        
        # Prepare document
        fields = {
            "prompt_text": prompt,
            "keywords": " ".join(keywords),
            "token_count": token_count,
            "complexity": complexity,
            "expected_time": expected_time,
            "actual_time": actual_time,
            "execution_variance": variance,
            "success": "true" if success else "false",
            "timestamp": int(asyncio.get_event_loop().time())
        }
        
        # Build HSET command
        field_args = []
        for k, v in fields.items():
            field_args.extend([k, str(v)])
        
        # Index the document
        await self.execute_redis(
            f"redis-cli HSET {doc_id} {' '.join(field_args)}"
        )
        
        print(f"✓ Indexed prompt: {doc_id} (tokens: {token_count}, complexity: {complexity})")
        return doc_id
    
    async def find_similar_prompts(
        self,
        prompt: str,
        token_count: int,
        complexity: str,
        token_range_percent: float = 0.2,  # ±20% tokens
        limit: int = 10
    ) -> List[Dict]:
        """
        Find similar prompts using multi-dimensional search.
        
        Args:
            prompt: The prompt to find similarities for
            token_count: Token count of the prompt
            complexity: Complexity level
            token_range_percent: Token count tolerance (0.2 = ±20%)
            limit: Maximum results to return
            
        Returns:
            List of similar prompts with execution data
        """
        # Calculate token range
        min_tokens = int(token_count * (1 - token_range_percent))
        max_tokens = int(token_count * (1 + token_range_percent))
        
        # Extract keywords for BM25 search
        keywords = self.extract_keywords(prompt)
        keyword_query = " ".join(keywords)
        
        # Build RediSearch query
        # Combine: keyword search + token range + complexity tag + success
        query = f"""
        (@keywords:({keyword_query}))
        @token_count:[{min_tokens} {max_tokens}]
        @complexity:{{{complexity}}}
        @success:{{true}}
        """
        
        # Execute search with scoring
        search_cmd = f"""
        redis-cli FT.SEARCH {self.index_name}
        '{query.strip()}'
        LIMIT 0 {limit}
        RETURN 6 actual_time expected_time token_count execution_variance prompt_text keywords
        SORTBY actual_time ASC
        """
        
        try:
            result = await self.execute_redis(search_cmd)
            return self._parse_search_results(result)
        except Exception as e:
            print(f"Search failed, using fallback: {e}")
            # Fallback to simpler search
            return await self._fallback_search(complexity, min_tokens, max_tokens, limit)
    
    def _parse_search_results(self, redis_output: str) -> List[Dict]:
        """Parse RediSearch output into structured results."""
        lines = redis_output.strip().split('\n')
        if not lines or lines[0] == '0':
            return []
        
        results = []
        try:
            # First line is count
            count = int(lines[0])
            if count == 0:
                return []
            
            # Parse each result
            i = 1
            while i < len(lines) and len(results) < count:
                # Doc ID
                doc_id = lines[i]
                i += 1
                
                # Fields
                fields = {}
                while i < len(lines) and not lines[i].startswith(self.redis_prefix):
                    if i + 1 < len(lines):
                        key = lines[i]
                        value = lines[i + 1]
                        fields[key] = value
                        i += 2
                    else:
                        break
                
                if fields:
                    results.append({
                        "doc_id": doc_id,
                        "actual_time": float(fields.get("actual_time", 0)),
                        "expected_time": float(fields.get("expected_time", 0)),
                        "token_count": int(fields.get("token_count", 0)),
                        "variance": float(fields.get("execution_variance", 1.0)),
                        "prompt_preview": fields.get("prompt_text", "")[:100],
                        "keywords": fields.get("keywords", "").split()
                    })
        except Exception as e:
            print(f"Parse error: {e}")
        
        return results
    
    async def _fallback_search(
        self, 
        complexity: str,
        min_tokens: int,
        max_tokens: int,
        limit: int
    ) -> List[Dict]:
        """Fallback search using SCAN when RediSearch unavailable."""
        results = []
        
        # Scan for matching documents
        cursor = "0"
        pattern = f"{self.redis_prefix}:*"
        
        while cursor != "0" or not results:
            scan_result = await self.execute_redis(
                f"redis-cli SCAN {cursor} MATCH '{pattern}' COUNT 100"
            )
            lines = scan_result.strip().split('\n')
            if len(lines) >= 2:
                cursor = lines[0]
                keys = lines[1:]
                
                # Check each key
                for key in keys:
                    if key:
                        doc = await self.execute_redis(f"redis-cli HGETALL {key}")
                        doc_fields = self._parse_hgetall(doc)
                        
                        # Filter by criteria
                        if (doc_fields.get("complexity") == complexity and
                            doc_fields.get("success") == "true" and
                            min_tokens <= int(doc_fields.get("token_count", 0)) <= max_tokens):
                            
                            results.append({
                                "doc_id": key,
                                "actual_time": float(doc_fields.get("actual_time", 0)),
                                "expected_time": float(doc_fields.get("expected_time", 0)),
                                "token_count": int(doc_fields.get("token_count", 0)),
                                "variance": float(doc_fields.get("execution_variance", 1.0))
                            })
                            
                            if len(results) >= limit:
                                return results
            
            if cursor == "0":
                break
        
        return results
    
    def _parse_hgetall(self, output: str) -> Dict[str, str]:
        """Parse HGETALL output into dictionary."""
        lines = output.strip().split('\n')
        result = {}
        for i in range(0, len(lines), 2):
            if i + 1 < len(lines):
                result[lines[i]] = lines[i + 1]
        return result
    
    async def get_average_execution_time(
        self,
        prompt: str,
        token_count: int,
        complexity: str,
        min_samples: int = 3
    ) -> Optional[Dict]:
        """
        Get average execution time from similar prompts.
        
        Returns:
            Dictionary with average time and metadata, or None if insufficient data
        """
        # Find similar prompts
        similar = await self.find_similar_prompts(
            prompt=prompt,
            token_count=token_count,
            complexity=complexity,
            limit=20  # Get more samples for better average
        )
        
        if len(similar) < min_samples:
            return None
        
        # Calculate statistics
        actual_times = [s["actual_time"] for s in similar]
        
        # Remove outliers using IQR method
        if len(actual_times) >= 5:
            q1 = statistics.quantiles(actual_times, n=4)[0]
            q3 = statistics.quantiles(actual_times, n=4)[2]
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            # Filter outliers
            filtered_times = [t for t in actual_times if lower_bound <= t <= upper_bound]
            if filtered_times:
                actual_times = filtered_times
        
        # Calculate average and other stats
        avg_time = statistics.mean(actual_times)
        median_time = statistics.median(actual_times)
        std_dev = statistics.stdev(actual_times) if len(actual_times) > 1 else 0
        
        return {
            "average_time": avg_time,
            "median_time": median_time,
            "std_dev": std_dev,
            "sample_count": len(actual_times),
            "confidence": min(len(actual_times) / 10, 1.0),  # Higher sample = higher confidence
            "similar_prompts": [s["prompt_preview"] for s in similar[:3]],  # Top 3 examples
            "token_range": {
                "min": min(s["token_count"] for s in similar),
                "max": max(s["token_count"] for s in similar)
            }
        }


# Example usage and testing
if __name__ == "__main__":
    async def test_similarity_search():
        """Test the Redis similarity search system"""
        
        search = RedisSimilaritySearch()
        
        # Create index
        await search.create_search_index()
        
        # Index some sample executions
        test_prompts = [
            {
                "prompt": "What is a Python function to calculate factorial?",
                "tokens": 120,
                "complexity": "medium",
                "expected": 30,
                "actual": 28
            },
            {
                "prompt": "What is Python code for factorial calculation with memoization?",
                "tokens": 130,
                "complexity": "medium", 
                "expected": 35,
                "actual": 32
            },
            {
                "prompt": "What is a recursive Python function for factorial?",
                "tokens": 110,
                "complexity": "medium",
                "expected": 30,
                "actual": 29
            },
            {
                "prompt": "What is a collection of 20 haikus about nature?",
                "tokens": 850,
                "complexity": "complex",
                "expected": 120,
                "actual": 115
            }
        ]
        
        print("Indexing test prompts...")
        for test in test_prompts:
            await search.index_prompt_execution(
                prompt=test["prompt"],
                token_count=test["tokens"],
                complexity=test["complexity"],
                expected_time=test["expected"],
                actual_time=test["actual"]
            )
        
        # Test similarity search
        print("\n" + "="*60)
        print("Testing similarity search...")
        
        new_prompt = "What is a Python implementation of factorial using iteration?"
        token_estimate = 125
        
        print(f"\nNew prompt: {new_prompt}")
        print(f"Estimated tokens: {token_estimate}")
        
        # Get average execution time
        result = await search.get_average_execution_time(
            prompt=new_prompt,
            token_count=token_estimate,
            complexity="medium"
        )
        
        if result:
            print(f"\n✓ Found {result['sample_count']} similar prompts")
            print(f"Average execution time: {result['average_time']:.1f}s")
            print(f"Median time: {result['median_time']:.1f}s")
            print(f"Standard deviation: {result['std_dev']:.1f}s")
            print(f"Confidence: {result['confidence']:.2f}")
            print(f"\nSimilar prompts:")
            for i, prompt in enumerate(result['similar_prompts'], 1):
                print(f"  {i}. {prompt}...")
        else:
            print("✗ Insufficient similar prompts found")
        
        # Cleanup
        print("\nCleaning up test data...")
        for test in test_prompts:
            prompt_hash = hashlib.md5(test["prompt"].encode()).hexdigest()[:12]
            doc_id = f"{search.redis_prefix}:{prompt_hash}:{int(test['actual'])}"
            await search.execute_redis(f"redis-cli DEL {doc_id}")
        
        return True
    
    # Run test
    asyncio.run(test_similarity_search())