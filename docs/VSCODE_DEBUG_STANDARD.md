# VSCode Debug Standard

## New Requirement

Every major Python script MUST have a simple, direct `if __name__ == "__main__"` block that:

1. **Starts immediately** - No argument parsing for basic operation
2. **No test code** - Tests belong in separate test files
3. **Clear output** - Shows what's happening when run
4. **Debug friendly** - Can set breakpoints and step through

## Example Template

```python
if __name__ == "__main__":
    """
    Direct debug entry point for VSCode.
    
    VSCode Debug:
        1. Set breakpoints anywhere in this file
        2. Press F5 (or Run > Start Debugging)
        3. The code will run with your breakpoints
    """
    print("=" * 60)
    print("Module Name Debug Mode")
    print("=" * 60)
    
    # Simple initialization
    handler = MyHandler()
    
    # Run the main functionality
    print("Starting...")
    handler.run()
    print("Complete!")
```

## For Async Code (asyncio)

```python
if __name__ == "__main__":
    """
    Direct debug entry point for VSCode.
    
    VSCode Debug:
        1. Set breakpoints anywhere in this file
        2. Press F5 (or Run > Start Debugging)
        3. The server will start
    """
    import asyncio
    
    print("=" * 60)
    print("Async Module Debug Mode")
    print("=" * 60)
    
    # All async code goes in main()
    async def main():
        # Initialize async components
        server = AsyncServer()
        
        # Run async operations
        print("Starting async server...")
        await server.serve()
    
    # Only ONE asyncio.run() at the very end
    asyncio.run(main())
```

## VSCode Setup

1. **Simple launch.json** - Just one config that works:
```json
{
    "name": "Python: Current File",
    "type": "python",
    "request": "launch",
    "program": "${file}",
    "console": "integratedTerminal",
    "justMyCode": false
}
```

2. **Usage**:
   - Open any Python file
   - Set breakpoints with F9
   - Press F5 to debug
   - That's it!

## What NOT to Do

❌ **Don't require arguments**:
```python
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", required=True)  # BAD
```

❌ **Don't include test code**:
```python
if __name__ == "__main__":
    run_unit_tests()  # BAD - tests go in test files
```

❌ **Don't make it complex**:
```python
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "debug":  # BAD
        # Too complex
```

## What TO Do

✅ **Start immediately**:
```python
if __name__ == "__main__":
    server = Server()
    server.run()  # GOOD - just runs
```

✅ **Show progress**:
```python
if __name__ == "__main__":
    print("Starting server on port 8000...")
    server = Server(port=8000)
    server.run()
```

✅ **Use environment variables for config**:
```python
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    
    print(f"Starting server on port {port} (debug={debug})")
    server = Server(port=port, debug=debug)
    server.run()
```

## Benefits

1. **Instant debugging** - Open file, press F5
2. **No documentation needed** - Code explains itself
3. **Consistent** - Every file works the same way
4. **Simple** - New developers understand immediately
5. **Fast iteration** - Change code, press F5, see results

## Applied Examples in This Project

- `websocket_handler.py` - Starts WebSocket server on port 8004
- `stream_handler.py` - Runs stream processing demo
- `main.py` - Starts full application server
- `process_manager.py` - Demonstrates process execution

Each can be debugged by simply:
1. Opening the file
2. Setting breakpoints
3. Pressing F5

No configuration, no arguments, no complexity.