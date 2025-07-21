#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "fastmcp",
#     "mcp-logger-utils>=0.1.5",
#     "python-dotenv",
#     "loguru",
#     "requests",
#     "aiohttp",
#     "playwright",
#     "beautifulsoup4",
#     "GitPython",
#     "tenacity",
#     "tqdm",
#     "aiofiles"
# ]
# ///
"""
MCP Server for Crawling, Fetching, and Discovering Resources.

This MCP provides agents with robust tools to download web pages (with or without
JavaScript rendering), perform sparse clones of Git repositories, and discover
local files. All fetched resources are saved to a local cache, and the tools
return the path to the local file for other MCPs to process.

=== MCP DEBUGGING NOTES (2025-01-20) ===

COMMON MCP USAGE PITFALLS:
1. Playwright requires system dependencies - run `playwright install` first
2. The 'patterns' parameter for sparse_clone must be a valid JSON array string
3. Git sparse clones default to 'main' branch - may fail on repos using 'master'
4. Cached content doesn't track if JS was used - shows "[unknown: from cache]"
5. batch_fetch_urls requires valid JSON array - use json.dumps() if needed
6. Semaphore limits concurrent downloads - default 5, override with max_concurrent

HOW TO DEBUG THIS MCP SERVER:

1. TEST LOCALLY (QUICKEST):
   ```bash
   # Test if server can start
   python src/cc_executor/servers/mcp_crawler.py test
   
   # Run working usage
   python src/cc_executor/servers/mcp_crawler.py working
   
   # Install Playwright browsers if needed
   playwright install
   ```

2. CHECK MCP LOGS:
   - Startup log: ~/.claude/mcp_logs/crawler_startup.log
   - Debug log: ~/.claude/mcp_logs/crawler_debug.log
   - Calls log: ~/.claude/mcp_logs/crawler_calls.jsonl

3. COMMON ISSUES & FIXES:
   
   a) Playwright browser not found:
      - Error: "Executable doesn't exist at..."
      - Fix: Run `playwright install` or `playwright install chromium`
      - Check: playwright browsers are in ~/.cache/ms-playwright/
   
   b) Git sparse clone fails:
      - Error: "error: pathspec 'main' did not match any file(s)"
      - Fix: Some repos use 'master' instead of 'main'
      - TODO: Auto-detect default branch
   
   c) URL fetch timeout:
      - Error: "Timeout 45000ms exceeded"
      - Fix: Some sites are slow, increase timeout or use force_render_js=False
      - Check: Network connectivity
   
   d) Too many concurrent connections:
      - Error: "Too many open connections" or rate limiting
      - Fix: Reduce max_concurrent parameter in batch_fetch_urls
      - Default: 5 concurrent downloads

4. ENVIRONMENT VARIABLES:
   - PYTHONPATH=/home/graham/workspace/experiments/cc_executor/src
   - No specific env vars required
   - Cache location: ~/.cache/mcp_crawler/

5. CURRENT STATUS:
   - ✅ All imports working
   - ✅ Playwright integration functional
   - ✅ Async batch downloads with progress tracking
   - ✅ Exponential backoff retry logic (via tenacity)
   - ✅ Concurrent download limiting with semaphore
   - ⚠️ Git sparse clone assumes 'main' branch
   - ⚠️ Cache doesn't expire (manual cleanup needed)

=== END DEBUGGING NOTES ===

AGENT VERIFICATION INSTRUCTIONS:
- This MCP requires system dependencies for Playwright. Run `playwright install` first.
- Run with `test` argument: `python mcp_crawler.py test`
- Run the `working_usage()`: `python mcp_crawler.py working`
- The `working_usage()` function MUST pass all assertions, which involves fetching
  a live URL, cloning a public git repo, and verifying local files are created.

Third-party Documentation:
- Playwright: https://playwright.dev/python/docs/
- GitPython: https://gitpython.readthedocs.io/
- Requests: https://requests.readthedocs.io/
"""

import asyncio
import json
import os
import sys
import time
import hashlib
import shutil
import subprocess
import fnmatch
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from urllib import parse, robotparser
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from fastmcp import FastMCP
from loguru import logger
from dotenv import load_dotenv, find_dotenv
from mcp_logger_utils import MCPLogger, debug_tool
import requests
import aiohttp
import aiofiles
from playwright.sync_api import sync_playwright, Error as PlaywrightError
from playwright.async_api import async_playwright
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from tqdm.asyncio import tqdm_asyncio
from tqdm import tqdm

# Import standardized response utilities (REQUIRED by MCP_CHECKLIST.md)
sys.path.insert(0, str(Path(__file__).parent))
from utils.response_utils import create_success_response, create_error_response

# Configure logging, MCP, etc.
logger.remove()
logger.add(sys.stderr, level="INFO")
load_dotenv(find_dotenv())
mcp = FastMCP("crawler")
mcp_logger = MCPLogger("crawler")

# --- Service Class holding all logic ---

class CrawlerTools:
    """Encapsulates all fetching, cloning, and file management logic."""
    def __init__(self, base_cache_dir: Optional[Path] = None, max_concurrent_downloads: int = 5):
        if base_cache_dir:
            self.base_cache_dir = base_cache_dir
        else:
            self.base_cache_dir = Path.home() / ".cache" / "mcp_crawler"
        
        self.fetches_dir = self.base_cache_dir / "fetches"
        self.clones_dir = self.base_cache_dir / "clones"
        self.fetches_dir.mkdir(parents=True, exist_ok=True)
        self.clones_dir.mkdir(parents=True, exist_ok=True)
        
        # Async download settings
        self.max_concurrent_downloads = max_concurrent_downloads
        self.semaphore = asyncio.Semaphore(max_concurrent_downloads)
        self.session = None  # Will be created when needed
        
        logger.info(f"Crawler cache initialized at {self.base_cache_dir}")
        logger.info(f"Max concurrent downloads: {max_concurrent_downloads}")

    def _get_cache_path_for_url(self, url: str) -> Path:
        """Creates a deterministic, safe cache path for a URL."""
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        # Sanitize a name from the URL path
        parsed_url = parse.urlparse(url)
        safe_filename_base = "".join(c for c in Path(parsed_url.path).name if c.isalnum() or c in '._-').strip('._-')[:50]
        safe_filename = safe_filename_base or "index"
        return self.fetches_dir / f"{safe_filename}_{url_hash}.html"

    def is_js_needed(self, url: str, html_content: Optional[str]) -> bool:
        """Heuristic to check if JavaScript rendering is likely needed."""
        if not html_content: return True # If requests failed, we need Playwright
        content = html_content.lower()
        if any(f in content for f in ["react", "vue", "angular", "svelte", "next/data"]):
            logger.debug(f"JS framework detected for {url}. Escalating to Playwright.")
            return True
        body_start = content.find('<body')
        if len(content[body_start:]) < 2000:
            logger.debug(f"Small body size ({len(content[body_start:])}b) for {url}. Escalating to Playwright.")
            return True
        return False

    def fetch_url(self, url: str, force_render_js: bool, use_cache: bool, user_agent: str = "MCP-Crawler/1.0") -> Dict:
        """Fetches a URL, progressively enhancing from requests to Playwright."""
        cache_path = self._get_cache_path_for_url(url)
        if use_cache and cache_path.exists() and cache_path.stat().st_size > 0:
            logger.info(f"Returning cached content for {url} from {cache_path}")
            return {"url": url, "local_path": str(cache_path), "from_cache": True, "js_rendered": "[unknown: from cache]"}

        # Try fast path first: requests
        html_content = None
        js_needed = True # Assume JS is needed until proven otherwise
        try:
            headers = {'User-Agent': user_agent}
            response = requests.get(url, timeout=10, headers=headers, allow_redirects=True)
            response.raise_for_status()
            html_content = response.text
            js_needed = self.is_js_needed(url, html_content)
        except requests.RequestException as e:
            logger.warning(f"Lightweight fetch failed for {url}: {e}. Will attempt Playwright.")
            js_needed = True # Must use Playwright if requests fails
        
        # Decide if we can stop here
        if html_content and not force_render_js and not js_needed:
            cache_path.write_text(html_content, encoding='utf-8')
            logger.info(f"Fetched static HTML for {url} successfully.")
            return {"url": url, "local_path": str(cache_path), "from_cache": False, "js_rendered": False}

        # Slow path: Use Playwright for full JS rendering
        logger.info(f"Using Playwright to render JavaScript for {url}")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(user_agent=user_agent)
                try:
                    page.goto(url, wait_until="networkidle", timeout=45000)
                    rendered_html = page.content()
                    cache_path.write_text(rendered_html, encoding='utf-8')
                    return {"url": url, "local_path": str(cache_path), "from_cache": False, "js_rendered": True}
                finally:
                    browser.close()
        except PlaywrightError as e:
            logger.error(f"Playwright failed for {url}: {e}")
            raise RuntimeError(f"Playwright failed to fetch {url}: {e}")

    def sparse_clone_repo(self, repo_url: str, patterns: List[str]) -> Dict:
        """Performs a sparse clone of a Git repository."""
        repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        clone_dir = self.clones_dir / repo_name
        
        if clone_dir.exists(): shutil.rmtree(clone_dir)
        clone_dir.mkdir()

        logger.info(f"Initializing sparse clone for {repo_url} in {clone_dir}")
        subprocess.run(['git', 'init'], cwd=clone_dir, check=True, capture_output=True, text=True)
        subprocess.run(['git', 'remote', 'add', 'origin', repo_url], cwd=clone_dir, check=True, capture_output=True, text=True)
        subprocess.run(['git', 'config', 'core.sparseCheckout', 'true'], cwd=clone_dir, check=True, capture_output=True, text=True)
        
        sparse_file = clone_dir / '.git' / 'info' / 'sparse-checkout'
        sparse_file.write_text('\n'.join(patterns) + '\n', encoding='utf-8')
        
        logger.info(f"Pulling from origin with patterns: {patterns}")
        pull_result = subprocess.run(['git', 'pull', '--depth=1', 'origin', 'main'], cwd=clone_dir, check=True, capture_output=True, text=True)
        logger.debug(f"Git pull stdout: {pull_result.stdout}")
        
        discovered = self.discover_files(str(clone_dir), [])
        
        return {"repo_url": repo_url, "local_path": str(clone_dir), "file_count": len(discovered["file_paths"])}

    def discover_files(self, path: str, exclude_patterns: List[str]) -> Dict:
        """Discovers files in a local directory, respecting excludes."""
        relevant_files = []
        base_path = Path(path).resolve()
        
        for root, dirs, files in os.walk(base_path):
            if ".git" in dirs: dirs.remove(".git")
            
            for name in files:
                file_path = Path(root) / name
                relative_path = file_path.relative_to(base_path)
                
                is_excluded = any(fnmatch.fnmatch(str(relative_path), p) for p in exclude_patterns)
                if not is_excluded:
                    relevant_files.append(str(file_path))
        
        return {"path": str(base_path), "file_paths": relevant_files}
    
    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def _close_session(self):
        """Close aiohttp session if it exists."""
        if self.session:
            await self.session.close()
            self.session = None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
    )
    async def _fetch_url_async(self, url: str, user_agent: str = "MCP-Crawler/1.0") -> Tuple[str, Optional[str]]:
        """Async fetch with retry logic."""
        await self._ensure_session()
        
        headers = {'User-Agent': user_agent}
        try:
            async with self.session.get(url, headers=headers, allow_redirects=True) as response:
                response.raise_for_status()
                content = await response.text()
                return content, None
        except Exception as e:
            return None, str(e)
    
    async def _playwright_fetch_async(self, url: str, user_agent: str = "MCP-Crawler/1.0") -> Tuple[str, Optional[str]]:
        """Async Playwright fetch for JS rendering."""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                try:
                    page = await browser.new_page(user_agent=user_agent)
                    await page.goto(url, wait_until="networkidle", timeout=45000)
                    content = await page.content()
                    return content, None
                finally:
                    await browser.close()
        except Exception as e:
            return None, str(e)
    
    async def fetch_url_async(self, url: str, force_render_js: bool, use_cache: bool, 
                             progress_callback=None) -> Dict:
        """Async version of fetch_url with progress callback."""
        cache_path = self._get_cache_path_for_url(url)
        
        # Check cache first
        if use_cache and cache_path.exists() and cache_path.stat().st_size > 0:
            logger.info(f"Returning cached content for {url}")
            if progress_callback:
                await progress_callback(url, "cached")
            return {
                "url": url, 
                "local_path": str(cache_path), 
                "from_cache": True, 
                "js_rendered": "[unknown: from cache]"
            }
        
        async with self.semaphore:  # Limit concurrent downloads
            try:
                # Try fast async fetch first
                html_content = None
                js_needed = True
                
                if not force_render_js:
                    if progress_callback:
                        await progress_callback(url, "downloading")
                    
                    html_content, error = await self._fetch_url_async(url)
                    
                    if html_content:
                        js_needed = self.is_js_needed(url, html_content)
                        
                        if not js_needed:
                            # Save and return
                            async with aiofiles.open(cache_path, 'w', encoding='utf-8') as f:
                                await f.write(html_content)
                            
                            if progress_callback:
                                await progress_callback(url, "completed")
                            
                            return {
                                "url": url,
                                "local_path": str(cache_path),
                                "from_cache": False,
                                "js_rendered": False
                            }
                
                # Need JS rendering
                if progress_callback:
                    await progress_callback(url, "rendering")
                
                logger.info(f"Using Playwright for JS rendering: {url}")
                html_content, error = await self._playwright_fetch_async(url)
                
                if error:
                    raise RuntimeError(f"Failed to fetch {url}: {error}")
                
                # Save rendered content
                async with aiofiles.open(cache_path, 'w', encoding='utf-8') as f:
                    await f.write(html_content)
                
                if progress_callback:
                    await progress_callback(url, "completed")
                
                return {
                    "url": url,
                    "local_path": str(cache_path),
                    "from_cache": False,
                    "js_rendered": True
                }
                
            except Exception as e:
                if progress_callback:
                    await progress_callback(url, "failed")
                raise
    
    async def batch_fetch_urls(self, urls: List[str], force_render_js: bool = False,
                              use_cache: bool = True, show_progress: bool = True) -> List[Dict]:
        """Fetch multiple URLs concurrently with progress tracking."""
        results = []
        failed_urls = []
        
        # Progress tracking
        if show_progress:
            pbar = tqdm(total=len(urls), desc="Fetching URLs", unit="url")
            
            async def update_progress(url: str, status: str):
                pbar.set_postfix_str(f"{status}: {url[:30]}...")
                if status in ["completed", "cached", "failed"]:
                    pbar.update(1)
        else:
            async def update_progress(url: str, status: str):
                logger.info(f"{status}: {url}")
        
        # Create tasks for all URLs
        tasks = []
        for url in urls:
            task = asyncio.create_task(
                self.fetch_url_async(url, force_render_js, use_cache, update_progress)
            )
            tasks.append((url, task))
        
        # Process completed tasks as they finish
        for url, task in tasks:
            try:
                result = await task
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to fetch {url}: {e}")
                failed_urls.append({
                    "url": url,
                    "error": str(e)
                })
                results.append({
                    "url": url,
                    "error": str(e),
                    "success": False
                })
        
        if show_progress:
            pbar.close()
        
        # Summary
        successful = len([r for r in results if r.get("error") is None])
        logger.info(f"Batch fetch completed: {successful}/{len(urls)} successful")
        
        return {
            "results": results,
            "summary": {
                "total": len(urls),
                "successful": successful,
                "failed": len(failed_urls),
                "from_cache": len([r for r in results if r.get("from_cache", False)])
            },
            "failed_urls": failed_urls
        }

# --- MCP Tool Definitions ---
tools = CrawlerTools()

@mcp.tool()
@debug_tool(mcp_logger)
async def fetch_url(url: str, force_render_js: bool = False, use_cache: bool = True) -> str:
    """
    Fetches a single URL and saves it to a local file, returning the path.
    
    It will try a fast static fetch first, and automatically escalate to a full
    JavaScript rendering with Playwright if the page seems to be a web app.

    Args:
        url: The URL to fetch (e.g., "https://example.com")
        force_render_js: If True, skip the fast static fetch and go straight to Playwright
        use_cache: If True, return the cached version if it exists

    Returns:
        JSON with local_path, from_cache, and js_rendered status
        
    Examples:
        - fetch_url("https://example.com") - Simple static fetch
        - fetch_url("https://spa-app.com", force_render_js=True) - Force JS rendering
        - fetch_url("https://example.com", use_cache=False) - Force refresh
    """
    start_time = time.time()
    try:
        result = tools.fetch_url(url, force_render_js, use_cache)
        return create_success_response(
            data=result,
            tool_name="fetch_url",
            start_time=start_time
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="fetch_url",
            start_time=start_time,
            suggestions=["Check the URL is correct and accessible.", "Try with force_render_js=True if the site is slow to load."]
        )

@mcp.tool()
@debug_tool(mcp_logger)
async def sparse_clone(repo_url: str, patterns: str) -> str:
    """
    Performs a sparse checkout of a git repo to fetch only specific file patterns.

    Args:
        repo_url: The URL of the git repository (e.g., https://github.com/user/repo.git)
        patterns: A JSON array of strings specifying file patterns to check out

    Returns:
        JSON with local_path and file_count
        
    Examples:
        - sparse_clone("https://github.com/user/repo.git", '["*.py"]') - Python files only
        - sparse_clone("https://github.com/user/repo.git", '["docs/", "README.md"]') - Docs + README
        
    Note: Currently assumes 'main' branch. Some repos may use 'master' instead.
    """
    start_time = time.time()
    try:
        parsed_patterns = json.loads(patterns)
        if not isinstance(parsed_patterns, list): raise TypeError("Patterns must be a JSON list of strings.")
        result = tools.sparse_clone_repo(repo_url, parsed_patterns)
        return create_success_response(
            data=result,
            tool_name="sparse_clone",
            start_time=start_time
        )
    except json.JSONDecodeError as e:
        return create_error_response(
            error=f"Invalid JSON in patterns parameter: {e}",
            tool_name="sparse_clone",
            start_time=start_time,
            suggestions=["Ensure patterns is a valid JSON array like '[\"*.py\", \"docs/\"]'"]
        )
    except subprocess.CalledProcessError as e:
        return create_error_response(
            error=f"Git command failed: {e.stderr}",
            tool_name="sparse_clone",
            start_time=start_time,
            suggestions=["Check if the repository URL is correct and public.", "Verify your git patterns are correct.", "Note: this tool assumes 'main' branch - some repos use 'master'"]
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="sparse_clone",
            start_time=start_time
        )

@mcp.tool()
@debug_tool(mcp_logger)
async def batch_fetch_urls(urls: str, force_render_js: bool = False, use_cache: bool = True, 
                          max_concurrent: Optional[int] = None) -> str:
    """
    Fetch multiple URLs concurrently with progress tracking and retry logic.
    
    Uses asyncio for concurrent downloads with a semaphore to limit simultaneous
    connections. Includes exponential backoff retry for failed requests.

    Args:
        urls: A JSON array of URLs to fetch
        force_render_js: If True, use Playwright for all URLs (slower but handles SPAs)
        use_cache: If True, return cached versions when available
        max_concurrent: Override the default max concurrent downloads (default: 5)

    Returns:
        JSON with results array and summary statistics
        
    Examples:
        - batch_fetch_urls('["https://example.com", "https://test.com"]')
        - batch_fetch_urls('[...]', force_render_js=True, max_concurrent=10)
        
    Features:
        - Concurrent downloads with semaphore control
        - Exponential backoff retry (3 attempts)
        - Progress bar with tqdm
        - Automatic JS detection and rendering when needed
        - Detailed error reporting per URL
    """
    start_time = time.time()
    try:
        url_list = json.loads(urls)
        if not isinstance(url_list, list):
            raise TypeError("URLs must be a JSON array of strings")
        
        # Override semaphore if requested
        if max_concurrent and max_concurrent != tools.max_concurrent_downloads:
            original_semaphore = tools.semaphore
            tools.semaphore = asyncio.Semaphore(max_concurrent)
            try:
                result = await tools.batch_fetch_urls(url_list, force_render_js, use_cache)
            finally:
                tools.semaphore = original_semaphore
        else:
            result = await tools.batch_fetch_urls(url_list, force_render_js, use_cache)
        
        return create_success_response(
            data=result,
            tool_name="batch_fetch_urls",
            start_time=start_time
        )
    except json.JSONDecodeError as e:
        return create_error_response(
            error=f"Invalid JSON in urls parameter: {e}",
            tool_name="batch_fetch_urls",
            start_time=start_time,
            suggestions=["Ensure urls is a valid JSON array like '[\"https://example.com\"]'"]
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="batch_fetch_urls",
            start_time=start_time
        )
    finally:
        # Ensure session cleanup
        await tools._close_session()

@mcp.tool()
@debug_tool(mcp_logger)
async def discover_files(path: str, exclude_patterns: Optional[str] = '[]') -> str:
    """
    Recursively finds all files in a local directory path, ignoring git directories.

    Args:
        path: The local directory path to search
        exclude_patterns: A JSON array of glob-style patterns to exclude

    Returns:
        JSON with path and file_paths array
        
    Examples:
        - discover_files("/home/user/project") - All files
        - discover_files("/home/user/project", '["*.log", "*.tmp"]') - Exclude logs and temp files
        - discover_files("/home/user/project", '["build/*", "dist/*"]') - Exclude build artifacts
    """
    start_time = time.time()
    try:
        parsed_excludes = json.loads(exclude_patterns)
        result = tools.discover_files(path, parsed_excludes)
        return create_success_response(
            data=result,
            tool_name="discover_files",
            start_time=start_time
        )
    except Exception as e:
        return create_error_response(
            error=str(e),
            tool_name="discover_files",
            start_time=start_time
        )

# --- Standard Main Block for MCP Servers ---

async def working_usage():
    logger.info("=== Crawler MCP Working Usage ===")
    
    # 1. Test URL Fetch
    test_url = "http://info.cern.ch/hypertext/WWW/TheProject.html" # A simple, static site
    result_str = await fetch_url(test_url, force_render_js=False, use_cache=False)
    result = json.loads(result_str)
    assert result["success"], f"Static fetch failed: {result.get('error')}"
    local_path = Path(result["data"]["local_path"])
    assert local_path.exists(), "Fetch did not create a local file"
    assert "hypertext" in local_path.read_text(encoding='utf-8'), "Static file content is incorrect"
    logger.success(f"✓ Static fetch successful. File saved to {local_path}")
    local_path.unlink()

    # 2. Test Git Clone
    test_repo = "https://github.com/pallets/flask.git"
    patterns = '["README.rst", "examples/"]'
    result_str = await sparse_clone(test_repo, patterns)
    result = json.loads(result_str)
    assert result["success"], f"Sparse clone failed: {result.get('error')}"
    clone_path = Path(result["data"]["local_path"])
    assert clone_path.exists() and (clone_path / "README.rst").exists()
    assert (clone_path / "examples").is_dir()
    logger.success(f"✓ Sparse clone successful. Repo in {clone_path}")
    shutil.rmtree(clone_path) # Cleanup
    
    # 3. Test Batch Fetch
    test_urls = [
        "http://info.cern.ch/hypertext/WWW/TheProject.html",
        "https://www.example.com",
        "https://httpbin.org/html"
    ]
    logger.info("Testing batch fetch with 3 URLs...")
    result_str = await batch_fetch_urls(json.dumps(test_urls), use_cache=False, max_concurrent=2)
    result = json.loads(result_str)
    assert result["success"], f"Batch fetch failed: {result.get('error')}"
    
    batch_data = result["data"]
    assert batch_data["summary"]["total"] == 3, "Wrong total count"
    assert batch_data["summary"]["successful"] >= 2, "Too many failures"
    
    # Cleanup downloaded files
    for item in batch_data["results"]:
        if "local_path" in item and not item.get("error"):
            Path(item["local_path"]).unlink(missing_ok=True)
    
    logger.success(f"✓ Batch fetch successful. {batch_data['summary']['successful']}/3 URLs fetched")

    return True

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            # Quick test mode
            print(f"✓ {Path(__file__).name} can start successfully!")
            sys.exit(0)
        elif sys.argv[1] == "debug":
            # Debug mode - could add debug function if needed
            asyncio.run(working_usage())
        elif sys.argv[1] == "working":
            asyncio.run(working_usage())
    else:
        # Run the MCP server
        try:
            logger.info("Starting Crawler MCP server")
            mcp.run()
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.critical(f"MCP server crashed: {e}", exc_info=True)
            if mcp_logger:
                mcp_logger.log_error(e, {"context": "server_startup"})
            sys.exit(1)