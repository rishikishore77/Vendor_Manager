# app/models/swipe_data.py
from app.utils.database import Database
from bson.objectid import ObjectId
from datetime import datetime

class SwipeData:
    COLLECTION = "swipe_data"

    @classmethod
    def create(cls, employee_code, user_id, date, login, logout, total_hours, month_year):
        """Create swipe data record"""
        swipe_data = {
            "employee_code": employee_code,
            "user_id": ObjectId(user_id),
            "date": date,
            "login": login,
            "logout": logout,
            "total_hours": float(total_hours),
            "month_year": month_year,
            "uploaded_at": datetime.utcnow()
        }
        return Database.insert_one(cls.COLLECTION, swipe_data)

    @classmethod
    def find_by_user_date(cls, user_id, date):
        """Find swipe data for user on specific date"""
        return Database.find_one(
            cls.COLLECTION, 
            {"user_id": ObjectId(user_id), "date": date}
        )

    @classmethod
    def find_by_month(cls, user_id, month_year):
        """Find all swipe data for user in a month"""
        return Database.find(
            cls.COLLECTION,
            {"user_id": ObjectId(user_id), "month_year": month_year},
            sort=[("date", 1)]
        )

    @classmethod
    def bulk_insert(cls, swipe_records):
        """Bulk insert swipe data records"""
        if not swipe_records:
            return 0

        collection = Database.get_collection(cls.COLLECTION)
        try:
            result = collection.insert_many(swipe_records)
            return len(result.inserted_ids)
        except Exception as e:
            print(f"Error in bulk insert: {e}")
            return 0

    @classmethod
    def delete_by_month(cls, month_year):
        """Delete all swipe data for a month (for re-upload)"""
        collection = Database.get_collection(cls.COLLECTION)
        result = collection.delete_many({"month_year": month_year})
        return result.deleted_count
