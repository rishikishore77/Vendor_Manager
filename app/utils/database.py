"""Database connection and utilities"""
from pymongo import MongoClient
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Database:
    """Database connection manager"""

    URI = None
    DATABASE = None

    @staticmethod
    def initialize(uri):
        """Initialize database connection"""
        try:
            Database.URI = uri
            client = MongoClient(uri)
            Database.DATABASE = client.get_default_database()
            logger.info("Database connection established successfully")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise

    @staticmethod
    def get_collection(collection_name):
        """Get a collection from the database"""
        if Database.DATABASE is None:
            raise RuntimeError("Database not initialized")
        return Database.DATABASE[collection_name]

    @staticmethod
    def insert_one(collection_name, document):
        """Insert a single document"""
        try:
            collection = Database.get_collection(collection_name)
            document['created_at'] = datetime.utcnow()
            if 'updated_at' not in document:
                document['updated_at'] = datetime.utcnow()
            result = collection.insert_one(document)
            return result.inserted_id
        except Exception as e:
            logger.error(f"Insert error in {collection_name}: {e}")
            return None

    @staticmethod
    def find_one(collection_name, query):
        """Find a single document"""
        try:
            collection = Database.get_collection(collection_name)
            return collection.find_one(query)
        except Exception as e:
            logger.error(f"Find one error in {collection_name}: {e}")
            return None

    @staticmethod
    def find(collection_name, query=None, sort=None, limit=None):
        """Find multiple documents"""
        try:
            collection = Database.get_collection(collection_name)
            cursor = collection.find(query or {})
            if sort:
                cursor = cursor.sort(sort)
            if limit:
                cursor = cursor.limit(limit)
            return list(cursor)
        except Exception as e:
            logger.error(f"Find error in {collection_name}: {e}")
            return []

    @staticmethod
    def update_one(collection_name, query, update):
        """Update a single document"""
        try:
            collection = Database.get_collection(collection_name)
            update.setdefault('$set', {})['updated_at'] = datetime.utcnow()
            result = collection.update_one(query, update)
            return result.modified_count
        except Exception as e:
            logger.error(f"Update error in {collection_name}: {e}")
            return 0
