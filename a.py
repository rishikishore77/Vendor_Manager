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