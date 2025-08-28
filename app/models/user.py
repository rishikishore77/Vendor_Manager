"""User model"""
from app.utils.database import Database
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime


class User:
    """User model"""

    COLLECTION = 'users'

    @staticmethod
    def create(username, password, role, name, site_id, **kwargs):
        """Create a new user"""
        user_data = {
            'username': username,
            'password_hash': generate_password_hash(password),
            'role': role,
            'name': name,
            'site_id': site_id,
            'active': True
        }

        # Add role-specific fields
        if role == 'vendor':
            user_data.update({
                'vendor_company': kwargs.get('vendor_company'),
                'manager_id': kwargs.get('manager_id'),
                'employee_code': kwargs.get('employee_code'),
                'department': kwargs.get('department')
            })

        user_id = Database.insert_one(User.COLLECTION, user_data)
        return str(user_id) if user_id else None

    @staticmethod
    def find_by_username(username):
        """Find user by username"""
        return Database.find_one(User.COLLECTION, {'username': username, 'active': True})

    @staticmethod
    def find_by_id(user_id):
        """Find user by ID"""
        try:
            return Database.find_one(User.COLLECTION, {'_id': ObjectId(user_id), 'active': True})
        except:
            return None

    @staticmethod
    def verify_password(user, password):
        """Verify user password"""
        return check_password_hash(user['password_hash'], password)

    @staticmethod
    def get_vendors_by_manager(manager_id):
        """Get all vendors managed by a specific manager"""
        return Database.find(User.COLLECTION, {
            'role': 'vendor',
            'manager_id': manager_id,
            'active': True
        })

    @staticmethod
    def get_all_by_site(site_id, role=None):
        """Get all users in a site, optionally filtered by role"""
        query = {'site_id': site_id, 'active': True}
        if role:
            query['role'] = role
        return Database.find(User.COLLECTION, query)

    @staticmethod
    def deactivate(user_id):
        """Deactivate a user by setting active=False"""
        try:
            count = Database.update_one(
                User.COLLECTION,
                {'_id': ObjectId(user_id), 'active': True},
                {'$set': {'active': False}}
            )
            return count
        except Exception as e:
            # You may want to log error here based on your logger setup
            return 0
