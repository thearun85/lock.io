from dataclasses import dataclass, field
import time
from typing import Set

@dataclass
class Session:
    """Represents a client session"""
    session_id: str
    client_id: str
    timeout: int
    created_at: float = field(default_factory=time.time)
    last_keepalive: float = field(default_factory=time.time)
    locks_held: Set[str] = field(default_factory=set)

    def is_expired(self):
        """Check if the session is expired"""
        return (time.time() - self.last_keepalive) > self.timeout

    def update_keepalive(self):
        """Update last keepalive"""
        self.last_keepalive = time.time()

@dataclass
class Lock:
    """Represents a lock on a resoutce"""
    resource: str
    session_id: str
    fence_token: str # To prevent stale operations
    acquired_at: float = field(default_factory=time.time)
