"""Distributed Lock Service - Error definitions"""
from enum import Enum

class ErrorCode(Enum):
    """Error codes for lock.io service"""
    # Session Errors
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    SESSION_EXPIRED = "SESSION_EXPIRED"


ERROR_MESSAGES = {
    ErrorCode.SESSION_NOT_FOUND: "Session {session_id} does not exist",
    ErrorCode.SESSION_EXPIRED: "Session {session_id} has expired",
}

ERROR_HTTP_STATUS = {
    ErrorCode.SESSION_NOT_FOUND: 404,
    ErrorCode.SESSION_EXPIRED: 410,
}
