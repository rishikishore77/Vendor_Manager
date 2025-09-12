# app/models/leave_data.py
from app.utils.database import Database
from bson.objectid import ObjectId
from datetime import datetime, date as date_obj
import re

class LeaveData:
    COLLECTION = "leave_data"

    @classmethod
    def create(cls, employee_code, user_id, start_date, end_date, leave_type, duration, is_full_day, month_year):
        """Create leave data record"""
        leave_data = {
            "employee_code": employee_code,
            "user_id": ObjectId(user_id),
            "start_date": start_date,
            "end_date": end_date,
            "leave_type": leave_type,
            "duration": float(duration),
            "is_full_day": is_full_day,
            "month_year": month_year,
            "uploaded_at": datetime.utcnow()
        }
        return Database.insert_one(cls.COLLECTION, leave_data)

    @classmethod
    def find_by_user_date(cls, user_id, date):
        """Find leave data for user on specific date"""
        return Database.find_one(
            cls.COLLECTION, 
            {
                "user_id": ObjectId(user_id),
                "start_date": {"$lte": date},
                "end_date": {"$gte": date}
            }
        )

    @classmethod
    def find_by_month(cls, user_id, month_year):
        """Find all leave data for user in a month"""
        year, month = month_year.split('-')
        start_date = f"{year}-{month}-01"
        end_date = f"{year}-{month}-31"  # Simplified

        return Database.find(
            cls.COLLECTION,
            {
                "user_id": ObjectId(user_id),
                "$or": [
                    {"start_date": {"$gte": start_date, "$lte": end_date}},
                    {"end_date": {"$gte": start_date, "$lte": end_date}},
                    {"start_date": {"$lte": start_date}, "end_date": {"$gte": end_date}}
                ]
            },
            sort=[("start_date", 1)]
        )

    @classmethod
    def bulk_insert(cls, leave_records):
        """Bulk insert leave data records"""
        if not leave_records:
            return 0

        collection = Database.get_collection(cls.COLLECTION)
        try:
            result = collection.insert_many(leave_records)
            return len(result.inserted_ids)
        except Exception as e:
            print(f"Error in bulk insert: {e}")
            return 0

    @classmethod
    def delete_by_month(cls, month_year):
        """Delete all leave data for a month (for re-upload)"""
        collection = Database.get_collection(cls.COLLECTION)
        result = collection.delete_many({"month_year": month_year})
        return result.deleted_count

    @classmethod
    def parse_date_range(cls, start_date_str, end_date_str):
        """Parse date range and return list of individual dates"""
        try:
            # Handle different date formats
            start_date = datetime.strptime(start_date_str, "%m/%d/%Y").date()
            end_date = datetime.strptime(end_date_str, "%m/%d/%Y").date()

            dates = []
            current_date = start_date
            while current_date <= end_date:
                dates.append(current_date.strftime("%Y-%m-%d"))
                current_date += datetime.timedelta(days=1)

            return dates
        except ValueError:
            # Try alternative formats
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

                dates = []
                current_date = start_date
                while current_date <= end_date:
                    dates.append(current_date.strftime("%Y-%m-%d"))
                    current_date += datetime.timedelta(days=1)

                return dates
            except ValueError:
                return []
