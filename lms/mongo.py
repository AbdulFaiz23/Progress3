import os
import logging
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from django.conf import settings
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Initialize MongoDB client lazily
_mongo_client = None

def get_mongo_db():
    global _mongo_client
    try:
        if _mongo_client is None:
            uri = getattr(settings, "MONGO_URI", "mongodb://localhost:27017/")
            _mongo_client = MongoClient(uri, serverSelectionTimeoutMS=2000)
        
        db_name = getattr(settings, "MONGO_DB_NAME", "lms_logs")
        return _mongo_client[db_name]
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        return None

def log_activity(user, action, resource_type, resource_id=None, metadata=None, request=None):
    """
    Logs an activity to the activity_logs collection in MongoDB.
    Safely ignores if MongoDB is unavailable.
    """
    try:
        db = get_mongo_db()
        if db is None:
            return

        ip_address = None
        if request:
            ip_address = request.META.get('REMOTE_ADDR')

        log_data = {
            "user_id": user.id if user else None,
            "username": user.username if user else "anonymous",
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "metadata": metadata or {},
            "ip_address": ip_address,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        db.activity_logs.insert_one(log_data)
    except PyMongoError as e:
        logger.error(f"Failed to log activity to MongoDB: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in log_activity: {e}")

def update_learning_analytics(student_id, course_id, total_lessons, completed_lessons):
    """
    Upserts the learning_analytics collection in MongoDB when progress is updated.
    """
    try:
        db = get_mongo_db()
        if db is None:
            return

        percentage = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0.0

        analytics_data = {
            "$set": {
                "student_id": student_id,
                "course_id": course_id,
                "total_lessons": total_lessons,
                "completed_lessons": completed_lessons,
                "completion_percentage": percentage,
                "last_activity": datetime.now(timezone.utc).isoformat()
            }
        }

        db.learning_analytics.update_one(
            {"student_id": student_id, "course_id": course_id},
            analytics_data,
            upsert=True
        )
    except PyMongoError as e:
        logger.error(f"Failed to update learning analytics in MongoDB: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in update_learning_analytics: {e}")
