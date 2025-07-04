# Developer-Controlled Task List Example

This shows how developers can mix different execution strategies.

## Task 1: Setup Database
Use `bash` to create a SQLite database:
```bash
sqlite3 app.db "CREATE TABLE todos (id INTEGER PRIMARY KEY, title TEXT, completed BOOLEAN);"
```

## Task 2: Create API
Use `src/cc_executor/prompts/cc_execute.md` to create main.py with FastAPI endpoints that connect to app.db using SQLAlchemy.

## Task 3: Run Custom Analysis
Use `scripts/analyze_code.py` to check the generated API for security issues and code quality.

## Task 4: Generate Docs
Let the orchestrator decide how to read all files and create comprehensive documentation in docs/API.md.

## Task 5: Deploy Check
Use `src/cc_executor/prompts/cc_execute.md` with extended timeout (300s) to create a Dockerfile and docker-compose.yml for the application.