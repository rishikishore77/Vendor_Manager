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
    
    # Check for export request
    if 'export' in request.args:
        export_data = Timesheet.get_export_data(filters)
        df = pd.DataFrame(export_data)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Vendor Timesheets')
        output.seek(0)
        
        filename = f'vendor_timesheets_{month_year or "all"}.xlsx'
        return send_file(output, 
                        download_name=filename,
                        as_attachment=True,
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    
    timesheets = Timesheet.get_timesheets(filters)
    vending_companies = VendingCompany.get_all(site_id)
    
    return render_template('admin/vendor_timesheets.html',
                           timesheets=timesheets,
                           vending_companies=vending_companies,
                           filters=filters)