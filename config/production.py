import os
from datetime import timedelta

class ProductionConfig:
    """Production configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24)
    MONGO_URI = os.environ.get('MONGO_URI') or 'mongodb://localhost:27017/vendor_management_prod'
    UPLOAD_FOLDER = os.path.abspath('app/static/uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    DEBUG = False
