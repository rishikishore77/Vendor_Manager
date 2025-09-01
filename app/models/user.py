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
            # Add assignment history (for new user, this is initial assignment)
            assignment_history = [{
                'department_id': kwargs.get('department_id'),
                'vendor_company_id': kwargs.get('vendor_company_id'),
                'from': datetime.utcnow(),
                'to': None
            }]
            user_data.update({
                'vendor_company_id': kwargs.get('vendor_company_id'),
                'manager_id': kwargs.get('manager_id'),
                'employee_code': kwargs.get('employee_code'),
                'department_id': kwargs.get('department_id'),
                'assignment_history': assignment_history
            })
        elif role == 'manager':
            user_data.update({
                'department_id': kwargs.get('department_id'),
                'subdepartment': kwargs.get('subdepartment')
            })

        user_id = Database.insert_one(User.COLLECTION, user_data)
        return str(user_id) if user_id else None

    @staticmethod
    def change_assignment(user_id, new_department_id, new_vendor_company_id):
        """
        Change vendor's department and company assignment and update assignment history.
        """
        user = Database.find_one(User.COLLECTION, {'_id': ObjectId(user_id)})
        if not user or user.get('role') != 'vendor':
            return False

        now = datetime.utcnow()
        history = user.get('assignment_history', [])

        # Close previous assignment if any
        if history and history[-1]['to'] is None:
            history[-1]['to'] = now

        # Add new assignment entry
        history.append({
            'department_id': new_department_id,
            'vendor_company_id': new_vendor_company_id,
            'from': now,
            'to': None
        })

        update_data = {
            'department_id': new_department_id,
            'vendor_company_id': new_vendor_company_id,
            'assignment_history': history
        }

        Database.update_one(User.COLLECTION, {'_id': ObjectId(user_id)}, {'$set': update_data})
        return True

    @staticmethod
    def find_by_username(username):
        """Find user by username (only active users)"""
        return Database.find_one(User.COLLECTION, {'username': username, 'active': True})

    @staticmethod
    def find_by_id(user_id):
        """Find user by ID (only active users)"""
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
        """Get all vendors managed by a specific manager (only active)"""
        return Database.find(User.COLLECTION, {
            'role': 'vendor',
            'manager_id': manager_id,
            'active': True
        })

    @staticmethod
    def get_all_by_site(site_id, role=None):
        """Get all active users in a site, optionally filtered by role"""
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

    @staticmethod
    def find(query):
        """
        Generic find method: support any MongoDB query.
        Use for admin filtering by name, manager, company, active/inactive, etc.
        Example:
            User.find({'site_id': sid, 'active': False})
            User.find({'role':'vendor', 'active': True, 'manager_id': X})
            User.find({'name': {'$regex': 'John', '$options': 'i'}})
        """
        return Database.find(User.COLLECTION, query)
