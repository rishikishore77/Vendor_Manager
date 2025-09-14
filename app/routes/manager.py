"""Manager routes"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models.mismatch import MismatchManagement
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
    manager_id = session['user_id']

    # Get filter params from query string (optional)
    employee_filter = request.args.get('employee_name', '').strip().lower()
    status_filter = request.args.get('status', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    # Get all vendors and apply filter (if implemented) or fetch all
    team_members = User.get_vendors_by_manager(manager_id)

    vendor_ids = [str(v['_id']) for v in team_members]

    pending_approvals_query = {
        'user_id': {'$in': vendor_ids},
        'approval_status': 'Pending',
        'status': {'$ne': 'Pending'}
    }

    if status_filter:
        pending_approvals_query['status'] = status_filter
    if start_date and end_date:
        pending_approvals_query['date'] = {'$gte': start_date, '$lte': end_date}

    pending_approvals = Attendance.find(pending_approvals_query)

    for record in pending_approvals:
        user = User.find_by_id(record['user_id'])
        record['user_info'] = user

    # Optionally filter by employee name in Python if your DB does not support text search
    if employee_filter:
        pending_approvals = [pa for pa in pending_approvals if pa.get('user_info', {}).get('name', '').lower().startswith(employee_filter)]

    pending_approval_count = len(pending_approvals)
    team_size = len(team_members)
    total_mismatches = MismatchManagement.count_team_mismatches(manager_id)
    attendance_records_count = Attendance.count_team_records(manager_id)

    stats = {
        'team_size': team_size,
        'pending_approvals': pending_approval_count,
        'total_mismatches': total_mismatches,
        'attendance_records': attendance_records_count
    }

    return render_template('manager/dashboard.html',
                           team_members=team_members,
                           pending_approvals=pending_approvals,
                           total_pending=pending_approval_count,
                           stats=stats,
                           filters={'employee_name': employee_filter, 'status': status_filter, 'start_date': start_date, 'end_date': end_date})


@manager_bp.route('/approve-attendance', methods=['POST'])
@login_required
@role_required('manager')
def approve_attendance():
    try:
        attendance_id = request.form.get('attendance_id')
        action = request.form.get('action')
        rejection_reason = request.form.get('rejection_reason', '')

        if not attendance_id or not action:
            flash('Invalid request parameters', 'error')
            return redirect(url_for('manager.dashboard'))

        record = Attendance.find_by_id(ObjectId(attendance_id))
        if not record:
            flash('Attendance record not found', 'error')
            return redirect(url_for('manager.dashboard'))

        if record.get('reapproval_required'):
            if action == 'approve':
                current = record.get('current_data', {})
                record.update(current)
                record['approval_status'] = 'Approved'
                record['reapproval_required'] = False
                record['previous_data'] = {}
                record['current_data'] = {}
                Attendance.save(record)
                flash('Attendance update approved', 'success')

            elif action == 'reject':
                record['approval_status'] = 'Rejected'
                record['reapproval_required'] = False
                record['current_data'] = {}
                Attendance.save(record)
                flash('Attendance update rejected', 'info')

            else:
                flash('Invalid approval action', 'error')

        else:
            status = 'Approved' if action == 'approve' else 'Rejected'
            update_data = {'approval_status': status}
            if rejection_reason:
                update_data['rejection_reason'] = rejection_reason
            result = Attendance.update_one({'_id': ObjectId(attendance_id)}, {'$set': update_data})
            if result > 0:
                flash(f'Attendance {status.lower()} successfully', 'success')
            else:
                flash(f'Failed to {action} attendance', 'error')

    except Exception as e:
        logger.error(f"Attendance approval error: {e}")
        flash('Error processing approval', 'error')

    return redirect(url_for('manager.dashboard'))

@manager_bp.route('/team-attendance')
@login_required
@role_required('manager')
def team_attendance():
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
        'manager/team_attendance.html',
        team_members=team_members,
        records=records,
        vendor_companies=vendor_companies,
        filters=filters
    )


@manager_bp.route('/reports')
@login_required
@role_required('manager')
def reports():
    """Manager reports"""
    return render_template('manager/reports.html', report_data=[])

@manager_bp.route('/mismatches')
@login_required
@role_required('manager')
def mismatches():
    manager_id = session['user_id']

    # Get filter params from request args
    vendor_name = request.args.get('vendor_name', '').strip().lower()
    status = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Fetch all mismatches for team
    team_mismatches = MismatchManagement.get_team_mismatches(manager_id)
    
    # Attach user info and attendance status
    from app.models.user import User
    from app.models.attendance import Attendance

    filtered_mismatches = []
    for mismatch in team_mismatches:
        user = User.find_by_id(mismatch['user_id'])
        mismatch['user_info'] = user
        attendance_record = Attendance.find_by_user_and_date(
            str(mismatch['user_id']),
            mismatch['date']
        )
        mismatch['attendance_status'] = attendance_record.get('status') if attendance_record else '-'

        # Apply filters
        if vendor_name and vendor_name not in (user.get('name', '').lower() if user else ''):
            continue
        if status and mismatch['status'] != status:
            continue
        if start_date and mismatch['date'] < start_date:
            continue
        if end_date and mismatch['date'] > end_date:
            continue

        filtered_mismatches.append(mismatch)

    return render_template('manager/mismatches.html', mismatches=filtered_mismatches)



@manager_bp.route('/mismatch-approval', methods=['POST'])
@login_required
@role_required('manager')
def mismatch_approval():
    mismatch_id = request.form.get('mismatch_id')
    action = request.form.get('action')  # 'approve' or 'reject'
    manager_comments = request.form.get('manager_comments', '')

    if not mismatch_id or action not in ('approve', 'reject'):
        flash('Invalid mismatch approval request', 'error')
        return redirect(url_for('manager.mismatches'))

    status = 'manager_approved' if action == 'approve' else 'manager_rejected'
    success = MismatchManagement.update_resolution_status(mismatch_id, status, manager_comments)

    if success and status == 'manager_approved':
            mismatch = MismatchManagement.get_by_id(mismatch_id)
            MismatchManagement._update_attendance_final_status(mismatch)
    
    if success:
        flash(f'Mismatch {action}d successfully', 'success')
    else:
        flash('Failed to update mismatch status', 'error')

    return redirect(url_for('manager.mismatches'))


@manager_bp.route('/team-data')
@login_required
@role_required('manager')
def team_data():
    site_id = session['site_id']
    manager_id = session['user_id']

    # Fetch all vendors under this manager
    team_members = User.get_vendors_by_manager(manager_id)
    user_ids = [str(m['_id']) for m in team_members]

    # Fetch attendance records for the team (can be filtered/paginated as needed)
    attendance_records = Attendance.find({"user_id": {"$in": user_ids}})

    # Map user info for attendance records
    user_map = {str(user['_id']): user for user in team_members}
    for record in attendance_records:
        record['user_info'] = user_map.get(str(record['user_id']), {})

    return render_template('manager/team_data.html',
                           attendance_records=attendance_records,
                           team_members=team_members)

@manager_bp.route('/monthly-summary')
@login_required
@role_required('manager')
def monthly_summary_report():
    from app.models.user import User
    from app.models.attendance import Attendance
    from app.models.department import Department
    from app.models.vending_company import VendingCompany

    site_id = session['site_id']
    manager_id = session['user_id']

    # Get filters from request query params
    name_filter = request.args.get('name', '').strip().lower()
    vending_company_filter = request.args.get('vending_company', '')
    department_filter = request.args.get('department', '')
    month_year = request.args.get('month_year') or date.today().strftime('%Y-%m')
    year, month = map(int, month_year.split('-'))

    # Fetch vendors managed by this manager
    user_query = {
        'manager_id': manager_id,
        'role': 'vendor',
        'site_id': site_id
    }
    if name_filter:
        user_query['name'] = {'$regex': f'.*{name_filter}.*', '$options': 'i'}
    if vending_company_filter:
        user_query['vendor_company_id'] = vending_company_filter
    if department_filter:
        user_query['department_id'] = department_filter

    vendors = User.find(user_query)
    vendor_ids = [v['_id'] for v in vendors]

    # Fetch vending companies and departments for mapping
    vending_companies = VendingCompany.get_all(site_id)
    company_map = {str(vc['_id']): vc['name'] for vc in vending_companies}

    departments = Department.get_all(site_id)
    department_map = {str(dept['_id']): dept['name'] for dept in departments}

    # Fetch attendance records for all vendors for month
    attendance_records = []
    for vendor_id in vendor_ids:
        records = Attendance.find_by_user_and_month(str(vendor_id), year, month)
        attendance_records.extend(records)

    # Group attendance by user_id
    attendance_by_user = {}
    for record in attendance_records:
        uid = str(record['user_id'])
        attendance_by_user.setdefault(uid, []).append(record)

    reports = []
    for vendor in vendors:
        vid = str(vendor['_id'])
        records = attendance_by_user.get(vid, [])
        total_days = len(records)
        in_office_days = sum(1 for r in records if 'office' in r['status'].lower())
        wfh_days = sum(1 for r in records if 'work from home' in r['status'].lower())
        leave_days = sum(1 for r in records if 'leave' in r['status'].lower())
        leave_dates = [r['date'] for r in records if 'leave' in r['status'].lower()]
        wfh_dates = [r['date'] for r in records if 'work from home' in r['status'].lower()]
        comments = [r['comments'] for r in records if r.get('comments')]

        reports.append({
            'name': vendor.get('name', '-'),
            'email': vendor.get('email', '-'),
            'vendor_id': vendor.get('employee_code', '-'),
            'department_name': department_map.get(str(vendor.get('department_id')), '-'),
            'vending_company': company_map.get(str(vendor.get('vendor_company_id')), '-'),
            'total_working_days': total_days,
            'in_office_days': in_office_days,
            'leave_days': leave_days,
            'leave_dates': leave_dates,
            'wfh_dates': wfh_dates,
            'comments': comments
        })

    return render_template('manager/monthly_summary.html',
                           reports=reports,
                           vending_companies=vending_companies,
                           departments=departments,
                           filters={
                               'name': name_filter,
                               'vending_company': vending_company_filter,
                               'department': department_filter,
                               'month_year': month_year
                           })

@manager_bp.route('/vendor-timesheets')
@login_required
@role_required('manager')
def vendor_timesheets():
    from bson import ObjectId
    from app.models.timesheet import Timesheet
    from app.models.user import User
    from app.models.vending_company import VendingCompany
    from flask import send_file
    import io
    import pandas as pd

    manager_id = session['user_id']
    site_id = session['site_id']

    # Filters
    vendor_name_filter = request.args.get('vendor_name', '').strip()
    vending_company_filter = request.args.get('vending_company', '').strip()
    month_year_filter = request.args.get('month_year', '').strip()

    # Fetch vendors under this manager
    vendors = User.get_vendors_by_manager(manager_id)

    # Filter vendors by name/company
    if vendor_name_filter:
        vendors = [v for v in vendors if vendor_name_filter.lower() in v.get('name', '').lower()]
    if vending_company_filter:
        vendors = [v for v in vendors if (str(v.get('vendor_company_id') or '') == vending_company_filter)]

    vendor_ids = [v['_id'] for v in vendors]

    # Prepare filters for timesheets
    filters = {}
    if vendor_ids:
        filters['vendor_id'] = {'$in': vendor_ids}
    if month_year_filter:
        filters['month_year'] = month_year_filter

    # Check if export requested
    if 'export' in request.args:
        timesheet_data = Timesheet.get_export_data(filters)
        df = pd.DataFrame(timesheet_data)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='VendorTimesheets')
        output.seek(0)

        filename = f'vendor_timesheets_{month_year_filter or "all"}.xlsx'
        return send_file(output, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    # Fetch timesheet data
    timesheets = Timesheet.get_timesheets(filters)

    # Get all vending companies for filter dropdown
    vending_companies = VendingCompany.get_all(site_id)

    return render_template('manager/vendor_timesheets.html',
                           timesheets=timesheets,
                           vendors=vendors,
                           vending_companies=vending_companies,
                           filters={'vendor_name': vendor_name_filter,
                                    'vending_company': vending_company_filter,
                                    'month_year': month_year_filter})


