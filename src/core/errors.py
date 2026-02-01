"""Distributed Lock Service - Error definitions"""
from enum import Enum

class ErrorCode(Enum):
    """Error codes for lock.io service"""
    # Session Errors
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    # Lock Errors
    LOCK_NOT_FOUND = "LOCK_NOT_FOUND"
    LOCK_ALREADY_HELD = "LOCK_ALREADY_HELD"
    LOCK_NOT_OWNED = "LOCK_NOT_OWNED"
    INVALID_FENCE_TOKEN = "INVALID_FENCE_TOKEN"
    


ERROR_MESSAGES = {
    ErrorCode.SESSION_NOT_FOUND: "Session {session_id} does not exist",
    ErrorCode.SESSION_EXPIRED: "Session {session_id} has expired",
    ErrorCode.LOCK_NOT_FOUND: "No lock exists on resource {resource}",
    ErrorCode.LOCK_ALREADY_HELD: "Resource {resource} already locked by another session",
    ErrorCode.LOCK_NOT_OWNED: "Session {session_id} does not own this resource {resource}",    
    ErrorCode.INVALID_FENCE_TOKEN: "Fence token {fence_token} mismatch",
    
}

ERROR_HTTP_STATUS = {
    ErrorCode.SESSION_NOT_FOUND: 404,
    ErrorCode.SESSION_EXPIRED: 410,
}
