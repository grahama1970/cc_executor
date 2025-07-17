This is a comprehensive and meticulously planned task list for implementing the ArangoDB-backed logging system with agent-friendly capabilities. It addresses all your requirements, including the use of ArangoDB 3.12.4, BM25 search (via ArangoSearch views), "CRUD-like" logger methods, agent-facing instructions in relevant files, and a new `prompts/` directory.

The plan is broken down into phases, with detailed tasks, completion checkboxes, and code examples where relevant.

---

# Comprehensive Logging System Implementation Plan

This document outlines the tasks required to implement an ArangoDB-backed logging system for the agent, providing powerful debugging, introspection, and learning capabilities.

## Phase 0: Environment & Core Dependencies Setup

This phase ensures the foundational environment and external Python packages are ready.

*   [ ] **Task 0.1: ArangoDB Docker Container Setup (Manual/External)**
    *   **Description:** Ensure an ArangoDB 3.12.4 Docker container is running and accessible. The system database's root password should be `openSesame`.
    *   **Agent/Human Instructions:**
        ```bash
        docker run -p 8529:8529 -e ARANGO_ROOT_PASSWORD=openSesame --name arangodb-instance -d arangodb/arangodb:3.12.4
        # Verify it's running:
        docker logs arangodb-instance
        # Or check directly: curl -X GET "http://localhost:8529/_api/version" -u "root:openSesame"
        ```
    *   **Assumptions:** Docker is installed and configured.

*   [ ] **Task 0.2: Python Package Installation**
    *   **Description:** Install necessary Python packages required for ArangoDB interaction, asynchronous operations, and advanced logging.
    *   **Agent/Human Instructions:**
        ```bash
        uv pip install python-arango loguru uvloop tqdm "uvloop==0.19.0" # uvloop is sometimes finicky with latest versions
        # For full-text search and embeddings (needed by some existing modules):
        uv pip install rapidfuzz sentence-transformers rich colorama
        # For LLM caching (if enabled):
        uv pip install redis litellm
        ```
    *   **Note:** `uvloop` is critical for `asyncio.to_thread` and overall async performance. `tqdm` is for progress bars in some utilities.

*   [ ] **Task 0.3: Environment Variable Configuration**
    *   **Description:** Set environment variables that the logging system will use to connect to ArangoDB. These should be accessible by any Python script.
    *   **Agent/Human Instructions (add to `~/.bashrc`, `~/.zshrc`, or your environment setup script):**
        ```bash
        export ARANGO_HOST="http://localhost:8529"
        export ARANGO_DB="script_logs" # New database for logs
        export ARANGO_USER="root"
        export ARANGO_PASSWORD="openSesame"
        ```
    *   **Note:** The `ARANGO_DB` variable specifies the *new database* specifically for logs, separate from other project data (e.g., `memory_bank`), but within the same ArangoDB instance.

## Phase 1: ArangoDB Backend Setup & Core Sink Logic

This phase sets up the database schema and the fundamental mechanism for Loguru to push data to ArangoDB.

*   [ ] **Task 1.1: Create `src/arangodb/core/utils/arango_init.py`**
    *   **Description:** A standalone script to initialize the ArangoDB database and its collections/views for the logging system. This needs to be run *once*.
    *   **Code Example (File: `src/arangodb/core/utils/arango_init.py`):**
        ```python
        #!/usr/bin/env python3
        """
        AGENT_INSTRUCTIONS:
          PURPOSE: Initializes the ArangoDB database and collections specifically for the logging system.
                   This script creates the 'script_logs' database, 'script_runs' collection,
                   'log_events' collection, and 'log_events_view' for full-text search.
                   It MUST be run ONCE before any scripts start logging to ArangoDB.
          HOW TO RUN:
            1. Ensure your ArangoDB Docker container is running and accessible (check Phase 0 instructions).
            2. Ensure ARANGO_HOST, ARANGO_DB, ARANGO_USER, ARANGO_PASSWORD environment variables are set.
            3. Execute this script directly: `python -m src.arangodb.core.utils.arango_init`
          EXPECTED OUTCOME:
            - Messages indicating successful database, collection, and view creation/verification.
            - No error messages related to database connection or creation.
        """
        import os
        import sys
        import time
        from arango import ArangoClient
        from arango.exceptions import ServerConnectionError, DatabaseCreateError, CollectionCreateError, ViewCreateError
        from loguru import logger
        
        # Configure logger for this script
        logger.remove()
        logger.add(sys.stderr, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>")
        
        # --- Constants from Environment Variables (or defaults) ---
        ARANGO_HOST = os.getenv("ARANGO_HOST", "http://localhost:8529")
        ARANGO_DB_NAME = os.getenv("ARANGO_DB", "script_logs") # New dedicated log DB
        ARANGO_USER = os.getenv("ARANGO_USER", "root")
        ARANGO_PASSWORD = os.getenv("ARANGO_PASSWORD", "openSesame") # Use specified password
        
        # --- Collection and View Names for Logging ---
        SCRIPT_RUNS_COLLECTION = "script_runs"
        LOG_EVENTS_COLLECTION = "log_events"
        LOG_EVENTS_VIEW = "log_events_view"
        
        # --- ArangoSearch View Fields and Analyzer ---
        # Fields to index for full-text search (BM25-like)
        ARANGOSEARCH_VIEW_FIELDS = [
            "message",
            "level", # log level name
            "function",
            "file", # file.name
            "line",
            "extra.execution_id", # Crucial for linking to script_runs
            "extra.log_category", # For agent learning, final response, etc.
            "extra.payload", # For the raw JSON response of the script
            "exception.value", # For searching within exception messages
            "exception.type", # For searching by exception type
        ]
        TEXT_ANALYZER = "text_en"
        
        def initialize_arango_logging_db <cyan>{message}</cyan>")
    
    def initialize_arango_logging_db():
        """Connects to ArangoDB and sets up the logging database and schema."""
        try:
            logger.info(f"Connecting to ArangoDB at {ARANGO_HOST}...")
            client = ArangoClient(hosts=ARANGO_HOST)
            
            # Connect to _system database for creation
            sys_db = client.db("_system", username=ARANGO_USER, password=ARANGO_PASSWORD)
            sys_db.properties() # Test connection
            logger.info("Successfully connected to ArangoDB.")
            
            # 1. Create the dedicated log database
            if not sys_db.has_database(ARANGO_LOG_DB_NAME):
                logger.info(f"Creating database: {ARANGO_LOG_DB_NAME}...")
                sys_db.create_database(
                    name=ARANGO_LOG_DB_NAME,
                    users=[{"username": ARANGO_USER, "password": ARANGO_PASSWORD, "active": True}]
                )
                logger.success(f"Database '{ARANGO_LOG_DB_NAME}' created.")
            else:
                logger.info(f"Database '{ARANGO_LOG_DB_NAME}' already exists.")
            
            # Connect to the new log database
            db = client.db(ARANGO_LOG_DB_NAME, username=ARANGO_USER, password=ARANGO_PASSWORD)
            
            # 2. Create collections
            for collection_name in [LOG_EVENTS_COLLECTION, SCRIPT_RUNS_COLLECTION]:
                if not db.has_collection(collection_name):
                    logger.info(f"Creating collection: {collection_name}...")
                    db.create_collection(collection_name)
                    logger.success(f"Collection '{collection_name}' created.")
                else:
                    logger.info(f"Collection '{collection_name}' already exists.")
            
            # 3. Create ArangoSearch View for full-text search
            view_exists = False
            try:
                view_info = db.view(LOG_EVENTS_VIEW).properties()
                view_exists = True
                logger.info(f"ArangoSearch View '{LOG_EVENTS_VIEW}' already exists.")
                # For clean setup, we might delete and recreate it. For idempotency, we just ensure config.
                # If properties change often, uncomment next lines to force recreation.
                # logger.info(f"Deleting existing view '{LOG_EVENTS_VIEW}' for clean setup...")
                # db.delete_view(LOG_EVENTS_VIEW)
                # view_exists = False
                # time.sleep(1) # Wait for deletion
            except Exception:
                pass # View does not exist or error getting properties
            
            if not view_exists:
                logger.info(f"Creating ArangoSearch View: {LOG_EVENTS_VIEW}...")
                db.create_arangosearch_view(
                    LOG_EVENTS_VIEW,
                    {
                        "links": {
                            LOG_EVENTS_COLLECTION: {
                                "analyzers": [TEXT_ANALYZER],
                                "includeAllFields": False,
                                "fields": {
                                    "message": {},
                                    "level.name": {}, # Allow searching by log level name
                                    "function": {},
                                    "file.name": {},
                                    "extra.payload": {}, # For script final responses
                                    "exception.value": {}, # For error messages
                                    "extra.log_category": {} # For searching agent learnings, errors etc.
                                }
                            }
                        }
                    }
                )
                logger.success(f"ArangoSearch View '{LOG_EVENTS_VIEW}' created.")
            
            logger.success("ArangoDB logging system setup complete!")
            return True
        
        except ServerConnectionError as e:
            logger.critical(f"Failed to connect to ArangoDB: {e}. Please ensure ArangoDB is running and accessible.")
            return False
        except (DatabaseCreateError, CollectionCreateError, ViewCreateError) as e:
            logger.critical(f"ArangoDB schema creation failed: {e}. Please check permissions or existing conflicts.")
            return False
        except Exception as e:
            logger.critical(f"An unexpected error occurred during setup: {e}", exc_info=True)
            return False
            
    if __name__ == "__main__":
        if not initialize_arango_logging_db():
            sys.exit(1)
        sys.exit(0)
    ```

## Phase 2: Loguru Custom Sink & Asynchronous Writes

This phase focuses on the heart of the logging system: the custom Loguru sink that writes log records to ArangoDB asynchronously.

### Task 2.1: Create `utils/arango_log_sink.py` (Loguru Custom ArangoDB Sink)

This file defines the actual function that Loguru will call for each log message.

*   [ ] **Description:** Implement a synchronous function `arango_log_sink(message)` that extracts relevant data from Loguru's `message.record` and places it into an `asyncio.Queue`. The ArangoDB connection and actual write operations will be handled by a separate background task.
*   **Relevant Files:** `src/arangodb/core/utils/arango_log_sink.py` (NEW)
*   **Agent Relevance:** This is an internal component, but its robust design ensures logs are reliably stored, which is critical for agent debugging.
*   **Code Example:**
    ```python
    # src/arangodb/core/utils/arango_log_sink.py
    """
    Loguru Custom Sink for ArangoDB.
    
    This module provides a custom Loguru sink function that pushes log records
    to an asyncio.Queue for asynchronous processing and storage in ArangoDB.
    This prevents blocking the main application thread during high-volume logging.
    """
    import asyncio
    import json
    from datetime import datetime, timezone
    from typing import Dict, Any, Optional
    from loguru import logger
    
    # Global queue to hold log records
    # This queue will be initialized and managed by AgentLogManager
    _log_queue: Optional[asyncio.Queue] = None
    
    def set_log_queue(queue: asyncio.Queue):
        """Sets the global log queue for the sink."""
        global _log_queue
        _log_queue = queue
    
    def arango_log_sink(message):
        """
        Loguru sink function to push log records to an asyncio.Queue.
        
        This function is called by Loguru for every log message. It extracts
        relevant data and enqueues it for a separate background task to write
        to ArangoDB.
        """
        if _log_queue is None:
            # Fallback for when queue isn't set up yet (e.g., during very early logging)
            print(f"Loguru sink: Queue not initialized. Message lost: {message.record['message']}", file=sys.stderr)
            return
            
        record = message.record
        
        # Extract relevant fields (top 6 + others crucial for agent reasoning)
        log_doc = {
            "time": record["time"].isoformat(),
            "level": {"name": record["level"].name, "no": record["level"].no},
            "message": record["message"],
            "file": {"name": record["file"].name, "path": record["file"].path},
            "function": record["function"],
            "line": record["line"],
            "elapsed": record["elapsed"].total_seconds(), # Duration since start of logger
            "process": {"id": record["process"].id, "name": record["process"].name},
            "thread": {"id": record["thread"].id, "name": record["thread"].name},
            "extra": record["extra"].copy() # Include all extra fields
        }
        
        # Add exception info if present
        if record["exception"]:
            log_doc["exception"] = {
                "type": record["exception"].type.__name__,
                "value": str(record["exception"].value),
                "traceback": "".join(record["exception"].traceback)
            }
        
        # Categorize for easier querying by agent
        log_category = log_doc["level"]["name"]
        if "log_category" in log_doc["extra"]:
            log_category = log_doc["extra"]["log_category"] # Use custom category if provided
        
        log_doc["log_category"] = log_category
        
        # Add to queue for asynchronous writing
        try:
            _log_queue.put_nowait(log_doc)
        except asyncio.QueueFull:
            logger.error(f"Log queue is full, message dropped: {log_doc['message']}")
            # In a very high-volume scenario, you might add a rate limit or another fallback
        except Exception as e:
            logger.error(f"Failed to add message to log queue: {e} - Message: {log_doc['message']}")
    ```

### Task 2.2: Implement Background Writer Task (within `AgentLogManager`)

This background task pulls messages from the queue and writes them to ArangoDB.

*   [ ] **Description:** This task will be implemented as a private method within the `AgentLogManager` (Task 3.1). It will run in a separate thread/task, connect to ArangoDB, and continuously process log records from the `asyncio.Queue` (from Task 2.1). Crucially, it will use `asyncio.to_thread()` for the actual blocking database write operations.
*   **Relevant Files:** `src/arangodb/core/utils/agent_log_manager.py` (created in Task 3.1)
*   **Agent Relevance:** Ensures non-blocking logging, which is crucial for script performance and stability.

## Phase 3: `AgentLogManager` & Unified Logger API

This is the core of the new logging system, providing a single point of interaction for the agent.

### Task 3.1: Create `utils/agent_log_manager.py` (AgentLogManager Class Definition)

This file defines the singleton logger that agents will primarily interact with.

*   [ ] **Description:** Create the `AgentLogManager` class as a singleton. It will initialize the Loguru logger with custom sinks (console and ArangoDB). It will encapsulate all ArangoDB connection logic and expose agent-friendly methods for logging, querying, searching, and managing log data.
*   **Relevant Files:** `src/arangodb/core/utils/agent_log_manager.py` (NEW)
*   **Agent Relevance:** This is the *primary interface* for the agent's logging. All agent instructions will point to using this `logger` object. Its comprehensive API simplifies complex tasks.
*   **Code Example (Partial, focusing on structure):**
    ```python
    # src/arangodb/core/utils/agent_log_manager.py
    """
    Agent Log Manager: Centralized ArangoDB-backed Logger for Autonomous Agents.
    
    AGENT_INSTRUCTIONS:
    This is your primary tool for logging, debugging, and learning.
    Import `logger` (as `agent_logger`) from this module in your scripts.
    
    Usage:
    - `logger.info("Your message")`: Standard logging.
    - `logger.error("Error occurred", exc_info=True)`: Log errors with traceback.
    - `logger.log_agent_learning("Lesson learned: ...", function_name="...")`: Document insights.
    - `execution_id = logger.start_run(script_name, mode)`: Begin a new script execution session.
      (Remember to `logger.bind(execution_id=execution_id)` for all subsequent logs in that run).
    - `logger.end_run(execution_id, success_status)`: Conclude a script execution.
    - `latest_response = logger.get_latest_response(script_name, execution_id=...)`: Retrieve your script's final output.
    - `results = logger.query("FOR l IN log_events RETURN l")`: Execute custom AQL queries for deep analysis.
    - `search_results = logger.search_bm25("query text")`: Perform full-text search on logs.
    - `logger.prune(days_to_keep=7, log_category="DEBUG")`: Clean up old logs.
    
    This manager provides a single source of truth for all your script executions,
    errors, and learnings within ArangoDB.
    """
    import asyncio
    import json
    import sys
    import threading
    import time
    from datetime import datetime, timedelta, timezone
    from functools import wraps
    from typing import Dict, List, Optional, Any, Tuple
    
    from arango import ArangoClient
    from arango.database import StandardDatabase
    from arango.exceptions import ServerConnectionError, AQLQueryExecuteError, DocumentInsertError
    from loguru import logger as loguru_logger
    
    from arangodb.core.utils.arango_constants import (
        ARANGO_HOST, ARANGO_USER, ARANGO_PASSWORD, ARANGO_LOG_DB_NAME,
        LOG_EVENTS_COLLECTION, SCRIPT_RUNS_COLLECTION, LOG_EVENTS_VIEW, TEXT_ANALYZER
    )
    from arangodb.core.utils.arango_log_sink import arango_log_sink, set_log_queue
    
    class AgentLogManager:
        _instance: Optional["AgentLogManager"] = None
        _lock = threading.Lock()
        _initialized = False
        
        def __new__(cls):
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
            return cls._instance
            
        def __init__(self):
            if self._initialized:
                return
            
            self._db_client: Optional[ArangoClient] = None
            self._db: Optional[StandardDatabase] = None
            self._log_queue = asyncio.Queue()
            
            self._setup_loguru()
            self._connect_db() # Blocking for init, but subsequent writes async
            self._start_writer_task()
            
            self._initialized = True
            loguru_logger.info("AgentLogManager initialized and ready.")

        def _setup_loguru(self):
            loguru_logger.remove() # Remove default handlers
            
            # Console handler for immediate feedback
            loguru_logger.add(
                sys.stderr,
                level="INFO",
                format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
                diagnose=False
            )
            
            # ArangoDB sink for persistent storage
            set_log_queue(self._log_queue) # Set the queue for the sink function
            loguru_logger.add(
                arango_log_sink,
                level="DEBUG", # Capture all logs for ArangoDB
                enqueue=True   # Process logs in a separate thread/task
            )

        def _connect_db(self):
            try:
                self._db_client = ArangoClient(hosts=ARANGO_HOST)
                # We connect to the specific log database
                self._db = self._db_client.db(ARANGO_LOG_DB_NAME, username=ARANGO_USER, password=ARANGO_PASSWORD)
                self._db.properties() # Test connection
            except Exception as e:
                loguru_logger.critical(f"AgentLogManager: Failed to connect to ArangoDB at {ARANGO_HOST} db {ARANGO_LOG_DB_NAME}: {e}")
                self._db = None # Mark as unavailable
                # Exit if critical connection fails at init
                sys.exit(1) 

        def _start_writer_task(self):
            """Starts the background task to write logs from the queue to ArangoDB."""
            if self._db is None:
                loguru_logger.warning("ArangoDB not connected, skipping log writer task start.")
                return
            
            # Use a separate thread for the async event loop to not block main thread
            # Or, if the main application is already asyncio-based, integrate directly.
            # For this template, a separate thread with a new loop is safer.
            def writer_thread_target():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                new_loop.run_until_complete(self._log_writer_task())
                new_loop.close()
            
            thread = threading.Thread(target=writer_thread_target, daemon=True)
            thread.start()
            loguru_logger.info("Background ArangoDB log writer task started.")

        async def _log_writer_task(self):
            """Continuously writes log records from the queue to ArangoDB."""
            if self._db is None: return
            
            while True:
                try:
                    log_doc = await self._log_queue.get()
                    if log_doc is None: # Signal to stop the writer
                        break
                    
                    # Wrap blocking DB call in to_thread
                    await asyncio.to_thread(self._db.collection(LOG_EVENTS_COLLECTION).insert, log_doc)
                    self._log_queue.task_done()
                    
                except Exception as e:
                    loguru_logger.error(f"Error writing log to ArangoDB: {e} - Log doc: {log_doc.get('message', 'N/A')}", exc_info=True)
                    # Re-queue if transient error? For simplicity, we drop for now.
                    self._log_queue.task_done() # Mark as done even on error to prevent blocking

        # --- Agent-Facing "CRUD" Methods ---
        
        @wraps(loguru_logger.info) # Preserve Loguru's info():
            logger.info(f"Attempting to initialize ArangoDB for logging at {ARANGO_HOST}/{ARANGO_DB_NAME}...")
            try:
                client = ArangoClient(hosts=ARANGO_HOST)
                
                # Connect to _system database to manage user and database creation
                sys_db = client.db("_system", username=ARANGO_USER, password=ARANGO_PASSWORD)
                sys_db.properties() # Test connection by fetching properties
        
                # Create the dedicated log database if it doesn't exist
                if not sys_db.has_database(ARANGO_DB_NAME):
                    logger.info(f"Creating database '{ARANGO_DB_NAME}'...")
                    sys_db.create_database(
                        name=ARANGO_DB_NAME,
                        users=[{
                            "username": ARANGO_USER,
                            "password": ARANGO_PASSWORD,
                            "active": True
                        }]
                    )
                    logger.success(f"Database '{ARANGO_DB_NAME}' created successfully.")
                else:
                    logger.info(f"Database '{ARANGO_DB_NAME}' already exists.")
        
                # Connect to the specific log database
                db = client.db(ARANGO_DB_NAME, username=ARANGO_USER, password=ARANGO_PASSWORD)
                db.properties() # Test connection to the specific database
                logger.success(f"Connected to database '{ARANGO_DB_NAME}'.")
        
                # --- Ensure Collections ---
                collections_to_create = [
                    (SCRIPT_RUNS_COLLECTION, False), # Document collection for script run metadata
                    (LOG_EVENTS_COLLECTION, False)   # Document collection for all log events
                ]
                for coll_name, is_edge in collections_to_create:
                    if not db.has_collection(coll_name):
                        logger.info(f"Creating {'edge ' if is_edge else ''}collection '{coll_name}'...")
                        db.create_collection(name=coll_name, edge=is_edge)
                        logger.success(f"Collection '{coll_name}' created.")
                    else:
                        logger.info(f"Collection '{coll_name}' already exists.")
        
                # --- Ensure ArangoSearch View for Full-Text Search (BM25-like) ---
                logger.info(f"Ensuring ArangoSearch View '{LOG_EVENTS_VIEW}'...")
                
                # Define view properties
                view_properties = {
                    "links": {
                        LOG_EVENTS_COLLECTION: {
                            "analyzers": [TEXT_ANALYZER],
                            "includeAllFields": False,
                            "fields": {field: {} for field in ARANGOSEARCH_VIEW_FIELDS}
                        }
                    }
                }
                
                # Delete view if it exists (for clean updates to properties)
                if db.has_view(LOG_EVENTS_VIEW):
                    logger.warning(f"View '{LOG_EVENTS_VIEW}' already exists. Deleting and recreating to ensure up-to-date configuration.")
                    db.delete_view(LOG_EVENTS_VIEW)
                    time.sleep(1) # Give ArangoDB time to delete
                
                # Create the view
                db.create_arangosearch_view(name=LOG_EVENTS_VIEW, properties=view_properties)
                logger.success(f"ArangoSearch View '{LOG_EVENTS_VIEW}' created successfully.")
                logger.info(f"View '{LOG_EVENTS_VIEW}' indexed fields: {', '.join(ARANGOSEARCH_VIEW_FIELDS)}")
                logger.info(f"View '{LOG_EVENTS_VIEW}' using analyzer: '{TEXT_ANALYZER}'")
        
                logger.success("ArangoDB logging system initialization complete!")
        
            except ServerConnectionError as e:
                logger.critical(f"Failed to connect to ArangoDB server. Please ensure it is running and accessible at {ARANGO_HOST}. Error: {e}")
                sys.exit(1)
            except DatabaseCreateError as e:
                logger.critical(f"Failed to create database '{ARANGO_DB_NAME}'. Check user permissions or if it already exists. Error: {e}")
                sys.exit(1)
            except CollectionCreateError as e:
                logger.critical(f"Failed to create a collection. Error: {e}")
                sys.exit(1)
            except ViewCreateError as e:
                logger.critical(f"Failed to create ArangoSearch View '{LOG_EVENTS_VIEW}'. Error: {e}")
                sys.exit(1)
            except Exception as e:
                logger.critical(f"An unexpected error occurred during initialization: {e}", exc_info=True)
                sys.exit(1)
        
        if __name__ == "__main__":
            initialize_arango_logging_db()
        ```
    *   **Agent/Human Instructions:** Execute this file directly once to set up the database.

*   [ ] **Task 1.2: Create `src/arangodb/core/utils/arango_log_sink.py`**
    *   **Description:** This module contains the actual `loguru` sink function that will format log records and push them onto an `asyncio.Queue`. A separate background task will drain this queue and write to ArangoDB.
    *   **Code Example (File: `src/arangodb/core/utils/arango_log_sink.py`):**
        ```python
        #!/usr/bin/env python3
        """
        AGENT_INSTRUCTIONS:
          PURPOSE: Internal module for the logging system. It defines how log messages
                   are formatted and sent to ArangoDB asynchronously. Agents typically
                   do NOT call this file directly but use the 'logger' object from
                   'agent_log_manager.py'.
          KEY FUNCTIONALITY:
            - Converts Loguru records into structured documents.
            - Puts log documents into an asynchronous queue for non-blocking writes.
            - Handles a background task to safely write logs to ArangoDB.
        """
        import asyncio
        import sys
        import json
        import threading
        from datetime import datetime
        from collections import deque
        from arango import ArangoClient
        from arango.exceptions import ArangoServerError, DocumentInsertError, ConnectionRefused
        from loguru import logger
        import uvloop # Ensure uvloop is used for performance
        
        # Ensure uvloop is installed and used if possible
        try:
            uvloop.install()
        except Exception:
            logger.warning("uvloop could not be installed, using default asyncio event loop.")
        
        # --- Constants from Environment Variables (or defaults) ---
        ARANGO_HOST = os.getenv("ARANGO_HOST", "http://localhost:8529")
        ARANGO_DB_NAME = os.getenv("ARANGO_DB", "script_logs")
        ARANGO_USER = os.getenv("ARANGO_USER", "root")
        ARANGO_PASSWORD = os.getenv("ARANGO_PASSWORD", "openSesame")
        
        # --- Collection Names ---
        LOG_EVENTS_COLLECTION = "log_events"
        
        # --- Global Queue and Background Task State ---
        _log_queue = deque() # Use deque for thread-safe append/pop (faster than asyncio.Queue for many small items)
        _log_queue_lock = threading.Lock() # Protect deque access
        _stop_event = threading.Event() # Signal to stop the writer thread
        _writer_thread = None # Reference to the background thread
        
        # --- ArangoDB Connection (for background writer) ---
        _db_connection_cache = {"db": None} # Cache the DB connection for the writer thread
        
        def _get_db_connection():
            """Get or create ArangoDB connection for the writer thread."""
            if _db_connection_cache["db"] is None:
                try:
                    client = ArangoClient(hosts=ARANGO_HOST)
                    db = client.db(ARANGO_DB_NAME, username=ARANGO_USER, password=ARANGO_PASSWORD)
                    db.properties() # Test connection
                    _db_connection_cache["db"] = db
                    logger.info("ArangoDB connection established for log sink writer.")
                except Exception as e:
                    logger.error(f"Failed to establish ArangoDB connection for log sink writer: {e}")
                    _db_connection_cache["db"] = None # Reset on failure
            return _db_connection_cache["db"]
        
        def _writer_main_loop():
            """Main loop for the background log writer thread."""
            logger.info("ArangoDB log writer thread started.")
            db = None
            consecutive_errors = 0
            MAX_CONSECUTIVE_ERRORS = 5
            RECONNECT_DELAY_S = 5
            BATCH_SIZE = 50 # Batch writes for efficiency
        
            while not _stop_event.is_set():
                if db is None:
                    db = _get_db_connection()
                    if db is None:
                        time.sleep(RECONNECT_DELAY_S) # Wait before retrying connection
                        continue
        
                records_to_write = []
                with _log_queue_lock:
                    while _log_queue and len(records_to_write) < BATCH_SIZE:
                        records_to_write.append(_log_queue.popleft())
        
                if not records_to_write:
                    time.sleep(0.01) # Small delay to prevent busy-waiting
                    continue
        
                try:
                    # Insert documents in a batch
                    db.collection(LOG_EVENTS_COLLECTION).insert_many(records_to_write, silent=True)
                    logger.debug(f"Inserted {len(records_to_write)} log events into ArangoDB.")
                    consecutive_errors = 0 # Reset error counter on success
                except (ArangoServerError, DocumentInsertError, ConnectionRefused) as e:
                    consecutive_errors += 1
                    logger.error(f"Failed to write log batch to ArangoDB (attempt {consecutive_errors}): {e}")
                    # Re-queue failed records if not too many errors, or if connection problem, they will be dropped
                    if consecutive_errors < MAX_CONSECUTIVE_ERRORS and not isinstance(e, ConnectionRefused):
                        with _log_queue_lock:
                            _log_queue.extendleft(reversed(records_to_write)) # Add back to front
                    else:
                        logger.critical(f"Too many consecutive ArangoDB write errors ({consecutive_errors}). Dropping {len(records_to_write)} log events.")
                        db = None # Force re-connection attempt
                        time.sleep(RECONNECT_DELAY_S) # Add delay to prevent rapid failing loops
                except Exception as e:
                    consecutive_errors += 1
                    logger.critical(f"Unexpected error in log writer thread (attempt {consecutive_errors}): {e}", exc_info=True)
                    if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                         logger.critical("Max consecutive unexpected errors reached. Stopping writer thread.")
                         _stop_event.set()
                         break
                    db = None # Force re-connection attempt on unexpected error
                    time.sleep(RECONNECT_DELAY_S) # Add delay
            
            logger.info("ArangoDB log writer thread stopped.")
        
        def start_writer_thread():
            """Starts the background log writer thread."""
            global _writer_thread
            if _writer_thread is None or not _writer_thread.is_alive():
                _stop_event.clear()
                _writer_thread = threading.Thread(target=_writer_main_loop, daemon=True)
                _writer_thread.start()
                logger.info("ArangoDB log writer thread initiated.")
            else:
                logger.info("ArangoDB log writer thread is already running.")
        
        def stop_writer_thread():
            """Stops the background log writer thread and flushes the queue."""
            logger.info("Signaling ArangoDB log writer thread to stop...")
            _stop_event.set()
            if _writer_thread and _writer_thread.is_alive():
                _writer_thread.join(timeout=10) # Wait for it to finish
                if _writer_thread.is_alive():
                    logger.warning("Log writer thread did not stop gracefully.")
            
            # Flush any remaining logs before exiting
            db = _get_db_connection()
            if db:
                remaining_records = []
                with _log_queue_lock:
                    while _log_queue:
                        remaining_records.append(_log_queue.popleft())
                if remaining_records:
                    logger.info(f"Flushing {len(remaining_records)} remaining log events to ArangoDB...")
                    try:
                        db.collection(LOG_EVENTS_COLLECTION).insert_many(remaining_records, silent=True)
                        logger.success("Remaining log events flushed successfully.")
                    except Exception as e:
                        logger.error(f"Failed to flush remaining log events: {e}")
            
            logger.info("ArangoDB log writer thread cleanup complete.")
        
        def arango_log_sink(message):
            """
            Loguru sink function to push log records to ArangoDB.
            This function is called by Loguru for each log message.
            """
            record = message.record
            log_doc = {
                "timestamp": record["time"].isoformat(),
                "level": record["level"].name,
                "message": record["message"],
                "file": record["file"].name,
                "function": record["function"],
                "line": record["line"],
                "process_id": record["process"].id,
                "thread_id": record["thread"].id,
                "elapsed": record["elapsed"].total_seconds(),
                "extra": record["extra"] # Store all extra data for flexibility
            }
        
            # Add exception details if present
            if record["exception"] is not None:
                log_doc["exception"] = {
                    "type": record["exception"].type,
                    "value": str(record["exception"].value),
                    "traceback": record["exception"].traceback,
                }
        
            # Add log_category for easier filtering/graph building (defaults to level name)
            log_doc["log_category"] = record["extra"].get("log_category", record["level"].name)
            
            with _log_queue_lock:
                _log_queue.append(log_doc)
            logger.debug(f"Queued log event: {log_doc['message'][:50]}...")
        
        if __name__ == "__main__":
            # Example usage of the sink and writer thread
            start_writer_thread()
            
            # Add some log messages (will be queued)
            logger.add(arango_log_sink, level="DEBUG", enqueue=True) # Use our custom sink
            
            logger.info("Test INFO message to ArangoDB.")
            logger.debug("Test DEBUG message with extra data.", extra={"custom_field": "custom_value"})
            
            try:
                raise ValueError("Simulated error")
            except ValueError as e:
                logger.error("Test ERROR message with exception.", exc_info=True)
            
            logger.info("SCRIPT_FINAL_RESPONSE_TAG", payload={"status": "success", "data": [1,2,3]}, log_category="SCRIPT_FINAL_RESPONSE")
            logger.info("AGENT_LEARNING_TAG", learned_fact="Learned how to fix a bug.", function_name="validate_input", log_category="AGENT_LEARNING")
            
            # Give time for the background thread to process the queue
            logger.info("Waiting for logs to flush...")
            time.sleep(5) 
            
            # Stop the writer thread explicitly in a real shutdown sequence
            # For this example, it will stop automatically on script exit (daemon thread)
            # but explicit stop is good for graceful shutdowns.
            # stop_writer_thread() 
            logger.success("Test messages sent. Check ArangoDB 'script_logs' database.")
        ```
    *   **Agent/Human Instructions:** This file is an *internal* utility. Agents will not directly call this file. Its functions are integrated into `AgentLogManager.py`.

*   [ ] **Task 1.3: Update `src/arangodb/core/utils/dependency_checker.py`**
    *   **Description:** Ensure `uvloop` and `uvloop.install()` are properly checked and imported if available, or mocked if not. This ensures the best performance for async operations if `uvloop` is present.
    *   **Code Example (Snippet in `dependency_checker.py`):**
        ```python
        # In src/arangodb/core/utils/dependency_checker.py
        # ... existing imports ...
        
        # Check for uvloop
        uvloop = check_dependency("uvloop", "uvloop", "0.19.0")
        HAS_UVLOOP = uvloop is not None
        
        if HAS_UVLOOP:
            try:
                import uvloop
                uvloop.install() # Install uvloop as default event loop
                logger.info("uvloop installed as default asyncio event loop.")
            except Exception as e:
                logger.warning(f"Failed to install uvloop as default event loop: {e}. Defaulting to standard loop.")
                HAS_UVLOOP = False # Mark as not effectively available
        ```
    *   **Note:** This snippet should be placed appropriately within the existing `dependency_checker.py` file, likely after other top-level dependency checks.

## Phase 2: `AgentLogManager` - The Agent's Gateway to Logs

This phase creates the primary interface for agents to interact with the logging system and its ArangoDB backend.

*   [ ] **Task 2.1: Create `src/arangodb/core/utils/agent_log_manager.py`**
    *   **Description:** This class provides the singleton `logger` instance that agents will use. It orchestrates `loguru` setup, background writing, and exposes simplified "CRUD-like" methods for querying and managing logs in ArangoDB.
    *   **Code Example (File: `src/arangodb/core/utils/agent_log_manager.py`):**
        ```python
        #!/usr/bin/env python3
        """
        AGENT_INSTRUCTIONS:
          PURPOSE: This module provides the central 'logger' object for all Python scripts.
                   It handles logging messages to an ArangoDB database, allowing the agent
                   to search, query, and manage logs (including errors, responses, and learnings)
                   using a unified API. It's designed for highly effective debugging and introspection.
          HOW TO USE:
            1. IMPORT: Replace `from loguru import logger` with `from src.arangodb.core.utils.agent_log_manager import logger, log_agent_learning, start_run, end_run, get_latest_response, search_bm25_logs, query_logs, prune_logs`
            2. START A RUN: At the beginning of your script's `if __name__ == "__main__":` block, call `execution_id = start_run(Path(__file__).stem, mode)`.
            3. BIND EXECUTION_ID: Immediately after `start_run`, bind the returned `execution_id` to the logger: `logger.bind(execution_id=execution_id)`. This links all logs to this specific script execution.
            4. LOG FINAL RESPONSE: For the script's primary JSON output, use `logger.info("SCRIPT_FINAL_RESPONSE", payload=your_final_json_data, log_category="SCRIPT_FINAL_RESPONSE")`. The 'payload' key is CRITICAL.
            5. LOG AGENT LEARNINGS: Use `log_agent_learning("Specific lesson learned", function_name="my_function")` to document debugging steps or insights.
            6. QUERY LOGS: From anywhere (e.g., debug_function, or a separate agent script/notebook), use `query_logs("FOR l IN log_events FILTER l.level == 'ERROR' RETURN l")` to retrieve log data using AQL.
            7. SEARCH LOGS (BM25): Use `search_bm25_logs("error in redis connection", limit=5)` for full-text search.
            8. GET LATEST RESPONSE: Use `latest_response = get_latest_response(Path(__file__).stem)` to retrieve the last primary output.
            9. PRUNE LOGS: Use `prune_logs(days_to_keep=7, log_category="DEBUG")` to manage log size.
            10. END A RUN: At the end of your script's `if __name__ == "__main__":` block, call `end_run(execution_id, success_status)`.
        """
        
        import asyncio
        import sys
        import json
        import threading
        from pathlib import Path
        from datetime import datetime, timedelta
        from arango import ArangoClient
        from arango.exceptions import ArangoServerError, DocumentInsertError
        from loguru import logger as loguru_logger # Use an alias to avoid name conflict
        
        # Internal imports for the sink logic
        from src.arangodb.core.utils.arango_log_sink import arango_log_sink, start_writer_thread, stop_writer_thread
        
        # --- Constants from Environment Variables (or defaults) ---
        ARANGO_HOST = os.getenv("ARANGO_HOST", "http://localhost:8529")
        ARANGO_DB_NAME = os.getenv("ARANGO_DB", "script_logs")
        ARANGO_USER = os.getenv("ARANGO_USER", "root")
        ARANGO_PASSWORD = os.getenv("ARANGO_PASSWORD", "openSesame")
        
        # --- Collection and View Names ---
        SCRIPT_RUNS_COLLECTION = "script_runs"
        LOG_EVENTS_COLLECTION = "log_events"
        LOG_EVENTS_VIEW = "log_events_view" # For BM25 search
        
        class AgentLogManager:
            _instance = None
            _lock = threading.Lock() # For thread-safe singleton instantiation
            _initialized = False
        
            def __new__(cls):
                with cls._lock:
                    if cls._instance is None:
                        cls._instance = super().__new__(cls)
                return cls._instance
        
            def __init__(self):
                if self._initialized:
                    return
                
                self._db = None
                self._connect_db() # Establish initial connection
                
                self._configure_loguru()
                start_writer_thread() # Start the background log writer thread
        
                self._initialized = True
                loguru_logger.info("AgentLogManager initialized and ArangoDB logging activated.")
        
            def _connect_db(self):
                """Establishes and caches the ArangoDB connection."""
                try:
                    client = ArangoClient(hosts=ARANGO_HOST)
                    self._db = client.db(ARANGO_DB_NAME, username=ARANGO_USER, password=ARANGO_PASSWORD)
                    self._db.properties() # Test connection
                    loguru_logger.info(f"AgentLogManager connected to ArangoDB '{ARANGO_DB_NAME}'.")
                except Exception as e:
                    loguru_logger.error(f"AgentLogManager: Failed to connect to ArangoDB at '{ARANGO_HOST}/{ARANGO_DB_NAME}': {e}")
                    self._db = None
                    # No sys.exit(1) here as it's a utility, not the main script
        
            def _configure_loguru(self):
                """Configures the loguru logger with custom sinks."""
                loguru_logger.remove() # Remove default handlers
        
                # Console Logger (for immediate feedback)
                loguru_logger.add(
                    sys.stderr,
                    level="INFO", # Default level for console output
                    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
                    diagnose=False
                )
        
                # Custom ArangoDB sink (all log levels go here for detailed history)
                loguru_logger.add(
                    arango_log_sink, # The sink function from arango_log_sink.py
                    level="DEBUG",   # Capture all messages from DEBUG upwards
                    enqueue=True,    # Crucial for non-blocking logging
                    diagnose=True,   # Include traceback and variable values for all logged messages
                    backtrace=True,  # Include full traceback
                )
                loguru_logger.info("Loguru configured with console and ArangoDB sinks.")
        
            @property
            def logger(self):
                """Provides the configured loguru logger instance."""
                return loguru_logger
            
            def _ensure_db_and_collections(self):
                """Internal helper to ensure DB connection and collections are available before query/write operations signature
        def info(self, message: str, *args, **kwargs):
            return loguru_logger.info(message, *args, **kwargs)

        @wraps(loguru_logger.debug)
        def debug(self, message: str, *args, **kwargs):
            return loguru_logger.debug(message, *args, **kwargs)
        
        @wraps(loguru_logger.warning)
        def warning(self, message: str, *args, **kwargs):
            return loguru_logger.warning(message, *args, **kwargs)

        @wraps(loguru_logger.error)
        def error(self, message: str, *args, **kwargs):
            return loguru_logger.error(message, *args, **kwargs)

        @wraps(loguru_logger.critical)
        def critical(self, message: str, *args, **kwargs):
            return loguru_logger.critical(message, *args, **kwargs)

        def query(self, aql_query: str, bind_vars: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
            """
            AGENT: Execute a custom AQL query against the log database.
            Use this for complex analysis or retrieving specific log patterns.
            
            Args:
                aql_query: The AQL query string.
                bind_vars: Optional dictionary of bind variables for the query.
            
            Returns:
                A list of dictionaries representing the query results.
            
            Example:
                `logger.query("FOR l IN log_events FILTER l.level.name == 'ERROR' RETURN l")`
                `logger.query("FOR r IN script_runs SORT r.start_time DESC LIMIT 1 RETURN r")`
            """
            if self._db is None:
                loguru_logger.error("ArangoDB not connected, cannot execute query.")
                return []
            try:
                # ArangoDB client methods are synchronous, use to_thread in async contexts
                cursor = self._db.aql.execute(aql_query, bind_vars=bind_vars)
                return list(cursor)
            except AQLQueryExecuteError as e:
                loguru_logger.error(f"AQL query failed: {e} - Query: {aql_query[:100]}...", exc_info=True)
                return []
            except Exception as e:
                loguru_logger.error(f"Unexpected error during AQL query: {e}", exc_info=True)
                return []

        def search_bm25(self, text_query: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
            """
            AGENT: Perform a full-text search using ArangoSearch (BM25-like relevance).
            This is ideal for finding log entries or script outputs by keywords.
            
            Args:
                text_query: The search string (e.g., "redis connection error", "script final response").
                limit: Maximum number of results to return.
                offset: Offset for pagination.
                
            Returns:
                A list of dictionaries, each containing a log document and its relevance score.
            
            Example:
                `logger.search_bm25("Failed to save results")`
                `logger.search_bm25("SCRIPT_FINAL_RESPONSE task:analyze_data")`
            """
            if self._db is None:
                loguru_logger.error("ArangoDB not connected, cannot perform BM25 search.")
                return []
            
            aql = f"""
            FOR doc IN {LOG_EVENTS_VIEW}
                SEARCH ANALYZER(doc.message IN TOKENS(@query, "{TEXT_ANALYZER}"))
                OR ANALYZER(doc.exception.value IN TOKENS(@query, "{TEXT_ANALYZER}"))
                OR ANALYZER(doc.extra.payload IN TOKENS(@query, "{TEXT_ANALYZER}"))
                OR ANALYZER(doc.log_category IN TOKENS(@query, "{TEXT_ANALYZER}"))
                LET score = BM25(doc)
                SORT score DESC
                LIMIT @offset, @limit
                RETURN {{ doc: doc, score: score }}
            """
            bind_vars = {"query": text_query, "limit": limit, "offset": offset}
            try:
                # ArangoDB client methods are synchronous, use to_thread in async contexts
                cursor = self._db.aql.execute(aql, bind_vars=bind_vars)
                return list(cursor)
            except AQLQueryExecuteError as e:
                loguru_logger.error(f"BM25 search failed: {e} - Query: {text_query}", exc_info=True)
                return []
            except Exception as e:
                loguru_logger.error(f"Unexpected error during BM25 search: {e}", exc_info=True)
                return []

        def prune(self, days_to_keep: int, log_category: Optional[str] = None, execution_id: Optional[str] = None) -> int:
            """
            AGENT: Delete old log entries from the database.
            Use this to manage log retention and keep your log data clean.
            
            Args:
                days_to_keep: Delete logs older than this many days.
                log_category: Optional filter to prune specific log categories (e.g., "DEBUG", "AGENT_LEARNING").
                execution_id: Optional filter to prune logs from a specific script run.
                
            Returns:
                The number of log documents deleted.
            
            Example:
                `logger.prune(days_to_keep=30)`: Prune all logs older than 30 days.
                `logger.prune(days_to_keep=7, log_category="DEBUG")`: Prune DEBUG logs older than 7 days.
            """
            if self._db is None:
                loguru_logger.error("ArangoDB not connected, cannot prune logs.")
                return 0
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            
            filters = ["l.time < @cutoff_time"]
            bind_vars = {"cutoff_time": cutoff_time.isoformat()}
            
            if log_category:
                filters.append("l.log_category == @log_category")
                bind_vars["log_category"] = log_category
            
            if execution_id:
                filters.append("l.extra.execution_id == @execution_id")
                bind_vars["execution_id"] = execution_id
            
            filter_clause = " AND ".join(filters)
            
            aql = f"""
            FOR l IN {LOG_EVENTS_COLLECTION}
                FILTER {filter_clause}
                REMOVE l IN {LOG_EVENTS_COLLECTION}
                RETURN OLD
            """
            try:
                cursor = self._db.aql.execute(aql, bind_vars=bind_vars)
                deleted_count = len(list(cursor))
                loguru_logger.info(f"Pruned {deleted_count} log entries older than {days_to_keep} days "
                                   f"(category: {log_category}, run: {execution_id}).")
                return deleted_count
            except AQLQueryExecuteError as e:
                loguru_logger.error(f"Failed to prune logs: {e}", exc_info=True)
                return 0
            except Exception as e:
                loguru_logger.error(f"Unexpected error during prune: {e}", exc_info=True)
                return 0

        def start_run(self, script_name: str, mode: str) -> str:
            """
            AGENT: Call this at the very beginning of your script's `if __name__ == "__main__":` block.
            Records the start of a new script execution session.
            
            Args:
                script_name: The name of the script (e.g., `Path(__file__).stem`).
                mode: The execution mode ("working" or "debug").
            
            Returns:
                A unique `execution_id` for this script run. You must `logger.bind(execution_id=execution_id)`
                for all subsequent logs within this run.
            """
            execution_id = f"{script_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"
            run_doc = {
                "_key": execution_id, # Use execution_id as _key for direct access
                "script_name": script_name,
                "start_time": datetime.now(timezone.utc).isoformat(),
                "mode": mode,
                "status": "running"
            }
            if self._db:
                try:
                    self._db.collection(SCRIPT_RUNS_COLLECTION).insert(run_doc)
                    loguru_logger.info(f"Started script run: {script_name} ({mode}) with execution_id: {execution_id}")
                except DocumentInsertError as e:
                    loguru_logger.error(f"Failed to record script run start for {script_name}: {e}")
            return execution_id

        def end_run(self, execution_id: str, success: bool):
            """
            AGENT: Call this at the very end of your script's `if __name__ == "__main__":` block.
            Updates the status of a script execution session.
            
            Args:
                execution_id: The unique ID returned by `start_run()`.
                success: True if the script completed successfully, False otherwise.
            """
            if self._db is None: return
            update_data = {
                "end_time": datetime.now(timezone.utc).isoformat(),
                "status": "success" if success else "failed"
            }
            try:
                self._db.collection(SCRIPT_RUNS_COLLECTION).update(execution_id, update_data)
                loguru_logger.info(f"Ended script run: {execution_id} with status: {update_data['status']}")
            except Exception as e:
                loguru_logger.error(f"Failed to record script run end for {execution_id}: {e}")

        def log_agent_learning(self, message: str, function_name: Optional[str] = None):
            """
            AGENT: Use this method to explicitly log lessons learned during debugging,
            insights gained, or complex steps taken during problem-solving.
            These messages are tagged for easy retrieval.
            
            Args:
                message: The lesson/insight learned.
                function_name: The name of the function related to the learning.
            
            Example:
                `logger.log_agent_learning("Redis connection requires port 6379", function_name="connect_redis")`
            """
            context = f"in function '{function_name}'" if function_name else "general"
            loguru_logger.opt(colors=True).info(f"AGENT_LEARNING ({context}): {message}", log_category="AGENT_LEARNING")
        
        def get_latest_response(self, script_name: str, execution_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
            """
            AGENT: Retrieve the full JSON output from the latest (or specific) script execution.
            This is how you get the structured output of your `working_usage()` or `debug_function()`.
            
            Args:
                script_name: The name of the script (e.g., 'my_script').
                execution_id: Optional specific execution_id to retrieve the response from.
            
            Returns:
                The parsed JSON dictionary of the script's final response, or None if not found.
            
            Example:
                `response = logger.get_latest_response('my_data_processor_script')`
            """
            if self._db is None:
                loguru_logger.error("ArangoDB not connected, cannot retrieve latest response.")
                return None
            
            filter_clause = "l.log_category == 'SCRIPT_FINAL_RESPONSE'"
            bind_vars = {}
            
            if execution_id:
                filter_clause += " AND l.extra.execution_id == @execution_id"
                bind_vars["execution_id"] = execution_id
            else:
                # Find the latest successful run if no specific execution_id is given
                latest_run_aql = f"""
                FOR r IN {SCRIPT_RUNS_COLLECTION}
                    FILTER r.script_name == @script_name AND r.status == 'success'
                    SORT r.end_time DESC
                    LIMIT 1
                    RETURN r._key
                """
                latest_run_bind_vars = {"script_name": script_name}
                try:
                    cursor = self._db.aql.execute(latest_run_aql, bind_vars=latest_run_bind_vars)
                    latest_run_id = next(cursor, None)
                    if not latest_run_id:
                        loguru_logger.warning(f"No successful runs found for script '{script_name}' to retrieve latest response.")
                        return None
                    filter_clause += " AND l.extra.execution_id == @latest_run_id"
                    bind_vars["latest_run_id"] = latest_run_id
                except Exception as e:
                    loguru_logger.error(f"Error finding latest script run for {script_name}: {e}", exc_info=True)
                    return None

            aql = f"""
            FOR l IN {LOG_EVENTS_COLLECTION}
                FILTER {filter_clause}
                SORT l.time DESC
                LIMIT 1
                RETURN l.extra.payload
            """
            
            try:
                cursor = self._db.aql.execute(aql, bind_vars=bind_vars)
                payload = next(cursor, None)
                if payload:
                    if isinstance(payload, str):
                        try:
                            return json.loads(payload) # Payload might be stored as string JSON
                        except json.JSONDecodeError:
                            loguru_logger.warning("Latest response payload is string but not valid JSON. Returning raw string.")
                            return {"raw_payload_string": payload}
                    return payload
                loguru_logger.warning(f"No SCRIPT_FINAL_RESPONSE found for script '{script_name}' (Execution ID: {execution_id}).")
                return None
            except AQLQueryExecuteError as e:
                loguru_logger.error(f"Failed to retrieve latest response: {e}", exc_info=True)
                return None
            except Exception as e:
                loguru_logger.error(f"Unexpected error retrieving latest response: {e}", exc_info=True)
                return None

    # Expose a global logger instance for direct import
    logger = AgentLogManager()

    if __name__ == "__main__":
        # --- Self-validation for AgentLogManager ---
        loguru_logger.info("--- Running Self-Validation for AgentLogManager ---")
        
        # Test 1: Initialization and connection
        loguru_logger.info("Test 1: Initialization and database connection.")
        # AgentLogManager is a singleton, it will connect on first instantiation
        if logger._db:
            loguru_logger.success("Test 1: PASSED - AgentLogManager connected to ArangoDB.")
        else:
            loguru_logger.error("Test 1: FAILED - AgentLogManager failed to connect to ArangoDB.")
            sys.exit(1)
        
        # Test 2: Start/End run and log binding
        loguru_logger.info("Test 2: Start/End run and log binding.")
        test_script_name = "test_script_logging"
        test_execution_id = logger.start_run(test_script_name, "debug_mode")
        
        if test_execution_id:
            loguru_logger.success(f"Test 2: PASSED - Started run with ID: {test_execution_id}")
            logger.bind(execution_id=test_execution_id) # Bind for this test run
            logger.info("This is an info message bound to the test execution ID.")
            logger.error("This is an error message for the test execution ID.")
            logger.log_agent_learning("Learned that binding execution_id works!", "test_function_binding")
            
            # Log a dummy final response
            final_response_payload = {"status": "success", "results": {"value": 123}, "test_case": "binding"}
            logger.info("SCRIPT_FINAL_RESPONSE_PAYLOAD", payload=final_response_payload, log_category="SCRIPT_FINAL_RESPONSE")
            
            logger.end_run(test_execution_id, True)
            loguru_logger.success("Test 2: PASSED - Ended run and logged messages.")
        else:
            loguru_logger.error("Test 2: FAILED - Failed to start run.")
            sys.exit(1)
        
        # Give writer task a moment to process logs
        time.sleep(2) 
        
        # Test 3: Querying logs
        loguru_logger.info("Test 3: Querying logs by execution_id.")
        retrieved_logs = logger.query(f"FOR l IN {LOG_EVENTS_COLLECTION} FILTER l.extra.execution_id == @exec_id RETURN l", {"exec_id": test_execution_id})
        
        if len(retrieved_logs) >= 4: # start_run, info, error, learning, final_response
            loguru_logger.success(f"Test 3: PASSED - Retrieved {len(retrieved_logs)} logs for execution ID.")
            # Verify categories
            if any(l['log_category'] == 'AGENT_LEARNING' for l in retrieved_logs) and \
               any(l['log_category'] == 'SCRIPT_FINAL_RESPONSE' for l in retrieved_logs):
                loguru_logger.success("Test 3: PASSED - Agent learning and final response categories found.")
            else:
                loguru_logger.error("Test 3: FAILED - Agent learning or final response categories missing in retrieved logs.")
                sys.exit(1)
        else:
            loguru_logger.error(f"Test 3: FAILED - Expected at least 4 logs, got {len(retrieved_logs)}.")
            sys.exit(1)
        
        # Test 4: Get latest response
        loguru_logger.info("Test 4: Retrieving latest script response.")
        retrieved_response = logger.get_latest_response(test_script_name, execution_id=test_execution_id)
        if retrieved_response == final_response_payload:
            loguru_logger.success("Test 4: PASSED - Retrieved latest script response correctly.")
        else:
            loguru_logger.error(f"Test 4: FAILED - Retrieved response mismatch. Expected: {final_response_payload}, Got: {retrieved_response}")
            sys.exit(1)

        # Test 5: BM25 Search
        loguru_logger.info("Test 5: Performing BM25 search.")
        search_results = logger.search_bm25("test message test_function_binding")
        if len(search_results) >= 2 and any("test_function_binding" in r['doc']['message'] for r in search_results):
            loguru_logger.success(f"Test 5: PASSED - BM25 search found {len(search_results)} relevant logs.")
        else:
            loguru_logger.error(f"Test 5: FAILED - BM25 search did not find expected results. Found {len(search_results)}.")
            sys.exit(1)

        # Test 6: Pruning
        loguru_logger.info("Test 6: Pruning old logs.")
        pruned_count = logger.prune(days_to_keep=0, execution_id=test_execution_id) # Prune only the test run's logs
        if pruned_count >= 4: # Should prune all logs from the test run
            loguru_logger.success(f"Test 6: PASSED - Pruned {pruned_count} logs.")
        else:
            loguru_logger.error(f"Test 6: FAILED - Expected at least 4 logs to be pruned, got {pruned_count}.")
            sys.exit(1)

        # Final Cleanup: Delete the script_runs entry
        if logger._db:
            try:
                logger._db.collection(SCRIPT_RUNS_COLLECTION).delete(test_execution_id)
                loguru_logger.info(f"Cleaned up script_runs entry for {test_execution_id}.")
            except Exception as e:
                loguru_logger.warning(f"Failed to clean up script_runs entry {test_execution_id}: {e}")

        loguru_logger.info("--- All AgentLogManager self-validation tests completed ---")
        sys.exit(0)
    ```

## Phase 4: Python Script Template & Documentation Update

This phase integrates the new logging system into the core Python script template and updates its comprehensive documentation.

### Task 4.1: Update `docs/05_development/PYTHON_SCRIPT_TEMPLATE.md`

This is a major rewrite of the documentation.

*   [ ] **Description:** Rewrite the "Logging Requirements" and "Assessment Requirements" sections to reflect the ArangoDB-backed logging system. Add detailed explanations for `logger.query()`, `logger.search_bm25()`, `logger.prune()`, `logger.start_run()`, `logger.end_run()`, and `logger.log_agent_learning()`. Emphasize how the agent will now retrieve script outputs from the database.
*   **Relevant Files:** `docs/05_development/PYTHON_SCRIPT_TEMPLATE.md` (MODIFIED)
*   **Agent Relevance:** This is the primary guide for the agent when creating new scripts and debugging. Clear, precise instructions are vital.
*   **Key Updates (excerpt):**
    *   **Logging Requirements:**
        *   "Use `loguru` via `agent_log_manager`."
        *   "All logs are stored in ArangoDB's `script_logs` database."
        *   "No more separate error or learning log files; all are in `log_events` collection, categorized by `log_category`."
        *   "Use `logger.start_run()` at script start and `logger.end_run()` at script end."
        *   "Use `logger.bind(execution_id=...)` for all messages within a run."
        *   "Primary script output: `logger.info("SCRIPT_FINAL_RESPONSE_PAYLOAD", payload=your_results, log_category="SCRIPT_FINAL_RESPONSE")`"
        *   "Agent learnings: `logger.log_agent_learning("Lesson...", function_name="...")`"
        *   "Retrieval: `logger.get_latest_response()`, `logger.query()`, `logger.search_bm25()`"
    *   **Assessment Requirements:**
        *   "Claude MUST retrieve the primary JSON output from ArangoDB using `logger.get_latest_response()` or `logger.query()`."
        *   "Agent MUST use `logger.query()` or `logger.search_bm25()` to diagnose errors."
        *   "Agent MUST log lessons learned using `logger.log_agent_learning()`."
    *   **Agent Debugging & Learning Strategy:** This section will be completely re-written to guide the agent through the new ArangoDB-centric debugging workflow.

### Task 4.2: Update Python Script Template (Code Block within Markdown)

The actual runnable Python code template needs to be updated.

*   [ ] **Description:** Modify the Python code block within `PYTHON_SCRIPT_TEMPLATE.md` to use the new `AgentLogManager` for all logging operations. This includes removing old log setup, adding `start_run`/`end_run` calls, and updating `log_final_response`.
*   **Relevant Files:** `docs/05_development/PYTHON_SCRIPT_TEMPLATE.md` (MODIFIED - *specifically the code block within it*)
*   **Agent Relevance:** This is the boilerplate code the agent will copy and adapt.
*   **Key Updates (excerpt from code block):**
    ```python
    # ... (imports)
    # Third-party imports
    # from loguru import logger # REMOVE THIS LINE
    # import redis # Keep if redis is used for non-log functions
    
    # NEW: Import the centralized logger
    from arangodb.core.utils.agent_log_manager import logger, log_agent_learning
    
    # ... (AGENT_TRANSFORMATION_INSTRUCTIONS constant)
    
    # REMOVE OLD LOGURU CONFIGURATION HERE
    # logger.remove()
    # logger.add(sys.stderr, ...)
    # log_dir = Path(__file__).parent / "logs" # REMOVE
    # ... (all file-based logger.add calls) ...
    
    # No direct loguru configuration needed here; AgentLogManager handles it.
    
    # ... (Redis connection - keep as is if Redis functionality is separate from logging)
    
    # ... (CORE FUNCTIONS - logger calls updated to use the new logger instance)
    
    # NEW: Modified save_results to log to ArangoDB, not file
    def log_final_response(results: Dict[str, Any]) -> None:
        """
        AGENT: This function logs the primary script output to ArangoDB.
        The agent can retrieve this using `logger.get_latest_response()`.
        """
        logger.info("Script's final primary response.", 
                    payload=results, # Store results in 'extra'
                    log_category="SCRIPT_FINAL_RESPONSE")
        logger.info(f"Primary script response has been logged to ArangoDB.")
    
    # ... (working_usage and debug_function - ensure they call `log_final_response` and `log_agent_learning`)
    
    if __name__ == "__main__":
        import sys
        
        # AGENT: Start a new script run and get its unique ID
        script_name = Path(__file__).stem
        mode = sys.argv[1] if len(sys.argv) > 1 else "working"
        
        execution_id = logger.start_run(script_name, mode)
        # AGENT: CRITICAL: Bind the execution_id to ALL subsequent logs for this run
        logger.bind(execution_id=execution_id)
        
        logger.info(f"Script starting in '{mode.upper()}' mode...")
        log_agent_learning(f"Script initiated in '{mode}' mode.", function_name="__main__")
    
        success = False
        try:
            if mode == "debug":
                success = asyncio.run(debug_function())
            else:
                success = asyncio.run(working_usage())
        except Exception as e:
            logger.critical(f"An unhandled critical error occurred during script execution in '{mode}' mode: {e}", exc_info=True)
            log_agent_learning(f"CRITICAL: Unhandled exception in main execution block for '{mode}' mode: {e}.", function_name="__main__")
    
        # AGENT: End the script run with its final status
        exit_code = 0 if success else 1
        logger.end_run(execution_id, success)
        
        logger.info(f"Script finished with exit code {exit_code}.")
        log_agent_learning(f"Script execution completed with exit code {exit_code}.", function_name="__main__")
        exit(exit_code)
    ```

## Phase 5: Agent-Facing Instructions for Existing Modules & Prompts Directory

This phase ensures the agent knows how to interact with the broader codebase and provides helper prompts.

### Task 5.1: Create `prompts/` Directory

*   [ ] **Description:** Create an empty `prompts/` directory at the top level of the project.
*   **Relevant Files:** `prompts/` (NEW Directory)
*   **Agent Relevance:** This is where the agent will look for pre-written complex task instructions.

### Task 5.2: Create `prompts/create_edge_relationship.md` Helper Prompt

This prompt will guide the agent to perform a complex task using multiple modules.

*   [ ] **Description:** Create a Markdown file in the `prompts/` directory that provides step-by-step instructions for the agent to create an edge relationship in the graph database. This will involve:
    *   Querying the log database for relevant `log_events` (using `logger.query` or `logger.search_bm25`).
    *   Identifying `_id`s from those `log_events`.
    *   Calling a function from `src/arangodb/core/graph/enhanced_relationships.py` (e.g., `create_temporal_relationship`) using the extracted `_id`s, specifying `_from`, `_to`, `type`, and a `rationale`.
    *   Logging its action and rationale using `logger.log_agent_learning()`.
*   **Relevant Files:** `prompts/create_edge_relationship.md` (NEW)
*   **Agent Relevance:** Provides a concrete, executable example for a complex graph operation, demonstrating how to combine search, data extraction, and graph function calls.
*   **Code Example (excerpt from prompt):**
    ```markdown
    # AGENT_PROMPT: Create a Custom Graph Edge Between Log Events

    **GOAL:** Establish a new, explicit relationship between two specific log entries
    in the `log_events` collection, based on a lesson learned or a detected pattern.

    **CONTEXT:** You've identified that `log_event_A` (e.g., an error message)
    `CAUSED` `log_event_B` (e.g., a subsequent debugging attempt, or another error).

    **STEPS:**

    1.  **Retrieve Log Event IDs:**
        First, identify the `_id` of the source and target log events. You can use
        `logger.search_bm25()` or `logger.query()` to find them.

        Example AQL to find recent error:
        ```aql
        FOR l IN log_events
        FILTER l.level.name == 'ERROR' AND CONTAINS(l.message, 'connection refused')
        SORT l.time DESC LIMIT 1
        RETURN { id: l._id, message: l.message }
        ```
        *ACTION:* Execute the AQL query above or a `logger.search_bm25()` call to get the `_id`s.
        *EXAMPLE PYTHON EXECUTION:*
        ```python
        # Agent's script, or interactive session
        from arangodb.core.utils.agent_log_manager import logger
        
        # Example: Find a specific error event
        error_search_results = logger.search_bm25("Redis connection refused", limit=1)
        if error_search_results:
            source_log_id = error_search_results[0]['doc']['_id']
            logger.log_agent_learning(f"Identified source log ID: {source_log_id}", function_name="create_edge_prompt")
        else:
            logger.error("Could not find source log event. Aborting edge creation.")
            exit(1)
        
        # Example: Find a related log event (e.g., subsequent warning from the same run)
        # You would adapt this to find your target log event.
        target_search_results = logger.search_bm25("Redis not available - some features will be limited", limit=1)
        if target_search_results:
            target_log_id = target_search_results[0]['doc']['_id']
            logger.log_agent_learning(f"Identified target log ID: {target_log_id}", function_name="create_edge_prompt")
        else:
            logger.error("Could not find target log event. Aborting edge creation.")
            exit(1)
        ```

    2.  **Import Edge Creation Utility:**
        *ACTION:* Ensure you have imported `create_temporal_relationship` from the correct module.
        *EXAMPLE PYTHON IMPORT:*
        ```python
        from arangodb.core.graph.enhanced_relationships import create_temporal_relationship
        # Ensure 'db' object is available (e.g., from AgentLogManager's internal connection or passed)
        # For simplicity in prompts, assume AgentLogManager's _db is accessible for advanced ops,
        # or that a helper function would provide it.
        # For this context, assume the agent could access it via logger._db (for advanced scenarios only).
        db_instance = logger._db 
        ```

    3.  **Define Edge Attributes:**
        Decide on the `relationship_type` (e.g., "CAUSED", "FOLLOWS", "RELATED_TO") and provide a `rationale` (min 50 chars).

    4.  **Create the Edge Relationship:**
        *ACTION:* Call `create_temporal_relationship` with the extracted IDs and chosen attributes.
        *EXAMPLE PYTHON EXECUTION:*
        ```python
        # ... (assuming source_log_id, target_log_id, and db_instance are defined from above steps)
        
        new_edge = create_temporal_relationship(
            db=db_instance,
            edge_collection="log_relations", # A new edge collection specific to log relationships
            from_id=source_log_id,
            to_id=target_log_id,
            relationship_type="CAUSED_BY",
            rationale="The Redis connection refused error (source_log) directly caused the features limited warning (target_log). This indicates a cascading failure.",
            attributes={"confidence": 0.9, "agent_inferred": True}
        )
        
        if new_edge:
            logger.log_agent_learning(
                f"Created new graph edge from {source_log_id} to {target_log_id} (Type: CAUSED_BY). Edge ID: {new_edge['_id']}",
                function_name="create_edge_prompt"
            )
            logger.info("Successfully created relationship. You can now query your graph for this connection.")
        else:
            logger.error("Failed to create the graph edge. Check logs for details.")
        ```

    5.  **Verify the Edge (Optional but Recommended):**
        *ACTION:* Query the edge collection to confirm the edge was created.
        *EXAMPLE AQL:*
        ```aql
        FOR e IN log_relations
        FILTER e._from == '<YOUR_SOURCE_LOG_ID>' AND e._to == '<YOUR_TARGET_LOG_ID>'
        RETURN e
        ```
    ```

### Task 5.3: Add `AGENT_INSTRUCTIONS` to Relevant Existing Modules (`__init__.py` files for package overview)

Provide high-level guidance for agent understanding and use of existing code.

*   [ ] **Description:** Add a prominent `AGENT_INSTRUCTIONS` section to the top-level docstring of key `__init__.py` files in `src/arangodb/core/graph`, `src/arangodb/core/search`, and `src/arangodb/core/memory`. These instructions will explain the package's purpose from an agent's perspective and guide general usage.
*   **Relevant Files:**
    *   `src/arangodb/core/graph/__init__.py` (MODIFIED)
    *   `src/arangodb/core/search/__init__.py` (MODIFIED)
    *   `src/arangodb/core/memory/__init__.py` (MODIFIED)
*   **Agent Relevance:** Helps the agent quickly grasp the purpose of major code sections without deep diving into every file. Provides import guidance.
*   **Code Example (."""
                if self._db is None:
                    self._connect_db()
                    if self._db is None:
                        raise Exception("ArangoDB connection not available for logging operations.")
                # Basic check for collections (assuming arango_init.py was run)
                if not self._db.has_collection(LOG_EVENTS_COLLECTION):
                    raise Exception(f"Log collection '{LOG_EVENTS_COLLECTION}' not found. Run arango_init.py.")
                if not self._db.has_collection(SCRIPT_RUNS_COLLECTION):
                    raise Exception(f"Script runs collection '{SCRIPT_RUNS_COLLECTION}' not found. Run arango_init.py.")
        
            # --- Agent-Facing "CRUD" Methods ---
        
            def query_logs(self, aql_query: str, bind_vars: Optional[dict] = None) -> list:
                """
                AGENT: Executes an AQL query against the ArangoDB log database.
                This is the primary way for agents to retrieve structured log data.
                """
                self._ensure_db_and_collections()
                loguru_logger.debug(f"Executing AQL query: {aql_query[:100]}...")
                try:
                    cursor = self._db.aql.execute(aql_query, bind_vars=bind_vars)
                    results = list(cursor)
                    loguru_logger.debug(f"AQL query returned {len(results)} results.")
                    return results
                except Exception as e:
                    loguru_logger.error(f"Failed to execute AQL query on logs: {e}. Query: {aql_query}", exc_info=True)
                    return []
        
            def search_bm25_logs(self, text_query: str, limit: int = 10, offset: int = 0) -> list:
                """
                AGENT: Performs a full-text (BM25-like) search across log messages.
                Useful for finding log entries related to a specific topic or keyword.
                """
                self._ensure_db_and_collections()
                loguru_logger.debug(f"Performing BM25 search for: '{text_query}'")
                aql = f"""
                FOR doc IN {LOG_EVENTS_VIEW}
                SEARCH ANALYZER(doc.message IN TOKENS(@text_query, "text_en"), "text_en")
                OR ANALYZER(doc.extra.payload IN TOKENS(@text_query, "text_en"), "text_en")
                OR ANALYZER(doc.exception.value IN TOKENS(@text_query, "text_en"), "text_en")
                SORT BM25(doc) DESC
                LIMIT @offset, @limit
                RETURN {{ doc: doc, score: BM25(doc) }}
                """
                bind_vars = {"text_query": text_query, "limit": limit, "offset": offset}
                return self.query_logs(aql, bind_vars)
        
            def prune_logs(self, days_to_keep: int, log_category: Optional[str] = None, execution_id: Optional[str] = None) -> int:
                """
                AGENT: Deletes log entries older than a specified number of days.
                Can be filtered by log category or specific script execution ID.
                """
                self._ensure_db_and_collections()
                loguru_logger.info(f"Pruning logs older than {days_to_keep} days. Category: {log_category}, Execution ID: {execution_id}")
                
                cutoff_datetime = datetime.now() - timedelta(days=days_to_keep)
                cutoff_iso = cutoff_datetime.isoformat()
        
                filters = ["doc.timestamp < @cutoff_iso"]
                bind_vars = {"cutoff_iso": cutoff_iso}
        
                if log_category:
                    filters.append("doc.log_category == @log_category")
                    bind_vars["log_category"] = log_category
                if execution_id:
                    filters.append("doc.extra.execution_id == @execution_id")
                    bind_vars["execution_id"] = execution_id
        
                filter_clause = " AND ".join(filters)
        
                aql = f"""
                FOR doc IN {LOG_EVENTS_COLLECTION}
                FILTER {filter_clause}
                REMOVE doc IN {LOG_EVENTS_COLLECTION}
                RETURN OLD._key
                """
                try:
                    cursor = self._db.aql.execute(aql, bind_vars=bind_vars)
                    deleted_count = len(list(cursor))
                    loguru_logger.info(f"Pruned {deleted_count} log entries.")
                    return deleted_count
                except Exception as e:
                    loguru_logger.error(f"Failed to prune logs: {e}", exc_info=True)
                    return 0
        
            def get_latest_response(self, script_name: str, execution_id: Optional[str] = None) -> Optional[dict]:
                """
                AGENT: Retrieves the primary JSON output from the latest run of a specific script.
                Looks for logs with log_category="SCRIPT_FINAL_RESPONSE" and extracts the payload.
                """
                self._ensure_db_and_collections()
                loguru_logger.debug(f"Getting latest response for script: {script_name}, execution_id: {execution_id}")
        
                filters = [
                    "l.log_category == 'SCRIPT_FINAL_RESPONSE'",
                    "l.file == @script_name" # file.name from log record
                ]
                bind_vars = {
                    "script_name": script_name # Assuming script_name is the file.name
                }
                if execution_id:
                    filters.append("l.extra.execution_id == @execution_id")
                    bind_vars["execution_id"] = execution_id
                
                filter_clause = " AND ".join(filters)
        
                aql = f"""
                FOR l IN {LOG_EVENTS_COLLECTION}
                FILTER {filter_clause}
                SORT l.timestamp DESC
                LIMIT 1
                RETURN l.extra.payload
                """
                try:
                    cursor = self._db.aql.execute(aql, bind_vars=bind_vars)
                    result = next(cursor, None)
                    if result:
                        loguru_logger.success(f"Retrieved latest response for {script_name}.")
                    else:
                        loguru_logger.warning(f"No SCRIPT_FINAL_RESPONSE found for {script_name}.")
                    return result
                except Exception as e:
                    loguru_logger.error(f"Failed to get latest response for {script_name}: {e}", exc_info=True)
                    return None
        
            def log_agent_learning(self, message: str, function_name: Optional[str] = None):
                """
                AGENT: Logs a specific lesson, insight, or debugging step learned by the agent.
                These messages are tagged with 'AGENT_LEARNING' for easy retrieval.
                """
                context = f"in function '{function_name}'" if function_name else "general"
                # Use the main logger, binding a special category
                loguru_logger.info(f"AGENT_LEARNING ({context}): {message}", log_category="AGENT_LEARNING", function=function_name)
        
            def start_run(self, script_name: str, mode: str = "working") -> str:
                """
                AGENT: Records the start of a new script execution.
                Returns a unique `execution_id` to link all subsequent log messages.
                """
                self._ensure_db_and_collections()
                execution_id = f"run_{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.getpid()}_{threading.get_ident()}"
                
                run_doc = {
                    "_key": execution_id, # Use execution_id as _key for direct lookup
                    "script_name": script_name,
                    "start_time": datetime.now().isoformat(),
                    "mode": mode,
                    "status": "running",
                    "pid": os.getpid(),
                    "thread_id": threading.get_ident(),
                    "messages_logged": 0 # Initial count
                }
                try:
                    self._db.collection(SCRIPT_RUNS_COLLECTION).insert(run_doc)
                    loguru_logger.info(f"Started script run '{script_name}' in '{mode}' mode. Execution ID: {execution_id}")
                    return execution_id
                except Exception as e:
                    loguru_logger.error(f"Failed to record start of script run '{script_name}': {e}", exc_info=True)
                    return f"ERROR_{execution_id}" # Return error-prefixed ID
        
            def end_run(self, execution_id: str, success: bool):
                """
                AGENT: Records the end of a script execution and its final status.
                """
                self._ensure_db_and_collections()
                loguru_logger.info(f"Ending script run '{execution_id}' with status: {'SUCCESS' if success else 'FAILURE'}")
                update_doc = {
                    "end_time": datetime.now().isoformat(),
                    "status": "completed" if success else "failed",
                }
                
                try:
                    # Count messages logged for this run
                    message_count_aql = f"""
                    RETURN LENGTH(
                        FOR l IN {LOG_EVENTS_COLLECTION}
                        FILTER l.extra.execution_id == @execution_id
                        RETURN 1
                    )
                    """
                    message_count = self.query_logs(message_count_aql, {"execution_id": execution_id})
                    if message_count:
                        update_doc["messages_logged"] = message_count[0]
        
                    self._db.collection(SCRIPT_RUNS_COLLECTION).update(execution_id, update_doc)
                    loguru_logger.success(f"Script run '{execution_id}' record updated in ArangoDB.")
                except Exception as e:
                    loguru_logger.error(f"Failed to update end of script run '{execution_id}': {e}", exc_info=True)
        
        # --- Instantiate the singleton and expose its logger and methods ---
        _log_manager = AgentLogManager()
        
        # Expose the configured logger
        logger = _log_manager.logger
        
        # Expose "CRUD" and helper methods directly
        log_agent_learning = _log_manager.log_agent_learning
        start_run = _log_manager.start_run
        end_run = _log_manager.end_run
        query_logs = _log_manager.query_logs
        search_bm25_logs = _log_manager.search_bm25_logs
        prune_logs = _log_manager.prune_logs
        get_latest_response = _log_manager.get_latest_response
        
        # --- Graceful Shutdown Hook ---
        # Ensure remaining logs are flushed on exit
        import atexit
        atexit.register(stop_writer_thread)
        ```
    *   **Agent/Human Instructions:** This file is an *internal* utility for the agent. Agents primarily interact with the exposed `logger` object and its methods (like `start_run`, `query_logs`, etc.). The provided instructions in its docstring are how to import and use these features.

## Phase 3: Python Script Template Integration & Agent Instructions

This phase modifies the core template for agents to use the new logging system.

*   [ ] **Task 3.1: Update `docs/05_development/PYTHON_SCRIPT_TEMPLATE.md`**
    *   **Description:** The main template for Python scripts will be updated to fully integrate the new `AgentLogManager` and reflect the database-centric logging strategy.
    *   **Key Changes (Snippets from the `.md` file, for context, the full file would be generated later):**
        *   **Module Docstring / Usage Instructions:**
            ```markdown
            === USAGE INSTRUCTIONS FOR AGENTS ===
            Run this script directly to test:
              python script.py          # Runs working_usage() - stable, known to work
              python script.py debug    # Runs debug_function() - for testing new ideas

            DO NOT create separate test/run files! Use the debug function!

            AGENT: When running this script, refer to the `AGENT_TRANSFORMATION_INSTRUCTIONS`
            and the comprehensive `AGENT_LOGGING_GUIDE` (in the `prompts/` directory) for detailed
            debugging, introspection, and learning strategies using the ArangoDB logging system.
            ```
        *   **Imports:**
            ```python
            # Third-party imports
            # CRITICAL: Use the centralized logger from AgentLogManager
            from src.arangodb.core.utils.agent_log_manager import logger, log_agent_learning, start_run, end_run, query_logs, search_bm25_logs, prune_logs, get_latest_response
            import redis
            ```
        *   **Removed Loguru Sinks:** Delete all `logger.add()` calls for file sinks (e.g., `log_dir / ... .log`). The `AgentLogManager` handles all `loguru` configuration. Keep only the `sys.stderr` sink if that's desired for console output, but the `AgentLogManager` already sets up a default console sink. So, **all `logger.add()` configurations should be removed from the template.**
        *   **`save_results` Function (Renamed to `log_final_response`):**
            ```python
            def log_final_response(results: Dict[str, Any]) -> None:
                """
                AGENT: Logs the primary JSON response of the script to ArangoDB.
                This output is categorized for easy retrieval by the agent.
                
                Args:
                    results: The final results dictionary to log.
                """
                # CRITICAL: Log the final structured output to ArangoDB.
                # The 'payload' in extra will be stored as a subfield for later querying.
                logger.info("SCRIPT_FINAL_RESPONSE", payload=results, log_category="SCRIPT_FINAL_RESPONSE")
                logger.success("Primary script response has been logged to ArangoDB.")
            ```
        *   **`working_usage` / `debug_function`:** Call `log_final_response(results)` at the end of successful execution.
        *   **`__main__` Block:**
            ```python
            if __name__ == "__main__":
                """
                Script entry point with TWO usage functions.
                ...
                IMPORTANT: See AGENT_TRANSFORMATION_INSTRUCTIONS constant at the top of this file!
                The transformation rules are defined there for agents to apply to the output.
                
                AGENT: All script executions are now logged to ArangoDB.
                The 'execution_id' links all messages from this run.
                """
                import sys
                from pathlib import Path # Ensure Path is imported if not already
                
                # Choose which function to run
                mode = sys.argv[1] if len(sys.argv) > 1 else "working"
                
                # AGENT: Start a new script run in ArangoDB logs
                script_name = Path(__file__).stem
                execution_id = start_run(script_name, mode)
                # AGENT: Bind the execution ID to all subsequent log messages in this run
                logger = logger.bind(execution_id=execution_id) # Re-bind logger with execution_id
                
                logger.info(f"Script '{script_name}' starting in '{mode.upper()}' mode. Execution ID: {execution_id}")
                log_agent_learning(f"Script initiated in '{mode}' mode.", function_name="__main__")

                success = False
                try:
                    if mode == "debug":
                        success = asyncio.run(debug_function())
                    else:
                        success = asyncio.run(working_usage())
                except Exception as e:
                    logger.critical(f"An unhandled critical error occurred during script execution in '{mode}' mode: {e}")
                    logger.exception("CRITICAL: Unhandled exception in main execution block:")
                    log_agent_learning(f"CRITICAL: Unhandled exception in main execution block for '{mode}' mode: {e}.", function_name="__main__")

                # Exit with appropriate code
                exit_code = 0 if success else 1
                logger.info(f"Script finished with exit code {exit_code}.")
                log_agent_learning(f"Script execution completed with exit code {exit_code}.", function_name="__main__")
                # AGENT: End the script run record in ArangoDB
                end_run(execution_id, success)
                exit(exit_code)
            ```
        *   **Assessment Requirements:** Update to reflect querying logs from ArangoDB instead of reading `/tmp/responses/` files.
            *   `Output filename format` section will be replaced/modified significantly.
            *   `AUTOMATIC FAILURE CONDITIONS`: Will include "Primary script output is not logged to ArangoDB with correct tags".
            *   `THE ASSESSMENT PROCESS`: "Claude MUST Query the ArangoDB log database... to locate and parse the actual output (via `get_latest_response` or AQL query)."

*   [ ] **Task 3.2: Create `prompts/` directory**
    *   **Description:** A new top-level directory for agent-specific helper prompts and guides.
    *   **Structure:**
        ```
        project_root/
        ├── prompts/
        │   ├── AGENT_LOGGING_GUIDE.md
        │   └── create_edge_relationship.md
        ├── src/
        │   └── arangodb/
        │       └── core/
        │           ├── graph/
        │           │   └── ... (existing graph modules)
        │           └── utils/
        │               ├── arango_init.py
        │               └── agent_log_manager.py
        └── docs/
            └── 05_development/
                └── PYTHON_SCRIPT_TEMPLATE.md
        ```

*   [ ] **Task 3.3: Create `prompts/AGENT_LOGGING_GUIDE.md`**
    *   **Description:** A comprehensive Markdown guide for the agent on how to use the new ArangoDB logging system for debugging, introspection, and learning.
    *   **Content:**
        ```markdown
        # AGENT: Comprehensive Logging and Debugging Guide (ArangoDB Backed)

        ## Overview

        This guide details how to effectively use the new ArangoDB-backed logging system to debug,
        introspect, and learn from your Python script executions. All log messages, script outputs,
        errors, and your own learnings are now centralized in ArangoDB, making them highly
        queryable and searchable.

        ## Key Concepts

        *   **Centralized Logs:** All logs (DEBUG, INFO, WARNING, ERROR, CRITICAL), script outputs,
            and your recorded learnings are stored in the `script_logs` database in ArangoDB's
            `log_events` collection.
        *   **`execution_id`:** Every script run is assigned a unique `execution_id`. This ID links
            all log messages generated during that specific run, allowing you to trace an entire
            script's lifecycle.
        *   **`log_category`:** Custom tags (like `SCRIPT_FINAL_RESPONSE` or `AGENT_LEARNING`) are
            used to categorize log entries, making specific types of information easy to retrieve.
        *   **"CRUD"-like API:** The `logger` object (imported from `src.arangodb.core.utils.agent_log_manager`)
            now has powerful methods for querying (`query_logs`, `search_bm25_logs`), retrieving
            specific outputs (`get_latest_response`), and managing data (`prune_logs`).
        *   **Graph Potential:** While the logger doesn't automatically create graph edges, the
            structured data (e.g., `execution_id`, `function_name`, `log_category`) allows you
            to infer relationships and *build* graph connections (using tools in `src/arangodb/core/graph`)
            for deeper analysis if needed.

        ## Core Agent Workflow for Debugging and Learning

        ### 1. Starting and Ending a Script Run (Mandatory)

        *   **Purpose:** To create a clear, traceable record for each script execution.
        *   **Action:**
            *   At the very beginning of `if __name__ == "__main__":` in your script:
                ```python
                from pathlib import Path
                # ... other imports ...
                fromexcerpt from `__init__.py`):**
    ```python
    # src/arangodb/core/graph/__init__.py
    """
    Graph Operations Core Module.
    Module: __init__.py
    Description: Package initialization and exports
    
    AGENT_INSTRUCTIONS:
    This package provides tools for managing your Knowledge Graph in ArangoDB.
    Use these functions to create, query, and analyze relationships between entities
    and other data. You can also build communities and detect contradictions.
    
    Key Functions for Agent Use:
    - `create_temporal_relationship(...)` in `enhanced_relationships`: Use to create
      relationships with a validity period. Crucial for linking log events, errors,
      or learnings in a graph (e.g., linking a learned fact to a resolved error).
    - `resolve_contradiction(...)` in `contradiction_detection`: For resolving conflicting
      information in your graph.
    - `graph_traverse(...)` in `search.graph_traverse`: To explore connections
      between documents or log events.
    - `CommunityBuilder(...)` in `community_building`: To find clusters of related items.
      
    To use: `from arangodb.core.graph import create_temporal_relationship` (or other functions).
    """
    # ... (existing imports and code)
    ```
    (Similar updates for `search/__init__.py` and `memory/__init__.py`)

### Task 5.4: Add `AGENT_INSTRUCTIONS` to Key Utility Modules (`.py` files with main agent functions)

Provide detailed usage instructions for specific functions within modules.

*   [ ] **Description:** For key, independently runnable or frequently imported/called utility modules, add an `AGENT_INSTRUCTIONS` section in their top-level docstring. This will detail their purpose, how to run their `if __name__ == "__main__":` block for testing/validation, and how to use their primary functions from other scripts.
*   **Relevant Files (selection of critical ones, not exhaustive across all provided files):**
    *   `src/arangodb/core/arango_setup.py` (MODIFIED) - How to setup DB, collections, views.
    *   `src/arangodb/core/graph/enhanced_relationships.py` (MODIFIED) - How to create temporal relations, important for linking log entries in graph.
    *   `src/arangodb/core/graph/relationship_extraction.py` (MODIFIED) - How to extract relationships from text, can be used on log messages.
    *   `src/arangodb/core/memory/memory_agent.py` (MODIFIED) - How to store and search conversations.
    *   `src/arangodb/core/utils/embedding_utils.py` (MODIFIED) - How to generate embeddings.
    *   `src/arangodb/core/utils/config_validator.py` (MODIFIED) - How to validate config.
    *   `src/arangodb/core/utils/error_handler.py` (MODIFIED) - How to understand error types/decorators.
    *   `src/arangodb/core/utils/test_reporter.py` (MODIFIED) - How to generate validation reports.
*   **Agent Relevance:** Directly guides the agent in using specific tools and understanding their role.
*   **Code Example (excerpt from a utility file):**
    ```python
    # src/arangodb/core/graph/enhanced_relationships.py
    """
    Enhanced Relationship Operations for ArangoDB with Temporal Metadata.
    Module: enhanced_relationships.py
    Description: Functions for enhanced relationships operations
    
    AGENT_INSTRUCTIONS:
    This module is crucial for creating and managing relationships in your Knowledge Graph,
    especially for bi-temporal data (tracking when a fact was true, and when it was recorded).
    
    Use `create_temporal_relationship()` to add connections between entities or log events.
    This function automatically handles temporal metadata and checks for contradictions.
    
    Key Functions for Agent Use:
    - `create_temporal_relationship(db, edge_collection, from_id, to_id, relationship_type, ...)`:
        *   **Purpose:** Create a new directed edge (relationship).
        *   **CRITICAL for Agent Learning:** Use this to define explicit links between log entries,
            errors, and agent learnings in the graph (e.g., `(ErrorEvent)-[CAUSED_BY]->(AgentLearning)`).
            You will need to identify the `_id` of the relevant `log_events` from the `log_events` collection.
        *   **Input:** `db` (your ArangoDB database instance, from `logger._db` for advanced ops),
                   `edge_collection` (e.g., "log_relations" - a new collection for these edges),
                   `from_id` (full ArangoDB `_id` of source document/log_event),
                   `to_id` (full ArangoDB `_id` of target document/log_event),
                   `relationship_type` (e.g., "CAUSED_BY", "RESOLVED_BY", "MENTIONED_IN").
        *   **Output:** The created edge document.
    - `invalidate_edge(db, edge_collection, edge_key, ...)`:
        *   **Purpose:** Mark an existing edge as no longer valid.
    
    Running this module directly (`python enhanced_relationships.py`) will perform validation tests
    to ensure its functionality.
    """
    # ... (existing code)
    ```
    (Similar updates for other selected modules).

---

This comprehensive plan ensures that the new logging system is not only technically robust but also provides explicit, actionable instructions for the agent across its entire interaction surface, from setup to complex graph reasoning.