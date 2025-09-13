"""Vendor routes"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models.mismatch import MismatchManagement
from app.models.user import User
from app.models.holiday import Holiday
from app.models.attendance import Attendance
from app.utils.helpers import login_required, role_required, get_month_calendar, is_working_day
from datetime import datetime, date, timedelta
import calendar
import logging

logger = logging.getLogger(__name__)
vendor_bp = Blueprint('vendor', __name__)

def get_vendor_attendance_edit_range(today=None):
    if today is None:
        today = datetime.now()
    
    start_of_this_month = today.replace(day=1)
    start_of_last_month = (start_of_this_month - timedelta(days=1)).replace(day=1)
    
    # Allowed editing ends on today if day ≤14, else 14th of next month
    if today.day <= 14:
        edit_end_date = today.date()
    else:
        if today.month == 12:
            edit_end_date = datetime(today.year + 1, 1, 14).date()
        else:
            edit_end_date = datetime(today.year, today.month + 1, 14).date()
    
    return start_of_last_month.date(), edit_end_date

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

        # Get today's attendance status
        today_attendance = Attendance.find_by_user_and_date(user_id, today_str)

        # Simple working day check (no holidays for now)
        is_today_working = today.weekday() < 5  # Monday to Friday

        # Get monthly summary (Assumed dictionary result)
        monthly_summary = Attendance.get_monthly_summary(user_id, today.year, today.month)

        # Get mismatch stats for vendor
        mismatch_count = MismatchManagement.count_user_mismatches(user_id)
        urgent_mismatch_count = MismatchManagement.count_user_mismatches(user_id, status='pending') + MismatchManagement.count_user_mismatches(user_id, status='manager_rejected')

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
                               allowed_range=allowed_range)

    except Exception as e:
        logger.error(f"Vendor dashboard error: {e}")
        flash('Error loading dashboard', 'error')
        return render_template('vendor/dashboard.html',
                               today_attendance=None,
                               is_today_working=True,
                               monthly_summary={},
                               today=datetime.now().strftime('%Y-%m-%d'),
                               stats={},
                               allowed_range={'start_date': '', 'end_date': ''})


    except Exception as e:
        logger.error(f"Vendor dashboard error: {e}")
        flash('Error loading dashboard', 'error')
        return render_template('vendor/dashboard.html', 
                             today_attendance=None,
                             is_today_working=True,
                             monthly_summary={},
                             today=datetime.now().strftime('%Y-%m-%d'),
                             open_mismatches=[],
                             upcoming_holidays=[])

@vendor_bp.route('/mark-attendance', methods=['POST'])
@login_required
@role_required('vendor')
def mark_attendance():
    user_id = session['user_id']
    site_id = session['site_id']
    
    date_str = request.form.get('date')
    status = request.form.get('status')
    comments = request.form.get('comments', '')
    
    if not date_str or not status:
        flash('Date and status are required', 'error')
        return redirect(url_for('vendor.dashboard'))
    
    try:
        attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid date format', 'error')
        return redirect(url_for('vendor.dashboard'))
    
    start_date, end_date = get_vendor_attendance_edit_range()
    if attendance_date < start_date or attendance_date > end_date:
        flash(f'Attendance date must be between {start_date} and {end_date}', 'error')
        return redirect(url_for('vendor.dashboard'))
    
    existing_record = Attendance.find_by_user_and_date(user_id, date_str)
    if existing_record and (existing_record.get('approval_status') == 'Approved' or existing_record.get('approval_status') == 'Rejected'):
        previous_data = {
            'status': existing_record['status'],
            'comments': existing_record.get('comments', ''),
            # add other fields if needed
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
        # notify_manager(existing_record.get('manager_id'), existing_record['_id'])
        flash('Attendance update submitted for manager reapproval', 'info')
    else:
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
