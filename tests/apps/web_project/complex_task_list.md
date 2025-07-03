# Complex Task List for WebSocket Execution

## Overview
This task list includes more complex scenarios to thoroughly test cc_execute.md reliability and reach the 10:1 success ratio required for graduation.

---

## Task 4: Multi-Step Function Creation

Use your ./src/cc_executor/prompts/cc_execute.md to execute:
- Task: What is a Python function that calculates factorial recursively? Create a file factorial.py with a factorial function and a main block that tests it with factorial(5).
- Timeout: 60 seconds
- Success Criteria:
  1. File factorial.py exists
  2. Contains a function named factorial
  3. Running python3 factorial.py outputs 120
- Retry Strategy: Provide explicit recursive implementation details

## Task 5: Error Handling Test

Use your ./src/cc_executor/prompts/cc_execute.md to execute:
- Task: How do I handle division by zero in Python? Create a file safe_divide.py with a function that safely divides two numbers and returns None on error.
- Timeout: 45 seconds
- Success Criteria:
  1. File safe_divide.py exists
  2. Contains try/except block for ZeroDivisionError
  3. Function returns None when dividing by zero
- Retry Strategy: Show example with try/except ZeroDivisionError

## Task 6: File Processing Task

Use your ./src/cc_executor/prompts/cc_execute.md to execute:
- Task: What is a Python script that counts lines in a file? Create line_counter.py that counts lines in any text file passed as argument.
- Timeout: Redis estimate
- Success Criteria:
  1. File line_counter.py exists
  2. Uses sys.argv to get filename
  3. Handles FileNotFoundError gracefully
- Retry Strategy: Include argparse for better argument handling

## Task 7: JSON Data Processing

Use your ./src/cc_executor/prompts/cc_execute.md to execute:
- Task: How do I read and parse JSON in Python? Create json_reader.py that reads a JSON file and pretty prints it.
- Timeout: 50 seconds
- Success Criteria:
  1. File json_reader.py exists
  2. Imports json module
  3. Uses json.dumps with indent parameter
- Retry Strategy: Show complete example with sample JSON data

## Task 8: Environment Variable Check

Use your ./src/cc_executor/prompts/cc_execute.md to execute:
- Task: What Python code checks if an environment variable exists? Create env_checker.py that checks if PYTHONPATH is set and prints its value.
- Timeout: 30 seconds
- Success Criteria:
  1. File env_checker.py exists
  2. Uses os.environ.get()
  3. Handles case when variable is not set
- Retry Strategy: Use os.environ with default value