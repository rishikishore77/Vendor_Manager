from datetime import date, timedelta
from app.utils.database import Database
from app.models.user import User
from app.models.attendance import Attendance
from app.models.holiday import Holiday  # Import your Holiday class


def is_weekend(date_obj):
    # Saturday=5, Sunday=6
    return date_obj.weekday() >= 5


def create_pending_attendance_for_day(target_date=None, site_id=None):
    if target_date is None:
        target_date = date.today().strftime("%Y-%m-%d")
    if site_id is None:
        raise ValueError("site_id must be provided")

    date_obj = date.fromisoformat(target_date)

    # Skip weekends
    if is_weekend(date_obj):
        print(f"Skipping weekend date {target_date}")
        return

    # Get holidays for site and year
    holidays = Holiday.get_year(site_id, date_obj.year)
    holiday_dates = {h['date'] for h in holidays}

    # Skip if holiday
    if target_date in holiday_dates:
        print(f"Skipping holiday date {target_date} for site {site_id}")
        return

    vendors = User.find({'site_id': site_id, 'role': 'vendor'})
    for vendor in vendors:
        user_id = str(vendor['_id'])
        existing_attendance = Attendance.find_by_user_and_date(user_id, target_date)
        if existing_attendance:
            continue
        Attendance.create(
            user_id=user_id,
            date=target_date,
            status='Pending',
            comments='',
            site_id=site_id
        )

    print(f"Created pending attendance for {len(vendors)} vendors on {target_date} (site {site_id})")


def get_all_site_ids():
    collection = Database.get_collection('users')
    return collection.distinct('site_id', {'role': 'vendor'})


if __name__ == "__main__":
    Database.initialize("mongodb://localhost:27017/vendor_management_dev")

    start_date = date(2025, 8, 1)
    end_date = date.today()

    site_ids = get_all_site_ids()

    current_date = start_date
    while current_date <= end_date:
        current_date_str = current_date.strftime("%Y-%m-%d")
        for site_id in site_ids:
            create_pending_attendance_for_day(target_date=current_date_str, site_id=site_id)
        current_date += timedelta(days=1)
