"""Distributed Lock Service"""

import uuid
import time
from datetime import datetime, timezone
from src.core.errors import ErrorCode, ERROR_MESSAGES
import threading
from pysyncobj import SyncObj, SyncObjConf, replicated
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_instance_locks = {} # a record of locks on various web server thread instances
_locks_lock = threading.RLock() # parent lock to manage the web server threads

def _get_instance_lock(instance_id: int) -> threading.RLock:
    with _locks_lock:
        if instance_id not in _instance_locks:
            _instance_locks[instance_id] = threading.RLock()
        return _instance_locks[instance_id]
        
# Helper functions
def ok(data=None):
    """Create success result"""
    return {"success": True, "data": data}

def fail(err_cd, **format_args):
    """Create error result"""
    err_msg = ERROR_MESSAGES[err_cd]
    err_msg = err_msg.format(**format_args)
    return {"success": False, "err_cd": err_cd, "err_msg": err_msg}

class DistributedLockService(SyncObj):

    def __init__(self, self_address: str, partner_addresses: list[str]):
        """Initialize the lock service"""
        
        conf = SyncObjConf(
            autoTick=True,
            dymanicmembershipChange=True,
        )
        self.__instance_id = id(self)
        super().__init__(self_address, partner_addresses, conf)
        
        self.__sessions: dict[str, dict] = {}
        self.__locks: dict[str, dict] = {}
        self.__fence_counter: int = 0 # to prevent stale sessions
        logger.info(f"[LockService] initialized with {self_address}")
        logger.info(f"[LockService] initialized with {partner_addresses}")

    @property
    def _lock(self) -> threading.RLock:
        return _get_instance_lock(self.__instance_id)

    def _is_expired(self, session) -> bool:
        """Check whether the session is expired"""
        timesince_keepalive = time.time() - session['last_keepalive']
        return timesince_keepalive > session['timeout']

    @replicated
    def _create_session_internal(self, client_id: str, timeout: int = 60) -> dict:
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
        logger.info(f"[LockService] Session {session_id} created")
        return ok(data=session_id)
    
    def create_session(self, client_id: str, timeout: int = 60) -> dict:
        """Create a client session"""
        with self._lock:
            logger.info(f"[LockService] Creating session")
            return self._create_session_internal(client_id, timeout, sync=True)

    def get_session_info(self, session_id: str) -> dict:
        """Get session details as dict filter by session ID"""
        if session_id not in self.__sessions:
            logger.info(f"[LockService] fetch session failed: session {session_id} not found")
            return fail(ErrorCode.SESSION_NOT_FOUND, session_id=session_id)

        session = self.__sessions[session_id].copy()
        session['is_expired'] = self._is_expired(self.__sessions[session_id])
        logger.info(f"[LockService] fetch session {session_id}")
        return ok(data=session)

    @replicated
    def _update_keepalive_internal(self, session_id: str) -> dict:
        """Update keepalive timestamp for a session"""
        if session_id not in self.__sessions:
            logger.info(f"[LockService] keepalive failed: session {session_id} not found")
            return fail(ErrorCode.SESSION_NOT_FOUND, session_id=session_id)

        
        if self._is_expired(self.__sessions[session_id]):
            logger.info(f"[LockService] keepalive failed: session {session_id} expired")
            return fail(ErrorCode.SESSION_EXPIRED, session_id=session_id)

        self.__sessions[session_id]['last_keepalive'] = time.time()
        logger.info(f"[LockService] keepalive success: session {session_id}")
        return ok()

    def update_keepalive(self, session_id: str) -> dict:
        with self._lock:
            logger.info(f"[LockService] Keepalive initiated")
            return self._update_keepalive_internal(session_id, sync=True)

    @replicated
    def _delete_session_internal(self, session_id: str) -> dict:
        """Delete a client session"""
        
        if session_id not in self.__sessions:
            logger.info(f"[LockService] delete session failed: session {session_id} not found")
            return fail(ErrorCode.SESSION_NOT_FOUND, session_id= session_id)    

        session = self.__sessions[session_id]
        for resource in session['locks_held']:
            logger.info(f"[LockService] delete session locks: session {session_id} {resource} found")
            if resource in self.__locks:
                logger.info(f"[LockService] delete session locks: session {session_id} {resource} released")
                del self.__locks[resource]
        del self.__sessions[session_id]
        
        logger.info(f"[LockService] session {session_id} deleted")
        return ok()

    def delete_session(self, session_id: str) -> dict:
        with self._lock:
            logger.info(f"[LockService] Delete session initiated")
            return self._delete_session_internal(session_id, sync=True)
        
    def get_service_stats(self) -> dict:
        """Get the lock service statistics"""
        total_sessions = len(self.__sessions)
        active_sessions = sum(1 for session in self.__sessions.values() if not self._is_expired(session))
        expired_sessions = sum(1 for session in self.__sessions.values() if self._is_expired(session))
        timestamp = datetime.now(timezone.utc).isoformat()
        logger.info(f"[LockService] Fetching service statistics")
        data = {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "expired_sessions": expired_sessions,
            "timestamp" : timestamp,
            "fence_counter": self.__fence_counter,
            "total_locks": len(self.__locks),
        }
        logger.info(f"[LockService] Service statistics {data}")
        return ok(data=data)

    @replicated
    def _acquire_lock_internal(self, session_id: str, resource: str) -> dict:
        """Acquire a lock on a resource if available"""
        if session_id not in self.__sessions:
            logger.info(f"acquire lock failed: session {session_id} does not exist")
            return fail(ErrorCode.SESSION_NOT_FOUND, session_id= session_id)
        session = self.__sessions[session_id]
        if self._is_expired(session):
            logger.info(f"[LockService] acquire lock failed: session {session_id} expired")
            return fail(ErrorCode.SESSION_EXPIRED, session_id= session_id)
            
        if resource in self.__locks:
            existing_lock = self.__locks[resource]
            if existing_lock['session_id'] == session_id:
                return ok(data=existing_lock['fence_token'])
            logger.info(f"[LockService] acquire lock failed: resource already locked by another session")
            return fail(ErrorCode.LOCK_ALREADY_HELD, resource=resource) 
        current_value = self.__fence_counter
        time.sleep(0.001)
        current_value = current_value + 1
        self.__fence_counter = current_value
        fence_token = self.__fence_counter
        self.__locks[resource] = {
            "resource": resource,
            "session_id": session_id,
            "fence_token": fence_token,
            "acquired_at": time.time(),
        }
        session['locks_held'].append(resource)
        logger.info(f"[LockService] lock acquired on resource {resource} by session {session_id}")
        return ok(data=fence_token)

    def acquire_lock(self, session_id: str, resource: str) -> dict:
        with self._lock:
            return self._acquire_lock_internal(session_id, resource, sync=True)

    @replicated
    def _release_lock_internal(self, session_id: str, resource: str, fence_token: int) -> dict:
        """Release a lock if owned by the session and if the fence_token is valid"""
        if resource not in self.__locks:
            logger.info(f"[LockService] Lock release failed: no lock exists on the resource {resource}")
            return fail(ErrorCode.LOCK_NOT_FOUND, resource=resource)

        existing_lock = self.__locks[resource]
        if existing_lock['fence_token'] != fence_token:
            logger.info(f"[LockService] Lock release failed: fence token mismatch")
            return fail(ErrorCode.INVALID_FENCE_TOKEN, fence_token=fence_token)

        if existing_lock['session_id'] != session_id:
            logger.info(f"[LockService] Lock release failed: session {session_id} does own the lock on the resource {resource}")
            return fail(ErrorCode.LOCK_NOT_OWNED, session_id=session_id, resource=resource)

        del self.__locks[resource]
        session = self.__sessions[session_id]
        if resource in session['locks_held']:
            session['locks_held'].remove(resource)

        logger.info(f"[LockService] Lock on resource {resource} held by session {session_id} released")

        return ok()

    def release_lock(self, session_id: str, resource: str, fence_token: int) -> dict:
        with self._lock:
            return self.release_lock_internal(session_id, resource, fence_token, sync=True)
            
    def lock_status(self, resource) -> dict:
        """Check if a resource is locked and who holds"""
        if resource not in self.__locks:
            logger.info(f"Lock status: There is currently no lock on the resource {resource}")
            return ok(data=None)
        existing_lock = self.__locks[resource]
        logger.info(f"Lock status: Resource {resource} is locked by session {existing_lock['session_id']}")
        return ok(data=existing_lock['session_id'])

    @replicated
    def _cleanup_expired_sessions_internal(self) -> int:
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
                    logger.info(f"[LockService] Lock on resource {resource} deleted due to session cleanup")
                    del self.__locks[resource]
            cleaned+=1
            logger.info(f"Session {session_id} deleted during expired session cleanup")
            del self.__sessions[session_id]
        return cleaned
            
    def cleanup_expired_sessions(self) -> int:
        with self._lock:
            return self._cleanup_expired_sessions_internal(sync=True)

    def is_leader(self) -> bool:
        return self._isLeader()

    def get_leader(self) -> str|None:
        leader = self._getLeader()
        if leader:
            return str(leader)
        return None
    
    def get_cluster_status(self) -> dict:
        """Get the statistics of the raft cluster"""
        result = self.getStatus()
        stats = self.get_service_stats()
        stats = stats['data']
        states = ["FOLLOWER", "CANDIDATE", "LEADER"]
        status = {
            "node": str(self.selfNode),
            "state": states[result['state']],
            "is_leader": self.is_leader(),
            "is_ready": self.isReady(),
            "leader": self.get_leader(),
            "has_quorum": result['has_quorum'],
            "term": result['raft_term'],
            "uptime": result['uptime'],
            "no_of_nodes": len(self.otherNodes)+1,
            "total_sessions": stats['total_sessions'],
            "total_locks": stats['total_locks'],
            "fence_counter": stats['fence_counter'],
            
        }

        return status


    
