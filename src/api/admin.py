"""
Distributed Lock Service - admin functionalities
"""
from flask import Blueprint, jsonify, current_app

admin_bp = Blueprint("admin", __name__)
@admin_bp.route("/admin/cleanup", methods=['POST'])
def cleanup() -> int:
    """Cleanup expired sessions and return the count"""
    svc = current_app.extensions['lock_service']
    cleaned = svc.cleanup_expired_sessions()
    return jsonify(cleaned), 200
    print(f"Session deleted {count} during cleanup")

@admin_bp.route("/admin/stats", methods=['GET'])
def get_stats() -> dict:
    """Get the service statistics as a dict"""
    svc = current_app.extensions['lock_service']
    stats = svc.get_service_stats()

    return jsonify(stats), 200
