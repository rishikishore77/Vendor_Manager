# app/utils/mismatch_processor.py
from datetime import datetime , time, timedelta
from bson import ObjectId
from app.models.mismatch import MismatchManagement
from app.models.attendance import Attendance
from app.models.monthly_cycle import MonthlyCycle
from app.models.swipe_data import SwipeData
from app.models.wfh_data import WFHData
from app.models.leave_data import LeaveData
from app.models.system_config import SystemConfig
from app.utils.database import Database
from app.enums.mismatch_types import MismatchType

class MismatchProcessor:
    """Process and detect mismatches between attendance and uploaded data"""

    @classmethod
    def detect_and_create_mismatches(cls, site_id, month_year):
        # Get monthly cycle upload status
        cycle = MonthlyCycle.get_by_month(site_id, month_year)
        if not cycle:
            # No cycle means no uploads yet; skip mismatch detection
            return 0

        upload_status = cycle.get('data_upload_status', {})
        swipe_uploaded = upload_status.get('swipe_data', {}).get('uploaded', False)
        wfh_uploaded = upload_status.get('wfh_data', {}).get('uploaded', False)
        leave_uploaded = upload_status.get('leave_data', {}).get('uploaded', False)

        # Get attendance records for the month
        attendance_records = Attendance.find({
            "site_id": site_id,
            "date": {"$regex": f"^{month_year}"}
        })

        mismatch_count = 0

        for record in attendance_records:
            mismatch = cls.check_record_for_mismatches(
                record, month_year,
                swipe_uploaded=swipe_uploaded,
                wfh_uploaded=wfh_uploaded,
                leave_uploaded=leave_uploaded
            )

            if mismatch:
                existing_mismatch = MismatchManagement.find_one({
                    'user_id': ObjectId(mismatch['user_id']),
                    'date': mismatch['date']
                })

                if existing_mismatch and existing_mismatch.get('mismatch_type') == mismatch.get('mismatch_type'):
                    # Do not update if the same mismatch already exists
                    pass
                elif existing_mismatch:
                    # Update existing mismatch
                    mismatch['status'] = 'pending'
                    MismatchManagement.update_one(
                        {'_id': existing_mismatch['_id']},
                        {'$set': mismatch}
                    )
                else:
                    MismatchManagement.create_mismatch(**mismatch)

                Attendance.mark_as_mismatch(record['_id'], True)
                mismatch_count += 1

        return mismatch_count

    @classmethod
    def check_record_for_mismatches(cls, attendance_record, month_year,
                                    swipe_uploaded=True,
                                    wfh_uploaded=True,
                                    leave_uploaded=True):
        """
        Check a single attendance record for mismatches,
        but only raise mismatches for data types that are uploaded
        """
        site_id = attendance_record['site_id']
        user_id = attendance_record['user_id']
        date = attendance_record['date']
        status = attendance_record['status']

        min_office_hours = SystemConfig.get_setting("minimum_office_hours", 4.0)
        min_half_office_hours = SystemConfig.get_setting("minimum_half_office_hours", 2.0)
        min_half_leave_hours = SystemConfig.get_setting("minimum_half_leave_hours", 3.0)
        min_full_leave_hours = SystemConfig.get_setting("minimum_full_leave_hours", 6.0)

        mismatch_types = []
        expected_data_sequence = []
        actual_data_sequence = []

        # Rule 1: Pending status always checked
        if status == "Pending":
            mismatch_types.append(MismatchType.PENDING_STATUS.value)
            expected_data_sequence.append({})
            actual_data_sequence.append({})

        # Rule 2: In office full day - only if swipe data uploaded
        elif status == "In office full day" and swipe_uploaded:
            swipe_data = SwipeData.find_by_user_date(user_id, date)
            if not swipe_data:
                mismatch_types.append(MismatchType.NO_SWIPE.value)
                expected_data_sequence.append({"swipe_hours": min_office_hours})
                actual_data_sequence.append({"swipe_hours": 0})
            elif swipe_data.get('total_hours', 0) < min_office_hours:
                mismatch_types.append(MismatchType.SHORT_SWIPE.value)
                expected_data_sequence.append({"swipe_hours": min_office_hours})
                actual_data_sequence.append({"swipe_hours": swipe_data.get('total_hours', 0)})

        # Rule 3: Office half + work from home half
        elif status == "Office half + work from home half":
            swipe_data = SwipeData.find_by_user_date(user_id, date) if swipe_uploaded else None
            wfh_data = WFHData.find_by_user_date(user_id, date) if wfh_uploaded else None

            if swipe_uploaded:
                if not swipe_data:
                    mismatch_types.append(MismatchType.NO_SWIPE.value)
                    expected_data_sequence.append({"swipe_hours": min_half_office_hours})
                    actual_data_sequence.append({"swipe_hours": 0})
                elif swipe_data.get('total_hours', 0) < min_half_office_hours:
                    mismatch_types.append(MismatchType.SHORT_HALF_SWIPE.value)
                    expected_data_sequence.append({"swipe_hours": min_half_office_hours})
                    actual_data_sequence.append({"swipe_hours": swipe_data.get('total_hours', 0)})

            if wfh_uploaded and not wfh_data:
                mismatch_types.append(MismatchType.NO_WFH.value)
                expected_data_sequence.append({"wfh_required": True})
                actual_data_sequence.append({"wfh_present": False})

        # Rule 4: Office half + leave half
        elif status == "Office half + leave half":
            swipe_data = SwipeData.find_by_user_date(user_id, date) if swipe_uploaded else None
            leave_data = LeaveData.find_by_user_date(user_id, date) if leave_uploaded else None

            if swipe_uploaded:
                if not swipe_data:
                    mismatch_types.append(MismatchType.NO_SWIPE.value)
                    expected_data_sequence.append({"swipe_hours": min_half_office_hours})
                    actual_data_sequence.append({"swipe_hours": 0})
                elif swipe_data.get('total_hours', 0) < min_half_office_hours:
                    mismatch_types.append(MismatchType.SHORT_HALF_SWIPE.value)
                    expected_data_sequence.append({"swipe_hours": min_half_office_hours})
                    actual_data_sequence.append({"swipe_hours": swipe_data.get('total_hours', 0)})

            if leave_uploaded:
                leave_hours = cls.total_leave_hours_in_window(user_id, date)
                if leave_hours < min_half_leave_hours and leave_hours > 0:
                    mismatch_types.append(MismatchType.SHORT_HALF_LEAVE.value)
                    expected_data_sequence.append({"leave_hours_6AM_to_7PM": 3.0})
                    actual_data_sequence.append({"leave_hours_present_6AM_to_7PM": leave_hours})
                elif leave_hours == 0:
                    mismatch_types.append(MismatchType.NO_LEAVE.value)
                    expected_data_sequence.append({"leave_hours_6AM_to_7PM": 3.0})
                    actual_data_sequence.append({"leave_hours_present_6AM_to_7PM": 0})

        # Rule 5: Work from home full
        elif status == "Work from home full":
            wfh_data = WFHData.find_by_user_date(user_id, date) if wfh_uploaded else None
            if wfh_uploaded and not wfh_data:
                mismatch_types.append(MismatchType.NO_WFH.value)
                expected_data_sequence.append({"wfh_required": True})
                actual_data_sequence.append({"wfh_present": False})

        # Rule 6: Leave
        elif status == "Leave":
            leave_data = LeaveData.find_by_user_date(user_id, date) if leave_uploaded else None
            if leave_uploaded:
                leave_hours = cls.total_leave_hours_in_window(user_id, date)
                if leave_hours < min_full_leave_hours and leave_hours > 0:
                    mismatch_types.append(MismatchType.SHORT_LEAVE.value)
                    expected_data_sequence.append({"leave_hours_6AM_to_7PM": 6.0})
                    actual_data_sequence.append({"leave_hours_present_6AM_to_7PM": leave_hours})
                elif leave_hours == 0:
                    mismatch_types.append(MismatchType.NO_LEAVE.value)
                    expected_data_sequence.append({"leave_hours_6AM_to_7PM": 6.0})
                    actual_data_sequence.append({"leave_hours_present_6AM_to_7PM": 0})

        # Rule 7: WFH half + leave half
        elif status == "Work from home half + leave half":
            wfh_data = WFHData.find_by_user_date(user_id, date) if wfh_uploaded else None
            leave_data = LeaveData.find_by_user_date(user_id, date) if leave_uploaded else None
            if wfh_uploaded and not wfh_data:
                mismatch_types.append(MismatchType.NO_WFH.value)
                expected_data_sequence.append({"wfh_required": True})
                actual_data_sequence.append({"wfh_present": False})

            if leave_uploaded:
                leave_hours = cls.total_leave_hours_in_window(user_id, date)
                if leave_hours < min_half_leave_hours and leave_hours > 0:
                    mismatch_types.append(MismatchType.SHORT_HALF_LEAVE.value)
                    expected_data_sequence.append({"leave_hours_6AM_to_7PM": 3.0})
                    actual_data_sequence.append({"leave_hours_present_6AM_to_7PM": leave_hours})
                elif leave_hours == 0:
                    mismatch_types.append(MismatchType.NO_LEAVE.value)
                    expected_data_sequence.append({"leave_hours_6AM_to_7PM": 3.0})
                    actual_data_sequence.append({"leave_hours_present_6AM_to_7PM": 0})

        if mismatch_types:
            return {
                "site_id": site_id,
                "user_id": user_id,
                "date": date,
                "mismatch_type": mismatch_types,
                "original_status": status,
                "expected_data": expected_data_sequence,
                "actual_data": actual_data_sequence
            }
        else:
            return None
        
    @classmethod
    def calculate_leave_hours_in_window(cls, leave, date):
        window_start = datetime.combine(date.date(), time(6, 0))  # 6:00 AM
        window_end = datetime.combine(date.date(), time(19, 0))   # 7:00 PM

        start_time_str = leave.get('start_time', '00:00')
        end_time_str = leave.get('end_time', '23:59')

        leave_start_dt = datetime.combine(
            datetime.strptime(leave['start_date'], "%Y-%m-%d").date(),
            datetime.strptime(start_time_str, '%H:%M:%S').time()
        )
        leave_end_dt = datetime.combine(
            datetime.strptime(leave['end_date'], "%Y-%m-%d").date(),
            datetime.strptime(end_time_str, '%H:%M:%S').time()
        )

        actual_start = max(leave_start_dt, window_start)
        actual_end = min(leave_end_dt, window_end)

        overlap_seconds = (actual_end - actual_start).total_seconds()
        return max(overlap_seconds, 0) / 3600  # hours

    @classmethod
    def total_leave_hours_in_window(cls, user_id, date_str):
        date = datetime.strptime(date_str, "%Y-%m-%d")
        leaves = Database.find(
            LeaveData.COLLECTION,
            {
                "user_id": ObjectId(user_id),
                "start_date": {"$lte": date_str},
                "end_date": {"$gte": date_str}
            }
        )
        total_hours = 0
        for leave in leaves:
            total_hours += cls.calculate_leave_hours_in_window(leave, date)
        return total_hours