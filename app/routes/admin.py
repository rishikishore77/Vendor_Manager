"""Admin routes"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models.user import User
from app.models.department import Department
from app.models.vending_company import VendingCompany
from app.utils.helpers import login_required, role_required
from app.utils.database import Database
from bson.objectid import ObjectId
from app.models.holiday import Holiday
from datetime import date, datetime, timedelta
import logging

logger = logging.getLogger(__name__)
admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/dashboard')
@login_required
@role_required('admin')
def dashboard():
    """Admin dashboard"""
    site_id = session['site_id']

    try:
        site_stats = {
            'total_vendors': len(User.get_all_by_site(site_id, 'vendor')),
            'total_managers': len(User.get_all_by_site(site_id, 'manager')),
            'monthly_attendance_count': 0  # Placeholder, implement as needed
        }
        return render_template(
            'admin/dashboard.html',
            site_stats=site_stats,
            recent_attendance=[],
            audit_statuses=[],
            mismatch_stats=[]
        )
    except Exception as e:
        logger.error(f"Admin dashboard error: {e}")
        flash('Error loading dashboard', 'error')
        return render_template(
            'admin/dashboard.html',
            site_stats={},
            recent_attendance=[],
            audit_statuses=[],
            mismatch_stats=[]
        )


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
    # Determine the selected year (from query or default to current year)
    try:
        selected_year = int(request.args.get('year', date.today().year))
    except ValueError:
        selected_year = date.today().year

    # Add holiday if requested
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
        if d.weekday() in [5, 6]:  # Saturday=5, Sunday=6
            weekends.add(d.strftime('%Y-%m-%d'))
        d += timedelta(days=1)

    # Today (as string)
    today = date.today().strftime('%Y-%m-%d')

    # Optionally, fetch all holidays for listing (for management table)
    all_holidays = Holiday.get_all(site_id)

    return render_template(
        'admin/holidays.html',
        db_holidays=db_holidays,
        weekends=weekends,
        today=today,
        selected_year=selected_year,
        all_holidays=all_holidays
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
