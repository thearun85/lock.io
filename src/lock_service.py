from typing import Optional
import threading
import uuid
import time
from pysyncobj import SyncObj, SyncObjConf, replicated
import logging
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

class LockService(SyncObj):

    def __init__(self, self_address: str, partner_addresses: list[str]):
        """
        Initialize distributed lock service"""

        conf = SyncObjConf(
            autoTick=True,
            dynamicMembershipChange=True
        )

        super().__init__(self_address, partner_addresses, conf)
        # Lock service state container for replication
        self.__sessions: dict[str, dict] = {}
        self.__locks: dict[str, dict] = {}
        self.__fence_counter: int = 0

        # Thread safety
        self.__lock = threading.RLock()
        logger.info(f"Lock service initialized with {self_address}")
        logger.info(f"Partners {partner_addresses}")
        
    def get_leader(self)->Optional[str]:
        """Wrapper for raft internal method"""
        leader = self._getLeader()
        if leader:
            return str(leader)
        return None

    def is_leader(self)->bool:
        """Wrapper for raft internal method"""
        return self._isLeader()

    def is_ready(self)->bool:
        """Wrapper for raft internal method"""
        return self.isReady()
        
    @replicated
    def _create_session_internal(self, client_id: str, session_id: str, timeout: int)->str:
        """Create a client session - internal replicated method"""
        logger.info("Inside _create_session_internal")
        self.__sessions[session_id] = {
            "session_id": session_id,
            "client_id": client_id,
            "timeout": timeout,
            "created_at": time.time(),
            "last_keepalive": time.time(),
            "locks_held": [],
        }
        logger.info(f"Created session {session_id}")
        return session_id        
    
    def create_session(self, client_id: str, timeout:int = 60)->str:
        """Create a client session"""
        logger.info("Entering lock service create_session")
        with self.__lock:
            session_id = str(uuid.uuid4())
            logger.info(f"Session ID is {session_id}")
            return self._create_session_internal(client_id, session_id, timeout, sync=True)

    def _is_expired(self, session:dict)-> bool:
        """Check if a session is expired"""
        return (time.time() - session['last_keepalive']) > session['timeout']
        
    def get_session_info(self, session_id:str)->Optional[dict]:
        """Get session details by ID"""
        session = self.__sessions.get(session_id)
        if not session:
            logger.warning(f"Get session info failed: {session_id} not found")
            return None

        return session.copy()

    def _get_session(self, session_id:str)->Optional[dict]:
        """Get session by ID"""
        return self.__sessions.get(session_id)

    @replicated
    def _keepalive_internal(self, session_id: str)->bool:
        """Update keepalive for a client session"""
        session = self._get_session(session_id)
        if not session:
            logger.warning(f"Keepalive failed: {session_id} not found")
            return False
        if self._is_expired(session):
            logger.warning(f"Keepalive failed: {session_id} expired")
            return False
        session['last_keepalive'] = time.time()
        
        return True
  
    
    def keepalive(self, session_id: str)->bool:
        """Update keepalive for a client session"""
        with self.__lock:
            return self._keepalive_internal(session_id, sync=True)

    @replicated
    def _delete_session_internal(self, session_id: str)->bool:
        """Delete a client session - internal replicated method"""
        session = self._get_session(session_id)
        if not session:
            logger.warning(f"Delete session failed: {session_id} not found")
            return False

        for resource in session['locks_held']:
            if resource in self.__locks:
                del self.__locks[resource]
                logger.info(f"Resource {resource} deleted due to session deletion")

        del self.__sessions[session_id]
        logger.info(f"Session {session_id} deleted")
        
        return True


    def delete_session(self, session_id: str)->bool:
        """Delete a client session"""
        with self.__lock:
            
            return self._delete_session_internal(session_id, sync=True)
        
    @replicated
    def _acquire_lock_internal(self, session_id:str, resource:str)->Optional[int]:
        """Acquire a lock on the resource - internal replicated method"""
        logging.info("Inside _acquire_lock_internal")
        session = self._get_session(session_id)
        if not session:
            logger.warning(f"Lock acquisition failed: {session_id} not found")
            return None
        if self._is_expired(session):
            logger.warning(f"Lock acquisition failed: {session_id} expired")
            return None
        logging.info("Inside _acquire_lock_internal, valid session")
        existing_lock = self.__locks.get(resource)
        if existing_lock:
            logger.warning(f"Lock acquisition failed: resource {resource} already locked")
            return None
        logging.info("Inside _acquire_lock_internal no locks")

        self.__fence_counter+=1
        fence_token = self.__fence_counter
        
        logging.info(f"Inside _acquire_lock_internal, fence token is {fence_token}")
        self.__locks[resource] = {
            "resource": resource,
            "session_id": session_id,
            "fence_token": fence_token,
            "acquired_at": time.time(),
        }
        session['locks_held'].append(resource)

        logger.info(f"Resource {resource} locked by session {session_id} with fence token {fence_token}")
        return fence_token


    def acquire_lock(self, session_id: str, resource:str)->Optional[int]:
        """Acquire a lock on the resource"""
        logging.info("Inside acquire_lock")
        with self.__lock:
            return self._acquire_lock_internal(session_id, resource, sync=True)

    def get_lock_info(self, resource:str)->Optional[dict]:
        """Get lock information on a resource"""
        
        lock = self.__locks.get(resource)
        if not lock:
            return None
        return lock.copy()

    @replicated
    def _release_lock_internal(self, session_id:str, resource:str, fence_token:int)->bool:
        """Release the lock on a resource - internal replicated method"""
        existing_lock = self.__locks.get(resource)
        if existing_lock:
            if existing_lock['session_id'] != session_id:
                logger.warning(f"Lock release failed: resource {resource} locked by another session")
                return False

            if existing_lock['fence_token'] != fence_token:
                logger.warning(f"Lock release failed: fence token mismatch")
                return False

            del self.__locks[resource]
            session = self._get_session(session_id)
            if resource in session['locks_held']:
                session['locks_held'].remove(resource)
            logger.info(f"Lock released on resource {resource}")
            return True
        return False
            
    def release_lock(self, session_id:str, resource: str, fence_token:int)->bool:
        """Release the lock on a resource"""
        with self.__lock:
            return self._release_lock_internal(session_id, resource, fence_token, sync=True)

    def get_stats(self)->dict:
        """Get service stats"""

        return {
            "total_sessions": len(self.__sessions),
            "total_locks": len(self.__locks),
            "active_sessions": sum(1 for session in self.__sessions.values() if not self._is_expired(session)),
            "expired_sessions": sum(1 for session in self.__sessions.values() if self._is_expired(session)),
            "fence_counter": self.__fence_counter,
        }

    @replicated
    def _release_expired_sessions(self)->int:
        """Release expired sessions and its locks - internal replicated method"""
        expired_ids = []
        cleaned = 0
        for session_id, session in self.__sessions.items():
            if self._is_expired(session):
                expired_ids.append(session_id)

        for session_id in expired_ids:
            session = self._get_session(session_id)
            for resource in session['locks_held']:
                if resource in self.__locks:
                    del self.__locks[resource]
        
            del self.__sessions[session_id]
            cleaned+=1
        return cleaned


    def release_expired_sessions(self)->int:
        """Release expired sessions and its locks"""
        with self.__lock:
            return self._release_expired_sessions(sync=True)

    def get_stats(self)->dict:
        """Get service stats"""
        return {
            "total_session": len(self.__sessions),
            "total_locks": len(self.__locks),
            "fence_counter": self.__fence_counter,
            "active_sessions": sum(1 for session in self.__sessions.values() if not self._is_expired(session)),
            "expired_sessions": sum(1 for session in self.__sessions.values() if self._is_expired(session))
        }

    def get_all_session_locks(self, session_id:str)->Optional[dict]:
        """Get all locks held by this session"""
        return self.__sessions[session_id]['locks_held']
