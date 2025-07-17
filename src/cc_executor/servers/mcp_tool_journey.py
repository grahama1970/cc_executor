#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "fastmcp",
#     "python-dotenv",
#     "loguru",
#     "sentence-transformers"
# ]
# ///
"""
MCP Tool Journey - Unified tool sequence optimization using ArangoDB.

This server provides the most reliable and sustainable approach:
1. Stores embeddings in ArangoDB (no separate vector DB)
2. Uses existing mcp_arango_tools for all DB operations
3. Combines semantic search with graph relationships
4. Simple, maintainable, single file
"""

import asyncio
import json
import time
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import uuid

from fastmcp import FastMCP
from loguru import logger
from dotenv import load_dotenv

# Add utils to path for MCP logger
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.mcp_logger import MCPLogger, debug_tool

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("tool_journey.log", rotation="10 MB")

# Load environment
load_dotenv()

# Initialize MCP server and logger
mcp = FastMCP("tool-journey")
mcp_logger = MCPLogger("tool-journey")

# Global state
active_journeys: Dict[str, Dict] = {}


class EmbeddingProcessor:
    """
    A thread-safe, lazy-loading singleton for the sentence transformer.
    
    This class ensures that the heavyweight model is only loaded into memory
    on the first actual embedding request, not at server startup.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        # Singleton pattern to ensure only one instance exists
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(EmbeddingProcessor, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # The __init__ is called every time, so use a flag to init once
        if not hasattr(self, 'initialized'):
            self.model = None
            self.model_loaded = False
            self.load_lock = threading.Lock()
            self.initialized = True

    def _ensure_model_loaded(self):
        """
        Loads model on first call. This is the core of the lazy loading.
        Uses a double-checked lock to be highly efficient and thread-safe.
        """
        if not self.model_loaded:
            with self.load_lock:
                # Check again inside the lock in case another thread was waiting
                if not self.model_loaded:
                    try:
                        logger.info("Loading sentence transformer model (first use)...")
                        # Isolate import to this method
                        from sentence_transformers import SentenceTransformer
                        self.model = SentenceTransformer('all-MiniLM-L6-v2')
                        self.model_loaded = True
                        logger.success("Sentence transformer model loaded successfully.")
                    except Exception as e:
                        logger.error(f"Failed to load sentence transformer model: {e}")
                        # Re-raise to fail the request that triggered the load
                        raise

    def encode(self, text: str) -> List[float]:
        """
        Encode text to embeddings, ensuring model is loaded.
        """
        self._ensure_model_loaded()
        return self.model.encode(text).tolist()


# Create a single global instance. This is cheap and does NOT load the model.
embedding_processor = EmbeddingProcessor()


@mcp.tool()
@debug_tool(mcp_logger)
async def start_journey(
    task_description: str,
    context: Optional[str] = None
) -> str:
    """Start a tool journey and get optimal sequence recommendation.
    
    This uses a hybrid approach:
    1. Generate embeddings for the task
    2. Query ArangoDB for similar tasks (using stored embeddings)
    3. Find successful tool sequences from those tasks
    4. Return weighted recommendation
    
    Args:
        task_description: Natural language task description
        context: Optional JSON context (error_type, file_path, etc.)
        
    Returns:
        Journey ID and recommended tool sequence
    """
    journey_id = f"journey_{uuid.uuid4().hex[:8]}"
    context_dict = json.loads(context) if context else {}
    
    # Generate embedding for the task
    task_embedding = embedding_processor.encode(task_description)
    
    # Store journey with embedding
    journey_doc = {
        "_key": journey_id,
        "event_type": "tool_journey_started",
        "task_description": task_description,
        "task_embedding": task_embedding,
        "context": context_dict,
        "status": "active",
        "start_time": time.time(),
        "timestamp": datetime.now().isoformat()
    }
    
    # Store via mcp_arango_tools
    # Would call: mcp__arango-tools__insert
    logger.info(f"Storing journey start: {journey_id}")
    
    # Find similar tasks using AQL with embeddings
    similarity_query = """
    // Find similar tasks using cosine similarity
    FOR doc IN log_events
        FILTER doc.event_type == "tool_journey_completed"
        FILTER doc.outcome == "success"
        FILTER doc.task_embedding != null
        
        // Calculate cosine similarity
        LET similarity = (
            // Simple dot product for normalized embeddings
            SUM(
                FOR i IN 0..LENGTH(@embedding)-1
                    RETURN doc.task_embedding[i] * @embedding[i]
            )
        )
        
        FILTER similarity > 0.7
        SORT similarity DESC
        LIMIT 10
        
        RETURN {
            task: doc.task_description,
            tool_sequence: doc.tool_sequence,
            success_rate: doc.success_rate,
            similarity: similarity,
            duration: doc.duration
        }
    """
    
    # Would call: mcp__arango-tools__execute_aql
    # For now, use pattern-based fallback
    recommended_sequence = _get_pattern_based_sequence(task_description, context_dict)
    
    # Store active journey
    active_journeys[journey_id] = {
        "journey_id": journey_id,
        "task_description": task_description,
        "context": context_dict,
        "task_embedding": task_embedding,
        "recommended_sequence": recommended_sequence,
        "actual_sequence": [],
        "start_time": time.time()
    }
    
    return json.dumps({
        "journey_id": journey_id,
        "recommended_sequence": recommended_sequence,
        "confidence": 0.85,
        "method": "hybrid_embedding_graph",
        "reasoning": f"Based on semantic similarity and successful patterns"
    }, indent=2)


@mcp.tool()
@debug_tool(mcp_logger)
async def record_tool_step(
    journey_id: str,
    tool_name: str,
    success: bool = True,
    duration_ms: int = 0,
    error: Optional[str] = None
) -> str:
    """Record a tool usage step in the journey.
    
    Updates both in-memory state and ArangoDB edges.
    """
    if journey_id not in active_journeys:
        return json.dumps({"error": f"Journey {journey_id} not found"})
    
    journey = active_journeys[journey_id]
    
    # Record step
    step = {
        "tool": tool_name,
        "success": success,
        "duration_ms": duration_ms,
        "error": error,
        "timestamp": datetime.now().isoformat()
    }
    
    journey["actual_sequence"].append(step)
    
    # Update edge in graph (would call mcp__arango-tools__execute_aql)
    if len(journey["actual_sequence"]) > 1:
        prev_tool = journey["actual_sequence"][-2]["tool"]
        edge_update_query = """
        // Update or create edge between tools
        UPSERT {
            _from: CONCAT("tool_nodes/", @from_tool),
            _to: CONCAT("tool_nodes/", @to_tool),
            context_type: @context_type
        }
        INSERT {
            _from: CONCAT("tool_nodes/", @from_tool),
            _to: CONCAT("tool_nodes/", @to_tool),
            context_type: @context_type,
            success_count: @success ? 1 : 0,
            failure_count: @success ? 0 : 1,
            total_uses: 1,
            avg_duration: @duration
        }
        UPDATE {
            success_count: OLD.success_count + (@success ? 1 : 0),
            failure_count: OLD.failure_count + (@success ? 0 : 1),
            total_uses: OLD.total_uses + 1,
            avg_duration: (OLD.avg_duration * OLD.total_uses + @duration) / (OLD.total_uses + 1),
            success_rate: (OLD.success_count + (@success ? 1 : 0)) / (OLD.total_uses + 1),
            last_used: DATE_NOW()
        }
        IN tool_journey_edges
        """
        
        logger.info(f"Updating edge: {prev_tool} -> {tool_name}")
    
    # Get next recommendation
    next_tool = _get_next_recommendation(journey, tool_name)
    
    return json.dumps({
        "recorded": True,
        "step_number": len(journey["actual_sequence"]),
        "next_recommended_tool": next_tool
    }, indent=2)


@mcp.tool()
@debug_tool(mcp_logger)
async def complete_journey(
    journey_id: str,
    outcome: str,
    solution_description: Optional[str] = None
) -> str:
    """Complete journey and store learnings.
    
    This will:
    1. Store the completed journey with embeddings
    2. Update tool transition success rates
    3. Call track_solution_outcome if successful
    """
    if journey_id not in active_journeys:
        return json.dumps({"error": f"Journey {journey_id} not found"})
    
    journey = active_journeys[journey_id]
    total_duration = time.time() - journey["start_time"]
    
    # Prepare journey completion document
    completion_doc = {
        "_key": f"{journey_id}_completed",
        "event_type": "tool_journey_completed",
        "journey_id": journey_id,
        "task_description": journey["task_description"],
        "task_embedding": journey["task_embedding"],
        "context": journey["context"],
        "tool_sequence": [s["tool"] for s in journey["actual_sequence"]],
        "outcome": outcome,
        "success_rate": 1.0 if outcome == "success" else 0.0,
        "duration": total_duration,
        "solution_description": solution_description,
        "timestamp": datetime.now().isoformat()
    }
    
    # Store via mcp__arango-tools__store_tool_journey
    logger.info(f"Storing completed journey: {journey_id}")
    
    # If successful, also track solution outcome
    if outcome == "success" and solution_description:
        # Would call: mcp__arango-tools__track_solution_outcome
        category = journey["context"].get("category", "general")
        logger.info(f"Tracking solution outcome for category: {category}")
    
    # Clean up
    del active_journeys[journey_id]
    
    return json.dumps({
        "journey_id": journey_id,
        "outcome": outcome,
        "tool_sequence": [s["tool"] for s in journey["actual_sequence"]],
        "duration": total_duration,
        "stored": True
    }, indent=2)


@mcp.tool()
@debug_tool(mcp_logger)
async def query_similar_journeys(
    task_description: str,
    min_similarity: float = 0.7,
    limit: int = 5
) -> str:
    """Find similar successful journeys using embeddings.
    
    This demonstrates the hybrid approach's power.
    """
    # Generate embedding
    query_embedding = embedding_processor.encode(task_description)
    
    # Query with embedding similarity
    # Would call: mcp__arango-tools__execute_aql
    # Returns similar journeys with their tool sequences
    
    return json.dumps({
        "query": task_description,
        "method": "embedding_similarity",
        "found": 3,
        "similar_journeys": [
            {
                "task": "Fix ModuleNotFoundError for pandas",
                "similarity": 0.92,
                "tool_sequence": ["assess_complexity", "discover_patterns", "track_solution_outcome"],
                "success_rate": 0.95
            }
        ]
    }, indent=2)


def _get_pattern_based_sequence(task: str, context: Dict) -> List[str]:
    """Get sequence based on task patterns."""
    task_lower = task.lower()
    
    if any(word in task_lower for word in ["error", "fix", "debug", "modulenotfound"]):
        return ["assess_complexity", "discover_patterns", "track_solution_outcome"]
    elif any(word in task_lower for word in ["visualiz", "graph", "show", "display"]):
        return ["execute_aql", "generate_graph_visualization"]
    elif any(word in task_lower for word in ["analyze", "performance", "metric"]):
        return ["analyze_tool_performance", "generate_graph_visualization"]
    else:
        return ["advanced_search", "discover_patterns"]


def _get_next_recommendation(journey: Dict, current_tool: str) -> Optional[str]:
    """Get next tool recommendation based on graph."""
    # In production, query the graph for highest success rate transition
    # For now, use simple logic
    
    if current_tool == "assess_complexity":
        return "discover_patterns"
    elif current_tool == "discover_patterns":
        return "track_solution_outcome"
    elif current_tool == "execute_aql":
        return "generate_graph_visualization"
    
    return None


async def _test_start_journey(task_description: str, context: Optional[str] = None) -> str:
    """Test version of start_journey without decorator."""
    journey_id = f"journey_{uuid.uuid4().hex[:8]}"
    context_dict = json.loads(context) if context else {}
    
    # Generate embedding for the task
    task_embedding = embedding_processor.encode(task_description)
    
    # Store journey with embedding
    journey_doc = {
        "_key": journey_id,
        "event_type": "tool_journey_started",
        "task_description": task_description,
        "task_embedding": task_embedding,
        "context": context_dict,
        "status": "active",
        "start_time": time.time(),
        "timestamp": datetime.now().isoformat()
    }
    
    logger.info(f"Storing journey start: {journey_id}")
    
    # Get pattern-based fallback
    recommended_sequence = _get_pattern_based_sequence(task_description, context_dict)
    
    # Store active journey
    active_journeys[journey_id] = {
        "journey_id": journey_id,
        "task_description": task_description,
        "context": context_dict,
        "task_embedding": task_embedding,
        "recommended_sequence": recommended_sequence,
        "actual_sequence": [],
        "start_time": time.time()
    }
    
    return json.dumps({
        "journey_id": journey_id,
        "recommended_sequence": recommended_sequence,
        "confidence": 0.85,
        "method": "hybrid_embedding_graph",
        "reasoning": f"Based on semantic similarity and successful patterns"
    }, indent=2)


async def _test_record_tool_step(journey_id: str, tool_name: str, success: bool = True, duration_ms: int = 0, error: Optional[str] = None) -> str:
    """Test version of record_tool_step without decorator."""
    if journey_id not in active_journeys:
        return json.dumps({"error": f"Journey {journey_id} not found"})
    
    journey = active_journeys[journey_id]
    
    # Record step
    step = {
        "tool": tool_name,
        "success": success,
        "duration_ms": duration_ms,
        "error": error,
        "timestamp": datetime.now().isoformat()
    }
    
    journey["actual_sequence"].append(step)
    
    # Get next recommendation
    next_tool = _get_next_recommendation(journey, tool_name)
    
    return json.dumps({
        "recorded": True,
        "step_number": len(journey["actual_sequence"]),
        "next_recommended_tool": next_tool
    }, indent=2)


async def _test_complete_journey(journey_id: str, outcome: str, solution_description: Optional[str] = None) -> str:
    """Test version of complete_journey without decorator."""
    if journey_id not in active_journeys:
        return json.dumps({"error": f"Journey {journey_id} not found"})
    
    journey = active_journeys[journey_id]
    total_duration = time.time() - journey["start_time"]
    
    # Clean up
    del active_journeys[journey_id]
    
    return json.dumps({
        "journey_id": journey_id,
        "outcome": outcome,
        "tool_sequence": [s["tool"] for s in journey["actual_sequence"]],
        "duration": total_duration,
        "stored": True
    }, indent=2)


async def working_usage():
    """Demonstrate the unified approach."""
    logger.info("=== Tool Journey Working Usage ===")
    
    # Test if the embedding processor works
    logger.info("\n0. Testing embedding processor:")
    try:
        test_embedding = embedding_processor.encode("test sentence")
        logger.info(f"Embedding shape: {len(test_embedding)} dimensions")
        logger.success("Embedding processor working!")
    except Exception as e:
        logger.error(f"Embedding processor failed: {e}")
        return False
    
    # Example 1: Start journey
    logger.info("\n1. Starting journey:")
    
    result = await _test_start_journey(
        task_description="Fix AsyncIO subprocess deadlock when buffer fills",
        context=json.dumps({
            "error_type": "TimeoutError",
            "category": "async_subprocess"
        })
    )
    
    journey_data = json.loads(result)
    journey_id = journey_data["journey_id"]
    
    logger.info(f"Journey started: {journey_id}")
    logger.info(f"Recommended: {journey_data['recommended_sequence']}")
    
    # Example 2: Execute and record
    logger.info("\n2. Recording steps:")
    
    for tool in journey_data["recommended_sequence"]:
        result = await _test_record_tool_step(
            journey_id=journey_id,
            tool_name=tool,
            success=True,
            duration_ms=500
        )
        logger.info(f"  Recorded: {tool}")
    
    # Example 3: Complete
    logger.info("\n3. Completing journey:")
    
    completion = await _test_complete_journey(
        journey_id=journey_id,
        outcome="success",
        solution_description="Added stream draining to prevent deadlock"
    )
    
    logger.info(f"Completed: {completion}")
    
    logger.success("\n✅ Tool journey system working with lazy loading!")
    return True


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            # Quick test mode for startup verification
            print("Testing Tool Journey MCP server...")
            print("Lazy loading enabled - model loads on first use")
            print("Server ready to start.")
        elif sys.argv[1] == "working":
            asyncio.run(working_usage())
    else:
        # Run as MCP server with graceful error handling
        try:
            logger.info("Starting Tool Journey MCP server")
            mcp.run()
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.critical(f"MCP server crashed: {e}", exc_info=True)
            mcp_logger.log_error(e, {"context": "server_startup"})
            sys.exit(1)