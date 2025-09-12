# app/models/mismatch.py
from app.utils.database import Database
from bson.objectid import ObjectId
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class MismatchManagement:
    COLLECTION = "mismatches"

    MISMATCH_TYPES = {
        "pending_status": "Attendance status pending",
        "office_no_swipe": "In office full day - no swipe data",
        "office_short_swipe": "In office full day - insufficient hours",
        "half_office_wfh_no_swipe": "Office half + WFH half - no swipe data",
        "half_office_wfh_short_swipe": "Office half + WFH half - insufficient hours",
        "half_office_wfh_no_wfh": "Office half + WFH half - no WFH entry",
        "half_office_leave_no_swipe": "Office half + Leave half - no swipe data",
        "half_office_leave_short_swipe": "Office half + Leave half - insufficient hours",
        "half_office_leave_no_leave": "Office half + Leave half - no leave entry",
        "wfh_no_wfh": "Work from home full - no WFH entry",
        "leave_no_leave": "Leave - no leave entry"
    }

    STATUSES = ["pending", "vendor_updated", "manager_approved", "manager_rejected", "expired"]

    @classmethod
    def create_mismatch(cls, site_id, user_id, date, mismatch_type, original_status, 
                       expected_data, actual_data, deadline_days=7):
        """Create a new mismatch record"""
        deadline = datetime.utcnow() + timedelta(days=deadline_days)
        mismatch_data = {
            "site_id": ObjectId(site_id),
            "user_id": ObjectId(user_id),
            "date": date,
            "month_year": date[:7],  # YYYY-MM
            "mismatch_type": mismatch_type,
            "original_status": original_status,
            "expected_data": expected_data,
            "actual_data": actual_data,
            "status": "pending",
            "deadline": deadline,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        return Database.insert_one(cls.COLLECTION, mismatch_data)

    @classmethod
    def get_user_mismatches(cls, user_id, status=None):
        """Get all mismatches for a user"""
        query = {"user_id": ObjectId(user_id)}
        if status:
            query["status"] = status
        return Database.find(cls.COLLECTION, query, sort=[("date", 1)])

    @classmethod
    def get_team_mismatches(cls, manager_id):
        """Get all mismatches for a manager's team"""
        from app.models.user import User

        # Get team members
        team_members = User.get_vendors_by_manager(manager_id)
        team_user_ids = [ObjectId(str(member['_id'])) for member in team_members]

        # Get mismatches for team
        mismatches = Database.find(
            cls.COLLECTION, 
            {"user_id": {"$in": team_user_ids}}, 
            sort=[("date", -1)]
        )

        # Add user info to each mismatch
        user_map = {str(user['_id']): user for user in team_members}
        for mismatch in mismatches:
            mismatch['user_info'] = user_map.get(str(mismatch['user_id']))

        return mismatches

    @classmethod
    def resolve_mismatch(cls, mismatch_id, new_status, comments):
        """Vendor resolves a mismatch"""
        update_data = {
            "vendor_resolution": {
                "new_status": new_status,
                "comments": comments,
                "updated_at": datetime.utcnow()
            },
            "status": "vendor_updated",
            "updated_at": datetime.utcnow()
        }
        return Database.update_one(
            cls.COLLECTION, 
            {"_id": ObjectId(mismatch_id)}, 
            {"$set": update_data}
        )

    @classmethod
    def manager_action(cls, mismatch_id, action, comments):
        """Manager approves or rejects a mismatch resolution"""
        new_status = "manager_approved" if action == "approve" else "manager_rejected"

        update_data = {
            "manager_resolution": {
                "action": action,
                "comments": comments,
                "updated_at": datetime.utcnow()
            },
            "status": new_status,
            "updated_at": datetime.utcnow()
        }

        result = Database.update_one(
            cls.COLLECTION, 
            {"_id": ObjectId(mismatch_id)}, 
            {"$set": update_data}
        )

        # If approved, update the attendance record
        if action == "approve" and result > 0:
            mismatch = cls.get_by_id(mismatch_id)
            if mismatch and mismatch.get('vendor_resolution'):
                cls._update_attendance_final_status(mismatch)

        return result

    @classmethod
    def _update_attendance_final_status(cls, mismatch):
        """Update attendance record with final status after approval"""
        from app.models.attendance import Attendance

        Attendance.update_final_status(
            mismatch['user_id'], 
            mismatch['date'], 
            mismatch['status'],
            mismatch['_id']
        )

    @classmethod
    def get_by_id(cls, mismatch_id):
        """Get mismatch by ID"""
        try:
            return Database.find_one(cls.COLLECTION, {"_id": ObjectId(mismatch_id)})
        except:
            return None

    @classmethod
    def auto_resolve_expired(cls, mismatch_id, default_status):
        """Auto-resolve expired mismatch with default status"""
        update_data = {
            "vendor_resolution": {
                "new_status": default_status,
                "comments": "Auto-resolved due to deadline expiry",
                "updated_at": datetime.utcnow()
            },
            "status": "expired",
            "updated_at": datetime.utcnow()
        }

        result = Database.update_one(
            cls.COLLECTION, 
            {"_id": ObjectId(mismatch_id)}, 
            {"$set": update_data}
        )

        if result > 0:
            # Update attendance record
            from app.models.attendance import Attendance
            mismatch = cls.get_by_id(mismatch_id)
            if mismatch:
                Attendance.update_final_status(
                    mismatch['user_id'],
                    mismatch['date'],
                    default_status,
                    mismatch_id
                )

        return result

    @classmethod
    def count_user_mismatches(cls, user_id, status=None):
        """Count mismatches for a user"""
        query = {"user_id": ObjectId(user_id)}
        if status:
            query["status"] = status

        collection = Database.get_collection(cls.COLLECTION)
        return collection.count_documents(query)
    
    @classmethod
    def count_team_mismatches(cls, manager_id, status=None):
        """Count mismatches for a team"""
        from app.models.user import User

        # Get team members
        team_members = User.get_vendors_by_manager(manager_id)
        team_user_ids = [ObjectId(str(member['_id'])) for member in team_members]

        # Get mismatches for team
        query = {"user_id": {"$in": team_user_ids}}
        if status:
            query["status"] = status
        mismatches = Database.find(
            cls.COLLECTION, 
            query, 
            sort=[("date", -1)]
        )
        return len(mismatches)

    @classmethod
    def get_monthly_stats(cls, site_id, month_year):
        """Get monthly mismatch statistics"""
        collection = Database.get_collection(cls.COLLECTION)

        pipeline = [
            {"$match": {"site_id": ObjectId(site_id), "month_year": month_year}},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]

        results = collection.aggregate(pipeline)
        stats = {status: 0 for status in cls.STATUSES}

        for result in results:
            stats[result["_id"]] = result["count"]

        return stats
    
    @classmethod
    def count_site_mismatches(cls, site_id, status=None):
        query = {"site_id": ObjectId(site_id)}
        if status:
            query["status"] = status
        collection = Database.get_collection(cls.COLLECTION)
        return collection.count_documents(query)
    
    @classmethod
    def get_site_mismatches(cls, site_id, month_year=None, status=None, limit=None):
        query = {"site_id": ObjectId(site_id)}
        if month_year:
            query["month_year"] = month_year
        if status:
            query["status"] = status
        collection = Database.get_collection(cls.COLLECTION)
        cursor = collection.find(query)
        if limit:
            cursor = cursor.limit(limit)
        return list(cursor)
    
    @classmethod
    def delete_mismatches_by_month(cls, site_id, month_year):
        collection = Database.get_collection(cls.COLLECTION)
        collection.delete_many({"site_id": ObjectId(site_id), "month_year": month_year})  

    @staticmethod
    def find_one(query):
        try:
            collection = Database.get_collection(MismatchManagement.COLLECTION)
            return collection.find_one(query)
        except Exception as e:
            logger.error(f"Error in find_one: {e}")
            return None 

    @staticmethod
    def update_one(filter_query, update_doc):
        try:
            collection = Database.get_collection(MismatchManagement.COLLECTION)
            result = collection.update_one(filter_query, update_doc)
            return result.modified_count
        except Exception as e:
            logger.error(f"Error in update_one: {e}")
            return 0
        
    @classmethod
    def update_resolution(cls, mismatch_id, vendor_status, vendor_reason):
        update_data = {
            'status': 'vendor_updated',
            'vendor_status': vendor_status,
            'vendor_reason': vendor_reason,
            'updated_at': datetime.utcnow()
        }
        return Database.update_one(cls.COLLECTION, {'_id': ObjectId(mismatch_id)}, {'$set': update_data})
        
    @classmethod
    def update_resolution_status(cls, mismatch_id, status, manager_comments=None):
        update_data = {'status': status}
        if manager_comments is not None:
            update_data['manager_comments'] = manager_comments
        return Database.update_one(cls.COLLECTION, {"_id": ObjectId(mismatch_id)}, {"$set": update_data})





