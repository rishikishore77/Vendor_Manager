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


def generate_email(name, prefix="ot"):
    username = ''.join(name.lower().split())
    return f"{prefix}_{username}@test.com"


def initialize_database():
    """Initialize database with sample data"""

    try:
        # Connect to database
        Database.initialize('mongodb://localhost:27017/vendor_management_dev')
        logger.info("Database connection established")

        # Create single site ModiaCell Bangalore
        logger.info("Creating site 'ModiaCell Bangalore'...")
        site_id = Site.create(
            name="ModiaCell Bangalore",
            address="Bangalore, India",
            admin_user_id=""
        )
        if not site_id:
            raise Exception("Failed to create site")
        logger.info(f"Site created with ID: {site_id}")

        # Create two managers: Anshul Sharma and Rishi K
        logger.info("Creating managers...")
        manager_names = ["Anshul Sharma", "Rishi K"]
        manager_emp_codes = ["MCB0010", "MCB0011"]
        department_name = "MCB"
        subdepartments = ["WCY/MB1", "WCY/MB2"]

        manager_ids = []
        department_ids = []

        # Create departments first (to assign to managers)
        for i, subdept in enumerate(subdepartments):
            dept_id = Department.create(site_id, department_name, subdept, None)
            if not dept_id:
                raise Exception(f"Failed to create department {department_name}/{subdept}")
            department_ids.append(dept_id)
        logger.info(f"Departments created: {department_ids}")

        for i, name in enumerate(manager_names):
            dep_id = department_ids[i]
            manager_id = User.create(
                username=manager_emp_codes[i].lower(),
                password="password123",
                role="manager",
                name=name,
                email=generate_email(name, prefix=""),
                site_id=site_id,
                department_id=str(dep_id),
                employee_code=manager_emp_codes[i],
                subdepartment=subdepartments[i]
            )
            if not manager_id:
                raise Exception(f"Failed to create manager: {name}")
            manager_ids.append(manager_id)
            # Update department's manager_id
            Department.assign_manager(dep_id, manager_id)
        logger.info(f"Managers created and assigned to departments: {manager_ids}")

        # Create vending companies (optional, can keep empty or add some)
        logger.info("Creating vending companies...")
        vending_companies = ["Default VC"]
        vendor_company_ids = []
        for vc_name in vending_companies:
            vc_id = VendingCompany.add(site_id, vc_name)
            if not vc_id:
                raise Exception(f"Failed to create vending company: {vc_name}")
            vendor_company_ids.append(vc_id)
        logger.info(f"Vending company created: {vendor_company_ids}")

        # Vendor data (2 per manager)
        vendor_data = [
            ("MCB0001", "Amartya Dhar"),
            ("MCB0002", "Shaik Asifa"),
            ("MCB0003", "Rahul B"),
            ("MCB0004", "Sandeep Kaushik")
        ]

        # Create vendors and assign managers and departments accordingly
        logger.info("Creating vendors and assigning managers and departments...")
        for i, (emp_code, emp_name) in enumerate(vendor_data):
            manager_index = 0 if i < 2 else 1  # first two vendors to first manager, next two to second manager
            assigned_manager_id = manager_ids[manager_index]
            # Fetch manager's department and subdepartment
            assigned_manager = User.find_by_id(assigned_manager_id)
            department_id = assigned_manager.get('department_id')
            subdepartment = assigned_manager.get('subdepartment')

            vendor_company_id = vendor_company_ids[0]  # assigning default vending company

            User.create(
                username=emp_code.lower(),
                password="password123",
                role="vendor",
                name=emp_name,
                email=generate_email(emp_name),
                site_id=site_id,
                manager_id=assigned_manager_id,
                vendor_company_id=vendor_company_id,
                employee_code=emp_code,
                department_id=str(department_id),
                subdepartment=subdepartment
            )
        logger.info(f"Created {len(vendor_data)} vendor users assigned to managers and companies.")

        logger.info("\n" + "="*60)
        logger.info("🎉 DATABASE INITIALIZED SUCCESSFULLY!")
        logger.info("="*60)
        logger.info("\n📋 Default Login Credentials:")
        logger.info("-" * 40)
        logger.info("🔧 Admin user must be created separately or via admin interface")
        logger.info(f"👥 Managers: {', '.join(manager_names)} / passwords: password123")
        logger.info(f"👤 Vendors: {', '.join([v[1] for v in vendor_data])} / passwords: password123")
        logger.info("-" * 40)
        logger.info("\n🚀 Next Steps:")
        logger.info("1. Start the application: python app.py")
        logger.info("2. Access: http://localhost:5000")
        logger.info("3. Login with above credentials")
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
        print("\n❌ Database initialization failed! Check log for details.")
