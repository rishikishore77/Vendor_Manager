from datetime import datetime
from app.models.attendance import Attendance
from app.models.mismatch import MismatchManagement

def generate_timesheets_for_month(site_id, manager_id, year, month):
    month_year = f"{year}-{month:02d}"
    
    from app.models.user import User
    vendors = User.find({'site_id': site_id, 'manager_id': manager_id, 'role': 'vendor'})
    
    from app.models.timesheet import Timesheet

    for vendor in vendors:
        attendance_records = Attendance.find_by_user_and_month(vendor['_id'], year, month)
        mismatches = MismatchManagement.find_by_user_and_month(vendor['_id'], month_year)
        
        worked_days = 0
        mismatch_leave_days = 0
        
        for record in attendance_records:
            status = record.get('status', '').lower()
            if 'office' in status or 'work from home' in status:
                worked_days += 1
        
        for mismatch in mismatches:
            if mismatch.get('status') != 'manager_approved':
                mismatch_leave_days += 1
        
        Timesheet.create_or_update(vendor['_id'], month_year, worked_days, mismatch_leave_days)

def update_offset_for_late_changes(vendor_id, changed_month_year, offset_days):
    from app.models.timesheet import Timesheet
    
    year, month = map(int, changed_month_year.split('-'))
    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year
    next_month_year = f"{next_year}-{next_month:02d}"
    
    existing = Timesheet.find_one(vendor_id, next_month_year)
    if existing:
        new_offset = existing.get('offset_days', 0) + offset_days
        Timesheet.create_or_update(vendor_id, next_month_year, existing['worked_days'], existing['mismatch_leave_days'], new_offset)
    else:
        Timesheet.create_or_update(vendor_id, next_month_year, 0, 0, offset_days)

