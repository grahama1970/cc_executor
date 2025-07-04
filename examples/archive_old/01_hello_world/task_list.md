# Hello World Example

The simplest possible cc_executor example. Creates a function and tests it.

## Setup

```bash
cd /home/graham/workspace/experiments/cc_executor
source .venv/bin/activate
```

## Tasks

### Task 1: Create a Hello Function

What function returns a greeting with a name? Create `hello.py` with a function `greet(name)` that returns "Hello, {name}!" and include a main block that tests it with the name "World".

### Task 2: Test the Function

How can I verify the hello function works correctly? Read `hello.py` and create `test_hello.py` with pytest tests that verify greet() returns the expected format for different names including edge cases like empty strings.

## Expected Results

After execution:
- `hello.py` - Function implementation
- `test_hello.py` - Comprehensive tests
- Both files work correctly when run

## Why This Example?

Shows the fundamental cc_executor concept:
1. Task 1 creates a file
2. Task 2 reads that file and builds on it
3. Each runs in fresh context with full attention