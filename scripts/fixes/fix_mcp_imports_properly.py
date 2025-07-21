#!/usr/bin/env python3
"""Fix all MCP servers to be self-contained by inlining MCPLogger."""

import re
from pathlib import Path

def fix_mcp_server(filepath: Path):
    """Fix a single MCP server file."""
    print(f"Processing {filepath.name}...")
    
    content = filepath.read_text()
    
    # Check if already has the inline MCPLogger
    if "class MCPLogger:" in content:
        print(f"  ✓ Already has MCPLogger inline")
        
        # Just check for missing imports
        lines = content.split('\n')
        
        # Find where imports are
        import_end = 0
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith(('import ', 'from ', '#', '"""')) and i > 15:
                import_end = i
                break
        
        # Add missing imports before the class
        new_imports = []
        if 'from typing import Any' not in content and ', Any' not in content:
            new_imports.append('from typing import Any')
        if 'import os' not in content:
            new_imports.append('import os')
        if 'import json' not in content:
            new_imports.append('import json')
        
        if new_imports:
            # Find MCPLogger class
            for i, line in enumerate(lines):
                if line.strip() == "class MCPLogger:":
                    # Insert imports before the class
                    for imp in reversed(new_imports):
                        lines.insert(i, imp)
                    lines.insert(i + len(new_imports), "")
                    break
            
            filepath.write_text('\n'.join(lines))
            print(f"  ✓ Added missing imports")
        
        return
    
    print(f"  No inline MCPLogger found - skipping")

def main():
    """Fix all MCP servers."""
    servers_dir = Path("src/cc_executor/servers")
    
    # List of files to fix
    files_to_fix = [
        "mcp_d3_visualizer.py",
        "mcp_kilocode_review.py", 
        "mcp_logger_tools.py",
        "mcp_tool_journey.py",
        "mcp_tool_sequence_optimizer.py"
    ]
    
    for filename in files_to_fix:
        filepath = servers_dir / filename
        if filepath.exists():
            fix_mcp_server(filepath)

if __name__ == "__main__":
    main()