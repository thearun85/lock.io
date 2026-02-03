"""Distributed Lock Service"""

import uuid
import time
from datetime import datetime, timezone
from src.core.errors import ErrorCode, ERROR_MESSAGES

# Helper functions
def ok(data=None):
    """Create success result"""
    return {"success": True, "data": data}

def fail(err_cd, **format_args):
    """Create error result"""
    err_msg = ERROR_MESSAGES[err_cd]
    err_msg = err_msg.format(**format_args)
    return {"success": False, "err_cd": err_cd, "err_msg": err_msg}

class DistributedLockService:

    def __init__(self):
        """Initialize the lock service"""
        self.__sessions: dict[str, dict] = {}
        self.__locks: dict[str, dict] = {}
        self.__fence_counter: int = 0 # to prevent stale sessions


    def _is_expired(self, session) -> bool:
        """Check whether the session is expired"""
        timesince_keepalive = time.time() - session['last_keepalive']
        return timesince_keepalive > session['timeout']
    
    def create_session(self, client_id: str, timeout: int = 60) -> dict:
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

        return ok(data=session_id)

    def get_session_info(self, session_id: str) -> dict:
        """Get session details as dict filter by session ID"""
        if session_id not in self.__sessions:
            print(f"[LockService] fetch session failed: session {session_id} not found")
            return fail(ErrorCode.SESSION_NOT_FOUND, session_id=session_id)

        session = self.__sessions[session_id].copy()
        session['is_expired'] = self._is_expired(self.__sessions[session_id])
        print(f"[LockService] fetch session {session_id}")
        return ok(data=session)

    def update_keepalive(self, session_id: str) -> dict:
        """Update keepalive timestamp for a session"""
        if session_id not in self.__sessions:
            print(f"[LockService] keepalive failed: session {session_id} not found")
            return fail(ErrorCode.SESSION_NOT_FOUND, session_id=session_id)

        
        if self._is_expired(self.__sessions[session_id]):
            print(f"[LockService] keepalive failed: session {session_id} expired")
            return fail(ErrorCode.SESSION_EXPIRED, session_id=session_id)

        self.__sessions[session_id]['last_keepalive'] = time.time()
        print(f"[LockService] keepalive success: session {session_id}")
        return ok()

    def delete_session(self, session_id: str) -> dict:
        """Delete a client session"""
        
        if session_id not in self.__sessions:
            print(f"[LockService] delete session failed: session {session_id} not found")
            return fail(ErrorCode.SESSION_NOT_FOUND, session_id= session_id)    

        session = self.__sessions[session_id]
        for resource in session['locks_held']:
            print(f"[LockService] delete session locks: session {session_id} {resource} found")
            if resource in self.__locks:
                print(f"[LockService] delete session locks: session {session_id} {resource} released")
                del self.__locks[resource]
        del self.__sessions[session_id]
        
        print(f"[LockService] session {session_id} deleted")
        return ok()

    def get_service_stats(self) -> dict:
        """Get the lock service statistics"""
        total_sessions = len(self.__sessions)
        active_sessions = sum(1 for session in self.__sessions.values() if not self._is_expired(session))
        expired_sessions = sum(1 for session in self.__sessions.values() if self._is_expired(session))
        timestamp = datetime.now(timezone.utc).isoformat()

        data = {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "expired_sessions": expired_sessions,
            "timestamp" : timestamp,
        }
        return ok(data=data)

    def acquire_lock(self, session_id: str, resource: str) -> dict:
        """Acquire a lock on a resource if available"""
        if session_id not in self.__sessions:
            print(f"acquire lock failed: session {session_id} does not exist")
            return fail(ErrorCode.SESSION_NOT_FOUND, session_id= session_id)
        session = self.__sessions[session_id]
        if self._is_expired(session):
            print(f"[LockService] acquire lock failed: session {session_id} expired")
            return fail(ErrorCode.SESSION_EXPIRED, session_id= session_id)
            
        if resource in self.__locks:
            existing_lock = self.__locks[resource]
            if existing_lock['session_id'] == session_id:
                return ok(data=existing_lock['fence_token'])
            print(f"[LockService] acquire lock failed: resource already locked by another session")
            return fail(ErrorCode.LOCK_ALREADY_HELD, resource=resource) 

        self.__fence_counter += 1
        fence_token = self.__fence_counter
        self.__locks[resource] = {
            "resource": resource,
            "session_id": session_id,
            "fence_token": fence_token,
            "acquired_at": time.time(),
        }
        session['locks_held'].append(resource)
        print(f"[LockService] lock acquired on resource {resource} by session {session_id}")
        return ok(data=fence_token)

    def release_lock(self, session_id: str, resource: str, fence_token: int) -> dict:
        """Release a lock if owned by the session and if the fence_token is valid"""
        if resource not in self.__locks:
            print(f"[LockService] Lock release failed: no lock exists on the resource {resource}")
            return fail(ErrorCode.LOCK_NOT_FOUND, resource=resource)

        existing_lock = self.__locks[resource]
        if existing_lock['fence_token'] != fence_token:
            print(f"[LockService] Lock release failed: fence token mismatch")
            return fail(ErrorCode.INVALID_FENCE_TOKEN, fence_token=fence_token)

        if existing_lock['session_id'] != session_id:
            print(f"[LockService] Lock release failed: session {session_id} does own the lock on the resource {resource}")
            return fail(ErrorCode.LOCK_NOT_OWNED, session_id=session_id, resource=resource)

        del self.__locks[resource]
        session = self.__sessions[session_id]
        if resource in session['locks_held']:
            session['locks_held'].remove(resource)

        print(f"[LockService] Lock on resource {resource} held by session {session_id} released")

        return ok()

    def lock_status(self, resource) -> dict:
        """Check if a resource is locked and who holds"""
        if resource not in self.__locks:
            print(f"Lock status: There is currently no lock on the resource {resource}")
            return ok(data=None)
        existing_lock = self.__locks[resource]
        print(f"Lock status: Resource {resource} is locked by session {existing_lock['session_id']}")
        return ok(data=existing_lock['session_id'])
        
    def cleanup_expired_sessions(self) -> int:
        """Delete all expired sessions and the associated locks and return the count of sessions cleared"""
        start_time = time.time()
        expired = []
        cleaned = 0
        for session_id, session in self.__sessions.items():
            if (start_time - session['last_keepalive']) > session['timeout']:
                expired.append(session_id)
        for session_id in expired:
            session = self.__sessions[session_id]
            for resource in session['locks_held']:
                if resource in self.__locks:
                    print(f"[LockService] Lock on resource {resource} deleted due to session cleanup")
                    del self.__locks[resource]
            cleaned+=1
            print(f"Session {session_id} deleted during expired session cleanup")
            del self.__sessions[session_id]
        return cleaned
            


        
