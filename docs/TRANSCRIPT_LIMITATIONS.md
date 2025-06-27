# Claude Transcript Limitations

## The Problem

The Claude transcript (`~/.claude/projects/.../*.jsonl`) automatically truncates large outputs with `[truncated]`. This makes it **unreliable for hallucination detection** when working with large responses.

## Impact

- **Small outputs** (<1KB): Transcript verification works fine
- **Large outputs** (>10KB): Transcript shows `[truncated]` - cannot verify full content
- **Critical for**: Story generation, code generation, large data processing

## Solution: File-Based Verification

Since we cannot rely on transcripts for large outputs, we must:

1. **Always save outputs to files** in `test_outputs/`
2. **Use verification markers** throughout the output (not just at the beginning)
3. **Check file properties**: existence, size, checksum
4. **Create verification reports** with timestamps and checksums

## Verification Strategy

```python
from src.cc_executor.utils.verification import verify_no_hallucination

# After claiming to generate output
success = verify_no_hallucination(
    test_name="5000_word_story",
    output_file="claude_test_--no-tools-long_20250627_091234.txt",
    expected_markers=[
        "The Ghost in the Repository",  # Title
        "Marcus had been debugging",     # Opening line
        "word_count: 5000"              # Metadata
    ]
)

if not success:
    print("HALLUCINATION DETECTED - Output was not actually generated!")
```

## Best Practices

1. **Never trust "I generated X"** without file verification
2. **Include unique markers** in generated content
3. **Save ALL test outputs** to `test_outputs/` 
4. **Use checksums** for exact content verification
5. **Log file operations** at INFO level or higher

## Example Verification Flow

```bash
# 1. Run test (output saved to test_outputs/)
python -m src.cc_executor.core.websocket_handler --long --no-server

# 2. Check verification report
cat test_outputs/verification_*_story_*.json

# 3. Manually verify if needed
ls -la test_outputs/claude_test_*.txt
grep "The Ghost in the Repository" test_outputs/claude_test_*.txt
```

## Remember

The transcript is useful for:
- Debugging command execution
- Viewing small outputs
- Understanding flow

The transcript is NOT reliable for:
- Verifying large outputs exist
- Detecting hallucinations in big responses
- Proving work was actually done

**Always use file-based verification for critical outputs!**