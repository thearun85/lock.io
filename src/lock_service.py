from .state import LockServiceState
from .models import Session, Lock
import uuid
import logging
from typing import Optional
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

class LockService:
    def __init__(self):
        self.state = LockServiceState()

    def create_session(self, client_id:str, timeout:int)->str:
        """Create a client session"""
        with self.state._lock:
            session_id = str(uuid.uuid4())
            session = Session(
                session_id = session_id,
                client_id = client_id,
                timeout = timeout
            )
            self.state.sessions[session_id] = session

            logger.info(f"Session {session_id} created for client {client_id}")
            return session_id

    def _get_session(self, session_id: str)->Optional[Session]:
        """Get session by ID"""
        return self.state.sessions.get(session_id, None)

    def delete_session(self, session_id:str)->bool:
        """Delete a session and release all locks held"""
        with self.state._lock:
            session = self._get_session(session_id)
            if session is None:
                logger.warning(f"Delete session failed: Session {session_id} not found")
                return False
            if session.is_expired():
                logger.warning(f"Delete session failed: Session {session_id} expired")
                return False

            for resource in list(session.locks_held):
                if resource in self.state.locks:
                    del self.state.locks[resource]
                
                session.locks_held.discard(resource)
                logger.info(f"Delete session: Resource {resource} deleted")
                
            del self.state.sessions[session_id]
            return True

    def get_session_info(self, session_id:str)->Optional[dict]:
        """Get session details as dict"""
        session = self._get_session(session_id)
        if session is None:
            return None
        return {
            "session_id": session.session_id,
            "client_id": session.client_id,
            "timeout": session.timeout,
            "created_at": session.created_at,
            "last_keepalive": session.last_keepalive,
            "locks_held": list(session.locks_held),
            "expired": session.is_expired(),
        }

    def keepalive(self, session_id:str)->bool:
        """Extend session lifetime"""
        with self.state._lock:
            session = self._get_session(session_id)
            if session is None:
                logger.warning(f"Keepalive failed: Invalid session {session_id}")
                return False
            if session.is_expired():
                logger.warning(f"Keepalive failed: Session {session_id} expired")
            session.update_keepalive()
            return True

    def acquire_lock(self, session_id:str, resource: str)->Optional[int]:
        """Acquire lock on a resource"""
        with self.state._lock:
            session = self._get_session(session_id)
            if session is None:
                logger.warning(f"Acquire lock failed: Session {session_id} not found")
                return None
            if session.is_expired():
                logger.warning(f"Acquire lock failed: Session {session_id} expired")
                return None

            existing_lock = self.state.locks.get(resource)
            if existing_lock:
                if existing_lock.session_id != session_id:
                    logger.warning(f"Acquire lock failed: Resource {resource} already locked by another session")
                    return None
                else:
                    logger.warning(f"Acquire lock success: Resource {resource} is already locked by this session")
                    return existing_lock.fence_token

            fence_token = self.state.next_fence_token()
            lock = Lock(
                resource = resource,
                session_id = session_id,
                fence_token = fence_token
            )
            self.state.locks[resource] = lock
            session.locks_held.add(resource)

            return fence_token

    def release_lock(self, session_id: str, resource: str, fence_token: int)->bool:
        """Release a lock on the resource"""
        with self.state._lock:
            existing_lock = self.state.locks.get(resource, None)
            if not existing_lock:
                logger.warning(f"Release lock failed: Resource {resource} is not locked")
                return False

            if existing_lock.session_id !=  session_id:
                logger.warning(f"Release lock failed: Session {session_id} doesn't own lock on resource {resource}")
                return False

            if existing_lock.fence_token != fence_token:
                logger.warning(f"Release lock failed: Fence token mismatch {fence_token} for resource {resource}")
                return False

            del self.state.locks[resource]

            session = self._get_session(session_id)
            if session:
                session.locks_held.discard(resource)

            logger.info("Lock released on resource {resource}")
            return True

    def get_lock_info(self, resource:str)->Optional[dict]:
        """Get lock information as a dict"""
        existing_lock = self.state.locks.get(resource)
        if not existing_lock:
            return None
        return {
            "resource": existing_lock.resource,
            "session_id": existing_lock.session_id,
            "acquired_at": existing_lock.acquired_at,
            "fence_token": existing_lock.fence_token,
        }

    def get_stats(self)->dict:
        """Collect information across container state"""
        with self.state._lock:
            
            return {
                "total_sessions": len(self.state.sessions),
                "total_locks": len(self.state.locks),
                "fence_counter": self.state.fence_counter,
                "active_sessions": sum( 1 for s in self.state.sessions.values() if not s.is_expired()),
                "expired_sessions": sum( 1 for s in self.state.sessions.values() if s.is_expired()),
            }
    def cleanup_expired_sessions(self)->int:
        """Cleanup expired sessions and release all its locks"""

        with self.state._lock:
            expired_sessions = []
            for session_id, session in self.state.sessions.items():
                if session.is_expired():
                    expired_sessions.append(session_id)


            cleaned_locks = 0
            cleaned_sessions = 0
            for session_id in expired_sessions:
                session = self._get_session(session_id)
                for resource in list(session.locks_held):
                    if resource in self.state.locks:
                        del self.state.locks[resource]
                        cleaned_locks+=1

                logger.info(f"Session {session_id} deleted")
                del self.state.sessions[session_id]
                logger.info(f"Session {session_id} deleted")
            cleaned_sessions+=1
            logger.info(f"Cleanup: total sessions {cleaned_sessions} and total locks {cleaned_locks}")
        return cleaned_sessions
