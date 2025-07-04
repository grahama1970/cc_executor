# Blog Platform Development - Task List with Hooks

## Overview

This example demonstrates the complete cc_executor task list lifecycle with pre-flight checks and post-execution reports. It builds a simple blog platform API to showcase sequential task dependencies and comprehensive verification.

## Setup Task

**Always run this first to prepare the environment:**

```bash
# Activate virtual environment
source .venv/bin/activate

# Navigate to project root
cd /home/graham/workspace/experiments/cc_executor

# Create and run setup
cat > setup_blog_platform.py << 'EOF'
from pathlib import Path
import sys

# Find project root
current = Path.cwd()
while current.parent != current:
    if (current / "pyproject.toml").exists():
        PROJECT_ROOT = current
        break
    current = current.parent
else:
    PROJECT_ROOT = Path.cwd()

# Add to path
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

# Read and customize setup template
template_path = PROJECT_ROOT / 'src/cc_executor/prompts/setup_template.py'
with open(template_path, 'r') as f:
    setup_code = f.read()

setup_code = setup_code.replace('PLACEHOLDER_TASK_LIST_NAME', 'Blog Platform Development')

# Write and execute
with open('setup_env.py', 'w') as f:
    f.write(setup_code)

exec(open('setup_env.py').read())

# Create project structure
blog_dir = Path("blog_platform")
blog_dir.mkdir(exist_ok=True)
(blog_dir / "app").mkdir(exist_ok=True)
(blog_dir / "tests").mkdir(exist_ok=True)

print(f"\n✅ Blog platform directories created at: {blog_dir.absolute()}")
EOF

python setup_blog_platform.py
```

## Task List

### Task 1: Create Database Models
**Description**: What database models are needed for a blog platform? Create blog_platform/app/models.py with SQLAlchemy models for User (id, username, email, created_at) and Post (id, title, content, author_id, created_at, updated_at).

**Complexity**: 2.5
**Estimated Duration**: 30s

### Task 2: Create FastAPI Application
**Description**: How do I create a FastAPI application for the blog? Read blog_platform/app/models.py and create blog_platform/app/main.py with FastAPI app initialization, database setup, and CORS middleware configuration.

**Complexity**: 2.8
**Estimated Duration**: 45s

### Task 3: Implement User Endpoints
**Description**: What REST endpoints are needed for user management? Read existing files in blog_platform/app/ and create blog_platform/app/routers/users.py with POST /users (create user), GET /users/{id} (get user), and GET /users (list users) endpoints.

**Complexity**: 3.2
**Estimated Duration**: 60s

### Task 4: Implement Post Endpoints
**Description**: How can I add blog post functionality? Read the models and existing routers, then create blog_platform/app/routers/posts.py with full CRUD endpoints: POST /posts, GET /posts, GET /posts/{id}, PUT /posts/{id}, DELETE /posts/{id}.

**Complexity**: 3.5
**Estimated Duration**: 75s

### Task 5: Add Authentication Middleware
**Description**: What authentication should protect the blog endpoints? Read all files in blog_platform/app/ and create blog_platform/app/auth.py with JWT token generation and validation middleware that protects POST, PUT, and DELETE operations.

**Complexity**: 4.0
**Estimated Duration**: 90s

### Task 6: Write Integration Tests
**Description**: How do I test the blog API endpoints? Read all files in blog_platform/app/ and create blog_platform/tests/test_api.py with pytest tests covering user creation, post CRUD operations, and authentication flows.

**Complexity**: 3.8
**Estimated Duration**: 80s

### Task 7: Create API Documentation
**Description**: What documentation is needed for the blog API? Read all source files and create blog_platform/API_DOCS.md with endpoint descriptions, request/response examples, authentication details, and usage instructions.

**Complexity**: 2.2
**Estimated Duration**: 40s

## Pre-Flight Check Configuration

Before execution, the `task_list_preflight_check.py` hook will:
- Calculate total complexity: ~23.5 (HIGH)
- Predict success rate based on sequential complexity
- Identify Tasks 5 & 6 as high-risk
- Recommend timeout adjustments
- Verify environment readiness

## Post-Execution Report Configuration

After execution, the `task_list_completion_report.py` hook will generate:
- Complete execution metrics
- Raw JSON output for each task
- File creation verification
- Cross-task dependency validation
- System health assessment

## Execution Commands

### Run Pre-Flight Check Only
```bash
export CLAUDE_FILE="examples/advanced/blog_platform/task_list_with_hooks.md"
python src/cc_executor/hooks/task_list_preflight_check.py
```

### Execute Task List with cc_execute.md
```python
from pathlib import Path
import sys

# Add to path
sys.path.insert(0, 'src')

from cc_executor.prompts.cc_execute_utils import execute_task_via_websocket
import json
from datetime import datetime

# Task definitions
tasks = [
    {
        'num': 1,
        'desc': "What database models are needed for a blog platform? Create blog_platform/app/models.py with SQLAlchemy models for User (id, username, email, created_at) and Post (id, title, content, author_id, created_at, updated_at).",
        'timeout': 60
    },
    {
        'num': 2,
        'desc': "How do I create a FastAPI application for the blog? Read blog_platform/app/models.py and create blog_platform/app/main.py with FastAPI app initialization, database setup, and CORS middleware configuration.",
        'timeout': 90
    },
    {
        'num': 3,
        'desc': "What REST endpoints are needed for user management? Read existing files in blog_platform/app/ and create blog_platform/app/routers/users.py with POST /users (create user), GET /users/{id} (get user), and GET /users (list users) endpoints.",
        'timeout': 120
    },
    {
        'num': 4,
        'desc': "How can I add blog post functionality? Read the models and existing routers, then create blog_platform/app/routers/posts.py with full CRUD endpoints: POST /posts, GET /posts, GET /posts/{id}, PUT /posts/{id}, DELETE /posts/{id}.",
        'timeout': 120
    },
    {
        'num': 5,
        'desc': "What authentication should protect the blog endpoints? Read all files in blog_platform/app/ and create blog_platform/app/auth.py with JWT token generation and validation middleware that protects POST, PUT, and DELETE operations.",
        'timeout': 150
    },
    {
        'num': 6,
        'desc': "How do I test the blog API endpoints? Read all files in blog_platform/app/ and create blog_platform/tests/test_api.py with pytest tests covering user creation, post CRUD operations, and authentication flows.",
        'timeout': 120
    },
    {
        'num': 7,
        'desc': "What documentation is needed for the blog API? Read all source files and create blog_platform/API_DOCS.md with endpoint descriptions, request/response examples, authentication details, and usage instructions.",
        'timeout': 90
    }
]

# Execute each task
results = []
for task in tasks:
    print(f"\n{'='*60}")
    print(f"Executing Task {task['num']}: {task['desc'][:50]}...")
    print(f"{'='*60}")
    
    result = execute_task_via_websocket(
        task=task['desc'],
        timeout=task['timeout'],
        tools=["Read", "Write", "Edit"]
    )
    
    # Save individual result
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = Path(f"tmp/responses/task_{task['num']}_result_{timestamp}.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    results.append({
        'task_num': task['num'],
        'status': result.get('status', 'unknown'),
        'duration': result.get('duration', 0),
        'output_file': str(output_file)
    })
    
    print(f"✅ Task {task['num']} completed with status: {result.get('status')}")

# Summary
print(f"\n{'='*60}")
print("EXECUTION SUMMARY")
print(f"{'='*60}")
for r in results:
    print(f"Task {r['task_num']}: {r['status']} ({r['duration']:.1f}s)")

# Trigger post-execution report
import os
os.environ['CLAUDE_TASK_LIST_FILE'] = 'examples/advanced/blog_platform/task_list_with_hooks.md'
os.system('python src/cc_executor/hooks/task_list_completion_report.py')
```

### Generate Final Report
```bash
export CLAUDE_TASK_LIST_FILE="examples/advanced/blog_platform/task_list_with_hooks.md"
export CLAUDE_SESSION_ID="blog_platform_$(date +%s)"
python src/cc_executor/hooks/task_list_completion_report.py
```

## Expected Outputs

### Pre-Flight Assessment
```
======================================================================
TASK LIST PRE-FLIGHT ASSESSMENT
======================================================================

📊 SUMMARY
Total Tasks: 7
Average Complexity: 3.4/5.0
Predicted Success Rate: 42.3%
Overall Risk: HIGH
Estimated Time: 8 minutes
Should Proceed: ✅ YES (with cautions)

⚠️  HIGH RISK TASKS: [5, 6]

💡 RECOMMENDATIONS
→ Consider breaking down Task 5 (Authentication) into smaller steps
→ Add explicit verification steps between tasks
→ Monitor Task 6 closely - complex test generation
```

### Post-Execution Report Structure

Each task will have:
1. **Execution metrics** (status, duration, exit code)
2. **Complete raw JSON** with full output
3. **Agent assessment placeholder** for manual review
4. **Evidence of completion** (files created, tests passed)

### Final Verification

After execution, verify the blog platform works:
```bash
# Check created files
find blog_platform -type f -name "*.py" | sort

# Run the API
cd blog_platform
uvicorn app.main:app --reload

# Run tests
pytest tests/test_api.py -v
```

## Benefits of This Pattern

1. **Pre-Flight Checks**
   - Catch high-risk tasks before wasting execution time
   - Get timeout recommendations
   - Understand complexity distribution

2. **Structured Execution**
   - Sequential dependencies handled properly
   - Each task builds on previous outputs
   - Clear success criteria

3. **Comprehensive Reports**
   - Raw output prevents hallucination
   - Agent can verify claims vs reality
   - Complete audit trail

4. **Quality Assurance**
   - Every file creation verified
   - Cross-task validation
   - Honest confidence assessment

This example proves cc_executor can handle complex, multi-step development tasks with full accountability and verification at every stage.