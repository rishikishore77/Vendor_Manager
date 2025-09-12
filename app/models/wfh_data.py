# app/models/wfh_data.py
from app.utils.database import Database
from bson.objectid import ObjectId
from datetime import datetime

class WFHData:
    COLLECTION = "wfh_data"

    @classmethod
    def create(cls, employee_code, user_id, start_date, end_date, duration, month_year):
        """Create WFH data record"""
        wfh_data = {
            "employee_code": employee_code,
            "user_id": ObjectId(user_id),
            "start_date": start_date,
            'end_date': end_date,
            "duration": float(duration),
            "month_year": month_year,
            "uploaded_at": datetime.utcnow()
        }
        return Database.insert_one(cls.COLLECTION, wfh_data)

    @classmethod
    def find_by_user_date(cls, user_id, date_str):
        """
        Find WFH data for user covering a specific date
        where start_date <= date <= end_date
        """
        return Database.find_one(
            cls.COLLECTION,
            {
                "user_id": ObjectId(user_id),
                "start_date": {"$lte": date_str},
                "end_date": {"$gte": date_str}
            }
        )

    @classmethod
    def find_by_month(cls, user_id, month_year):
        """Find all WFH data for user in a month"""
        return Database.find(
            cls.COLLECTION,
            {"user_id": ObjectId(user_id), "month_year": month_year},
            sort=[("date", 1)]
        )

    @classmethod
    def bulk_insert(cls, wfh_records):
        """Bulk insert WFH data records"""
        if not wfh_records:
            return 0

        collection = Database.get_collection(cls.COLLECTION)
        try:
            result = collection.insert_many(wfh_records)
            return len(result.inserted_ids)
        except Exception as e:
            print(f"Error in bulk insert: {e}")
            return 0

    @classmethod
    def delete_by_month(cls, month_year):
        """Delete all WFH data for a month (for re-upload)"""
        collection = Database.get_collection(cls.COLLECTION)
        result = collection.delete_many({"month_year": month_year})
        return result.deleted_count
