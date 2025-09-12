from bson.objectid import ObjectId
from datetime import datetime
from app.utils.database import Database

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
    def get_timesheets(cls, filters):
        query = {}
        if 'vending_company_id' in filters and filters['vending_company_id']:
            query['vending_company_id'] = ObjectId(filters['vending_company_id'])
        if 'month_year' in filters and filters['month_year']:
            query['month_year'] = filters['month_year']
        return list(Database.find(cls.COLLECTION, query))
