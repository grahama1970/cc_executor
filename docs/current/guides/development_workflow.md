# O3-Claude Review Workflow & Directory Structure

## Optimal Directory Structure

```
src/cc_executor/
├── development/              # Active development work
│   ├── current/             # Current implementation being worked on
│   │   ├── prompt.md        # Self-improving prompt
│   │   ├── implementation.py # Code implementation
│   │   └── usage_test.py    # Standalone usage tests
│   └── archive/             # Previous iterations
│       └── T01_v1/         # Archived versions
│
├── reviews/                 # O3 review cycle
│   ├── pending/            # Awaiting O3 review
│   │   └── T01_robust_logging/
│   │       ├── prompt.md
│   │       ├── implementation.py
│   │       └── review_request.md
│   ├── in_review/          # Currently being reviewed by O3
│   └── completed/          # Reviewed with feedback
│       └── T01_robust_logging/
│           ├── O3_REVIEW_001.md      # O3's feedback
│           ├── fix_tasks.json        # Structured fix tasks
│           └── original_files/       # Pre-review versions
│
├── tasks/                   # Task management
│   ├── backlog/            # New tasks from O3 reviews
│   │   └── T01_fixes_001.json
│   ├── in_progress/        # Currently being fixed
│   └── completed/          # Completed fixes
│
├── production/             # Graduated code (10:1 ratio achieved)
│   ├── core/              # Production implementations
│   │   └── implementation.py
│   └── modules/           # Graduated task modules
│       ├── T01_robust_logging.py
│       └── T02_backpressure_handling.py
│
├── templates/              # Workflow templates
│   ├── REVIEW_REQUEST_TEMPLATE.md
│   ├── O3_REVIEW_CONTEXT.md
│   └── FIX_TASK_TEMPLATE.json
│
└── metrics/               # Performance tracking
    ├── review_cycles.json  # Track review iterations
    └── success_metrics.json # Gamification metrics
```

## Workflow Steps

### 1. Development Phase (Claude)
```bash
# Start new implementation
cd development/current/
# Create prompt.md following SELF_IMPROVING_PROMPT_TEMPLATE
# Create implementation.py
# Test with usage functions
python implementation.py
```

### 2. Submit for Review
```bash
# Move to pending review
./scripts/submit_for_review.sh T01_robust_logging

# This script:
# 1. Copies files to reviews/pending/T01_robust_logging/
# 2. Creates review_request.md with context
# 3. Runs pre-review checks
# 4. Updates metrics/review_cycles.json
```

### 3. O3 Review Process
O3 receives:
- `reviews/pending/T01_robust_logging/review_request.md`
- All associated files
- Context from templates

O3 outputs:
- `O3_REVIEW_001.md` - Detailed feedback
- `fix_tasks.json` - Structured tasks

### 4. Process Review Feedback
```bash
# Process O3 feedback
./scripts/process_review.sh T01_robust_logging

# This script:
# 1. Moves review to completed/
# 2. Parses fix_tasks.json
# 3. Creates individual task files in tasks/backlog/
# 4. Updates TodoWrite with new tasks
```

### 5. Fix Implementation (Claude)
```bash
# Work on fixes
cd development/current/
# Pick task from tasks/backlog/
# Implement fixes
# Update evolution history
# Run tests
```

### 6. Re-submit or Graduate
```bash
# If more fixes needed
./scripts/submit_for_review.sh T01_robust_logging --revision 2

# If 10:1 ratio achieved
./scripts/graduate_to_production.sh T01_robust_logging
```

## Fix Task Format

`fix_tasks.json`:
```json
{
  "review_id": "O3_REVIEW_001",
  "component": "T01_robust_logging",
  "review_date": "2025-06-25",
  "severity_counts": {
    "critical": 2,
    "major": 3,
    "minor": 5
  },
  "tasks": [
    {
      "id": "T01_FIX_001",
      "severity": "critical",
      "file": "implementation.py",
      "line": 45,
      "issue": "Missing error handling for WebSocket disconnect",
      "fix": "Add try-except block with proper cleanup",
      "verification": "Test with abrupt connection termination"
    }
  ]
}
```

## Automation Scripts

### submit_for_review.sh
```bash
#!/bin/bash
COMPONENT=$1
REVISION=${2:-1}

# Create review package
mkdir -p reviews/pending/$COMPONENT
cp development/current/* reviews/pending/$COMPONENT/

# Generate review request
cat > reviews/pending/$COMPONENT/review_request.md << EOF
# Review Request: $COMPONENT (Revision $REVISION)
Date: $(date -I)
Requester: Claude Opus

## Files for Review
- prompt.md
- implementation.py

## Context
$(cat templates/O3_REVIEW_CONTEXT.md)

## Previous Reviews
$(find reviews/completed/$COMPONENT -name "O3_REVIEW_*.md" | wc -l) previous reviews

## Testing Instructions
\`\`\`bash
cd reviews/pending/$COMPONENT
python implementation.py
\`\`\`
EOF

echo "✅ Submitted $COMPONENT for review (revision $REVISION)"
```

### process_review.sh
```bash
#!/bin/bash
COMPONENT=$1

# Parse O3's fix tasks
python scripts/parse_o3_review.py \
  reviews/in_review/$COMPONENT/fix_tasks.json \
  --output tasks/backlog/

# Update metrics
python scripts/update_review_metrics.py $COMPONENT

# Move to completed
mv reviews/in_review/$COMPONENT reviews/completed/

echo "✅ Processed O3 review for $COMPONENT"
echo "📋 New tasks created in tasks/backlog/"
```

## Benefits of This Structure

1. **Clear Separation**: Development, review, and production are separate
2. **Version History**: Archive keeps all iterations
3. **Task Tracking**: Structured JSON tasks from O3 reviews
4. **Automation**: Scripts handle repetitive workflow steps
5. **Metrics**: Track review cycles and success rates
6. **No Confusion**: Always know what's being worked on vs reviewed

## Quick Commands

```bash
# Check current work
ls development/current/

# See pending reviews
ls reviews/pending/

# Check backlog from O3
cat tasks/backlog/*.json | jq '.tasks[] | select(.severity=="critical")'

# Graduate to production
./scripts/graduate_to_production.sh T01_robust_logging
```

This workflow ensures smooth collaboration between O3 (reviewer) and Claude (implementer) with clear handoffs and tracking.