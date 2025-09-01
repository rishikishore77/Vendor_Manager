from datetime import datetime
from bson.objectid import ObjectId
from app.utils.database import Database


class Department:
    COLLECTION = 'departments'

    @classmethod
    def create(cls, site_id, name, subdepartment, manager_id=None):
        """Create a new department with optional initial manager assignment"""
        doc = {
            'site_id': site_id,
            'name': name,
            'subdepartment': subdepartment,
            'current_manager_id': None,
            'manager_history': []
        }
        if manager_id:
            doc['current_manager_id'] = manager_id
            doc['manager_history'].append({
                'manager_id': manager_id,
                'from': datetime.utcnow(),
                'to': None
            })
        inserted_id = Database.insert_one(cls.COLLECTION, doc)
        return str(inserted_id) if inserted_id else None

    @classmethod
    def get_all(cls, site_id):
        """Get all departments for a site"""
        return list(Database.find(cls.COLLECTION, {'site_id': site_id}))

    @classmethod
    def find_by_id(cls, dept_id):
        """Find a department by its ID"""
        try:
            return Database.find_one(cls.COLLECTION, {'_id': ObjectId(dept_id)})
        except:
            return None

    @classmethod
    def update(cls, dept_id, update_data):
        """Update department fields"""
        try:
            return Database.update_one(cls.COLLECTION, {'_id': ObjectId(dept_id)}, {'$set': update_data})
        except:
            return 0

    @classmethod
    def change_manager(cls, dept_id, new_manager_id):
        """Change the manager of a department and maintain assignment history"""
        dept = cls.find_by_id(dept_id)
        if not dept:
            return False
        now = datetime.utcnow()
        history = dept.get('manager_history', [])

        # Close previous manager assignment entry
        prev_manager_id = dept.get('current_manager_id')
        if prev_manager_id:
            for entry in history:
                if entry['manager_id'] == prev_manager_id and entry.get('to') is None:
                    entry['to'] = now

        # Add new manager assignment entry with open-ended 'to'
        history.append({
            'manager_id': new_manager_id,
            'from': now,
            'to': None
        })

        update_data = {
            'current_manager_id': new_manager_id,
            'manager_history': history
        }
        updated_count = cls.update(dept_id, update_data)
        return updated_count > 0
