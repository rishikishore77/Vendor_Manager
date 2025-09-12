# app/models/system_config.py
from app.utils.database import Database
from datetime import datetime

class SystemConfig:
    COLLECTION = "system_config"

    DEFAULT_SETTINGS = {
        "mismatch_resolution_deadline_days": 7,
        "manager_approval_deadline_days": 3,
        "default_expired_mismatch_status": "Leave",
        "minimum_office_hours": 4.0,
        "minimum_half_office_hours": 2.0,
        "minimum_half_leave_hours": 3.0,
        "minimum_full_leave_hours": 6.0,
        "wfh_workday_rate": 0.8,
        "auto_approve_expired_manager_approvals": True
    }

    @classmethod
    def get_setting(cls, key, default=None):
        """Get a system setting value"""
        setting = Database.find_one(cls.COLLECTION, {"key": key})
        if setting:
            return setting.get("value", default)
        return cls.DEFAULT_SETTINGS.get(key, default)

    @classmethod  
    def update_setting(cls, key, value):
        """Update or create a system setting"""
        return Database.update_one(
            cls.COLLECTION, 
            {"key": key}, 
            {"$set": {"value": value, "updated_at": datetime.utcnow()}},
            upsert=True
        )

    @classmethod
    def get_all_settings(cls):
        """Get all system settings"""
        settings = Database.find(cls.COLLECTION)
        settings_dict = cls.DEFAULT_SETTINGS.copy()

        for setting in settings:
            settings_dict[setting["key"]] = setting["value"]

        return settings_dict

    @classmethod
    def initialize_default_settings(cls):
        """Initialize system with default settings"""
        for key, value in cls.DEFAULT_SETTINGS.items():
            existing = Database.find_one(cls.COLLECTION, {"key": key})
            if not existing:
                Database.insert_one(cls.COLLECTION, {
                    "key": key,
                    "value": value,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                })
