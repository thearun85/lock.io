"""Distributed Lock Service"""

import uuid
import time
from datetime import datetime, timezone

class DistributedLockService:

    def __init__(self):
        """Initialize the lock service"""
        self.__sessions: dict[str, dict] = {}
        self.__locks: dict[str, dict] = {}


    def _is_expired(self, session) -> bool:
        """Check whether the session is expired"""
        timesince_keepalive = time.time() - session['last_keepalive']
        return timesince_keepalive > session['timeout']
    
    def create_session(self, client_id: str, timeout: int = 60):
        """Create a client session"""
        session_id = str(uuid.uuid4())

        self.__sessions[session_id] = {
            "session_id": session_id,
            "client_id": client_id,
            "timeout": timeout,
            "created_at": time.time(),
            "last_keepalive": time.time(),
            "locks_held": [], # Resources locked by this session
        }

        return session_id

    def get_session_info(self, session_id: str) -> dict | None:
        """Get session details as dict filter by session ID"""
        if session_id not in self.__sessions:
            print(f"[LockService] fetch session failed: session {session_id} not found")
            return None

        session = self.__sessions[session_id].copy()
        session['is_expired'] = self._is_expired(self.__sessions[session_id])
        print(f"[LockService] fetch session {session_id}")
        return session

    def update_keepalive(self, session_id: str) -> bool:
        """Update keepalive timestamp for a session"""
        if session_id not in self.__sessions:
            print(f"[LockService] keepalive failed: session {session_id} not found")
            return False

        
        if self._is_expired(self.__sessions[session_id]):
            print(f"[LockService] keepalive failed: session {session_id} expired")
            return False

        self.__sessions[session_id]['last_keepalive'] = time.time()
        print(f"[LockService] keepalive success: session {session_id}")
        return True

    def delete_session(self, session_id: str) -> bool:
        """Delete a client session"""
        
        if session_id not in self.__sessions:
            print(f"[LockService] delete session failed: session {session_id} not found")
            return False

        del self.__sessions[session_id]
        print(f"[LockService] session {session_id} deleted")
        return True

    def get_service_stats(self) -> dict:
        """Get the lock service statistics"""
        total_sessions = len(self.__sessions)
        active_sessions = sum(1 for session in self.__sessions.values() if not self._is_expired(session))
        expired_sessions = sum(1 for session in self.__sessions.values() if self._is_expired(session))
        timestamp = datetime.now(timezone.utc).isoformat()

        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "expired_sessions": expired_sessions,
            "timestamp" : timestamp,
        }
