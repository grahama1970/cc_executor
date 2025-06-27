"""
Module: multimodal_utils.py
Description: Utility functions and helpers for multimodal utils

External Dependencies:
- loguru: [Documentation URL]
- llm_call: [Documentation URL]

Sample Input:
>>> # Add specific examples based on module functionality

Expected Output:
>>> # Add expected output examples

Example Usage:
>>> # Add usage examples
"""

from typing import List, Dict, Any
from loguru import logger

from llm_call.core.utils.image_processing_utils import process_image_input

###
# Helper Functions
###
def is_multimodal(messages: List[Dict[str, Any]]) -> bool:
    """
    Determine if the messages list contains multimodal content (e.g., images).

    Args:
        messages (List[Dict[str, Any]]): List of message dictionaries.

    Returns:
        bool: True if any message contains multimodal content, False otherwise.
    """
    for message in messages:
        content = message.get('content')
        if (
            isinstance(content, list) and 
            any(item.get("type") == "image_url" for item in content)
        ):
            return True
    return False



def process_messages_for_content(messages: List[Dict[str, Any]], image_directory: str, max_size_kb: int = 500) -> List[Dict[str, Any]]:
    """
    Processes messages to extract text and image content in a structured format.

    Args:
        messages (List[Dict[str, Any]]): List of messages containing text or image inputs.
        image_directory (str): Directory to store compressed images.
        max_size_kb (int): Maximum size for compressed images in KB.

    Returns:
        List[Dict[str, Any]]: Structured content list including text, Base64-encoded images, or external URLs.
    """
    # Early return if no images are found
    if not any("image" in msg for msg in messages):
        return messages
    
    if not messages:
        logger.warning("Received empty messages list. Returning an empty content list.")
        return []

    content_list = []
    for msg in messages:
        if "content" in msg and isinstance(msg["content"], str):  # Handle text content
            content_list.append({"type": "text", "text": msg["content"]})
        elif "image" in msg:  # Handle image content
            try:
                processed_image = process_image_input(msg["image"], image_directory, max_size_kb=max_size_kb)
                content_list.append(processed_image)
            except ValueError as e:
                logger.exception(f"Skipping unsupported image input: {msg['image']} - {e}")
        else:
            logger.warning(f"Unsupported message type detected: {msg}. Skipping.")
    return content_list


def format_multimodal_messages(
    messages: List[Dict[str, Any]], 
    image_directory: str, # This is now primarily a cache/output dir for processing
    max_size_kb: int
) -> List[Dict[str, Any]]:
    """
    Processes messages list for multimodal content.
    - For local image paths in "image_url" items, converts them to Base64 data URIs
      after potentially compressing them.
    - HTTP(S) URLs are passed through (as OpenAI supports them directly).
    - Existing Base64 data URIs are passed through (or could be re-processed if too large).
    """
    if not messages:
        return []

    processed_messages_list = []
    for message in messages:
        original_content = message.get("content")
        role = message.get("role", "user")

        if isinstance(original_content, list): # Expected format for multimodal messages
            new_content_parts = []
            valid_message = True
            for item in original_content:
                if not isinstance(item, dict): # Skip malformed parts
                    logger.warning(f"Skipping malformed content item (not a dict): {item}")
                    new_content_parts.append(item) # Or simply skip: continue
                    continue

                item_type = item.get("type")
                if item_type == "text":
                    new_content_parts.append(item)
                elif item_type == "image_url":
                    image_url_data = item.get("image_url", {}).get("url")
                    if not image_url_data:
                        logger.warning(f"Skipping image_url item with no URL: {item}")
                        continue # Skip this malformed image item

                    # process_image_input handles if it's HTTP, Base64, or local path
                    # It returns a dict like {"type": "image_url", "image_url": {"url": "..."}} or None
                    processed_image_item = process_image_input(
                        image_url_data, 
                        image_directory, # Used as cache/output for compression
                        max_size_kb
                    )
                    
                    if processed_image_item:
                        new_content_parts.append(processed_image_item)
                    else:
                        logger.warning(f"Failed to process image_url item ('{str(image_url_data)[:100]}...'). Skipping this image.")
                        # Decide if a message with a failed image should be dropped or text kept
                        # For now, we just skip the image part.
                else:
                    new_content_parts.append(item) # Pass through other types

            if new_content_parts: # Only add message if content remains
                processed_messages_list.append({"role": role, "content": new_content_parts})
            else:
                logger.warning(f"Message from role '{role}' became empty after processing image parts. Original content: {original_content}")
        
        elif isinstance(original_content, str): # Simple text message
            processed_messages_list.append({"role": role, "content": original_content})
        
        else: # Fallback for unexpected message content structure
            logger.warning(f"Message from role '{role}' has unexpected content type: {type(original_content)}. Keeping original.")
            processed_messages_list.append(message)
            
    return processed_messages_list




###
# Main Function for Multimodal Processing
###
def prepare_multimodal_messages(
    messages: List[Dict[str, Any]],
    config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Handles multimodal message processing.

    Args:
        messages (List[Dict[str, Any]]): Input messages.
        config (Dict[str, Any]): Configuration dictionary.

    Returns:
        List[Dict[str, Any]]: Processed messages or original messages if processing fails.
    """
    if not messages:
        logger.warning("Empty messages list received. Skipping multimodal processing.")
        return messages

    image_directory = config["directories"]["images"]
    max_image_size_kb = config["llm_config"].get("max_image_size_kb", 500)

    logger.debug("Checking for multimodal content in messages...")
    if is_multimodal(messages):
        logger.info("Multimodal content detected. Processing messages...")
        try:
            processed_messages = format_multimodal_messages(
                messages, image_directory, max_image_size_kb
            )
            logger.info("Multimodal processing completed successfully.")
            return processed_messages
        except Exception as e:
            logger.exception(f"Error during multimodal processing: {e}")
            logger.debug("Falling back to raw messages.")
            return messages
    logger.info("No multimodal content detected. Returning original messages.")
    return messages