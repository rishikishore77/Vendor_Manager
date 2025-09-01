#!/usr/bin/env python3
"""
Database initialization script for Vendor Management System
"""

import random
import logging
from app.utils.database import Database
from app.models.user import User
from app.models.site import Site
from app.models.department import Department
from app.models.vending_company import VendingCompany
from bson.objectid import ObjectId

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_database():
    """Initialize database with sample data"""

    try:
        # Connect to database
        Database.initialize('mongodb://localhost:27017/vendor_management_dev')
        logger.info("Database connection established")

        # Create sample site
        logger.info("Creating sample site...")
        site_id = Site.create(
            name="Main Office",
            address="123 Business St, City, State 12345",
            admin_user_id=""
        )
        if not site_id:
            raise Exception("Failed to create site")
        logger.info(f"Site created with ID: {site_id}")

        # Create admin user
        logger.info("Creating admin user...")
        admin_id = User.create(
            username="admin1",
            password="password123",
            role="admin",
            name="System Administrator",
            site_id=site_id
        )
        if not admin_id:
            raise Exception("Failed to create admin user")
        logger.info(f"Admin user created with ID: {admin_id}")

        # Initialize vending companies for the site
        logger.info("Creating vending companies...")
        fixed_vendor_companies = [
            "ABC Corp",
            "XYZ Ltd",
            "Acme Vendors",
            "Global Supplies",
            "Premier Services"
        ]
        vendor_company_ids = []
        for vc_name in fixed_vendor_companies:
            vc_id = VendingCompany.add(site_id, vc_name)
            if not vc_id:
                raise Exception(f"Failed to create vending company: {vc_name}")
            vendor_company_ids.append(vc_id)
        logger.info(f"Vending companies created: {vendor_company_ids}")

        # Create departments (with manager assignment)
        logger.info("Creating departments with managers...")
        # Manager names and departments/subdepartments
        manager_names = [
            "Alice Johnson", "Bob Smith", "Carol Lee", "David Kim", "Eva Brown",
            "Frank Adams", "Grace Miller", "Henry Clark", "Irene Turner", "Jack Harris"
        ]
        subdepartments = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10"]
        department_ids = []
        manager_ids = []

        # Create managers first with no department assigned yet
        for i, name in enumerate(manager_names):
            manager_id = User.create(
                username=f"manager{i+1}",
                password="password123",
                role="manager",
                name=name,
                site_id=site_id,
                department_id=None,  # will assign below after department creation
                subdepartment=subdepartments[i % len(subdepartments)]
            )
            if not manager_id:
                raise Exception(f"Failed to create manager: {name}")
            manager_ids.append(manager_id)

        # Now create departments and assign managers to them, record in department collection including manager history
        for i, manager_id in enumerate(manager_ids):
            dept_name = "BU1/D1"
            subdept = subdepartments[i % len(subdepartments)]
            dept_id = Department.create(site_id, dept_name, subdept, manager_id)
            if not dept_id:
                raise Exception(f"Failed to create department {dept_name}/{subdept}")
            department_ids.append(dept_id)
            # Update manager's department_id to link
            Database.update_one(User.COLLECTION, {'_id': ObjectId(manager_id)}, {'$set': {'department_id': dept_id}})
        logger.info(f"Departments created and managers assigned: {department_ids}")

        # Vendor user data: [Employee Code, Employee Name, Department Index, Subdepartment Index]
        vendor_data = [
            ["OT0001", "Samuel Davis", 0, 0],
            ["OT0002", "Dennis Moore", 0, 3],
            ["OT0003", "Donald Rodriguez", 0, 1],
            ["OT0004", "Patrick Mitchell", 0, 8],
            ["OT0005", "James Nguyen", 0, 6],
            ["OT0006", "Michael Johnson", 0, 1],
            ["OT0007", "Mark Anderson", 0, 8],
            ["OT0008", "Brandon Johnson", 0, 8],
            ["OT0009", "Anthony Rivera", 0, 8],
            ["OT0010", "Jason Anderson", 0, 7],
            # ... More vendors as you had
        ]

        # Create vendors and assign random manager + assign department and vendor company refs
        logger.info("Creating vendor users...")
        for i, (emp_code, emp_name, dept_idx, subdept_idx) in enumerate(vendor_data):
            # Use departments list indexed by dept_idx for department_id (all BU1/D1) and subdepartment in original data
            department_id = department_ids[dept_idx]  # all BU1/D1 here
            # For subdepartment, we are storing as field on user, can store string or ref if desired
            subdepartment_val = subdepartments[subdept_idx]
            assigned_manager = random.choice(manager_ids)
            # Cycle vendor_company_ids
            vendor_company_id = vendor_company_ids[i % len(vendor_company_ids)]

            User.create(
                username=emp_code.lower(),
                password="password123",
                role="vendor",
                name=emp_name,
                site_id=site_id,
                manager_id=assigned_manager,
                vendor_company_id=vendor_company_id,
                employee_code=emp_code,
                department_id=department_id,
                subdepartment=subdepartment_val
            )
        logger.info(f"{len(vendor_data)} vendor users created and assigned to managers and companies.")

        logger.info("\n" + "="*60)
        logger.info("🎉 DATABASE INITIALIZED SUCCESSFULLY!")
        logger.info("="*60)
        logger.info("\n📋 Default Login Credentials:")
        logger.info("-" * 40)
        logger.info("🔧 Admin:    admin1    / password123")
        logger.info("👥 Managers: manager1 ... manager10 / password123")
        logger.info("👤 Vendors:  demo vendor users / password123")
        logger.info("-" * 40)
        logger.info("\n🚀 Next Steps:")
        logger.info("1. Start the application: python app.py")
        logger.info("2. Access: http://localhost:5000")
        logger.info("3. Login with any of the above credentials")
        logger.info("\n" + "="*60)

        return True

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


if __name__ == "__main__":
    success = initialize_database()
    if success:
        print("\n✅ Database initialization completed successfully!")
        print("🚀 You can now start the application with: python app.py")
    else:
        print("\n❌ Database initialization failed!")
        print("Please check the error messages above and try again.")
