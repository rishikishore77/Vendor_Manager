"""Manager routes"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models.user import User
from app.models.attendance import Attendance
from app.utils.helpers import login_required, role_required
from bson.objectid import ObjectId
import logging

logger = logging.getLogger(__name__)
manager_bp = Blueprint('manager', __name__)

@manager_bp.route('/dashboard')
@login_required
@role_required('manager')
def dashboard():
    """Manager dashboard"""
    manager_id = session['user_id']

    try:
        team_members = User.get_vendors_by_manager(manager_id)
        pending_approvals = Attendance.get_pending_approvals(manager_id)

        return render_template('manager/dashboard.html',
                             team_members=team_members,
                             pending_approvals=pending_approvals[:10],
                             today_submissions=[],
                             open_mismatches=[],
                             total_pending=len(pending_approvals))

    except Exception as e:
        logger.error(f"Manager dashboard error: {e}")
        flash('Error loading dashboard', 'error')
        return render_template('manager/dashboard.html',
                             team_members=[],
                             pending_approvals=[],
                             today_submissions=[],
                             open_mismatches=[],
                             total_pending=0)

@manager_bp.route('/approve-attendance', methods=['POST'])
@login_required
@role_required('manager')
def approve_attendance():
    """Approve or reject attendance"""
    try:
        attendance_id = request.form.get('attendance_id')
        action = request.form.get('action')
        rejection_reason = request.form.get('rejection_reason', '')

        if not attendance_id or not action:
            flash('Invalid request parameters', 'error')
            return redirect(url_for('manager.dashboard'))

        status = 'Approved' if action == 'approve' else 'Rejected'

        update_data = {'approval_status': status}
        if rejection_reason:
            update_data['rejection_reason'] = rejection_reason

        from app.utils.database import Database
        result = Database.update_one('attendance', 
                                   {'_id': ObjectId(attendance_id)}, 
                                   {'$set': update_data})

        if result > 0:
            flash(f'Attendance {status.lower()} successfully', 'success')
        else:
            flash(f'Failed to {action} attendance', 'error')

    except Exception as e:
        logger.error(f"Attendance approval error: {e}")
        flash('Error processing approval', 'error')

    return redirect(url_for('manager.dashboard'))

@manager_bp.route('/team-data')
@login_required
@role_required('manager')
def team_data():
    """Team data view"""
    return render_template('manager/team_data.html', team_members=[], records=[])

@manager_bp.route('/mismatches')
@login_required
@role_required('manager')
def mismatches():
    """Manager mismatches view"""
    return render_template('manager/mismatches.html', team_mismatches=[])

@manager_bp.route('/reports')
@login_required
@role_required('manager')
def reports():
    """Manager reports"""
    return render_template('manager/reports.html', report_data=[])
