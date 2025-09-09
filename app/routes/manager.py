"""Manager routes"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models.user import User
from app.models.attendance import Attendance
from app.utils.helpers import login_required, role_required
from bson.objectid import ObjectId
from datetime import date
from app.utils.database import Database
from app.models.vending_company import VendingCompany
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
    site_id = session['site_id']
    manager_id = session['user_id']

    # Get single employee_id from request args
    employee_id = request.args.get('employee_id', '').strip()
    status = request.args.get('status', '')
    vendor_company_id = request.args.get('vendor_company_id', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    # Build user query with single employee filter
    user_query = {
        'site_id': site_id,
        'role': 'vendor',
        'manager_id': manager_id
    }
    if employee_id:
        try:
            user_query['_id'] = ObjectId(employee_id)
        except Exception as e:
            logger.error(f"Invalid employee ID in filter: {e}")
    if vendor_company_id:
        user_query['vendor_company_id'] = vendor_company_id

    team_members = User.find(user_query)
    vendor_companies = VendingCompany.get_all(site_id)
    vendor_company_map = {str(vc['_id']): vc['name'] for vc in vendor_companies}

    # Prepare attendance aggregation pipeline for all team members
    user_ids = [str(m['_id']) for m in team_members]
    attendance_match = {
        'user_id': {'$in': user_ids}
    }
    if start_date and end_date:
        attendance_match['date'] = {'$gte': start_date, '$lte': end_date}
    elif start_date:
        attendance_match['date'] = {'$gte': start_date}
    elif end_date:
        attendance_match['date'] = {'$lte': end_date}
    if status:
        attendance_match['status'] = status

    pipeline = [
        { '$match': attendance_match },
        { '$sort': { 'updated_at': -1 } },
        { '$group': {
            '_id': { 'user_id': '$user_id', 'date': '$date' },
            'doc': { '$first': "$$ROOT" }
        }},
        { '$replaceRoot': { 'newRoot': '$doc' } }
    ]

    attendance_records = Database.aggregate('attendance', pipeline)

    # Combine attendance with user info for display
    member_info_map = {str(m['_id']): m for m in team_members}
    records = []
    for record in attendance_records:
        user_info = member_info_map.get(record['user_id'])
        vendor_company = vendor_company_map.get(str(user_info.get('vendor_company_id')), 'N/A') if user_info else 'N/A'
        record['user_info'] = {
            'name': user_info.get('name', 'N/A') if user_info else 'N/A',
            'vendor_company': vendor_company
        }
        records.append(record)

    filters = {
        'employee_id': employee_id,
        'status': status,
        'vendor_company_id': vendor_company_id,
        'start_date': start_date,
        'end_date': end_date
    }

    return render_template(
        'manager/team_data.html',
        team_members=team_members,
        records=records,
        vendor_companies=vendor_companies,
        filters=filters
    )


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
