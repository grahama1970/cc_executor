"""
Data models for LiteLLM MCP servers.
"""

import uuid
from typing import List, Dict, Optional, Literal, Any
from pydantic import BaseModel, Field


class LiteLLMRequest(BaseModel):
    """Model for a single LiteLLM request."""
    model: str
    messages: List[Dict[str, str]]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    cache: Optional[Dict[str, Any]] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class LiteLLMResult(BaseModel):
    """Model for a LiteLLM result."""
    request_id: str
    status: Literal["success", "error"]
    response: Optional[Dict[str, Any]] = None
    cost: Optional[float] = None
    error: Optional[str] = None
    final_attempt: int = 1