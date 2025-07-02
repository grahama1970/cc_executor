# Self-Reflecting Prompts with Timeout Recovery

## The Ultimate Defense: Self-Reflection + Timeout Awareness

Combining self-reflection with timeout recovery creates prompts that can:
1. Self-correct quality issues
2. Recover from timeout scenarios
3. Provide partial results when needed

## Template Pattern

```
[TIMEOUT AWARENESS]
[MAIN REQUEST]
[SELF-REFLECTION CRITERIA]
[RECOVERY INSTRUCTIONS]
```

## Complete Examples

### Example 1: Code Generation with Full Recovery

```bash
claude -p "RESPONSE PROTOCOL:
- [0-2s] Output: 'WORKING: Analyzing request...'
- [Every 15s] Output: 'PROGRESS: [current section]...'
- [If timeout approaching] Output: '[PARTIAL RESULT]' and summarize

REQUEST: What is a Python implementation of a binary search tree with insert, search, and delete operations?

After providing your implementation, self-evaluate:
1. Are all three operations (insert, search, delete) implemented?
2. Is the code properly commented and documented?
3. Are edge cases handled (empty tree, single node, etc.)?
4. Is the code syntactically correct?

If any criteria are not met, provide an improved version.
Label versions as 'Version 1:', 'Version 2:', etc.
Maximum self-improvements: 2

TIMEOUT RECOVERY:
If you sense time running out:
- Mark current version as '[PARTIAL]'
- List what's missing in bullet points
- Provide the most critical parts first"
```

### Example 2: Complex Analysis with Checkpoints

```python
recovery_prompt = """CHECKPOINT PROTOCOL:
☐ [0-5s] Acknowledge: "ANALYZING: Processing architecture request..."
☐ [5-15s] Core Components: List main architectural elements
☐ [15-30s] Relationships: Describe how components interact  
☐ [30-45s] Deep Dive: Add implementation details
☐ [45s+] Best Practices: Include advanced patterns

REQUEST: What is the architecture for a real-time chat application?

After your response, evaluate against these criteria:
1. Did I cover all major components (server, client, database, messaging)?
2. Are the component interactions clearly explained?
3. Did I address scalability concerns?
4. Are security considerations mentioned?

Rate each: ✓ Complete | ~ Partial | ✗ Missing

If any are Partial or Missing, provide Version 2 with improvements.
Max iterations: 2

STALL PREVENTION:
- Every 20 seconds output: "CONTINUING: [section name]..."
- This prevents connection timeout
- If time critical, output: "[TIME_LIMIT] Condensed version: [summary]"
"""
```

### Example 3: Learning Task with Progressive Detail

```python
progressive_learning_prompt = """TIME-AWARE RESPONSE STRUCTURE:

IMMEDIATE (0-5s):
Output: "LEARNING TOPIC: Quantum Computing Basics"
Provide: One-paragraph overview

QUICK (5-20s):  
Add: Key concepts list with 1-line explanations

DETAILED (20-40s):
Add: In-depth explanation of each concept

COMPREHENSIVE (40s+):
Add: Examples, applications, and further reading

REQUEST: What is quantum computing and how does it differ from classical computing?

SELF-ASSESSMENT after each stage:
- Is my explanation accurate? [Y/N]
- Is it accessible to beginners? [Y/N]  
- Are the differences clearly stated? [Y/N]

If any 'N', revise that section before continuing.

TIMEOUT HANDLING:
- At any stage, if timeout approaching, output: "[STAGE COMPLETE: {stage_name}]"
- Summarize what would come next
- Mark as "[EXPANDABLE]" for follow-up
"""
```

## Implementation Strategy

### 1. Prompt Transformer Function

```python
def add_timeout_recovery_to_prompt(
    base_prompt: str,
    reflection_criteria: List[str],
    max_iterations: int = 2,
    timeout_expected: int = 90
) -> str:
    """
    Transform a self-reflecting prompt to include timeout recovery.
    """
    
    # Calculate checkpoint intervals
    checkpoints = generate_checkpoints(timeout_expected)
    
    # Build the enhanced prompt
    enhanced = f"""RESPONSE TIMING PROTOCOL:
{format_checkpoints(checkpoints)}

If approaching {timeout_expected}s limit, switch to summary mode.

{base_prompt}

SELF-REFLECTION CRITERIA:
{format_criteria(reflection_criteria)}

Evaluate and improve up to {max_iterations} times.

RECOVERY INSTRUCTIONS:
1. If timeout seems imminent, output '[TRUNCATING]'
2. Provide essentials only
3. List omitted items as bullets
4. End with '[FULL_VERSION_AVAILABLE]'
"""
    return enhanced

def generate_checkpoints(total_seconds: int) -> List[Tuple[int, str]]:
    """Generate reasonable checkpoints based on expected duration."""
    if total_seconds <= 30:
        return [
            (0, "Acknowledge request"),
            (10, "Provide core answer"),
            (20, "Add details/examples")
        ]
    elif total_seconds <= 90:
        return [
            (0, "Acknowledge request"),
            (15, "Outline structure"),
            (30, "Deliver main content"),
            (60, "Enhance with examples"),
            (80, "Final polish/summary")
        ]
    else:
        # Long-running task
        return [
            (0, "Acknowledge and plan"),
            (30, "First major section"),
            (60, "Second major section"),
            (90, "Third major section"),
            (120, "Integration and summary"),
            (150, "Advanced topics (if time)")
        ]
```

### 2. Response Parser with Recovery Detection

```python
class RecoveryAwareResponseParser:
    """Parse responses that may include timeout recovery markers."""
    
    def __init__(self):
        self.recovery_markers = [
            'WORKING:', 'PROGRESS:', 'CONTINUING:',
            'CHECKPOINT', '[PARTIAL]', '[TRUNCATING]',
            '[TIME_LIMIT]', '[STAGE COMPLETE'
        ]
        self.version_markers = [
            'Version 1:', 'Version 2:', 'Initial Response:',
            'Improved Response:', 'Final Version:'
        ]
        
    def parse_response(self, response: str) -> Dict:
        """Parse response detecting recovery and reflection."""
        result = {
            'versions': [],
            'recovery_used': False,
            'truncated': False,
            'checkpoints_hit': [],
            'self_evaluation': None
        }
        
        # Check for recovery markers
        for marker in self.recovery_markers:
            if marker in response:
                result['recovery_used'] = True
                if marker in ['[PARTIAL]', '[TRUNCATING]', '[TIME_LIMIT]']:
                    result['truncated'] = True
        
        # Extract versions
        result['versions'] = self._extract_versions(response)
        
        # Extract checkpoints
        result['checkpoints_hit'] = self._extract_checkpoints(response)
        
        # Extract self-evaluation
        result['self_evaluation'] = self._extract_evaluation(response)
        
        return result
    
    def _extract_versions(self, response: str) -> List[Dict]:
        """Extract different versions from self-reflection."""
        versions = []
        
        # Split by version markers
        parts = response
        for marker in self.version_markers:
            parts = parts.replace(marker, f"\n|||{marker}|||")
        
        sections = parts.split("|||")
        
        current_version = None
        for section in sections:
            for marker in self.version_markers:
                if section.strip().startswith(marker):
                    if current_version:
                        versions.append(current_version)
                    current_version = {
                        'marker': marker,
                        'content': section[len(marker):].strip()
                    }
        
        if current_version:
            versions.append(current_version)
            
        return versions
```

### 3. Integration with Stress Tests

```python
# Update stress test JSON with recovery-aware prompts
enhanced_stress_test = {
    "id": "complex_with_recovery",
    "name": "distributed_system_architecture",
    "natural_language_request": """TIMING: Respond within 120 seconds using this structure:
[0-10s] Output: 'DESIGNING: Distributed system architecture...'
[10-30s] List core components with one-line descriptions
[30-60s] Detail each component's responsibilities  
[60-90s] Explain inter-component communication
[90s+] Add scalability and failure handling

REQUEST: Design a distributed e-commerce system architecture.

SELF-EVALUATION after main response:
1. Did I cover all critical components? (API, Database, Cache, Queue, etc.)
2. Are failure scenarios addressed?
3. Is the design scalable?
4. Are security aspects considered?

If missing any, provide 'Improved Architecture:' section.
Max improvements: 1

TIMEOUT SAFETY:
- If approaching 120s, output '[CONDENSED]'
- List remaining topics as TODOs
- Focus on most critical elements""",
    
    "verification": {
        "expected_patterns": [
            "DESIGNING:", "components", "architecture",
            "API", "database", "cache"
        ],
        "timeout": 150,  # Extra buffer
        "recovery_markers": ["DESIGNING:", "CONTINUING:", "[CONDENSED]"],
        "version_markers": ["Improved Architecture:"],
        "allow_partial": true
    }
}
```

## Monitoring Recovery Effectiveness

```python
class RecoveryEffectivenessMonitor:
    """Track how well timeout recovery works."""
    
    def analyze_results(self, test_results: List[Dict]) -> Dict:
        """Analyze recovery effectiveness across tests."""
        
        recovery_stats = {
            'total_tests': len(test_results),
            'timeouts_prevented': 0,
            'partial_results_saved': 0,
            'successful_self_corrections': 0,
            'average_versions_needed': []
        }
        
        for result in test_results:
            if result.get('recovery_used') and result.get('success'):
                recovery_stats['timeouts_prevented'] += 1
            
            if result.get('truncated') and result.get('partial_value') > 0:
                recovery_stats['partial_results_saved'] += 1
            
            versions = result.get('versions_count', 1)
            if versions > 1:
                recovery_stats['successful_self_corrections'] += 1
            recovery_stats['average_versions_needed'].append(versions)
        
        recovery_stats['average_versions_needed'] = sum(
            recovery_stats['average_versions_needed']
        ) / len(recovery_stats['average_versions_needed'])
        
        return recovery_stats
```

## Best Practices

1. **Always Start with Acknowledgment**: Prevents immediate timeout
2. **Use Progressive Disclosure**: Most important info first
3. **Include Time Estimates**: Help Claude pace its response
4. **Clear Truncation Markers**: Enable parsing partial responses
5. **Combine with Reflection**: Quality + Reliability

## Success Metrics

Track these to measure effectiveness:
- Timeout rate reduction
- Partial result usefulness score  
- Self-correction success rate
- Average response completeness
- User satisfaction with truncated responses

This approach ensures that even in worst-case scenarios, users get:
- Immediate acknowledgment (no early timeout)
- Core information (even if truncated)
- Quality through self-reflection
- Clear indication of completeness
- Graceful degradation