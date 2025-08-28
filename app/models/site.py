"""Site model"""
from app.utils.database import Database
from bson.objectid import ObjectId

class Site:
    """Site model"""

    COLLECTION = 'sites'

    @staticmethod
    def create(name, address, admin_user_id, **kwargs):
        """Create a new site"""
        site_data = {
            'name': name,
            'address': address,
            'admin_user_id': admin_user_id,
            'active': True
        }

        site_id = Database.insert_one(Site.COLLECTION, site_data)
        return str(site_id) if site_id else None

    @staticmethod
    def find_by_id(site_id):
        """Find site by ID"""
        try:
            return Database.find_one(Site.COLLECTION, {'_id': ObjectId(site_id), 'active': True})
        except:
            return None
