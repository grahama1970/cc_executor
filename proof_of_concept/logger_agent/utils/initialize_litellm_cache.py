"""
Module: initialize_litellm_cache.py
Description: Functions for initialize litellm cache operations

External Dependencies:
- litellm: [Documentation URL]
- redis: https://redis-py.readthedocs.io/
- loguru: [Documentation URL]
- dotenv: [Documentation URL]

Sample Input:
>>> # Add specific examples based on module functionality

Expected Output:
>>> # Add expected output examples

Example Usage:
>>> # Add usage examples
"""

import litellm
import os
import redis
from loguru import logger
import sys  # Needed for test function logger setup
from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()


def initialize_litellm_cache() -> None:
    """Initializes LiteLLM caching (Redis fallback to in-memory), ensuring 'embedding' is cached."""
    if "REDIS_PASSWORD" in os.environ:
        logger.debug(f"Found REDIS_PASSWORD: {os.environ['REDIS_PASSWORD']}")
        del os.environ["REDIS_PASSWORD"]
        logger.debug("Unset REDIS_PASSWORD from environment")
    
    # We are on Claude Max plan - no API key needed

    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    redis_password = os.getenv("REDIS_PASSWORD", None)

    
    logger.debug(
        f"Redis config: host={redis_host}, port={redis_port}, password={redis_password}"
    )

    try:
        logger.debug(
            f"Attempting Redis connection (Target: {redis_host}:{redis_port})..."
        )
        redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            password=None,
            socket_timeout=2,
            decode_responses=True,  # Keep for manual test
        )
        if not redis_client.ping():
            raise redis.ConnectionError("Ping failed")
        requirepass = redis_client.config_get("requirepass").get("requirepass", "")
        logger.debug(f"Redis requirepass: '{requirepass}'")
        if requirepass:
            logger.warning(
                "Redis has a password set, but none provided. Update configuration."
            )
            raise redis.AuthenticationError("Password required by Redis server")

        logger.debug("Manual Redis connection successful.")

        logger.debug("Configuring LiteLLM Redis cache...")
        litellm.cache = litellm.Cache(
            type="redis",
            host=redis_host,
            port=redis_port,
            password=None,
            # Remove decode_responses to avoid string decoding issue
            supported_call_types=["acompletion", "completion", "embedding"],
            ttl=(60 * 60 * 24 * 2),
        )
        litellm.enable_cache()
        logger.info(
            f" LiteLLM Caching enabled using Redis at {redis_host}:{redis_port}"
        )

    except (redis.ConnectionError, redis.TimeoutError, redis.AuthenticationError) as e:
        logger.warning(
            f"⚠️ Redis connection/setup failed: {e}. Falling back to in-memory caching."
        )
        logger.debug("Configuring LiteLLM in-memory cache...")
        litellm.cache = litellm.Cache(
            type="local",
            supported_call_types=["acompletion", "completion", "embedding"],
            ttl=(60 * 60 * 1),
        )
        litellm.enable_cache()
        logger.info(" LiteLLM Caching enabled using in-memory (local) cache.")
    except Exception as e:
        logger.exception(f"Unexpected error during LiteLLM cache initialization: {e}")
# --- Test Function (Kept for standalone testing) ---
def test_litellm_cache():
    """Test the LiteLLM cache functionality with a sample completion call"""
    initialize_litellm_cache()

    try:
        # Test the cache with a simple completion call
        test_messages = [
            {"role": "user", "content": "What is the capital of France?"}
        ]  # Make sure it's >1024 tokens'
        logger.info("Testing cache with completion call...")

        # First call should miss cache
        response1 = litellm.completion(
            model="gpt-4o-mini",
            messages=test_messages,
            cache={"no-cache": False},
        )
        logger.info(f"First call usage: {response1.usage}")
        if m := response1._hidden_params.get("cache_hit"):
            logger.info(f"Response 1: Cache hit: {m}")

        # Second call should hit cache
        response2 = litellm.completion(
            model="gpt-4o-mini",
            messages=test_messages,
            cache={"no-cache": False},
        )
        logger.info(f"Second call usage: {response2.usage}")
        if m := response2._hidden_params.get("cache_hit"):
            logger.info(f"Response 2: Cache hit: {m}")

    except Exception as e:
        logger.error(f"Cache test failed with error: {e}")
        raise

if __name__ == "__main__":
    # Allows running this script directly to test caching setup
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")
    # Set dummy key if needed for test provider
    os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "sk-dummy")
    test_litellm_cache()
