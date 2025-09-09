from datetime import date
from app.utils.database import Database
from app.models.user import User
from app.models.attendance import Attendance

def create_pending_attendance_for_day(target_date=None, site_id=None):
    if target_date is None:
        target_date = date.today().strftime("%Y-%m-%d")
    if site_id is None:
        raise ValueError("site_id must be provided")
    vendors = User.find({'site_id': site_id, 'role': 'vendor'})
    for vendor in vendors:
        user_id_str = str(vendor['_id'])
        existing = Attendance.find_by_user_and_date(user_id_str, target_date)
        if existing:
            continue
        Attendance.create(
            user_id=user_id_str,
            date=target_date,
            status='Pending',
            comments='',
            site_id=site_id
        )
    print(f"Pending attendance records created for {len(vendors)} vendors on {target_date} (site {site_id})")

def get_all_site_ids():
    collection = Database.get_collection('users')
    site_ids = collection.distinct('site_id', {'role': 'vendor'})
    return site_ids

if __name__ == "__main__":
    Database.initialize("mongodb://localhost:27017/vendor_management_dev")
    site_ids = get_all_site_ids()
    for site_id in site_ids:
        create_pending_attendance_for_day(site_id=site_id)
