# app/utils/data_upload_processor.py
import pandas as pd
from datetime import datetime
from app.models.swipe_data import SwipeData
from app.models.wfh_data import WFHData
from app.models.leave_data import LeaveData
from app.models.user import User
from app.models.monthly_cycle import MonthlyCycle
import logging

logger = logging.getLogger(__name__)

class DataUploadProcessor:
    """Process CSV/Excel data uploads for swipe, WFH, and leave data"""

    @classmethod
    def process_upload(cls, file, data_type, month_year, site_id):
        """Main method to process file upload based on data type"""
        try:
            # Read file based on extension
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file)
            elif file.filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file)
            else:
                return {'success': False, 'error': 'Unsupported file format'}

            if data_type == 'swipe_data':
                result = cls._process_swipe_data(df, month_year, site_id)
            elif data_type == 'wfh_data':
                result = cls._process_wfh_data(df, month_year, site_id)
            elif data_type == 'leave_data':
                result = cls._process_leave_data(df, month_year, site_id)
            else:
                return {'success': False, 'error': 'Invalid data type'}

            # Update monthly cycle upload status
            if result['success']:
                cycle = MonthlyCycle.get_by_month(site_id, month_year)
                if not cycle:
                    MonthlyCycle.create_cycle(site_id, month_year)
                MonthlyCycle.update_upload_status(site_id, month_year, data_type)

            return result

        except Exception as e:
            logger.error(f"Error processing upload: {str(e)}")
            return {'success': False, 'error': str(e)}

    @classmethod
    def _process_swipe_data(cls, df, month_year, site_id):
        """Process swipe data CSV/Excel file"""
        try:
            # Clear existing data for the month
            SwipeData.delete_by_month(month_year)

            processed_count = 0
            swipe_records = []

            # Expected columns (adjust based on your CSV format)
            required_columns = ['Employee Code', 'Employee Name', 'Attendance Date', 'Login', 'Logout', 'Total Working Hours']

            # Validate columns
            if not all(col in df.columns for col in required_columns):
                missing_cols = [col for col in required_columns if col not in df.columns]
                return {'success': False, 'error': f'Missing columns: {missing_cols}'}

            for _, row in df.iterrows():
                employee_code = str(row['Employee Code'])
                user = User.find_by_employee_code(employee_code)

                if not user:
                    logger.warning(f"User not found for employee code: {employee_code}")
                    continue

                # Parse date
                try:
                    if isinstance(row['Attendance Date'], str):
                        # Handle different date formats
                        if len(row['Attendance Date']) == 6:  # DDMMYY
                            date_str = row['Attendance Date']
                            date_obj = datetime.strptime(f"20{date_str[4:]}-{date_str[2:4]}-{date_str[:2]}", "%Y-%m-%d")
                        else:
                            date_obj = pd.to_datetime(row['Attendance Date'])
                    else:
                        date_obj = pd.to_datetime(row['Attendance Date'])

                    date_str = date_obj.strftime("%Y-%m-%d")
                except:
                    logger.warning(f"Invalid date format for {employee_code}: {row['Attendance Date']}")
                    continue

                # Parse login/logout times
                login_time = cls._parse_time(row['Login'])
                logout_time = cls._parse_time(row['Logout'])

                # Parse total hours
                try:
                    total_hours = float(row['Total Working Hours'])
                except:
                    total_hours = 0.0

                swipe_record = {
                    'employee_code': employee_code,
                    'user_id': user['_id'],
                    'date': date_str,
                    'login': login_time,
                    'logout': logout_time,
                    'total_hours': total_hours,
                    'month_year': month_year,
                    'uploaded_at': datetime.utcnow()
                }

                swipe_records.append(swipe_record)
                processed_count += 1

            # Bulk insert records
            if swipe_records:
                SwipeData.bulk_insert(swipe_records)

            return {'success': True, 'count': processed_count}

        except Exception as e:
            logger.error(f"Error processing swipe data: {str(e)}")
            return {'success': False, 'error': str(e)}

    @classmethod
    def _process_wfh_data(cls, df, month_year, site_id):
        """Process WFH data CSV/Excel file"""
        try:
            # Clear existing data for the month
            WFHData.delete_by_month(month_year)

            processed_count = 0
            wfh_records = []

            # Expected columns (adjust based on your CSV format)
            required_columns = ['Name', 'Start Date', 'End Date', 'Duration']

            # Validate columns
            if not all(col in df.columns for col in required_columns):
                missing_cols = [col for col in required_columns if col not in df.columns]
                return {'success': False, 'error': f'Missing columns: {missing_cols}'}

            for _, row in df.iterrows():
                employee_name = str(row['Name']).strip()

                # Find user by name (you might want to use employee code instead)
                user = User.find_one({'name': {'$regex': employee_name, '$options': 'i'}})

                if not user:
                    logger.warning(f"User not found for name: {employee_name}")
                    continue

                # Parse date
                try:
                    start_date_obj = pd.to_datetime(row['Start Date'])
                    start_date_str = start_date_obj.strftime("%Y-%m-%d")
                    end_date_obj = pd.to_datetime(row['End Date'])
                    end_date_str = end_date_obj.strftime("%Y-%m-%d")
                except:
                    logger.warning(f"Invalid date format for {employee_name}: {row['Start Date']}")
                    continue

                # Parse duration
                try:
                    duration = float(row['Duration'])
                except:
                    duration = 0.5  # Default half day

                wfh_record = {
                    'employee_code': user.get('employee_code', ''),
                    'user_id': user['_id'],
                    'start_date': start_date_str,
                    'end_date': end_date_str,
                    'duration': duration,
                    'month_year': month_year,
                    'uploaded_at': datetime.utcnow()
                }

                wfh_records.append(wfh_record)
                processed_count += 1

            # Bulk insert records
            if wfh_records:
                WFHData.bulk_insert(wfh_records)

            return {'success': True, 'count': processed_count}

        except Exception as e:
            logger.error(f"Error processing WFH data: {str(e)}")
            return {'success': False, 'error': str(e)}

    @classmethod
    def _process_leave_data(cls, df, month_year, site_id):
        """Process leave data CSV/Excel file with AM/PM time parsing"""
        try:
            # Clear existing data for the month
            LeaveData.delete_by_month(month_year)

            processed_count = 0
            leave_records = []

            required_columns = ['Personnel Number', 'Start Date', 'End Date', 'Attendance or Absence Type',
                                'Start Time', 'End Time', 'Days']

            if not all(col in df.columns for col in required_columns):
                missing_cols = [col for col in required_columns if col not in df.columns]
                return {'success': False, 'error': f'Missing columns: {missing_cols}'}

            def parse_time_ampm(time_str):
                try:
                    return datetime.strptime(time_str.strip(), '%I:%M %p').time()
                except Exception as e:
                    logger.warning(f"Error parsing time '{time_str}': {e}")
                    return datetime.strptime('00:00', '%H:%M').time()

            for _, row in df.iterrows():
                employee_code = str(row['Personnel Number'])
                user = User.find_by_employee_code(employee_code)
                if not user:
                    logger.warning(f"User not found for employee code: {employee_code}")
                    continue

                try:
                    start_date = pd.to_datetime(row['Start Date']).strftime("%Y-%m-%d")
                    end_date = pd.to_datetime(row['End Date']).strftime("%Y-%m-%d")

                    start_time_str = str(row.get('Start Time', '12:00 AM')).strip()
                    end_time_str = str(row.get('End Time', '11:59 PM')).strip()

                    start_time = parse_time_ampm(start_time_str)
                    end_time = parse_time_ampm(end_time_str)

                except Exception as e:
                    logger.warning(f"Invalid date/time for {employee_code}: {e}")
                    continue

                leave_type = str(row['Attendance or Absence Type'])
                try:
                    duration = float(row['Days'])
                except:
                    duration = 1.0

                is_full_day = duration >= 1.0

                leave_record = {
                    'employee_code': employee_code,
                    'user_id': user['_id'],
                    'start_date': start_date,
                    'start_time': str(start_time),
                    'end_date': end_date,
                    'end_time': str(end_time),
                    'leave_type': leave_type,
                    'duration': duration,
                    'is_full_day': is_full_day,
                    'month_year': month_year,
                    'uploaded_at': datetime.utcnow()
                }

                leave_records.append(leave_record)
                processed_count += 1

            if leave_records:
                LeaveData.bulk_insert(leave_records)

            return {'success': True, 'count': processed_count}

        except Exception as e:
            logger.error(f"Error processing leave data: {str(e)}")
            return {'success': False, 'error': str(e)}


    @classmethod
    def _parse_time(cls, time_value):
        """Parse time value to HH:MM format"""
        if pd.isna(time_value):
            return "00:00"

        try:
            # Handle different time formats
            time_str = str(time_value).strip()

            if len(time_str) == 6:  # HHMMSS
                return f"{time_str[:2]}:{time_str[2:4]}"
            elif len(time_str) == 4:  # HHMM
                return f"{time_str[:2]}:{time_str[2:]}"
            elif ':' in time_str:  # Already formatted
                return time_str.split(':')[0] + ':' + time_str.split(':')[1]
            else:
                return "00:00"
        except:
            return "00:00"
