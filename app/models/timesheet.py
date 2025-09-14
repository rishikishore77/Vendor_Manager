from bson.objectid import ObjectId
from datetime import datetime
from app.utils.database import Database
from app.models.user import User
from app.models.vending_company import VendingCompany

class Timesheet:
    COLLECTION = 'timesheets'

    @classmethod
    def find_one(cls, vendor_id, month_year):
        return Database.find_one(cls.COLLECTION, {
            'vendor_id': ObjectId(vendor_id),
            'month_year': month_year
        })

    @classmethod
    def create_or_update(cls, vendor_id, month_year, worked_days, mismatch_leave_days, offset_days=0):
        existing = cls.find_one(vendor_id, month_year)
        data = {
            'vendor_id': ObjectId(vendor_id),
            'month_year': month_year,
            'worked_days': worked_days,
            'mismatch_leave_days': mismatch_leave_days,
            'offset_days': offset_days,
            'generated_on': datetime.utcnow()
        }
        if existing:
            Database.update_one(cls.COLLECTION, {'_id': existing['_id']}, {'$set': data})
            return existing['_id']
        else:
            return Database.insert_one(cls.COLLECTION, data)

    @classmethod
    def create_or_update_detailed(cls, vendor_id, vending_company_id, month_year,
                                  work_dates_hours, mismatch_leave_days,
                                  offset_dates_hours, total_offset_hours):
        existing = cls.find_one(vendor_id, month_year)
        
        total_work_hours = sum(work_dates_hours.values())
        total_hours_with_offset = total_work_hours + total_offset_hours
        
        data = {
            'vendor_id': ObjectId(vendor_id),
            'vending_company_id': ObjectId(vending_company_id) if vending_company_id else None,
            'month_year': month_year,
            'work_dates_hours': work_dates_hours,
            'mismatch_leave_days': mismatch_leave_days,
            'offset_dates_hours': offset_dates_hours,
            'total_offset_hours': total_offset_hours,
            'total_work_hours': total_work_hours,
            'total_hours_with_offset': total_hours_with_offset,
            'worked_days': len([h for h in work_dates_hours.values() if h > 0]),
            'offset_days': len([h for h in offset_dates_hours.values() if h > 0]),
            'generated_on': datetime.utcnow()
        }
        
        if existing:
            Database.update_one(cls.COLLECTION, {'_id': existing['_id']}, {'$set': data})
            return existing['_id']
        else:
            return Database.insert_one(cls.COLLECTION, data)

    @classmethod
    def get_latest_timesheet(cls, vendor_id):
        results = list(Database.find(
            cls.COLLECTION,
            {'vendor_id': ObjectId(vendor_id)},
            sort=[('month_year', -1)],
            limit=1
        ))
        return results[0] if results else None


    @classmethod
    def get_timesheets(cls, filters):
        query = {}
        if 'vending_company_id' in filters and filters['vending_company_id']:
            query['vending_company_id'] = ObjectId(filters['vending_company_id'])
        if 'month_year' in filters and filters['month_year']:
            query['month_year'] = filters['month_year']
        if 'manager_id' in filters and filters['manager_id']:
            # Find vendors under this manager
            vendors = User.find({'manager_id': ObjectId(filters['manager_id']), 'role': 'vendor'})
            vendor_ids = [v['_id'] for v in vendors]
            query['vendor_id'] = {'$in': vendor_ids}
            
        timesheets = list(Database.find(cls.COLLECTION, query))
        
        # Enrich with vendor and company info
        for ts in timesheets:
            vendor = User.find_one({'_id': ts['vendor_id']})
            if vendor:
                ts['vendor_name'] = vendor.get('name', 'N/A')
                ts['vendor_email'] = vendor.get('email', 'N/A')

                # Get vending company from vendor
                if vendor.get('vendor_company_id'):
                    company = VendingCompany.find_by_id(vendor['vendor_company_id'])
                    if company:
                        ts['vending_company_name'] = company.get('name', 'N/A')
                    else:
                        ts['vending_company_name'] = 'N/A'
                else:
                    ts['vending_company_name'] = 'N/A'
            else:
                ts['vendor_name'] = 'N/A'
                ts['vendor_email'] = 'N/A'
                ts['vending_company_name'] = 'N/A'
        
        return timesheets

    @classmethod
    def get_export_data(cls, filters):
        timesheets = cls.get_timesheets(filters)
        export_data = []
        
        for ts in timesheets:
            # Main timesheet row
            base_row = {
                'Vendor Name': ts.get('vendor_name', 'N/A'),
                'Vendor Email': ts.get('vendor_email', 'N/A'),
                'Company': ts.get('vending_company_name', 'N/A'),
                'Month-Year': ts['month_year'],
                'Total Work Hours': ts.get('total_work_hours', 0),
                'Mismatch Leave Days': ts.get('mismatch_leave_days', 0),
                'Total Offset Hours': ts.get('total_offset_hours', 0),
                'Total Hours (with offset)': ts.get('total_hours_with_offset', 0)
            }
            
            # Add work dates details
            work_dates = ts.get('work_dates_hours', {})
            for date, hours in work_dates.items():
                row = base_row.copy()
                row['Date'] = date
                row['Hours Worked'] = hours
                row['Type'] = 'Work'
                export_data.append(row)
            
            # Add offset dates details
            offset_dates = ts.get('offset_dates_hours', {})
            for date, hours in offset_dates.items():
                row = base_row.copy()
                row['Date'] = date
                row['Hours Worked'] = hours
                row['Type'] = 'Offset'
                export_data.append(row)
                
            # If no work or offset dates, add summary row
            if not work_dates and not offset_dates:
                export_data.append(base_row)
        
        return export_data
    
    @classmethod
    def count_generated_timesheets(cls, vendor_ids):
        if not vendor_ids:
            return 0
        query = {
            'vendor_id': {'$in': [ObjectId(v_id) if not isinstance(v_id, ObjectId) else v_id for v_id in vendor_ids]}
        }
        return Database.count(cls.COLLECTION, query)

