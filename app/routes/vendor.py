"""Vendor routes"""
from bson import ObjectId
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models.mismatch import MismatchManagement
from app.models.monthly_cycle import MonthlyCycle
from app.models.timesheet import Timesheet
from app.models.user import User
from app.models.holiday import Holiday
from app.models.attendance import Attendance
from app.utils.database import Database
from app.utils.helpers import login_required, role_required, get_month_calendar, is_working_day
from datetime import datetime, date, timedelta
import calendar
import logging

from app.utils.mismatch_processor import MismatchProcessor

logger = logging.getLogger(__name__)
vendor_bp = Blueprint('vendor', __name__)

def get_vendor_attendance_edit_range(today=None):
    if today is None:
        today = datetime.now()
    
    start_of_this_month = today.replace(day=1)
    start_of_last_month = (start_of_this_month - timedelta(days=1)).replace(day=1)
    
    # Allowed editing ends on today if day ≤14, else 14th of next month
    if today.day <= 15:
        edit_end_date = today.date()
    else:
        if today.month == 12:
            edit_end_date = datetime(today.year + 1, 1, 15).date()
        else:
            edit_end_date = datetime(today.year, today.month + 1, 15).date()
    
    return start_of_last_month.date(), edit_end_date

def calculate_hours_for_status(status):
    """Calculate hours based on attendance status"""
    status = status.lower()
    if status in ['in office full day', 'work from home full', 'office half + work from home half']:
        return 8
    elif status in ['office half + leave half', 'work from home half + leave half']:
        return 4
    else:
        return 0

@vendor_bp.route('/dashboard')
@login_required
@role_required('vendor')
def dashboard():
    user_id = session['user_id']
    site_id = session['site_id']

    try:
        today = datetime.now()
        today_str = today.strftime('%Y-%m-%d')

        # Attendance marking allowed date range
        start_date, end_date = get_vendor_attendance_edit_range(today)
        allowed_range = {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
        }

        # Fetch holiday list for current site and year
        holidays_list = Holiday.get_year(site_id, today.year) or []
        holiday_dates = [h['date'] for h in holidays_list]

        # Get today's attendance status
        today_attendance = Attendance.find_by_user_and_date(user_id, today_str)

        # Check if today is working day (weekday + not holiday)
        is_today_working = today.weekday() < 5 and (today_str not in holiday_dates)

        # Get monthly summary (Assumed dictionary result)
        monthly_summary = Attendance.get_monthly_summary(user_id, today.year, today.month)

        user_timesheets = Timesheet.get_latest_timesheet(user_id)
        timesheet_locked_month = user_timesheets['month_year'] if user_timesheets else None

        # Get mismatch stats for vendor
        mismatch_count = MismatchManagement.count_user_mismatches(user_id)
        urgent_mismatch_count = (
            MismatchManagement.count_user_mismatches(user_id, status='pending') +
            MismatchManagement.count_user_mismatches(user_id, status='manager_rejected')
        )

        stats = {
            'mismatch_count': mismatch_count,
            'urgent_mismatch_count': urgent_mismatch_count,
            'pending_count': 0,  # Add actual logic if needed
            'total_days': (
                monthly_summary.get('present', 0) +
                monthly_summary.get('wfh', 0) +
                monthly_summary.get('leave', 0)
            ) if monthly_summary else 0
        }

        return render_template('vendor/dashboard.html',
                               today_attendance=today_attendance,
                               is_today_working=is_today_working,
                               monthly_summary=monthly_summary,
                               today=today_str,
                               stats=stats,
                               allowed_range=allowed_range,
                               holidays=holiday_dates,
                               timesheet_locked_month=timesheet_locked_month)
    
                       
    except Exception as e:
        logger.error(f"Vendor dashboard error: {e}")
        flash('Error loading dashboard', 'error')
        return render_template('vendor/dashboard.html',
                               today_attendance=None,
                               is_today_working=True,
                               monthly_summary={},
                               today=today_str,
                               stats={},
                               allowed_range={'start_date': today_str, 'end_date': today_str},
                               holidays=[],
                               timesheet_locked_months=[])


@vendor_bp.route('/my-timesheets')
@login_required
@role_required('vendor')
def my_timesheets():
    from app.models.timesheet import Timesheet
    from io import BytesIO
    import pandas as pd
    from flask import send_file
    
    user_id = session['user_id']
    month_year = request.args.get('month_year')
    
    filters = {
        'vendor_id': user_id,
        'month_year': month_year
    }
    
    # Build query for vendor's timesheets
    query = {'vendor_id': ObjectId(user_id)}
    if month_year:
        query['month_year'] = month_year
    
    timesheets = list(Database.find(Timesheet.COLLECTION, query, sort=[('month_year', -1)]))
    
    # Check for export request
    if 'export' in request.args:
        export_data = []
        for ts in timesheets:
            work_dates = ts.get('work_dates_hours', {})
            offset_dates = ts.get('offset_dates_hours', {})
            
            for date, hours in work_dates.items():
                export_data.append({
                    'Month-Year': ts['month_year'],
                    'Date': date,
                    'Hours Worked': hours,
                    'Type': 'Work'
                })
            
            for date, hours in offset_dates.items():
                export_data.append({
                    'Month-Year': ts['month_year'],
                    'Date': date,
                    'Hours Worked': hours,
                    'Type': 'Offset'
                })
        
        df = pd.DataFrame(export_data)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='My Timesheets')
        output.seek(0)
        
        filename = f'my_timesheets_{month_year or "all"}.xlsx'
        return send_file(output, 
                        download_name=filename,
                        as_attachment=True,
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    
    return render_template('vendor/my_timesheets.html',
                           timesheets=timesheets,
                           filters=filters)

@vendor_bp.route('/mark_attendance', methods=['POST'])
@login_required
@role_required('vendor')
def mark_attendance():
    user_id = session['user_id']
    site_id = session['site_id']

    date_str = request.form.get('date')
    status = request.form.get('status')
    comments = request.form.get('comments', '')

    # Validate required fields
    if not date_str or not status:
        flash('Date and status are required', 'error')
        return redirect(url_for('vendor.dashboard'))

    # Validate date format
    try:
        attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid date format', 'error')
        return redirect(url_for('vendor.dashboard'))

    # Check if date within allowed attendance edit range
    start_date, end_date = get_vendor_attendance_edit_range()
    if attendance_date < start_date or attendance_date > end_date:
        flash(f'Attendance date must be between {start_date} and {end_date}', 'error')
        return redirect(url_for('vendor.dashboard'))

    month_year = date_str[:7]

    # 1. Block if unresolved mismatch exists
    existing_mismatch = MismatchManagement.find_one({
        'user_id': ObjectId(user_id),
        'date': date_str
    })

    if existing_mismatch and existing_mismatch.get('status') not in ['manager_approved', 'resolved']:
        flash('Attendance for this date has an unresolved mismatch. Please resolve it before making changes.', 'danger')
        return redirect(url_for('vendor.dashboard'))

    # 2. Check if timesheet is generated for this month
    from app.models.monthly_cycle import MonthlyCycle
    from app.models.attendance_offset import AttendanceOffset
    
    if MonthlyCycle.is_timesheet_generated(site_id, month_year):
        # Create offset record for late attendance update
        existing_attendance = Attendance.find_by_user_and_date(user_id, date_str)
        attendance_id = existing_attendance['_id'] if existing_attendance else None
        
        hours = calculate_hours_for_status(status)
        AttendanceOffset.create_offset(
            vendor_id=user_id,
            month_year=month_year,
            attendance_id=attendance_id,
            date=date_str,
            hours=hours,
            source="late_attendance_update"
        )
        
        flash('Timesheet already generated for this month. Your attendance change has been recorded as an offset for next month.', 'warning')

    # 3. Check if monthly cycle exists and mismatch processed flag
    cycle = MonthlyCycle.get_by_month(site_id, month_year)
    mismatch_processed = False
    if cycle:
        upload_status = cycle.get('data_upload_status', {})
        swipe_uploaded = upload_status.get('swipe_data', {}).get('uploaded', False)
        wfh_uploaded = upload_status.get('wfh_data', {}).get('uploaded', False)
        leave_uploaded = upload_status.get('leave_data', {}).get('uploaded', False)
        mismatch_processed = upload_status.get('mismatch_data', {}).get('processed', False)

    # Prepare record for mismatch check
    record = {
        "site_id": site_id,
        "user_id": user_id,
        "date": date_str,
        "status": status,
        "comments": comments
    }

    # 4. Run mismatch detection if processed flag true
    if mismatch_processed:
        mismatch_check = MismatchProcessor.check_record_for_mismatches(
            record, month_year,
            swipe_uploaded=swipe_uploaded,
            wfh_uploaded=wfh_uploaded,
            leave_uploaded=leave_uploaded
        )
        if mismatch_check:
            # If previously resolved mismatch exists, update it
            if existing_mismatch and existing_mismatch.get('status') == 'manager_approved':
                mismatch_check['status'] = 'pending'
                MismatchManagement.update_one(
                    {'_id': existing_mismatch['_id']},
                    {'$set': mismatch_check}
                )
            else:
                # Create new mismatch entry
                MismatchManagement.create_mismatch(**mismatch_check)
            flash('Attendance results in a mismatch. Please resolve via the Resolve Mismatch option.', 'danger')
            return redirect(url_for('vendor.dashboard'))

    # 5. Handle attendance update/insert with approval workflow
    existing_record = Attendance.find_by_user_and_date(user_id, date_str)
    if existing_record and existing_record.get('approval_status') in ['Approved', 'Rejected']:
        # If attendance already approved or rejected, mark for reapproval
        previous_data = {
            'status': existing_record['status'],
            'comments': existing_record.get('comments', ''),
        }
        update_data = {
            'current_data': {
                'status': status,
                'comments': comments
            },
            'previous_data': previous_data,
            'status': status,
            'approval_status': 'Pending',
            'reapproval_required': True,
            'manager_id': existing_record.get('manager_id')
        }
        Attendance.update_one({'_id': existing_record['_id']}, {'$set': update_data})
        flash('Attendance update submitted for manager reapproval', 'info')
    else:
        # For new attendance or previously unapproved entries
        Attendance.update_status(user_id, date_str, status, comments, site_id)
        flash('Attendance marked successfully', 'success')

    return redirect(url_for('vendor.dashboard'))

@vendor_bp.route('/calendar')
@login_required
@role_required('vendor')
def calendar_view():
    user_id = session['user_id']
    site_id = session['site_id']

    try:
        year = int(request.args.get('year', datetime.now().year))
        month = int(request.args.get('month', datetime.now().month))

        attendance_records = Attendance.find_by_user_and_month(user_id, year, month)
        attendance_map = {record['date']: record for record in attendance_records}

        calendar_data = get_month_calendar(year, month)

        # Fetch holidays for the current month (all holidays for the site that match the month)
        holidays = [
            h for h in Holiday.get_all(site_id)
            if h['date'].startswith(f"{year}-") and int(h['date'][5:7]) == month
        ]
        holidays_dict = {h['date']: h['name'] for h in holidays}

        # Get all weekends for this month for coloring (Saturday=5, Sunday=6)
        weekends = set()
        d = date(year, month, 1)
        while d.month == month:
            if d.weekday() in [0, 6]:
                weekends.add(d.strftime('%Y-%m-%d'))
            if d.day < calendar.monthrange(year, month)[1]:
                d = d.replace(day=d.day + 1)
            else:
                next_month = month + 1 if month < 12 else 1
                next_year = year if month < 12 else year + 1
                d = date(next_year, next_month, 1)

        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1

        current_date_str = datetime.now().strftime('%Y-%m-%d')

        return render_template(
            'vendor/calendar.html',
            calendar_data=calendar_data,
            attendance_map=attendance_map,
            holidays=holidays_dict,
            weekends=weekends,
            prev_month=prev_month,
            prev_year=prev_year,
            next_month=next_month,
            next_year=next_year,
            year=year,
            month=month,
            current_date=current_date_str
        )
    except Exception as e:
        # Handle errors gracefuly if needed
        return str(e), 500


    except Exception as e:
        logger.error(f"Calendar view error: {e}")
        flash('Error loading calendar', 'error')
        return render_template(
            'vendor/calendar.html',
            calendar_data=get_month_calendar(datetime.now().year, datetime.now().month),
            attendance_map={},
            holidays={},
            weekends=set(),
            prev_month=datetime.now().month-1,
            prev_year=datetime.now().year,
            next_month=datetime.now().month+1,
            next_year=datetime.now().year,
            year=datetime.now().year,
            month=datetime.now().month
        )
    
@vendor_bp.route('/history')
@login_required
@role_required('vendor')
def history():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    # Build query
    query = {'user_id': user_id}

    # Optional filter: start_date and end_date
    start_date = request.args.get('start_date')  # e.g. '2025-08-01'
    end_date = request.args.get('end_date')      # e.g. '2025-08-31'

    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            query['date'] = query.get('date', {})
            query['date']['$gte'] = start_date_obj.strftime('%Y-%m-%d')
        except ValueError:
            pass  # handle invalid date format if needed

    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            query['date'] = query.get('date', {})
            query['date']['$lte'] = end_date_obj.strftime('%Y-%m-%d')
        except ValueError:
            pass

    # Optional filter: status
    status = request.args.get('status')
    if status and status in Attendance.STATUSES:
        query['status'] = status

    records = Attendance.find(query, sort=[('date', -1)])

    return render_template('vendor/history.html', records=records, statuses=Attendance.STATUSES,
                           filters={'start_date': start_date, 'end_date': end_date, 'status': status})

@vendor_bp.route('/mismatches')
@login_required
@role_required('vendor')
def mismatches():
    user_id = session['user_id']
    user_mismatches = MismatchManagement.get_user_mismatches(user_id)

    # Attach user info if needed
    for mismatch in user_mismatches:
        mismatch['user_info'] = User.find_by_id(mismatch['user_id'])

    return render_template('vendor/mismatches.html', mismatches=user_mismatches)

@vendor_bp.route('/resolve-mismatch/<mismatch_id>', methods=['POST'])
@login_required
@role_required('vendor')
def resolve_mismatch(mismatch_id):
    new_status = request.form.get('new_status')
    comments = request.form.get('comments', '').strip()
    
    # Find mismatch
    mismatch = MismatchManagement.get_by_id(mismatch_id)
    if not mismatch:
        flash('Mismatch not found', 'error')
        return redirect(url_for('vendor.mismatches'))

    # Check authorization
    if str(mismatch.get('user_id')) != session['user_id']:
        flash('Unauthorized access to mismatch', 'error')
        return redirect(url_for('vendor.mismatches'))
    
    # Check deadline
    if datetime.utcnow() > mismatch['deadline']:
        flash('Resolution deadline has passed', 'error')      
        return redirect(url_for('vendor.mismatches'))

    if not new_status:
        flash('Please select a corrected status', 'error')
        return redirect(url_for('vendor.mismatches'))

    success = MismatchManagement.update_resolution(mismatch_id, new_status, comments)
    if success:
        flash('Mismatch resolution submitted successfully', 'success')
    else:
        flash('Failed to submit mismatch resolution', 'error')
    
    return redirect(url_for('vendor.mismatches'))
