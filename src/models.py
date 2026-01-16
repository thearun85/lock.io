from dataclasses import dataclass, field
import time
from typing import Set

@dataclass
class Session:
    """Represents client sessions"""
    session_id: str
    client_id: str
    timeout: int
    created_at: float = field(default_factory=time.time)
    last_keepalive: float = field(default_factory=time.time)
    locks_held: Set[str] = field(default_factory=set)

    def is_expired(self)->bool:
        """Check if session has expired"""
        return (time.time() - self.last_keepalive) > self.timeout

    def update_keepalive(self)->None:
        """Update last keepalive time"""
        self.last_keepalive = time.time()

@dataclass
class Lock:
    """Represents a distributed lock"""
    resource: str
    session_id: str
    fence_token: int
    acquired_at: float = field(default_factory=time.time)
