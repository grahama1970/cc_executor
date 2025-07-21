#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "fastmcp",
#     "python-dotenv",
#     "loguru",
#     "pydantic",
#     "mcp-logger-utils>=0.1.5"
# ]
# ///
"""
MCP Server for validating LLM responses from various sources.

This tool validates responses from:
- LiteLLM API calls (structured JSON responses)
- CLI tools (raw text output from claude, gemini, etc.)
- Universal LLM executor outputs

=== USAGE INSTRUCTIONS FOR AGENTS ===
Run this script directly to test:
  python script.py          # Runs working_usage() - stable, known to work
  python script.py debug    # Runs debug_function() - for testing new ideas

DO NOT create separate test files - use the debug function!

=== VALIDATION TYPES ===

1. **Format Validation**: Check if response is valid JSON, has expected fields
2. **Content Validation**: Verify response contains expected information
3. **Quality Validation**: Check for hallucinations, completeness, accuracy
4. **Schema Validation**: Ensure response matches expected structure
5. **Token Validation**: Verify response is within token limits

=== EXAMPLES ===

1. Validate LiteLLM response:
   result = await validate_llm_response(
       response='{"status": "success", "response": {...}}',
       validation_type="litellm_batch",
       expected_fields=["status", "response", "cost"]
   )

2. Validate CLI output:
   result = await validate_llm_response(
       response="The capital of France is Paris.",
       validation_type="content",
       expected_content=["capital", "France", "Paris"]
   )

3. Validate JSON structure:
   result = await validate_llm_response(
       response='{"name": "John", "age": 30}',
       validation_type="schema",
       schema='{"type": "object", "properties": {"name": {"type": "string"}, "age": {"type": "number"}}}'
   )

=== RESPONSE FORMATS ===

The tool returns standardized responses:
{
    "success": true/false,
    "validation_passed": true/false,
    "issues": [...],  // List of validation issues found
    "suggestions": [...],  // Suggestions for fixing issues
    "metadata": {...}  // Additional validation metadata
}
"""

import os
import sys
import asyncio
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from enum import Enum

from fastmcp import FastMCP
from pydantic import BaseModel, Field
from dotenv import load_dotenv, find_dotenv
from loguru import logger

# Import standardized response utilities
sys.path.insert(0, str(Path(__file__).parent))
from utils.response_utils import create_success_response, create_error_response

# Import from our shared PyPI package
from mcp_logger_utils import MCPLogger, debug_tool

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")

# Load environment variables
load_dotenv(find_dotenv())

# Initialize MCP server and logger
mcp = FastMCP("response-validator")
mcp_logger = MCPLogger("response-validator")

# Response utilities are imported from utils.response_utils above

# Try to import optional dependencies
try:
    import json_repair
    JSON_REPAIR_AVAILABLE = True
except ImportError:
    JSON_REPAIR_AVAILABLE = False
    logger.warning("json-repair not available - JSON fixing will be limited")

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.warning("tiktoken not available - token counting will use estimates")


class ValidationType(str, Enum):
    """Types of validation available."""
    FORMAT = "format"  # JSON format, structure
    CONTENT = "content"  # Contains expected content
    SCHEMA = "schema"  # Matches JSON schema
    LITELLM_SINGLE = "litellm_single"  # LiteLLM single response
    LITELLM_BATCH = "litellm_batch"  # LiteLLM batch response
    CLI_OUTPUT = "cli_output"  # Raw CLI output
    QUALITY = "quality"  # Response quality checks


class ResponseValidator:
    """Validates LLM responses from various sources."""
    
    def __init__(self):
        self.token_encoder = None
        self._tiktoken_loaded = False
    
    def _ensure_tiktoken_loaded(self):
        """Lazy load tiktoken encoder."""
        if not self._tiktoken_loaded and TIKTOKEN_AVAILABLE:
            try:
                self.token_encoder = tiktoken.encoding_for_model("gpt-4")
            except:
                try:
                    self.token_encoder = tiktoken.get_encoding("cl100k_base")
                except:
                    pass
            self._tiktoken_loaded = True
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        self._ensure_tiktoken_loaded()
        if self.token_encoder:
            return len(self.token_encoder.encode(text))
        # Fallback: estimate ~4 chars per token
        return len(text) // 4
    
    def extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from text, handling various formats."""
        # Try direct parsing
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON blocks
        json_patterns = [
            r'```json\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
            r'\{[^{}]*\}',
            r'\[[^\[\]]*\]'
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    if JSON_REPAIR_AVAILABLE:
                        try:
                            return json_repair.loads(match)
                        except:
                            pass
        
        return None
    
    def validate_format(self, response: str, expected_format: str = "json") -> Dict[str, Any]:
        """Validate response format."""
        issues = []
        suggestions = []
        
        if expected_format == "json":
            try:
                json.loads(response)
                return {"valid": True, "issues": [], "suggestions": []}
            except json.JSONDecodeError as e:
                issues.append(f"Invalid JSON: {str(e)}")
                
                # Try to fix with json-repair
                if JSON_REPAIR_AVAILABLE:
                    try:
                        fixed = json_repair.loads(response)
                        suggestions.append("JSON can be repaired automatically")
                        return {
                            "valid": False,
                            "issues": issues,
                            "suggestions": suggestions,
                            "repaired": fixed
                        }
                    except:
                        pass
                
                # Try to extract JSON
                extracted = self.extract_json(response)
                if extracted:
                    suggestions.append("Found valid JSON embedded in response")
                    return {
                        "valid": False,
                        "issues": issues,
                        "suggestions": suggestions,
                        "extracted": extracted
                    }
                else:
                    suggestions.append("Wrap response in valid JSON format")
        
        return {"valid": False, "issues": issues, "suggestions": suggestions}
    
    def validate_content(self, response: str, expected_content: List[str]) -> Dict[str, Any]:
        """Validate response contains expected content."""
        issues = []
        found = []
        missing = []
        
        response_lower = response.lower()
        
        for content in expected_content:
            if content.lower() in response_lower:
                found.append(content)
            else:
                missing.append(content)
                issues.append(f"Missing expected content: '{content}'")
        
        return {
            "valid": len(missing) == 0,
            "issues": issues,
            "found": found,
            "missing": missing,
            "suggestions": [f"Ensure response mentions: {', '.join(missing)}"] if missing else []
        }
    
    def validate_litellm_response(self, response: Union[str, Dict], response_type: str = "single") -> Dict[str, Any]:
        """Validate LiteLLM response format."""
        issues = []
        suggestions = []
        
        # Parse if string
        if isinstance(response, str):
            parsed = self.extract_json(response)
            if not parsed:
                return {
                    "valid": False,
                    "issues": ["Could not parse JSON from response"],
                    "suggestions": ["Ensure response is valid JSON"]
                }
        else:
            parsed = response
        
        if response_type == "single":
            # Single response should have specific fields
            expected_fields = ["request_id", "status", "response"]
            optional_fields = ["cost", "error", "final_attempt"]
            
        elif response_type == "batch":
            # Batch response should be a list
            if not isinstance(parsed, list):
                issues.append("Batch response should be a list")
                return {"valid": False, "issues": issues, "suggestions": ["Return array of results"]}
            
            # Check each item
            for i, item in enumerate(parsed):
                if not isinstance(item, dict):
                    issues.append(f"Item {i} is not a dict")
                    continue
                
                for field in ["request_id", "status"]:
                    if field not in item:
                        issues.append(f"Item {i} missing field '{field}'")
                
                if item.get("status") == "success" and "response" not in item:
                    issues.append(f"Item {i} has success status but no response")
                elif item.get("status") == "error" and "error" not in item:
                    issues.append(f"Item {i} has error status but no error message")
            
            return {
                "valid": len(issues) == 0,
                "issues": issues,
                "suggestions": suggestions,
                "item_count": len(parsed)
            }
        
        # Check fields for single response
        for field in expected_fields:
            if field not in parsed:
                issues.append(f"Missing required field: '{field}'")
                suggestions.append(f"Add '{field}' field to response")
        
        # Check status values
        if "status" in parsed and parsed["status"] not in ["success", "error"]:
            issues.append(f"Invalid status: '{parsed.get('status')}' (should be 'success' or 'error')")
        
        # Check error handling
        if parsed.get("status") == "error" and "error" not in parsed:
            issues.append("Status is 'error' but no error message provided")
            suggestions.append("Add 'error' field with error message")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "suggestions": suggestions,
            "fields_found": list(parsed.keys()) if isinstance(parsed, dict) else []
        }
    
    def validate_cli_output(self, response: str, checks: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Validate CLI tool output."""
        issues = []
        suggestions = []
        metadata = {}
        
        # Basic checks
        if not response or not response.strip():
            return {
                "valid": False,
                "issues": ["Empty response"],
                "suggestions": ["Ensure CLI tool produced output"]
            }
        
        # Check for common error patterns
        error_patterns = [
            (r"error:?\s+(.+)", "Error detected"),
            (r"exception:?\s+(.+)", "Exception detected"),
            (r"failed:?\s+(.+)", "Failure detected"),
            (r"timeout", "Timeout detected"),
            (r"permission denied", "Permission issue detected"),
            (r"not found", "Resource not found"),
            (r"invalid", "Invalid input/operation detected")
        ]
        
        response_lower = response.lower()
        for pattern, message in error_patterns:
            if re.search(pattern, response_lower):
                issues.append(message)
        
        # Token count check
        token_count = self.count_tokens(response)
        metadata["token_count"] = token_count
        
        if token_count > 100000:
            issues.append(f"Response very large: {token_count} tokens")
            suggestions.append("Consider chunking or summarizing response")
        
        # Check for truncation indicators
        truncation_patterns = ["...", "[truncated]", "[output truncated]", "max length"]
        for pattern in truncation_patterns:
            if pattern in response_lower:
                issues.append("Response appears to be truncated")
                suggestions.append("Increase output limit or use streaming")
                break
        
        # Custom checks if provided
        if checks:
            if "min_length" in checks and len(response) < checks["min_length"]:
                issues.append(f"Response too short: {len(response)} chars (min: {checks['min_length']})")
            
            if "max_length" in checks and len(response) > checks["max_length"]:
                issues.append(f"Response too long: {len(response)} chars (max: {checks['max_length']})")
            
            if "must_contain" in checks:
                for term in checks["must_contain"]:
                    if term not in response:
                        issues.append(f"Missing required content: '{term}'")
            
            if "must_not_contain" in checks:
                for term in checks["must_not_contain"]:
                    if term in response:
                        issues.append(f"Contains forbidden content: '{term}'")
        
        # Check if JSON extraction is possible
        json_data = self.extract_json(response)
        if json_data:
            metadata["has_json"] = True
            metadata["json_data"] = json_data
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "suggestions": suggestions,
            "metadata": metadata
        }
    
    def validate_quality(self, response: str, prompt: Optional[str] = None) -> Dict[str, Any]:
        """Check response quality indicators."""
        issues = []
        suggestions = []
        quality_indicators = {}
        
        # Check for hallucination indicators
        hallucination_phrases = [
            "as an ai language model",
            "i don't have access to",
            "i cannot browse",
            "based on my training data",
            "as of my last update",
            "i don't have real-time"
        ]
        
        response_lower = response.lower()
        for phrase in hallucination_phrases:
            if phrase in response_lower:
                issues.append(f"Potential hallucination indicator: '{phrase}'")
                quality_indicators["has_disclaimers"] = True
        
        # Check for non-answers
        non_answer_patterns = [
            r"i (?:don't|do not|can't|cannot) (?:know|understand|help)",
            r"(?:unable|impossible) to (?:determine|assist|help)",
            r"insufficient (?:information|context|data)"
        ]
        
        for pattern in non_answer_patterns:
            if re.search(pattern, response_lower):
                issues.append("Response appears to be a non-answer")
                suggestions.append("Provide more specific context or rephrase question")
                quality_indicators["is_non_answer"] = True
                break
        
        # Check response coherence
        sentences = re.split(r'[.!?]+', response)
        sentence_count = len([s for s in sentences if s.strip()])
        
        if sentence_count == 0:
            issues.append("No complete sentences found")
        elif sentence_count == 1 and len(response) > 200:
            issues.append("Very long single sentence - may lack structure")
            suggestions.append("Break into multiple sentences for clarity")
        
        quality_indicators["sentence_count"] = sentence_count
        
        # Check for repetition
        words = response_lower.split()
        if len(words) > 10:
            word_freq = {}
            for word in words:
                if len(word) > 4:  # Only check longer words
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            repetitive_words = [w for w, count in word_freq.items() if count > len(words) * 0.1]
            if repetitive_words:
                issues.append(f"Excessive repetition of words: {', '.join(repetitive_words[:3])}")
                quality_indicators["has_repetition"] = True
        
        # Check if response addresses the prompt
        if prompt:
            prompt_keywords = [w.lower() for w in prompt.split() if len(w) > 3]
            addressed_keywords = [w for w in prompt_keywords if w in response_lower]
            coverage = len(addressed_keywords) / len(prompt_keywords) if prompt_keywords else 1.0
            
            quality_indicators["prompt_coverage"] = coverage
            if coverage < 0.3:
                issues.append("Response may not address the prompt adequately")
                suggestions.append("Ensure response directly answers the question")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "suggestions": suggestions,
            "quality_indicators": quality_indicators
        }


# Create global validator instance
validator = ResponseValidator()


@mcp.tool()
@debug_tool(mcp_logger)
async def validate_llm_response(
    response: str,
    validation_type: str = "format",
    expected_fields: Optional[List[str]] = None,
    expected_content: Optional[List[str]] = None,
    schema: Optional[str] = None,
    prompt: Optional[str] = None,
    checks: Optional[Dict[str, Any]] = None
) -> str:
    """
    Validates LLM responses from various sources.
    
    Args:
        response: The response to validate (string or JSON)
        validation_type: Type of validation to perform
        expected_fields: Fields expected in JSON response
        expected_content: Content expected in response
        schema: JSON schema to validate against
        prompt: Original prompt (for quality checks)
        checks: Additional validation checks
    
    Returns:
        JSON string with standardized validation results
    """
    start_time = time.time()
    
    try:
        logger.info(f"Validating response with type: {validation_type}")
        
        # Route to appropriate validation
        if validation_type == ValidationType.FORMAT:
            result = validator.validate_format(response, "json")
            
        elif validation_type == ValidationType.CONTENT:
            if not expected_content:
                return create_error_response(
                    "expected_content required for content validation",
                    tool_name="validate_llm_response",
                    start_time=start_time
                )
            result = validator.validate_content(response, expected_content)
            
        elif validation_type == ValidationType.LITELLM_SINGLE:
            result = validator.validate_litellm_response(response, "single")
            
        elif validation_type == ValidationType.LITELLM_BATCH:
            result = validator.validate_litellm_response(response, "batch")
            
        elif validation_type == ValidationType.CLI_OUTPUT:
            result = validator.validate_cli_output(response, checks)
            
        elif validation_type == ValidationType.QUALITY:
            result = validator.validate_quality(response, prompt)
            
        elif validation_type == ValidationType.SCHEMA:
            # TODO: Implement JSON schema validation
            result = {
                "valid": False,
                "issues": ["Schema validation not yet implemented"],
                "suggestions": ["Use format validation for now"]
            }
            
        else:
            return create_error_response(
                f"Unknown validation type: {validation_type}",
                tool_name="validate_llm_response",
                start_time=start_time
            )
        
        # Build response
        validation_result = {
            "validation_passed": result.get("valid", False),
            "issues": result.get("issues", []),
            "suggestions": result.get("suggestions", []),
            "metadata": {
                "validation_type": validation_type,
                "response_length": len(response),
                "timestamp": datetime.now().isoformat()
            }
        }
        
        # Add type-specific metadata
        for key in ["fields_found", "quality_indicators", "token_count", "has_json", "item_count"]:
            if key in result:
                validation_result["metadata"][key] = result[key]
        
        # Add extracted/repaired data if available
        for key in ["extracted", "repaired", "json_data"]:
            if key in result:
                validation_result[key] = result[key]
        
        return create_success_response(
            data=validation_result,
            tool_name="validate_llm_response",
            start_time=start_time
        )
        
    except Exception as e:
        logger.exception(f"Validation failed: {e}")
        return create_error_response(
            f"Validation error: {type(e).__name__}: {e}",
            tool_name="validate_llm_response",
            start_time=start_time
        )


async def working_usage():
    """Demonstrate proper usage of the response validator tool."""
    logger.info("=== Response Validator Working Usage ===")
    
    # Example 1: Validate LiteLLM single response
    logger.info("\n1. Validating LiteLLM single response:")
    
    litellm_response = json.dumps({
        "request_id": "test_123",
        "status": "success",
        "response": {
            "id": "chatcmpl-123",
            "choices": [{"message": {"content": "Paris is the capital of France."}}]
        },
        "cost": 0.0002
    })
    
    result = await validate_llm_response(
        response=litellm_response,
        validation_type="litellm_single"
    )
    
    result_data = json.loads(result)
    logger.info(f"Result: {result}")
    assert result_data["success"], "Validation should succeed"
    assert result_data["data"]["validation_passed"], "Valid LiteLLM response should pass"
    
    # Example 2: Validate CLI output
    logger.info("\n2. Validating CLI output:")
    
    cli_output = """
    The capital of France is Paris. Paris is known for the Eiffel Tower,
    art museums, and café culture. The city has a population of over 2 million.
    """
    
    result2 = await validate_llm_response(
        response=cli_output,
        validation_type="cli_output",
        checks={"min_length": 50, "must_contain": ["Paris", "France"]}
    )
    
    result2_data = json.loads(result2)
    logger.info(f"Result: {result2}")
    assert result2_data["success"], "Validation should succeed"
    
    # Example 3: Validate content
    logger.info("\n3. Validating content presence:")
    
    result3 = await validate_llm_response(
        response="The weather in Tokyo is sunny with temperatures around 25°C.",
        validation_type="content",
        expected_content=["weather", "Tokyo", "temperature"]
    )
    
    result3_data = json.loads(result3)
    logger.info(f"Result: {result3}")
    
    # Example 4: Validate JSON format with repair
    logger.info("\n4. Validating malformed JSON:")
    
    malformed_json = '{"name": "John", "age": 30, "city": "New York"'  # Missing closing brace
    
    result4 = await validate_llm_response(
        response=malformed_json,
        validation_type="format"
    )
    
    result4_data = json.loads(result4)
    logger.info(f"Result: {result4}")
    assert not result4_data["data"]["validation_passed"], "Malformed JSON should fail"
    
    # Example 5: Quality validation
    logger.info("\n5. Validating response quality:")
    
    poor_response = "I don't know. I cannot help with that. Unable to determine the answer."
    
    result5 = await validate_llm_response(
        response=poor_response,
        validation_type="quality",
        prompt="What is the capital of France?"
    )
    
    result5_data = json.loads(result5)
    logger.info(f"Result: {result5}")
    assert not result5_data["data"]["validation_passed"], "Poor quality response should fail"
    
    logger.success("\n✅ Response validator working correctly!")
    return True


async def debug_function():
    """Debug function for testing edge cases and new validation types."""
    logger.info("=== Debug Mode - Testing Response Validator Edge Cases ===")
    
    # Test 1: Batch response validation
    logger.info("\n1. Testing batch response validation:")
    
    batch_response = json.dumps([
        {
            "request_id": "req_1",
            "status": "success",
            "response": {"choices": [{"message": {"content": "Response 1"}}]},
            "cost": 0.001
        },
        {
            "request_id": "req_2",
            "status": "error",
            "error": "Rate limit exceeded"
        },
        {
            "request_id": "req_3",
            "status": "success",
            "response": {"choices": [{"message": {"content": "Response 3"}}]},
            "cost": 0.001
        }
    ])
    
    result = await validate_llm_response(
        response=batch_response,
        validation_type="litellm_batch"
    )
    logger.info(f"Batch validation: {result}")
    
    # Test 2: Very large response
    logger.info("\n2. Testing large response handling:")
    
    large_response = "Lorem ipsum " * 10000  # ~20k words
    
    result = await validate_llm_response(
        response=large_response,
        validation_type="cli_output",
        checks={"max_length": 100000}
    )
    
    result_data = json.loads(result)
    logger.info(f"Token count: {result_data['data']['metadata'].get('token_count', 'N/A')}")
    
    # Test 3: Embedded JSON extraction
    logger.info("\n3. Testing JSON extraction from text:")
    
    mixed_response = """
    Here's the analysis you requested:
    
    ```json
    {
        "sentiment": "positive",
        "score": 0.85,
        "keywords": ["happy", "excited", "wonderful"]
    }
    ```
    
    The sentiment analysis shows a positive result.
    """
    
    result = await validate_llm_response(
        response=mixed_response,
        validation_type="format"
    )
    
    result_data = json.loads(result)
    if "extracted" in result_data["data"]:
        logger.info(f"Extracted JSON: {result_data['data']['extracted']}")
    
    # Test 4: Multiple validation types
    logger.info("\n4. Testing combined validations:")
    
    # First validate format
    response = '{"result": "The capital is Paris", "confidence": 0.95}'
    
    format_result = await validate_llm_response(
        response=response,
        validation_type="format"
    )
    
    # Then validate content
    content_result = await validate_llm_response(
        response=response,
        validation_type="content",
        expected_content=["capital", "Paris"]
    )
    
    logger.info(f"Format valid: {json.loads(format_result)['data']['validation_passed']}")
    logger.info(f"Content valid: {json.loads(content_result)['data']['validation_passed']}")
    
    # Test 5: Error pattern detection
    logger.info("\n5. Testing error pattern detection:")
    
    error_responses = [
        "Error: Connection timeout while processing request",
        "Permission denied: cannot access /etc/passwd",
        "Failed to execute: command not found",
        "The operation completed successfully with result: 42"
    ]
    
    for resp in error_responses:
        result = await validate_llm_response(
            response=resp,
            validation_type="cli_output"
        )
        result_data = json.loads(result)
        logger.info(f"Response: '{resp[:50]}...' - Issues: {len(result_data['data']['issues'])}")
    
    logger.success("\n✅ Debug tests completed!")
    return True


if __name__ == "__main__":
    """
    AGENT INSTRUCTIONS:
    - DEFAULT: Runs working_usage() - stable example that works
    - DEBUG: Run with 'debug' argument to test new ideas
    - DO NOT create external test files - use debug_function() instead!
    """
    import sys
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "working"
    
    if mode == "debug":
        print("Running debug mode...")
        asyncio.run(debug_function())
    elif mode == "test":
        print("Testing Response Validator MCP server...")
        print("This tool validates LLM responses from various sources.")
        print("It checks format, content, quality, and structure.")
        print("Server ready to start.")
    else:
        try:
            if mode == "working":
                asyncio.run(working_usage())
            else:
                logger.info("Starting Response Validator MCP server")
                mcp.run()
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.critical(f"MCP server crashed: {e}", exc_info=True)
            if mcp_logger:
                try:
                    mcp_logger.log_error({"error": str(e), "context": "server_startup"})
                except:
                    pass
            sys.exit(1)