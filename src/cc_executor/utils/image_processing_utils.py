"""
Module: image_processing_utils.py
Description: Utility functions and helpers for image processing utils

External Dependencies:
- base64: [Documentation URL]
- mimetypes: [Documentation URL]
- PIL: [Documentation URL]
- loguru: [Documentation URL]
- requests: https://requests.readthedocs.io/

Sample Input:
>>> # Add specific examples based on module functionality

Expected Output:
>>> # Add expected output examples

Example Usage:
>>> # Add usage examples
"""

import base64
import hashlib
from typing import Any, Dict, Optional, Tuple, Union
import mimetypes
from pathlib import Path
from PIL import Image
import os
import time
from loguru import logger
import requests

# Supported image formats with MIME types
SUPPORTED_FORMATS = {
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'webp': 'image/webp',
    'gif': 'image/gif'
}

# Size limits based on API documentation
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
MAX_RESOLUTION = (2048, 2048)


def detect_image_format(image_path: Union[str, Path]) -> str:
    """
    Detect image format with multiple fallback methods.
    
    Returns:
        Format string (e.g., 'png', 'jpeg') or 'unknown'
    """
    image_path = Path(image_path)
    
    # Try from extension first
    ext = image_path.suffix.lower().lstrip('.')
    if ext in SUPPORTED_FORMATS:
        return ext
    
    # Try from MIME type
    mime_type, _ = mimetypes.guess_type(str(image_path))
    if mime_type:
        for fmt, mime in SUPPORTED_FORMATS.items():
            if mime == mime_type:
                return fmt
    
    # Use PIL as fallback
    try:
        with Image.open(image_path) as img:
            format_str = img.format.lower() if img.format else "unknown"
            # Normalize jpeg/jpg
            if format_str == "jpeg":
                return "jpeg"
            return format_str
    except Exception:
        return "unknown"


# download_and_cache_image remains the same

def compress_image(image_path_str: str, image_directory_str: str, max_size_kb: int, max_attempts: int = 5, resize_step: int = 10) -> str:
    """
    Compress and resize an image file to be under the size threshold.
    Returns path to the compressed image, or original path if fails or not needed.
    """
    # Ensure image_directory exists
    image_output_dir = Path(image_directory_str)
    image_output_dir.mkdir(parents=True, exist_ok=True)

    original_image_path = Path(image_path_str)
    if not original_image_path.is_file():
        logger.error(f"Compress Image Error: Original image not found at {original_image_path}")
        raise FileNotFoundError(f"Original image not found: {original_image_path}")

    # Create a name for the potentially compressed version
    original_file_name = original_image_path.name
    # Always output as JPEG for consistent compression control, adjust if lossless is needed
    compressed_file_name = f"{original_image_path.stem}_compressed.jpg"
    compressed_file_path = image_output_dir / compressed_file_name
    
    logger.debug(f"Compressing '{original_image_path}' to be under {max_size_kb}KB. Output target: '{compressed_file_path}'")

    try:
        img = Image.open(original_image_path)
        
        # Convert to RGB if it has an alpha channel (e.g., PNG with transparency)
        # as JPEG doesn't support alpha.
        if img.mode == 'RGBA' or img.mode == 'LA' or (img.mode == 'P' and 'transparency' in img.info):
            logger.debug(f"Image {original_file_name} has alpha or is palette with transparency, converting to RGB for JPEG compression.")
            img = img.convert("RGB")

        current_width, current_height = img.size
        current_quality = 90 # Start with high quality

        for attempt in range(max_attempts):
            logger.debug(f"Compression attempt {attempt + 1}/{max_attempts} for {original_file_name}. Quality: {current_quality}, Size: {current_width}x{current_height}")
            
            # Create a new image object for resizing if dimensions changed
            img_to_save = img
            if img.size != (current_width, current_height): # If img was resized in previous iteration
                 img_to_save = img.resize((current_width, current_height), Image.Resampling.LANCZOS)

            img_to_save.save(compressed_file_path, format="JPEG", quality=current_quality, optimize=True)
            compressed_size_kb = compressed_file_path.stat().st_size / 1024
            logger.debug(f"Saved {compressed_file_path} at {compressed_size_kb:.2f}KB (target: {max_size_kb}KB)")

            if compressed_size_kb <= max_size_kb:
                logger.info(f"Successfully compressed '{original_file_name}' to {compressed_size_kb:.2f}KB at '{compressed_file_path}'.")
                return str(compressed_file_path)

            # Reduce quality first
            if current_quality > 10:
                current_quality -= 15 # More aggressive quality reduction
                current_quality = max(10, current_quality) # Don't go below 10'
            # If quality is already low, start resizing
            elif attempt < max_attempts - 1 : # Avoid resizing on the very last attempt if quality reduction alone failed
                new_width = int(current_width * (1 - resize_step / 100))
                new_height = int(current_height * (1 - resize_step / 100))
                if new_width < 50 or new_height < 50 : # Don't make it too tiny'
                    logger.warning(f"Image dimensions for {original_file_name} too small to reduce further. Current: {current_width}x{current_height}")
                    break # Stop trying if it gets too small
                current_width, current_height = new_width, new_height
                # The actual resize will happen at the start of the next loop or before final save
                logger.info(f"Dimensions reduced to {current_width}x{current_height} for next attempt on {original_file_name}.")
        
        logger.warning(f"Could not compress '{original_image_path}' under {max_size_kb}KB after {max_attempts} attempts. Current size: {compressed_size_kb:.2f}KB. Returning path to last attempt: '{compressed_file_path}'")
        return str(compressed_file_path) # Return the last compressed version even if over budget

    except FileNotFoundError: # Should be caught by initial check, but as a safeguard
        raise
    except Exception as e:
        logger.exception(f"Error compressing image '{original_image_path}': {e}")
        return image_path_str # Fallback to original path on error


def convert_image_to_base64(image_path_str: str) -> Optional[str]: # Return Optional[str]
    """
    Converts an image file to a Base64-encoded data URI string.
    Returns None on failure.
    """
    image_path = Path(image_path_str)
    logger.debug(f"Attempting to convert '{image_path}' to Base64.")
    try:
        if not image_path.is_file():
            logger.error(f"Base64 conversion error: File does not exist or is not a file: '{image_path}'")
            return None

        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type or not mime_type.startswith("image/"):
            logger.warning(f"Could not determine MIME type for '{image_path}' via mimetypes. Trying with PIL.")
            try:
                with Image.open(image_path) as img:
                    img_format = img.format
                    if img_format:
                        mime_type = Image.MIME.get(img_format.upper())
                    if not mime_type or not mime_type.startswith("image/"):
                        logger.error(f"File '{image_path}' is not a recognized image type (PIL check also failed).")
                        return None
                    logger.info(f"Determined MIME type with PIL: {mime_type} for '{image_path}'")
            except Exception as pil_e:
                logger.error(f"PIL could not open or identify image type for '{image_path}': {pil_e}")
                raise
        
        with image_path.open("rb") as image_file:
            encoded_bytes = base64.b64encode(image_file.read())
            base64_encoded_str = encoded_bytes.decode("utf-8")
        
        data_uri = f"data:{mime_type};base64,{base64_encoded_str}"
        logger.info(f"Successfully converted '{image_path}' to Base64 Data URI (length: {len(data_uri)}).")
        return data_uri
    except Exception as e:
        logger.exception(f"Failed to convert image '{image_path}' to Base64: {e}")
        raise

def decode_base64_image(base64_image_str: str, image_directory_str: str, max_size_kb: int) -> Optional[str]:
    """
    Decodes a Base64 image, compresses if needed, and returns Base64 of the processed image.
    Returns None on critical failure.
    """
    # ... (implementation remains similar but ensure it calls the refined compress_image and convert_image_to_base64)
    # This function primarily deals with images that are *already* Base64 but might need compression.
    # For this PoC, if an image is already Base64 in the input, we might just pass it through or do a simple size check.
    # The main path for local files is local_file -> compress_image -> convert_image_to_base64.
    logger.debug("Decoding Base64 image for potential re-compression.")
    try:
        header, base64_data = base64_image_str.split(",", 1)
        mime_type = header.split(":")[1].split(";")[0]
        image_data = base64.b64decode(base64_data)
        
        # Check size before saving and re-processing (approximate)
        # len(image_data) is bytes. max_size_kb * 1024 is target bytes.
        if len(image_data) <= max_size_kb * 1024:
            logger.info(f"Input Base64 image is already within size limit ({len(image_data)/1024:.2f}KB). Passing through.")
            return base64_image_str

        image_output_dir = Path(image_directory_str)
        image_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Use a unique temp name
        temp_file_name = f"temp_b64_decoded_{hashlib.md5(image_data).hexdigest()}.{mime_type.split('/')[-1]}"
        temp_image_path = image_output_dir / temp_file_name

        with open(temp_image_path, "wb") as f:
            f.write(image_data)
        logger.debug(f"Temporarily saved decoded Base64 image to {temp_image_path}")

        compressed_image_file_path = compress_image(str(temp_image_path), image_directory_str, max_size_kb)
        
        final_base64 = convert_image_to_base64(compressed_image_file_path)
        
        try:
            os.remove(temp_image_path)
            if Path(compressed_image_file_path).exists() and compressed_image_file_path != str(temp_image_path):
                os.remove(compressed_image_file_path)
        except OSError as e_remove:
            logger.warning(f"Could not remove temporary image files: {e_remove}")
            
        return final_base64
    except Exception as e:
        logger.error(f"Error decoding/compressing Base64 image: {e}")
        return None # Signal failure


def process_image_input(image_input_url_or_path: str, image_cache_and_output_dir: str, max_size_kb: int = 500) -> Optional[Dict[str, Any]]:
    """
    Processes an image input (URL, Base64 string, or local file path).
    Local files are compressed and converted to Base64 Data URI.
    HTTP(S) URLs are passed through.
    Base64 inputs are decoded, potentially compressed, and re-encoded.
    Returns None if processing fails to produce a usable image_url structure.
    """
    logger.debug(f"Processing image input: '{image_input_url_or_path[:100]}...'")
    
    if image_input_url_or_path.startswith("http://") or image_input_url_or_path.startswith("https://"):
        logger.info(f"Passing through HTTP(S) URL: {image_input_url_or_path}")
        # For PoC, we pass URL directly. In production, consider downloading, caching, and then processing.
        # Or, if LiteLLM handles remote URLs directly for the target model, this is fine.
        # For OpenAI, remote URLs are generally supported.
        # cached_path = download_and_cache_image(image_input_url_or_path, image_cache_and_output_dir)
        # base64_image = convert_image_to_base64(cached_path)
        # if not base64_image: return None
        # return {"type": "image_url", "image_url": {"url": base64_image}}
        return {"type": "image_url", "image_url": {"url": image_input_url_or_path}}


    elif image_input_url_or_path.startswith("data:image"):
        logger.info("Processing Base64 data URI.")
        base64_output = decode_base64_image(image_input_url_or_path, image_cache_and_output_dir, max_size_kb)
        if base64_output:
            return {"type": "image_url", "image_url": {"url": base64_output}}
        else:
            logger.error("Failed to process existing Base64 image data.")
            return None
    else:  # Assume local file path
        logger.info(f"Processing local file path: {image_input_url_or_path}")
        try:
            # For local files, always compress then convert to base64
            compressed_image_file_path = compress_image(image_input_url_or_path, image_cache_and_output_dir, max_size_kb)
            base64_image_data_uri = convert_image_to_base64(compressed_image_file_path)
            
            if base64_image_data_uri:
                return {"type": "image_url", "image_url": {"url": base64_image_data_uri}}
            else:
                logger.error(f"Failed to convert local image to Base64: {compressed_image_file_path}")
                return None
        except FileNotFoundError:
            logger.error(f"Local image file not found: {image_input_url_or_path}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error processing local image '{image_input_url_or_path}': {e}")
            raise


def format_image_for_api(image_data: Dict[str, Any], api_type: str = "openai") -> Dict[str, Any]:
    """
    Format image data for specific API type.
    
    Args:
        image_data: Dict with "type": "image_url" and "image_url": {"url": "..."}
        api_type: API type (openai, anthropic, litellm)
        
    Returns:
        Formatted image object for the specific API
    """
    if not image_data or "image_url" not in image_data:
        return image_data
    
    url = image_data["image_url"]["url"]
    
    if api_type == "openai":
        # OpenAI format (default)
        return image_data
    
    elif api_type == "anthropic":
        # Anthropic expects different format
        if url.startswith("data:"):
            # Extract base64 data from data URI
            header, data = url.split(',', 1)
            mime_type = header.split(':')[1].split(';')[0]
            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime_type,
                    "data": data
                }
            }
        else:
            # For URLs, Anthropic might need different handling
            logger.warning(f"URL images for Anthropic API may need special handling: {url[:50]}...")
            return image_data
    
    elif api_type == "litellm":
        # LiteLLM standardized format
        if "format" not in image_data["image_url"] and url.startswith("data:"):
            # Extract MIME type from data URI
            header = url.split(',')[0]
            mime_type = header.split(':')[1].split(';')[0]
            image_data["image_url"]["format"] = mime_type
        return image_data
    
    else:
        logger.warning(f"Unknown API type: {api_type}. Returning original format.")
        return image_data


def encode_image_with_metadata(image_path: Union[str, Path], encoding: str = "base64") -> Dict[str, Any]:
    """
    Encode image with detailed metadata (format, size, dimensions, encoding time).
    Enhanced version with performance tracking from POC 11.
    
    Args:
        image_path: Path to image file
        encoding: Either "base64" or "url"
        
    Returns:
        Dict with encoded image data and metadata
    """
    start_time = time.time()
    image_path = Path(image_path)
    
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    # Check file size
    file_size = image_path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        raise ValueError(f"Image too large: {file_size} bytes (max: {MAX_FILE_SIZE})")
    
    # Detect format
    img_format = detect_image_format(image_path)
    if img_format not in SUPPORTED_FORMATS and img_format != "unknown":
        logger.warning(f"Unsupported format detected: {img_format}")
    
    # Get image dimensions
    with Image.open(image_path) as img:
        dimensions = img.size
        if dimensions[0] > MAX_RESOLUTION[0] or dimensions[1] > MAX_RESOLUTION[1]:
            logger.warning(f"Image exceeds max resolution: {dimensions} > {MAX_RESOLUTION}")
    
    result = {
        "format": img_format.upper(),
        "mime_type": SUPPORTED_FORMATS.get(img_format, f"image/{img_format}"),
        "size_bytes": file_size,
        "dimensions": dimensions
    }
    
    if encoding == "base64":
        # Use existing function for consistency
        data_uri = convert_image_to_base64(str(image_path))
        if data_uri:
            result["encoded"] = data_uri
            result["encoding"] = "base64"
        else:
            raise ValueError("Failed to encode image to base64")
    elif encoding == "url":
        # For local files, convert to file:// URL
        result["encoded"] = image_path.absolute().as_uri()
        result["encoding"] = "url"
    else:
        raise ValueError(f"Unsupported encoding: {encoding}")
    
    result["encoding_time_ms"] = (time.time() - start_time) * 1000
    return result