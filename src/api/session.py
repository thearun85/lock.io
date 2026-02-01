"""Distributed Lock Service - Public API for Sessions"""
from flask import Blueprint, request, jsonify, current_app
from src.core import ErrorCode, ERROR_HTTP_STATUS

session_bp = Blueprint("sessions", __name__)

def get_lock_service():
    """Helper to get lock service from app context"""
    return current_app.extensions['lock_service']

def validate_create_session() -> str | None:
    """Validate create request and respond"""
    data = request.get_json()
    if data is None:
        return "Request body must be JSON", None

    client_id = data.get('client_id', None)
    if not client_id:
        return "client_id is required", None

    if not isinstance(client_id, str):
        return "client_id must be a string", None

    client_id = client_id.strip()
    if not client_id:
        return "client_id must be non-empty", None

    if len(client_id) > 255:
        return "client_id cannot exceed 255 characters", None
        
    timeout = data.get('timeout', 60)
    if not isinstance(timeout, int):
        return "timeout must be an integer", None

    if timeout < 5 or timeout > 3600:
        return "timeout must be between 5 and 3600 seconds", None

    return "", data

@session_bp.route("/sessions", methods=['POST'])
def create_session() -> dict:
    """
    Create a client session
    Request:
    {
        "client_id": "str",
        "timeout": int (optional, defaults to 60s)
    }
    Response:
    {
        "session_id": "str",
        "client_id": "str",
        "timeout": int,
        "keepalive_interval": int, 1/3rd of the timeout
    }

    """

    ## Validate request
    error, data = validate_create_session()
    if error:
        return jsonify({
            "error": error,
        }), 400
        
    client_id = data.get('client_id').strip()
    timeout = data.get('timeout', 60)
    result = get_lock_service().create_session(
        client_id=client_id, 
        timeout=timeout)
        
    keepalive_interval = timeout//3
    if result['success']:
        return jsonify({
            "session_id": result['data'],
            "client_id": client_id,
            "timeout": timeout,
            "keepalive_interval": keepalive_interval,
        }), 201
    else:
        return jsonify({
        "err_msg": "Session creation failed"
    }), 500

@session_bp.route("/sessions/<string:session_id>", methods=['GET'])
def get_session_info(session_id: str) -> dict:
    """
    Get client session details if it exists, as a dict
    
    Response Success:
        {
            "session_id": "str",
            "client_id": "str",
            "timeout": int,
            "created_at": float,
            "last_keepalive": float,
            "locks_held": list[str],
            "keepalive_interval": int,
            "is_expired": false,
        }, 201

    Response Error:
            {
                "session_id": "str",
                "error": "str",
            }, 404
    """
    result = get_lock_service().get_session_info(session_id)
    if not result['success']:
        status = ERROR_HTTP_STATUS.get(result['err_cd'], 400)
        return jsonify({
            "error": result['err_msg'],
            "session_id": session_id,
        }), status

    session = result['data']
    session['keepalive_interval'] = session['timeout']//3
    
    return jsonify(session), 200

@session_bp.route("/sessions/<string:session_id>/keepalive", methods=['POST'])
def keepalive(session_id: str) -> dict:
    """
    Extend the session lifetime

    Response Success:
    {
        "updated": true,
        "session_id": "str"
    }

    Response Error:
        {
            "updated": false,
            "session_id": "str",
            "error": "str"
        }, 404/ 400 # Session does not exist or session expired
    """
    result = get_lock_service().update_keepalive(session_id)
    if not result['success']:
        status = ERROR_HTTP_STATUS.get(result['err_cd'], 400)
        return jsonify({
            "error": result['err_msg'],
            "session_id": session_id,
            "updated": False,
        }), status

    return jsonify({
        "updated": True,
        "session_id": session_id,
    }), 200
    
    
@session_bp.route("/sessions/<string:session_id>", methods=['DELETE'])
def delete_session(session_id: str) -> dict:
    """
    Delete a valid client session
    Response Success:
        {
            "deleted": true,
            "session_id": "str"
        }
    
    Response Error:
        {
            "deleted": false,
            "session_id": "str",
            "error": "str"
        }, 404 # Session does not exist
    """
    result = get_lock_service().delete_session(session_id)
    if not result['success']:
        status = ERROR_HTTP_STATUS.get(result['err_cd'], 400)
        return jsonify({
            "error": result['err_msg'],
            "session_id": session_id,
            "deleted": False,
        }), status

    return jsonify({
        "deleted": True,
        "session_id": session_id,
    }), 200
    
