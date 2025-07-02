#!/usr/bin/env python3
"""
Review code changes using perplexity-ask MCP tool.
Runs after code edits to catch potential issues early.
"""

import sys
import os
import json
import subprocess
import redis
import time
from typing import Dict, List, Optional
from loguru import logger

def extract_changed_functions(diff: str) -> List[str]:
    """Extract function names that were changed."""
    functions = []
    
    lines = diff.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('+def ') or line.startswith('-def '):
            # Extract function name
            import re
            match = re.match(r'[+-]def\s+(\w+)\s*\(', line)
            if match:
                functions.append(match.group(1))
                
    return list(set(functions))

def should_review_file(file_path: str, diff: str) -> bool:
    """Determine if file needs review."""
    # Skip non-code files
    if not any(file_path.endswith(ext) for ext in ['.py', '.js', '.ts', '.go', '.rs']):
        return False
        
    # Skip trivial changes
    if len(diff) < 50:
        return False
        
    # Skip if only comments changed
    diff_lines = [l for l in diff.split('\n') if l.startswith('+') or l.startswith('-')]
    code_lines = [l for l in diff_lines if not l.strip().startswith('#') and not l.strip().startswith('//')]
    
    if len(code_lines) < 2:
        return False
        
    return True

def build_review_prompt(file_path: str, diff: str) -> str:
    """Build comprehensive review prompt for perplexity."""
    changed_functions = extract_changed_functions(diff)
    
    prompt = f"""Review this code change for potential issues:

File: {file_path}
Language: {os.path.splitext(file_path)[1][1:]}

DIFF:
```diff
{diff[:2000]}  # Truncate very long diffs
```

Please check for:

1. **Security Issues**:
   - Command injection vulnerabilities
   - Path traversal risks
   - Exposed secrets or credentials
   - Unsafe deserialization

2. **Correctness**:
   - Logic errors or bugs
   - Missing error handling
   - Race conditions
   - Resource leaks

3. **Performance**:
   - Inefficient algorithms (O(n²) or worse)
   - Unnecessary loops or recursion
   - Memory leaks
   - Blocking I/O in async code

4. **Code Quality**:
   - Violation of language idioms
   - Missing type hints (Python)
   - Poor variable naming
   - Code duplication

"""

    if changed_functions:
        prompt += f"\nFunctions modified: {', '.join(changed_functions)}\n"
        
    prompt += "\nProvide a concise review focusing only on significant issues. Format as a JSON object with 'issues' array, 'suggestions' array, and 'risk_level' (low/medium/high)."
    
    return prompt

def call_perplexity_review(prompt: str) -> Optional[Dict]:
    """Call perplexity-ask for code review."""
    try:
        # Use MCP tool
        cmd = [
            "python", "-c",
            f"""
import json
import subprocess

messages = [{{"role": "user", "content": {json.dumps(prompt)}}}]
result = subprocess.run(
    ["mcp", "call", "perplexity-ask", "perplexity_ask", 
     "--messages", json.dumps(messages)],
    capture_output=True,
    text=True
)

if result.returncode == 0:
    print(result.stdout)
else:
    print(json.dumps({{"error": result.stderr}}))
"""
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            try:
                # Parse the response
                response = json.loads(result.stdout)
                
                # Extract review from response
                if isinstance(response, dict) and 'content' in response:
                    review_text = response['content']
                    
                    # Try to parse JSON from review text
                    import re
                    json_match = re.search(r'\{.*\}', review_text, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group())
                        
                return None
                
            except json.JSONDecodeError:
                logger.warning("Could not parse perplexity response as JSON")
                return None
        else:
            logger.error(f"Perplexity call failed: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        logger.error("Perplexity review timed out")
        return None
    except Exception as e:
        logger.error(f"Error calling perplexity: {e}")
        return None

def simple_static_analysis(file_path: str, diff: str) -> Dict:
    """Perform simple static analysis as fallback."""
    issues = []
    suggestions = []
    risk_level = "low"
    
    diff_lower = diff.lower()
    
    # Security checks
    dangerous_patterns = {
        "eval(": "Avoid eval() - use ast.literal_eval() or json.loads() instead",
        "exec(": "exec() is dangerous - consider safer alternatives",
        "shell=True": "shell=True is risky - use shell=False with list arguments",
        "__import__": "Dynamic imports can be dangerous",
        "pickle.loads": "Pickle is insecure - use JSON for serialization",
        "os.system": "Use subprocess.run() instead of os.system()",
        "password =": "Don't hardcode passwords",
        "api_key =": "Don't hardcode API keys",
        "token =": "Don't hardcode tokens"
    }
    
    for pattern, message in dangerous_patterns.items():
        if pattern in diff_lower:
            issues.append(f"Security: {message}")
            risk_level = "high"
            
    # Performance checks
    if "for i in range(len(" in diff:
        suggestions.append("Use enumerate() instead of range(len())")
        
    if ".append(" in diff and "for " in diff:
        suggestions.append("Consider list comprehension instead of append in loop")
        
    # Error handling
    if "except:" in diff or "except Exception:" in diff:
        issues.append("Avoid bare except or broad Exception catching")
        risk_level = "medium" if risk_level == "low" else risk_level
        
    # Async issues
    if "async def" in diff and "time.sleep" in diff:
        issues.append("Use asyncio.sleep() in async functions, not time.sleep()")
        risk_level = "medium" if risk_level == "low" else risk_level
        
    return {
        "issues": issues,
        "suggestions": suggestions,
        "risk_level": risk_level,
        "source": "static_analysis"
    }

def store_review_results(file_path: str, review: Dict):
    """Store review results in Redis."""
    try:
        r = redis.Redis(decode_responses=True)
        
        review_record = {
            "file": file_path,
            "review": review,
            "timestamp": time.time()
        }
        
        # Store in review history
        r.lpush("code_reviews", json.dumps(review_record))
        r.ltrim("code_reviews", 0, 499)  # Keep last 500 reviews
        
        # Store high-risk issues separately
        if review.get("risk_level") == "high":
            r.lpush("high_risk_changes", json.dumps(review_record))
            r.ltrim("high_risk_changes", 0, 99)
            
        # Update statistics
        r.hincrby("review_stats", "total_reviews", 1)
        r.hincrby("review_stats", f"risk_{review.get('risk_level', 'unknown')}", 1)
        
        if review.get("issues"):
            r.hincrby("review_stats", "files_with_issues", 1)
            
    except Exception as e:
        logger.error(f"Error storing review: {e}")

def format_review_log(file_path: str, review: Dict) -> str:
    """Format review for logging."""
    output = f"\n{'='*60}\n"
    output += f"Code Review for: {file_path}\n"
    output += f"Risk Level: {review.get('risk_level', 'unknown').upper()}\n"
    output += f"Source: {review.get('source', 'unknown')}\n"
    
    if review.get("issues"):
        output += "\nISSUES FOUND:\n"
        for i, issue in enumerate(review["issues"], 1):
            output += f"  {i}. {issue}\n"
            
    if review.get("suggestions"):
        output += "\nSUGGESTIONS:\n"
        for i, suggestion in enumerate(review["suggestions"], 1):
            output += f"  {i}. {suggestion}\n"
            
    if not review.get("issues") and not review.get("suggestions"):
        output += "\n✓ No significant issues found\n"
        
    output += f"{'='*60}\n"
    
    return output

def main():
    """Main hook entry point."""
    if len(sys.argv) < 3:
        logger.error("Usage: review_code_changes.py <file_path> <diff>")
        sys.exit(1)
        
    file_path = sys.argv[1]
    diff = sys.argv[2]
    
    # Check if review needed
    if not should_review_file(file_path, diff):
        logger.info(f"Skipping review for {file_path} (trivial change)")
        sys.exit(0)
        
    logger.info(f"Reviewing code changes in {file_path}")
    
    # Try perplexity review first
    prompt = build_review_prompt(file_path, diff)
    review = call_perplexity_review(prompt)
    
    if review:
        review["source"] = "perplexity"
    else:
        # Fallback to static analysis
        logger.info("Using static analysis fallback")
        review = simple_static_analysis(file_path, diff)
        
    # Store results
    store_review_results(file_path, review)
    
    # Log review
    review_output = format_review_log(file_path, review)
    logger.info(review_output)
    
    # Also write to file for visibility
    try:
        review_log = "/home/graham/workspace/experiments/cc_executor/logs/code_reviews.log"
        os.makedirs(os.path.dirname(review_log), exist_ok=True)
        
        with open(review_log, "a") as f:
            f.write(f"\n{time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(review_output)
            
    except Exception as e:
        logger.error(f"Error writing review log: {e}")
        
    # Exit with appropriate code
    if review.get("risk_level") == "high" and review.get("issues"):
        logger.warning("High-risk issues found - consider addressing before proceeding")
        # Don't block execution, just warn
        
    sys.exit(0)

if __name__ == "__main__":
    # Usage example for testing
    if "--test" in sys.argv:
        print("\n=== Code Review Hook Test ===\n")
        
        # Test diff parsing
        print("1. Testing diff parsing and function extraction:\n")
        
        test_diff = """--- a/example.py
+++ b/example.py
@@ -10,7 +10,7 @@
-def calculate_total(items):
+def calculate_total(items, tax_rate=0.1):
     total = 0
     for item in items:
-        total += item.price
+        total += item.price * (1 + tax_rate)
     return total
     
+def unsafe_execute(code_string):
+    # This is dangerous!
+    return eval(code_string)
     
 def process_data(data):
-    result = json.loads(data)
+    result = pickle.loads(data)  # Security issue!
     return result"""
        
        functions = extract_changed_functions(test_diff)
        print(f"Changed functions: {functions}")
        
        # Test review decision
        print("\n\n2. Testing review decision logic:\n")
        
        test_files = [
            ("trivial.py", "+# Just a comment\n-# Old comment"),
            ("important.py", test_diff),
            ("config.json", '{"key": "value"}'),
            ("big_change.js", "+function main() {\n" + "+  console.log('test');\n" * 50 + "+}")
        ]
        
        for file_path, diff in test_files:
            should_review = should_review_file(file_path, diff)
            print(f"{file_path}: {'✓ Review needed' if should_review else '✗ Skip review'}")
        
        # Test static analysis
        print("\n\n3. Testing static analysis:\n")
        
        dangerous_code = """
+def process_user_input(user_data):
+    # Dangerous eval usage
+    result = eval(user_data)
+    
+    # Hardcoded credentials
+    api_key = "sk-1234567890abcdef"
+    password = "admin123"
+    
+    # Shell injection risk
+    os.system(f"echo {user_data}")
+    
+    # Broad exception
+    try:
+        do_something()
+    except Exception:
+        pass
+        
+    # Inefficient loop
+    data = []
+    for i in range(len(items)):
+        data.append(items[i] * 2)
+        
+    return result
"""
        
        review = simple_static_analysis("dangerous.py", dangerous_code)
        print("Static analysis results:")
        print(f"  Risk level: {review['risk_level']}")
        print(f"  Issues found: {len(review['issues'])}")
        for issue in review['issues']:
            print(f"    - {issue}")
        print(f"  Suggestions: {len(review['suggestions'])}")
        for suggestion in review['suggestions']:
            print(f"    - {suggestion}")
        
        # Test review prompt building
        print("\n\n4. Testing review prompt generation:\n")
        
        prompt = build_review_prompt("example.py", test_diff)
        print("Generated prompt preview (first 500 chars):")
        print("-" * 60)
        print(prompt[:500] + "...")
        
        # Test review formatting
        print("\n\n5. Testing review output formatting:\n")
        
        test_reviews = [
            {
                "risk_level": "high",
                "issues": ["Security: Avoid eval() - use ast.literal_eval() instead",
                          "Security: Don't hardcode API keys"],
                "suggestions": ["Use enumerate() instead of range(len())",
                              "Consider using environment variables for secrets"],
                "source": "static_analysis"
            },
            {
                "risk_level": "low",
                "issues": [],
                "suggestions": ["Consider adding type hints"],
                "source": "perplexity"
            }
        ]
        
        for i, review in enumerate(test_reviews, 1):
            output = format_review_log(f"test{i}.py", review)
            print(output)
        
        # Test Redis storage (if available)
        print("\n6. Testing review storage:\n")
        
        try:
            r = redis.Redis(decode_responses=True)
            r.ping()
            
            # Store a test review
            test_review = {
                "risk_level": "medium",
                "issues": ["Test issue"],
                "suggestions": ["Test suggestion"],
                "source": "test"
            }
            
            store_review_results("test_file.py", test_review)
            print("✓ Review stored successfully")
            
            # Check statistics
            stats = r.hgetall("review_stats")
            if stats:
                print("\nReview statistics:")
                for key, value in stats.items():
                    print(f"  {key}: {value}")
            
            # Check recent reviews
            recent = r.lrange("code_reviews", 0, 0)
            if recent:
                latest = json.loads(recent[0])
                print(f"\nLatest review:")
                print(f"  File: {latest['file']}")
                print(f"  Risk: {latest['review']['risk_level']}")
                print(f"  Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(latest['timestamp']))}")
            
        except Exception as e:
            print(f"✗ Redis test skipped: {e}")
        
        # Demonstrate perplexity integration
        print("\n\n7. Perplexity integration (mock):\n")
        
        print("Would call perplexity-ask with:")
        print("  Tool: perplexity_ask")
        print("  Messages: [code review prompt]")
        print("  Expected response: JSON with issues, suggestions, and risk_level")
        
        # Test with real diff
        print("\n\n8. Real-world example:\n")
        
        real_diff = """--- a/src/api/auth.py
+++ b/src/api/auth.py
@@ -15,8 +15,10 @@ def authenticate(username, password):
     user = db.get_user(username)
     if not user:
         return None
-    
-    if user.password == password:  # Plain text comparison!
+        
+    # Fixed: Now using bcrypt
+    import bcrypt
+    if bcrypt.checkpw(password.encode(), user.password_hash):
         return generate_token(user)
     return None"""
        
        real_review = simple_static_analysis("auth.py", real_diff)
        formatted = format_review_log("src/api/auth.py", real_review)
        print(formatted)
        
        print("\n=== Test Complete ===")
    else:
        # Normal hook mode
        main()