#!/usr/bin/env python3
"""Debug the shape structure."""

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

analysis = _analyze_data_structure(test_data)

print("Analysis shape:")
print(json.dumps(analysis['shape'], indent=2))