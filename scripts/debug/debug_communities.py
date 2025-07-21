#!/usr/bin/env python3
"""Debug community detection issue"""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from cc_executor.servers.mcp_arango_tools import detect_communities

async def debug_function():
    """Test community detection directly"""
    print("Testing community detection...")
    
    try:
        result = await detect_communities(
            edge_collection="error_similarity",
            algorithm="louvain", 
            min_community_size=3,
            resolution=1.2
        )
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_function())