from app.utils.database import Database
from datetime import datetime

class Holiday:
    COLLECTION = 'holidays'

    @staticmethod
    def add(site_id, date, name):
        return Database.insert_one(Holiday.COLLECTION, {
            "site_id": site_id,
            "date": date,
            "name": name
        })

    @staticmethod
    def get_all(site_id):
        return Database.find(Holiday.COLLECTION, {"site_id": site_id})

    @staticmethod
    def delete(site_id, holiday_id):
        from bson.objectid import ObjectId
        return Database.delete_one(Holiday.COLLECTION, {"site_id": site_id, "_id": ObjectId(holiday_id)})
