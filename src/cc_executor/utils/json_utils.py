"""
Module: json_utils.py
Description: Utility functions and helpers for json utils

External Dependencies:
- json_repair: [Documentation URL]
- loguru: [Documentation URL]

Sample Input:
>>> # Add specific examples based on module functionality

Expected Output:
>>> # Add expected output examples

Example Usage:
>>> # Add usage examples
"""

import json
import os
import json
from pathlib import Path
import re
from typing import Union, Callable, Any

from json_repair import repair_json
from loguru import logger

class PathEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Path):
            return str(obj)
        return super().default(obj)

def json_serialize(data, handle_paths=False, **kwargs):
    """
    Serialize data to JSON, optionally handling Path objects.
    
    Args:
        data: The data to serialize.
        handle_paths (bool): Whether to handle Path objects explicitly.
        **kwargs: Additional arguments for json.dumps().
    
    Returns:
        str: JSON-serialized string.
    """
    if handle_paths:
        return json.dumps(data, cls=PathEncoder, **kwargs)
    return json.dumps(data, **kwargs)



def load_json_file(file_path):
    """
    Load the extracted tables cache from a JSON file.

    Args:
        file_path (str): The path to the file from where the cache will be loaded.

    Returns:
        Any: The data loaded from the JSON file, or None if the file does not exist.
    """
    if not os.path.exists(file_path):
        logger.warning(f'File does not exist: {file_path}')
        return None
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
        logger.info('JSON file loaded successfully')
        return data
    except json.JSONDecodeError as e:
        logger.warning(f'JSON decoding error: {e}, trying utf-8-sig encoding')
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as file:
                data = json.load(file)
            logger.info('JSON file loaded successfully with utf-8-sig encoding')
            return data
        except json.JSONDecodeError:
            logger.error('JSON decoding error persists with utf-8-sig encoding')
            raise
    except IOError as e:
        logger.error(f'I/O error: {e}')
        raise

def save_json_to_file(data, file_path):
    """
    Save the extracted tables cache to a JSON file.

    Args:
        cache (Any): The data to be saved.
        file_path (str): The path to the file where cache will be saved.
        logger (logging.Logger, optional): A logger instance. If None, a default logger will be used.
    """
    directory = os.path.dirname(file_path)
    try:
        if directory:
            os.makedirs(directory, exist_ok=True)
            logger.info(f'Ensured the directory exists: {directory}')
    except OSError as e:
        logger.error(f'Failed to create directory {directory}: {e}')
        raise
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
            logger.info(f'Saved extracted tables to JSON cache at: {file_path}')
    except Exception as e:
        logger.error(f'Failed to save cache to {file_path}: {e}')
        raise


def parse_json(content: str, logger=None) -> Union[dict, list, str]:
    """
    Attempt to parse a JSON string directly, and if that fails, try repairing it.

    Args:
    content (str): The input JSON string to parse.

    Returns:
    Union[dict, list, str]: Parsed JSON as a dict or list, or the original string if parsing fails.
    """
    try:
        parsed_content = json.loads(content)
        logger.debug('Successfully parsed JSON response directly')
        return parsed_content
    except json.JSONDecodeError as e:
        logger.warning(f'Direct JSON parsing failed: {e}')
    try:
        json_match = re.search('(\\[.*\\]|\\{.*\\})', content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
        repaired_json = repair_json(content, return_objects=True)
        if isinstance(repaired_json, (dict, list)):
            logger.info('Successfully repaired and validated JSON response')
            return repaired_json
        parsed_content = json.loads(repaired_json)
        logger.debug('Successfully validated JSON response')
        return parsed_content
    except json.JSONDecodeError as e:
        logger.error(f'JSON decode error after repair attempt: {e}')
    except Exception as e:
        logger.error(f'Failed to parse JSON response: {e}')
    logger.debug(f'Returning original content as string: {content}')
    return content

def clean_json_string(content: Union[str, dict, list], return_dict: bool=False) -> Union[str, dict, list]:
    """
    Clean and parse a JSON string, dict, or list, returning either a valid JSON string or a Python dict/list.

    Args:
    content (Union[str, dict, list]): The input JSON string, dict, or list to clean.
    return_dict (bool): If True, return a Python dict/list; if False, return a JSON string.

    Returns:
    Union[str, dict, list]: Cleaned JSON as a string, dict, or list, depending on return_dict parameter.
    """
    if isinstance(content, (dict, list)):
        return content if return_dict else json.dumps(content)
    elif isinstance(content, str) and return_dict == False:
        return content
    elif isinstance(content, str) and return_dict == True:
        # Check if the string contains the word 'json' (a common feature of LLM responses)
        # and try to extract JSON content if it does
        if 'json' in content.lower():
            # Try to extract JSON content from the string
            matches = re.findall(r'```(?:json)?\s*([\s\S]*?)```', content)
            if matches:
                # Use the first match as the JSON content
                json_content = matches[0].strip()
                logger.debug(f"Extracted JSON content from markdown code block: {json_content[:100]}...")
                try:
                    return json.loads(json_content)
                except json.JSONDecodeError:
                    logger.debug("Failed to parse extracted content as JSON, falling back to parse_json")
                    parsed_content = parse_json(json_content, logger)
                    return parsed_content if isinstance(parsed_content, (dict, list)) else json_content

        # Default behavior if no JSON was extracted from code blocks
        parsed_content = parse_json(content, logger)
        if return_dict and isinstance(parsed_content, str):
            try:
                return json.loads(parsed_content)
            except Exception as e:
                logger.error(f'Failed to convert parsed content to dict/list: {e}\nFailed content: {type(parsed_content)}: {parsed_content}')
                return parsed_content
        return parsed_content
    logger.info(f'Returning original content: {content}')
    return content


def json_to_markdown(data, level=1, title_case=True):
    md = ""
    if isinstance(data, dict):
        for key, value in data.items():
            heading = key.replace('_', ' ').title() if title_case else key
            if key.lower() == "summary" and isinstance(value, str):
                md += f"{'#' * level} {heading}\n\n{value.strip()}\n\n"
            elif key.lower() == "table_of_contents" and isinstance(value, list):
                md += f"{'#' * level} {heading}\n\n"
                for item in value:
                    md += f"- {item}\n"
                md += "\n"
            elif key.lower() == "key_sections" and isinstance(value, list):
                md += f"{'#' * level} {heading}\n\n"
                for section in value:
                    name = section.get("name", "")
                    desc = section.get("description", "")
                    md += f"- **{name}**\n\n  {desc}\n\n"
            else:
                # For other keys, recurse
                md += f"{'#' * level} {heading}\n\n"
                md += json_to_markdown(value, level + 1, title_case)
    elif isinstance(data, list):
        for item in data:
            md += "- " + json_to_markdown(item, level + 1, title_case).lstrip()
    else:
        md += str(data) + "\n\n"
    return md


def usage_example():
    """
    Example usage of the clean_json_string function.
    """
    example_json_str = '{"name": "John", "age": 30, "city": "New York"}'
    example_invalid_json_str = '{"name": "John", "age": 30, "city": "New York" some invalid text}'
    example_dict = {'name': 'John', 'age': 30, 'city': 'New York'}
    example_list_of_dicts = '[\n        {\n            "type": "function",\n            "function": {\n                "name": "get_current_weather",\n                "description": "Get the current weather in a given location as a plain text string.",\n                "parameters": {\n                    "type": "object",\n                    "properties": {\n                        "location": {"type": "string"},\n                        "unit": {"type": "string", "default": "celsius"}\n                    },\n                    "required": ["location"]\n                },\n                "dependencies": []\n            }\n        },\n        {\n            "type": "function",\n            "function": {\n                "name": "get_clothes",\n                "description": "Function to recommend clothing based on temperature and weather condition.",\n                "parameters": {\n                    "type": "object",\n                    "properties": {\n                        "temperature": {"type": "string"},\n                        "condition": {"type": "string"}\n                    },\n                    "required": ["temperature", "condition"]\n                },\n                "dependencies": ["get_weather"]\n            }\n        }\n    ]'
    schema_v2 = '{authors: list[str], title: str, abstract: str, keywords: list[str]}'
    print(clean_json_string(schema_v2, return_dict=True))
    example_mixed_content = 'Here is some text {"name": "John", "age": 30, "city": "New York"} and more text.'
    example_nested_json = '{"person": {"name": "John", "details": {"age": 30, "city": "New York"}}}'
    example_escaped_characters = '{"text": "He said, \\"Hello, World!\\""}'
    example_large_json = json.dumps([{'index': i, 'value': i * 2} for i in range(1000)])
    example_partial_json = '{"name": "John", "age": 30, "city":'
    print('Valid JSON String (return dict):')
    print(clean_json_string(example_json_str, return_dict=True))
    print('\nInvalid JSON String (return dict):')
    print(clean_json_string(example_invalid_json_str, return_dict=True))
    print('\nDict input (return dict):')
    print(clean_json_string(example_dict, return_dict=True))
    print('\nList of dicts (return dict):')
    print(clean_json_string(example_list_of_dicts, return_dict=True))
    print('\nMixed content (return dict):')
    print(clean_json_string(example_mixed_content, return_dict=True))
    print('\nNested JSON (return dict):')
    print(clean_json_string(example_nested_json, return_dict=True))
    print('\nEscaped characters (return dict):')
    print(clean_json_string(example_escaped_characters, return_dict=True))
    print('\nPartial JSON (return dict):')
    print(clean_json_string(example_partial_json, return_dict=True))
if __name__ == '__main__':
    usage_example()