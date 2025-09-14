from datetime import datetime
from app.models.attendance import Attendance
from app.models.mismatch import MismatchManagement
from app.models.timesheet import Timesheet
from app.models.user import User
from app.models.attendance_offset import AttendanceOffset

def calculate_hours_for_status(status):
    """Calculate hours based on attendance status"""
    status = status.lower()
    if status in ['in office full day', 'work from home full', 'office half + work from home half']:
        return 8
    elif status in ['office half + leave half', 'work from home half + leave half']:
        return 4
    else:
        return 0

def generate_timesheets_for_month(site_id, manager_id, month_year, vending_company_id=None):
    """Generate detailed timesheets for vendors"""
    year, month = map(int, month_year.split('-'))

    # Filter vendors by site, optionally manager and vending company
    query = {'site_id': site_id, 'role': 'vendor'}
    if manager_id:
        query['manager_id'] = manager_id
    if vending_company_id:
        query['vending_company_id'] = vending_company_id
        
    vendors = User.find(query)

    for vendor in vendors:
        vendor_id = vendor['_id']

        # Get attendance records for the month
        attendance_records = Attendance.find_by_user_and_month(str(vendor_id), year, month)
        
        # Get mismatches for the month
        mismatches = MismatchManagement.find_by_user_and_month(str(vendor_id), month_year)

        # Get offsets from previous months
        offsets_summary = AttendanceOffset.get_offsets_summary(vendor_id, month_year)

        # Calculate worked dates and hours
        work_dates_hours = {}
        for record in attendance_records:
            status = record.get('status', '')
            date = record.get('date')
            hours = calculate_hours_for_status(status)
            if hours > 0:
                work_dates_hours[date] = hours

        # Handle mismatches according to status
        mismatch_leave_days = 0
        for mismatch in mismatches:
            mismatch_status = mismatch.get('status', '')
            date = mismatch.get('date')
            
            if mismatch_status == 'pending':
                # Consider as leave (8 hours lost)
                mismatch_leave_days += 1
                if date in work_dates_hours:
                    del work_dates_hours[date]  # Remove work hours for this date
                    
            elif mismatch_status == 'vendor_updated':
                # Consider what vendor submitted
                vendor_data = mismatch.get('vendor_data', {})
                vendor_status = vendor_data.get('status', '')
                if vendor_status:
                    hours = calculate_hours_for_status(vendor_status)
                    work_dates_hours[date] = hours

        # Get offsets (from previous months or late corrections)
        offset_dates_hours = offsets_summary.get('dates_hours', {})
        total_offset_hours = offsets_summary.get('total_hours', 0)

        # Create or update detailed timesheet
        Timesheet.create_or_update_detailed(
            vendor_id=vendor_id,
            vending_company_id=vendor.get('vending_company_id'),
            month_year=month_year,
            work_dates_hours=work_dates_hours,
            mismatch_leave_days=mismatch_leave_days,
            offset_dates_hours=offset_dates_hours,
            total_offset_hours=total_offset_hours
        )

    print(f"Timesheets generated for {len(vendors)} vendors for {month_year}")

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

