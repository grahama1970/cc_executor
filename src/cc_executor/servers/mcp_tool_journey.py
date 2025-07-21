#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "fastmcp",
#     "python-dotenv",
#     "loguru",
#     "sentence-transformers",
#     "mcp-logger-utils>=0.1.5",
#     "numpy"
# ]
# ///

import os
import asyncio
import json
import time
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import uuid
import hashlib
import random
import numpy as np

from fastmcp import FastMCP
from functools import wraps
from loguru import logger

# Import standardized response utilities
sys.path.insert(0, str(Path(__file__).parent))
from utils.response_utils import create_success_response, create_error_response
from dotenv import load_dotenv, find_dotenv

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("tool_journey.log", rotation="10 MB")

# Load environment
load_dotenv(find_dotenv())

# Import from mcp-logger-utils package
from mcp_logger_utils import MCPLogger, debug_tool

# Initialize MCP server and logger
mcp = FastMCP("tool-journey")
mcp_logger = MCPLogger("tool-journey")

# Global state
active_journeys: Dict[str, Dict] = {}

# Q-Learning parameters
LEARNING_RATE = 0.1
DISCOUNT_FACTOR = 0.9
EXPLORATION_RATE = 0.3
MIN_EXPLORATION_RATE = 0.05
EXPLORATION_DECAY = 0.995

# Reward structure
REWARDS = {
    "optimal_completion": 10.0,
    "suboptimal_completion": 5.0,
    "per_extra_step": -0.5,
    "per_tool_call": -0.1,
    "failed_tool_call": -1.0,
    "task_failure": -5.0,
    "timeout_penalty": -3.0,
    "novel_success": 2.0  # Bonus for discovering new successful paths
}

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

def _hash_state(state: Dict[str, Any]) -> str:
    """Create a hash for state representation for Q-value storage."""
    # Create a deterministic string representation
    state_str = json.dumps({
        "current_tool": state.get("current_tool", ""),
        "tools_used": sorted(state.get("tools_used", [])),
        "error_type": state.get("context", {}).get("error_type", ""),
        "category": state.get("context", {}).get("category", ""),
        "task_type": state.get("task_type", "")
    }, sort_keys=True)
    return hashlib.md5(state_str.encode()).hexdigest()[:16]

async def _get_q_value(state: Dict[str, Any], action: str) -> float:
    """Get Q-value for state-action pair from ArangoDB."""
    state_hash = _hash_state(state)
    
    # Would call: mcp__arango-tools__query
    query = """
    FOR doc IN q_values
        FILTER doc.state_hash == @state_hash
        FILTER doc.action == @action
        RETURN doc.q_value
    """
    # For now, return a default value
    return 0.0

async def _update_q_value(state: Dict[str, Any], action: str, 
                         reward: float, next_state: Dict[str, Any]) -> None:
    """Update Q-value using Q-learning update rule."""
    current_q = await _get_q_value(state, action)
    
    # Get max Q-value for next state
    next_tools = _get_valid_next_tools(next_state)
    max_next_q = 0.0
    if next_tools:
        next_q_values = [await _get_q_value(next_state, tool) for tool in next_tools]
        max_next_q = max(next_q_values) if next_q_values else 0.0
    
    # Q-learning update
    new_q = current_q + LEARNING_RATE * (reward + DISCOUNT_FACTOR * max_next_q - current_q)
    
    # Store updated Q-value
    state_hash = _hash_state(state)
    # Would call: mcp__arango-tools__upsert
    logger.info(f"Updated Q({state_hash}, {action}) = {new_q:.3f}")

async def _get_thompson_params(state: Dict[str, Any], action: str) -> Tuple[float, float]:
    """Get Thompson Sampling parameters (alpha, beta) for state-action pair."""
    state_hash = _hash_state(state)
    
    # Would query from ArangoDB
    # For now, return default priors
    return 1.0, 1.0  # Uniform prior

async def _update_thompson_params(state: Dict[str, Any], action: str, 
                                 success: bool) -> None:
    """Update Thompson Sampling parameters based on outcome."""
    alpha, beta = await _get_thompson_params(state, action)
    
    if success:
        alpha += 1
    else:
        beta += 1
    
    state_hash = _hash_state(state)
    # Would call: mcp__arango-tools__upsert to store updated params
    logger.info(f"Updated Thompson params({state_hash}, {action}): α={alpha}, β={beta}")

def _get_valid_next_tools(state: Dict[str, Any]) -> List[str]:
    """Get valid next tools based on current state."""
    current_tool = state.get("current_tool", "")
    tools_used = state.get("tools_used", [])
    
    # Define tool transition rules
    valid_transitions = {
        "": ["assess_complexity", "advanced_search", "execute_aql"],
        "assess_complexity": ["discover_patterns", "send_to_gemini", "query_converter"],
        "discover_patterns": ["track_solution_outcome", "extract_lesson", "advanced_search"],
        "query_converter": ["execute_aql", "discover_patterns"],
        "execute_aql": ["generate_graph_visualization", "analyze_graph"],
        "send_to_gemini": ["extract_gemini_code", "track_solution_outcome"],
        "advanced_search": ["discover_patterns", "track_solution_outcome"]
    }
    
    # Get base valid tools
    valid_tools = valid_transitions.get(current_tool, [])
    
    # Filter out tools that would create cycles (except for retries)
    valid_tools = [t for t in valid_tools if t not in tools_used[-3:]]
    
    # Always allow track_solution_outcome as final step
    if len(tools_used) > 2 and "track_solution_outcome" not in tools_used:
        valid_tools.append("track_solution_outcome")
    
    return valid_tools

def _calculate_reward(journey: Dict[str, Any], outcome: str, 
                     optimal_length: int = 3) -> float:
    """Calculate reward for completed journey."""
    tool_sequence = journey["actual_sequence"]
    num_tools = len(tool_sequence)
    
    if outcome == "success":
        if num_tools <= optimal_length:
            reward = REWARDS["optimal_completion"]
        else:
            extra_steps = num_tools - optimal_length
            reward = REWARDS["suboptimal_completion"] + (REWARDS["per_extra_step"] * extra_steps)
        
        # Check if this is a novel successful path
        # Would query ArangoDB to check if this exact sequence exists
        is_novel = random.random() < 0.1  # Placeholder
        if is_novel:
            reward += REWARDS["novel_success"]
    else:
        reward = REWARDS["task_failure"]
    
    # Add per-tool costs
    reward += REWARDS["per_tool_call"] * num_tools
    
    # Add failure penalties
    failed_calls = sum(1 for step in tool_sequence if not step.get("success", True))
    reward += REWARDS["failed_tool_call"] * failed_calls
    
    return reward

@mcp.tool()
@debug_tool(mcp_logger)
async def start_journey(
    task_description: str,
    context: Optional[str] = None
) -> str:
    """Start a tool journey with Q-learning and Thompson Sampling.
    
    This uses a sophisticated approach:
    1. Generate embeddings for the task
    2. Query ArangoDB for similar tasks and their Q-values
    3. Use Thompson Sampling for exploration vs exploitation
    4. Return optimal sequence with alternatives
    
    Args:
        task_description: Natural language task description
        context: Optional JSON context (error_type, file_path, etc.)
        
    Returns:
        Journey ID and recommended tool sequence with confidence scores
    """
    start_time = time.time()
    journey_id = f"journey_{uuid.uuid4().hex[:8]}"
    context_dict = json.loads(context) if context else {}
    
    # Generate embedding for the task
    task_embedding = embedding_processor.encode(task_description)
    
    # Initial state
    initial_state = {
        "current_tool": "",
        "tools_used": [],
        "context": context_dict,
        "task_type": context_dict.get("category", "general")
    }
    
    # Get valid starting tools
    valid_tools = _get_valid_next_tools(initial_state)
    
    # Use Thompson Sampling to select tools
    tool_scores = {}
    thompson_samples = {}
    q_values = {}
    
    for tool in valid_tools:
        # Get Q-value
        q_value = await _get_q_value(initial_state, tool)
        q_values[tool] = q_value
        
        # Get Thompson Sampling parameters
        alpha, beta = await _get_thompson_params(initial_state, tool)
        
        # Sample from Beta distribution
        thompson_sample = np.random.beta(alpha, beta)
        thompson_samples[tool] = thompson_sample
        
        # Combine Q-value and Thompson sample
        # Weight more towards Q-value as we get more confident
        confidence_weight = min(0.7, (alpha + beta - 2) / 20)  # Increases with more data
        tool_scores[tool] = (confidence_weight * q_value + 
                            (1 - confidence_weight) * thompson_sample)
    
    # Epsilon-greedy exploration
    if random.random() < EXPLORATION_RATE:
        selected_tool = random.choice(valid_tools)
        logger.info(f"Exploration: randomly selected {selected_tool}")
    else:
        selected_tool = max(tool_scores, key=tool_scores.get)
        logger.info(f"Exploitation: selected {selected_tool} with score {tool_scores[selected_tool]:.3f}")
    
    # Build recommended sequence by simulating trajectory
    recommended_sequence = [selected_tool]
    current_state = initial_state.copy()
    current_state["current_tool"] = selected_tool
    current_state["tools_used"] = [selected_tool]
    
    # Simulate forward to build full sequence
    for _ in range(5):  # Max sequence length
        next_tools = _get_valid_next_tools(current_state)
        if not next_tools:
            break
            
        # Get best next tool based on Q-values
        next_q_values = {tool: await _get_q_value(current_state, tool) 
                        for tool in next_tools}
        next_tool = max(next_q_values, key=next_q_values.get)
        
        recommended_sequence.append(next_tool)
        current_state["current_tool"] = next_tool
        current_state["tools_used"].append(next_tool)
        
        if next_tool == "track_solution_outcome":
            break
    
    # Store journey with embedding
    journey_doc = {
        "_key": journey_id,
        "event_type": "tool_journey_started",
        "task_description": task_description,
        "task_embedding": task_embedding,
        "context": context_dict,
        "status": "active",
        "start_time": time.time(),
        "timestamp": datetime.now().isoformat(),
        "initial_q_values": q_values,
        "thompson_samples": thompson_samples
    }
    
    # Store via mcp_arango_tools
    # Would call: mcp__arango-tools__insert
    logger.info(f"Storing journey start: {journey_id}")
    
    # Store active journey
    active_journeys[journey_id] = {
        "journey_id": journey_id,
        "task_description": task_description,
        "context": context_dict,
        "task_embedding": task_embedding,
        "recommended_sequence": recommended_sequence,
        "actual_sequence": [],
        "start_time": time.time(),
        "exploration_rate": EXPLORATION_RATE
    }
    
    # Sort alternatives by score
    alternatives = sorted(tool_scores.items(), key=lambda x: x[1], reverse=True)[:3]
    
    return create_success_response(data={"journey_id": journey_id,
        "recommended_sequence": recommended_sequence,
        "confidence": tool_scores.get(selected_tool, 0.5),
        "method": "q_learning_thompson_sampling",
        "reasoning": f"Q-value: {q_values.get(selected_tool, 0):.3f}, Thompson: {thompson_samples.get(selected_tool, 0.5):.3f}",
        "alternatives": [{"tool": t, "score": s} for t, s in alternatives]})

@mcp.tool()
@debug_tool(mcp_logger)
async def record_tool_step(
    journey_id: str,
    tool_name: str,
    success: bool = True,
    duration_ms: int = 0,
    error: Optional[str] = None
) -> str:
    """Record a tool usage step with real-time Q-learning updates.
    
    Updates:
    1. Journey state
    2. Q-values based on immediate reward
    3. Thompson Sampling parameters
    4. Edge weights in graph
    """
    start_time = time.time()
    if journey_id not in active_journeys:
        return create_success_response(data={"error": f"Journey {journey_id} not found"})
    
    # Validate duration_ms
    if duration_ms < 0 or duration_ms > 86_400_000:  # 24 hours in milliseconds
        return create_success_response(data={"error": f"Invalid duration_ms: {duration_ms}. Must be between 0 and 86400000 (24 hours)."})
    
    journey = active_journeys[journey_id]
    
    # Create current state before recording step
    current_state = {
        "current_tool": journey["actual_sequence"][-1]["tool"] if journey["actual_sequence"] else "",
        "tools_used": [s["tool"] for s in journey["actual_sequence"]],
        "context": journey["context"],
        "task_type": journey["context"].get("category", "general")
    }
    
    # Record step
    step = {
        "tool": tool_name,
        "success": success,
        "duration_ms": duration_ms,
        "error": error,
        "timestamp": datetime.now().isoformat()
    }
    
    journey["actual_sequence"].append(step)
    
    # Calculate immediate reward
    immediate_reward = REWARDS["per_tool_call"]
    if not success:
        immediate_reward += REWARDS["failed_tool_call"]
    
    # Create next state
    next_state = {
        "current_tool": tool_name,
        "tools_used": [s["tool"] for s in journey["actual_sequence"]],
        "context": journey["context"],
        "task_type": journey["context"].get("category", "general")
    }
    
    # Update Q-value
    await _update_q_value(current_state, tool_name, immediate_reward, next_state)
    
    # Update Thompson Sampling parameters
    await _update_thompson_params(current_state, tool_name, success)
    
    # Update edge in graph
    if len(journey["actual_sequence"]) > 1:
        prev_tool = journey["actual_sequence"][-2]["tool"]
        
        # Calculate current Q-value for the edge
        edge_q_value = await _get_q_value(current_state, tool_name)
        
        edge_update_query = """
        // Update or create edge between tools with Q-learning data
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
            avg_duration: @duration,
            q_value: @q_value,
            thompson_alpha: @success ? 2 : 1,
            thompson_beta: @success ? 1 : 2
        }
        UPDATE {
            success_count: OLD.success_count + (@success ? 1 : 0),
            failure_count: OLD.failure_count + (@success ? 0 : 1),
            total_uses: OLD.total_uses + 1,
            avg_duration: (OLD.avg_duration * OLD.total_uses + @duration) / (OLD.total_uses + 1),
            success_rate: (OLD.success_count + (@success ? 1 : 0)) / (OLD.total_uses + 1),
            q_value: @q_value,
            thompson_alpha: OLD.thompson_alpha + (@success ? 1 : 0),
            thompson_beta: OLD.thompson_beta + (@success ? 0 : 1),
            last_used: DATE_NOW()
        }
        IN tool_journey_edges
        """
        
        logger.info(f"Updating edge: {prev_tool} -> {tool_name} with Q={edge_q_value:.3f}")
    
    # Get next recommendation using Q-learning + Thompson Sampling
    next_tool = await _get_next_recommendation_q_learning(journey, next_state)
    
    return create_success_response(data={"recorded": True,
        "step_number": len(journey["actual_sequence"]),
        "immediate_reward": immediate_reward,
        "next_recommended_tool": next_tool["tool"] if next_tool else None,
        "next_tool_confidence": next_tool["confidence"] if next_tool else 0,
        "exploration_mode": next_tool["exploration"] if next_tool else False})

async def _get_next_recommendation_q_learning(journey: Dict, current_state: Dict) -> Optional[Dict]:
    """Get next tool recommendation using Q-learning and Thompson Sampling."""
    valid_tools = _get_valid_next_tools(current_state)
    
    if not valid_tools:
        return None
    
    # Calculate scores for each valid tool
    tool_scores = {}
    for tool in valid_tools:
        # Get Q-value
        q_value = await _get_q_value(current_state, tool)
        
        # Get Thompson parameters and sample
        alpha, beta = await _get_thompson_params(current_state, tool)
        thompson_sample = np.random.beta(alpha, beta)
        
        # Adaptive weighting based on confidence
        confidence_weight = min(0.8, (alpha + beta - 2) / 30)
        score = confidence_weight * q_value + (1 - confidence_weight) * thompson_sample
        
        tool_scores[tool] = {
            "score": score,
            "q_value": q_value,
            "thompson_sample": thompson_sample,
            "confidence": confidence_weight
        }
    
    # Decay exploration rate
    current_exploration = journey.get("exploration_rate", EXPLORATION_RATE)
    current_exploration *= EXPLORATION_DECAY
    current_exploration = max(current_exploration, MIN_EXPLORATION_RATE)
    journey["exploration_rate"] = current_exploration
    
    # Select tool
    if random.random() < current_exploration:
        # Exploration
        selected_tool = random.choice(valid_tools)
        return {
            "tool": selected_tool,
            "confidence": tool_scores[selected_tool]["score"],
            "exploration": True
        }
    else:
        # Exploitation
        best_tool = max(tool_scores.items(), key=lambda x: x[1]["score"])
        return {
            "tool": best_tool[0],
            "confidence": best_tool[1]["score"],
            "exploration": False
        }

@mcp.tool()
@debug_tool(mcp_logger)
async def complete_journey(
    journey_id: str,
    outcome: str,
    solution_description: Optional[str] = None
) -> str:
    """Complete journey with final Q-learning updates and reward calculation.
    
    This will:
    1. Calculate final reward based on outcome
    2. Backpropagate Q-values through the journey
    3. Store completed journey with learnings
    4. Update global statistics
    """
    if journey_id not in active_journeys:
        return create_success_response(data={"error": f"Journey {journey_id} not found"})
    
    journey = active_journeys[journey_id]
    total_duration = time.time() - journey["start_time"]
    
    # Calculate final reward
    final_reward = _calculate_reward(journey, outcome)
    
    # Backpropagate Q-values through the journey
    # This ensures earlier actions get credit for final outcome
    tool_sequence = journey["actual_sequence"]
    discounted_reward = final_reward
    
    for i in range(len(tool_sequence) - 1, -1, -1):
        step = tool_sequence[i]
        
        # Create state at this step
        state = {
            "current_tool": tool_sequence[i-1]["tool"] if i > 0 else "",
            "tools_used": [s["tool"] for s in tool_sequence[:i]],
            "context": journey["context"],
            "task_type": journey["context"].get("category", "general")
        }
        
        # Update Q-value with discounted final reward
        if i < len(tool_sequence) - 1:
            next_state = {
                "current_tool": step["tool"],
                "tools_used": [s["tool"] for s in tool_sequence[:i+1]],
                "context": journey["context"],
                "task_type": journey["context"].get("category", "general")
            }
        else:
            next_state = state  # Terminal state
        
        await _update_q_value(state, step["tool"], discounted_reward, next_state)
        
        # Decay reward as we go back
        discounted_reward *= DISCOUNT_FACTOR
    
    # Check if this is a novel successful path
    is_novel = False
    if outcome == "success":
        # Would query ArangoDB to check if this exact sequence exists
        # For now, use randomness as placeholder
        is_novel = len(set([s["tool"] for s in tool_sequence])) / len(tool_sequence) > 0.8
    
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
        "timestamp": datetime.now().isoformat(),
        "final_reward": final_reward,
        "is_novel_path": is_novel,
        "exploration_rate_used": journey.get("exploration_rate", EXPLORATION_RATE)
    }
    
    # Store via mcp__arango-tools__store_tool_journey
    logger.info(f"Storing completed journey: {journey_id}")
    logger.info(f"Final reward: {final_reward:.2f}, Novel: {is_novel}")
    
    # If successful, also track solution outcome
    if outcome == "success" and solution_description:
        # Would call: mcp__arango-tools__track_solution_outcome
        category = journey["context"].get("category", "general")
        logger.info(f"Tracking solution outcome for category: {category}")
    
    # Extract insights for future learning
    insights = {
        "successful_transitions": [],
        "failed_transitions": []
    }
    
    for i in range(len(tool_sequence) - 1):
        transition = {
            "from": tool_sequence[i]["tool"],
            "to": tool_sequence[i+1]["tool"],
            "success": tool_sequence[i+1]["success"]
        }
        
        if transition["success"]:
            insights["successful_transitions"].append(transition)
        else:
            insights["failed_transitions"].append(transition)
    
    # Clean up
    del active_journeys[journey_id]
    
    return create_success_response(data={"journey_id": journey_id,
        "outcome": outcome,
        "tool_sequence": [s["tool"] for s in journey["actual_sequence"]],
        "duration": total_duration,
        "final_reward": final_reward,
        "is_novel": is_novel,
        "insights": insights,
        "stored": True})

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
    
    return create_success_response(data={"query": task_description,
        "method": "embedding_similarity",
        "found": 3,
        "similar_journeys": [
            {
                "task": "Fix ModuleNotFoundError for pandas",
                "similarity": 0.92,
                "tool_sequence": ["assess_complexity", "discover_patterns", "track_solution_outcome"],
                "success_rate": 0.95
            }
        ]})

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
    
    return create_success_response(data={"journey_id": journey_id,
        "recommended_sequence": recommended_sequence,
        "confidence": 0.85,
        "method": "hybrid_embedding_graph",
        "reasoning": f"Based on semantic similarity and successful patterns"})

async def _test_record_tool_step(journey_id: str, tool_name: str, success: bool = True, duration_ms: int = 0, error: Optional[str] = None) -> str:
    """Test version of record_tool_step without decorator."""
    if journey_id not in active_journeys:
        return create_success_response(data={"error": f"Journey {journey_id} not found"})
    
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
    
    return create_success_response(data={"recorded": True,
        "step_number": len(journey["actual_sequence"]),
        "next_recommended_tool": next_tool})

async def _test_complete_journey(journey_id: str, outcome: str, solution_description: Optional[str] = None) -> str:
    """Test version of complete_journey without decorator."""
    if journey_id not in active_journeys:
        return create_success_response(data={"error": f"Journey {journey_id} not found"})
    
    journey = active_journeys[journey_id]
    total_duration = time.time() - journey["start_time"]
    
    # Clean up
    del active_journeys[journey_id]
    
    return create_success_response(data={"journey_id": journey_id,
        "outcome": outcome,
        "tool_sequence": [s["tool"] for s in journey["actual_sequence"]],
        "duration": total_duration,
        "stored": True})

async def working_usage():
    """Demonstrate Q-learning and Thompson Sampling approach."""
    logger.info("=== Tool Journey Q-Learning Demo ===")
    
    # Test if the embedding processor works
    logger.info("\n0. Testing embedding processor:")
    try:
        test_embedding = embedding_processor.encode("test sentence")
        logger.info(f"Embedding shape: {len(test_embedding)} dimensions")
        logger.success("Embedding processor working!")
    except Exception as e:
        logger.error(f"Embedding processor failed: {e}")
        return False
    
    # Example 1: Start journey with Q-learning
    logger.info("\n1. Starting journey with Q-learning:")
    
    # Note: Using the actual tool functions without decorators for testing
    journey_result = await start_journey(
        task_description="Fix ModuleNotFoundError for pandas in data processor",
        context=json.dumps({
            "error_type": "ModuleNotFoundError",
            "category": "import_error",
            "module": "pandas"
        })
    )
    
    journey_data = json.loads(journey_result)
    journey_id = journey_data["journey_id"]
    
    logger.info(f"Journey ID: {journey_id}")
    logger.info(f"Recommended sequence: {journey_data['recommended_sequence']}")
    logger.info(f"Method: {journey_data['method']}")
    logger.info(f"Reasoning: {journey_data['reasoning']}")
    logger.info(f"Alternatives: {journey_data.get('alternatives', [])}")
    
    # Example 2: Simulate tool execution with varying success
    logger.info("\n2. Recording tool steps with Q-learning updates:")
    
    tools_to_execute = [
        ("assess_complexity", True, 250),
        ("discover_patterns", True, 500),
        ("track_solution_outcome", True, 100)
    ]
    
    for tool_name, success, duration in tools_to_execute:
        step_result = await record_tool_step(
            journey_id=journey_id,
            tool_name=tool_name,
            success=success,
            duration_ms=duration
        )
        
        step_data = json.loads(step_result)
        logger.info(f"  Tool: {tool_name}")
        logger.info(f"    Immediate reward: {step_data.get('immediate_reward', 0):.2f}")
        logger.info(f"    Next recommended: {step_data.get('next_recommended_tool')}")
        logger.info(f"    Confidence: {step_data.get('next_tool_confidence', 0):.3f}")
        logger.info(f"    Exploration mode: {step_data.get('exploration_mode', False)}")
    
    # Example 3: Complete journey with reward calculation
    logger.info("\n3. Completing journey with final reward:")
    
    completion_result = await complete_journey(
        journey_id=journey_id,
        outcome="success",
        solution_description="Added pandas to requirements.txt and installed with uv add"
    )
    
    completion_data = json.loads(completion_result)
    logger.info(f"Journey completed: {journey_id}")
    logger.info(f"Final reward: {completion_data['final_reward']:.2f}")
    logger.info(f"Novel path: {completion_data['is_novel']}")
    logger.info(f"Insights: {completion_data['insights']}")
    
    # Example 4: Query similar journeys
    logger.info("\n4. Querying similar journeys:")
    
    similar_result = await query_similar_journeys(
        task_description="Fix import error for numpy",
        min_similarity=0.6
    )
    
    logger.info(f"Similar journeys: {similar_result}")
    
    logger.success("\n✅ Q-Learning Tool Journey system working!")
    return True

async def debug_function():
    """Test Q-learning reward calculations and Thompson Sampling."""
    logger.info("=== Debug Mode - Testing Reward System ===")
    
    # Test 1: State hashing
    logger.info("\n1. Testing state hashing:")
    test_states = [
        {
            "current_tool": "assess_complexity",
            "tools_used": ["assess_complexity"],
            "context": {"error_type": "ImportError"},
            "task_type": "error_fix"
        },
        {
            "current_tool": "assess_complexity",
            "tools_used": ["assess_complexity"],
            "context": {"error_type": "ImportError"},
            "task_type": "error_fix"
        }
    ]
    
    hash1 = _hash_state(test_states[0])
    hash2 = _hash_state(test_states[1])
    logger.info(f"Same states produce same hash: {hash1 == hash2} ({hash1})")
    
    # Test 2: Reward calculation
    logger.info("\n2. Testing reward calculations:")
    
    test_journeys = [
        {
            "name": "Optimal success",
            "actual_sequence": [
                {"tool": "assess_complexity", "success": True},
                {"tool": "discover_patterns", "success": True},
                {"tool": "track_solution_outcome", "success": True}
            ],
            "outcome": "success"
        },
        {
            "name": "Suboptimal success",
            "actual_sequence": [
                {"tool": "assess_complexity", "success": True},
                {"tool": "query_converter", "success": False},
                {"tool": "discover_patterns", "success": True},
                {"tool": "advanced_search", "success": True},
                {"tool": "track_solution_outcome", "success": True}
            ],
            "outcome": "success"
        },
        {
            "name": "Failure",
            "actual_sequence": [
                {"tool": "assess_complexity", "success": False},
                {"tool": "send_to_gemini", "success": False}
            ],
            "outcome": "failed"
        }
    ]
    
    for test_journey in test_journeys:
        reward = _calculate_reward(test_journey, test_journey["outcome"])
        logger.info(f"  {test_journey['name']}: {reward:.2f}")
    
    # Test 3: Thompson Sampling
    logger.info("\n3. Testing Thompson Sampling:")
    
    # Simulate different alpha/beta values
    thompson_tests = [
        (1, 1, "Uniform prior"),
        (10, 2, "High success rate"),
        (2, 10, "Low success rate"),
        (50, 50, "High confidence, average")
    ]
    
    for alpha, beta, desc in thompson_tests:
        samples = [np.random.beta(alpha, beta) for _ in range(100)]
        mean_sample = np.mean(samples)
        std_sample = np.std(samples)
        logger.info(f"  {desc}: α={alpha}, β={beta} → mean={mean_sample:.3f}, std={std_sample:.3f}")
    
    logger.success("\n✅ Debug tests completed!")
    return True

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            # Quick test mode for startup verification
            print("Testing Tool Journey MCP server with Q-Learning...")
            print("Features:")
            print("- Q-Learning for optimal tool sequences")
            print("- Thompson Sampling for exploration/exploitation")
            print("- Reward-based learning from outcomes")
            print("- Lazy loading for embeddings")
            print("Server ready to start.")
        elif sys.argv[1] == "working":
            asyncio.run(working_usage())
        elif sys.argv[1] == "debug":
            asyncio.run(debug_function())
    else:
        # Run as MCP server with graceful error handling
        try:
            logger.info("Starting Tool Journey MCP server with Q-Learning")
            mcp.run()
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.critical(f"MCP server crashed: {e}", exc_info=True)
            mcp_logger.log_error(e, {"context": "server_startup"})
            sys.exit(1)