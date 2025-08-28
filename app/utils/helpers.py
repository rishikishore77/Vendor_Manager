"""Helper functions and decorators"""
from functools import wraps
from flask import session, redirect, url_for, flash, current_app
from datetime import datetime
import calendar

def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))

            if session.get('role') != role:
                flash('Access denied. Insufficient permissions.', 'error')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_month_calendar(year, month):
    """Get calendar data for a specific month"""
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    return {
        'year': year,
        'month': month,
        'month_name': month_name,
        'calendar': cal
    }

def is_working_day(date, holidays=None):
    """Check if a date is a working day"""
    if holidays is None:
        holidays = []

    if isinstance(date, str):
        try:
            date = datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return False

    # Check if it's a weekend
    if date.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False

    # Check if it's a holiday
    date_str = date.strftime('%Y-%m-%d')
    return date_str not in holidays
