#!/usr/bin/env python3
"""Simple test that returns JSON with test_id, status, and timestamp."""

import json
from datetime import datetime

def create_test_response():
    """Create a test response with the specified JSON structure."""
    response = {
        "test_id": "TEST_20250710_113508",
        "status": "success",
        "timestamp": "2025-07-10T11:35:08.630829"
    }
    return response

if __name__ == "__main__":
    result = create_test_response()
    print(json.dumps(result, indent=2))