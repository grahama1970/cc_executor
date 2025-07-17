"""
Module: file_utils.py
Description: Utility functions and helpers for file utils

External Dependencies:
- loguru: [Documentation URL]
- dotenv: [Documentation URL]

Sample Input:
>>> # Add specific examples based on module functionality

Expected Output:
>>> # Add expected output examples

Example Usage:
>>> # Add usage examples
"""

import os
from loguru import logger
from pathlib import Path
from dotenv import load_dotenv
from typing import Union, Optional  


def load_text_file(file_path: Union[Path, str]) -> str:
    """
    Loads the content of a text file (e.g., AQL query) from the given path.

    Args:
        file_path (Union[Path, str]): Relative or absolute path to the text file as a Path object or string.

    Returns:
        str: Content of the text file as a string.

    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If there is an issue reading the file.
    """
    logger.debug(f"Attempting to load text file: {file_path}")

    # Convert string path to Path object if needed
    file_path = file_path if isinstance(file_path, Path) else Path(file_path)

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
            logger.success(f"Successfully loaded file: {file_path} (size: {len(content)} bytes)")
            return content
    except FileNotFoundError as e:
        logger.error(f"File not found: {file_path}")
        raise FileNotFoundError(f"File not found: {file_path}") from e
    except IOError as e:
        logger.error(f"IOError while reading file {file_path}: {str(e)}")
        raise IOError(f"Error reading file {file_path}: {str(e)}") from e
    except Exception as e:
        logger.critical(f"Unexpected error loading file {file_path}: {str(e)}")
        raise


def get_project_root(marker_file: str = ".git") -> Path:
    """
    Find the project root directory by looking for a marker file.

    Args:
        marker_file (str): File/directory to look for (default: ".git")

    Returns:
        Path: Project root directory path

    Raises:
        RuntimeError: If marker file not found in parent directories
    """
    current_dir = Path(__file__).resolve().parent
    while current_dir != current_dir.root:
        if (current_dir / marker_file).exists():
            return current_dir
        current_dir = current_dir.parent
    raise RuntimeError(f"Could not find project root. Ensure {marker_file} exists.")


def load_env_file(env_name: Optional[str] = None) -> None:
    """
    Load environment variables from a .env file.

    Args:
        env_name (str, optional): Environment name suffix to look for.
            If provided, looks for .env.{env_name}. Otherwise looks for .env

    Raises:
        FileNotFoundError: If .env file not found in expected locations
    """
    project_dir = get_project_root()
    env_dirs = [project_dir, project_dir / "app/backend"]

    for env_dir in env_dirs:
        env_file = env_dir / (f".env.{env_name}" if env_name else ".env")
        if env_file.exists():
            load_dotenv(env_file)
            # logger.success(f"Loaded environment file: {env_file}")
            # NOTE: how can I suppress the print statement?
            return

    raise FileNotFoundError(
        f"Environment file {'.env.' + env_name if env_name else '.env'} "
        f"not found in any known locations."
    )


if __name__ == "__main__":
    load_env_file()
    print(os.getenv("OPENAI_API_KEY"))
