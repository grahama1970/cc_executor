# AssessComplexity Tool Optimization Plan

## Current Issues
1. Shows irrelevant metrics (e.g., high coupling) when analyzing simple import errors
2. Generic analysis doesn't match specific error types
3. No contextual awareness of common fixes in the project

## Proposed Optimization: Error-Specific Analysis

### Error Type Handlers

```python
ERROR_STRATEGIES = {
    'ModuleNotFoundError': {
        'focus': ['project_structure', 'import_paths', 'installed_packages'],
        'skip': ['call_graph', 'coupling_metrics'],
        'show': [
            'File location in project tree',
            'Available modules at same level',
            'Common import patterns in project',
            'Is module in requirements.txt?'
        ]
    },
    'TypeError': {
        'focus': ['variable_types', 'method_signatures', 'type_conversions'],
        'skip': ['import_analysis'],
        'show': [
            'Variable assignments leading to error',
            'Expected vs actual types',
            'Common fixes for this type mismatch'
        ]
    },
    'AttributeError': {
        'focus': ['object_attributes', 'class_hierarchy'],
        'skip': ['general_metrics'],
        'show': [
            'Available attributes on object',
            'Similar attribute names (typos?)',
            'Class definition and inheritance'
        ]
    }
}
```

### Improved Prompt Structure

For ModuleNotFoundError:
```
## 🎯 Key Issues Identified
- ❌ Missing module: 'utils'
- 📁 Current file location: /proof_of_concept/logger_agent/src/arangodb/core/graph/
- 📦 Available at parent level: ../../../utils/

## Import Analysis
- Current import: `from utils.test_db_utils import ...`
- Suggested fix: `from ...utils.test_db_utils import ...`
- Project uses: Relative imports from src/

## Quick Fix Confidence: HIGH
This is a path issue, not a missing dependency.
```

### Context Awareness

1. **Project Patterns**: Learn common import styles, test patterns
2. **Previous Fixes**: Track what worked before for similar errors
3. **Environment Info**: Virtual env, PYTHONPATH, installed packages

### Benefits

1. **Relevant Analysis**: Only show metrics that matter for the error
2. **Faster Decisions**: Clear, actionable information
3. **Higher Success Rate**: Context-aware suggestions
4. **Less Noise**: Skip irrelevant complexity metrics

### Implementation Priority

1. **Phase 1**: Basic error type detection and routing
2. **Phase 2**: Error-specific analyzers for top 5 error types
3. **Phase 3**: Context learning from previous fixes
4. **Phase 4**: Integration with project-specific patterns

This would make the tool much more effective for actual debugging rather than just showing generic code metrics.