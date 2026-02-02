"""
Distributed Lock Service - Public API endpoints for Locks
"""
from flask import Blueprint, request, jsonify, current_app
from src.core.errors import ERROR_HTTP_STATUS

lock_bp = Blueprint("locks", __name__)

def validate_acquire_request(session_id: str, resource: str) -> str | None:    
    """Validate session_id and resource"""

    session_id = session_id.strip()
    if not session_id:
        return "Session ID must be a non-empty string"

    resource = resource.strip()
    
    if not resource:
        return "Resource must be a non-empty string"

    if len(resource) > 255:
        return "Resource cannot exceed 255 characters"

    return None
    
@lock_bp.route("sessions/<string:session_id>/locks/<string:resource>", methods=['POST'])
def acquire_lock(session_id: str, resource:str):
    """Acquire lock on a resource if available"""
    
    error = validate_acquire_request(session_id, resource)
    if error:
        return jsonify({
            "error": error,
            "session_id": session_id,
            "resource": resource
        }), 400

    svc = current_app.extensions['lock_service']
    result = svc.acquire_lock(session_id, resource)
    if not result['success']:
        status = ERROR_HTTP_STATUS.get(result['err_cd'], 400)
        return jsonify({
            "error": result['err_msg'],
            "session_id": session_id,
            "resource": resource
        }), status

    fence_token = result['data']
    
    return jsonify({
        "session_id": session_id,
        "resource": resource,
        "fence_token": fence_token,
        "acquired": True,
    }), 201

def validate_release_request(session_id: str, resource: str) -> str | None:    
    """Validate session_id and resource"""

    error = validate_acquire_request(session_id, resource)
    if error:
        return error

    fence_token = request.args.get("fence_token", type=int)
    if not fence_token:
        return "Fence token is required"

    return None


@lock_bp.route("sessions/<string:session_id>/locks/<string:resource>", methods=['POST'])
def release_lock(session_id: str, resource:str):
    """Release the lock on a resource if it exists and is owned the session"""
    
    error = validate_release_request(session_id, resource)
    if error:
        return jsonify({
            "error": error,
            "session_id": session_id,
            "resource": resource,
        }), 400

    fence_token = request.args.get("fence_token", type=int)
    svc = current_app.extensions['lock_service']
    result = svc.release_lock(session_id, resource, fence_token)
    if not result['success']:
        status = ERROR_HTTP_STATUS.get(result['err_cd'], 400)
        return jsonify({
            "error": result['err_msg'],
            "session_id": session_id,
            "resource": resource
        }), status

    return jsonify({
        "session_id": session_id,
        "resource": resource,
        "fence_token": fence_token,
        "released": True
    }), 200
