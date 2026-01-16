from typing import Optional
import uuid
import logging
from .state import LockServiceState
from .models import Session, Lock

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

class LockService:
    """Core lock service implementation"""
    def __init__(self):
        self.state = LockServiceState()

    def create_session(self, client_id:str, timeout:int)->str:
        """Create a new session for a client"""
        session_id = str(uuid.uuid4())

        with self.state._lock:
            session = Session(
                session_id=session_id,
                client_id=client_id,
                timeout=timeout,
            )
            self.state.sessions[session_id] = session
        logger.info(f"Created session {session_id} for client {client_id}")
        return session_id

    def get_session(self, session_id:str)->Optional[Session]:
        """Get session by ID"""
        return self.state.sessions.get(session_id)

    def keepalive(self, session_id:str)->bool:
        """Update session keepalive"""
        with self.state._lock:
            session = self.state.sessions.get(session_id)
            if not session:
                logger.warning(f"Keepalive failed: session {session_id} not found")
                return False
                
            if session.is_expired():
                logger.warning(f"Keepalive failed: session {session_id} expired")
                return False
                
            session.update_keepalive()
            logger.debug(f"Keepalive updated for session {session_id}")
            return True

    def acquire_lock(self, session_id:str, resource:str)->Optional[int]:
        """Acquire a lock for a resource"""
        with self.state._lock:
            session = self.state.sessions.get(session_id)
            if not session:
                logger.warning(f"Lock acquisition failed: invalid session {session_id}")
                return None
            if session.is_expired():
                logger.warning(f"Lock acquisition failed: session {session_id} expired")
                return None

            existing_lock = self.state.locks.get(resource)
            if existing_lock:
                logger.warning(f"Resource {resource} already locked")
                return None
            fence_token = self.state.next_fence_token()
            lock = Lock(
                resource = resource,
                session_id = session_id,
                fence_token = fence_token,
            )
            self.state.locks[resource] = lock
            session.locks_held.add(resource)
            logger.info(f"Session {session_id} acquired lock on resource {resource} with fence_token {fence_token}")
            return fence_token

    def release_lock(self, session_id:str, resource:str, fence_token:int)->bool:
        """Release a lock"""
        with self.state._lock:
            lock = self.state.locks.get(resource)
            
            if not lock:
                logger.warning(f"Lock release failed: lock on resource {resource} doesn't exist")
                return False
                
            if lock.session_id != session_id:
                logger.warning(f"Lock release failed: session {session_id} doesn't own lock on resource {resource}")
                return False

            if lock.fence_token != fence_token:
                logger.warning(f"Lock release failed: fence token mismatch for resource {resource}")
                return False
            del self.state.locks[resource]
            session = self.state.sessions.get(session_id)
            if session:
                session.locks_held.discard(resource)
            logger.info(f"Lock release on resource {resource}")
            
            return True

    def cleanup_expired_sessions(self)->int:
        """Remove expired sessions and release their locks"""
        with self.state._lock:
            expired_sessions = []
            # Find expired sessions
            for session_id, session in self.state.sessions.items():
                if session.is_expired():
                    expired_sessions.append(session_id)

            # Cleanup each expired session
            cleaned = 0
            for session_id in expired_sessions:
                session = self.state.sessions.get(session_id)
                for resource in list(session.locks_held):
                    if resource in self.state.locks:
                        del self.state.locks[resource]
                        logger.info(f"Released lock on resource {resource} due to session expiry")
                del self.state.sessions[session_id]
                logger.info(f"Clean up expired session {session_id}")
                cleaned+=1

            return cleaned
            
            
            
