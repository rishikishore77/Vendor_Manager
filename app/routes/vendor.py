"""Vendor routes"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models.user import User
from app.models.attendance import Attendance
from app.utils.helpers import login_required, role_required, get_month_calendar, is_working_day
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
vendor_bp = Blueprint('vendor', __name__)

@vendor_bp.route('/dashboard')
@login_required
@role_required('vendor')
def dashboard():
    """Vendor dashboard"""
    user_id = session['user_id']
    site_id = session['site_id']

    try:
        today = datetime.now()
        today_str = today.strftime('%Y-%m-%d')

        # Get today's attendance status
        today_attendance = Attendance.find_by_user_and_date(user_id, today_str)

        # Simple working day check (no holidays for now)
        is_today_working = today.weekday() < 5  # Monday to Friday

        # Get monthly summary
        monthly_summary = Attendance.get_monthly_summary(user_id, today.year, today.month)

        return render_template('vendor/dashboard.html', 
                             today_attendance=today_attendance,
                             is_today_working=is_today_working,
                             monthly_summary=monthly_summary,
                             today=today_str,
                             open_mismatches=[],
                             upcoming_holidays=[])

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
    """Mark attendance"""
    user_id = session['user_id']
    site_id = session['site_id']

    try:
        date = request.form.get('date')
        status = request.form.get('status')
        comments = request.form.get('comments', '')

        if not date or not status:
            flash('Date and status are required', 'error')
            return redirect(url_for('vendor.dashboard'))

        if Attendance.update_status(user_id, date, status, comments, site_id):
            flash('Attendance marked successfully', 'success')
        else:
            flash('Failed to mark attendance', 'error')

    except Exception as e:
        logger.error(f"Mark attendance error: {e}")
        flash('Error marking attendance', 'error')

    return redirect(url_for('vendor.dashboard'))

@vendor_bp.route('/calendar')
@login_required
@role_required('vendor')
def calendar_view():
    """Attendance calendar"""
    user_id = session['user_id']

    try:
        year = int(request.args.get('year', datetime.now().year))
        month = int(request.args.get('month', datetime.now().month))

        attendance_records = Attendance.find_by_user_and_month(user_id, year, month)
        attendance_map = {record['date']: record for record in attendance_records}

        calendar_data = get_month_calendar(year, month)

        # Navigation
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1

        return render_template('vendor/calendar.html',
                             calendar_data=calendar_data,
                             attendance_map=attendance_map,
                             prev_month=prev_month,
                             prev_year=prev_year,
                             next_month=next_month,
                             next_year=next_year)

    except Exception as e:
        logger.error(f"Calendar view error: {e}")
        flash('Error loading calendar', 'error')
        return render_template('vendor/calendar.html',
                             calendar_data=get_month_calendar(datetime.now().year, datetime.now().month),
                             attendance_map={},
                             prev_month=datetime.now().month-1,
                             prev_year=datetime.now().year,
                             next_month=datetime.now().month+1,
                             next_year=datetime.now().year)

@vendor_bp.route('/history')
@login_required
@role_required('vendor')
def history():
    """Attendance history"""
    return render_template('vendor/history.html', records=[], statuses=Attendance.STATUSES)

@vendor_bp.route('/mismatches')
@login_required
@role_required('vendor')
def mismatches():
    """View mismatches"""
    return render_template('vendor/mismatches.html', mismatches_by_date={})
