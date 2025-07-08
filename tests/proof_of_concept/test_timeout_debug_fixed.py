#!/usr/bin/env python3
"""Debug timeout estimation - with detailed breakdown."""
from executor import estimate_timeout

task = "Write a Python function that calculates fibonacci numbers"
print(f"Task: {task}")
print(f"Length: {len(task)}")

# Manual calculation
if len(task) < 50:
    base = 30
elif len(task) < 200:
    base = 60
else:
    base = 120

print(f"Base timeout: {base}s")

# Keywords
keywords = ['create', 'build', 'implement', 'design', 'develop', 'full', 'complete', 'comprehensive', 'test', 'suite']
keyword_count = sum(1 for kw in keywords if kw in task.lower())
print(f"Keywords found: {keyword_count}")
print(f"Keyword bonus: {keyword_count * 30}s")

# MCP overhead
mcp_overhead = 30
print(f"MCP overhead: {mcp_overhead}s")

# Total before Redis/cap
total = base + (keyword_count * 30) + mcp_overhead
print(f"Total before cap: {total}s")

# Now test the function
result = estimate_timeout(task)
print(f"\nActual result: {result}s")

# The issue is likely Redis returning a cached very low value!