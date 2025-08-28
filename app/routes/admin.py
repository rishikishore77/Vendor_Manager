"""Admin routes"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models.user import User
from app.utils.helpers import login_required, role_required
import logging
from bson.objectid import ObjectId

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
            'monthly_attendance_count': 0
        }

        return render_template('admin/dashboard.html',
                               site_stats=site_stats,
                               recent_attendance=[],
                               audit_statuses=[],
                               mismatch_stats=[])

    except Exception as e:
        logger.error(f"Admin dashboard error: {e}")
        flash('Error loading dashboard', 'error')
        return render_template('admin/dashboard.html',
                               site_stats={},
                               recent_attendance=[],
                               audit_statuses=[],
                               mismatch_stats=[])


@admin_bp.route('/users')
@login_required
@role_required('admin')
def users():
    """User management"""
    site_id = session['site_id']
    users = User.get_all_by_site(site_id)

    vendors = [u for u in users if u.get('role') == 'vendor']
    managers = [u for u in users if u.get('role') == 'manager']
    admins = [u for u in users if u.get('role') == 'admin']

    return render_template('admin/users.html',
                           vendors=vendors,
                           managers=managers,
                           admins=admins)


@admin_bp.route('/add-user', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_user():
    """Add new user"""
    if request.method == 'POST':
        # Add user creation logic here
        flash('User creation functionality not fully implemented yet', 'info')
        return redirect(url_for('admin.users'))

    managers = User.get_all_by_site(session['site_id'], 'manager')
    return render_template('admin/add_user.html', managers=managers)


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
    """Holiday management"""
    return render_template('admin/holidays.html', holidays=[])


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


@admin_bp.route('/edit-user/<user_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_user(user_id):
    user = User.find_by_id(user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.users'))
    if request.method == 'POST':
        name = request.form.get('name')
        # Additional fields can be added here as per your user schema
        update_data = {'name': name}
        from app.utils.database import Database
        try:
            Database.update_one(User.COLLECTION, {'_id': ObjectId(user_id)}, {'$set': update_data})
            flash('User updated successfully.', 'success')
            return redirect(url_for('admin.users'))
        except Exception as e:
            flash(f'Error updating user: {e}', 'error')
    return render_template('admin/edit_user.html', user=user)
