# Key-Value Store API

A simple task list that will automatically get UUID4 verification through hooks.

## Tasks

### Task 1: Create KV Store API
Create a FastAPI key-value store in folder `kv_store/` with file `main.py` containing:
- POST /set - Set a key-value pair
- GET /get/{key} - Get value by key
- DELETE /delete/{key} - Delete a key
- GET /keys - List all keys

Use a simple dictionary for in-memory storage.

### Task 2: Add Persistence
How can I add file-based persistence to the KV store? Read `kv_store/main.py` and modify it to save the dictionary to `kv_store/data.json` after each modification. Load existing data on startup if the file exists.

### Task 3: Write Tests
What tests should I write for the KV store API? Read the implementation in `kv_store/main.py` and create `kv_store/test_kv_store.py` with pytest tests covering all endpoints and persistence functionality.

## Notes

Notice that:
- No UUID4 mentioned anywhere in these tasks
- No special instructions about JSON output format
- Just normal, clean task descriptions
- The hooks will automatically inject UUID4 requirements!