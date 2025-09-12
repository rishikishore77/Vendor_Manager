# app/utils/workday_calculator.py
from app.models.attendance import Attendance
from app.models.user import User
from app.models.vending_company import VendingCompany
from app.models.system_config import SystemConfig
from app.utils.database import Database
from bson.objectid import ObjectId
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

class WorkdayCalculator:
    """Calculate workdays and generate reports for vending companies"""

    @classmethod
    def calculate_monthly_workdays(cls, site_id, month_year):
        """Calculate final workdays for all vendors in a month"""
        try:
            # Get all finalized attendance (resolved mismatches) 
            attendance_records = cls._get_finalized_attendance(site_id, month_year)

            vendor_workdays = {}
            vendor_details = {}

            for record in attendance_records:
                user_id = str(record['user_id'])
                final_status = record.get('final_status', record['status'])

                # Get workday value based on final status
                workday_value = cls.get_workday_value(final_status)

                if user_id not in vendor_workdays:
                    vendor_workdays[user_id] = {
                        'total_workdays': 0.0,
                        'office_days': 0,
                        'wfh_days': 0,
                        'leave_days': 0,
                        'half_days': 0,
                        'records': []
                    }

                vendor_workdays[user_id]['total_workdays'] += workday_value
                vendor_workdays[user_id]['records'].append({
                    'date': record['date'],
                    'status': final_status,
                    'workday_value': workday_value
                })

                # Count different types of days
                if final_status == "In office full day":
                    vendor_workdays[user_id]['office_days'] += 1
                elif final_status == "Work from home full":
                    vendor_workdays[user_id]['wfh_days'] += 1
                elif final_status == "Leave":
                    vendor_workdays[user_id]['leave_days'] += 1
                elif "half" in final_status.lower():
                    vendor_workdays[user_id]['half_days'] += 1

            # Get vendor details and group by company
            company_workdays = cls._group_by_vending_company(vendor_workdays, site_id)

            return {
                'month_year': month_year,
                'individual_workdays': vendor_workdays,
                'company_summary': company_workdays,
                'total_vendors': len(vendor_workdays),
                'calculation_date': datetime.utcnow()
            }

        except Exception as e:
            logger.error(f"Error calculating workdays: {str(e)}")
            return None

    @classmethod
    def get_workday_value(cls, status):
        """Return workday value based on attendance status"""
        wfh_rate = SystemConfig.get_setting("wfh_workday_rate", 0.8)

        if status == "In office full day":
            return 1.0
        elif status in ["Office half + work from home half", "Office half + leave half"]:
            return 0.5
        elif status == "Work from home full":
            return wfh_rate
        elif status == "Leave":
            return 0.0
        else:
            return 0.0  # Default for unrecognized status

    @classmethod
    def _get_finalized_attendance(cls, site_id, month_year):
        """Get all finalized attendance records for the month"""
        start_date = f"{month_year}-01"
        end_date = f"{month_year}-31"  # Should be improved for proper month end

        # Get records where mismatches are resolved OR no mismatches exist
        query = {
            "site_id": ObjectId(site_id),
            "date": {"$gte": start_date, "$lte": end_date},
            "$or": [
                {"is_mismatch": {"$ne": True}},  # No mismatch
                {"mismatch_resolved": True}      # Mismatch resolved
            ]
        }

        return Database.find("attendance", query, sort=[("date", 1)])

    @classmethod
    def _group_by_vending_company(cls, vendor_workdays, site_id):
        """Group workday data by vending company"""
        company_data = {}

        # Get all vendors
        vendors = User.find({"site_id": ObjectId(site_id), "role": "vendor"})

        for vendor in vendors:
            user_id = str(vendor['_id'])
            vendor_company_id = vendor.get('vendor_company_id')

            if not vendor_company_id:
                continue

            # Get company details
            company = VendingCompany.find_by_id(vendor_company_id)
            if not company:
                continue

            company_name = company['name']
            company_id = str(vendor_company_id)

            if company_id not in company_data:
                company_data[company_id] = {
                    'company_name': company_name,
                    'total_workdays': 0.0,
                    'vendor_count': 0,
                    'vendors': []
                }

            # Add vendor workday data
            if user_id in vendor_workdays:
                vendor_data = vendor_workdays[user_id]
                company_data[company_id]['total_workdays'] += vendor_data['total_workdays']
                company_data[company_id]['vendor_count'] += 1
                company_data[company_id]['vendors'].append({
                    'name': vendor['name'],
                    'employee_code': vendor.get('employee_code', ''),
                    'workdays': vendor_data['total_workdays'],
                    'office_days': vendor_data['office_days'],
                    'wfh_days': vendor_data['wfh_days'],
                    'leave_days': vendor_data['leave_days'],
                    'half_days': vendor_data['half_days']
                })

        return company_data

    @classmethod
    def generate_workday_report(cls, site_id, month_year, format='dict'):
        """Generate comprehensive workday report"""
        workday_data = cls.calculate_monthly_workdays(site_id, month_year)

        if not workday_data:
            return None

        if format == 'dict':
            return workday_data
        elif format == 'csv':
            return cls._generate_csv_report(workday_data)
        elif format == 'excel':
            return cls._generate_excel_report(workday_data)

        return workday_data

    @classmethod
    def _generate_csv_report(cls, workday_data):
        """Generate CSV format report"""
        import io
        import csv

        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow([
            'Company', 'Employee Code', 'Employee Name', 
            'Total Workdays', 'Office Days', 'WFH Days', 
            'Leave Days', 'Half Days'
        ])

        # Write data
        for company_data in workday_data['company_summary'].values():
            for vendor in company_data['vendors']:
                writer.writerow([
                    company_data['company_name'],
                    vendor['employee_code'],
                    vendor['name'],
                    vendor['workdays'],
                    vendor['office_days'], 
                    vendor['wfh_days'],
                    vendor['leave_days'],
                    vendor['half_days']
                ])

        output.seek(0)
        return output.getvalue()

    @classmethod
    def calculate_offset(cls, site_id, month_year, expected_workdays):
        """Calculate offset for next month based on over/under work"""
        workday_data = cls.calculate_monthly_workdays(site_id, month_year)

        if not workday_data:
            return {}

        offset_data = {}

        for company_id, company_data in workday_data['company_summary'].items():
            actual_workdays = company_data['total_workdays']
            offset = actual_workdays - expected_workdays

            offset_data[company_id] = {
                'company_name': company_data['company_name'],
                'expected_workdays': expected_workdays,
                'actual_workdays': actual_workdays,
                'offset': offset,
                'offset_type': 'credit' if offset > 0 else 'debit'
            }

        return offset_data
