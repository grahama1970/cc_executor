#!/usr/bin/env python3
"""Debug the network error."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp_d3_visualization_advisor import _analyze_data_structure, _get_network_recommendations

# Test with network data
network_data = {
    "nodes": [{"id": "A"}, {"id": "B"}, {"id": "C"}],
    "links": [{"source": "A", "target": "B"}, {"source": "B", "target": "C"}]
}

try:
    network_analysis = _analyze_data_structure(network_data)
    print("Analysis completed:")
    print(json.dumps(network_analysis, indent=2))
    
    network_recs = _get_network_recommendations(network_analysis, network_data)
    print("\nRecommendations generated successfully")
    print(f"Length: {len(network_recs)}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()