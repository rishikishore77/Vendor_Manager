from app.utils.database import Database
from datetime import datetime


class Holiday:
    COLLECTION = 'holidays'

    @staticmethod
    def add(site_id, date, name):
        return Database.insert_one(Holiday.COLLECTION, {
            "site_id": site_id,
            "date": date,  # Expected format: YYYY-MM-DD
            "name": name
        })

    @staticmethod
    def get_all(site_id):
        return Database.find(Holiday.COLLECTION, {"site_id": site_id})

    @staticmethod
    def get_year(site_id, year):
        # Get holidays only for the given year (assumes 'date' is in format 'YYYY-MM-DD')
        year_str = str(year)
        return Database.find(Holiday.COLLECTION, {
            "site_id": site_id,
            "date": {"$regex": f"^{year_str}-"}
        })

    @staticmethod
    def delete(site_id, holiday_id):
        from bson.objectid import ObjectId
        return Database.delete_one(Holiday.COLLECTION, {"site_id": site_id, "_id": ObjectId(holiday_id)})
