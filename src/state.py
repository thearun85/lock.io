from typing import Dict
from .models import Session, Lock
import threading

class LockServiceState:
    """Thread-safe state container for lock service"""
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.locks: Dict[str, Lock] = {}
        self.fence_counter: int = 0
        
        # Thread-safety
        self._lock = threading.RLock()

    def next_fence_token(self)->int:
        """Get next fence token (thread-safe)"""
        with self._lock:
            self.fence_counter+=1
            return self.fence_counter

    
