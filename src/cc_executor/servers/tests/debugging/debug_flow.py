#!/usr/bin/env python3
"""Debug the data flow."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp_d3_visualization_advisor import _analyze_data_structure

# Test data
test_data = [
    {"category": "A", "value": 100},
    {"category": "B", "value": 150},
]

print(f"Input data type: {type(test_data)}")
print(f"Is list: {isinstance(test_data, list)}")
print(f"All dicts: {all(isinstance(item, dict) for item in test_data)}")
print(f"Data: {test_data}")

analysis = _analyze_data_structure(test_data)

print(f"\nFull analysis:")
print(json.dumps(analysis, indent=2, default=str))