"""Distributed Lock Service health check API"""
from flask import Blueprint, jsonify
from datetime import datetime, timezone

health_bp = Blueprint("health", __name__)

@health_bp.route("/health", methods=['GET'])
def health_check():
    """Return the health of the Distributed Lock Service"""
    return jsonify({
        "service": "lock.io",
        "version": "0.1.0",
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }), 200
