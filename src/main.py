"""Distributed Lock Service public API"""
from flask import Flask

from src.core import DistributedLockService, get_node_config, get_api_port

def create_app():

    app = Flask(__name__)
    self_address, partner_addresses = get_node_config()
    lock_service = DistributedLockService(self_address, partner_addresses)
    app.extensions['lock_service'] = lock_service

    from src.api import health_bp, session_bp, lock_bp, admin_bp
    app.register_blueprint(health_bp)
    app.register_blueprint(session_bp)
    app.register_blueprint(lock_bp)
    app.register_blueprint(admin_bp)
    return app

if __name__ == '__main__':
    app = create_app()
    
    app.run(host="0.0.0.0", port=get_api_port(), debug=True, use_reloader=False)
