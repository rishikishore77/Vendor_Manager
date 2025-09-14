from bson.objectid import ObjectId
from datetime import datetime
from app.utils.database import Database

class AttendanceOffset:
    COLLECTION = 'attendance_offsets'

    @classmethod
    def create_offset(cls, vendor_id, month_year, attendance_id, date, hours, source="late_attendance_update"):
        """Create offset record for attendance changes after timesheet generation"""
        data = {
            "vendor_id": ObjectId(vendor_id),
            "month_year": month_year,
            "attendance_id": ObjectId(attendance_id) if attendance_id else None,
            "date": date,
            "hours": hours,
            "source": source,
            "created_at": datetime.utcnow()
        }
        return Database.insert_one(cls.COLLECTION, data)

    @classmethod
    def get_offsets_for_vendor(cls, vendor_id, month_year):
        """Get all offsets for a vendor in a specific month"""
        return list(Database.find(cls.COLLECTION, {
            "vendor_id": ObjectId(vendor_id),
            "month_year": month_year
        }))

    @classmethod
    def get_offsets_summary(cls, vendor_id, month_year):
        """Get offset summary with dates and hours"""
        offsets = cls.get_offsets_for_vendor(vendor_id, month_year)
        dates_hours = {}
        total_hours = 0
        
        for offset in offsets:
            date = offset['date']
            hours = offset['hours']
            dates_hours[date] = dates_hours.get(date, 0) + hours
            total_hours += hours
            
        return {
            'dates_hours': dates_hours,
            'total_hours': total_hours,
            'details': offsets
        }
