#!/bin/bash
# Script to run TodoList unit tests

echo "Running TodoList unit tests..."
echo "=============================="

# Run tests with verbose output
python -m pytest test_todo_list.py -v

# Optional: Run with minimal output
# python -m pytest test_todo_list.py -q

# Optional: Run specific test class
# python -m pytest test_todo_list.py::TestTodoList -v

# Optional: Run specific test
# python -m pytest test_todo_list.py::TestTodoList::test_add_single_todo -v

echo ""
echo "To install coverage support:"
echo "  pip install pytest-cov"
echo ""
echo "Then run with coverage:"
echo "  python -m pytest test_todo_list.py --cov=todo_list --cov-report=term-missing"