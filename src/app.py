from flask import Flask, request, jsonify
from datetime import datetime, timezone
from typing import Optional
from .config import get_node_config, get_api_port
from .lock_service import LockService
import logging
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

current_node, partner_nodes = get_node_config()
lock_service = LockService(current_node, partner_nodes)

def create_app():

    app = Flask(__name__)

    @app.route("/health", methods=['GET'])
    def health_check():
        """Health check for the service"""
        return jsonify({
            "service": "lock.io",
            "status": "healthy",
            "version": "0.1.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "is_leader": lock_service.is_leader(),
            "leader": lock_service.get_leader(),
            "is_ready": lock_service.is_ready(),
        })

    def validate_request(*required_fields):
        """Validate the request"""
        if not request.is_json:
            return jsonify({
                "error": "Request must be of Content-Type application/json"
            }), 400

        data = request.get_json()
        missing_fields = []
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                "error": "Required missing field",
                "fields": missing_fields,
            }), 400

        return None

    def get_request_data(*required_fields)->tuple[str, dict]:
        error = validate_request(*required_fields)
        if error:
            return None, error
        return request.get_json(), ""
        
    @app.route("/sessions", methods=['POST'])
    def create_session():
        """Create a client session
        Request:
            {
                "client_id": "string",
                "timeout": int
            }
        Response: 
        {
            "session_id": "uuid",
            "client_id": "string",
            "timeout": int,
            "keepalive_interval": int
        }

        """
        logger.info("Entering create_session")
        data, error = get_request_data("client_id")
        if error:
            return error
        client_id = data['client_id']
        timeout = data.get("timeout", 60)
        logger.info(f"Creating session for client {client_id} and timeout {timeout}")
        session_id = lock_service.create_session(client_id, timeout)

        logger.info(f"Session created {session_id}")
        return jsonify({
            "session_id": session_id,
            "client_id": client_id,
            "timeout": timeout,
            "keepalive_interval": timeout//3,
        }), 201

    @app.route("/sessions/<string:session_id>", methods=['GET'])
    def get_session_info(session_id:str)->Optional[dict]:
        """Get session details as a dict"""
        session = lock_service.get_session_info(session_id)
        if not session:
            return {
                "error": "Invalid session",
                "session_id": session_id,
            }, 400
        return jsonify(session), 200

    @app.route("/sessions/<string:session_id>/keepalive", methods=['POST'])
    def keepalive(session_id:str)->bool:
        """Extend session lifetime"""
        success = lock_service.keepalive(session_id)
        if not success:
            return {
                "error": "Invalid session",
                "session_id": session_id,
            }, 400
        return {
            "success": True,
            "session_id": session_id,
        }, 200

    @app.route("/sessions/<string:session_id>", methods=['DELETE'])
    def delete_session(session_id:str)->bool:
        """Delete a client session"""
        success = lock_service.delete_session(session_id)
        if not success:
            return jsnoify({
                "error": "Invalid session",
                "session_id": session_id,
            }), 400
        return jsonify({
            "deleted": True,
            "session_id": session_id
        }), 200

    @app.route("/sessions/<string:session_id>/locks/<string:resource>", methods=['POST'])
    def acquire_lock(session_id:str, resource:str)->Optional[int]:
        """Acquire a lock on a resource"""
        fence_token = lock_service.acquire_lock(session_id, resource)
        if not fence_token:
            return jsonify({
                "acquired": False,
                "error": "Lock acquisition failed",
                "resource": resource,
            }), 409
        return jsonify({
            "acquired": True,
            "fence_token": fence_token,
            "resource": resource,
        }), 201

    @app.route("/sessions/<string:session_id>/locks/<string:resource>", methods=['DELETE'])
    def release_lock(session_id:str, resource:str)->bool:
        """Release lock on a resource"""
        data, error = get_request_data("fence_token")
        if error:
            return error
        fence_token = data['fence_token']
        success = lock_service.release_lock(session_id, resource, fence_token)
        if not success:
            return jsonify({
                "error": "Failed to release lock ",
                "resource": resource,
                "reason": "Invalid session, resource or fence token"
            }), 400
        return jsonify({
            "released": True,
            "resource": resource
        }), 200

    @app.route("/sessions/<string:session_id>/locks", methods=['GET'])
    def get_session_locks(session_id:str):
        """Get all locks held by this session"""
        locks = lock_service.get_all_session_locks(session_id)
        if locks:
            return jsonify({
                "total_locks": len(locks),
                "locks": locks,
            }), 200
    
    @app.route("/admin/stats", methods=['GET'])
    def stats():
        """Get the service stats"""
        stats = lock_service.get_stats()
        return jsonify(stats), 200
    

    @app.route("/admin/cleanup", methods=['POST'])
    def cleanup()->int:
        """Clean up expired sessions and release its locks"""
        cleaned = lock_service.release_expired_sessions()
        return jsonify({
            "cleanup": "completed",
            "count": cleaned
        }), 200

    @app.route("/admin/locks/<string:resource>", methods=['GET'])
    def lock_info(resource:str):
        """Get the lock information on a resource"""
        lock_info = lock_service.get_lock_info(resource)
        if not lock_info:
            return jsonify({
                "locked": False,
                "resource": resource
            }), 200
        return jsonify({
            "locked": True,
            **lock_info,
        }), 200

    return app
if __name__ == '__main__':
    app = create_app()
    port = get_api_port()
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
