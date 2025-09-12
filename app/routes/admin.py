"""Admin routes"""
from io import BytesIO
from flask import Blueprint, render_template, request, redirect, send_file, url_for, session, flash
from app.models.user import User
from app.models.department import Department
from app.models.vending_company import VendingCompany
from app.utils.helpers import login_required, role_required
from app.utils.database import Database
from bson.objectid import ObjectId
from app.models.holiday import Holiday
from datetime import date, datetime, timedelta
import logging
import calendar
from app.models.mismatch import MismatchManagement
from app.models.monthly_cycle import MonthlyCycle
from app.models.swipe_data import SwipeData
from app.models.wfh_data import WFHData
from app.models.leave_data import LeaveData
from app.utils.mismatch_processor import MismatchProcessor
from app.utils.data_upload_processor import DataUploadProcessor
from app.utils.helpers import allowed_file
import pandas as pd
from dateutil.relativedelta import relativedelta
import os
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)
admin_bp = Blueprint('admin', __name__)

def get_year_calendar(year):
    cal = calendar.Calendar(firstweekday=0)  # Monday=0
    months = {}
    for month in range(1, 13):
        weeks = []
        for week in cal.monthdatescalendar(year, month):
            weeks.append(week)
        months[month] = weeks
    return months

@admin_bp.route('/dashboard')
@login_required
@role_required('admin')
def dashboard():
    site_id = session['site_id']
    
    # Get site statistics
    site_stats = {
        'total_vendors': len(User.get_all_by_site(site_id, 'vendor')),
        'total_managers': len(User.get_all_by_site(site_id, 'manager')),
    }
    
    # Get mismatch statistics
    mismatch_stats = {
        'total_mismatches': MismatchManagement.count_site_mismatches(site_id),
        'pending_mismatches': MismatchManagement.count_site_mismatches(site_id, status='pending')
    }
    
    months = [(datetime.utcnow() - relativedelta(months=i)).strftime('%Y-%m') for i in range(12)]

    # Get recent mismatches
    recent_mismatches = MismatchManagement.get_site_mismatches(site_id, limit=10)
    
    return render_template('admin/dashboard.html', 
                         site_stats=site_stats,
                         mismatch_stats=mismatch_stats,
                         recent_mismatches=recent_mismatches,
                         months=months )

@admin_bp.route('/users')
@login_required
@role_required('admin')
def users():
    """User management with advanced filters and show inactive users"""

    site_id = session['site_id']

    # Get filter parameters
    name = request.args.get('name', '').strip()
    manager_id = request.args.get('manager_id', '')
    vendor_company_id = request.args.get('vendor_company_id', '')
    role = request.args.get('role', '')
    status = request.args.get('status', '')
    department_id = request.args.get('department_id', '')

    # Build dynamic query based on filters
    query = {'site_id': site_id}
    if role:
        query['role'] = role
    if name:
        query['name'] = {'$regex': name, '$options': 'i'}
    if manager_id:
        query['manager_id'] = manager_id
    if vendor_company_id:
        query['vendor_company_id'] = vendor_company_id
    if department_id:
        query['department_id'] = department_id
    if status == 'active':
        query['active'] = True
    elif status == 'inactive':
        query['active'] = False
    # For 'all' or blank status, do not restrict

    users = User.find(query)

    # Split users by role
    vendors = [u for u in users if u.get('role') == 'vendor']
    managers = [u for u in users if u.get('role') == 'manager']
    admins = [u for u in users if u.get('role') == 'admin']

    # Map manager ID to manager object for names
    managers_map = {str(m['_id']): m for m in managers}
    for v in vendors:
        v['manager_name'] = managers_map.get(str(v.get('manager_id')), {}).get('name', 'N/A')

    for m in managers:
        m['vendor_count'] = sum(1 for v in vendors if str(v.get('manager_id')) == str(m['_id']))

    # Fetch all departments and vending companies for dropdowns and mapping
    departments = Department.get_all(site_id)
    vendor_companies = VendingCompany.get_all(site_id)

    # Create maps for efficient lookup
    department_map = {str(d['_id']): d for d in departments}
    vendor_company_map = {str(vc['_id']): vc for vc in vendor_companies}

    # Map referenced IDs to names for vendors
    for v in vendors:
        v['vendor_company'] = vendor_company_map.get(str(v.get('vendor_company_id')), {}).get('name', 'N/A')
        dept = department_map.get(str(v.get('department_id')))
        if dept:
            v['department'] = f"{dept.get('name')}/{dept.get('subdepartment')}"
        else:
            v['department'] = 'N/A'

    # Map referenced IDs to names for managers
    for m in managers:
        dept = department_map.get(str(m.get('department_id')))
        if dept:
            m['department'] = f"{dept.get('name')}/{dept.get('subdepartment')}"
        else:
            m['department'] = 'N/A'

    # Filters to pass back into the form for UI
    filters = {
        'name': name,
        'manager_id': manager_id,
        'vendor_company_id': vendor_company_id,
        'department_id': department_id,
        'role': role,
        'status': status,
    }

    return render_template(
        'admin/users.html',
        vendors=vendors,
        managers=managers,
        admins=admins,
        all_managers=managers,
        departments=departments,
        vendor_companies=vendor_companies,
        filters=filters
    )


@admin_bp.route('/add-user', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_user():
    site_id = session['site_id']
    managers = User.get_all_by_site(site_id, 'manager')
    departments = Department.get_all(site_id)
    vendor_companies = VendingCompany.get_all(site_id)

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        name = request.form.get('name')

        kwargs = {}
        if role == 'vendor':
            kwargs['vendor_company_id'] = request.form.get('vendor_company_id')
            kwargs['manager_id'] = request.form.get('manager_id')
            kwargs['employee_code'] = request.form.get('employee_code')
            kwargs['department_id'] = request.form.get('department_id')
        elif role == 'manager':
            kwargs['department_id'] = request.form.get('department_id')

        new_user_id = User.create(username, password, role, name, site_id, **kwargs)
        if new_user_id:
            # Update department's manager_id if manager created with department assigned
            if role == 'manager' and kwargs.get('department_id'):
                Database.update_one(
                    Department.COLLECTION,
                    {'_id': ObjectId(kwargs['department_id'])},
                    {'$set': {'manager_id': ObjectId(new_user_id)}}
                )
            flash('User created successfully!', 'success')
            return redirect(url_for('admin.users'))
        flash('Error creating user.', 'error')

    return render_template(
        'admin/add_user.html',
        managers=managers,
        departments=departments,
        vendor_companies=vendor_companies
    )


@admin_bp.route('/edit-user/<user_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_user(user_id):
    user = User.find_by_id(user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.users'))

    site_id = session['site_id']
    managers = User.get_all_by_site(site_id, 'manager')
    departments = Department.get_all(site_id)
    vendor_companies = VendingCompany.get_all(site_id)

    if request.method == 'POST':
        name = request.form.get('name')
        update_data = {'name': name}

        if user.get('role') == 'vendor':
            update_data['vendor_company_id'] = request.form.get('vendor_company_id')
            update_data['department_id'] = request.form.get('department_id')
            update_data['manager_id'] = request.form.get('manager_id')
            # Add employee_code update if needed
        elif user.get('role') == 'manager':
            new_dept_id = request.form.get('department_id')
            update_data['department_id'] = new_dept_id

        try:
            Database.update_one(User.COLLECTION, {'_id': ObjectId(user_id)}, {'$set': update_data})

            # If manager role and department changed, update department's manager_id
            if user.get('role') == 'manager' and update_data.get('department_id'):
                Database.update_one(
                    Department.COLLECTION,
                    {'_id': ObjectId(update_data['department_id'])},
                    {'$set': {'manager_id': ObjectId(user_id)}}
                )

            flash('User updated successfully.', 'success')
            return redirect(url_for('admin.users'))
        except Exception as e:
            flash(f'Error updating user: {e}', 'error')

    return render_template(
        'admin/edit_user.html',
        user=user,
        managers=managers,
        departments=departments,
        vendor_companies=vendor_companies
    )


@admin_bp.route('/add-vending-company', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_vending_company():
    site_id = session['site_id']
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Vending company name is required.', 'error')
        else:
            new_id = VendingCompany.add(site_id, name)
            if new_id:
                flash('Vending company created successfully.', 'success')
                return redirect(url_for('admin.add_user'))
            else:
                flash('Error creating vending company.', 'error')
    return render_template('admin/add_vending_company.html')


@admin_bp.route('/add-department', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_department():
    site_id = session['site_id']
    managers = User.get_all_by_site(site_id, 'manager')  # For optional assignment

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        subdepartment = request.form.get('subdepartment', '').strip()
        manager_id = request.form.get('manager_id', '')  # Can be empty string

        if not name or not subdepartment:
            flash('Department name and subdepartment are required.', 'error')
        else:
            mgr_obj_id = ObjectId(manager_id) if manager_id else None
            new_dept_id = Department.create(site_id, name, subdepartment, mgr_obj_id)
            if new_dept_id:
                if mgr_obj_id:
                    Database.update_one(
                        User.COLLECTION,
                        {'_id': mgr_obj_id},
                        {'$set': {'department_id': new_dept_id}}
                    )
                flash('Department created successfully.', 'success')
                return redirect(url_for('admin.add_user'))
            else:
                flash('Error creating department.', 'error')

    return render_template('admin/add_department.html', managers=managers)


@admin_bp.route('/upload-data', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def upload_data():
    """Upload data files"""
    if request.method == 'POST':
        flash('File upload functionality not fully implemented yet', 'info')
    return render_template('admin/upload_data.html')


@admin_bp.route('/holidays', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def holidays():
    site_id = session['site_id']
    try:
        selected_year = int(request.args.get('year', date.today().year))
    except ValueError:
        selected_year = date.today().year

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        holiday_date = request.form.get('date', '').strip()
        if name and holiday_date:
            Holiday.add(site_id, holiday_date, name)
            flash('Holiday added successfully!', 'success')
        else:
            flash('Please enter all holiday details.', 'error')

    # Fetch stored holidays for the year
    db_holidays = {h['date']: h['name'] for h in Holiday.get_all(site_id) if h['date'].startswith(str(selected_year))}

    # Calculate all weekends for the selected year
    weekends = set()
    d = date(selected_year, 1, 1)
    while d.year == selected_year:
        if d.weekday() in [5, 6]:
            weekends.add(d.strftime('%Y-%m-%d'))
        d += timedelta(days=1)

    # Generate calendar layout for each month
    year_calendar = get_year_calendar(selected_year)
    month_names = [
        '', 'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]

    # Today's date
    today = date.today().strftime('%Y-%m-%d')

    # All holidays for management table
    all_holidays = Holiday.get_all(site_id)

    return render_template(
        'admin/holidays.html',
        db_holidays=db_holidays,
        weekends=weekends,
        today=today,
        selected_year=selected_year,
        all_holidays=all_holidays,
        year_calendar=year_calendar,
        month_names=month_names
    )


@admin_bp.route('/holidays/delete/<holiday_id>', methods=['POST'])
@login_required
@role_required('admin')
def delete_holiday(holiday_id):
    site_id = session['site_id']
    Holiday.delete(site_id, holiday_id)
    flash('Holiday deleted.', 'success')
    return redirect(url_for('admin.holidays'))


@admin_bp.route('/reports')
@login_required
@role_required('admin')
def reports():
    """Admin reports"""
    return render_template('admin/reports.html', records=[], summary_stats={})


@admin_bp.route('/audit-management')
@login_required
@role_required('admin')
def audit_management():
    """Audit management"""
    return render_template('admin/audit_management.html', manager_audit_info=[])


@admin_bp.route('/deactivate-user', methods=['POST'])
@login_required
@role_required('admin')
def deactivate_user():
    user_id = request.form.get('user_id')
    if not user_id:
        flash('User ID is required for deactivation.', 'error')
        return redirect(url_for('admin.users'))
    try:
        count = User.deactivate(user_id)
        if count:
            flash('User deactivated successfully.', 'success')
        else:
            flash('User not found or already inactive.', 'warning')
    except Exception as e:
        flash(f'Error deactivating user: {e}', 'error')
    return redirect(url_for('admin.users'))

@admin_bp.route('/monthly-cycles')
@login_required
@role_required('admin')
def monthly_cycles():
    site_id = session['site_id']
    cycles = MonthlyCycle.get_all(site_id)
    return render_template('admin/monthly_cycles.html', cycles=cycles)

@admin_bp.route('/upload-monthly-data/<month_year>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def upload_monthly_data(month_year):
    if request.method == 'POST':
        data_type = request.form.get('data_type') # swipe/wfh/leave
        file = request.files['file']
        site_id = session['site_id']
        if file and allowed_file(file.filename):
            result = DataUploadProcessor.process_upload(file, data_type, month_year, site_id)
            if result:
                flash(f'{data_type.title()} data uploaded successfully!', 'success')
                return redirect(url_for('admin.monthly_cycles'))
            else:
                flash(f'Error uploading {data_type} data', 'error')
    return render_template('admin/upload_monthly_data.html', month_year=month_year)

@admin_bp.route('/process-mismatches/<month_year>', methods=['POST'])
@login_required
@role_required('admin')
def process_mismatches(month_year):
    site_id = session['site_id']
    mismatch_count = MismatchProcessor.detect_and_create_mismatches(site_id, month_year)
    flash(f'{mismatch_count} mismatches detected and created', 'info')
    return redirect(url_for('admin.monthly_cycles'))

@admin_bp.route('/upload-with-month-selector')
@login_required
@role_required('admin')
def upload_with_month_selector():
    month_year = request.args.get('month_year')
    if month_year:
        return redirect(url_for('admin.upload_monthly_data', month_year=month_year))
    else:
        flash('Please select a month', 'error')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/process-mismatches-with-month', methods=['POST'])
@login_required
@role_required('admin')
def process_mismatches_with_month():
    month_year = request.form.get('month_year')
    site_id = session.get('site_id')
    
    if month_year and site_id:
        count = MismatchProcessor.detect_and_create_mismatches(site_id, month_year)
        flash(f'{count} mismatches detected and created for {month_year}', 'info')
    else:
        flash('Please select a month', 'error')
    
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/mismatches')
@login_required
@role_required('admin')
def view_mismatches():
    site_id = session.get('site_id')
    mismatches = []
    if site_id:
        mismatches = MismatchManagement.get_site_mismatches(site_id)
        for mismatch in mismatches:
            user = User.find_by_id(mismatch['user_id'])
            mismatch['user_info'] = user
    return render_template('admin/mismatches.html', mismatches=mismatches)

@admin_bp.route('/vendor-timesheets')
@login_required
@role_required('admin')
def vendor_timesheets():
    from app.models.timesheet import Timesheet
    from app.models.user import User
    from app.models.vending_company import VendingCompany

    site_id = session['site_id']
    vending_company_id = request.args.get('vending_company_id')
    month_year = request.args.get('month_year')

    filters = {
        'vending_company_id': vending_company_id,
        'month_year': month_year,
    }
    
    timesheets = Timesheet.get_timesheets(filters)
    
    vendor_ids = [ts['vendor_id'] for ts in timesheets]
    vendors = User.find({'_id': {'$in': vendor_ids}})
    vendor_map = {v['_id']: v for v in vendors}
    
    data_for_export = []
    for ts in timesheets:
        vendor = vendor_map.get(ts['vendor_id'])
        data_for_export.append({
            'Vendor Name': vendor.get('name') if vendor else '',
            'Month-Year': ts['month_year'],
            'Worked Days': ts['worked_days'],
            'Mismatch Leave Days': ts['mismatch_leave_days'],
            'Offset Days': ts['offset_days'],
            'Total Days (with offset)': ts['worked_days'] + ts['offset_days']
        })

    if 'export' in request.args:
        df = pd.DataFrame(data_for_export)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Timesheets')
        output.seek(0)
        return send_file(output, attachment_filename='vendor_timesheets.xlsx', as_attachment=True)

    vending_companies = VendingCompany.get_all(site_id)
    
    return render_template('admin/vendor_timesheets.html',
                           timesheets=data_for_export,
                           vending_companies=vending_companies,
                           filters=filters)