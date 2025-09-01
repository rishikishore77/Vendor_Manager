from bson.objectid import ObjectId
from app.utils.database import Database


class VendingCompany:
    COLLECTION = 'vending_companies'

    @classmethod
    def add(cls, site_id, name):
        """Add a new vending company for a site"""
        doc = {
            'site_id': site_id,
            'name': name
        }
        inserted_id = Database.insert_one(cls.COLLECTION, doc)
        return str(inserted_id) if inserted_id else None

    @classmethod
    def get_all(cls, site_id):
        """Get all vending companies for a site"""
        return list(Database.find(cls.COLLECTION, {'site_id': site_id}))

    @classmethod
    def find_by_id(cls, company_id):
        """Find vending company by ID"""
        try:
            return Database.find_one(cls.COLLECTION, {'_id': ObjectId(company_id)})
        except:
            return None

    @classmethod
    def update(cls, company_id, update_data):
        """Update vending company fields"""
        try:
            return Database.update_one(cls.COLLECTION, {'_id': ObjectId(company_id)}, {'$set': update_data})
        except:
            return 0

    @classmethod
    def remove(cls, company_id):
        """Remove vending company from database"""
        try:
            return Database.delete_one(cls.COLLECTION, {'_id': ObjectId(company_id)})
        except:
            return 0
