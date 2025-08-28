"""Attendance model"""
from app.utils.database import Database
from bson.objectid import ObjectId
from datetime import datetime

class Attendance:
    """Attendance model"""

    COLLECTION = 'attendance'

    STATUSES = [
        'In office full day',
        'Office half + work from home half',
        'Office half + leave half',
        'Work from home full',
        'Holiday',
        'Leave'
    ]

    @staticmethod
    def create(user_id, date, status, comments='', site_id=None):
        """Create attendance record"""
        attendance_data = {
            'user_id': user_id,
            'date': date,
            'status': status,
            'approval_status': 'Pending',
            'comments': comments,
            'rejection_reason': '',
            'site_id': site_id
        }

        attendance_id = Database.insert_one(Attendance.COLLECTION, attendance_data)
        return str(attendance_id) if attendance_id else None

    @staticmethod
    def find_by_user_and_date(user_id, date):
        """Find attendance record by user and date"""
        return Database.find_one(Attendance.COLLECTION, {
            'user_id': user_id,
            'date': date
        })

    @staticmethod
    def find_by_user_and_month(user_id, year, month):
        """Find all attendance records for a user in a specific month"""
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year+1}-01-01"
        else:
            end_date = f"{year}-{month+1:02d}-01"

        return Database.find(Attendance.COLLECTION, {
            'user_id': user_id,
            'date': {'$gte': start_date, '$lt': end_date}
        }, sort=[('date', 1)])

    @staticmethod
    def get_pending_approvals(manager_id):
        """Get pending attendance records for manager's team"""
        from app.models.user import User
        vendors = User.get_vendors_by_manager(manager_id)
        vendor_ids = [str(v['_id']) for v in vendors]

        if not vendor_ids:
            return []

        records = Database.find(Attendance.COLLECTION, {
            'user_id': {'$in': vendor_ids},
            'approval_status': 'Pending'
        }, sort=[('date', -1)])

        # Add user info to records
        for record in records:
            user = User.find_by_id(record['user_id'])
            record['user_info'] = user

        return records

    @staticmethod
    def update_status(user_id, date, status, comments='', site_id=None):
        """Update or create attendance status"""
        existing = Attendance.find_by_user_and_date(user_id, date)

        if existing:
            update_data = {
                'status': status,
                'comments': comments,
                'approval_status': 'Pending'
            }

            result = Database.update_one(
                Attendance.COLLECTION,
                {'_id': existing['_id']},
                {'$set': update_data}
            )
            return result > 0
        else:
            attendance_id = Attendance.create(user_id, date, status, comments, site_id)
            return attendance_id is not None

    @staticmethod
    def get_monthly_summary(user_id, year, month):
        """Get monthly attendance summary"""
        records = Attendance.find_by_user_and_month(user_id, year, month)

        summary = {
            'total_days': len(records),
            'present': 0,
            'wfh': 0,
            'leave': 0,
            'pending': 0,
            'approved': 0,
            'rejected': 0
        }

        for record in records:
            status = record['status'].lower()

            if 'office' in status:
                summary['present'] += 0.5 if 'half' in status else 1
            elif 'work from home' in status:
                summary['wfh'] += 0.5 if 'half' in status else 1
            elif 'leave' in status:
                summary['leave'] += 1

            if record['approval_status'] == 'Pending':
                summary['pending'] += 1
            elif record['approval_status'] == 'Approved':
                summary['approved'] += 1
            elif record['approval_status'] == 'Rejected':
                summary['rejected'] += 1

        return summary
