#!/usr/bin/env python3
"""
Database initialization script for Vendor Management System
"""

from app.utils.database import Database
from app.models.user import User
from app.models.site import Site
from datetime import datetime
import logging

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

        # Create manager user
        logger.info("Creating manager user...")
        manager_id = User.create(
            username="manager1",
            password="password123",
            role="manager",
            name="Alice Johnson",
            site_id=site_id,
            department="Operations"
        )

        logger.info(f"Manager created with ID: {manager_id}")

        # Create vendor users
        logger.info("Creating vendor users...")
        vendor1_id = User.create(
            username="vendor1",
            password="password123",
            role="vendor",
            name="John Doe",
            site_id=site_id,
            manager_id=manager_id,
            vendor_company="ABC Corp",
            employee_code="EMP001",
            department="IT"
        )

        vendor2_id = User.create(
            username="vendor2",
            password="password123",
            role="vendor",
            name="Jane Smith",
            site_id=site_id,
            manager_id=manager_id,
            vendor_company="XYZ Ltd",
            employee_code="EMP002",
            department="IT"
        )

        logger.info(f"Vendors created: {vendor1_id}, {vendor2_id}")

        logger.info("\n" + "="*60)
        logger.info("🎉 DATABASE INITIALIZED SUCCESSFULLY!")
        logger.info("="*60)
        logger.info("\n📋 Default Login Credentials:")
        logger.info("-" * 40)
        logger.info("🔧 Admin:    admin1    / password123")
        logger.info("👥 Manager:  manager1  / password123")
        logger.info("👤 Vendor1:  vendor1   / password123")
        logger.info("👤 Vendor2:  vendor2   / password123")
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
