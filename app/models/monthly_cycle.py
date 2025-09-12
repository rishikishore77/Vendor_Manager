# app/models/monthly_cycle.py
from app.utils.database import Database
from bson.objectid import ObjectId
from datetime import datetime, timedelta

class MonthlyCycle:
    COLLECTION = "monthly_cycles"

    STATUSES = ["active", "processing", "closed"]
    DATA_TYPES = ["swipe_data", "wfh_data", "leave_data"]

    @classmethod
    def create_cycle(cls, site_id, month_year, deadline_days=14):
        """Create a new monthly cycle"""

        # Parse year and month
        year, month = map(int, month_year.split('-'))

        # Calculate next month and year
        if month == 12:
            month = 1
            year = year + 1
        else:
            month = month + 1

        deadline = datetime(year, month, deadline_days)
        cycle_data = {
            "site_id": ObjectId(site_id),
            "month_year": month_year,
            "status": "active",
            "data_upload_status": {
                "swipe_data": {"uploaded": False, "uploaded_at": None},
                "wfh_data": {"uploaded": False, "uploaded_at": None},
                "leave_data": {"uploaded": False, "uploaded_at": None}
            },
            "mismatch_deadline": deadline,
            "workdays_calculated": False,
            "created_at": datetime.utcnow()
        }
        return Database.insert_one(cls.COLLECTION, cycle_data)

    @classmethod
    def get_all(cls, site_id):
        """Get all cycles for a site"""
        return Database.find(
            cls.COLLECTION, 
            {"site_id": ObjectId(site_id)}, 
            sort=[("month_year", -1)]
        )

    @classmethod
    def get_by_month(cls, site_id, month_year):
        """Get cycle by site and month"""
        return Database.find_one(
            cls.COLLECTION, 
            {"site_id": ObjectId(site_id), "month_year": month_year}
        )

    @classmethod
    def update_upload_status(cls, site_id, month_year, data_type):
        """Update upload status for a data type"""
        update_data = {
            f"data_upload_status.{data_type}.uploaded": True,
            f"data_upload_status.{data_type}.uploaded_at": datetime.utcnow()
        }
        return Database.update_one(
            cls.COLLECTION,
            {"site_id": ObjectId(site_id), "month_year": month_year},
            {"$set": update_data}
        )

    @classmethod
    def update_status(cls, site_id, month_year, status):
        """Update cycle status"""
        return Database.update_one(
            cls.COLLECTION,
            {"site_id": ObjectId(site_id), "month_year": month_year},
            {"$set": {"status": status, "updated_at": datetime.utcnow()}}
        )

    @classmethod
    def mark_workdays_calculated(cls, site_id, month_year):
        """Mark workdays as calculated"""
        return Database.update_one(
            cls.COLLECTION,
            {"site_id": ObjectId(site_id), "month_year": month_year},
            {"$set": {"workdays_calculated": True, "finalized_at": datetime.utcnow()}}
        )

    @classmethod
    def is_all_data_uploaded(cls, site_id, month_year):
        """Check if all data types are uploaded"""
        cycle = cls.get_by_month(site_id, month_year)
        if not cycle:
            return False

        upload_status = cycle.get('data_upload_status', {})
        return all(
            upload_status.get(data_type, {}).get('uploaded', False)
            for data_type in cls.DATA_TYPES
        )
