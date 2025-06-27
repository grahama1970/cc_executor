# Generate Unified Stress Test Report

## 🔴 SELF-IMPROVEMENT RULES
This prompt MUST follow the self-improvement protocol:
1. Every failure updates metrics immediately
2. Every failure fixes the root cause
3. Every failure adds a recovery test
4. Every change updates evolution history

## 🎮 GAMIFICATION METRICS
- **Success**: 0
- **Failure**: 0
- **Total Executions**: 0
- **Last Updated**: 2025-06-26
- **Success Ratio**: N/A (need 10:1 to graduate)

## Evolution History
- v1: Initial implementation combining test definitions with results
- v2: Added hallucination verification with transcript commands
- v3: Updated to use official transcript_helper.py

## PURPOSE
Generate a comprehensive, easy-to-read report that combines:
1. Original test definitions from unified_stress_test_tasks.json
2. Actual execution results with full responses
3. Clear success/failure indicators
4. Actionable insights

## IMPLEMENTATION

```python
#!/usr/bin/env python3
"""Generate unified stress test report combining definitions and results"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

class UnifiedStressTestReporter:
    def __init__(self):
        self.task_definitions_file = "/home/graham/workspace/experiments/cc_executor/src/cc_executor/tasks/unified_stress_test_tasks.json"
        self.output_dir = Path("stress_test_outputs")
        self.report_style = "enhanced"  # enhanced, simple, markdown
        
    def load_task_definitions(self) -> Dict[str, Any]:
        """Load the original test definitions"""
        with open(self.task_definitions_file, 'r') as f:
            return json.load(f)
    
    def find_latest_results(self) -> Dict[str, Any]:
        """Find the most recent test execution results"""
        # Look for latest summary JSON
        summary_files = list(Path(".").glob("stress_test_summary_*.json"))
        if not summary_files:
            return {}
        
        latest_summary = max(summary_files, key=lambda p: p.stat().st_mtime)
        with open(latest_summary, 'r') as f:
            return json.load(f)
    
    def load_response_content(self, category: str, task_id: str) -> Optional[str]:
        """Load the actual response content for a task"""
        # Find matching output file
        pattern = f"{category}_{task_id}_*.txt"
        matches = list(self.output_dir.glob(pattern))
        
        if matches:
            # Get the most recent one
            latest = max(matches, key=lambda p: p.stat().st_mtime)
            with open(latest, 'r') as f:
                return f.read()
        return None
    
    def extract_marker_from_response(self, response_content: str) -> Optional[str]:
        """Extract the marker from response content"""
        import re
        # Look for MARKER_YYYYMMDD_HHMMSS_microseconds_taskid pattern
        marker_pattern = r'MARKER_\d{8}_\d{6}_\d+_\w+'
        match = re.search(marker_pattern, response_content)
        return match.group(0) if match else None
    
    def verify_in_transcript(self, marker: str) -> bool:
        """Verify marker exists in Claude transcript logs using the helper script"""
        import subprocess
        try:
            # Use the official transcript helper script
            result = subprocess.run(
                ['python', '/home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts/commands/transcript_helper.py', marker],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            # Fallback to direct check
            try:
                cmd = f'rg "{marker}" ~/.claude/projects/-home-graham-workspace-experiments-cc_executor/*.jsonl'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
                return result.returncode == 0 and marker in result.stdout
            except:
                return False
    
    def get_transcript_verification_command(self, marker: str) -> str:
        """Get the exact command to verify in transcript"""
        # Provide multiple verification options
        return f'''# To verify this response was not hallucinated, run ONE of these:

# Option 1: Use the official transcript helper (RECOMMENDED)
python /home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts/commands/transcript_helper.py "{marker}"

# Option 2: Check for hallucination specifically
python /home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts/commands/transcript_helper.py check "{marker}"

# Option 3: Simple count check
rg "{marker}" ~/.claude/projects/-home-graham-workspace-experiments-cc_executor/*.jsonl | wc -l

# Option 4: Extract actual output
rg "{marker}" ~/.claude/projects/-home-graham-workspace-experiments-cc_executor/*.jsonl | cut -d: -f2- | jq -r '.toolUseResult.stdout // .message.content' | grep -A10 "{marker}"'''
    
    def generate_unified_report(self) -> str:
        """Generate the comprehensive report"""
        definitions = self.load_task_definitions()
        results = self.find_latest_results()
        
        report = []
        report.append("="*100)
        report.append("🚀 UNIFIED STRESS TEST REPORT - COMPLETE RESULTS")
        report.append("="*100)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Overall summary
        if results:
            total_time = results.get('execution_time', 0)
            report.append(f"Total Execution Time: {total_time:.2f}s ({total_time/60:.1f} minutes)")
            report.append("")
        
        # Process each category
        for category_name, category_def in definitions['categories'].items():
            report.append(f"\n{'='*100}")
            report.append(f"📁 CATEGORY: {category_name.upper()}")
            report.append(f"   Description: {category_def['description']}")
            report.append("="*100)
            
            # Get results for this category
            category_results = results.get('categories', {}).get(category_name, {})
            cat_tasks = category_results.get('tasks', [])
            
            # Category summary
            if cat_tasks:
                total = category_results.get('total', 0)
                successful = category_results.get('successful', 0)
                report.append(f"\n📊 Category Summary: {successful}/{total} tasks succeeded ({successful/total*100:.1f}%)")
                avg_time = sum(t['duration'] for t in cat_tasks) / len(cat_tasks)
                report.append(f"   Average execution time: {avg_time:.2f}s")
            
            # Process each task
            for task_def in category_def['tasks']:
                task_id = task_def['id']
                task_name = task_def['name']
                
                report.append(f"\n{'─'*80}")
                report.append(f"📋 Task: {task_name} (ID: {task_id})")
                report.append("─"*80)
                
                # Original request
                report.append(f"\n📝 Request:")
                report.append(f"   {task_def['natural_language_request']}")
                
                # Expected patterns
                report.append(f"\n🔍 Expected Patterns:")
                for pattern in task_def['verification']['expected_patterns']:
                    report.append(f"   - {pattern}")
                
                # Find matching result
                task_result = next((t for t in cat_tasks if t['id'] == task_id), None)
                
                if task_result:
                    # Execution results
                    success = task_result.get('success', False)
                    duration = task_result.get('duration', 0)
                    response_length = task_result.get('response_length', 0)
                    patterns_found = task_result.get('patterns_found', 0)
                    patterns_total = task_result.get('patterns_total', 0)
                    
                    status_icon = "✅" if success else "❌"
                    report.append(f"\n{status_icon} Execution Result:")
                    report.append(f"   Duration: {duration:.2f}s")
                    report.append(f"   Response Length: {response_length:,} characters")
                    report.append(f"   Patterns Found: {patterns_found}/{patterns_total}")
                    
                    if task_result.get('error'):
                        report.append(f"   ⚠️ Error: {task_result['error']}")
                    
                    # Load and show actual response
                    response_content = self.load_response_content(category_name, task_id)
                    if response_content:
                        # Extract just the response part (after the headers)
                        lines = response_content.split('\n')
                        response_start = 0
                        for i, line in enumerate(lines):
                            if line.startswith('='*80):
                                response_start = i + 2
                                break
                        
                        actual_response = '\n'.join(lines[response_start:])
                        
                        report.append(f"\n📤 Actual Response Preview:")
                        report.append("```")
                        # Show first 1000 chars
                        preview = actual_response[:1000]
                        if len(actual_response) > 1000:
                            preview += f"\n... [{len(actual_response)-1000:,} more characters]"
                        report.append(preview)
                        report.append("```")
                        
                        # Analysis
                        report.append(f"\n🔬 Pattern Analysis:")
                        for pattern in task_def['verification']['expected_patterns']:
                            found = pattern.lower() in actual_response.lower()
                            icon = "✓" if found else "✗"
                            report.append(f"   {icon} '{pattern}' - {'Found' if found else 'NOT FOUND'}")
                            
                            if found and pattern.lower() not in preview.lower():
                                # Find where it appears
                                pos = actual_response.lower().find(pattern.lower())
                                context_start = max(0, pos - 50)
                                context_end = min(len(actual_response), pos + len(pattern) + 50)
                                context = actual_response[context_start:context_end]
                                report.append(f"      Found at position {pos}: ...{context}...")
                        
                        # HALLUCINATION CHECK
                        report.append(f"\n🔍 Hallucination Verification:")
                        marker = self.extract_marker_from_response(response_content)
                        if marker:
                            transcript_verified = self.verify_in_transcript(marker)
                            if transcript_verified:
                                report.append(f"   ✅ VERIFIED: Found marker '{marker}' in transcript")
                                report.append(f"   This response was NOT hallucinated.")
                            else:
                                report.append(f"   ❌ WARNING: Marker '{marker}' NOT found in transcript")
                                report.append(f"   This response may be hallucinated!")
                            
                            # Show exact verification command
                            report.append(f"\n   📋 Verification Command:")
                            report.append(f"   ```bash")
                            report.append(f"   {self.get_transcript_verification_command(marker)}")
                            report.append(f"   ```")
                        else:
                            report.append(f"   ⚠️ No marker found in response")
                else:
                    report.append(f"\n❓ No execution results found for this task")
        
        # Final summary
        report.append(f"\n{'='*100}")
        report.append("📈 OVERALL SUMMARY")
        report.append("="*100)
        
        if results:
            total_tasks = sum(cat.get('total', 0) for cat in results.get('categories', {}).values())
            total_success = sum(cat.get('successful', 0) for cat in results.get('categories', {}).values())
            
            report.append(f"Total Tasks Executed: {total_tasks}")
            report.append(f"Successful: {total_success}")
            report.append(f"Failed: {total_tasks - total_success}")
            report.append(f"Overall Success Rate: {total_success/total_tasks*100:.1f}%")
            
            # Hallucination summary
            report.append(f"\n🔍 HALLUCINATION CHECK SUMMARY:")
            verified_count = 0
            total_checked = 0
            unverified_tasks = []
            
            for cat_name in results.get('categories', {}).keys():
                for task_def in definitions['categories'][cat_name]['tasks']:
                    response_content = self.load_response_content(cat_name, task_def['id'])
                    if response_content:
                        total_checked += 1
                        marker = self.extract_marker_from_response(response_content)
                        if marker and self.verify_in_transcript(marker):
                            verified_count += 1
                        else:
                            unverified_tasks.append(f"{cat_name}/{task_def['id']}")
            
            report.append(f"   Responses with transcript verification: {verified_count}/{total_checked}")
            if total_checked > 0:
                verification_rate = verified_count/total_checked*100
                if verification_rate == 100:
                    report.append(f"   ✅ ALL responses verified in transcript (NOT hallucinated)")
                elif verification_rate > 90:
                    report.append(f"   ✅ {verification_rate:.1f}% verified (mostly reliable)")
                else:
                    report.append(f"   ⚠️ Only {verification_rate:.1f}% verified (possible hallucinations)")
                
                if unverified_tasks:
                    report.append(f"\n   ❌ Unverified tasks (may be hallucinated):")
                    for task in unverified_tasks:
                        report.append(f"      - {task}")
            
            # Category breakdown table
            report.append(f"\n{'Category':<25} {'Tasks':<10} {'Success':<10} {'Rate':<10} {'Avg Time':<10}")
            report.append("-"*65)
            
            for cat_name, cat_data in results.get('categories', {}).items():
                total = cat_data.get('total', 0)
                successful = cat_data.get('successful', 0)
                rate = successful/total*100 if total > 0 else 0
                tasks = cat_data.get('tasks', [])
                avg_time = sum(t['duration'] for t in tasks) / len(tasks) if tasks else 0
                
                report.append(f"{cat_name:<25} {total:<10} {successful:<10} {rate:<10.1f}% {avg_time:<10.1f}s")
        
        return "\n".join(report)
    
    def save_report(self, content: str) -> str:
        """Save the report to a file"""
        filename = f"unified_stress_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, 'w') as f:
            f.write(content)
        return filename

# Extract to: tmp/generate_report.py
if __name__ == "__main__":
    reporter = UnifiedStressTestReporter()
    report = reporter.generate_unified_report()
    filename = reporter.save_report(report)
    print(f"✅ Report generated: {filename}")
    print(f"\nReport preview:")
    print("="*80)
    print(report[:2000])
    print("="*80)
    print(f"\nFull report saved to: {filename}")
```

## USAGE

```bash
# First run the stress tests with full capture
cd /home/graham/workspace/experiments/cc_executor/src/cc_executor/tests/stress
python unified_stress_test_executor_v3.py

# Then generate the unified report
python -c "
import sys
sys.path.insert(0, '.')
exec(open('/home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts/generate_unified_stress_test_report.md').read().split('```python')[1].split('```')[0])
"

# Or extract and run
sed -n '/^```python$/,/^```$/p' /home/graham/workspace/experiments/cc_executor/src/cc_executor/prompts/generate_unified_stress_test_report.md | sed '1d;$d' > tmp/generate_report.py
python tmp/generate_report.py
```

## REPORT FEATURES

The unified report shows:

1. **Original Test Definition**
   - The request sent to Claude
   - Expected patterns to find

2. **Execution Results**
   - Success/failure status
   - Execution duration
   - Response length
   - Pattern match count

3. **Actual Response**
   - Preview of Claude's actual response
   - Full pattern analysis
   - Shows WHERE patterns were found

4. **Hallucination Verification**
   - Checks if response exists in transcript
   - Provides exact `rg` + `jq` command to verify
   - Summary of verified vs unverified responses

5. **Category Summaries**
   - Success rates by category
   - Average execution times
   - Overall statistics

## EXAMPLE OUTPUT

```
📋 Task: ten_functions (ID: parallel_1)
────────────────────────────────────────

📝 Request:
   Generate 10 different Python functions simultaneously: 1) Calculate area of circle...

🔍 Expected Patterns:
   - def 
   - return
   - circle
   - fibonacci

✅ Execution Result:
   Duration: 31.62s
   Response Length: 3,421 characters
   Patterns Found: 2/4

📤 Actual Response Preview:
```
Here are 10 different Python functions as requested:

1. Calculate area of circle:
def calculate_circle_area(radius):
    import math
    return math.pi * radius ** 2

2. Convert celsius to fahrenheit:
def celsius_to_fahrenheit(celsius):
    return (celsius * 9/5) + 32
...
```

🔬 Pattern Analysis:
   ✗ 'def ' - NOT FOUND
   ✓ 'return' - Found
   ✓ 'circle' - Found
   ✓ 'fibonacci' - Found
      Found at position 1523: ...def generate_fibonacci(n):...

🔍 Hallucination Verification:
   ✅ VERIFIED: Found marker 'MARKER_20250625_174345_968380_parallel_1' in transcript
   This response was NOT hallucinated.

   📋 Verification Command:
   ```bash
   # To verify this response was not hallucinated, run:
   rg "MARKER_20250625_174345_968380_parallel_1" ~/.claude/projects/-home-graham-workspace-experiments-cc-executor/*.jsonl | jq -r '.message.content[] | select(.type=="text") | .text' 2>/dev/null | head -20
   ```
```

## VERIFICATION

```bash
# Verify report generation
ls -la unified_stress_test_report_*.txt | tail -1

# Check report content
grep -E "(✅|❌|📤)" unified_stress_test_report_*.txt | head -20
```

## WHY THIS MATTERS

Now when you ask "show me the stress test report", I can:
1. Generate this unified report
2. Show exactly what was requested vs what was received
3. Explain why patterns were "missing" (often formatting issues)
4. Provide actionable insights for improving tests