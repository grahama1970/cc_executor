# [Component Name] — Gamified Self-Improving Prompt

<!-- 
IMPORTANT: This template is for scenarios where:
1. Hooks are not available or not being used
2. You want explicit UUID4 handling in the prompt itself
3. You're creating standalone self-improving scripts

If you're using CC Executor with hooks, the UUID4 verification
can be handled automatically and transparently by hooks instead!
See: /docs/hooks/UUID_VERIFICATION_HOOK.md

This template includes:
1. Explicit UUID4 generation and verification (at END of JSON)
2. Success/failure tracking with 10:1 graduation requirement
3. Self-recovery patterns for automatic improvement
4. Raw output saving to prevent fabrication
-->

## 🔐 Anti-Hallucination UUID
<!-- Generated fresh for each execution - NEVER reuse -->
**Execution UUID**: `[GENERATE WITH uuid.uuid4()]`

## 📊 TASK METRICS & HISTORY
<!-- Updated after EVERY run - truthful tracking is mandatory -->
- **Success/Failure Ratio**: 0:0 (Target: 10:1 to graduate)
- **Last Updated**: YYYY-MM-DD HH:MM:SS
- **Last UUID**: `[Previous execution UUID for verification]`
- **Evolution History**:
  | Version | Change & Reason | Result | UUID |
  | :------ | :-------------- | :----- | :--- |
  | v1      | Initial implementation | TBD | TBD |

### Verification Command
```bash
# Verify last execution actually happened
grep "[Last UUID]" ~/.claude/projects/*/\*.jsonl
```

---
## 🎯 GAMIFICATION RULES
<!-- These rules create accountability and prevent giving up -->

### HOW TO WIN (Graduate to .py file)
1. Achieve 10 successful executions for every 1 failure
2. All outputs must be verifiable (UUID present in JSON)
3. No hallucinated results (transcript verification required)

### HOW TO LOSE (Penalties)
1. **Hallucination = Instant Failure** ❌
   - Every output checked against transcripts
   - Lying/faking results = automatic failure
   - No partial credit for "almost working"

2. **Incomplete Work = Failure** ❌
   - Stopping before 10:1 ratio = punishment
   - Giving up = failure
   - Partial solutions = failure

3. **Graduated File Failure = Reset to 0:0**
   - If .py file fails after graduation, back to square one
   - All progress lost
   - Must start over from scratch

### VERIFICATION IS MANDATORY
```python
# Every execution must include:
execution_uuid = str(uuid.uuid4())
print(f"🔐 Execution UUID: {execution_uuid}")

# And end with UUID verification:
assert execution_uuid in output_content, "UUID verification failed!"
```

---
## 🏛️ ARCHITECT'S BRIEFING (Immutable)
<!-- Core requirements that cannot change -->

### 1. Purpose
[Clear description of what this component does]

### 2. Core Requirements
- [ ] Generate UUID4 at start of execution
- [ ] Include UUID at END of all JSON outputs
- [ ] Save raw outputs to prevent hallucination
- [ ] Implement self-recovery on failures
- [ ] Track success/failure honestly

### 3. Output Structure
```json
{
  "timestamp": "ISO-8601 timestamp",
  "results": "actual results here",
  "metrics": {
    "duration": "seconds",
    "success": true/false
  },
  "execution_uuid": "MUST BE LAST KEY"
}
```

---
## 🤖 IMPLEMENTATION WORKSPACE

### **Implementation Code Block**
```python
#!/usr/bin/env python3
"""
[Component description]
Implements UUID4 anti-hallucination verification
"""

import uuid
import json
import time
from pathlib import Path
from datetime import datetime

class ComponentExecutor:
    def __init__(self):
        # Generate UUID4 immediately - this proves execution started
        self.execution_uuid = str(uuid.uuid4())
        self.start_time = time.time()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Print UUID for transcript verification
        print(f"🔐 Starting execution with UUID: {self.execution_uuid}")
        
    def execute(self):
        """Main execution logic"""
        try:
            # Your implementation here
            results = self._do_work()
            
            # Build output with UUID at END
            output = self._build_output(results, success=True)
            
            # Save and verify
            self._save_output(output)
            self._verify_uuid(output)
            
            print(f"✅ Execution successful. UUID: {self.execution_uuid}")
            return output
            
        except Exception as e:
            # Self-recovery: analyze and document failure
            failure_output = self._build_output(
                {"error": str(e)}, 
                success=False
            )
            self._save_output(failure_output)
            self._analyze_failure(e)
            print(f"❌ Execution failed. UUID: {self.execution_uuid}")
            raise
            
    def _do_work(self):
        """Actual component logic goes here"""
        # TODO: Implement actual functionality
        return {"status": "implemented"}
        
    def _build_output(self, results, success):
        """Build output dict with UUID at END"""
        return {
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "metrics": {
                "duration": time.time() - self.start_time,
                "success": success
            },
            "execution_uuid": self.execution_uuid  # MUST BE LAST
        }
        
    def _save_output(self, output):
        """Save output to prevent hallucination"""
        # Create directories
        reports_dir = Path(__file__).parent / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        responses_dir = Path(__file__).parent / "tmp" / "responses"
        responses_dir.mkdir(parents=True, exist_ok=True)
        
        # Save JSON with UUID at end
        json_file = responses_dir / f"{Path(__file__).stem}_{self.timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(output, f, indent=2)
            
        print(f"💾 Output saved to: {json_file}")
        
    def _verify_uuid(self, output):
        """Verify UUID is present and at END"""
        # Check it exists
        assert "execution_uuid" in output, "UUID missing from output!"
        assert output["execution_uuid"] == self.execution_uuid, "UUID mismatch!"
        
        # Check it's at END
        keys = list(output.keys())
        assert keys[-1] == "execution_uuid", f"UUID not at end! Last key: {keys[-1]}"
        
    def _analyze_failure(self, error):
        """Self-recovery: analyze failure for next attempt"""
        print(f"\n🔍 Analyzing failure for self-improvement:")
        print(f"  Error type: {type(error).__name__}")
        print(f"  Error message: {str(error)}")
        
        # Suggest improvements
        if "timeout" in str(error).lower():
            print("  💡 Suggestion: Increase timeout or optimize performance")
        elif "import" in str(error).lower():
            print("  💡 Suggestion: Check dependencies and imports")
        elif "connection" in str(error).lower():
            print("  💡 Suggestion: Verify service is running and accessible")
            
if __name__ == "__main__":
    # Create and run executor
    executor = ComponentExecutor()
    
    try:
        output = executor.execute()
        
        # Additional verification for main execution
        assert output["metrics"]["success"] == True, "Execution marked as failure!"
        assert output["execution_uuid"] == executor.execution_uuid, "UUID verification failed!"
        
        print("\n✅ All verifications passed!")
        
    except Exception as e:
        print(f"\n❌ Component failed: {e}")
        print("\n📝 Update the metrics section with this failure")
        exit(1)
```

### **Self-Recovery Patterns**

#### Pattern 1: Timeout Recovery
```python
@retry(wait=wait_exponential(min=1, max=10), stop=stop_after_attempt(3))
def operation_with_timeout():
    """Automatically retry with exponential backoff"""
    pass
```

#### Pattern 2: Import Error Recovery
```python
try:
    import optional_module
except ImportError:
    print("⚠️  Optional module not available, using fallback")
    optional_module = None
```

#### Pattern 3: Connection Recovery
```python
for attempt in range(3):
    try:
        connection = connect_to_service()
        break
    except ConnectionError:
        if attempt < 2:
            print(f"Retry {attempt + 1}/3 after connection failed")
            time.sleep(2 ** attempt)
        else:
            raise
```

---
## 🧪 VERIFICATION STEPS

### Step 1: UUID Generation
**Goal**: Verify UUID is generated and displayed
**Command**: `python component.py | grep "Execution UUID"`
**Expected**: Line containing UUID pattern: `🔐 Starting execution with UUID: [UUID]`

### Step 2: Output Structure
**Goal**: Verify JSON has UUID at END
**Command**: `python component.py && tail -3 tmp/responses/*.json`
**Expected**: Last key before closing brace is `"execution_uuid"`

### Step 3: Failure Recovery
**Goal**: Test self-recovery on failure
**Command**: `python component.py --force-failure`
**Expected**: Failure analysis and suggestions displayed

### Step 4: Transcript Verification
**Goal**: Verify execution in Claude transcript
**Command**: `grep "[UUID from output]" ~/.claude/projects/*/\*.jsonl`
**Expected**: Matching entries in transcript logs

---
## 📈 METRICS UPDATE TEMPLATE

After each run, update the metrics section:

```markdown
| v2 | Added timeout handling | ✅ Success | a4f5c2d1-8b3e-4f7a-9c1b-2d3e4f5a6b7c |
| v3 | Fixed import error | ❌ Failed | b5e6d3e2-9c4f-5g8b-0d2c-3e4f5g6b7c8d |
```

Current ratio: X successes, Y failures (X:Y)
- If X:Y ≥ 10:1 → Graduate to .py file! 🎓
- If X:Y < 10:1 → Keep improving 💪

---
## 🚨 ANTI-HALLUCINATION CHECKLIST

Before claiming success, verify ALL of these:

- [ ] UUID printed at start of execution
- [ ] UUID appears in saved JSON file
- [ ] UUID is the LAST key in JSON
- [ ] Output file actually exists on disk
- [ ] Execution appears in Claude transcripts
- [ ] No "simulated" or "would" language used
- [ ] Actual execution times recorded
- [ ] Real error messages (not fabricated)

Remember: **Hallucination = Instant Failure** ❌

---
## 🎯 GRADUATION CRITERIA

To graduate this prompt to a .py file:

1. **Success Ratio**: Achieve 10:1 (10 successes per failure)
2. **UUID Verification**: All executions have verifiable UUIDs
3. **No Hallucinations**: All results traceable in transcripts
4. **Self-Recovery**: Failures include improvement analysis
5. **Clean Code**: Follows all best practices

Once graduated:
- Move implementation to `component_name.py`
- Archive this prompt with final metrics
- If graduated file fails, return here with 0:0 ratio

---
## 🔍 DEBUGGING RESOURCES

### When Stuck, Use Both:
1. **perplexity-ask**: For real-time issues and specific errors
2. **gemini CLI**: For best practices and architectural guidance

### Example Debug Session:
```python
# Use Task tool to query both simultaneously
from tools import Task

Task.run([
    {
        "tool": "perplexity-ask",
        "query": f"Python error: {specific_error_message}"
    },
    {
        "tool": "gemini",
        "query": "Best practices for handling this error pattern"
    }
])
```

### Common Issues Reference:
- Subprocess deadlocks → See PROMPT_BEST_PRACTICES.md
- Claude CLI hangs → Use `-p` not `--print`
- Buffer overflows → Drain streams immediately
- UUID verification fails → Check JSON key order

---

Remember: The goal is not just to make it work once, but to create reliable, verifiable, self-improving code that graduates to production quality. Every failure is a learning opportunity documented in the metrics table.