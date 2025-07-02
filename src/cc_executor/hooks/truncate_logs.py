#!/usr/bin/env python3
"""
Post-output hook to truncate large logs before they're written.
Prevents log bloat from base64 blobs, embeddings, or verbose outputs.

This hook runs after command execution to ensure logs remain manageable
while preserving full output in Redis/results for debugging.
"""

import os
import sys
import json
from typing import Dict, Any, Optional
from loguru import logger

# Configuration
MAX_LOG_LINE_LENGTH = 1000  # Max chars per line
MAX_LOG_LINES = 100         # Max lines to keep
MAX_TOTAL_SIZE = 10240      # 10KB total max
TRUNCATION_MARKER = "\n... [TRUNCATED: {} bytes omitted] ...\n"

def truncate_large_value(value: str, max_size: int = MAX_TOTAL_SIZE) -> str:
    """Truncate large strings intelligently."""
    if len(value) <= max_size:
        return value
    
    # Keep first and last portions for context
    keep_start = max_size // 2
    keep_end = max_size // 4
    
    omitted_bytes = len(value) - keep_start - keep_end
    
    return (
        value[:keep_start] + 
        TRUNCATION_MARKER.format(omitted_bytes) + 
        value[-keep_end:]
    )

def truncate_output_lines(output: str) -> str:
    """Truncate output by limiting lines and line length."""
    lines = output.split('\n')
    
    # Truncate individual long lines
    truncated_lines = []
    for line in lines[:MAX_LOG_LINES]:
        if len(line) > MAX_LOG_LINE_LENGTH:
            truncated_lines.append(line[:MAX_LOG_LINE_LENGTH] + "... [LINE TRUNCATED]")
        else:
            truncated_lines.append(line)
    
    # Add marker if lines were omitted
    if len(lines) > MAX_LOG_LINES:
        truncated_lines.append(f"\n... [{len(lines) - MAX_LOG_LINES} lines omitted] ...")
    
    result = '\n'.join(truncated_lines)
    
    # Final size check
    return truncate_large_value(result)

def detect_binary_content(data: str) -> bool:
    """Detect if content is likely binary/base64."""
    # Common base64 patterns
    if len(data) > 1000:
        # High ratio of alphanumeric chars without spaces
        alnum_ratio = sum(c.isalnum() for c in data[:1000]) / 1000
        space_ratio = data[:1000].count(' ') / 1000
        
        if alnum_ratio > 0.95 and space_ratio < 0.01:
            return True
    
    # Check for common binary markers
    binary_markers = [
        'data:image/', 'data:application/', 'data:video/',
        'base64,', '\\x00', '\\xff\\xd8\\xff'  # JPEG header
    ]
    
    return any(marker in data[:200] for marker in binary_markers)

def main():
    """Main hook entry point."""
    # Get context from environment
    output = os.environ.get('CLAUDE_OUTPUT', '')
    duration = os.environ.get('CLAUDE_DURATION', '')
    tokens = os.environ.get('CLAUDE_TOKENS', '')
    
    if not output:
        logger.debug("No output to process")
        return
    
    # Detect binary content
    if detect_binary_content(output):
        logger.info("Binary/base64 content detected - aggressive truncation")
        truncated = "[BINARY DATA - {} bytes total]".format(len(output))
    else:
        # Normal text truncation
        truncated = truncate_output_lines(output)
    
    # Log truncation stats
    if len(truncated) < len(output):
        reduction_pct = (1 - len(truncated) / len(output)) * 100
        logger.info(
            f"Log truncation applied: {len(output)} → {len(truncated)} bytes "
            f"({reduction_pct:.1f}% reduction)"
        )
    
    # Store truncation metadata for metrics
    try:
        # Try Redis first for metrics
        import redis
        r = redis.Redis(decode_responses=True)
        
        session_id = os.environ.get('CLAUDE_SESSION_ID', 'default')
        truncation_key = f"logs:truncation:{session_id}"
        
        truncation_data = {
            'original_size': len(output),
            'truncated_size': len(truncated),
            'is_binary': detect_binary_content(output),
            'timestamp': os.environ.get('CLAUDE_TIMESTAMP', ''),
            'duration': duration
        }
        
        r.lpush(truncation_key, json.dumps(truncation_data))
        r.expire(truncation_key, 3600)  # 1 hour TTL
        
    except Exception as e:
        logger.debug(f"Could not store truncation metrics: {e}")
    
    # Write truncated output back to environment
    # This allows other hooks or the main process to use it
    os.environ['CLAUDE_OUTPUT_TRUNCATED'] = truncated
    
    # Also write to stdout for immediate use
    print(json.dumps({
        'truncated': True,
        'original_size': len(output),
        'truncated_size': len(truncated),
        'output': truncated
    }))

if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{message}")
    
    # Usage example for testing
    if "--test" in sys.argv:
        print("\n=== Log Truncation Hook Test ===\n")
        
        # Test binary content detection
        print("1. Testing binary content detection:\n")
        
        test_cases = [
            ("Normal text", "This is normal text with spaces and punctuation!"),
            ("Code snippet", "def hello():\n    print('Hello World')\n    return True"),
            ("Base64 image", "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA" + "A" * 500),
            ("Long alphanumeric", "a1b2c3d4e5f6g7h8i9j0" * 100),
            ("JSON data", '{"key": "value", "number": 42, "array": [1, 2, 3]}'),
            ("Binary marker", "\\xff\\xd8\\xff\\xe0\\x00\\x10JFIF" + "X" * 200)
        ]
        
        for name, content in test_cases:
            is_binary = detect_binary_content(content)
            print(f"{name}: {'✓ Binary' if is_binary else '✗ Text'}")
        
        # Test value truncation
        print("\n\n2. Testing large value truncation:\n")
        
        large_text = "A" * 5000 + " [MIDDLE CONTENT] " + "Z" * 5000
        truncated = truncate_large_value(large_text, 1000)
        
        print(f"Original size: {len(large_text)} bytes")
        print(f"Truncated size: {len(truncated)} bytes")
        print(f"Truncated preview: {truncated[:100]}...")
        print(f"Contains marker: {'TRUNCATED' in truncated}")
        
        # Test line truncation
        print("\n\n3. Testing output line truncation:\n")
        
        # Create output with many lines
        many_lines = "\n".join([f"Line {i}: " + "x" * 200 for i in range(200)])
        truncated_lines = truncate_output_lines(many_lines)
        
        print(f"Original lines: {len(many_lines.split(chr(10)))}")
        print(f"Truncated lines: {len(truncated_lines.split(chr(10)))}")
        print(f"Original size: {len(many_lines)} bytes")
        print(f"Truncated size: {len(truncated_lines)} bytes")
        
        # Show truncation markers
        if "LINE TRUNCATED" in truncated_lines:
            print("✓ Long lines were truncated")
        if "lines omitted" in truncated_lines:
            print("✓ Extra lines were omitted")
        
        # Test different output types
        print("\n\n4. Testing different output types:\n")
        
        test_outputs = [
            {
                "name": "Small normal output",
                "content": "Task completed successfully\nAll tests passed\nDone."
            },
            {
                "name": "Large code output",
                "content": "\n".join([
                    f"def function_{i}():\n    # This is function number {i}\n    return {i} * 2\n"
                    for i in range(100)
                ])
            },
            {
                "name": "Base64 blob",
                "content": "Result: data:image/png;base64," + "iVBORw0KGgoAAAANSUhEUgAAAAUA" * 1000
            },
            {
                "name": "Verbose logs",
                "content": "\n".join([
                    f"[2024-01-01 12:00:{i:02d}] DEBUG: Processing item {i} of 1000..."
                    for i in range(1000)
                ])
            },
            {
                "name": "Mixed content",
                "content": "Normal start\n" + "=" * 2000 + "\ndata:image/jpeg;base64," + "A" * 5000 + "\nNormal end"
            }
        ]
        
        for test in test_outputs:
            print(f"\n{test['name']}:")
            original_size = len(test['content'])
            
            # Detect if binary
            if detect_binary_content(test['content']):
                result = "[BINARY DATA - {} bytes total]".format(original_size)
            else:
                result = truncate_output_lines(test['content'])
            
            truncated_size = len(result)
            reduction = (1 - truncated_size / original_size) * 100 if original_size > 0 else 0
            
            print(f"  Original: {original_size} bytes")
            print(f"  Truncated: {truncated_size} bytes")
            print(f"  Reduction: {reduction:.1f}%")
            print(f"  Preview: {result[:80]}...")
        
        # Test Redis storage
        print("\n\n5. Testing Redis metrics storage:\n")
        
        try:
            import redis
            r = redis.Redis(decode_responses=True)
            r.ping()
            
            # Set up test environment
            os.environ['CLAUDE_SESSION_ID'] = 'test_truncate'
            os.environ['CLAUDE_TIMESTAMP'] = '2024-01-01T12:00:00'
            os.environ['CLAUDE_DURATION'] = '5.5'
            
            # Store test truncation data
            test_output = "A" * 50000  # Large output
            
            session_id = os.environ.get('CLAUDE_SESSION_ID')
            truncation_key = f"logs:truncation:{session_id}"
            
            truncation_data = {
                'original_size': len(test_output),
                'truncated_size': len(truncate_large_value(test_output)),
                'is_binary': False,
                'timestamp': os.environ.get('CLAUDE_TIMESTAMP'),
                'duration': os.environ.get('CLAUDE_DURATION')
            }
            
            r.lpush(truncation_key, json.dumps(truncation_data))
            r.expire(truncation_key, 60)
            
            # Retrieve and verify
            stored = r.lrange(truncation_key, 0, -1)
            if stored:
                latest = json.loads(stored[0])
                print("✓ Truncation metrics stored")
                print(f"  Original size: {latest['original_size']}")
                print(f"  Truncated size: {latest['truncated_size']}")
                print(f"  Reduction: {(1 - latest['truncated_size']/latest['original_size'])*100:.1f}%")
            
            # Cleanup
            r.delete(truncation_key)
            os.environ.pop('CLAUDE_SESSION_ID', None)
            os.environ.pop('CLAUDE_TIMESTAMP', None)
            os.environ.pop('CLAUDE_DURATION', None)
            
        except Exception as e:
            print(f"✗ Redis test skipped: {e}")
        
        # Demonstrate full workflow
        print("\n\n6. Full workflow demonstration:\n")
        
        # Simulate a verbose command output
        sample_output = """
Starting task execution...
[INFO] Initializing environment
[DEBUG] Loading configuration from /etc/config.yaml
[DEBUG] Setting up database connection
""" + "\n".join([f"[VERBOSE] Processing record {i}: " + "x" * 100 for i in range(150)])
        
        print(f"Simulated command output: {len(sample_output)} bytes")
        
        # Set environment
        os.environ['CLAUDE_OUTPUT'] = sample_output
        os.environ['CLAUDE_DURATION'] = '12.5'
        os.environ['CLAUDE_TOKENS'] = '1500'
        
        # Run truncation
        original_main = main
        
        # Capture output
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            original_main()
        
        output = f.getvalue()
        if output:
            try:
                result = json.loads(output)
                print(f"\nTruncation result:")
                print(f"  Truncated: {result['truncated']}")
                print(f"  Original size: {result['original_size']}")
                print(f"  Truncated size: {result['truncated_size']}")
                print(f"  Reduction: {(1 - result['truncated_size']/result['original_size'])*100:.1f}%")
            except:
                print("Could not parse truncation result")
        
        # Check environment variable
        truncated_output = os.environ.get('CLAUDE_OUTPUT_TRUNCATED')
        if truncated_output:
            print(f"\n✓ Truncated output stored in environment ({len(truncated_output)} bytes)")
        
        # Cleanup
        os.environ.pop('CLAUDE_OUTPUT', None)
        os.environ.pop('CLAUDE_DURATION', None)
        os.environ.pop('CLAUDE_TOKENS', None)
        os.environ.pop('CLAUDE_OUTPUT_TRUNCATED', None)
        
        print("\n=== Test Complete ===")
    else:
        # Normal hook mode
        try:
            main()
        except Exception as e:
            logger.error(f"Truncation hook failed: {e}")
            # Don't block execution on truncation failures
            sys.exit(0)