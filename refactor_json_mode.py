#!/usr/bin/env python
"""Refactor return_json to json_mode throughout the codebase."""

import re
from pathlib import Path

def refactor_file(file_path):
    """Refactor a single file."""
    print(f"\nProcessing {file_path}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Track changes
    changes = []
    
    # 1. Update function signatures
    # cc_execute signature
    pattern = r'(async def cc_execute\([^)]+)return_json: bool = False,'
    replacement = r'\1json_mode: bool = False,\n    return_json: Optional[bool] = None,  # Deprecated - use json_mode'
    content, n = re.subn(pattern, replacement, content)
    if n: changes.append(f"Updated cc_execute signature ({n} occurrence)")
    
    # cc_execute_list signature
    pattern = r'(async def cc_execute_list\([^)]+)return_json: bool = False,'
    replacement = r'\1json_mode: bool = False,\n    return_json: Optional[bool] = None,  # Deprecated'
    content, n = re.subn(pattern, replacement, content)
    if n: changes.append(f"Updated cc_execute_list signature ({n} occurrence)")
    
    # 2. Update docstrings
    content = content.replace(
        "return_json: If True, parse output as JSON and return dict",
        "json_mode: If True, parse output as JSON and return dict (industry standard naming)\n        return_json: Deprecated - use json_mode instead"
    )
    
    content = content.replace(
        "Complete output from Claude (str if return_json=False, dict if return_json=True)",
        "Complete output from Claude (str if json_mode=False, dict if json_mode=True)"
    )
    
    # 3. Add backward compatibility check after docstring
    # Find the start of cc_execute function body
    if "async def cc_execute(" in content:
        # Insert compatibility check after the docstring
        pattern = r'(async def cc_execute\([^)]+\)[^:]+:\s*"""[^"]*"""\s*)'
        replacement = r'\1\n    # Handle backward compatibility\n    if return_json is not None:\n        logger.warning("Parameter \'return_json\' is deprecated, use \'json_mode\' instead")\n        json_mode = return_json\n    '
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # 4. Replace usage of return_json with json_mode in function bodies
    # But NOT in function calls (those need different handling)
    
    # Replace standalone checks
    content = re.sub(r'\n(\s+)if return_json:\n', r'\n\1if json_mode:\n', content)
    
    # Replace in string formatting
    content = content.replace("{return_json}", "{json_mode}")
    content = content.replace("- JSON Mode: {return_json}", "- JSON Mode: {json_mode}")
    
    # Replace in conditionals with 'and'
    content = re.sub(r'if return_json and ', r'if json_mode and ', content)
    
    # 5. Update function calls
    # Simple calls
    content = re.sub(r'return_json=True\b', r'json_mode=True', content)
    content = re.sub(r'return_json=False\b', r'json_mode=False', content)
    content = re.sub(r'return_json=return_json\b', r'json_mode=json_mode', content)
    
    # Calls passing variables
    pattern = r'cc_execute\(([^,]+), ([^,]+), return_json=([^,\)]+)'
    replacement = r'cc_execute(\1, \2, json_mode=\3'
    content = re.sub(pattern, replacement, content)
    
    # Save if changed
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"✓ Updated {file_path}")
        for change in changes:
            print(f"  - {change}")
        return True
    else:
        print(f"  No changes needed")
        return False

def main():
    """Main refactoring function."""
    print("Refactoring return_json to json_mode...")
    
    # Files to refactor
    files_to_check = [
        "src/cc_executor/client/cc_execute.py",
        "src/cc_executor/core/executor.py",
        "src/cc_executor/utils/prompt_amender.py",
        "src/cc_executor/client/README.md",
        "TEST_SIMPLE_PROMPT.py"
    ]
    
    updated_files = []
    
    for file_path in files_to_check:
        if Path(file_path).exists():
            if refactor_file(file_path):
                updated_files.append(file_path)
        else:
            print(f"✗ File not found: {file_path}")
    
    print(f"\n✅ Refactoring complete! Updated {len(updated_files)} files:")
    for f in updated_files:
        print(f"  - {f}")

if __name__ == "__main__":
    main()