"""
Module: json_utils.py
Description: Robust JSON parsing and repair utilities.
"""
import json
import re
from typing import Any, Dict, List, Optional, Union

from json_repair import repair_json
from loguru import logger

def repair_and_parse_json(
    content: Union[str, dict, list],
    logger_instance: Optional[Any] = None,
) -> Union[Dict, List, str]:
    """
    Cleans and parses a string that is expected to be JSON, but might be malformed
    or wrapped in markdown code blocks. Handles common LLM output issues.

    Args:
        content: The input string, dict, or list to clean. If it's already a
                 dict or list, it will be returned directly.
        logger_instance: An optional loguru logger instance to log repair steps.

    Returns:
        A cleaned Python dict or list, or the original string if it cannot be
        parsed into a valid JSON structure.
    """
    log = logger_instance or logger  # Use provided logger or a default one

    if isinstance(content, (dict, list)):
        return content

    if not isinstance(content, str):
        log.warning(f"Input is not a string, dict, or list, returning as is. Type: {type(content)}")
        return content

    original_content = content
    # 1. Extract from markdown code blocks if present
    # This is a common pattern for LLMs
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
    if match:
        content = match.group(1).strip()
        log.debug("Extracted content from JSON markdown block.")

    # 2. Try direct parsing first
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        log.debug("Direct JSON parsing failed, attempting repair.")

    # 3. Attempt to repair the JSON
    try:
        # The repair_json function is robust against many common errors
        repaired = repair_json(content, return_objects=True)
        if isinstance(repaired, (dict, list)):
            log.info("Successfully repaired and parsed JSON content.")
            return repaired
    except Exception as e:
        log.error(f"JSON repair failed unexpectedly: {e}")
        # Fallback to returning the original string
        return original_content
        
    log.warning("Could not parse content as JSON, returning original string.")
    return original_content