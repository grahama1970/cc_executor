# Usage Function Response Saving Guide

## 📋 Current Status

### What's Already Done:
1. **Assessment Scripts** ✅
   - `core/ASSESS_ALL_CORE_USAGE.md` - Saves raw responses
   - `hooks/ASSESS_ALL_HOOKS_USAGE.md` - Saves raw responses
   - `cli/ASSESS_ALL_CLI_USAGE.md` - Saves raw responses

2. **Helper Module** ✅
   - `core/usage_helper.py` - Provides utilities for saving responses

3. **Template Updated** ✅
   - `templates/SELF_IMPROVING_PROMPT_TEMPLATE.md` - Shows pattern

### What Still Needs to Be Done:
1. **Individual Usage Functions** ❌
   - Most components don't save their raw outputs yet
   - This is critical for preventing AI hallucination

## 🎯 Why This Matters

When AI agents run usage functions, they may hallucinate the output if it's not saved. By saving raw responses:
- Agents can verify actual output vs claimed output
- Debugging is easier with saved responses
- Historical record of component behavior

## 💡 How to Implement

### Method 1: Using the Helper (Recommended)

```python
if __name__ == "__main__":
    from usage_helper import capture_usage_output
    
    with capture_usage_output(__file__) as capture:
        print("=== Component Usage Example ===")
        
        # Your usage code here
        result = some_function()
        capture.add_result('key', result)
        print(f"Result: {result}")
        
        print("✅ Usage example completed")
    
    # Output is automatically saved and location printed
```

### Method 2: Manual Implementation

```python
if __name__ == "__main__":
    import json
    from pathlib import Path
    from datetime import datetime
    
    # Create responses directory
    responses_dir = Path(__file__).parent / "tmp" / "responses"
    responses_dir.mkdir(parents=True, exist_ok=True)
    
    # Collect output
    output_lines = []
    
    # Run usage example
    output_lines.append("=== Component Usage Example ===")
    result = some_function()
    output_lines.append(f"Result: {result}")
    
    # Save raw response
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = Path(__file__).stem
    
    # Save as JSON
    response_file = responses_dir / f"{filename}_{timestamp}.json"
    with open(response_file, 'w') as f:
        json.dump({
            'filename': filename,
            'timestamp': timestamp,
            'output': '\n'.join(output_lines),
            'result': result
        }, f, indent=2)
    
    # Print output
    print('\n'.join(output_lines))
    print(f"\n💾 Raw response saved to: {response_file.relative_to(Path.cwd())}")
```

## 📁 Directory Structure

Each directory should have:
```
component_dir/
├── tmp/
│   └── responses/
│       ├── component_name_TIMESTAMP.json  # Structured data
│       └── component_name_TIMESTAMP.txt   # Plain text
```

## 🔄 Migration Plan

1. **High Priority** (Most used components):
   - `websocket_handler.py`
   - `process_manager.py`
   - `session_manager.py`
   - `hook_integration.py`

2. **Medium Priority**:
   - All other core components
   - All hooks

3. **Low Priority**:
   - Helper scripts
   - Test utilities

## ✅ Verification

To verify a component saves responses:
```bash
# Run the component
python component.py

# Check for saved response
ls tmp/responses/component_*

# View the saved response
cat tmp/responses/component_*.json
```

## 🚨 Important Notes

1. **Don't Break Existing Functionality**
   - Add response saving without changing behavior
   - Ensure all tests still pass

2. **Keep It Simple**
   - Use the helper for consistency
   - Don't overcomplicate the implementation

3. **Clean Output**
   - Save exactly what was printed
   - Don't add extra formatting in saved files

4. **Error Handling**
   - If saving fails, don't crash the usage function
   - Continue with normal output

This guide ensures all components will save their raw responses, preventing AI hallucination and improving debugging capabilities.