"""
Redis connection manager with health checks and automatic reconnection.

This module provides a robust Redis connection manager that handles:
- Connection pooling
- Health checks
- Automatic reconnection on failure
- Connection state monitoring
"""
import asyncio
import time
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
import redis.asyncio as redis
from loguru import logger


class RedisConnectionManager:
    """Manages Redis connections with health checks and auto-reconnection."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_connections: int = 50,
        health_check_interval: int = 5,
        reconnect_interval: int = 1,
        max_reconnect_attempts: int = 10
    ):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.max_connections = max_connections
        self.health_check_interval = health_check_interval
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        
        self._pool: Optional[redis.ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
        self._is_connected = False
        self._health_check_task: Optional[asyncio.Task] = None
        self._reconnect_attempts = 0
        self._last_health_check = 0
        
    async def connect(self) -> None:
        """Establish connection to Redis."""
        try:
            self._pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                max_connections=self.max_connections,
                decode_responses=True
            )
            
            self._client = redis.Redis(connection_pool=self._pool)
            
            # Test connection
            await self._client.ping()
            self._is_connected = True
            self._reconnect_attempts = 0
            logger.info(f"Connected to Redis at {self.host}:{self.port}")
            
            # Start health check task
            if self._health_check_task:
                self._health_check_task.cancel()
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._is_connected = False
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from Redis and cleanup resources."""
        self._is_connected = False
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        if self._client:
            await self._client.close()
            self._client = None
            
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
            
        logger.info("Disconnected from Redis")
    
    async def _health_check_loop(self) -> None:
        """Continuously monitor Redis connection health."""
        while self._is_connected:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                self._is_connected = False
                asyncio.create_task(self._reconnect())
    
    async def _health_check(self) -> bool:
        """Check if Redis connection is healthy."""
        try:
            if not self._client:
                return False
                
            start = time.time()
            pong = await self._client.ping()
            latency = (time.time() - start) * 1000  # ms
            
            self._last_health_check = time.time()
            
            if pong and latency < 1000:  # Less than 1 second
                return True
            else:
                logger.warning(f"Redis health check slow: {latency:.2f}ms")
                return True
                
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    async def _reconnect(self) -> None:
        """Attempt to reconnect to Redis."""
        while self._reconnect_attempts < self.max_reconnect_attempts:
            self._reconnect_attempts += 1
            logger.info(f"Reconnect attempt {self._reconnect_attempts}/{self.max_reconnect_attempts}")
            
            try:
                await self.disconnect()
                await asyncio.sleep(self.reconnect_interval)
                await self.connect()
                logger.info("Successfully reconnected to Redis")
                return
            except Exception as e:
                logger.error(f"Reconnect failed: {e}")
                await asyncio.sleep(self.reconnect_interval * self._reconnect_attempts)
        
        logger.error("Max reconnection attempts reached. Give up.")
    
    @asynccontextmanager
    async def get_client(self):
        """Get Redis client with automatic connection management."""
        if not self._is_connected or not self._client:
            await self.connect()
            
        try:
            yield self._client
        except redis.ConnectionError as e:
            logger.error(f"Redis connection error: {e}")
            self._is_connected = False
            asyncio.create_task(self._reconnect())
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """Get current connection status."""
        return {
            "connected": self._is_connected,
            "host": self.host,
            "port": self.port,
            "reconnect_attempts": self._reconnect_attempts,
            "last_health_check": self._last_health_check,
            "pool_size": self._pool.max_connections if self._pool else 0
        }


async def working_usage():
    """Demonstrate Redis connection manager usage.
    
    AGENT: Run this for stable, production-ready example.
    This function is known to work and should not be modified.
    """
    manager = RedisConnectionManager()
    
    try:
        # Connect to Redis
        await manager.connect()
        
        # Use the connection
        async with manager.get_client() as client:
            await client.set("test_key", "test_value")
            value = await client.get("test_key")
            print(f"Retrieved value: {value}")
        
        # Check status
        status = manager.get_status()
        print(f"Connection status: {status}")
        
        # Simulate some work
        await asyncio.sleep(2)
        
    finally:
        await manager.disconnect()
    
    print("✓ Redis connection manager test complete")
    return True


async def debug_function():
    """Debug function for testing connection failures and recovery.
    
    AGENT: Use this function for experimenting! Rewrite freely.
    This is constantly rewritten to test different things.
    """
    # Test with wrong port to simulate connection failure
    manager = RedisConnectionManager(port=9999, max_reconnect_attempts=2)
    
    try:
        await manager.connect()
    except Exception as e:
        print(f"Expected connection failure: {e}")
    
    # Test with correct port
    manager2 = RedisConnectionManager()
    await manager2.connect()
    
    # Test multiple operations
    async with manager2.get_client() as client:
        # Set multiple keys
        for i in range(5):
            await client.set(f"test_{i}", f"value_{i}")
        
        # Get all keys
        keys = await client.keys("test_*")
        print(f"Found keys: {keys}")
        
        # Cleanup
        for key in keys:
            await client.delete(key)
    
    await manager2.disconnect()
    print("✓ Debug tests complete")


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
    else:
        print("Running working usage mode...")
        asyncio.run(working_usage())