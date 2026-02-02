"""Distributed Lock Service public API"""
from flask import Flask

from src.core import DistributedLockService

def create_app():

    app = Flask(__name__)

    lock_service = DistributedLockService()
    app.extensions['lock_service'] = lock_service

    from src.api import health_bp, session_bp, lock_bp
    app.register_blueprint(health_bp)
    app.register_blueprint(session_bp)
    app.register_blueprint(lock_bp)
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
