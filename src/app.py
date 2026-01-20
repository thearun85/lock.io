from flask import Flask, request, jsonify
from datetime import datetime, timezone
import logging
from .lock_service import LockService
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)
lock_service = LockService()
def create_app():
    app = Flask(__name__)
    
    @app.route("/health", methods=['GET'])
    def health_check():
        """Health check for the app"""
        return jsonify({
            "service": "lock.io",
            "version": "0.1.0",
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }), 200


    def validate_request(*required_fields):
        """Validate request is JSON and contains required fields"""
        if not request.is_json:
            return jsonify({
                "error": "Request content-type must be application/json"
            }), 400
            
        data = request.get_json()
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                "error": "Missing required fields",
                "missing_fields": missing_fields,
            }), 400

        return None
    
    def get_request_data(*required_fields):
        """Validate and get the request data"""
        error = validate_request(*required_fields)
        if error:
            return None, error

        return request.get_json(), None
        
    @app.route("/sessions", methods=['POST'])
    def create_session():
        """Create a new client session
        Request body:
        {
            "client_id": "string",
            "timeout": 60 - optional (defaults to 60) # seconds
        }

        Response:
        {
            "session_id": "uuid",
            "client_id": string,
            "timeout": 60,
            "keepalive_interval": timeout//3 # 1/3 rd of the timeout
        }
        """ 
        data, error = get_request_data("client_id")
        if error:
            return error
        client_id = data['client_id']
        timeout = data.get("timeout", 60) # default timeout to 60

        session_id = lock_service.create_session(client_id, timeout)
        logger.info(f"Session {session_id} created for client {client_id} with timeout {timeout}")
        return jsonify({
            "session_id": session_id,
            "client_id": client_id,
            "timeout": timeout,
            "keepalive_interval": timeout//3,
        }), 201

    @app.route("/sessions/<string:session_id>", methods=['GET'])
    def get_session(session_id:str)->dict:
        """Get session details as a dict
        Response:
        {
            "session_id": "uuid",
            "client_id": "string",
            "timeout": 60,
            "created_at": 1234567890.123,
            "last_keepalive": 1234567890.123,
            "expired": false,
            "locks_held": ["resource1", "resource2"],
        }
        """
        
        session_info = lock_service.get_session_info(session_id)
        if not session_info:
            logger.warning(f"Get session info failed: Invalid session {session_id}")
            return jsonify({
                "error": "Invalid session",
                "session_id": session_id,
            }), 404
        return jsonify(session_info), 200

    @app.route("/sessions/<string:session_id>/keepalive", methods=['POST'])
    def keepalive(session_id:str):
        """Extend session lifetime
        Response:
        {
            "sucess": true,
            "session_id": session_id
        }"""
        success = lock_service.keepalive(session_id)
        if not success:
            logger.warning(f"Keep alive failed: Invalid session {session_id}")
            return jsonify({
                "success": False,
                "reason": "Invalid or expired session",
                "session_id": session_id,
            }), 404

        return jsonify({
            "success": True,
            "session_id": session_id
        }), 200

    @app.route("/sessions/<string:session_id>", methods=['DELETE'])
    def delete_session(session_id:str):
        """Delete a session and release all its locks

        Response
        {
            "success": true,
            "session_id": session_id
        }
        """
        success = lock_service.delete_session(session_id)
        if not success:
            return jsonify({
                "success": False,
                "reason": "Invalid or expired session",
                "session_id": session_id,
            }), 404

        return jsonify({
            "success": True,
            "session_id": session_id,
        }), 200

    @app.route("/sessions/<string:session_id>/locks/<string:resource>", methods=['POST'])
    def acquire_lock(session_id:str, resource:str):
        """Acquire a lock on a resource
        Response
        {   
            "acquired": True,
            "resource": "string",
            "session_id": "uuid",
            "fence_token": int
        }

        """
        if not resource or len(resource) > 256:
            return jsonify({
                "error": "Invalid resource name",
                "session_id": session_id,
                "resource": resource,
            }), 400
        fence_token = lock_service.acquire_lock(session_id, resource)
        if not fence_token:
            return jsonify({
                "acquired": False,
                "reason": "Invalid session or lock unavailable",
                "session_id": session_id,
                "resource": resource,
            }), 409 # Conflict

        return jsonify({
            "acquired": True,
            "resource": resource,
            "session_id": session_id,
            "fence_token": fence_token,
        }), 201

    @app.route("/sessions/<string:session_id>/locks/<string:resource>", methods=['DELETE'])
    def release_lock(session_id:str, resource:str):
        """Release a lock on the resource
        Response:
        {
            "released": True,
            "resource": "string",
        }
        """
        if not resource:
            return jsonify({
                "released": False,
                "reason": "Invalid resource name",
            }), 400
        fence_token = request.args.get("fence_token", type=int)
        if fence_token is None:
            return jsonify({
                "released": False,
                "reason": "fence token is required",
            }), 400

        released = lock_service.release_lock(session_id, resource, fence_token)
        if not released:
            return jsonify({
                "released": False,
                "reason": "Invalid session, resource or fence_token"
            }), 400

        return jsonify({
            "released": True,
            "resource": resource,
        }), 200

    @app.route("/locks/<string:resource>", methods=['GET'])
    def get_lock_info(resource:str):
        """Get lock information on a resource
        Response:
        {
            "resource": "string",
            "status": locked,
            "fence_token": int,
            "session_id": "uuid",
            "acquired_at": 1234567890.123,
        }

        """
        if not resource:
            return jsonify({
                "error": "Invalid resource name",
                "resource": resource,
            }), 400
            
        lock_info = lock_service.get_lock_info(resource)
        if not lock_info:
            return jsonify({
                "error": "Resource not locked",
                "resource": resource,
            }), 400
        return jsonify({
            "resource": lock_info.resource,
            "locked": True,
            "session_id": lock_info.session_id,
            "fence_token": lock_info.fence_token,
            "acquired_at": lock_info.acquired_at,
        }), 200

    @app.route("/admin/cleanup", methods=['POST'])
    def admin_cleanup():
        """Force cleanup of expired sessions
        Response:
        {
            "cleaned": int,
            "message": "string"
        }

        """
        cleaned = lock_service.cleanup_expired_sessions()
        return jsonify({
            "cleaned": cleaned,
            "message": f"Cleaned up {cleaned} expired sessions"
        }), 200

    @app.route("/stats", methods=['GET'])
    def get_stats():
        """Get service statistics
        Response:
        {
            "total_sessions": int,
            "total_locks": int,
            "fence_counter": int,
            "active_sessions": int,
            "expired_sessions": int,
        }"""

        stats = lock_service.get_stats()
        return jsonify(stats), 200
    return app
    



if __name__ == '__main__':
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
