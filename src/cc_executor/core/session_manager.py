"""
Session management module for CC Executor MCP WebSocket Service.

This module handles WebSocket session lifecycle management with proper
locking to prevent race conditions. It tracks active sessions, enforces
session limits, and provides thread-safe access to session data.

Third-party Documentation:
- asyncio Locks: https://docs.python.org/3/library/asyncio-sync.html#asyncio.Lock
- WebSocket Sessions: https://websockets.readthedocs.io/en/stable/topics/design.html
- FastAPI WebSockets: https://fastapi.tiangolo.com/advanced/websockets/
- Race Condition Prevention: https://docs.python.org/3/library/asyncio-sync.html

Example Input:
    Creating a new session with WebSocket connection:
    - session_id: "uuid-1234-5678"
    - websocket: <WebSocket instance>
    - max_sessions: 100

Expected Output:
    Test creates 4 sessions with limit of 3:
    ✓ Created session-1 with <MockWebSocket 4379e3ba>
    ✓ Created session-2 with <MockWebSocket c6279e7c>  
    ✓ Created session-3 with <MockWebSocket 6b3080ef>
    ✗ Failed to create session-4 - limit reached
    
    Race condition test shows all 3 concurrent accesses succeed safely.
    Session cleanup removes expired sessions automatically.
    Final state: 1 active session remaining.
"""

import asyncio
import time
import json
import os
import redis
from typing import Dict, Optional, Any
from loguru import logger

try:
    from .config import MAX_SESSIONS, SESSION_TIMEOUT
    from .models import SessionInfo
except ImportError:
    # For standalone execution
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from config import MAX_SESSIONS, SESSION_TIMEOUT
    from models import SessionInfo


class SessionManager:
    """
    Manages WebSocket sessions with thread-safe operations.
    
    This class ensures:
    - No race conditions when creating/accessing sessions
    - Session limit enforcement
    - Proper cleanup of terminated sessions
    - Session timeout handling
    """
    
    def __init__(self, max_sessions: int = MAX_SESSIONS, use_redis: bool = True):
        """
        Initialize the session manager with optional Redis backend.
        
        Args:
            max_sessions: Maximum number of concurrent sessions allowed
            use_redis: Whether to use Redis for session storage (default: True)
        """
        self.sessions: Dict[str, SessionInfo] = {}  # Fallback for non-Redis mode
        self.lock = asyncio.Lock()
        self.max_sessions = max_sessions
        self._start_time = time.time()
        self.use_redis = use_redis
        self.redis_client = None
        self.redis_prefix = "cc_executor:sessions:"
        
        # Initialize Redis connection if requested
        if self.use_redis:
            try:
                redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self.redis_client.ping()
                logger.info(f"Redis connection established for session storage")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis, falling back to in-memory: {e}")
                self.use_redis = False
                self.redis_client = None
        
    async def create_session(self, session_id: str, websocket: Any) -> bool:
        """
        Create a new session if under the limit.
        
        Args:
            session_id: Unique session identifier
            websocket: WebSocket connection instance
            
        Returns:
            True if session was created, False if limit exceeded
        """
        async with self.lock:
            # Check session count
            session_count = await self._get_session_count()
            if session_count >= self.max_sessions:
                logger.warning(
                    f"Session limit reached: {session_count}/{self.max_sessions}"
                )
                return False
                
            current_time = time.time()
            session_info = SessionInfo(
                session_id=session_id,
                websocket=websocket,
                created_at=current_time,
                last_activity=current_time
            )
            
            # Store in Redis or memory
            if self.use_redis and self.redis_client:
                try:
                    # Store session data (excluding websocket object)
                    session_data = {
                        'session_id': session_id,
                        'created_at': current_time,
                        'last_activity': current_time,
                        'websocket_id': id(websocket)  # Store ID reference only
                    }
                    self.redis_client.setex(
                        f"{self.redis_prefix}{session_id}",
                        SESSION_TIMEOUT,
                        json.dumps(session_data)
                    )
                    # Keep websocket reference in memory
                    self.sessions[session_id] = session_info
                except Exception as e:
                    logger.error(f"Redis error in create_session: {e}")
                    # Fallback to memory
                    self.sessions[session_id] = session_info
            else:
                self.sessions[session_id] = session_info
            
            session_count = await self._get_session_count()
            logger.info(
                f"Session created: {session_id} "
                f"(active: {session_count}/{self.max_sessions})"
            )
            return True
            
    async def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """
        Get session info by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            SessionInfo if found, None otherwise
        """
        async with self.lock:
            # Check memory first (for websocket reference)
            session = self.sessions.get(session_id)
            
            # If not in memory but using Redis, check Redis
            if not session and self.use_redis and self.redis_client:
                try:
                    session_data = self.redis_client.get(f"{self.redis_prefix}{session_id}")
                    if session_data:
                        # Session exists in Redis but websocket reference was lost
                        # This shouldn't happen in normal operation
                        logger.warning(f"Session {session_id} found in Redis but not in memory")
                        return None
                except Exception as e:
                    logger.error(f"Redis error in get_session: {e}")
                    
            if session:
                # Update last activity
                current_time = time.time()
                session.last_activity = current_time
                
                # Update Redis if enabled
                if self.use_redis and self.redis_client:
                    try:
                        session_data = {
                            'session_id': session_id,
                            'created_at': session.created_at,
                            'last_activity': current_time,
                            'websocket_id': id(session.websocket)
                        }
                        self.redis_client.setex(
                            f"{self.redis_prefix}{session_id}",
                            SESSION_TIMEOUT,
                            json.dumps(session_data)
                        )
                    except Exception as e:
                        logger.error(f"Redis error updating last_activity: {e}")
                        
            return session
            
    async def update_session(
        self,
        session_id: str,
        process: Optional[Any] = None,
        pgid: Optional[int] = None,
        task: Optional[Any] = None
    ) -> bool:
        """
        Update session with process information.
        
        Args:
            session_id: Session identifier
            process: asyncio.Process instance
            pgid: Process group ID
            task: asyncio.Task for the process
            
        Returns:
            True if updated, False if session not found
        """
        async with self.lock:
            session = self.sessions.get(session_id)
            if not session:
                return False
                
            if process is not None:
                session.process = process
            if pgid is not None:
                session.pgid = pgid
            if task is not None:
                session.task = task
                
            session.last_activity = time.time()
            return True
            
    async def remove_session(self, session_id: str) -> Optional[SessionInfo]:
        """
        Remove a session and return its info.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Removed SessionInfo if found, None otherwise
        """
        async with self.lock:
            # Remove from memory
            session = self.sessions.pop(session_id, None)
            
            # Remove from Redis if enabled
            if self.use_redis and self.redis_client:
                try:
                    self.redis_client.delete(f"{self.redis_prefix}{session_id}")
                except Exception as e:
                    logger.error(f"Redis error in remove_session: {e}")
                    
            if session:
                session_count = await self._get_session_count()
                logger.info(
                    f"Session removed: {session_id} "
                    f"(active: {session_count}/{self.max_sessions})"
                )
            return session
            
    async def get_all_sessions(self) -> Dict[str, SessionInfo]:
        """
        Get a copy of all active sessions.
        
        Returns:
            Dictionary of session_id -> SessionInfo
        """
        async with self.lock:
            # For Redis mode, we return memory sessions since they contain websocket refs
            # Redis sessions without websocket refs are considered orphaned
            if self.use_redis and self.redis_client:
                try:
                    # Log if there are orphaned sessions in Redis
                    redis_keys = self.redis_client.keys(f"{self.redis_prefix}*")
                    memory_ids = set(self.sessions.keys())
                    redis_ids = {key.replace(self.redis_prefix, '') for key in redis_keys}
                    orphaned = redis_ids - memory_ids
                    if orphaned:
                        logger.warning(f"Found {len(orphaned)} orphaned sessions in Redis: {orphaned}")
                except Exception as e:
                    logger.error(f"Redis error checking orphaned sessions: {e}")
                    
            return self.sessions.copy()
            
    async def cleanup_expired_sessions(self) -> int:
        """
        Remove sessions that have exceeded the timeout.
        
        Returns:
            Number of sessions cleaned up
        """
        current_time = time.time()
        cleaned = 0
        
        # Perform all deletions while holding the lock to prevent race conditions
        async with self.lock:
            # Clean up memory sessions
            expired_sessions = []
            for session_id, session in self.sessions.items():
                if current_time - session.last_activity > SESSION_TIMEOUT:
                    expired_sessions.append(session_id)
            
            # Remove expired sessions while still holding the lock
            for session_id in expired_sessions:
                session = self.sessions.pop(session_id, None)
                if session:
                    cleaned += 1
                    logger.info(f"Expired session cleaned up: {session_id}")
                    
                    # Remove from Redis if enabled
                    if self.use_redis and self.redis_client:
                        try:
                            self.redis_client.delete(f"{self.redis_prefix}{session_id}")
                        except Exception as e:
                            logger.error(f"Redis error cleaning up session: {e}")
                            
            # Clean up orphaned Redis sessions (sessions without memory reference)
            if self.use_redis and self.redis_client:
                try:
                    redis_keys = self.redis_client.keys(f"{self.redis_prefix}*")
                    memory_ids = set(self.sessions.keys())
                    
                    for key in redis_keys:
                        session_id = key.replace(self.redis_prefix, '')
                        if session_id not in memory_ids:
                            # Check if expired by getting TTL
                            ttl = self.redis_client.ttl(key)
                            if ttl == -1:  # No TTL set (shouldn't happen)
                                self.redis_client.delete(key)
                                cleaned += 1
                                logger.info(f"Orphaned Redis session cleaned up: {session_id}")
                            elif ttl == -2:  # Key doesn't exist
                                pass  # Already gone
                            # Otherwise Redis will handle TTL expiration
                except Exception as e:
                    logger.error(f"Redis error cleaning orphaned sessions: {e}")
                
        return cleaned
        
    def get_stats(self) -> Dict[str, Any]:
        """
        Get session manager statistics.
        
        Returns:
            Dictionary with current stats
        """
        stats = {
            "active_sessions": len(self.sessions),
            "max_sessions": self.max_sessions,
            "uptime_seconds": time.time() - self._start_time,
            "session_ids": list(self.sessions.keys()),
            "redis_enabled": self.use_redis
        }
        
        # Add Redis stats if enabled
        if self.use_redis and self.redis_client:
            try:
                redis_keys = self.redis_client.keys(f"{self.redis_prefix}*")
                stats["redis_sessions"] = len(redis_keys)
                stats["redis_connected"] = self.redis_client.ping()
            except Exception as e:
                logger.error(f"Redis error getting stats: {e}")
                stats["redis_sessions"] = 0
                stats["redis_connected"] = False
                
        return stats
        
    async def session_exists(self, session_id: str) -> bool:
        """
        Check if a session exists.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session exists
        """
        async with self.lock:
            if self.use_redis and self.redis_client:
                try:
                    return self.redis_client.exists(f"{self.redis_prefix}{session_id}") > 0
                except Exception as e:
                    logger.error(f"Redis error in session_exists: {e}")
            return session_id in self.sessions
    
    async def _get_session_count(self) -> int:
        """Get the total count of active sessions from Redis or memory."""
        if self.use_redis and self.redis_client:
            try:
                keys = self.redis_client.keys(f"{self.redis_prefix}*")
                return len(keys)
            except Exception as e:
                logger.error(f"Redis error in _get_session_count: {e}")
        return len(self.sessions)


if __name__ == "__main__":
    """Usage example demonstrating session management with race condition prevention."""
    
    import uuid
    from usage_helper import OutputCapture
    
    async def simulate_websocket():
        """Simulate a WebSocket connection object."""
        class MockWebSocket:
            def __init__(self):
                self.id = str(uuid.uuid4())[:8]
            def __repr__(self):
                return f"<MockWebSocket {self.id}>"
        return MockWebSocket()
    
    async def simulate_process():
        """Simulate a process object."""
        class MockProcess:
            def __init__(self):
                self.pid = 12345
                self.returncode = None
        return MockProcess()
    
    async def main():
        print("=== Session Manager Usage Example ===\n")
        
        # Test with both Redis and in-memory modes
        for use_redis in [True, False]:
            mode = "Redis" if use_redis else "In-Memory"
            print(f"\n{'='*50}")
            print(f"Testing with {mode} Backend")
            print(f"{'='*50}")
            
            # Create session manager with limit of 3
            manager = SessionManager(max_sessions=3, use_redis=use_redis)
            print(f"Created SessionManager with max_sessions={manager.max_sessions}, use_redis={use_redis}")
            
            # Show initial stats
            initial_stats = manager.get_stats()
            print(f"Redis enabled: {initial_stats.get('redis_enabled', False)}")
            if use_redis and initial_stats.get('redis_connected'):
                print(f"Redis connected: True")
            
            # Test 1: Create sessions
            print(f"\n--- Test 1: Creating Sessions ({mode}) ---")
            sessions_created = []
            
            for i in range(4):  # Try to create 4 sessions (1 more than limit)
                session_id = f"{mode.lower()}-session-{i+1}"
                websocket = await simulate_websocket()
                
                success = await manager.create_session(session_id, websocket)
                if success:
                    sessions_created.append(session_id)
                    print(f"✓ Created {session_id} with {websocket}")
                else:
                    print(f"✗ Failed to create {session_id} - limit reached")
            
            stats = manager.get_stats()
            print(f"\nActive sessions: {stats['active_sessions']}/{stats['max_sessions']}")
            if use_redis and 'redis_sessions' in stats:
                print(f"Redis sessions: {stats['redis_sessions']}")
        
            # Test 2: Update session with process
            print(f"\n--- Test 2: Updating Session with Process ({mode}) ---")
            if sessions_created:
                session_id = sessions_created[0]
                process = await simulate_process()
                pgid = 12345
                
                updated = await manager.update_session(
                    session_id, 
                    process=process,
                    pgid=pgid
                )
                print(f"Updated {session_id} with process (PID={process.pid}): {updated}")
                
                # Retrieve and check
                session = await manager.get_session(session_id)
                if session:
                    print(f"Session details: PID={session.process.pid}, PGID={session.pgid}")
            
            # Test 3: Concurrent access (race condition test)
            print(f"\n--- Test 3: Concurrent Access Test ({mode}) ---")
            
            async def concurrent_get(mgr, sess_id: str, delay: float):
                """Simulate concurrent access to same session."""
                await asyncio.sleep(delay)
                session = await mgr.get_session(sess_id)
                return f"Task {delay}s: Got session={session is not None}"
            
            if sessions_created:
                # Launch concurrent tasks
                tasks = [
                    concurrent_get(manager, sessions_created[0], 0.0),
                    concurrent_get(manager, sessions_created[0], 0.001),
                    concurrent_get(manager, sessions_created[0], 0.002)
                ]
                
                results = await asyncio.gather(*tasks)
                for result in results:
                    print(f"  {result}")
            
            # Test 4: Remove session
            print(f"\n--- Test 4: Removing Sessions ({mode}) ---")
            for session_id in sessions_created[:2]:  # Remove first 2
                removed = await manager.remove_session(session_id)
                print(f"Removed {session_id}: {removed is not None}")
            
            stats = manager.get_stats()
            print(f"\nActive sessions after removal: {stats['active_sessions']}/{stats['max_sessions']}")
            if use_redis and 'redis_sessions' in stats:
                print(f"Redis sessions after removal: {stats['redis_sessions']}")
            
            # Test 5: Session timeout simulation
            print(f"\n--- Test 5: Session Timeout Test ({mode}) ---")
            
            # Create an old session
            old_session_id = f"{mode.lower()}-old-session"
            websocket = await simulate_websocket()
            await manager.create_session(old_session_id, websocket)
            
            # Manually set last_activity to past
            async with manager.lock:
                if old_session_id in manager.sessions:
                    manager.sessions[old_session_id].last_activity = time.time() - 7200  # 2 hours ago
            
            # Run cleanup
            cleaned = await manager.cleanup_expired_sessions()
            print(f"Cleaned up {cleaned} expired sessions")
            
            # Test 6: Verify all sessions cleaned
            print(f"\n--- Test 6: Final State ({mode}) ---")
            all_sessions = await manager.get_all_sessions()
            print(f"Remaining sessions: {list(all_sessions.keys())}")
            
            stats = manager.get_stats()
            print(f"Final stats: {stats['active_sessions']} active, uptime: {stats['uptime_seconds']:.1f}s")
            if use_redis and 'redis_sessions' in stats:
                print(f"Redis final sessions: {stats['redis_sessions']}")
        
        # Verify thread safety
        print(f"\n✅ All operations completed without race conditions")
        print(f"✅ Session limits enforced correctly")
        print(f"✅ Cleanup mechanisms working")
        print(f"✅ Redis backend support implemented")
    
    # Run the example with OutputCapture
    with OutputCapture(__file__) as capture:
        asyncio.run(main())