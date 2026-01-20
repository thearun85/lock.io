from typing import Dict
import threading
from .models import Session, Lock

class LockServiceState:
    def __init__(self):
        """Thread-safe state container for lock service"""
        self.sessions: Dict[str, Session] = {}
        self.locks: Dict[str, Lock] = {}
        self.fence_counter = 0
        # Thread safety
        self._lock = threading.RLock()

    def next_fence_token(self):
        """Get the fence token for a lock"""
        with self._lock:
            self.fence_counter+=1
            return self.fence_counter
