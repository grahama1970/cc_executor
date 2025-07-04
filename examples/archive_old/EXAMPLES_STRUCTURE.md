# Examples Directory Structure

## Current Issues
- Too many variations of the same example
- Confusing nested directories (todo_api/todo_api)
- Mix of setup scripts and task lists in same directory
- No clear progression from simple to complex

## Proposed Clean Structure

```
examples/
├── README.md                    # Overview and guide
├── 01_simple_hello/            # Simplest possible example
│   ├── task_list.md           # Single task: create hello.py
│   └── README.md              # What this demonstrates
│
├── 02_sequential_tasks/        # Show task dependencies
│   ├── task_list.md           # 3 tasks that build on each other
│   └── README.md              # Explains sequential execution
│
├── 03_todo_api/               # Complete API example
│   ├── task_list.md           # The canonical todo API tasks
│   ├── setup.py               # Environment setup
│   └── README.md              # Full explanation
│
├── 04_with_hooks/             # Demonstrate hooks
│   ├── task_list.md           # Tasks with pre/post hooks
│   ├── .claude-hooks.json     # Hook configuration
│   └── README.md              # Hook benefits
│
├── 05_self_improving/         # Advanced pattern
│   ├── task_list.md           # Self-improving task list
│   └── README.md              # Evolution tracking
│
└── archive/                   # Old examples for reference
    └── ...
```

## Key Principles

1. **One Canonical Example Per Concept**
   - Not 5 versions of todo_api
   - Clear progression of complexity

2. **Self-Contained Directories**
   - Each example in its own directory
   - No nested project folders
   - Generated files go in .gitignored output/

3. **Clear Purpose**
   - Each example demonstrates ONE concept
   - README explains what you'll learn

4. **No Pollution**
   - setup.py creates tmp/ and output/ directories
   - All generated files go there
   - Easy to clean up

## What Each Example Shows

### 01_simple_hello
- Basic task execution
- File creation verification
- Simplest possible cc_execute usage

### 02_sequential_tasks
- Task dependencies
- Using output from previous tasks
- Why cc_execute is valuable

### 03_todo_api
- Real-world API development
- Multiple file creation
- Testing included

### 04_with_hooks
- Pre-flight assessment
- Post-execution reports
- Quality assurance

### 05_self_improving
- Task evolution
- Metric tracking
- Continuous improvement

## Migration Plan

1. Keep current examples working
2. Create new clean structure
3. Move best examples to new structure
4. Archive the rest
5. Update documentation to reference new structure