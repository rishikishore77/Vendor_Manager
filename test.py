# Import ObjectId if needed
from bson.objectid import ObjectId
from app.models.user import User
from app.utils.database import Database

def print_managers_department_ids():
    Database.initialize('mongodb://localhost:27017/vendor_management_dev')
    # Query all users with role 'manager'
    managers = User.find({'role': 'manager'})

    # Iterate over managers and print their ID and department_id
    for m in managers:
        manager_id = m.get('_id')
        dept_id = m.get('department_id')
        print(f"Manager ID: {manager_id} | Department ID: {dept_id} | Department ID Type: {type(dept_id)}")

# Call the function to execute
print_managers_department_ids()
