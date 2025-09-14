#!/usr/bin/env python3
"""
Database initialization script for Vendor Management System
"""

import logging
import random
from bson.objectid import ObjectId
from app.utils.database import Database
from app.models.user import User
from app.models.site import Site
from app.models.department import Department
from app.models.vending_company import VendingCompany

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_email(name, prefix="ot"):
    username = ''.join(name.lower().split())
    return f"{prefix}_{username}@test.com"


def initialize_database():
    try:
        # Initialize DB Connection
        Database.initialize('mongodb://localhost:27017/vendor_management_dev')
        logger.info("Database connection established")

        # Create Site
        logger.info("Creating site 'ModiaCell Bangalore'...")
        site_id = Site.create(
            name="ModiaCell Bangalore",
            address="Bangalore, India",
            admin_user_id=""
        )
        if not site_id:
            raise Exception("Failed to create site")
        logger.info(f"Site created with ID: {site_id}")

        # Create Admin User
        logger.info("Creating Admin user...")
        admin_id = User.create(
            username="admin",
            password="admin123",
            role="admin",
            name="System Administrator",
            email=generate_email("System Administrator", prefix="admin"),
            site_id=site_id
        )
        if not admin_id:
            raise Exception("Failed to create admin user")
        logger.info(f"Admin user created with ID: {admin_id}")

        # Update site doc with admin_user_id
        Database.update_one(
            Site.COLLECTION,
            {'_id': ObjectId(site_id)},
            {'$set': {'admin_user_id': ObjectId(admin_id)}}
        )

        # Create Departments (MCB/WCY/MB1 and MCB/WCY/MB2)
        logger.info("Creating departments...")
        department_name = "MCB"
        subdepartments = ["WCY/MB1", "WCY/MB2"]
        department_ids = []
        for subdep in subdepartments:
            dep_id = Department.create(site_id, department_name, subdep, None)
            if not dep_id:
                raise Exception(f"Failed to create department {department_name}/{subdep}")
            department_ids.append(dep_id)
        logger.info(f"Departments created: {department_ids}")

        # Create Managers: Anshul Sharma and Rishi K with emp codes MCB0010 and MCB0011
        logger.info("Creating managers...")
        manager_names = ["Anshul Sharma", "Rishi K"]
        manager_emp_codes = ["MCB0010", "MCB0011"]
        manager_ids = []
        for i, name in enumerate(manager_names):
            dep_id = department_ids[i]
            mgr_id = User.create(
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
            if not mgr_id:
                raise Exception(f"Failed to create manager: {name}")
            manager_ids.append(mgr_id)
            # Update department with manager_id
            Database.update_one(
                Department.COLLECTION,
                {'_id': ObjectId(dep_id)},
                {'$set': {'manager_id': ObjectId(mgr_id)}}
            )
        logger.info(f"Managers created and assigned to departments: {manager_ids}")

        # Create two vending companies
        logger.info("Creating vending companies...")
        vending_companies = ["Global Supplies", "Premier Services"]
        vendor_company_ids = []
        for vc_name in vending_companies:
            vc_id = VendingCompany.add(site_id, vc_name)
            if not vc_id:
                raise Exception(f"Failed to create vending company: {vc_name}")
            vendor_company_ids.append(vc_id)
        logger.info(f"Vending companies created: {vendor_company_ids}")

        # Create Vendors: 4 vendors, 2 per manager, assign vending company cycling through the list
        vendor_data = [
            ("MCB0001", "Amartya Dhar"),
            ("MCB0002", "Shaik Asifa"),
            ("MCB0003", "Rahul B"),
            ("MCB0004", "Sandeep Kaushik")
        ]
        logger.info("Creating vendors...")
        for i, (emp_code, emp_name) in enumerate(vendor_data):
            manager_index = 0 if i < 2 else 1
            assigned_manager_id = manager_ids[manager_index]

            assigned_manager = User.find_by_id(assigned_manager_id)
            department_id = assigned_manager.get('department_id')
            subdepartment = assigned_manager.get('subdepartment')

            vendor_company_id = vendor_company_ids[i % len(vendor_company_ids)]  # Cycling vending company

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
        logger.info(f"Created {len(vendor_data)} vendors assigned to managers and vending companies.")

        logger.info("\n" + "=" * 60)
        logger.info("🎉 DATABASE INITIALIZED SUCCESSFULLY!")
        logger.info("=" * 60)
        logger.info("\n📋 Default Login Credentials:")
        logger.info("Admin: username='admin', password='admin123'")
        logger.info(f"Managers: {', '.join(manager_names)} with password 'password123'")
        logger.info(f"Vendors: {', '.join([v[1] for v in vendor_data])} with password 'password123'")
        logger.info("\n🚀 Start your application and login with above credentials")
        logger.info("\n" + "=" * 60)

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
        print("\n❌ Database initialization failed! See logs for details.")
