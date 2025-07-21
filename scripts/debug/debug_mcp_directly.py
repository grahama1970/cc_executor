#!/usr/bin/env python3
"""
Direct MCP Debugging Tool - Bypasses uv script isolation

This tool helps debug MCP servers by:
1. Running them in our current environment (not uv isolated)
2. Capturing ALL output (stdout, stderr)
3. Showing exactly what errors occur
4. Testing if the MCP tools are actually callable
"""

import sys
import os
import subprocess
import json
import asyncio
from pathlib import Path
from datetime import datetime

# Add src to path so we can import directly
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_mcp_server_directly(server_name: str):
    """Test an MCP server by importing it directly, bypassing uv script."""
    print(f"\n{'='*60}")
    print(f"Testing {server_name} MCP Server DIRECTLY (no uv isolation)")
    print(f"{'='*60}\n")
    
    # Step 1: Test if we can import the module at all
    print("Step 1: Testing direct import...")
    try:
        if server_name == "arango-tools":
            from cc_executor.servers.mcp_arango_tools import ArangoTools
            print("✅ Import successful!")
            
            # Step 2: Test initialization
            print("\nStep 2: Testing initialization...")
            # Use _system database for testing
            os.environ["ARANGO_DATABASE"] = "_system"
            
            tools = ArangoTools()
            print("✅ ArangoTools instance created!")
            
            # Step 3: Test if methods work
            print("\nStep 3: Testing methods...")
            
            # Test schema
            try:
                result = tools.schema()
                print(f"✅ schema() works: {len(result.get('collections', []))} collections")
            except Exception as e:
                print(f"❌ schema() failed: {e}")
                
            # Test query
            try:
                result = tools.execute_aql("RETURN 1")
                print(f"✅ execute_aql() works: {result}")
            except Exception as e:
                print(f"❌ execute_aql() failed: {e}")
                
            print("\n✅ Server appears functional!")
            
        elif server_name == "logger-tools":
            from cc_executor.servers.mcp_debugging_assistant import LoggerTools
            print("✅ Import successful!")
            # Add more tests for other servers
            
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    except Exception as e:
        print(f"❌ Runtime error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    return True


def test_mcp_with_uv(server_path: str):
    """Test MCP server using uv to see what happens."""
    print(f"\n{'='*60}")
    print(f"Testing with UV command (isolated environment)")
    print(f"{'='*60}\n")
    
    # Run with uv
    cmd = [
        "uv", "run", "--script", 
        server_path, "test"
    ]
    
    print(f"Command: {' '.join(cmd)}")
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env={**os.environ, "ARANGO_DATABASE": "_system"}
    )
    
    print(f"\nExit code: {result.returncode}")
    
    if result.stdout:
        print("\nSTDOUT:")
        print(result.stdout)
        
    if result.stderr:
        print("\nSTDERR:")
        print(result.stderr)
        
    return result.returncode == 0


def compare_approaches(server_name: str):
    """Compare direct import vs uv script approach."""
    server_path = f"src/cc_executor/servers/mcp_{server_name.replace('-', '_')}.py"
    
    print(f"\n{'='*70}")
    print(f"DEBUGGING MCP SERVER: {server_name}")
    print(f"{'='*70}")
    
    # Test direct import
    direct_works = test_mcp_server_directly(server_name)
    
    # Test with uv
    if os.path.exists(server_path):
        uv_works = test_mcp_with_uv(server_path)
    else:
        print(f"\n❌ Server file not found: {server_path}")
        uv_works = False
        
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY:")
    print(f"  Direct import: {'✅ Works' if direct_works else '❌ Failed'}")
    print(f"  UV script:     {'✅ Works' if uv_works else '❌ Failed'}")
    
    if direct_works and not uv_works:
        print("\n⚠️  Server works directly but fails with uv script!")
        print("  This suggests an environment/dependency issue with uv isolation")
    elif not direct_works:
        print("\n⚠️  Server fails even with direct import!")
        print("  Fix the import/initialization issues first")
        
    print(f"{'='*60}\n")


def create_simplified_mcp_server(server_name: str):
    """Create a simplified version without uv script header for easier debugging."""
    original_path = Path(f"src/cc_executor/servers/mcp_{server_name.replace('-', '_')}.py")
    simplified_path = Path(f"src/cc_executor/servers/mcp_{server_name.replace('-', '_')}_debug.py")
    
    if not original_path.exists():
        print(f"❌ Original server not found: {original_path}")
        return
        
    with open(original_path, 'r') as f:
        content = f.read()
        
    # Remove uv script header
    if content.startswith('#!/usr/bin/env -S uv run --script'):
        lines = content.split('\n')
        # Find where the docstring starts (after # ///)
        for i, line in enumerate(lines):
            if line.strip() == '# ///':
                # Skip to after the closing # ///
                for j in range(i+1, len(lines)):
                    if lines[j].strip() == '# ///':
                        # Found closing, start from next line
                        simplified_content = '#!/usr/bin/env python3\n' + '\n'.join(lines[j+1:])
                        break
                break
        else:
            # Couldn't find proper markers, just remove shebang
            simplified_content = '#!/usr/bin/env python3\n' + '\n'.join(lines[1:])
            
        with open(simplified_path, 'w') as f:
            f.write(simplified_content)
            
        os.chmod(simplified_path, 0o755)
        print(f"✅ Created simplified version: {simplified_path}")
        print("   This version can be run directly with python for easier debugging")
    else:
        print("ℹ️  Server doesn't use uv script header")


if __name__ == "__main__":
    # Test arango-tools
    compare_approaches("arango-tools")
    
    # Create simplified version for debugging
    create_simplified_mcp_server("arango-tools")
    
    print("\nSUGGESTIONS:")
    print("1. Use the simplified debug version for testing")
    print("2. Once working, update the original with fixes")
    print("3. Consider removing uv script headers from MCP servers")
    print("   (Use regular Python files with requirements in pyproject.toml)")