import os
from datetime import timedelta

class DevelopmentConfig:
    """Development configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-2025'
    MONGO_URI = os.environ.get('MONGO_URI') or 'mongodb://localhost:27017/vendor_management_dev'
    UPLOAD_FOLDER = os.path.abspath('app/static/uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    DEBUG = True
