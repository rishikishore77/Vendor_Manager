#!/usr/bin/env python3
"""
Enhanced Vendor Management System
A comprehensive system for managing vendor attendance, approvals, and billing.
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app(config_name='development'):
    """Application factory pattern"""
    # IMPORTANT: Configure template and static folders correctly
    app = Flask(__name__, 
                template_folder='app/templates', 
                static_folder='app/static')

    # Load configuration
    if config_name == 'development':
        from config.development import DevelopmentConfig
        app.config.from_object(DevelopmentConfig)
    elif config_name == 'production':
        from config.production import ProductionConfig
        app.config.from_object(ProductionConfig)
    else:
        from config.development import DevelopmentConfig
        app.config.from_object(DevelopmentConfig)

    # Initialize database
    from app.utils.database import Database
    try:
        Database.initialize(app.config['MONGO_URI'])
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.vendor import vendor_bp
    from app.routes.manager import manager_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(vendor_bp, url_prefix='/vendor')
    app.register_blueprint(manager_bp, url_prefix='/manager')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    @app.route('/')
    def index():
        """Home page - redirect based on user role"""
        if 'user_id' in session:
            from app.models.user import User
            user = User.find_by_id(session['user_id'])
            if user:
                if user['role'] == 'vendor':
                    return redirect(url_for('vendor.dashboard'))
                elif user['role'] == 'manager':
                    return redirect(url_for('manager.dashboard'))
                elif user['role'] == 'admin':
                    return redirect(url_for('admin.dashboard'))
        return redirect(url_for('auth.login'))

    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(error):
        logger.error(f"Server error: {error}")
        return render_template('errors/500.html'), 500

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
