# Test Database Isolation Pattern

## Problem Statement
Tests were polluting the main database, causing issues with:
- Data contamination between test runs
- Parallel test execution conflicts
- CI/CD pipeline reliability
- Development environment safety

## Solution: Transient Test Databases

### Core Pattern
```python
async def create_test_database():
    """Creates a unique test database for each run."""
    unique_db_name = f"script_logs_test_{uuid.uuid4().hex[:8]}"
    
    # Create in system database
    sys_db = client.db("_system", username=username, password=password)
    sys_db.create_database(unique_db_name)
    
    # Initialize with full schema
    test_db = client.db(unique_db_name, username=username, password=password)
    _create_database_schema_sync(test_db)
    
    return test_db, unique_db_name

async def teardown_test_database(db_name: str):
    """Completely removes the test database."""
    sys_db = client.db("_system", username=username, password=password)
    if sys_db.has_database(db_name):
        sys_db.delete_database(db_name)
```

### Implementation in Test Blocks
```python
if __name__ == "__main__":
    async def run_tests():
        # Setup
        db, db_name, db_config = await create_test_database()
        
        try:
            # Configure components to use test database
            log_sink = ArangoLogSink(db_config)
            
            # Run tests
            await test_functionality(log_sink)
            
        finally:
            # Always cleanup
            await teardown_test_database(db_name)
```

## Benefits

1. **Perfect Isolation**: Each test run gets a completely fresh database
2. **No Pollution**: Test data never persists beyond the test run
3. **Parallel Safety**: Multiple tests can run simultaneously without conflicts
4. **CI/CD Ready**: Safe for automated testing pipelines
5. **Development Safety**: No risk of corrupting production or development data

## Database Naming Convention
- Pattern: `script_logs_test_{8_char_hex}`
- Examples:
  - `script_logs_test_564d76df`
  - `script_logs_test_ab5d6815`
  - `script_logs_test_51a9a115`

## Error Handling
- Database creation failures are critical and should raise exceptions
- Cleanup failures should be logged but not prevent test completion
- Use try/finally to ensure cleanup always runs

## Verification
Run the mock test to verify the pattern:
```bash
python test_db_isolation.py
```

This creates multiple test databases and verifies they are properly isolated and cleaned up.