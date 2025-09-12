import csv
import random
from datetime import datetime, timedelta
from app.utils.database import Database
from app.models.user import User
from app.models.attendance import Attendance
# Vendor, department, vending company mapping exactly as provided
vendors = [
    {
        '_id': '68c264546afaae72715b20bd', 'employee_code': 'OT0001', 'name': 'Samuel Davis',
        'department_id': '68c264546afaae72715b20bc', 'vendor_company_id': '68c2644f6afaae72715b20a4'
    },
    {
        '_id': '68c264556afaae72715b20be', 'employee_code': 'OT0002', 'name': 'Dennis Moore',
        'department_id': '68c264546afaae72715b20b7', 'vendor_company_id': '68c2644f6afaae72715b20a5'
    },
    {
        '_id': '68c264556afaae72715b20bf', 'employee_code': 'OT0003', 'name': 'Donald Rodriguez',
        'department_id': '68c264546afaae72715b20b4', 'vendor_company_id': '68c2644f6afaae72715b20a6'
    },
    {
        '_id': '68c264566afaae72715b20c0', 'employee_code': 'OT0004', 'name': 'Patrick Mitchell',
        'department_id': '68c264546afaae72715b20b6', 'vendor_company_id': '68c2644f6afaae72715b20a7'
    },
    {
        '_id': '68c264566afaae72715b20c1', 'employee_code': 'OT0005', 'name': 'James Nguyen',
        'department_id': '68c264546afaae72715b20b5', 'vendor_company_id': '68c2644f6afaae72715b20a8'
    },
    {
        '_id': '68c264576afaae72715b20c2', 'employee_code': 'OT0006', 'name': 'Michael Johnson',
        'department_id': '68c264546afaae72715b20b6', 'vendor_company_id': '68c2644f6afaae72715b20a4'
    },
    {
        '_id': '68c264576afaae72715b20c3', 'employee_code': 'OT0007', 'name': 'Mark Anderson',
        'department_id': '68c264546afaae72715b20b5', 'vendor_company_id': '68c2644f6afaae72715b20a5'
    },
    {
        '_id': '68c264576afaae72715b20c4', 'employee_code': 'OT0008', 'name': 'Brandon Johnson',
        'department_id': '68c264546afaae72715b20bb', 'vendor_company_id': '68c2644f6afaae72715b20a6'
    },
    {
        '_id': '68c264586afaae72715b20c5', 'employee_code': 'OT0009', 'name': 'Anthony Rivera',
        'department_id': '68c264546afaae72715b20b4', 'vendor_company_id': '68c2644f6afaae72715b20a7'
    }
]

departments = {
    '68c264546afaae72715b20b3': {'name': 'BU1/D1', 'subdepartment': 'M1'},
    '68c264546afaae72715b20b4': {'name': 'BU1/D1', 'subdepartment': 'M2'},
    '68c264546afaae72715b20b5': {'name': 'BU1/D1', 'subdepartment': 'M3'},
    '68c264546afaae72715b20b6': {'name': 'BU1/D1', 'subdepartment': 'M4'},
    '68c264546afaae72715b20b7': {'name': 'BU1/D1', 'subdepartment': 'M5'},
    '68c264546afaae72715b20b8': {'name': 'BU1/D1', 'subdepartment': 'M6'},
    '68c264546afaae72715b20b9': {'name': 'BU1/D1', 'subdepartment': 'M7'},
    '68c264546afaae72715b20ba': {'name': 'BU1/D1', 'subdepartment': 'M8'},
    '68c264546afaae72715b20bb': {'name': 'BU1/D1', 'subdepartment': 'M9'},
    '68c264546afaae72715b20bc': {'name': 'BU1/D1', 'subdepartment': 'M10'}
}

vending_companies = {
    '68c2644f6afaae72715b20a4': 'ABC Corp',
    '68c2644f6afaae72715b20a5': 'XYZ Ltd',
    '68c2644f6afaae72715b20a6': 'Acme Vendors',
    '68c2644f6afaae72715b20a7': 'Global Supplies',
    '68c2644f6afaae72715b20a8': 'Premier Services'
}
attendance_statuses = [
    'In office full day',
    'Office half + work from home half',
    'Office half + leave half',
    'Work from home full',
    'Pending',
    'Leave'
]
mismatches = {
    "pending": False,
    "in_office_missing_swipe": False,
    "in_office_short_swipe": False,
    "half_office_wfh_missing_swipe": False,
    "half_office_wfh_short_swipe": False,
    "half_office_wfh_missing_wfh": False,
    "half_office_leave_missing_swipe": False,
    "half_office_leave_short_swipe": False,
    "half_office_leave_missing_leave": False,
    "wfh_missing_wfh": False,
    "leave_missing_leave": False
}

def set_approval_status_for_august(site_id):
    Database.initialize("mongodb://localhost:27017/vendor_management_dev")
    # 1. Get all attendance records for August 2025
    records = Attendance.find({
        'site_id': site_id,
        'date': {'$gte': '2025-08-01', '$lte': '2025-08-31'}
    })

    attendance_ids = [r['_id'] for r in records]
    total_count = len(attendance_ids)
    num_to_approve = int(0.9 * total_count)
    # Randomly pick 90% records for approval
    to_approve = set(random.sample(attendance_ids, num_to_approve))

    for rec in records:
        approval = "Approved" if rec['_id'] in to_approve else rec.get('approval_status', 'Pending')
        Attendance.update_status(
            user_id=rec['user_id'],
            date=rec['date'],
            status=rec['status'],
            comments=rec.get('comments',''),
            site_id=site_id
        )
        # Direct DB update for approval_status field
        Database.update_one(
            Attendance.COLLECTION,
            {'_id': rec['_id']},
            {'$set': {'approval_status': approval}}
        )

    print(f"Set 'Approved' for {num_to_approve} of {total_count} August attendance records.")

def random_time(start_h, end_h):
    h = random.randint(start_h, end_h)
    m = random.randint(0, 59)
    return f"{h:02d}:{m:02d}:00"
def calc_duration(login, logout):
    fmt = "%H:%M:%S"
    t1 = datetime.strptime(login, fmt)
    t2 = datetime.strptime(logout, fmt)
    delta = t2 - t1
    hours = delta.seconds // 3600
    mins = (delta.seconds // 60) % 60
    return f"{hours:02d}:{mins:02d}:00"
def format_swipe_record(sr_no, vendor, date_obj, login, logout, total_work, status):
    dept = departments.get(vendor['department_id'], {'name': '', 'subdepartment': ''})
    attendance_date = date_obj.strftime("%m/%d/%y")
    weekday = date_obj.strftime("%A")
    return [
        sr_no, vendor['employee_code'], vendor['name'],
        attendance_date, weekday, "G",
        login, logout,
        "00:00:00", total_work,
        status, "5", "BU1", dept['name'], dept['subdepartment']
    ]
def format_leave_excel(vendor, date_obj, full_day=True, leave_type="Casual Leave (CL)"):
    return [
        vendor['employee_code'], vendor['employee_code'],
        date_obj.strftime("%m/%d/%Y"),
        date_obj.strftime("%m/%d/%Y"),
        leave_type,
        "9:00 AM" if full_day else "1:00 PM",
        "6:00 PM" if full_day else "5:00 PM",
        8 if full_day else 4,
        "Yes" if full_day else "No",
        1 if full_day else 0.5,
        1,
        8 if full_day else 4
    ]
def format_wfh_excel(vendor, dept, date_obj, duration=1):
    return [
        vendor['name'],
        f"BU1_{dept['name']}",
        date_obj.strftime("%Y-%m-%d"),
        date_obj.strftime("%Y-%m-%d"),
        duration
    ]
def generate_august2025_attendance(site_id):
    Database.initialize("mongodb://localhost:27017/vendor_management_dev")
    aug_dates = []
    start = datetime(2025, 8, 1)
    for i in range(31):
        d = start + timedelta(days=i)
        if d.weekday() < 5:
            aug_dates.append(d)
    sr_no = 1
    attendance_ex = []
    leave_ex = []
    wfh_ex = []
    for vendor in vendors:
        for date_obj in aug_dates:
            status = random.choice(attendance_statuses)
            approval_status = "Approved" if random.random() < 0.9 else "Pending"
            # Forced mismatches included per each type only once
            if not mismatches["pending"]:
                Attendance.create(
                    user_id=vendor['_id'],
                    date=date_obj.strftime("%Y-%m-%d"),
                    status='Pending',
                    comments='',
                    site_id=site_id
                )
                mismatches["pending"] = True
                continue
            if not mismatches["in_office_missing_swipe"] and status == "In office full day":
                Attendance.create(
                    user_id=vendor['_id'],
                    date=date_obj.strftime("%Y-%m-%d"),
                    status='In office full day',
                    comments='',
                    site_id=site_id
                )
                mismatches["in_office_missing_swipe"] = True
                continue
            if not mismatches["in_office_short_swipe"] and status == "In office full day":
                login = "09:00:00"
                logout = "12:30:00"
                swipe_ex = format_swipe_record(sr_no, vendor, date_obj, login, logout, "03:30:00", "PP")
                attendance_ex.append(swipe_ex)
                Attendance.create(
                    user_id=vendor['_id'],
                    date=date_obj.strftime("%Y-%m-%d"),
                    status='In office full day',
                    comments='',
                    site_id=site_id
                )
                sr_no += 1
                mismatches["in_office_short_swipe"] = True
                continue
            if not mismatches["half_office_wfh_missing_swipe"] and status == "Office half + work from home half":
                Attendance.create(
                    user_id=vendor['_id'],
                    date=date_obj.strftime("%Y-%m-%d"),
                    status='Office half + work from home half',
                    comments='',
                    site_id=site_id
                )
                mismatches["half_office_wfh_missing_swipe"] = True
                continue
            if not mismatches["half_office_wfh_short_swipe"] and status == "Office half + work from home half":
                login = "09:00:00"
                logout = "10:45:00"
                swipe_ex = format_swipe_record(sr_no, vendor, date_obj, login, logout, "01:45:00", "PP")
                attendance_ex.append(swipe_ex)
                dept = departments[vendor['department_id']]
                wfh_ex.append(format_wfh_excel(vendor, dept, date_obj, 1))
                Attendance.create(
                    user_id=vendor['_id'],
                    date=date_obj.strftime("%Y-%m-%d"),
                    status='Office half + work from home half',
                    comments='',
                    site_id=site_id
                )
                sr_no += 1
                mismatches["half_office_wfh_short_swipe"] = True
                continue
            if not mismatches["half_office_wfh_missing_wfh"] and status == "Office half + work from home half":
                login = "09:00:00"
                logout = "12:00:00"
                swipe_ex = format_swipe_record(sr_no, vendor, date_obj, login, logout, "03:00:00", "PP")
                attendance_ex.append(swipe_ex)
                Attendance.create(
                    user_id=vendor['_id'],
                    date=date_obj.strftime("%Y-%m-%d"),
                    status='Office half + work from home half',
                    comments='',
                    site_id=site_id
                )
                sr_no += 1
                mismatches["half_office_wfh_missing_wfh"] = True
                continue
            if not mismatches["half_office_leave_missing_swipe"] and status == "Office half + leave half":
                leave_ex.append(format_leave_excel(vendor, date_obj, full_day=False, leave_type="Casual Leave (CL)"))
                Attendance.create(
                    user_id=vendor['_id'],
                    date=date_obj.strftime("%Y-%m-%d"),
                    status='Office half + leave half',
                    comments='',
                    site_id=site_id
                )
                mismatches["half_office_leave_missing_swipe"] = True
                continue
            if not mismatches["half_office_leave_short_swipe"] and status == "Office half + leave half":
                login = "09:00:00"
                logout = "10:30:00"
                swipe_ex = format_swipe_record(sr_no, vendor, date_obj, login, logout, "01:30:00", "PP")
                attendance_ex.append(swipe_ex)
                leave_ex.append(format_leave_excel(vendor, date_obj, full_day=False, leave_type="Casual Leave (CL)"))
                Attendance.create(
                    user_id=vendor['_id'],
                    date=date_obj.strftime("%Y-%m-%d"),
                    status='Office half + leave half',
                    comments='',
                    site_id=site_id
                )
                sr_no += 1
                mismatches["half_office_leave_short_swipe"] = True
                continue
            if not mismatches["half_office_leave_missing_leave"] and status == "Office half + leave half":
                login = "09:00:00"
                logout = "14:00:00"
                swipe_ex = format_swipe_record(sr_no, vendor, date_obj, login, logout, "05:00:00", "PP")
                attendance_ex.append(swipe_ex)
                Attendance.create(
                    user_id=vendor['_id'],
                    date=date_obj.strftime("%Y-%m-%d"),
                    status='Office half + leave half',
                    comments='',
                    site_id=site_id
                )
                sr_no += 1
                mismatches["half_office_leave_missing_leave"] = True
                continue
            if not mismatches["wfh_missing_wfh"] and status == "Work from home full":
                Attendance.create(
                    user_id=vendor['_id'],
                    date=date_obj.strftime("%Y-%m-%d"),
                    status='Work from home full',
                    comments='',
                    site_id=site_id
                )
                mismatches["wfh_missing_wfh"] = True
                continue
            if not mismatches["leave_missing_leave"] and status == "Leave":
                Attendance.create(
                    user_id=vendor['_id'],
                    date=date_obj.strftime("%Y-%m-%d"),
                    status='Leave',
                    comments='',
                    site_id=site_id
                )
                mismatches["leave_missing_leave"] = True
                continue
            # --- Normal data ---
            Attendance.create(
                user_id=vendor['_id'],
                date=date_obj.strftime("%Y-%m-%d"),
                status=status,
                comments='',
                site_id=site_id
            )
            dept = departments[vendor['department_id']]
            if status == "In office full day":
                login = random_time(8, 10)
                logout = random_time(17, 19)
                total_work = calc_duration(login, logout)
                swipe_ex = format_swipe_record(sr_no, vendor, date_obj, login, logout, total_work, "PP")
                attendance_ex.append(swipe_ex)
                sr_no += 1
            elif status == "Office half + work from home half":
                login = random_time(8, 10)
                logout = random_time(11, 13)
                total_work = calc_duration(login, logout)
                swipe_ex = format_swipe_record(sr_no, vendor, date_obj, login, logout, total_work, "PP")
                attendance_ex.append(swipe_ex)
                wfh_ex.append(format_wfh_excel(vendor, dept, date_obj, 0.5))
                sr_no += 1
            elif status == "Office half + leave half":
                login = random_time(8, 10)
                logout = random_time(11, 13)
                total_work = calc_duration(login, logout)
                swipe_ex = format_swipe_record(sr_no, vendor, date_obj, login, logout, total_work, "PP")
                attendance_ex.append(swipe_ex)
                leave_ex.append(format_leave_excel(vendor, date_obj, full_day=False, leave_type="Casual Leave (CL)"))
                sr_no += 1
            elif status == "Work from home full":
                wfh_ex.append(format_wfh_excel(vendor, dept, date_obj, 1))
            elif status == "Leave":
                leave_ex.append(format_leave_excel(vendor, date_obj, full_day=True, leave_type="Casual Leave (CL)"))
    # Write CSVs
    with open('attendance_swipe_aug2025.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Sr No','Employee Code','Employee Name','Attendance Date','Weekday',
            'Shift Code','Login','Logout','Extra Work Hours','Total Working Hours',
            'Attendance Status','Floor','Business Unit','Department','Subdepartment'
        ])
        for r in attendance_ex:
            writer.writerow(r)
    with open('leave_data_aug2025.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'OT ID','Personnel Number','Start Date','End Date','Attendance or Absence Type','Start Time',
            'End Time','Hrs','Record is for full day','Days','Cal.days','Payroll hrs'
        ])
        for i, r in enumerate(leave_ex):
            writer.writerow([f"OT{i+1:04d}", *r])
    with open('wfh_data_aug2025.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Name','Department','Start Date','End Date','Duration'])
        for r in wfh_ex:
            writer.writerow(r)
    print("Generated attendance and CSV data with mismatches.")
if __name__ == "__main__":
    generate_august2025_attendance("68c2644e6afaae72715b20a2")
    set_approval_status_for_august("68c2644e6afaae72715b20a2")
