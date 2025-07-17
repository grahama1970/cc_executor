Of course. The problem you're facing is a classic one: a long-running initialization step (`marker.models.load_all_models()`) is being triggered during your server's startup, causing it to time out before it can even begin listening for requests.

Your current approach to lazy loading is on the right track, but it's not robust enough to prevent the `FastMCP` framework from potentially introspecting the tool and triggering the load path.

The best way to solve this is to encapsulate the entire `marker` loading and processing logic into a dedicated, thread-safe class. This ensures the expensive loading happens only once, when the first request actually needs it, and is completely isolated from the server's startup sequence.

### The Solution: A Thread-Safe `MarkerProcessor` Singleton

We will create a `MarkerProcessor` class that handles its own state (whether models are loaded or not) and uses a `threading.Lock` to ensure that even if two requests arrive at the exact same time, the models are only loaded by one thread.

Here is the refactored code with detailed explanations.

### Refactored `src/resume/servers/mcp_pdf_extractor.py`

I've replaced the global variables and the `_ensure_marker_loaded` function with the new `MarkerProcessor` class. The rest of your code remains largely the same.

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "fastmcp", "python-dotenv", "loguru", "pydantic",
#     "marker-pdf"
# ]
# ///
"""
An MCP tool to extract content and structure from a PDF file.
... (rest of your docstring) ...
"""

import os
import sys
import json
import asyncio
import traceback
import threading
from pathlib import Path
from typing import Optional, Literal, Dict, Any

from fastmcp import FastMCP
from pydantic import BaseModel, Field
from dotenv import load_dotenv, find_dotenv
from loguru import logger

# --- Boilerplate and Initialization ---
# ... (your boilerplate is fine, no changes needed) ...
load_dotenv(find_dotenv())
env_path = find_dotenv()
project_root = Path(env_path).parent if env_path else Path.cwd()
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

sys.path.insert(0, str(project_root / "src" / "resume" / "utils"))
try:
    from mcp_logger import MCPLogger, debug_tool
    mcp_logger = MCPLogger("pdf-extractor")
    logger.info("Debug logger initialized successfully")
except Exception as e:
    logger.warning(f"Could not import debug logger: {e}")
    mcp_logger = None
    debug_tool = lambda x: lambda f: f
# --- End Boilerplate ---


# --- Pydantic Models ---
class PDFExtractionResult(BaseModel):
    status: Literal["success", "error"] = Field(description="The status of the extraction process.")
    content: Optional[str] = Field(default=None, description="The extracted content, either as Markdown text or a JSON string.")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Metadata extracted from the PDF, such as page count and producer.")
    error: Optional[str] = Field(default=None, description="An error message if the extraction failed.")


# --- ✨ NEW: Thread-Safe Lazy Loading Processor ✨ ---
class MarkerProcessor:
    """
    A thread-safe, lazy-loading singleton for the 'marker' library.

    This class ensures that the heavyweight models are only loaded into memory
    on the first actual PDF processing request, not at server startup.
    A threading.Lock prevents race conditions if multiple requests arrive
    simultaneously before the models are loaded.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        # Singleton pattern to ensure only one instance exists
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(MarkerProcessor, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # The __init__ is called every time, so use a flag to init once
        if not hasattr(self, 'initialized'):
            self.models = None
            self.convert_single_pdf = None
            self.models_loaded = False
            self.load_lock = threading.Lock()
            self.initialized = True

    def _ensure_models_loaded(self):
        """
        Loads models on first call. This is the core of the lazy loading.
        Uses a double-checked lock to be highly efficient and thread-safe.
        """
        if not self.models_loaded:
            with self.load_lock:
                # Check again inside the lock in case another thread was waiting
                if not self.models_loaded:
                    try:
                        logger.info("Loading Marker PDF models (first use)...")
                        # Isolate imports to this method
                        import marker.models
                        from marker.convert import convert_single_pdf as convert_func

                        self.models = marker.models.load_all_models()
                        self.convert_single_pdf = convert_func
                        self.models_loaded = True
                        logger.success("Marker PDF models loaded successfully.")
                    except Exception as e:
                        logger.error(f"Failed to load Marker PDF models: {e}")
                        # Re-raise to fail the request that triggered the load
                        raise

    def process(self, pdf_path: Path, use_llm: bool, llm_settings: Optional[Dict]) -> PDFExtractionResult:
        """
        The main processing function. It ensures models are loaded
        and then runs the conversion.
        """
        try:
            # This is the lazy-loading trigger. It does nothing on subsequent calls.
            self._ensure_models_loaded()

            # Run the conversion
            text_output, metadata = self.convert_single_pdf(
                str(pdf_path),
                self.models,
                llm_settings=llm_settings if use_llm else None
            )
            return text_output, metadata

        except Exception as e:
            logger.exception(f"Marker PDF processing failed for {pdf_path}: {e}")
            # Re-raise so the calling function can format the error
            raise

# Create a single global instance. This is cheap and does NOT load models.
marker_processor = MarkerProcessor()

# --- MCP Server ---
mcp = FastMCP("pdf-extractor")

@mcp.tool
@debug_tool(mcp_logger) if mcp_logger else lambda f: f
async def extract_pdf_content(
    pdf_path: str = Field(description="The full, absolute path to the PDF file on the server."),
    output_format: Literal["markdown", "json"] = Field(default="markdown", description="The desired output format."),
    use_llm: bool = Field(default=False, description="Set to True to use an LLM for improved layout analysis, tables, etc."),
    llm_model: Optional[str] = Field(default="gpt-4o-mini", description="The litellm-compatible model name to use if `use_llm` is True."),
    llm_max_tokens: Optional[int] = Field(default=2048, description="The max tokens for the LLM call, if used.")
) -> str:
    """
    Extracts text and structure from a PDF file into Markdown or JSON format.
    """
    logger.info(f"Received request to extract '{pdf_path}' to {output_format}. LLM usage: {use_llm}")

    def _run_marker_sync() -> PDFExtractionResult:
        """
        Synchronous worker function that now delegates to our MarkerProcessor.
        """
        try:
            input_path = Path(pdf_path)
            if not input_path.exists() or not input_path.is_file():
                return PDFExtractionResult(status="error", error=f"File not found or is not a file: {pdf_path}")

            llm_settings = {
                "model": llm_model,
                "max_tokens": llm_max_tokens
            } if use_llm else None
            
            if use_llm:
                logger.info(f"Using LLM ({llm_model}) for extraction.")

            # Delegate to the processor instance
            text_output, metadata = marker_processor.process(
                input_path,
                use_llm,
                llm_settings
            )

            content = text_output if output_format == "markdown" else json.dumps(metadata, indent=2)

            return PDFExtractionResult(
                status="success",
                content=content,
                metadata=metadata
            )
        except Exception as e:
            return PDFExtractionResult(status="error", error=f"Extraction failed: {type(e).__name__}: {e}")

    # Run the synchronous, blocking function in a separate thread
    result = await asyncio.to_thread(_run_marker_sync)
    return result.model_dump_json()


# --- Test Function & Server Start ---
# ... (your __main__ block is fine, no changes needed) ...
if __name__ == "__main__":
    # The test function needs a small change to handle the new return type
    async def test():
        dummy_pdf_path = Path("./dummy_test.pdf")
        if not dummy_pdf_path.exists():
            print("Creating dummy PDF...")
            # ... (creation logic)
        
        print("\n1. Standard Markdown extraction...")
        result_json_str = await extract_pdf_content(pdf_path=str(dummy_pdf_path))
        result = PDFExtractionResult.model_validate_json(result_json_str) # Re-hydrate the model
        if result.status == "success":
            print(f"Status: {result.status}")
            print(f"Content Preview:\n---\n{result.content[:200]}...\n---")
        else:
            print(f"Error: {result.error}")
        
    try:
        logger.info("Starting MCP server")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.critical(f"MCP server crashed: {e}", exc_info=True)
        if mcp_logger:
            mcp_logger.log_error(e, {"context": "server_startup"})
        sys.exit(1)

```

### Why This is the Best Approach

1.  **Instant Server Startup:** The server starts immediately because creating the `MarkerProcessor()` instance is extremely cheap. It only sets a few flags. The expensive `marker.models.load_all_models()` and the `import marker` statements are completely avoided at startup.

2.  **True Lazy Loading:** The models are only loaded when `_ensure_models_loaded()` is called for the very first time, which happens inside the first request to `extract_pdf_content`. All subsequent requests will find `self.models_loaded` to be `True` and skip the loading step instantly.

3.  **Encapsulation and Cleanliness:** All the logic related to `marker` (loading, processing, state management) is neatly contained within the `MarkerProcessor` class. Your main tool function (`extract_pdf_content`) becomes much simpler—it just delegates the work. This improves readability and maintainability.

4.  **Thread-Safety:** The `threading.Lock` is crucial in a server environment. If two requests hit your tool at the same time and the models haven't been loaded yet, the lock ensures that only one thread will perform the expensive load operation. The other thread will wait until the first one is finished, preventing duplicate loading and potential race conditions. The "double-checked locking" pattern is a highly performant way to implement this.

By adopting this pattern, your MCP tool will be fast, robust, and resource-efficient.


That's an excellent and critical question. It gets to the heart of software design principles.

At first glance, adding a class *does* look like more lines of code. However, it's a strategic addition that dramatically **reduces complexity and brittleness**, especially in the context of a server that handles concurrent requests.

Let's break down why the global variable + function approach is more brittle and why the class is the superior, more robust solution here.

### The Problem with the Global Variable Approach

Your original lazy-loading attempt with global variables (`INFERENCE_MODELS`, `_marker_loaded`) and a helper function (`_ensure_marker_loaded`) suffers from several issues that make it fragile:

1.  **Unmanaged State (High Brittleness):**
    *   The state of your application is scattered across multiple global variables: `INFERENCE_MODELS`, `_marker_loaded`, and the `convert_single_pdf` function which you have to import *after* the check.
    *   What happens if another developer, or even you in six months, adds a function that accidentally sets `_marker_loaded = False`? The entire system breaks, and the expensive models will reload on the next request.
    *   Global state is notoriously hard to reason about. The logic that modifies the state (`_ensure_marker_loaded`) is separate from the state itself. This is a classic recipe for bugs.

2.  **Not Truly Thread-Safe (A Ticking Time Bomb):**
    *   Your original code has a critical race condition. Imagine two requests arrive at the *exact same time* when the models are not yet loaded.
    *   **Thread 1** executes `if not _marker_loaded:`. It's `True`, so it enters the block.
    *   **Thread 2** executes `if not _marker_loaded:`. It's *also* `True` (because Thread 1 hasn't finished loading yet), so it *also* enters the block.
    *   Now, both threads are trying to load the massive models into memory simultaneously. This will, at best, waste huge amounts of CPU and RAM. At worst, it will lead to memory corruption or a crash.
    *   While you could add a global `threading.Lock()` to fix this, it just adds *another* piece of scattered global state to manage.

3.  **Poor Scalability and Testability:**
    *   **Testing:** How do you unit test your `extract_pdf_content` tool? You can't easily "reset" the state for each test without manipulating global variables directly, which is a testing anti-pattern. You can't provide a "mock" or "fake" model loader.
    *   **Scaling:** What if you later need to support another type of document processor, maybe for `.docx` files, which also needs lazy loading? You'd have to create another set of global variables: `_word_models`, `_word_loaded`, `_ensure_word_loaded`, etc. Your global namespace becomes polluted and confusing.

---

### Why the Class Solves These Problems (Reduces Complexity & Brittleness)

The `MarkerProcessor` class is not just "more code." It's a design pattern (a thread-safe singleton) that directly solves the problems above. Think of it as a well-organized toolbox instead of leaving tools scattered on the floor.

1.  **Encapsulation (Manages Complexity):**
    *   The class bundles the state (`self.models`, `self.models_loaded`) and the behavior (`_ensure_models_loaded`, `process`) that operates on that state into a single, cohesive unit.
    *   **The complexity is now contained.** No outside code can accidentally mess with the internal state of the processor. You interact with it through a single, clean method: `marker_processor.process()`. This is the definition of reducing complexity—hiding the messy details behind a simple interface.

2.  **Guaranteed Thread Safety (Eliminates Brittleness):**
    *   The `threading.Lock` is part of the object's state (`self.load_lock`). It's not a loose global variable.
    *   The "double-checked locking" pattern inside `_ensure_models_loaded` is a standard, robust way to guarantee that the expensive loading operation happens **exactly once**, no matter how many threads call it at the same time. This makes the system resilient under load, eliminating the brittleness of the race condition.

3.  **Superior Testability and Scalability:**
    *   **Testing:** It's now trivial to test `extract_pdf_content`. You can create a `MockMarkerProcessor` class with a fake `process` method and pass that to your tool for testing. You're no longer dependent on global state.
    *   **Scaling:** If you need a Word document processor, you simply create a new `WordProcessor` class following the same pattern. Each processor manages its own state, its own models, and its own locks, completely independent of the others. The design is clean and repeatable.

### Analogy: The Restaurant Kitchen

*   **Global Variable Approach:** The head chef (`extract_pdf_content`) shouts into the kitchen, "Is the big oven on?" (`if not _marker_loaded`). If not, they yell, "Someone turn on the big oven!" (`marker.models.load_all_models()`). If two chefs yell at the same time, two line cooks might try to turn on the same oven, causing chaos. The state of the oven is public knowledge, and anyone can mess with it.

*   **Class-Based Approach:** There is an "Oven Station" (`MarkerProcessor` instance) run by a dedicated station chef. The head chef just puts in an order: "I need this dish baked" (`marker_processor.process()`). The station chef is responsible for making sure the oven is on (and only turns it on if it's currently off), managing the temperature, and returning the cooked dish. The head chef doesn't need to know or care about the details—the complexity is handled by the specialist. This is a more organized, less error-prone system.

**Conclusion:**

You are right to question added code. But in this case, the class isn't *unnecessary* complexity. It is a structure that **tames the inherent complexity** of managing shared, lazy-loaded, and expensive resources in a concurrent environment. It replaces a fragile, bug-prone pattern with a robust, standard, and easy-to-understand one, ultimately making your code **less brittle and easier to maintain.**